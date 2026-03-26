<template>
  <div class="relative h-full w-full overflow-hidden">
    <SimpleBar ref="simpleBarRef" @scroll="handleScroll">
      <div ref="chatContainerRef" class="relative flex flex-col h-full flex-1 min-w-0 px-5">
        <div ref="observerRef"
          class="sm:min-w-[390px] flex flex-row items-center justify-between pt-3 pb-2 gap-1 sticky top-0 z-10 bg-[var(--background-gray-main)]/90 backdrop-blur-sm flex-shrink-0 border-b border-gray-100/50 dark:border-gray-800/50">
          <div class="flex items-center flex-1">
            <a href="/" class="hidden sm:flex group">
              <div class="flex items-center gap-2">
                <div class="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 via-red-500 to-amber-500 p-[3px] shadow-sm transition-transform duration-200 group-hover:scale-105">
                  <div class="w-full h-full rounded-[5px] bg-white dark:bg-[#1e1e1e] flex items-center justify-center overflow-hidden">
                    <RobotAvatar class="w-full h-full" :interactive="false" />
                  </div>
                </div>
                <ScienceClawLogoTextIcon :height="30" :width="65" />
              </div>
            </a>
          </div>
          <div class="max-w-full sm:max-w-[768px] sm:min-w-[390px] flex w-full flex-col gap-[4px] overflow-hidden">
            <div class="text-[var(--text-primary)] text-base font-semibold w-full flex flex-row items-center justify-between flex-1 min-w-0 gap-2">
              <div class="flex flex-row items-center gap-[6px] flex-1 min-w-0">
                <span class="whitespace-nowrap text-ellipsis overflow-hidden">{{ title }}</span>
              </div>
              <div class="flex items-center gap-1.5 flex-shrink-0">
                <button @click="handleCopyLink"
                  class="h-8 w-8 rounded-xl inline-flex items-center justify-center transition-all duration-200 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 hover:shadow-sm">
                  <Link class="text-[var(--icon-secondary)]" :size="16" />
                </button>
                <button @click="handleFileListShow"
                  class="h-8 w-8 rounded-xl inline-flex items-center justify-center transition-all duration-200 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 hover:shadow-sm">
                  <FileSearch class="text-[var(--icon-secondary)]" :size="16" />
                </button>
              </div>
            </div>
          </div>
          <div class="flex-1"></div>
        </div>

        <div class="mx-auto w-full max-w-full sm:max-w-[768px] sm:min-w-[390px] flex flex-col flex-1">
          <div class="flex flex-col w-full gap-[12px] pb-[80px] pt-[12px] flex-1 overflow-y-auto">
            <template v-for="(group, index) in groupedMessages" :key="group.id">
              <!-- Process groups: show a compact clickable indicator -->
              <div v-if="group.type === 'process'" class="flex items-center gap-2 py-1 my-1">
                <div
                  @click="showActivityForTurn(getProcessTurnIndex(index))"
                  class="flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors w-fit select-none group/proc"
                  :class="isLoading && index === groupedMessages.length - 1
                    ? 'bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30 hover:from-blue-100 hover:to-indigo-100'
                    : 'hover:bg-[var(--fill-tsp-gray-main)]'"
                >
                  <div v-if="isLoading && index === groupedMessages.length - 1" class="w-3.5 h-3.5 border-[1.5px] border-blue-500 border-t-transparent rounded-full animate-spin flex-shrink-0"></div>
                  <svg v-else class="w-4 h-4 text-emerald-500 flex-shrink-0" viewBox="0 0 16 16" fill="currentColor">
                    <path fill-rule="evenodd" d="M8 16A8 8 0 108 0a8 8 0 000 16zm3.78-9.72a.75.75 0 00-1.06-1.06L7 8.94 5.28 7.22a.75.75 0 00-1.06 1.06l2.25 2.25a.75.75 0 001.06 0l4.25-4.25z"/>
                  </svg>
                  <span class="text-sm font-medium transition-colors"
                    :class="isLoading && index === groupedMessages.length - 1
                      ? 'text-blue-600 dark:text-blue-400'
                      : 'text-[var(--text-tertiary)] group-hover/proc:text-[var(--text-secondary)]'"
                  >
                    {{ isLoading && index === groupedMessages.length - 1 ? 'Thinking...' : 'Thought Process' }}
                  </span>
                  <span v-if="(group.messages || []).filter(m => m.type === 'tool').length > 0"
                    class="text-[10px] font-medium px-1.5 py-0.5 rounded-full"
                    :class="isLoading && index === groupedMessages.length - 1
                      ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
                      : 'bg-[var(--fill-tsp-gray-main)] text-[var(--text-tertiary)]'"
                  >
                    {{ (group.messages || []).filter(m => m.type === 'tool').length }} tools
                  </span>
                </div>
              </div>
              <ChatMessage v-else-if="group.type === 'single' && group.message" :message="group.message"
                @toolClick="handleToolClick" :mode="mode"
                :isLast="index === groupedMessages.length - 1" :isLoading="isLoading" />
            </template>

            <!-- Loading indicator -->
            <LoadingIndicator v-if="isLoading" :text="$t('Thinking')" />
          </div>

          <div class="flex flex-col bg-[var(--background-gray-main)] sticky bottom-0">
            <button @click="handleFollow" v-if="!follow"
              class="flex items-center justify-center w-[36px] h-[36px] rounded-full bg-[var(--background-white-main)] hover:bg-[var(--background-gray-main)] clickable border border-[var(--border-main)] shadow-[0px_5px_16px_0px_var(--shadow-S),0px_0px_1.25px_0px_var(--shadow-S)] absolute -top-20 left-1/2 -translate-x-1/2">
              <ArrowDown class="text-[var(--icon-primary)]" :size="20" />
            </button>
            <div class="bg-white/80 dark:bg-[#1a1a1a]/80 backdrop-blur-xl rounded-2xl border border-gray-100 dark:border-gray-800 shadow-lg shadow-black/5 flex items-center justify-between py-3 pr-3 pl-4 sm:flex-row flex-col max-sm:gap-3 max-sm:p-3 mb-3">
              <div class="flex items-center gap-2.5 w-full sm:flex-1">
                <div class="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 via-red-500 to-amber-500 p-[3px] flex-shrink-0">
                  <div class="w-full h-full rounded-[5px] bg-white dark:bg-[#1e1e1e] flex items-center justify-center overflow-hidden">
                    <RobotAvatar class="w-full h-full" :interactive="false" />
                  </div>
                </div>
                <p class="text-sm text-[var(--text-primary)]">
                  {{ replayActive
                    ? $t('ScienceClaw is replaying the task...')
                    : replayCompleted
                      ? $t('ScienceClaw task replay completed.')
                      : $t('You are viewing a shared ScienceClaw task.') }}
                </p>
              </div>
              <div class="flex items-center flex-row gap-2 max-sm:w-full">
                <button v-if="replayActive" @click="skipToEnd"
                  class="inline-flex items-center justify-center whitespace-nowrap font-semibold transition-all duration-200 bg-gradient-to-r from-blue-500 to-indigo-600 text-white h-9 rounded-xl gap-1.5 text-sm min-w-16 px-4 shadow-md hover:shadow-lg hover:shadow-indigo-500/20 active:scale-[0.97] max-sm:w-1/2">
                  <SkipForward :size="14" />
                  <span>{{ $t('Skip to Result') }}</span>
                </button>
                <button v-else-if="replayCompleted" @click="startReplay"
                  class="inline-flex items-center justify-center whitespace-nowrap font-semibold transition-all duration-200 bg-gradient-to-r from-blue-500 to-indigo-600 text-white h-9 rounded-xl gap-1.5 text-sm min-w-16 px-4 shadow-md hover:shadow-lg hover:shadow-indigo-500/20 active:scale-[0.97] max-sm:w-1/2">
                  <RotateCcw :size="14" />
                  <span>{{ $t('Replay') }}</span>
                </button>
                <button @click="handleCopyLink"
                  class="inline-flex items-center justify-center whitespace-nowrap font-medium transition-all duration-200 h-9 rounded-xl gap-1.5 text-sm min-w-16 px-4 max-sm:w-1/2 border border-gray-200 dark:border-gray-700 text-[var(--text-primary)] bg-white dark:bg-[#2a2a2a] hover:border-gray-300 hover:shadow-sm">
                  <Link :size="14" />
                  <span>{{ $t('Copy Link') }}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
      <!-- Activity Panel (right side - thinking + execution timeline) -->
      <ActivityPanel
        ref="activityPanelRef"
        :items="displayActivityItems"
        :plan="displayActivityPlan"
        :isLoading="isLoading && selectedActivityTurn === -1"
        @toolClick="handleToolClick"
        @close="() => {}"
      />
      <!-- Tool Detail Panel (opens on top when a tool is clicked) -->
      <ToolPanel ref="toolPanel" :size="toolPanelSize" :sessionId="sessionId" :realTime="realTime"
        :isShare="true"
        @jumpToRealTime="jumpToRealTime" />
    </SimpleBar>
  </div>
