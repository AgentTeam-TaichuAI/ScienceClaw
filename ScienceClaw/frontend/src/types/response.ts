import { AgentSSEEvent } from "./event";

export enum SessionStatus {
    PENDING = "pending",
    RUNNING = "running",
    WAITING = "waiting",
    COMPLETED = "completed",
    FAILED = "failed"
}

export interface CreateSessionResponse {
    session_id: string;
}

export interface GetSessionResponse {
    session_id: string;
    title: string | null;
    status: SessionStatus;
    events: AgentSSEEvent[];
    is_shared: boolean;
    mode: string;
    model_config_id: string | null;
    source?: string | null;
}

export interface ListSessionItem {
    session_id: string;
    title: string | null;
    latest_message: string | null;
    latest_message_at: number | null;
    status: SessionStatus;
    unread_message_count: number;
    is_shared: boolean;
    mode: string;
    pinned?: boolean;
    source?: string | null;
}

export interface ListSessionResponse {
    sessions: ListSessionItem[];
}

export interface ConsoleRecord {
    ps1: string;
    command: string;
    output: string;
  }
  
  export interface ShellViewResponse {
    output: string;
    session_id: string;
    console: ConsoleRecord[];
  }

export interface FileViewResponse {
    content: string;
    file: string;
}

export interface SignedUrlResponse {
    signed_url: string;
    expires_in: number;
}

export interface ShareSessionResponse {
    session_id: string;
    is_shared: boolean;
}

export interface SharedSessionResponse {
    session_id: string;
    title: string | null;
    status: SessionStatus;
    events: AgentSSEEvent[];
    is_shared: boolean;
    source?: string | null;
}

export interface SkillItem {
    name: string;
    files: string[];
}

export interface ExternalSkillItem {
    name: string;
    description: string;
    files: string[];
    blocked: boolean;
    builtin?: boolean;
    metadata?: Record<string, any>;
}

export interface InstallSkillResponse {
    installed: boolean;
    skill_name: string;
    description: string;
    files: string[];
    metadata?: Record<string, any>;
    source: string;
    normalized_source: string;
    requested_skill?: string;
    installed_directory: string;
    available_skills: string[];
    manifest_file: string;
}

export interface ExternalToolItem {
    name: string;
    tool_name?: string;
    description: string;
    file: string;
    source_file?: string;
    blocked: boolean;
    category: string;
    subcategory: string;
    tags: string[];
    parameters?: {
        type: string;
        properties: Record<string, any>;
        required?: string[];
    };
    examples?: Record<string, any>[];
    return_schema?: any;
    runner?: string;
    function_group?: string;
    function_group_zh?: string;
    discipline?: string;
    discipline_zh?: string;
    system_group?: string;
    system_group_zh?: string;
    system_subgroup?: string;
    system_subgroup_zh?: string;
}
