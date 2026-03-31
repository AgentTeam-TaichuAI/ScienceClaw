<template>
  <div class="[&:not(:empty)]:pb-2 bg-[var(--background-gray-main)] rounded-[22px_22px_0px_0px]">
    <!-- ═══ 展开视图 ═══ -->
    <div v-if="isExpanded"
      class="border border-black/8 dark:border-[var(--border-main)] bg-[var(--background-menu-white)] rounded-[16px] sm:rounded-[12px] shadow-[0px_0px_1px_0px_rgba(0,_0,_0,_0.05),_0px_8px_32px_0px_rgba(0,_0,_0,_0.04)] z-99 flex flex-col">
      <!-- 标题栏 -->
      <div class="flex items-center justify-between px-4 pt-3 pb-2">
        <div class="flex items-center gap-2">
          <span class="text-[13px] font-semibold text-[var(--text-primary)]">To-dos</span>
          <span class="text-[11px] text-[var(--text-tertiary)] bg-[var(--fill-tsp-gray-main)] px-1.5 py-0.5 rounded-md font-medium">
            {{ planProgress }}
          </span>
        </div>
        <div class="flex items-center gap-1.5">
          <!-- 进度条 -->
          <div class="w-16 h-1 bg-[var(--border-light)] rounded-full overflow-hidden">
            <div class="h-full rounded-full transition-all duration-500 ease-out"
              :class="isCompleted ? 'bg-emerald-500' : hasFailed ? 'bg-amber-500' : 'bg-blue-500'"
              :style="{ width: progressPercent + '%' }"></div>
          </div>
          <div @click="togglePanel"
            class="flex h-6 w-6 items-center justify-center cursor-pointer hover:bg-[var(--fill-tsp-gray-main)] rounded-md">
            <ChevronDown class="text-[var(--icon-tertiary)]" :size="14" />
          </div>
        </div>
      </div>

      <!-- 步骤列表 -->
      <div class="max-h-[min(calc(100vh-360px),320px)] overflow-y-auto px-3 pb-3">
        <div v-for="step in plan.steps" :key="step.id"
          class="flex items-start gap-2 py-1.5 px-1.5 rounded-md transition-colors"
          :class="{ 'bg-blue-50/40 dark:bg-blue-950/15': ['running', 'in_progress'].includes(step.status) }">
          <!-- 状态图标 -->
          <div class="flex-shrink-0 w-4 h-4 mt-0.5 flex items-center justify-center">
            <svg v-if="step.status === 'completed'" class="w-4 h-4 text-emerald-500" viewBox="0 0 16 16" fill="currentColor">
              <path fill-rule="evenodd" d="M8 16A8 8 0 108 0a8 8 0 000 16zm3.78-9.72a.75.75 0 00-1.06-1.06L7 8.94 5.28 7.22a.75.75 0 00-1.06 1.06l2.25 2.25a.75.75 0 001.06 0l4.25-4.25z"/>
            </svg>
            <svg v-else-if="step.status === 'failed'" class="w-4 h-4 text-amber-500" viewBox="0 0 16 16" fill="currentColor">
              <path fill-rule="evenodd" d="M8 16A8 8 0 108 0a8 8 0 000 16zM7.25 4.75a.75.75 0 011.5 0v3.5a.75.75 0 01-1.5 0v-3.5zM8 11a1 1 0 100-2 1 1 0 000 2z"/>
            </svg>
            <div v-else-if="['running', 'in_progress'].includes(step.status)" class="w-3.5 h-3.5 border-[1.5px] border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            <div v-else class="w-3.5 h-3.5 rounded-full border-[1.5px] border-[var(--border-main)]"></div>
          </div>
          <!-- 内容 -->
          <div class="flex-1 min-w-0">
            <div class="text-[13px] leading-5"
              :class="{
                'text-[var(--text-primary)]': ['running', 'in_progress'].includes(step.status),
                'text-[var(--text-secondary)]': step.status === 'completed',
                'text-amber-600 dark:text-amber-400': step.status === 'failed',
                'text-[var(--text-tertiary)]': !['running', 'in_progress', 'completed', 'failed'].includes(step.status)
              }">
              {{ step.description }}
            </div>
            <!-- 工具标签 -->
            <div v-if="step.tools && step.tools.length > 0" class="flex flex-wrap gap-1 mt-1">
              <span v-for="tool in step.tools" :key="tool.tool_call_id"
                class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] border"
                :class="tool.status === 'calling'
                  ? 'bg-blue-50 text-blue-600 border-blue-200/50 dark:bg-blue-950/30 dark:text-blue-400 dark:border-blue-800/30'
                  : 'bg-[var(--fill-tsp-gray-main)] text-[var(--text-tertiary)] border-[var(--border-light)]'">
                <span v-if="tool.tool_meta?.icon" class="text-[9px]">{{ tool.tool_meta.icon }}</span>
                <span class="truncate max-w-[120px]">{{ tool.name }}</span>
                <span v-if="tool.duration_ms != null && tool.status === 'called'" class="opacity-60">{{ formatDuration(tool.duration_ms) }}</span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ 折叠视图 ═══ -->
    <div v-if="!isExpanded" @click="togglePanel"
      class="flex flex-row items-center justify-between px-4 py-2 relative clickable border border-black/8 dark:border-[var(--border-main)] bg-[var(--background-menu-white)] rounded-[16px] sm:rounded-[12px] shadow-[0px_0px_1px_0px_rgba(0,_0,_0,_0.05),_0px_8px_32px_0px_rgba(0,_0,_0,_0.04)] z-99">
      <div class="flex items-center gap-2 flex-1 min-w-0">
        <!-- 状态图标 -->
        <svg v-if="isCompleted" class="w-4 h-4 text-emerald-500 flex-shrink-0" viewBox="0 0 16 16" fill="currentColor">
          <path fill-rule="evenodd" d="M8 16A8 8 0 108 0a8 8 0 000 16zm3.78-9.72a.75.75 0 00-1.06-1.06L7 8.94 5.28 7.22a.75.75 0 00-1.06 1.06l2.25 2.25a.75.75 0 001.06 0l4.25-4.25z"/>
        </svg>
        <svg v-else-if="hasFailed" class="w-4 h-4 text-amber-500 flex-shrink-0" viewBox="0 0 16 16" fill="currentColor">
          <path fill-rule="evenodd" d="M8 16A8 8 0 108 0a8 8 0 000 16zM7.25 4.75a.75.75 0 011.5 0v3.5a.75.75 0 01-1.5 0v-3.5zM8 11a1 1 0 100-2 1 1 0 000 2z"/>
        </svg>
        <div v-else-if="isRunning" class="w-3.5 h-3.5 border-[1.5px] border-blue-500 border-t-transparent rounded-full animate-spin flex-shrink-0"></div>
        <div v-else class="w-3.5 h-3.5 rounded-full border-[1.5px] border-[var(--border-main)] flex-shrink-0"></div>
        <!-- 当前步骤文本 -->
        <span class="text-[13px] truncate"
          :class="isCompleted ? 'text-emerald-600 dark:text-emerald-400' : hasFailed ? 'text-amber-600 dark:text-amber-400' : 'text-[var(--text-tertiary)]'">
          {{ currentStep }}
        </span>
      </div>
      <div class="flex items-center gap-2 flex-shrink-0 ml-2">
        <span class="text-[11px] text-[var(--text-tertiary)] font-medium hidden sm:inline">{{ planProgress }}</span>
        <ChevronUp class="text-[var(--icon-tertiary)]" :size="14" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { ChevronUp, ChevronDown } from 'lucide-vue-next';
