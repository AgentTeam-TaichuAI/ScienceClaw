<template>
  <div class="bg-[var(--background-gray-main)] sm:bg-[var(--background-menu-white)] sm:rounded-[22px] shadow-[0px_0px_8px_0px_rgba(0,0,0,0.02)] border border-black/8 dark:border-[var(--border-light)] flex h-full w-full">
    <div class="flex-1 min-w-0 p-4 flex flex-col h-full">
      <!-- Header -->
      <div class="flex items-center gap-2 w-full">
        <div class="text-[var(--text-primary)] text-lg font-semibold flex-1">{{ $t('ScienceClaw Computer') }}</div>
        <button
          class="w-7 h-7 relative rounded-md inline-flex items-center justify-center gap-2.5 cursor-pointer hover:bg-[var(--fill-tsp-gray-main)]">
          <Minimize2 class="w-5 h-5 text-[var(--icon-tertiary)]" @click="hide" />
        </button>
      </div>

      <!-- Tool Info Bar -->
      <div v-if="toolInfo" class="flex items-center gap-2 mt-2">
        <div
          class="w-[40px] h-[40px] bg-[var(--fill-tsp-gray-main)] rounded-lg flex items-center justify-center flex-shrink-0">
          <component :is="toolInfo.icon" :size="28" />
        </div>
        <div class="flex-1 flex flex-col gap-1 min-w-0">
          <div class="text-[12px] text-[var(--text-tertiary)] flex items-center gap-2 flex-wrap">
            <span>{{ $t('ScienceClaw is using') }} <span class="text-[var(--text-secondary)]">{{ toolInfo.name }}</span></span>
            <span v-if="isSandboxTool"
              class="px-2 py-[1px] rounded-full text-[11px] border border-[var(--border-light)] text-[var(--text-tertiary)] bg-[var(--fill-tsp-gray-main)]">
              Sandbox
            </span>
            <!-- Status: Running / Duration -->
            <span v-if="toolContent.status === 'calling'"
              class="px-2 py-[1px] rounded-full text-[11px] border border-[var(--border-light)] text-[var(--text-tertiary)] bg-[var(--fill-tsp-gray-main)]">
              Running
            </span>
            <span v-else-if="toolContent.duration_ms != null"
              class="px-2 py-[1px] rounded-full text-[11px] border border-emerald-200/60 text-emerald-600 bg-emerald-50/60 dark:border-emerald-800/40 dark:text-emerald-400 dark:bg-emerald-950/20">
              {{ formatDuration(toolContent.duration_ms) }}
            </span>
          </div>
          <div :title="`${toolInfo.function} ${toolInfo.functionArg}`"
            class="max-w-[100%] w-[max-content] truncate text-[13px] rounded-full inline-flex items-center px-[10px] py-[3px] border border-[var(--border-light)] bg-[var(--fill-tsp-gray-main)] text-[var(--text-secondary)]">
            {{ toolInfo.function }}<span v-if="toolInfo.functionArg"
              class="flex-1 min-w-0 px-1 ml-1 text-[12px] font-mono max-w-full text-ellipsis overflow-hidden whitespace-nowrap text-[var(--text-tertiary)]"><code>{{ toolInfo.functionArg }}</code></span>
          </div>
        </div>
      </div>

      <!-- Tool View Area -->
      <div
        class="flex flex-col rounded-[12px] overflow-hidden bg-[var(--background-gray-main)] border border-[var(--border-dark)] dark:border-black/30 shadow-[0px_4px_32px_0px_rgba(0,0,0,0.04)] flex-1 min-h-0 mt-[16px]">
        
        <!-- Loading bar -->
        <div v-if="toolContent.status === 'calling'" class="h-0.5 w-full bg-[var(--border-light)] overflow-hidden flex-shrink-0">
          <div class="h-full bg-gradient-to-r from-blue-500 to-indigo-500 animate-progress-indeterminate"></div>
        </div>

        <!-- 有专用视图组件 → 渲染组件 -->
        <component v-if="toolInfo?.view" :is="toolInfo.view" :live="live" :sessionId="sessionId"
          :toolContent="toolContent" :isShare="isShare" />
        
        <!-- 无专用视图（自定义工具）→ 通用视图 -->
        <div v-else class="flex-1 min-h-0 overflow-y-auto">
          <div class="h-[36px] flex items-center px-3 w-full bg-[var(--background-gray-main)] border-b border-[var(--border-main)] rounded-t-[12px] shadow-[inset_0px_1px_0px_0px_#FFFFFF] dark:shadow-[inset_0px_1px_0px_0px_#FFFFFF30]">
            <div class="flex-1 flex items-center justify-center">
              <div class="max-w-[250px] truncate text-[var(--text-tertiary)] text-sm font-medium text-center">
                {{ toolInfo?.name || toolContent.function }}
              </div>
            </div>
          </div>
          <div class="px-4 py-3 flex flex-col gap-3">
            <!-- 参数 -->
            <div v-if="toolContent.args && Object.keys(toolContent.args).length > 0">
              <div class="text-[11px] text-[var(--text-tertiary)] mb-1.5 uppercase tracking-wider font-medium">Input</div>
              <pre class="text-[12px] leading-relaxed whitespace-pre-wrap break-words text-[var(--text-secondary)] bg-[var(--fill-tsp-gray-main)] rounded-lg px-3 py-2 border border-[var(--border-light)]">{{ argsJson }}</pre>
            </div>
            <!-- 结果 -->
            <div v-if="toolContent.content != null">
              <div class="text-[11px] text-[var(--text-tertiary)] mb-1.5 uppercase tracking-wider font-medium">Output</div>
              <pre class="text-[12px] leading-relaxed whitespace-pre-wrap break-words text-[var(--text-secondary)] bg-[var(--fill-tsp-gray-main)] rounded-lg px-3 py-2 border border-[var(--border-light)] max-h-[400px] overflow-y-auto">{{ contentJson }}</pre>
            </div>
            <!-- 空状态 -->
            <div v-if="toolContent.status === 'calling' && !toolContent.content" class="text-sm text-[var(--text-tertiary)] py-8 text-center flex flex-col items-center gap-2">
              <div class="w-5 h-5 border-2 border-[var(--border-light)] border-t-[var(--text-tertiary)] rounded-full animate-spin"></div>
              {{ $t('Running') }}...
            </div>
          </div>
        </div>

        <!-- Jump to live -->
        <div class="mt-auto flex w-full items-center gap-2 px-4 h-[44px] relative" v-if="!realTime">
          <button
            class="h-10 px-3 border border-[var(--border-main)] flex items-center gap-1 bg-[var(--background-white-main)] hover:bg-[var(--background-gray-main)] shadow-[0px_5px_16px_0px_var(--shadow-S),0px_0px_1.25px_0px_var(--shadow-S)] rounded-full cursor-pointer absolute left-[50%] translate-x-[-50%]"
            style="bottom: calc(100% + 10px);" @click="jumpToRealTime">
            <PlayIcon :size="16" />
            <span class="text-[var(--text-primary)] text-sm font-medium">{{ $t('Jump to live') }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, toRef } from 'vue';