</template>

<script setup lang="ts">
import SimpleBar from '../components/SimpleBar.vue';
import { ref, onMounted, onUnmounted, watch, nextTick, reactive, toRefs, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
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
  StatisticsData,
  AgentSSEEvent,
} from '../types/event';
import ToolPanel from '../components/ToolPanel.vue'
import { ArrowDown, FileSearch, Link, SkipForward, RotateCcw } from 'lucide-vue-next';
import RobotAvatar from '../components/icons/RobotAvatar.vue';
import ScienceClawLogoTextIcon from '../components/icons/ScienceClawLogoTextIcon.vue';
import { showErrorToast, showSuccessToast } from '../utils/toast';
import type { FileInfo } from '../api/file';
import { useSessionFileList } from '../composables/useSessionFileList'
import { useFilePanel } from '../composables/useFilePanel'
import { copyToClipboard } from '../utils/dom'
import { useMessageGrouper } from '../composables/useMessageGrouper';
import ActivityPanel from '../components/ActivityPanel.vue';
import type { ActivityItem } from '../components/ActivityPanel.vue';
import LoadingIndicator from '@/components/ui/LoadingIndicator.vue';

const router = useRouter()
const { t } = useI18n()
const { shared } = useSessionFileList()
const { hideFilePanel, showFileListPanel } = useFilePanel()