import type { PlanEventData } from '../types/event';

interface Props {
  plan: PlanEventData;
}

const props = defineProps<Props>();
const { t } = useI18n();
const isExpanded = ref(true);  // 默认展开（Cursor 风格）

const togglePanel = () => { isExpanded.value = !isExpanded.value; };

// 多步骤时自动展开
watch(() => props.plan?.steps?.length, (len) => {
  if (len && len > 1) isExpanded.value = true;
});

const planProgress = computed(() => {
  const done = props.plan?.steps.filter(s => s.status === 'completed').length ?? 0;
  return `${done}/${props.plan?.steps.length ?? 1}`;
});

const progressPercent = computed(() => {
  const total = props.plan?.steps.length ?? 1;
  const done = props.plan?.steps.filter(s => s.status === 'completed').length ?? 0;
  return Math.round((done / total) * 100);
});

const isCompleted = computed(() => props.plan?.steps.every(s => s.status === 'completed') ?? false);
const hasFailed = computed(() => props.plan?.steps.some(s => s.status === 'failed') ?? false);
const isRunning = computed(() => props.plan?.steps.some(s => ['running', 'in_progress'].includes(s.status)) ?? false);

const currentStep = computed(() => {
  for (const s of props.plan?.steps ?? []) {
    if (s.status === 'running' || s.status === 'in_progress' || s.status === 'pending') return s.description;
  }
  if (hasFailed.value) return t('Task Interrupted');
  return t('Task Completed');
});

const formatDuration = (ms: number): string => {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
};
</script>

<style scoped>
.\[\&\:not\(\:empty\)\]\:pb-2:not(:empty) {
  padding-bottom: .5rem;
}
</style>
