<template>
  <div
    ref="panelRef"
    v-if="isVisible"
    :class="{
      'h-full w-full top-0 ltr:right-0 rtl:left-0 z-50 fixed sm:sticky sm:top-0 sm:right-0 sm:h-[100vh] sm:ml-3 sm:py-3 sm:mr-4': isShow,
      'h-full overflow-hidden': !isShow
    }"
    :style="{ width: isShow ? `${panelWidth}px` : '0px', opacity: isShow ? '1' : '0', transition: '0.2s ease-in-out' }"
  >
    <div v-if="isShow" class="h-full flex flex-col bg-white/95 dark:bg-gray-900/95 backdrop-blur-xl border border-gray-200/60 dark:border-gray-700/40 rounded-2xl shadow-lg overflow-hidden">
      <!-- Header -->
      <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800 flex-shrink-0">
        <div class="flex items-center gap-2.5">
          <div v-if="isLoading" class="relative size-4 flex-shrink-0">
            <div class="absolute inset-0 rounded-full border-2 border-blue-200 dark:border-blue-800"></div>
            <div class="absolute inset-0 rounded-full border-2 border-blue-500 border-t-transparent animate-spin"></div>
          </div>
          <div v-else-if="lastTurnHadError" class="size-4 rounded-full bg-amber-400 flex items-center justify-center flex-shrink-0 shadow-sm shadow-amber-400/20">
            <svg class="size-2.5 text-white" viewBox="0 0 16 16" fill="currentColor"><path fill-rule="evenodd" d="M8 16A8 8 0 108 0a8 8 0 000 16zM7.25 4.75a.75.75 0 011.5 0v3.5a.75.75 0 01-1.5 0v-3.5zM8 11a1 1 0 100-2 1 1 0 000 2z"/></svg>
          </div>
          <div v-else class="size-4 rounded-full bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center flex-shrink-0 shadow-sm shadow-emerald-400/20">
            <svg class="size-2.5 text-white" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="2 6.5 5 9.5 10 3"/></svg>
          </div>
          <span class="text-[13px] font-bold" :class="isLoading ? 'text-blue-600 dark:text-blue-400' : lastTurnHadError ? 'text-amber-600 dark:text-amber-400' : 'text-gray-700 dark:text-gray-200'">{{ isLoading ? t('Reasoning') + '...' : (lastTurnHadError ? t('Reasoning failed') : t('Reasoning completed')) }}</span>
        </div>
        <button @click="handleClose" class="flex size-7 items-center justify-center cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors">
          <XIcon :size="14" class="text-gray-400 dark:text-gray-500" />
        </button>
      </div>

      <!-- Content: flex layout keeps all section headers visible -->
      <div class="flex-1 flex flex-col min-h-0 overflow-hidden">

        <!-- ═══ Thoughts Section ═══ -->
        <template v-if="thinkingItems.length > 0">
          <!-- Thoughts header -->
          <div
            @click="thinkingExpanded = !thinkingExpanded"
            class="flex-shrink-0 flex items-center gap-2 cursor-pointer select-none group/sec px-4 py-2.5 border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors"
          >
            <ChevronRightIcon :size="12"
              class="text-gray-400 dark:text-gray-500 transition-transform duration-150 flex-shrink-0"
              :class="{ 'rotate-90': thinkingExpanded }" />
            <Lightbulb :size="13" class="text-amber-400 flex-shrink-0" />
            <span class="text-[12px] font-semibold transition-colors"
              :class="isCurrentlyThinking || thinkingExpanded ? 'text-gray-600 dark:text-gray-300' : 'text-gray-400 dark:text-gray-500 group-hover/sec:text-gray-600 dark:group-hover/sec:text-gray-300'">
              {{ t('Thinking') }}
            </span>
            <div v-if="isCurrentlyThinking" class="flex gap-0.5 ml-0.5">
              <span v-for="d in 3" :key="d"
                class="w-[3px] h-[3px] rounded-full bg-blue-400 animate-bounce-dot"
                :style="{ 'animation-delay': `${(d-1) * 200}ms` }"></span>
            </div>
          </div>
          <!-- Thoughts content -->
          <div v-if="thinkingExpanded" ref="thoughtsContentRef"
            class="overflow-y-auto border-b border-gray-100 dark:border-gray-800 px-4 py-2 min-h-0 section-content-enter" style="flex: 1 1 0%; min-height: 60px;">
            <div class="px-3 py-2.5 text-[12px] leading-[1.7] text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800/50 rounded-xl whitespace-pre-wrap break-words font-mono border border-gray-100 dark:border-gray-700/50">
              {{ aggregatedThinkingContent }}
            </div>
            <div v-if="isCurrentlyThinking" class="flex items-center gap-2 text-[11px] text-blue-500 dark:text-blue-400 py-2 pl-1 mt-1">
              <span class="flex gap-0.5">
                <span class="size-1 rounded-full bg-blue-400 animate-bounce" style="animation-delay: 0ms"></span>
                <span class="size-1 rounded-full bg-blue-400 animate-bounce" style="animation-delay: 150ms"></span>
                <span class="size-1 rounded-full bg-blue-400 animate-bounce" style="animation-delay: 300ms"></span>
              </span>
              {{ t('Thinking') }}...
            </div>
          </div>
        </template>

        <!-- ═══ To-dos Section ═══ -->
        <template v-if="plan && plan.steps.length > 0">
          <div
            @click="todosExpanded = !todosExpanded"
            class="flex-shrink-0 flex items-center gap-2 cursor-pointer select-none group/sec px-4 py-2.5 border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors"
          >
            <ChevronRightIcon :size="12"
              class="text-gray-400 dark:text-gray-500 transition-transform duration-150 flex-shrink-0"
              :class="{ 'rotate-90': todosExpanded }" />
            <ListChecks :size="13" class="text-violet-400 flex-shrink-0" />
            <span class="text-[12px] font-semibold transition-colors"
              :class="todosExpanded ? 'text-gray-600 dark:text-gray-300' : 'text-gray-400 dark:text-gray-500 group-hover/sec:text-gray-600 dark:group-hover/sec:text-gray-300'">
              {{ t('Task Progress') }}
            </span>
            <span class="text-[10px] text-gray-400 dark:text-gray-500 font-bold tabular-nums ml-auto bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded-md">{{ planProgress }}</span>
          </div>
          <div v-if="todosExpanded" class="border-b border-gray-100 dark:border-gray-800 px-4 py-2 overflow-y-auto min-h-0 section-content-enter" style="flex: 0.8 1 0%; min-height: 40px;">
            <div class="w-full h-1 bg-[var(--border-light)] rounded-full overflow-hidden mb-2">
              <div class="h-full rounded-full transition-all duration-500 ease-out"
                :class="planCompleted ? 'bg-emerald-500' : 'bg-blue-500'"
                :style="{ width: planPercent + '%' }"></div>
            </div>
            <div class="flex flex-col gap-1">
              <div v-for="step in plan.steps" :key="step.id"
                @click="toggleStepFilter(step.id)"
                class="flex items-start gap-2 py-1 px-1.5 -mx-1.5 rounded-md cursor-pointer transition-colors select-none"
                :class="{
                  'bg-blue-50 dark:bg-blue-950/30 ring-1 ring-blue-200 dark:ring-blue-800/40': selectedStepId === step.id,
                  'hover:bg-[var(--fill-tsp-gray-main)]': selectedStepId !== step.id
                }"
              >
                <div class="flex-shrink-0 w-4 h-4 mt-0.5 flex items-center justify-center">
                  <svg v-if="step.status === 'completed'" class="w-3.5 h-3.5 text-emerald-500" viewBox="0 0 16 16" fill="currentColor">
                    <path fill-rule="evenodd" d="M8 16A8 8 0 108 0a8 8 0 000 16zm3.78-9.72a.75.75 0 00-1.06-1.06L7 8.94 5.28 7.22a.75.75 0 00-1.06 1.06l2.25 2.25a.75.75 0 001.06 0l4.25-4.25z"/>
                  </svg>
                  <div v-else-if="['running', 'in_progress'].includes(step.status)" class="w-3 h-3 border-[1.5px] border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                  <div v-else class="w-3 h-3 rounded-full border-[1.5px] border-[var(--border-main)]"></div>
                </div>
                <span class="text-[12px] leading-4 flex-1 step-description"
                  :class="{
                    'text-[var(--text-primary)] font-medium': ['running', 'in_progress'].includes(step.status) || selectedStepId === step.id,
                    'text-[var(--text-secondary)]': step.status === 'completed' && selectedStepId !== step.id,
                    'text-[var(--text-tertiary)]': step.status !== 'running' && step.status !== 'completed' && selectedStepId !== step.id
                  }">
                  {{ step.description }}
                </span>
                <span v-if="step.tools?.length" class="flex-shrink-0 text-[10px] font-mono text-[var(--text-tertiary)] mt-0.5">
                  {{ step.tools.length }}
                </span>
              </div>
            </div>
          </div>
        </template>

        <!-- ═══ Tools Section ═══ -->
        <template v-if="hasSkillState">
          <div
            @click="skillsExpanded = !skillsExpanded"
            class="flex-shrink-0 flex items-center gap-2 cursor-pointer select-none group/sec px-4 py-2.5 border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors"
          >
            <ChevronRightIcon :size="12"
              class="text-gray-400 dark:text-gray-500 transition-transform duration-150 flex-shrink-0"
              :class="{ 'rotate-90': skillsExpanded }" />
            <BookOpen :size="13" class="text-sky-400 flex-shrink-0" />
            <span class="text-[12px] font-semibold transition-colors"
              :class="skillsExpanded ? 'text-gray-600 dark:text-gray-300' : 'text-gray-400 dark:text-gray-500 group-hover/sec:text-gray-600 dark:group-hover/sec:text-gray-300'">
              Local Skills
            </span>
            <span class="text-[10px] text-gray-400 dark:text-gray-500 font-bold tabular-nums ml-auto bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded-md">
              {{ skillSummary }}
            </span>
          </div>
          <div v-if="skillsExpanded" class="border-b border-gray-100 dark:border-gray-800 px-4 py-2 section-content-enter">
            <div class="flex flex-col gap-2 text-[12px]">
              <div v-if="props.skillState?.requiredSkills?.length">
                <div class="text-[10px] uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-1">Required</div>
                <div class="flex flex-wrap gap-1">
                  <span v-for="skill in props.skillState.requiredSkills" :key="`required-${skill}`" class="px-2 py-1 rounded-full bg-sky-50 text-sky-700 dark:bg-sky-950/30 dark:text-sky-300 border border-sky-200/60 dark:border-sky-800/40">{{ skill }}</span>
                </div>
              </div>
              <div v-if="props.skillState?.readSkills?.length">
                <div class="text-[10px] uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-1">Read</div>
                <div class="flex flex-wrap gap-1">
                  <span v-for="skill in props.skillState.readSkills" :key="`read-${skill}`" class="px-2 py-1 rounded-full bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300 border border-emerald-200/60 dark:border-emerald-800/40">{{ skill }}</span>
                </div>
              </div>
              <div v-if="props.skillState?.missingRequiredSkills?.length">
                <div class="text-[10px] uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-1">Missing</div>
                <div class="flex flex-wrap gap-1">
                  <span v-for="skill in props.skillState.missingRequiredSkills" :key="`missing-${skill}`" class="px-2 py-1 rounded-full bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-300 border border-amber-200/60 dark:border-amber-800/40">{{ skill }}</span>
                </div>
              </div>
            </div>
          </div>
        </template>

        <template v-if="toolItems.length > 0 || isLoading">
          <!-- Tools header -->
          <div
            @click="toolsExpanded = !toolsExpanded"
            class="flex-shrink-0 flex items-center gap-2 cursor-pointer select-none group/sec px-4 py-2.5 border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors"
          >
            <ChevronRightIcon :size="12"
              class="text-gray-400 dark:text-gray-500 transition-transform duration-150 flex-shrink-0"
              :class="{ 'rotate-90': toolsExpanded }" />
            <WrenchIcon :size="13" class="text-blue-400 flex-shrink-0" />
            <span class="text-[12px] font-semibold transition-colors"
              :class="toolsExpanded ? 'text-gray-600 dark:text-gray-300' : 'text-gray-400 dark:text-gray-500 group-hover/sec:text-gray-600 dark:group-hover/sec:text-gray-300'">
              {{ t('tools') }}
            </span>
            <span v-if="selectedStepId"
              @click.stop="selectedStepId = null"
              class="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 border border-blue-200/60 dark:border-blue-800/40 cursor-pointer hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors ml-1 font-bold">
              {{ visibleToolItems.length }}/{{ toolItems.length }}
              <span class="ml-0.5">&times;</span>
            </span>
            <span v-else-if="toolItems.length > 0" class="text-[10px] text-gray-400 dark:text-gray-500 font-bold tabular-nums ml-auto bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded-md">
              {{ toolItems.length }}
            </span>
          </div>
          <!-- Tools content (independently scrollable, auto-scroll to bottom) -->
          <div v-if="toolsExpanded" ref="toolsContentRef"
            class="min-h-0 overflow-y-auto px-4 py-2 section-content-enter" style="flex: 1.2 1 0%; min-height: 60px;">
            <div class="px-3 py-2 bg-[var(--fill-tsp-gray-main)] rounded-lg">
              <div class="flex flex-col gap-0.5">
                <!-- Empty state when filter yields no results -->
                <div v-if="selectedStepId && visibleToolItems.length === 0"
                  class="text-[11px] text-[var(--text-tertiary)] py-3 text-center">
                  No tools associated with this step
                </div>
                <template v-for="item in visibleToolItems" :key="item.id">
                  <div v-if="item.tool" class="py-0.5">
                    <!-- Tool header (always visible, click to toggle) -->
                    <div
                      @click="toggleToolExpand(item.id)"
                      class="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-[var(--background-menu-white)] transition-colors cursor-pointer border border-transparent group/tool"
                      :class="{ 'bg-[var(--background-menu-white)] border-[var(--border-light)]': expandedToolIds.has(item.id) }"
                    >
                      <ChevronRightIcon :size="10"
                        class="text-[var(--text-tertiary)] transition-transform duration-150 flex-shrink-0"
                        :class="{ 'rotate-90': expandedToolIds.has(item.id) }" />
                      <span v-if="item.tool.tool_meta?.icon" class="flex-shrink-0 text-sm leading-none">{{ item.tool.tool_meta.icon }}</span>
                      <div v-else class="flex-shrink-0 flex items-center justify-center w-4 h-4 text-[var(--text-tertiary)]">
                        <LoadingSpinnerIcon v-if="item.tool.status === 'calling'" class="w-3.5 h-3.5 animate-spin" />
                        <ZapIcon v-else :size="14" />
                      </div>
                      <LoadingSpinnerIcon v-if="item.tool.status === 'calling' && item.tool.tool_meta?.icon" class="w-3 h-3 animate-spin text-blue-500 flex-shrink-0" />
                      <div class="flex items-center gap-1.5 min-w-0 flex-1 text-[11px] font-mono">
                        <span class="text-[var(--text-secondary)] font-semibold flex-shrink-0">{{ item.tool.function || item.tool.name }}</span>
                        <span v-if="getToolArg(item.tool) && !expandedToolIds.has(item.id)" class="text-[var(--text-tertiary)] truncate max-w-[180px]">{{ getToolArg(item.tool) }}</span>
                      </div>
                      <span v-if="item.tool.duration_ms != null && item.tool.status === 'called'"
                        class="flex-shrink-0 text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-600 dark:bg-emerald-950/30 dark:text-emerald-400">
                        {{ formatDuration(item.tool.duration_ms) }}
                      </span>
                    </div>

                    <!-- Expanded detail (input & output) -->
                    <div v-if="expandedToolIds.has(item.id)"
                      class="tool-detail-enter mt-1 ml-4 mr-1 flex flex-col gap-2 px-3 py-2.5 rounded-lg bg-[var(--background-menu-white)] border border-[var(--border-light)]">
                      <!-- Input -->
                      <div v-if="item.tool.args && Object.keys(item.tool.args).length > 0">
                        <div class="text-[10px] text-[var(--text-tertiary)] mb-1 uppercase tracking-wider font-semibold">Input</div>
                        <pre class="text-[11px] leading-[1.5] whitespace-pre-wrap break-words text-[var(--text-secondary)] bg-[var(--fill-tsp-gray-main)] rounded-md px-2.5 py-2 border border-[var(--border-light)] max-h-[200px] overflow-y-auto font-mono">{{ safeStringify(item.tool.args) }}</pre>
                      </div>
                      <!-- Output -->
                      <div v-if="item.tool.content != null">
                        <div class="text-[10px] text-[var(--text-tertiary)] mb-1 uppercase tracking-wider font-semibold">Output</div>
                        <pre class="text-[11px] leading-[1.5] whitespace-pre-wrap break-words text-[var(--text-secondary)] bg-[var(--fill-tsp-gray-main)] rounded-md px-2.5 py-2 border border-[var(--border-light)] max-h-[200px] overflow-y-auto font-mono">{{ safeStringify(item.tool.content) }}</pre>
                      </div>
                      <!-- Loading state -->
                      <div v-if="item.tool.status === 'calling' && !item.tool.content"
                        class="flex items-center gap-2 text-[11px] text-[var(--text-tertiary)] py-2 justify-center">
                        <div class="w-3.5 h-3.5 border-[1.5px] border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                        Running...
                      </div>
                    </div>
                  </div>
                </template>
              </div>
            </div>
            <!-- Processing at bottom -->
            <div v-if="isLoading" class="flex items-center gap-2 text-[11px] text-blue-500 dark:text-blue-400 py-2 pl-1 mt-1">
              <span class="relative flex h-2 w-2">
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                <span class="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
              </span>
              Processing...
            </div>
          </div>
        </template>

        <!-- ═══ Sandbox Preview Section ═══ -->
        <SandboxPreview
          ref="sandboxPreviewRef"
          :mode="activeSandboxMode"
          :isLive="isSandboxLive"
          :history="sandboxHistory"
          @close="activeSandboxMode = 'none'"
        />

      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, nextTick, onMounted, onUnmounted } from 'vue';
