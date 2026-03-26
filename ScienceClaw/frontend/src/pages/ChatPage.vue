<template>
  <div class="relative h-full w-full overflow-hidden">
    <SimpleBar ref="simpleBarRef" @scroll="handleScroll">
      <div ref="chatContainerRef" class="relative flex flex-col h-full flex-1 min-w-0 px-5">
      <div ref="observerRef"
        class="sm:min-w-[390px] flex flex-row items-center justify-between pt-3 pb-1 gap-1 sticky top-0 z-10 bg-[var(--background-gray-main)] flex-shrink-0">
        <div class="flex items-center flex-1">
        </div>
        <div class="max-w-full sm:max-w-[768px] sm:min-w-[390px] flex w-full flex-col gap-[4px] overflow-hidden">
          <div
            class="text-[var(--text-primary)] text-lg font-medium w-full flex flex-row items-center justify-between flex-1 min-w-0 gap-2">
            <div class="flex flex-row items-center gap-[6px] flex-1 min-w-0">
              <span class="whitespace-nowrap text-ellipsis overflow-hidden">
                {{ title }}
              </span>
            </div>
            <div class="flex items-center gap-2 flex-shrink-0">
              <span class="relative flex-shrink-0" aria-expanded="false" aria-haspopup="dialog">
                <Popover>
                  <PopoverTrigger>
                    <button
                      class="h-8 w-8 rounded-xl inline-flex items-center justify-center border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 hover:shadow-sm transition-all duration-200 me-1.5">
                      <ShareIcon color="var(--icon-secondary)" />
                    </button>
                  </PopoverTrigger>
                  <PopoverContent>
                    <div
                      class="w-[380px] flex flex-col rounded-2xl bg-white dark:bg-[#1e1e1e] shadow-xl shadow-black/10 border border-gray-100 dark:border-gray-800"
                      style="max-width: calc(-16px + 100vw);">
                      <div class="flex flex-col p-4 gap-1">
                        <!-- Private mode option -->
                        <div @click="handleShareModeChange('private')"
                          :class="{'pointer-events-none opacity-50': sharingLoading}"
                          class="flex items-center gap-3 px-3 py-3 rounded-xl cursor-pointer transition-all duration-200 hover:bg-gray-50 dark:hover:bg-gray-900/50">
                          <div
                            :class="shareMode === 'private' ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white' : 'bg-gray-100 dark:bg-gray-800 text-[var(--text-secondary)]'"
                            class="size-9 rounded-xl flex items-center justify-center transition-colors">
                            <Lock :size="16" /></div>
                          <div class="flex flex-col flex-1 min-w-0">
                            <div class="text-sm font-semibold text-[var(--text-primary)]">{{ t('Private Only') }}</div>
                            <div class="text-xs text-[var(--text-tertiary)]">{{ t('Only visible to you') }}</div>
                          </div><Check :size="18" :class="shareMode === 'private' ? 'ml-auto text-blue-500' : 'ml-auto invisible'" />
                        </div>
                        <!-- Public mode option -->
                        <div @click="handleShareModeChange('public')"
                          :class="{'pointer-events-none opacity-50': sharingLoading}"
                          class="flex items-center gap-3 px-3 py-3 rounded-xl cursor-pointer transition-all duration-200 hover:bg-gray-50 dark:hover:bg-gray-900/50">
                          <div
                            :class="shareMode === 'public' ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white' : 'bg-gray-100 dark:bg-gray-800 text-[var(--text-secondary)]'"
                            class="size-9 rounded-xl flex items-center justify-center transition-colors">
                            <Globe :size="16" /></div>
                          <div class="flex flex-col flex-1 min-w-0">
                            <div class="text-sm font-semibold text-[var(--text-primary)]">{{ t('Public Access') }}</div>
                            <div class="text-xs text-[var(--text-tertiary)]">{{ t('Anyone with the link can view') }}</div>
                          </div><Check :size="18" :class="shareMode === 'public' ? 'ml-auto text-blue-500' : 'ml-auto invisible'" />
                        </div>
                        <div class="border-t border-gray-100 dark:border-gray-800 mt-1"></div>
                        
                        <!-- Show instant share button when in private mode -->
                        <div v-if="shareMode === 'private'">
                          <button @click.stop="handleInstantShare"
                            :disabled="sharingLoading"
                            class="inline-flex items-center justify-center whitespace-nowrap font-semibold transition-all duration-200 bg-gradient-to-r from-blue-500 to-indigo-600 text-white h-[38px] px-4 rounded-xl gap-2 text-sm w-full mt-3 shadow-md hover:shadow-lg hover:shadow-indigo-500/20 active:scale-[0.97] disabled:opacity-50 disabled:cursor-not-allowed">
                            <div v-if="sharingLoading" class="size-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                            <Link v-else :size="15" />
                            {{ sharingLoading ? t('Sharing...') : t('Share Instantly') }}
                          </button>
                        </div>
                        
                        <!-- Show copy link button when in public mode -->
                        <div v-else>
                          <button @click.stop="handleCopyLink"
                            :class="linkCopied ? 'inline-flex items-center justify-center whitespace-nowrap font-medium transition-all duration-200 bg-white dark:bg-[#2a2a2a] text-[var(--text-primary)] border border-gray-200 dark:border-gray-700 h-[38px] px-4 rounded-xl gap-2 text-sm w-full mt-3' : 'inline-flex items-center justify-center whitespace-nowrap font-semibold transition-all duration-200 bg-gradient-to-r from-blue-500 to-indigo-600 text-white h-[38px] px-4 rounded-xl gap-2 text-sm w-full mt-3 shadow-md hover:shadow-lg hover:shadow-indigo-500/20 active:scale-[0.97]'"
                            data-tabindex="" tabindex="-1">
                            <Link v-if="!linkCopied" :size="16" stroke="currentColor" :stroke-width="2" />
                            <Check v-else :size="16" color="var(--text-primary)" />
                            {{ linkCopied ? t('Link Copied') : t('Copy Link') }}
                          </button>
                        </div>
                      </div>
                    </div>
                  </PopoverContent>
                </Popover>
              </span>
              <button @click="handleFileListShow"
                class="h-8 w-8 rounded-xl inline-flex items-center justify-center border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 hover:shadow-sm transition-all duration-200">
                <FileSearch class="text-[var(--icon-secondary)]" :size="16" />
              </button>

            </div>
          </div>
          <div class="w-full flex justify-between items-center">
          </div>
        </div>
        <div class="flex-1"></div>
      </div>

      <div class="mx-auto w-full max-w-full sm:max-w-[768px] sm:min-w-[390px] flex flex-col flex-1">
        <div class="flex flex-col w-full gap-[12px] pb-[80px] pt-[12px] flex-1 overflow-y-auto">
          <template v-for="(group, index) in groupedMessages" :key="group.id">
            <!-- Process groups: compact reasoning indicator -->
            <div v-if="group.type === 'process'" class="flex items-start py-1 my-1">
              <div
                @click="showActivityForTurn(getProcessTurnIndex(index))"
                class="process-indicator flex items-center gap-2.5 px-3.5 py-2 rounded-xl cursor-pointer transition-all duration-200 select-none group/proc border"
                :class="isLoading && index === lastProcessGroupIndex
                  ? 'bg-gradient-to-r from-blue-50/80 to-indigo-50/60 dark:from-blue-950/30 dark:to-indigo-950/20 border-blue-200/50 dark:border-blue-800/30 shadow-sm shadow-blue-500/5 hover:shadow-md hover:shadow-blue-500/10'
                  : 'bg-white dark:bg-gray-800/50 border-gray-100 dark:border-gray-700/50 hover:border-gray-200 dark:hover:border-gray-600 hover:shadow-sm'"
              >
                <!-- Spinning ring when running -->
                <div v-if="isLoading && index === lastProcessGroupIndex" class="relative size-4 flex-shrink-0">
                  <div class="absolute inset-0 rounded-full border-2 border-blue-200 dark:border-blue-800"></div>
                  <div class="absolute inset-0 rounded-full border-2 border-blue-500 border-t-transparent animate-spin"></div>
                </div>
                <!-- Failed: amber circle -->
                <div v-else-if="lastTurnHadError && index === lastProcessGroupIndex" class="size-4 rounded-full bg-amber-400 flex items-center justify-center flex-shrink-0 shadow-sm shadow-amber-400/30">
                  <svg class="size-2.5 text-white" viewBox="0 0 16 16" fill="currentColor"><path fill-rule="evenodd" d="M8 16A8 8 0 108 0a8 8 0 000 16zM7.25 4.75a.75.75 0 011.5 0v3.5a.75.75 0 01-1.5 0v-3.5zM8 11a1 1 0 100-2 1 1 0 000 2z"/></svg>
                </div>
                <!-- Completed: gradient check circle -->
                <div v-else class="size-4 rounded-full bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center flex-shrink-0 shadow-sm shadow-emerald-400/30">
                  <svg class="size-2.5 text-white" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="2 6.5 5 9.5 10 3"/></svg>
                </div>

                <!-- Title -->
                <span class="text-[13px] font-semibold transition-colors"
                  :class="isLoading && index === lastProcessGroupIndex
                    ? 'text-blue-600 dark:text-blue-400'
                    : lastTurnHadError && index === lastProcessGroupIndex
                      ? 'text-amber-600 dark:text-amber-400'
                      : 'text-gray-500 dark:text-gray-400 group-hover/proc:text-gray-700 dark:group-hover/proc:text-gray-200'"
                >
                  {{ isLoading && index === lastProcessGroupIndex ? t('Reasoning') + '...' : (lastTurnHadError && index === lastProcessGroupIndex ? t('Reasoning failed') : t('Reasoning completed')) }}
                </span>

                <!-- Tool count badge -->
                <span v-if="(group.messages || []).filter(m => m.type === 'tool').length > 0"
                  class="text-[10px] font-bold px-2 py-0.5 rounded-full tabular-nums"
                  :class="isLoading && index === lastProcessGroupIndex
                    ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-300'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400'"
                >
                  {{ (group.messages || []).filter(m => m.type === 'tool').length }} {{ (group.messages || []).filter(m => m.type === 'tool').length === 1 ? t('tool') : t('tools') }}
                </span>

                <!-- Arrow hint -->
                <svg class="size-3.5 text-gray-300 dark:text-gray-600 group-hover/proc:text-gray-400 dark:group-hover/proc:text-gray-500 transition-colors flex-shrink-0 ml-0.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 4l4 4-4 4"/></svg>
              </div>
            </div>
            <ChatMessage v-else-if="group.type === 'single' && group.message" :message="group.message"
              @toolClick="handleToolClick" @suggestionClick="handleSuggestionClick" @convertToPdf="handleConvertToPdf" :mode="mode"
              :isLast="index === lastProcessGroupIndex" :isLoading="isLoading" />
          </template>

          <!-- Loading indicator -->
          <LoadingIndicator v-if="isLoading" :text="$t('Thinking')" />

        </div>

        <div class="flex flex-col bg-[var(--background-gray-main)] sticky bottom-0">
          <button @click="handleFollow" v-if="!follow"
            class="flex items-center justify-center w-[36px] h-[36px] rounded-full bg-[var(--background-white-main)] hover:bg-[var(--background-gray-main)] clickable border border-[var(--border-main)] shadow-[0px_5px_16px_0px_var(--shadow-S),0px_0px_1.25px_0px_var(--shadow-S)] absolute -top-20 left-1/2 -translate-x-1/2">
            <ArrowDown class="text-[var(--icon-primary)]" :size="20" />
          </button>
          <!-- Skill Save Prompt Bar -->
          <div v-if="pendingSkillSave && !isLoading"
            class="flex items-center gap-3 px-4 py-3 mb-2 rounded-xl border border-blue-200 dark:border-blue-800 bg-blue-50/80 dark:bg-blue-950/30 animate-fadeIn">
            <Package :size="18" class="text-blue-500 flex-shrink-0" />
            <div class="flex-1 min-w-0">
              <div class="text-sm font-medium text-[var(--text-primary)] truncate">
                {{ t('Save skill "{name}" to library?', { name: pendingSkillSave }) }}
              </div>
              <div class="text-xs text-[var(--text-tertiary)]">
                {{ t('The skill will be saved permanently for future use') }}
              </div>
            </div>
            <button @click="handleSaveSkill" :disabled="savingSkill"
              class="px-3 py-1.5 text-sm font-medium rounded-lg bg-blue-500 text-white hover:bg-blue-600 transition-colors disabled:opacity-50 flex-shrink-0">
              {{ savingSkill ? t('Saving...') : t('Save') }}
            </button>
            <button @click="handleSkipSkillSave" :disabled="savingSkill"
              class="p-1 rounded-md hover:bg-[var(--fill-tsp-gray-main)] transition-colors flex-shrink-0">
              <X :size="16" class="text-[var(--icon-tertiary)]" />
            </button>
          </div>
          <!-- Tool Save Prompt Bar -->
          <div v-if="pendingToolSave && !isLoading"
            class="flex items-center gap-3 px-4 py-3 mb-2 rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50/80 dark:bg-emerald-950/30 animate-fadeIn">
            <Wrench :size="18" class="text-emerald-500 flex-shrink-0" />
            <div class="flex-1 min-w-0">
              <div class="text-sm font-medium text-[var(--text-primary)] truncate">
                {{ t('Save tool "{name}" to library?', { name: pendingToolSave }) }}
              </div>
              <div class="text-xs text-[var(--text-tertiary)]">
                {{ t('The tool will be saved permanently and available in new sessions') }}
              </div>
            </div>
            <button @click="handleSaveTool" :disabled="savingTool"
              class="px-3 py-1.5 text-sm font-medium rounded-lg bg-emerald-500 text-white hover:bg-emerald-600 transition-colors disabled:opacity-50 flex-shrink-0">
              {{ savingTool ? t('Saving...') : t('Save') }}
            </button>
            <button @click="handleSkipToolSave" :disabled="savingTool"
              class="p-1 rounded-md hover:bg-[var(--fill-tsp-gray-main)] transition-colors flex-shrink-0">
              <X :size="16" class="text-[var(--icon-tertiary)]" />
            </button>
          </div>
          <ChatBox v-model="inputMessage" :rows="1" @submit="handleSubmit" :isRunning="isLoading" @stop="handleStop"
            :attachments="attachments"
            :sessionId="sessionId"
            :models="models"
            :selectedModelId="selectedModelId"
            @update:selectedModelId="selectedModelId = $event"
            @files-changed="onFilesChanged"
            @open-model-settings="openSettingsDialog('models')"
            />
        </div>
      </div>
    </div>
      <!-- Activity Panel (right side - Cursor-style thinking + execution timeline) -->
      <ActivityPanel
        :key="sessionId"
        ref="activityPanelRef"
        :items="displayActivityItems"
        :plan="displayActivityPlan"
        :isLoading="isLoading && selectedActivityTurn === -1"
        :lastTurnHadError="lastTurnHadError"
        @toolClick="handleToolClick"
        @close="() => {}"
      />
      <!-- Tool Detail Panel (opens on top when a tool is clicked) -->
      <ToolPanel ref="toolPanel" :size="toolPanelSize" :sessionId="sessionId" :realTime="realTime" 
      :isShare="false"
      @jumpToRealTime="jumpToRealTime" />
    </SimpleBar>
  </div>