const createInitialState = () => ({
  isLoading: false,
  sessionId: undefined as string | undefined,
  messages: [] as Message[],
  toolPanelSize: 0,
  realTime: true,
  follow: true,
  title: t('New Chat'),
  plan: undefined as PlanEventData | undefined,
  lastNoMessageTool: undefined as ToolContent | undefined,
  lastTool: undefined as ToolContent | undefined,
  lastEventId: undefined as string | undefined,
  mode: 'deep' as string,
  thinkingContent: '' as string,
  sessionStatistics: undefined as StatisticsData | undefined,
  activityItems: [] as ActivityItem[],
  activitySnapshots: [] as { items: ActivityItem[], plan: PlanEventData | undefined }[],
  selectedActivityTurn: -1 as number,
  pendingToolCallIds: [] as string[],
  replayActive: false,
  replayCompleted: false,
  jumpToEnd: false,
});

const state = reactive(createInitialState());

const {
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
  mode,
  thinkingContent,
  sessionStatistics,
  activityItems,
  activitySnapshots,
  selectedActivityTurn,
  pendingToolCallIds,
  replayActive,
  replayCompleted,
  jumpToEnd,
} = toRefs(state);

let cachedEvents: AgentSSEEvent[] = [];

const { groupedMessages } = useMessageGrouper(messages);

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