import { X as XIcon, ChevronRight as ChevronRightIcon, Zap as ZapIcon, Lightbulb, ListChecks, Wrench as WrenchIcon, BookOpen } from 'lucide-vue-next';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
import LoadingSpinnerIcon from './icons/LoadingSpinnerIcon.vue';
import SandboxPreview from './SandboxPreview.vue';
import type { ToolContent } from '../types/message';
import type { PlanEventData } from '../types/event';
import type { SandboxPreviewMode } from '../utils/sandbox';
import { getPreviewMode } from '../utils/sandbox';
import { useResizeObserver } from '../composables/useResizeObserver';
import { eventBus } from '../utils/eventBus';
import { EVENT_SHOW_FILE_PANEL, EVENT_SHOW_TOOL_PANEL, EVENT_SHOW_ACTIVITY_PANEL } from '../constants/event';

export interface ActivityItem {
  id: string;
  type: 'thinking' | 'tool';
  timestamp: number;
  content?: string;
  tool?: ToolContent;
  collapsed?: boolean;
}

const props = withDefaults(defineProps<{
  items: ActivityItem[];
  plan?: PlanEventData;
  skillState?: {
    requiredSkills: string[];
    readSkills: string[];
    missingRequiredSkills: string[];
  };
  isLoading: boolean;
  lastTurnHadError?: boolean;
}>(), { lastTurnHadError: false });