import { Minimize2, PlayIcon } from 'lucide-vue-next';
import type { ToolContent } from '@/types/message';
import { useToolInfo } from '@/composables/useTool';

const props = defineProps<{
  sessionId?: string;
  realTime: boolean;
  toolContent: ToolContent;
  live: boolean;
  isShare: boolean;
}>();

const { toolInfo } = useToolInfo(toRef(props, 'toolContent'));

const isSandboxTool = computed(() => {
  const n = props.toolContent?.name || '';
  const f = props.toolContent?.function || '';
  const meta = props.toolContent?.tool_meta;
  return ['shell', 'file', 'browser', 'execute', 'sandbox_exec'].includes(n)
    || f.startsWith('sandbox_')
    || f.startsWith('terminal_')
    || f.startsWith('file_')
    || f.startsWith('browser_')
    || f.startsWith('markitdown_')
    || meta?.sandbox === true;
});

const formatDuration = (ms: number): string => {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const mins = Math.floor(ms / 60000);
  const secs = ((ms % 60000) / 1000).toFixed(0);
  return `${mins}m ${secs}s`;
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
    if (json.length > 20000) return json.slice(0, 20000) + '\n...';
    return json;
  } catch (e: any) {
    return String(e);
  }
};

const argsJson = computed(() => safeStringify(props.toolContent?.args));
const contentJson = computed(() => safeStringify(props.toolContent?.content));

const emit = defineEmits<{
  (e: 'jumpToRealTime'): void,
  (e: 'hide'): void
}>();

const hide = () => emit('hide');
const jumpToRealTime = () => emit('jumpToRealTime');
</script>

<style scoped>
@keyframes progress-indeterminate {
  0% { transform: translateX(-100%); width: 40%; }
  50% { transform: translateX(60%); width: 60%; }
  100% { transform: translateX(200%); width: 40%; }
}
.animate-progress-indeterminate {
  animation: progress-indeterminate 1.5s ease-in-out infinite;
}
</style>
