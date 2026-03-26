from motor.motor_asyncio import AsyncIOMotorClient
from loguru import logger
from backend.config import settings


class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

    @classmethod
    async def connect(cls):
        if cls.client is None:
            try:
                # Build connection string
                # Format: mongodb://username:password@host:port/database?authSource=admin
                auth_part = ""
                if settings.mongodb_username and settings.mongodb_password:
                    auth_part = f"{settings.mongodb_username}:{settings.mongodb_password}@"
                
                uri = f"mongodb://{auth_part}{settings.mongodb_host}:{settings.mongodb_port}"
                logger.info(f"Connecting to MongoDB at {settings.mongodb_host}:{settings.mongodb_port}")
                
                cls.client = AsyncIOMotorClient(uri)
                cls.db = cls.client[settings.mongodb_db_name]
                
                # Verify connection
                await cls.client.admin.command('ping')
                logger.info("Successfully connected to MongoDB")
                
                # Initialize indexes
                await cls.init_indexes()
                
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                raise e

    @classmethod
    async def close(cls):
        if cls.client:
            cls.client.close()
            cls.client = None
            cls.db = None
            logger.info("MongoDB connection closed")

    @classmethod
    async def init_indexes(cls):
        """Create necessary indexes"""
        if cls.db is None:
            return

        # Users collection
        # username unique index
        await cls.db.users.create_index("username", unique=True)
        
        # Sessions collection
        # user_id index for fast lookup
        await cls.db.sessions.create_index("user_id")
        # updated_at index for sorting
        await cls.db.sessions.create_index([("updated_at", -1)])
        
        # Session Events collection (if separated)
        # session_id index
        await cls.db.session_events.create_index("session_id")
        await cls.db.session_events.create_index([("timestamp", 1)])

        # Blocked skills collection
        await cls.db.blocked_skills.create_index(
            [("user_id", 1), ("skill_name", 1)], unique=True
        )
        await cls.db.im_user_bindings.create_index(
            [("platform", 1), ("platform_user_id", 1)], unique=True
        )
        await cls.db.im_user_bindings.create_index(
            [("platform", 1), ("science_user_id", 1), ("status", 1)]
        )
        await cls.db.im_chat_sessions.create_index(
            [("platform", 1), ("platform_chat_id", 1), ("science_user_id", 1), ("status", 1)]
        )
        await cls.db.im_chat_sessions.create_index(
            [("platform", 1), ("conversation_scope_id", 1), ("science_user_id", 1), ("session_mode", 1), ("status", 1)]
        )
        await cls.db.im_chat_sessions.create_index([("updated_at", -1)])
        await cls._drop_matching_indexes(
            cls.db.im_message_dedup,
            keys_to_drop=[
                (("platform", 1), ("message_id", 1)),
            ],
        )
        await cls.db.im_message_dedup.create_index(
            [("platform", 1), ("delivery_id", 1)], unique=True
        )
        await cls.db.im_message_dedup.create_index(
            [("platform", 1), ("message_id", 1)]
        )
        await cls.db.im_message_dedup.create_index(
            "created_at",
            expireAfterSeconds=86400
        )
        await cls.db.im_conversation_bindings.create_index(
            [("platform", 1), ("conversation_scope_id", 1)], unique=True
        )
        await cls.db.im_conversation_bindings.create_index(
            [("platform", 1), ("owner_science_user_id", 1), ("status", 1)]
        )
        await cls.db.im_binding_tokens.create_index(
            [("platform", 1), ("token", 1)], unique=True
        )
        await cls.db.im_binding_tokens.create_index(
            [("platform", 1), ("science_user_id", 1), ("status", 1)]
        )
        await cls.db.im_binding_tokens.create_index(
            [("expires_at", 1)]
        )

    @classmethod
    async def _drop_matching_indexes(cls, collection, keys_to_drop):
        try:
            index_info = await collection.index_information()
        except Exception as exc:
            logger.warning(f"Failed to inspect MongoDB indexes for {collection.name}: {exc}")
            return
        normalized_targets = {tuple(item) for item in keys_to_drop}
        for index_name, payload in index_info.items():
            if index_name == "_id_":
                continue
            keys = tuple((str(key), int(direction)) for key, direction in payload.get("key", []))
            if keys not in normalized_targets:
                continue
            try:
                await collection.drop_index(index_name)
                logger.info(f"Dropped legacy MongoDB index {collection.name}.{index_name}")
            except Exception as exc:
                logger.warning(f"Failed to drop legacy index {collection.name}.{index_name}: {exc}")

    @classmethod
    def get_collection(cls, collection_name: str):
        if cls.db is None:
             # Lazy connect or raise error. 
             # Ideally connection should be established at startup.
             raise RuntimeError("Database not initialized. Call connect() first.")
        return cls.db[collection_name]

# Global instance helper
db = MongoDB