const toolPanel = ref<InstanceType<typeof ToolPanel>>()
const activityPanelRef = ref<InstanceType<typeof ActivityPanel>>()
const simpleBarRef = ref<InstanceType<typeof SimpleBar>>();
const observerRef = ref<HTMLDivElement>();
const chatContainerRef = ref<HTMLDivElement>();

watch(messages, async () => {
  await nextTick();
  if (follow.value) {
    simpleBarRef.value?.scrollToBottom();
  }
}, { deep: true });

const getLastStep = (): StepContent | undefined => {
  return messages.value.filter(message => message.type === 'step').pop()?.content as StepContent;
}

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

const showActivityForTurn = (turnIndex: number) => {
  const targetTurn = (turnIndex >= 0 && turnIndex < activitySnapshots.value.length) ? turnIndex : -1;

  if (activityPanelRef.value?.isShow && selectedActivityTurn.value === targetTurn) {
    activityPanelRef.value?.hide();
    return;
  }

  selectedActivityTurn.value = targetTurn;
  activityPanelRef.value?.show();
};

const smartMerge = (target: any, source: any) => {
  for (const key of Object.keys(source)) {
    const val = source[key];
    if (val === undefined || val === null) continue;
    if (typeof val === 'object' && !Array.isArray(val) && Object.keys(val).length === 0) continue;
    target[key] = val;
  }
};

const handleMessageEvent = (messageData: MessageEventData) => {
  if (messageData.role === 'user') {
    selectedActivityTurn.value = -1;
    activityItems.value = [];
    pendingToolCallIds.value = [];
    plan.value = undefined;
    isLoading.value = true;
    activityPanelRef.value?.show();
  }

  messages.value.push({
    type: messageData.role,
    content: { ...messageData } as MessageContent,
  });

  if (messageData.role === 'user' && messageData.attachments?.length > 0) {
    messages.value.push({
      type: 'attachments',
      content: { ...messageData } as AttachmentsContent,
    });
  }
}

const handleToolEvent = (toolData: ToolEventData) => {
  const lastStep = getLastStep();
  let toolContent: ToolContent = { ...toolData }

  if (typeof toolContent.content === 'string') {
    try {
      toolContent.content = JSON.parse(toolContent.content);
    } catch (e) { /* keep as string */ }
  }

  let associatedWithStep = false;
  if (plan.value) {
    const runningStep = plan.value.steps.find(s => s.status === 'running' || s.status === 'in_progress');
    if (runningStep) {
      if (!runningStep.tools) runningStep.tools = [];
      const existingTool = runningStep.tools.find(t => t.tool_call_id === toolContent.tool_call_id);
      if (existingTool) {
        smartMerge(existingTool, toolContent);
      } else {
        runningStep.tools.push(toolContent as unknown as ToolEventData);
      }
      associatedWithStep = true;
    }
  }

  if (!associatedWithStep && toolContent.name !== 'message') {
    if (!pendingToolCallIds.value.includes(toolContent.tool_call_id)) {
      pendingToolCallIds.value.push(toolContent.tool_call_id);
    }
  }

  if (lastTool.value && lastTool.value.tool_call_id === toolContent.tool_call_id) {
    smartMerge(lastTool.value, toolContent);
  } else {
    if (lastStep?.status === 'running' || lastStep?.status === 'in_progress') {
      lastStep.tools.push(toolContent);
    } else {
      messages.value.push({ type: 'tool', content: toolContent });
    }
    lastTool.value = toolContent;
  }

  if (plan.value) {
    plan.value = { ...plan.value };
  }

  if (toolContent.name !== 'message') {
    lastNoMessageTool.value = toolContent;
    const existingIdx = activityItems.value.findIndex(
      (a) => a.type === 'tool' && a.tool?.tool_call_id === toolContent.tool_call_id
    );
    if (existingIdx >= 0) {
      activityItems.value[existingIdx] = {
        ...activityItems.value[existingIdx],
        tool: { ...toolContent },
      };
    } else {
      activityItems.value.push({
        id: `tool-${toolContent.tool_call_id}`,
        type: 'tool',
        tool: { ...toolContent },
        timestamp: toolContent.timestamp || Date.now(),
      });
    }
    if (realTime.value) {
      activityPanelRef.value?.show();
    }
  }
}

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