const emit = defineEmits<{
  (e: 'toolClick', tool: ToolContent): void;
  (e: 'close'): void;
}>();

const panelRef = ref<HTMLElement>();
const thoughtsContentRef = ref<HTMLElement>();
const toolsContentRef = ref<HTMLElement>();
const sandboxPreviewRef = ref<InstanceType<typeof SandboxPreview>>();
const isShow = ref(false);
const visible = ref(true);

const activeSandboxMode = ref<SandboxPreviewMode>('none');
const isSandboxLive = computed(() => {
  if (!props.isLoading) return false;
  return activeSandboxMode.value !== 'none';
});

const { size: parentWidth } = useResizeObserver(panelRef, {
  target: 'parent',
  property: 'width'
});

const panelWidth = computed(() => Math.min(parentWidth.value / 2, 600));

// Section expand/collapse states
const thinkingExpanded = ref(true);
const todosExpanded = ref(true);
const skillsExpanded = ref(true);
const toolsExpanded = ref(true);

// Step filter: when a To-do step is selected, only show its associated tools
const selectedStepId = ref<string | null>(null);

const toggleStepFilter = (stepId: string) => {
  selectedStepId.value = selectedStepId.value === stepId ? null : stepId;
};

const stepToolCallIds = computed(() => {
  if (!selectedStepId.value || !props.plan) return null;
  const step = props.plan.steps.find(s => s.id === selectedStepId.value);
  if (!step?.tools?.length) return new Set<string>();
  return new Set(step.tools.map(t => t.tool_call_id));
});

