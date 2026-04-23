<template>
  <div class="session-item-wrapper" ref="wrapperRef">
    <!-- Swipe delete background -->
    <div class="swipe-delete-bg absolute inset-y-0 right-0 flex items-center justify-end px-4 bg-red-500 rounded-lg"
      :style="{ opacity: Math.min(Math.abs(swipeOffset) / 80, 1) }">
      <Trash2 :size="18" class="text-white" />
    </div>

    <div @click="handleSessionClick"
      @mouseenter="isHovered = true"
      @mouseleave="isHovered = false"
      @touchstart="handleTouchStart"
      @touchmove="handleTouchMove"
      @touchend="handleTouchEnd"
      class="session-item group flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-all duration-150 relative"
      :class="isCurrentSession
        ? 'bg-blue-50 dark:bg-blue-900/30'
        : 'hover:bg-gray-50 dark:hover:bg-gray-800/50'"
      :style="{ transform: `translateX(${swipeOffset}px)` }">

      <!-- Status indicator dot -->
      <div class="status-dot flex-shrink-0 w-1.5 h-1.5 rounded-full mt-1.5 transition-colors duration-200"
        :class="{
          'bg-blue-500': isCurrentSession,
          'bg-amber-400': isRunning || (session.pinned && !isRunning),
          'bg-gray-300 dark:bg-gray-600': !isCurrentSession && !isRunning && !session.pinned
        }">
      </div>

      <!-- Content area -->
      <div class="flex-1 min-w-0">
        <!-- Title row -->
        <div class="flex items-center gap-2">
          <span class="truncate text-sm font-medium flex-1 min-w-0 transition-colors duration-150"
            :class="isCurrentSession ? 'text-blue-600 dark:text-blue-300' : 'text-gray-700 dark:text-gray-100'"
            :title="session.title || t('New Chat')">
            {{ session.title || t('New Chat') }}
          </span>

          <!-- Indicators row -->
          <div class="flex items-center gap-1.5 flex-shrink-0">
            <!-- WeChat badge -->
            <span v-if="session.source === 'wechat'"
              class="text-xs font-semibold px-1.5 py-0.5 rounded bg-green-50 text-green-600 dark:bg-green-900/20 dark:text-green-400 leading-none">微信</span>

            <!-- Pinned icon -->
            <Pin v-if="session.pinned" :size="12" class="text-amber-500" />

            <!-- Shared icon -->
            <Globe v-if="session.is_shared" :size="12" class="text-blue-400" />

            <!-- Running indicator -->
            <span v-if="isRunning" class="running-dots flex items-center gap-0.5">
              <span class="w-1 h-1 rounded-full bg-amber-400 animate-bounce" style="animation-delay: 0ms"></span>
              <span class="w-1 h-1 rounded-full bg-amber-400 animate-bounce" style="animation-delay: 120ms"></span>
              <span class="w-1 h-1 rounded-full bg-amber-400 animate-bounce" style="animation-delay: 240ms"></span>
            </span>

            <!-- Time -->
            <span class="text-[11px] text-gray-400 dark:text-gray-400 tabular-nums whitespace-nowrap">
              {{ session.latest_message_at ? customTime(session.latest_message_at) : '' }}
            </span>
          </div>
        </div>

        <!-- Subtitle row -->
        <div class="flex items-center gap-2 mt-0.5">
          <span class="text-xs text-gray-400 dark:text-gray-400 truncate flex-1 min-w-0"
            :title="session.latest_message || ''">
            {{ session.latest_message || '—' }}
          </span>

          <!-- Unread badge -->
          <div v-if="session.unread_message_count > 0 && !isCurrentSession"
            class="flex-shrink-0 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 flex items-center justify-center">
            <span class="text-[10px] font-medium text-white leading-none">{{ session.unread_message_count }}</span>
          </div>
        </div>
      </div>

      <!-- Quick Actions (hover) -->
      <div v-show="isHovered || isContextMenuOpen"
        @click.stop
        class="quick-actions absolute right-2 top-1/2 -translate-y-1/2 flex items-center bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
        <button @click="handleTogglePin"
          class="action-btn w-7 h-7 flex items-center justify-center transition-colors duration-100"
          :class="session.pinned
            ? 'text-amber-500 bg-amber-50 dark:bg-amber-900/20'
            : 'text-gray-400 hover:text-amber-500 hover:bg-gray-50 dark:hover:bg-gray-700'"
          :title="session.pinned ? t('Unpin') : t('Pin')">
          <Pin :size="14" />
        </button>
        <button @click="handleEditTitle"
          class="action-btn w-7 h-7 flex items-center justify-center text-gray-400 hover:text-blue-500 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors duration-100"
          :title="t('Rename')">
          <Pencil :size="14" />
        </button>
        <button @click="handleDeleteClick"
          class="action-btn w-7 h-7 flex items-center justify-center text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors duration-100"
          :title="t('Delete')">
          <Trash2 :size="14" />
        </button>
      </div>
    </div>

    <!-- Rename Dialog -->
    <Teleport to="body">
      <div v-if="isRenaming" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 dark:bg-black/50" @click.self="cancelRename">
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow-xl p-4 w-[320px] max-w-[90vw]">
          <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-3">{{ t('Rename Session') }}</h3>
          <input
            ref="renameInputRef"
            v-model="newTitle"
            @keyup.enter="confirmRename"
            @keyup.escape="cancelRename"
            type="text"
            class="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
            :placeholder="t('Enter new title')"
          />
          <div class="flex justify-end gap-2 mt-4">
            <button @click="cancelRename" class="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
              {{ t('Cancel') }}
            </button>
            <button @click="confirmRename" class="px-3 py-1.5 text-sm bg-blue-500 text-white rounded-lg hover:bg-blue-600">
              {{ t('Confirm') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { Pencil, Pin, Trash2, Globe } from 'lucide-vue-next';
import { computed, ref, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import { useCustomTime } from '../composables/useTime';
import { ListSessionItem, SessionStatus } from '../types/response';
import { useDialog } from '../composables/useDialog';
import { deleteSession, updateSessionPin, updateSessionTitle } from '../api/agent';
import { showSuccessToast, showErrorToast } from '../utils/toast';
import { useLeftPanel } from '../composables/useLeftPanel';

interface Props {
  session: ListSessionItem;
}

const props = defineProps<Props>();

const { t } = useI18n();
const { customTime } = useCustomTime();
const route = useRoute();
const router = useRouter();
const { showConfirmDialog } = useDialog();
const { toggleLeftPanel } = useLeftPanel();

const isHovered = ref(false);
const isContextMenuOpen = ref(false);
const isRenaming = ref(false);
const newTitle = ref('');
const renameInputRef = ref<HTMLInputElement | null>(null);
const wrapperRef = ref<HTMLElement | null>(null);

// Swipe to delete state
const swipeOffset = ref(0);
const touchStartX = ref(0);
const touchStartY = ref(0);
const isSwiping = ref(false);
const SWIPE_THRESHOLD = 60;
const DELETE_THRESHOLD = 120;

const emit = defineEmits<{
  (e: 'deleted', sessionId: string): void
  (e: 'updated', session: ListSessionItem): void
}>();

const currentSessionId = computed(() => {
  return route.params.sessionId as string;
});

const isCurrentSession = computed(() => {
  return currentSessionId.value === props.session.session_id;
});

const isRunning = computed(() => {
  return props.session.status === SessionStatus.RUNNING || props.session.status === SessionStatus.PENDING;
});

const handleSessionClick = () => {
  if (isSwiping.value) {
    return;
  }
  router.push(`/chat/${props.session.session_id}`);

  // Auto close left panel on mobile/tablet
  if (window.innerWidth < 1280) {
    toggleLeftPanel();
  }
};

const handleTogglePin = async () => {
  try {
    await updateSessionPin(props.session.session_id, !props.session.pinned);
    emit('updated', { ...props.session, pinned: !props.session.pinned });
    showSuccessToast(props.session.pinned ? t('Unpinned') : t('Pinned'));
  } catch (error) {
    showErrorToast(t('Failed to update'));
  }
};

const handleEditTitle = () => {
  newTitle.value = props.session.title || '';
  isRenaming.value = true;
  nextTick(() => {
    renameInputRef.value?.focus();
    renameInputRef.value?.select();
  });
};

const confirmRename = async () => {
  const trimmedTitle = newTitle.value.trim();
  if (!trimmedTitle || trimmedTitle === props.session.title) {
    cancelRename();
    return;
  }

  try {
    await updateSessionTitle(props.session.session_id, trimmedTitle);
    emit('updated', { ...props.session, title: trimmedTitle });
    showSuccessToast(t('Renamed successfully'));
  } catch (error) {
    showErrorToast(t('Failed to rename'));
  }

  isRenaming.value = false;
};

const cancelRename = () => {
  isRenaming.value = false;
  newTitle.value = '';
};

const handleTouchStart = (event: TouchEvent) => {
  const touch = event.touches[0];
  if (!touch) return;
  touchStartX.value = touch.clientX;
  touchStartY.value = touch.clientY;
  isSwiping.value = false;
};

const handleTouchMove = (event: TouchEvent) => {
  const touch = event.touches[0];
  if (!touch) return;

  const deltaX = touch.clientX - touchStartX.value;
  const deltaY = touch.clientY - touchStartY.value;

  if (!isSwiping.value) {
    const isHorizontalSwipe = Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > SWIPE_THRESHOLD;
    if (!isHorizontalSwipe) {
      return;
    }
    isSwiping.value = true;
  }

  swipeOffset.value = Math.max(-DELETE_THRESHOLD - 40, Math.min(0, deltaX));
  if (Math.abs(swipeOffset.value) > SWIPE_THRESHOLD) {
    event.preventDefault();
  }
};

const handleTouchEnd = () => {
  if (!isSwiping.value) {
    swipeOffset.value = 0;
    return;
  }

  const shouldDelete = Math.abs(swipeOffset.value) >= DELETE_THRESHOLD;
  swipeOffset.value = 0;
  isSwiping.value = false;

  if (shouldDelete) {
    handleDeleteClick();
  }
};

const handleDeleteClick = () => {
  showConfirmDialog({
    title: t('Are you sure you want to delete this session?'),
    content: t('The chat history of this session cannot be recovered after deletion.'),
    confirmText: t('Delete'),
    cancelText: t('Cancel'),
    confirmType: 'danger',
    onConfirm: async () => {
      try {
        await deleteSession(props.session.session_id);
        showSuccessToast(t('Deleted successfully'));
        emit('deleted', props.session.session_id);
        if (isCurrentSession.value) {
          router.push('/');
        }
      } catch (error) {
        showErrorToast(t('Failed to delete session'));
      }
    }
  });
};
</script>

<style scoped>
.session-item-wrapper {
  padding: 1px 4px;
}

.session-item {
  min-height: 48px;
}

.session-item:hover .status-dot {
  transform: scale(1.2);
}

/* Current session glow */
.session-item.bg-blue-50\/80::before,
.session-item.bg-blue-900\/30::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 2px;
  height: 16px;
  background: linear-gradient(to bottom, #3b82f6, #6366f1);
  border-radius: 0 2px 2px 0;
}

:deep(.dark) .session-item.bg-blue-900\/30::before {
  background: linear-gradient(to bottom, #60a5fa, #818cf8);
}

.quick-actions {
  animation: slideIn 0.15s ease-out;
  z-index: 10;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-50%) translateX(8px);
  }
  to {
    opacity: 1;
    transform: translateY(-50%) translateX(0);
  }
}

.running-dots span {
  animation-duration: 0.6s;
}

/* Dark mode adjustments */
:deep(.dark) .quick-actions {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}
</style>