const findBestStepForFlush = (): StepEventData | undefined => {
  if (!plan.value?.steps.length) return undefined;
  return plan.value.steps.find(s => s.status === 'running' || s.status === 'in_progress')
    || plan.value.steps.find(s => s.status === 'completed')
    || plan.value.steps[0];
};

const handleStepEvent = (stepData: StepEventData) => {
  const lastStep = getLastStep();

  if (plan.value) {
    const planStep = plan.value.steps.find(s => s.id === stepData.id);
    if (planStep) {
      planStep.status = stepData.status;
      if (pendingToolCallIds.value.length > 0 && (stepData.status === 'running' || stepData.status === 'in_progress' || stepData.status === 'completed')) {
        flushPendingToolsToStep(planStep);
        plan.value = { ...plan.value };
      }
    }
  }

  if (stepData.status === 'running' || stepData.status === 'in_progress') {
    messages.value.push({
      type: 'step',
      content: { ...stepData, tools: [] } as StepContent,
    });
  } else if (stepData.status === 'completed') {
    if (lastStep) lastStep.status = stepData.status;
  } else if (stepData.status === 'failed') {
    isLoading.value = false;
  }
}

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
    if (realTime.value) {
      activityPanelRef.value?.show();
    }
  }
}

const handleDoneEvent = (doneData: DoneEventData) => {
  isLoading.value = false;
  if (plan.value?.steps?.length) {
    for (const step of plan.value.steps) {
      if (step.status !== 'completed' && step.status !== 'failed') {
        step.status = doneData.status === 'failed' ? 'failed' : 'completed';
      }
    }
    plan.value = { ...plan.value };
  }
  if (doneData.status === 'failed' && doneData.error) {
    messages.value.push({
      type: 'assistant',
      content: { content: doneData.error, timestamp: doneData.timestamp } as MessageContent,
    });
  }
  if (doneData.statistics) {
    sessionStatistics.value = doneData.statistics;
    // 将统计信息设置到最后一个 assistant 消息的 content.statistics
    // 这样 ChatMessage 组件会自动显示统计胶囊
    const lastAssistantMsg = [...messages.value].reverse().find(m => m.type === 'assistant');
    if (lastAssistantMsg && lastAssistantMsg.content) {
      (lastAssistantMsg.content as MessageContent).statistics = doneData.statistics;
    }
  }

  if (pendingToolCallIds.value.length > 0) {
    const targetStep = findBestStepForFlush();
    if (targetStep) {
      flushPendingToolsToStep(targetStep);
      if (plan.value) plan.value = { ...plan.value };
    }
  }

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

const handleErrorEvent = (errorData: ErrorEventData) => {
  isLoading.value = false;
  messages.value.push({
    type: 'assistant',
    content: { content: errorData.error, timestamp: errorData.timestamp } as MessageContent,
  });
}

const handleTitleEvent = (titleData: TitleEventData) => {
  title.value = titleData.title;
}

const handlePlanEvent = (planData: PlanEventData) => {
  if (plan.value) {
    for (const newStep of planData.steps) {
      const oldStep = plan.value.steps.find(s => s.id === newStep.id);
      if (oldStep && oldStep.tools) {
        newStep.tools = oldStep.tools;
      }
    }
  }
  plan.value = planData;

  if (pendingToolCallIds.value.length > 0) {
    const targetStep = findBestStepForFlush();
    if (targetStep) {
      flushPendingToolsToStep(targetStep);
      plan.value = { ...plan.value };
    }
  }
}

const handleEvent = (event: AgentSSEEvent) => {
  if (event.event === 'message') {
    handleMessageEvent(event.data as MessageEventData);
  } else if (event.event === 'tool') {
    handleToolEvent(event.data as ToolEventData);
  } else if (event.event === 'step') {
    handleStepEvent(event.data as StepEventData);
  } else if (event.event === 'thinking') {
    handleThinkingEvent(event.data as ThinkingEventData);
  } else if (event.event === 'done') {
    handleDoneEvent(event.data as DoneEventData);
  } else if (event.event === 'wait') {
    // noop
  } else if (event.event === 'error') {
    handleErrorEvent(event.data as ErrorEventData);
  } else if (event.event === 'title') {
    handleTitleEvent(event.data as TitleEventData);
  } else if (event.event === 'plan') {
    handlePlanEvent(event.data as PlanEventData);
  }
  lastEventId.value = event.data.event_id;
}

const REPLAY_DELAYS: Record<string, number> = {
  message: 80,
  tool: 40,
  step: 30,
  thinking: 30,
  plan: 50,
  error: 50,
  title: 0,
  done: 0,
  wait: 0,
};

const resetState = () => {
  Object.assign(state, createInitialState());
};

const fetchAndCacheEvents = async (): Promise<AgentSSEEvent[]> => {
  if (!sessionId.value) return [];
  const session = await agentApi.getSharedSession(sessionId.value);
  if (session.mode) {
    mode.value = session.mode;
  }
  cachedEvents = session.events || [];
  return cachedEvents;
}

// 立即加载所有事件（用于初始加载，无延迟）
const loadEventsImmediately = (events: AgentSSEEvent[]) => {
  isLoading.value = true;
  realTime.value = true;
  follow.value = true;
  selectedActivityTurn.value = -1;

  for (const event of events) {
    handleEvent(event);
  }

  isLoading.value = false;
  replayCompleted.value = true;
}

// 带延迟的回放（用于用户点击回放按钮）
const replayEvents = async (events: AgentSSEEvent[]) => {
  replayActive.value = true;
  replayCompleted.value = false;
  isLoading.value = true;
  realTime.value = true;
  follow.value = true;
  selectedActivityTurn.value = -1;

  for (const event of events) {
    if (jumpToEnd.value) {
      handleEvent(event);
      continue;
    }

    const delay = REPLAY_DELAYS[event.event] ?? 100;
    if (delay > 0) {
      await new Promise(resolve => setTimeout(resolve, delay));
    }
    handleEvent(event);
  }

  isLoading.value = false;
  replayActive.value = false;
  replayCompleted.value = true;
}

const startReplay = async () => {
  hideFilePanel();
  toolPanel.value?.hideToolPanel();

  const savedSessionId = sessionId.value;
  resetState();
  sessionId.value = savedSessionId;

  const events = cachedEvents.length > 0 ? cachedEvents : await fetchAndCacheEvents();
  await replayEvents(events);
}

const skipToEnd = () => {
  jumpToEnd.value = true;
}

onMounted(async () => {
  hideFilePanel();
  const routeParams = router.currentRoute.value.params;
  if (routeParams.sessionId) {
    sessionId.value = String(routeParams.sessionId) as string;
    const events = await fetchAndCacheEvents();
    // 初始加载时立即显示所有事件，不使用延迟
    loadEventsImmediately(events);
  }
});

const handleToolClick = (tool: ToolContent) => {
  realTime.value = false;
  if (sessionId.value) {
    toolPanel.value?.showToolPanel(tool, false);
  }
}

const jumpToRealTime = () => {
  realTime.value = true;
  if (lastNoMessageTool.value) {
    toolPanel.value?.showToolPanel(lastNoMessageTool.value, false);
  }
}

const handleFollow = () => {
  follow.value = true;
  simpleBarRef.value?.scrollToBottom();
}

const handleScroll = (_: Event) => {
  follow.value = simpleBarRef.value?.isScrolledToBottom() ?? false;
}

const handleFileListShow = () => {
  shared.value = true;
  showFileListPanel()
}

const handleCopyLink = async () => {
  if (!sessionId.value) return;
  const shareUrl = `${window.location.origin}/share/${sessionId.value}`;

  try {
    const success = await copyToClipboard(shareUrl);
    if (success) {
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
</style>