const visibleToolItems = computed(() => {
  if (!stepToolCallIds.value) return toolItems.value;
  return toolItems.value.filter(
    item => item.tool && stepToolCallIds.value!.has(item.tool.tool_call_id)
  );
});

// Per-tool expand/collapse tracking
const expandedToolIds = reactive(new Set<string>());

const toggleToolExpand = (id: string) => {
  if (expandedToolIds.has(id)) {
    expandedToolIds.delete(id);
  } else {
    expandedToolIds.add(id);
  }
};

const safeStringify = (value: any): string => {
  const seen = new WeakSet<object>();
  try {
    const json = JSON.stringify(value ?? null, (key, v) => {
      if (key === '__proto__') return undefined;
      if (typeof v === 'object' && v !== null) {
        if (seen.has(v)) return '[Circular]';
        seen.add(v);
      }
      return v;
    }, 2);
    if (!json) return '';
    if (json.length > 10000) return json.slice(0, 10000) + '\n...';
    return json;
  } catch (e: any) {
    return String(e);
  }
};

const thinkingItems = computed(() =>
  props.items.filter(i => i.type === 'thinking' && i.content)
);

const toolItems = computed(() =>
  props.items.filter(i => i.type === 'tool')
);

const aggregatedThinkingContent = computed(() =>
  thinkingItems.value.map(i => (i.content || '').trim()).filter(Boolean).join('\n\n').replace(/\n{3,}/g, '\n\n')
);