</template>

<script setup lang="ts">
import SimpleBar from '../components/SimpleBar.vue';
import { ref, onMounted, watch, nextTick, onUnmounted, reactive, toRefs, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import ChatBox from '../components/ChatBox.vue';
import ChatMessage from '../components/ChatMessage.vue';
import * as agentApi from '../api/agent';
import { Message, MessageContent, ToolContent, StepContent, AttachmentsContent, ThinkingContent } from '../types/message';
import {
  StepEventData,
  ToolEventData,
  MessageEventData,
  ErrorEventData,
  TitleEventData,
  PlanEventData,
  ThinkingEventData,
  DoneEventData,
  AgentSSEEvent,
} from '../types/event';
import ToolPanel from '../components/ToolPanel.vue'
import PlanPanel from '../components/PlanPanel.vue';
import { ArrowDown, FileSearch, PanelLeft, Lock, Globe, Link, Check, Package, Wrench, X } from 'lucide-vue-next';
import ShareIcon from '@/components/icons/ShareIcon.vue';
import { showErrorToast, showSuccessToast } from '../utils/toast';
import type { FileInfo } from '../api/file';
import { useLeftPanel } from '../composables/useLeftPanel'
import { useSessionListUpdate } from '../composables/useSessionListUpdate'
import { useSessionFileList } from '../composables/useSessionFileList'
import { useFilePanel } from '../composables/useFilePanel'
import { useAuth } from '../composables/useAuth' // Import useAuth
import { copyToClipboard } from '../utils/dom'
import { SessionStatus } from '../types/response';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import LoadingIndicator from '@/components/ui/LoadingIndicator.vue';
import { listModels, type ModelConfig } from '../api/models';
import { useSettingsDialog } from '../composables/useSettingsDialog';
import { useSessionNotifications } from '../composables/useSessionNotifications';
import { consumePendingChat } from '../composables/usePendingChat';

import { useMessageGrouper } from '../composables/useMessageGrouper';
import ProcessMessage from '../components/ProcessMessage.vue';
import ActivityPanel from '../components/ActivityPanel.vue';
import type { ActivityItem } from '../components/ActivityPanel.vue';

const router = useRouter()
const { t, locale } = useI18n()
const { shared } = useSessionFileList()
const { hideFilePanel, showFileListPanel } = useFilePanel()
const { currentUser } = useAuth()
const { updateSessionTitle } = useSessionListUpdate()
const { onSessionUpdated } = useSessionNotifications()
const sessionSource = ref<string | null>(null);
const IM_PASSIVE_SYNC_INTERVAL_MS = 2000;
let imPassiveSyncTimer: ReturnType<typeof setInterval> | null = null;
let imPassiveSyncInFlight = false;

// Models related state
const models = ref<ModelConfig[]>([]);
const selectedModelId = ref<string | null>(null);
const { isSettingsDialogOpen, openSettingsDialog } = useSettingsDialog();


// Create initial state factory
const createInitialState = () => ({
  inputMessage: '',
  isLoading: false,
  sessionId: undefined as string | undefined,
  messages: [] as Message[],
  toolPanelSize: 0,
  realTime: true,
  follow: true,
  title: t('New Chat'),
  plan: undefined as PlanEventData | undefined,
  lastNoMessageTool: undefined as ToolContent | undefined,
  lastMessageTool: undefined as ToolContent | undefined,
  lastTool: undefined as ToolContent | undefined,
  lastEventId: undefined as string | undefined,
  cancelCurrentChat: null as (() => void) | null,
  attachments: [] as FileInfo[],
  shareMode: 'private' as 'private' | 'public', // Default to private mode
  linkCopied: false,
  sharingLoading: false, // Loading state for share operations
  mode: 'deep' as string,
  thinkingContent: '' as string, // Thinking event content
  activityItems: [] as ActivityItem[], // Activity panel timeline items
  activitySnapshots: [] as { items: ActivityItem[], plan: PlanEventData | undefined }[], // Per-turn snapshots
  selectedActivityTurn: -1 as number, // Which turn to show (-1 = live/current)
  pendingToolCallIds: [] as string[], // Tools not yet associated with any plan step
});

// Create reactive state
const state = reactive(createInitialState());

// Destructure refs from reactive state
const {
  inputMessage,
  isLoading,
  sessionId,
  messages,
  toolPanelSize,
  realTime,
  follow,
  title,
  plan,
  lastNoMessageTool,
  lastTool,
  lastEventId,
  cancelCurrentChat,
  attachments,
  shareMode,
  linkCopied,
  sharingLoading,
  mode,
  thinkingContent,
  activityItems,
  activitySnapshots,
  selectedActivityTurn,
  pendingToolCallIds,
} = toRefs(state);

const { groupedMessages } = useMessageGrouper(messages);

// 最后一个 process 组的索引（推理失败时会先 push 一条 assistant 消息，此时最后一组不是 process，需用此判断当前轮次的 process 组）
const lastProcessGroupIndex = computed(() => {
  const groups = groupedMessages.value;
  for (let i = groups.length - 1; i >= 0; i--) {
    if (groups[i].type === 'process') return i;
  }
  return -1;
});

const displayActivityItems = computed(() => {
  if (selectedActivityTurn.value >= 0 && selectedActivityTurn.value < activitySnapshots.value.length) {
    return activitySnapshots.value[selectedActivityTurn.value].items;
  }
  return activityItems.value;
});

const displayActivityPlan = computed(() => {
  if (selectedActivityTurn.value >= 0 && selectedActivityTurn.value < activitySnapshots.value.length) {
    return activitySnapshots.value[selectedActivityTurn.value].plan;
  }
  return plan.value;
});

// Skill save prompt state (persists across state resets)
const pendingSkillSave = ref<string | null>(null);
const savingSkill = ref(false);

// Tool save prompt state (persists across state resets)
const pendingToolSave = ref<string | null>(null);
const pendingToolReplaces = ref<string | null>(null);
const savingTool = ref(false);

// 上一轮是否因报错结束（用于显示「推理失败」而非「推理完成」）
const lastTurnHadError = ref(false);

// Non-state refs that don't need reset
const toolPanel = ref<InstanceType<typeof ToolPanel>>()
const activityPanelRef = ref<InstanceType<typeof ActivityPanel>>()
const simpleBarRef = ref<InstanceType<typeof SimpleBar>>();
const observerRef = ref<HTMLDivElement>();
const chatContainerRef = ref<HTMLDivElement>();

// Watch message changes and automatically scroll to bottom
watch(messages, async () => {
  await nextTick();
  if (follow.value) {
    simpleBarRef.value?.scrollToBottom();
  }
}, { deep: true });



const getLastStep = (): StepContent | undefined => {
  return messages.value.filter(message => message.type === 'step').pop()?.content as StepContent;
}

// Determine which conversation turn a process group belongs to
const getProcessTurnIndex = (groupIndex: number): number => {
  let userCount = 0;
  for (let i = 0; i < groupIndex; i++) {
    const g = groupedMessages.value[i];
    if (g.type === 'single' && g.message?.type === 'user') {
      userCount++;
    }
  }
  return Math.max(0, userCount - 1);
};

// Toggle activity panel for a specific turn
const showActivityForTurn = (turnIndex: number) => {
  const targetTurn = (turnIndex >= 0 && turnIndex < activitySnapshots.value.length) ? turnIndex : -1;

  // If panel is already open showing the same turn, close it
  if (activityPanelRef.value?.isShow && selectedActivityTurn.value === targetTurn) {
    activityPanelRef.value?.hide();
    return;
  }

  selectedActivityTurn.value = targetTurn;
  activityPanelRef.value?.show();
};

// ── Streaming state for message_chunk ──
const _streamingMsgIndex = ref<number | null>(null);

// Set to true when the component unmounts; async callbacks check this
// to avoid mutating dead state after the user navigated away.
let _unmounted = false;
const _processedEventIds = new Set<string>();

// Handle message_chunk event (token-by-token streaming)
const handleMessageChunkEvent = (data: any) => {
  const token = data.content || '';
  if (!token) return;

  if (_streamingMsgIndex.value === null) {
    // First chunk: create a new assistant message
    messages.value.push({
      type: 'assistant',
      content: {
        event_id: data.event_id || '',
        timestamp: data.timestamp || 0,
        content: token,
        role: 'assistant',
        attachments: [],
      } as MessageContent,
    });
    _streamingMsgIndex.value = messages.value.length - 1;
  } else {
    // Subsequent chunks: append to existing message
    const msg = messages.value[_streamingMsgIndex.value];
    if (msg && msg.content) {
      (msg.content as any).content += token;
    }
  }
};

// Handle message_chunk_done event
const handleMessageChunkDoneEvent = () => {
  _streamingMsgIndex.value = null;
};

// Handle message event (complete message, e.g. user message or fallback)
const handleMessageEvent = (messageData: MessageEventData) => {
  // If streaming was active, finalize it first
  if (_streamingMsgIndex.value !== null) {
    _streamingMsgIndex.value = null;
  }

  messages.value.push({
    type: messageData.role,
    content: {
      ...messageData
    } as MessageContent,
  });

  if (messageData.role === 'user' && messageData.attachments?.length > 0) {
    const normalizedAttachments = messageData.attachments.map((att: any) => {
      if (typeof att === 'string') {
        const filename = att.split('/').pop() || att;
        return { file_id: att, filename, size: 0, upload_date: '', content_type: '' };
      }
      return att;
    });
    messages.value.push({
      type: 'attachments',
      content: {
        ...messageData,
        attachments: normalizedAttachments,
      } as AttachmentsContent,
    });
  }
}

// Smart merge: only overwrite fields that have actual values (not empty/null/undefined)
const smartMerge = (target: any, source: any) => {
  for (const key of Object.keys(source)) {
    const val = source[key];
    // Skip undefined, null, empty objects, empty strings
    if (val === undefined || val === null) continue;
    if (typeof val === 'object' && !Array.isArray(val) && Object.keys(val).length === 0) continue;
    target[key] = val;
  }
};

// Handle tool event
const handleToolEvent = (toolData: ToolEventData) => {
  const lastStep = getLastStep();
  let toolContent: ToolContent = {
    ...toolData
  }

  // Try to parse content if it's a string
  if (typeof toolContent.content === 'string') {
    try {
      toolContent.content = JSON.parse(toolContent.content);
    } catch (e) {
      // Ignore parse error, keep as string
    }
  }

  // Detect propose_skill_save / propose_tool_save on 'called' event.
  // Only trigger during live streaming (realTime), NOT during historical event replay.
  if (toolContent.status === 'called' && realTime.value) {
    const callingArgs = toolContent.args
      || (lastTool.value?.tool_call_id === toolContent.tool_call_id ? lastTool.value.args : null);

    if (toolContent.function === 'propose_skill_save') {
      const skillName = callingArgs?.skill_name;
      if (skillName) {
        pendingSkillSave.value = skillName;
      }
    }

    if (toolContent.function === 'propose_tool_save') {
      const toolName = callingArgs?.tool_name;
      if (toolName) {
        pendingToolSave.value = toolName;
        pendingToolReplaces.value = callingArgs?.replaces || null;
      }
    }
  }

  // Sync with plan: associate tool with the currently running step
  let associatedWithStep = false;
  if (plan.value) {
    const runningStep = plan.value.steps.find(s => s.status === 'running' || s.status === 'in_progress');
    if (runningStep) {
      if (!runningStep.tools) {
        runningStep.tools = [];
      }
      const existingTool = runningStep.tools.find(t => t.tool_call_id === toolContent.tool_call_id);
      if (existingTool) {
        smartMerge(existingTool, toolContent);
      } else {
        runningStep.tools.push(toolContent as unknown as ToolEventData);
      }
      associatedWithStep = true;
    }
  }

  // Buffer tool_call_id if it couldn't be associated yet (plan or running step not available)
  if (!associatedWithStep && toolContent.name !== 'message') {
    if (!pendingToolCallIds.value.includes(toolContent.tool_call_id)) {
      pendingToolCallIds.value.push(toolContent.tool_call_id);
    }
  }

  if (lastTool.value && lastTool.value.tool_call_id === toolContent.tool_call_id) {
    // Smart merge: called event enriches calling event without overwriting args
    smartMerge(lastTool.value, toolContent);
  } else {
    if (lastStep?.status === 'running' || lastStep?.status === 'in_progress') {
      lastStep.tools.push(toolContent);
    } else {
      messages.value.push({
        type: 'tool',
        content: toolContent,
      });
    }
    lastTool.value = toolContent;
  }
  
  // Force plan update to ensure reactivity in PlanPanel
  if (plan.value) {
    plan.value = { ...plan.value };
  }

  if (toolContent.name !== 'message') {
    lastNoMessageTool.value = toolContent;
    // Push to activity timeline (update existing or add new)
    const existingIdx = activityItems.value.findIndex(
      (a) => a.type === 'tool' && a.tool?.tool_call_id === toolContent.tool_call_id
    );
    if (existingIdx >= 0) {
      const merged = { ...activityItems.value[existingIdx].tool };
      smartMerge(merged, toolContent);
      activityItems.value[existingIdx] = {
        ...activityItems.value[existingIdx],
        tool: merged,
      };
    } else {
      activityItems.value.push({
        id: `tool-${toolContent.tool_call_id}`,
        type: 'tool',
        tool: { ...toolContent },
        timestamp: toolContent.timestamp || Date.now(),
      });
    }
    activityPanelRef.value?.show();
  }
}

// Flush pending (unassociated) tools into a plan step
const flushPendingToolsToStep = (planStep: StepEventData) => {
  if (pendingToolCallIds.value.length === 0) return;
  if (!planStep.tools) planStep.tools = [];

  for (const toolCallId of pendingToolCallIds.value) {
    if (planStep.tools.some(t => t.tool_call_id === toolCallId)) continue;
    const activityItem = activityItems.value.find(
      a => a.type === 'tool' && a.tool?.tool_call_id === toolCallId
    );
    if (activityItem?.tool) {
      planStep.tools.push(activityItem.tool as unknown as ToolEventData);
    }
  }
  pendingToolCallIds.value = [];
};

// Find the best step to flush pending tools into (running > completed > first)
const findBestStepForFlush = (): StepEventData | undefined => {
  if (!plan.value?.steps.length) return undefined;
  return plan.value.steps.find(s => s.status === 'running' || s.status === 'in_progress')
    || plan.value.steps.find(s => s.status === 'completed')
    || plan.value.steps[0];
};

// Handle step event
const handleStepEvent = (stepData: StepEventData) => {
  const lastStep = getLastStep();
  
  // Sync status with plan
  if (plan.value) {
    const planStep = plan.value.steps.find(s => s.id === stepData.id);
    if (planStep) {
      planStep.status = stepData.status;

      // When a step becomes running or completed, retroactively associate any buffered tools
      if (pendingToolCallIds.value.length > 0 && (stepData.status === 'running' || stepData.status === 'in_progress' || stepData.status === 'completed')) {
        flushPendingToolsToStep(planStep);
        plan.value = { ...plan.value };
      }
    }
  }

  if (stepData.status === 'running' || stepData.status === 'in_progress') {
    messages.value.push({
      type: 'step',
      content: {
        ...stepData,
        tools: []
      } as StepContent,
    });
  } else if (stepData.status === 'completed') {
    if (lastStep) {
      lastStep.status = stepData.status;
    }
  } else if (stepData.status === 'failed') {
    isLoading.value = false;
  }
}

// Handle thinking event → append to current thinking item or create new one
const handleThinkingEvent = (thinkingData: ThinkingEventData) => {
  thinkingContent.value = thinkingData.content;
  if (thinkingData.content) {
    const last = activityItems.value[activityItems.value.length - 1];
    if (last && last.type === 'thinking') {
      last.content = (last.content || '') + thinkingData.content;
    } else {
      activityItems.value.push({
        id: `think-${Date.now()}-${activityItems.value.length}`,
        type: 'thinking',
        content: thinkingData.content,
        timestamp: thinkingData.timestamp || Date.now(),
        collapsed: true,
      });
    }
  }
  activityPanelRef.value?.show();
}

// Handle done event with statistics
const handleDoneEvent = (doneData: DoneEventData) => {
  _streamingMsgIndex.value = null;
  isLoading.value = false;
  if (plan.value?.steps?.length) {
    for (const step of plan.value.steps) {
      if (step.status !== 'completed' && step.status !== 'failed') {
        step.status = doneData.status === 'failed' ? 'failed' : 'completed';
      }
    }
    plan.value = { ...plan.value };
  }

  // 将统计信息和本轮文件列表附加到最后一条 assistant 消息
  const shouldAppendFailureMessage = doneData.status === 'failed' && !!doneData.error && !lastTurnHadError.value;
  if (doneData.status === 'failed') {
    lastTurnHadError.value = true;
  }
  if (shouldAppendFailureMessage) {
    messages.value.push({
      type: 'assistant',
      content: {
        content: doneData.error as string,
        timestamp: doneData.timestamp,
      } as MessageContent,
    });
  }
  if (doneData.statistics || doneData.round_files?.length) {
    for (let i = messages.value.length - 1; i >= 0; i--) {
      if (messages.value[i].type === 'assistant') {
        messages.value[i] = {
          ...messages.value[i],
          content: {
            ...messages.value[i].content,
            ...(doneData.statistics ? { statistics: doneData.statistics } : {}),
            ...(doneData.round_files?.length ? { round_files: doneData.round_files } : {}),
          } as MessageContent
        };
        break;
      }
    }
  }

  // Final flush: associate any remaining pending tools before snapshotting
  if (pendingToolCallIds.value.length > 0) {
    const targetStep = findBestStepForFlush();
    if (targetStep) {
      flushPendingToolsToStep(targetStep);
      if (plan.value) plan.value = { ...plan.value };
    }
  }

  // Snapshot current turn's activity data and switch to viewing it
  const turnIdx = activitySnapshots.value.length;
  activitySnapshots.value.push({
    items: [...activityItems.value],
    plan: plan.value ? JSON.parse(JSON.stringify(plan.value)) : undefined,
  });
  activityItems.value = [];
  pendingToolCallIds.value = [];
  plan.value = undefined;
  selectedActivityTurn.value = turnIdx;
}

// Handle error event
const handleErrorEvent = (errorData: ErrorEventData) => {
  lastTurnHadError.value = true;
  isLoading.value = false;
  // 防御性：将当前 plan 中 running/in_progress 步骤标为 failed，避免任务进度一直旋转
  if (plan.value?.steps?.length) {
    for (const step of plan.value.steps) {
      if (step.status === 'running' || step.status === 'in_progress') {
        step.status = 'failed';
      }
    }
    plan.value = { ...plan.value };
  }
  messages.value.push({
    type: 'assistant',
    content: {
      content: errorData.error,
      timestamp: errorData.timestamp
    } as MessageContent,
  });
}

// Handle title event (backend sends after first user message; update local title and session list)
const handleTitleEvent = (titleData: TitleEventData) => {
  title.value = titleData.title;
  if (sessionId.value) updateSessionTitle(sessionId.value, titleData.title);
}

// Handle plan event
const handlePlanEvent = (planData: PlanEventData) => {
  if (plan.value) {
    // Preserve tools from existing plan steps (matched by step ID)
    for (const newStep of planData.steps) {
      const oldStep = plan.value.steps.find(s => s.id === newStep.id);
      if (oldStep && oldStep.tools) {
        newStep.tools = oldStep.tools;
      }
    }

    // Re-buffer tools from the default _user_query step so they can be
    // properly flushed into the real plan's steps
    const defaultStep = plan.value.steps.find(s => s.id === '_user_query');
    if (defaultStep?.tools?.length) {
      for (const tool of defaultStep.tools) {
        const callId = (tool as any).tool_call_id;
        if (callId && !pendingToolCallIds.value.includes(callId)) {
          pendingToolCallIds.value.push(callId);
        }
      }
    }
  }
  plan.value = planData;

  // Flush any pending tools into the best available step
  if (pendingToolCallIds.value.length > 0) {
    const targetStep = findBestStepForFlush();
    if (targetStep) {
      flushPendingToolsToStep(targetStep);
      plan.value = { ...plan.value };
    }
  }
}

// Main event handler function
const handleEvent = (event: AgentSSEEvent) => {
  const eid = event.data?.event_id;
  if (eid && _processedEventIds.has(eid)) return;
  if (eid) _processedEventIds.add(eid);

  if (event.event === 'message_chunk') {
    handleMessageChunkEvent(event.data);
  } else if (event.event === 'message_chunk_done') {
    handleMessageChunkDoneEvent();
  } else if (event.event === 'message') {
    handleMessageEvent(event.data as MessageEventData);
  } else if (event.event === 'tool') {
    handleToolEvent(event.data as ToolEventData);
  } else if (event.event === 'step') {
    handleStepEvent(event.data as StepEventData);
  } else if (event.event === 'thinking') {
    handleThinkingEvent(event.data as ThinkingEventData);
  } else if (event.event === 'skill_save_prompt') {
    if (realTime.value) {
      const skillName = (event.data as any)?.skill_name;
      if (skillName && !pendingSkillSave.value) {
        pendingSkillSave.value = skillName;
      }
    }
  } else if (event.event === 'tool_save_prompt') {
    if (realTime.value) {
      const toolName = (event.data as any)?.tool_name;
      if (toolName && !pendingToolSave.value) {
        pendingToolSave.value = toolName;
      }
    }
  } else if (event.event === 'done') {
    handleDoneEvent(event.data as DoneEventData);
  } else if (event.event === 'wait') {
    // TODO: handle wait event
  } else if (event.event === 'error') {
    handleErrorEvent(event.data as ErrorEventData);
  } else if (event.event === 'title') {
    handleTitleEvent(event.data as TitleEventData);
  } else if (event.event === 'plan') {
    handlePlanEvent(event.data as PlanEventData);
  }
  lastEventId.value = event.data.event_id;
}

const onFilesChanged = (files: FileInfo[]) => {
  attachments.value = [...files];
};

const handleSubmit = () => {
  chat(inputMessage.value, attachments.value);
}

const getEventsAfterCursor = (events: AgentSSEEvent[], cursor?: string) => {
  if (!cursor) return events;
  const replay: AgentSSEEvent[] = [];
  let foundCursor = false;
  for (const event of events || []) {
    const eventId = (event?.data as any)?.event_id;
    if (!foundCursor) {
      if (eventId === cursor) {
        foundCursor = true;
      }
      continue;
    }
    replay.push(event);
  }
  return replay;
};

const stopImPassiveSync = () => {
  if (imPassiveSyncTimer) {
    clearInterval(imPassiveSyncTimer);
    imPassiveSyncTimer = null;
  }
};

const syncImSession = async () => {
  if (!sessionId.value || _unmounted || sessionSource.value !== 'im' || imPassiveSyncInFlight) {
    return;
  }
  if (typeof document !== 'undefined' && document.hidden) {
    return;
  }

  const targetSessionId = sessionId.value;
  imPassiveSyncInFlight = true;
  try {
    const session = await agentApi.getSession(targetSessionId);
    if (_unmounted || sessionId.value !== targetSessionId) {
      return;
    }

    sessionSource.value = session.source || null;
    if (session.title && session.title !== title.value) {
      title.value = session.title;
      updateSessionTitle(targetSessionId, session.title);
    }
    if (session.model_config_id && session.model_config_id !== selectedModelId.value) {
      selectedModelId.value = session.model_config_id;
    }

    const newEvents = getEventsAfterCursor(session.events || [], lastEventId.value);
    if (newEvents.length > 0) {
      for (const event of newEvents) {
        if (_unmounted || sessionId.value !== targetSessionId) {
          return;
        }
        handleEvent(event);
      }
      agentApi.clearUnreadMessageCount(targetSessionId).catch(() => {});
    }

    isLoading.value = session.status === SessionStatus.RUNNING || session.status === SessionStatus.PENDING;
  } catch (error) {
    console.error('[syncImSession] failed:', error);
  } finally {
    imPassiveSyncInFlight = false;
  }
};

const startImPassiveSync = () => {
  if (sessionSource.value !== 'im') {
    stopImPassiveSync();
    return;
  }
  stopImPassiveSync();
  void syncImSession();
  imPassiveSyncTimer = setInterval(() => {
    void syncImSession();
  }, IM_PASSIVE_SYNC_INTERVAL_MS);
};

const chat = async (message: string = '', files: FileInfo[] = [], reconnect: boolean = false) => {
  console.log('[chat] called, sessionId:', sessionId.value, 'reconnect:', reconnect, 'message:', message?.slice(0, 30), 'files:', files?.length, '_unmounted:', _unmounted);
  if (!sessionId.value || _unmounted) { console.log('[chat] aborted: no sessionId or unmounted'); return; }

  if (cancelCurrentChat.value) {
    cancelCurrentChat.value();
    cancelCurrentChat.value = null;
  }

  if (!reconnect) {
    if (message.trim()) {
      messages.value.push({
        type: 'user',
        content: {
          content: message,
          timestamp: Math.floor(Date.now() / 1000)
        } as MessageContent,
      });
    }

    if (files.length > 0) {
      messages.value.push({
        type: 'attachments',
        content: {
          role: 'user',
          attachments: files
        } as AttachmentsContent,
      });
    }

    inputMessage.value = '';
    attachments.value = [];
    selectedActivityTurn.value = -1;
    activityItems.value = [];
    pendingToolCallIds.value = [];

    if (message.trim()) {
      lastTurnHadError.value = false;
      plan.value = {
        event_id: '',
        timestamp: Math.floor(Date.now() / 1000),
        steps: [{
          event_id: '',
          timestamp: Math.floor(Date.now() / 1000),
          id: '_user_query',
          description: message.trim(),
          status: 'running',
          tools: [],
        }],
      } as PlanEventData;
    } else {
      plan.value = undefined;
    }
  }

  follow.value = true;
  isLoading.value = true;
  activityPanelRef.value?.show();

  const chatSessionId = sessionId.value;
  const isStale = () => _unmounted;

  // SSE inactivity timeout (10 minutes without any event → force close)
  const SSE_TIMEOUT_MS = 10 * 60 * 1000;
  let sseTimer: ReturnType<typeof setTimeout> | null = null;

  const resetSSETimer = () => {
    if (sseTimer) clearTimeout(sseTimer);
    sseTimer = setTimeout(() => {
      if (isStale()) return;
      console.warn('SSE inactivity timeout, force closing connection');
      isLoading.value = false;
      if (cancelCurrentChat.value) {
        cancelCurrentChat.value();
        cancelCurrentChat.value = null;
      }
    }, SSE_TIMEOUT_MS);
  };

  const clearSSETimer = () => {
    if (sseTimer) { clearTimeout(sseTimer); sseTimer = null; }
  };

  resetSSETimer();

  try {
    const cancelFn = await agentApi.chatWithSession(
      chatSessionId,
      {
        message: message,
        event_id: lastEventId.value,
        attachments: files.map((file: FileInfo) => file.file_id),
        language: locale.value,
        model_config_id: selectedModelId.value || undefined,
      },
      {
        onOpen: () => {
          if (isStale()) return;
          console.log('Chat opened');
          isLoading.value = true;
          resetSSETimer();
        },
        onMessage: ({ event, data }) => {
          if (isStale()) return;
          resetSSETimer();
          try {
            handleEvent({
              event: event as AgentSSEEvent['event'],
              data: data as AgentSSEEvent['data']
            });
          } catch (e) {
            console.error('handleEvent error:', e);
          }
        },
        onClose: () => {
          clearSSETimer();
          if (isStale()) return;
          console.log('Chat closed');
          isLoading.value = false;
          cancelCurrentChat.value = null;
        },
        onError: (error) => {
          clearSSETimer();
          if (isStale()) return;
          console.error('Chat error:', error);
          isLoading.value = false;
          cancelCurrentChat.value = null;
        }
      }
    );

    if (isStale()) {
      cancelFn();
      return;
    }
    cancelCurrentChat.value = cancelFn;
  } catch (error) {
    clearSSETimer();
    if (isStale()) return;
    console.error('Chat error:', error);
    isLoading.value = false;
    cancelCurrentChat.value = null;
  }
}

const restoreSession = async () => {
  _processedEventIds.clear();
  console.log('[restoreSession] start, sessionId:', sessionId.value, '_unmounted:', _unmounted);
  stopImPassiveSync();
  if (!sessionId.value) {
    showErrorToast(t('Session not found'));
    router.replace('/');
    return;
  }

  const restoreTarget = sessionId.value;
  const isStale = () => _unmounted;

  let session;
  try {
    session = await agentApi.getSession(restoreTarget);
    console.log('[restoreSession] loaded, status:', session.status, 'events:', session.events?.length, '_unmounted:', _unmounted);
  } catch (error: any) {
    console.warn('[restoreSession] FAILED to load session:', error);
    if (error?.code === 404) {
      showErrorToast(t('Session not found'));
    }
    if (!isStale()) {
      router.replace('/');
    }
    return;
  }

  if (isStale()) { console.log('[restoreSession] stale after load, aborting'); return; }

  sessionSource.value = session.source || null;
  if (session.title) {
    title.value = session.title;
    updateSessionTitle(sessionId.value, session.title);
  }
  shareMode.value = session.is_shared ? 'public' : 'private';
  if (session.mode) {
    mode.value = session.mode;
  }
  if (session.model_config_id) {
    selectedModelId.value = session.model_config_id;
  }
  realTime.value = false;
  for (const event of session.events) {
    if (isStale()) return;
    handleEvent(event);
  }
  realTime.value = true;

  if (isStale()) return;

  if (sessionSource.value === 'im') {
    isLoading.value = session.status === SessionStatus.RUNNING || session.status === SessionStatus.PENDING;
    startImPassiveSync();
  } else if (session.status === SessionStatus.RUNNING || session.status === SessionStatus.PENDING) {
    const hasEvents = session.events && session.events.length > 0;
    if (!hasEvents && session.status === SessionStatus.PENDING) {
      console.log('[restoreSession] PENDING with no events, idle');
    } else {
      const lastEvent = session.events?.[session.events.length - 1];
      const lastTs = lastEvent?.data?.timestamp || 0;
      const staleThresholdSec = 15 * 60;
      const sessionIsStale = lastTs > 0 && (Math.floor(Date.now() / 1000) - lastTs) > staleThresholdSec;

      if (sessionIsStale) {
        console.warn('[restoreSession] session stale, stopping');
        try { await agentApi.stopSession(restoreTarget); } catch (_) { /* ignore */ }
        isLoading.value = false;
      } else {
        console.log('[restoreSession] session RUNNING, reconnecting SSE...');
        await chat('', [], true);
        console.log('[restoreSession] reconnect done');
      }
    }
  } else {
    console.log('[restoreSession] session status:', session.status, '- no reconnect needed');
  }
  agentApi.clearUnreadMessageCount(restoreTarget);
}



// Initialize active conversation
  onMounted(async () => {
    hideFilePanel();
    const routeParams = router.currentRoute.value.params;
    console.log('[ChatPage] onMounted, sessionId:', routeParams.sessionId);
    if (routeParams.sessionId) {
      sessionId.value = String(routeParams.sessionId) as string;

      const pending = consumePendingChat();
      if (pending?.message) {
        console.log('[ChatPage] has pending chat, files:', pending.files?.length || 0);
        if (pending.mode) mode.value = pending.mode;
        if (pending.selectedModelId) selectedModelId.value = pending.selectedModelId;
        chat(pending.message, pending.files || []);
      } else {
        console.log('[ChatPage] no pending chat, restoring session');
        restoreSession();
      }
    }

  onSessionUpdated(({ session_id, session_event }) => {
    if (!sessionId.value || session_id !== sessionId.value || _unmounted) return;
    if (session_event) {
      if (session_event.event === 'message' && session_event.data?.role === 'user') {
        isLoading.value = true;
        lastTurnHadError.value = false;
        selectedActivityTurn.value = -1;
        activityItems.value = [];
        pendingToolCallIds.value = [];
        activityPanelRef.value?.show();
      }
      handleEvent(session_event as any);
      return;
    }
  });

  // Load models
  const modelsData = await listModels().catch(err => {
    console.error("Failed to load models", err);
    return [];
  });
  models.value = modelsData;

  // No models available — guide user to configure one
  if (models.value.length === 0) {
    openSettingsDialog('models');
  } else if (!selectedModelId.value || !models.value.find(m => m.id === selectedModelId.value)) {
    const sys = models.value.find(m => m.is_system);
    if (sys) selectedModelId.value = sys.id;
    else if (models.value.length > 0) selectedModelId.value = models.value[0].id;
  }
});

// Refresh model list when settings dialog closes
watch(isSettingsDialogOpen, async (newVal, oldVal) => {
  if (oldVal === true && newVal === false) {
    try {
      const modelsData = await listModels();
      models.value = modelsData;
      if (!selectedModelId.value || !modelsData.find(m => m.id === selectedModelId.value)) {
        const sys = modelsData.find(m => m.is_system);
        selectedModelId.value = sys ? sys.id : (modelsData.length > 0 ? modelsData[0].id : null);
      }
    } catch (err) {
      console.error("Failed to refresh models after settings change", err);
    }
  }
});

onUnmounted(() => {
  console.log('[ChatPage] onUnmounted, sessionId:', sessionId.value);
  _unmounted = true;
  stopImPassiveSync();
  if (cancelCurrentChat.value) {
    cancelCurrentChat.value();
    cancelCurrentChat.value = null;
  }
})

const isLastNoMessageTool = (tool: ToolContent) => {
  return tool.tool_call_id === lastNoMessageTool.value?.tool_call_id;
}

const isLiveTool = (tool: ToolContent) => {
  if (tool.status === 'calling') {
    return true;
  }
  if (!isLastNoMessageTool(tool)) {
    return false;
  }
  if (tool.timestamp > Date.now() - 5 * 60 * 1000) {
    return true;
  }
  return false;
}

const handleToolClick = (tool: ToolContent) => {
  realTime.value = false;
  if (sessionId.value) {
    toolPanel.value?.showToolPanel(tool, isLiveTool(tool));
  }
}

const handleSuggestionClick = (question: string) => {
  chat(question);
}

const handleConvertToPdf = () => {
  inputMessage.value = '转成pdf';
}

const handleSaveSkill = async () => {
  if (!sessionId.value || !pendingSkillSave.value) return;
  savingSkill.value = true;
  try {
    await agentApi.saveSkillFromSession(sessionId.value, pendingSkillSave.value);
    showSuccessToast(t('Skill "{name}" saved successfully', { name: pendingSkillSave.value }));
    pendingSkillSave.value = null;
  } catch (e) {
    showErrorToast(t('Failed to save skill'));
  } finally {
    savingSkill.value = false;
  }
}

const handleSkipSkillSave = () => {
  pendingSkillSave.value = null;
}

const handleSaveTool = async () => {
  if (!sessionId.value || !pendingToolSave.value) return;
  savingTool.value = true;
  try {
    await agentApi.saveToolFromSession(
      sessionId.value,
      pendingToolSave.value,
      pendingToolReplaces.value || undefined,
    );
    showSuccessToast(t('Tool "{name}" saved successfully', { name: pendingToolSave.value }));
    pendingToolSave.value = null;
    pendingToolReplaces.value = null;
  } catch (e) {
    showErrorToast(t('Failed to save tool'));
  } finally {
    savingTool.value = false;
  }
  activityPanelRef.value?.hide();
}

const handleSkipToolSave = () => {
  pendingToolSave.value = null;
  pendingToolReplaces.value = null;
  activityPanelRef.value?.hide();
}

const jumpToRealTime = () => {
  realTime.value = true;
  if (lastNoMessageTool.value) {
    toolPanel.value?.showToolPanel(lastNoMessageTool.value, isLiveTool(lastNoMessageTool.value));
  }
}

const handleFollow = () => {
  follow.value = true;
  simpleBarRef.value?.scrollToBottom();
}

const handleScroll = (_: Event) => {
  follow.value = simpleBarRef.value?.isScrolledToBottom() ?? false;
}

const handleStop = () => {
  if (sessionId.value) {
    agentApi.stopSession(sessionId.value);
    // Manually set loading to false to reflect UI change immediately
    isLoading.value = false;
    // Also clear the cancel function if it exists (SSE connection)
    if (cancelCurrentChat.value) {
      cancelCurrentChat.value();
      cancelCurrentChat.value = null;
    }
  }
}

const handleFileListShow = () => {
  shared.value = false
  showFileListPanel()
}

// Share functionality handlers
const handleShareModeChange = async (mode: 'private' | 'public') => {
  if (!sessionId.value || sharingLoading.value) return;
  
  // If mode is same as current, no need to call API
  if (shareMode.value === mode) {
    linkCopied.value = false;
    return;
  }
  
  try {
    sharingLoading.value = true;
    
    if (mode === 'public') {
      await agentApi.shareSession(sessionId.value);
    } else {
      await agentApi.unshareSession(sessionId.value);
    }
    
    shareMode.value = mode;
    linkCopied.value = false;
  } catch (error) {
    console.error('Error changing share mode:', error);
    showErrorToast(t('Failed to change sharing settings'));
  } finally {
    sharingLoading.value = false;
  }
}

const handleInstantShare = async () => {
  if (!sessionId.value) return;
  
  try {
    sharingLoading.value = true;
    await agentApi.shareSession(sessionId.value);
    shareMode.value = 'public';
    linkCopied.value = false;
    
    // Auto copy link after sharing
    await handleCopyLink();
  } catch (error) {
    console.error('Error sharing session:', error);
    showErrorToast(t('Failed to share session'));
  } finally {
    sharingLoading.value = false;
  }
}

const formatStatsDuration = (ms: number): string => {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const mins = Math.floor(ms / 60000);
  const secs = ((ms % 60000) / 1000).toFixed(0);
  return `${mins}m ${secs}s`;
};

const formatTokenCount = (count: number): string => {
  if (count < 1000) return `${count}`;
  return `${(count / 1000).toFixed(1)}K`;
};

const handleCopyLink = async () => {
  if (!sessionId.value) return;
  
  const shareUrl = `${window.location.origin}/share/${sessionId.value}`;
  
  try {
    const success = await copyToClipboard(shareUrl);
    
    if (success) {
      linkCopied.value = true;
      setTimeout(() => {
        linkCopied.value = false;
      }, 3000);
      showSuccessToast(t('Link copied to clipboard'));
    } else {
      showErrorToast(t('Failed to copy link'));
    }
  } catch (error) {
    console.error('Error copying share link:', error);
    showErrorToast(t('Failed to copy link'));
  }
}
</script>

<style scoped>
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fadeIn {
  animation: fadeIn 0.4s ease-out;
}
</style>