const isCurrentlyThinking = computed(() => {
  if (!props.isLoading) return false;
  const lastItem = props.items[props.items.length - 1];
  return lastItem?.type === 'thinking';
});

const planProgress = computed(() => {
  const done = props.plan?.steps.filter(s => s.status === 'completed').length ?? 0;
  return `${done}/${props.plan?.steps.length ?? 0}`;
});

const planPercent = computed(() => {
  const total = props.plan?.steps.length ?? 1;
  const done = props.plan?.steps.filter(s => s.status === 'completed').length ?? 0;
  return Math.round((done / total) * 100);
});

const planCompleted = computed(() => props.plan?.steps.every(s => s.status === 'completed') ?? false);
const hasSkillState = computed(() =>
  Boolean(
    props.skillState?.requiredSkills?.length
    || props.skillState?.readSkills?.length
    || props.skillState?.missingRequiredSkills?.length,
  ),
);
const skillSummary = computed(() => {
  const readCount = props.skillState?.readSkills?.length ?? 0;
  const requiredCount = props.skillState?.requiredSkills?.length ?? 0;
  return `${readCount}/${requiredCount}`;
});

const isVisible = computed(() => visible.value);

const getToolArg = (tool: ToolContent): string => {
  if (!tool.args) return '';
  const fn = tool.function || tool.name || '';
  if (fn.includes('search')) return tool.args.query || tool.args.search_query || '';
  if (fn.includes('exec') || fn === 'execute' || fn.startsWith('terminal_')) return tool.args.command || '';
  if (fn.includes('file') || fn === 'read_file' || fn === 'write_file' || fn === 'edit_file') return tool.args.file_path || tool.args.file || tool.args.path || '';
  if (fn.includes('crawl') || fn.startsWith('browser_')) return tool.args.url || '';
  if (fn.startsWith('markitdown_')) return tool.args.file || '';
  const vals = Object.values(tool.args);
  if (vals.length > 0 && typeof vals[0] === 'string') return (vals[0] as string).slice(0, 80);
  return '';
};

const formatDuration = (ms: number): string => {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
};

const handleClose = () => {
  isShow.value = false;
  emit('close');
};

const scrollThoughtsToBottom = () => {
  nextTick(() => {
    if (thoughtsContentRef.value) {
      thoughtsContentRef.value.scrollTop = thoughtsContentRef.value.scrollHeight;
    }
  });
};

const scrollToolsToBottom = () => {
  nextTick(() => {
    if (toolsContentRef.value) {
      toolsContentRef.value.scrollTop = toolsContentRef.value.scrollHeight;
    }
  });
};

watch(aggregatedThinkingContent, scrollThoughtsToBottom);
watch(() => toolItems.value.length, scrollToolsToBottom);
watch(() => props.plan, () => {}, { deep: true });

/**
 * Extract a display-friendly command string from tool args.
 */
function extractCommand(tool: ToolContent): string {
  const args = tool.args;
  if (!args || typeof args !== 'object') return '';
  return args.command || args.code || args.script || args.path || args.file || args.url || args.action || '';
}

/**
 * Extract output text from tool result content.
 */
function extractOutput(tool: ToolContent): string {
  const c = tool.content;
  if (!c) return '';
  if (typeof c === 'string') {
    try {
      const parsed = JSON.parse(c);
      return parsed.stdout || parsed.output || parsed.text || c;
    } catch {
      return c;
    }
  }
  if (typeof c === 'object') {
    return (c as any).stdout || (c as any).output || (c as any).text || JSON.stringify(c);
  }
  return String(c);
}

// Track which tool calls we've already written to terminal
const writtenToolCalls = new Set<string>();

export interface SandboxExecEntry {
  toolName: string;
  command: string;
  output?: string;
  status: string;
}

const sandboxHistory = ref<SandboxExecEntry[]>([]);

function scanSandboxTools() {
  for (const item of props.items) {
    if (item.type !== 'tool' || !item.tool) continue;
    const fn = item.tool.function || item.tool.name || '';
    const isSandboxProxy = !!item.tool.tool_meta?.sandbox;
    const mode = getPreviewMode(fn, isSandboxProxy);
    if (mode === 'none') continue;

    const callId = item.tool.tool_call_id || item.id;

    if (item.tool.status === 'calling' && !writtenToolCalls.has(callId + ':calling')) {
      activeSandboxMode.value = mode;
      writtenToolCalls.add(callId + ':calling');
      sandboxHistory.value.push({ toolName: fn, command: extractCommand(item.tool!), status: 'calling' });
    }

    if (item.tool.status === 'called' && !writtenToolCalls.has(callId + ':called')) {
      activeSandboxMode.value = mode;
      if (!writtenToolCalls.has(callId + ':calling')) {
        writtenToolCalls.add(callId + ':calling');
        sandboxHistory.value.push({ toolName: fn, command: extractCommand(item.tool!), status: 'calling' });
      }
      writtenToolCalls.add(callId + ':called');
      sandboxHistory.value.push({ toolName: fn, command: extractCommand(item.tool!), output: extractOutput(item.tool!), status: 'called' });
    }
  }
}

// Watch both new items AND status changes on existing items
watch(() => props.items.map(i => `${i.id}:${i.tool?.status}`).join(','), scanSandboxTools);

const show = () => {
  eventBus.emit(EVENT_SHOW_ACTIVITY_PANEL);
  visible.value = true;
  isShow.value = true;
};

const hide = () => {
  isShow.value = false;
};

onMounted(() => {
  eventBus.on(EVENT_SHOW_FILE_PANEL, () => {
    visible.value = false;
  });
  eventBus.on(EVENT_SHOW_TOOL_PANEL, () => {
    visible.value = false;
  });
});

onUnmounted(() => {
  eventBus.off(EVENT_SHOW_FILE_PANEL);
  eventBus.off(EVENT_SHOW_TOOL_PANEL);
});

defineExpose({
  show,
  hide,
  isShow,
});
</script>

<style scoped>
.animate-bounce-dot {
  display: inline-block;
  animation: dot-animation 1.5s infinite;
}
@keyframes dot-animation {
  0% { transform: translateY(0); }
  20% { transform: translateY(-3px); }
  40% { transform: translateY(0); }
  100% { transform: translateY(0); }
}

.step-description {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.section-content-enter {
  animation: section-reveal 0.2s ease-out;
}
@keyframes section-reveal {
  from { opacity: 0; transform: translateY(-6px); }
  to { opacity: 1; transform: translateY(0); }
}

.tool-detail-enter {
  animation: tool-detail-slide 0.15s ease-out;
}
@keyframes tool-detail-slide {
  from {
    opacity: 0;
    max-height: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    max-height: 500px;
    transform: translateY(0);
  }
}
</style>
