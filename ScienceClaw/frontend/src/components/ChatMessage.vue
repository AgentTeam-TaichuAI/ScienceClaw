<template>
  <div v-if="message.type === 'user'" class="msg-enter-right flex w-full flex-col items-end justify-end gap-1 group mt-4">
    <div class="flex items-end mb-0.5">
      <div class="transition-opacity duration-200 text-[11px] text-[var(--text-tertiary)] opacity-40 group-hover:opacity-100 tabular-nums">
        {{ relativeTime(message.content.timestamp) }}
      </div>
    </div>
    <div class="flex max-w-[85%] relative flex-col gap-2 items-end">
      <div
        class="relative flex flex-col items-center rounded-2xl overflow-hidden bg-gradient-to-br from-blue-500 to-indigo-600 text-white p-3.5 ltr:rounded-br-sm rtl:rounded-bl-sm shadow-lg shadow-blue-500/15">
        <template v-for="(part, index) in parseContent(messageContent.content)" :key="index">
          <div
            v-if="part.type === 'html'"
            v-html="part.content"
            class="message-html-content message-html-content-user w-full text-white/95"
          ></div>
          <molecule-viewer v-else-if="part.type === 'molecule'" :src="part.src || ''" class="w-full my-2" />
          <image-viewer v-else-if="part.type === 'image'" :src="part.src || ''" :alt="part.alt" class="w-full my-2" />
          <html-viewer v-else-if="part.type === 'html-file'" :src="part.src || ''" class="w-full my-2" />
          <suggested-questions v-else-if="part.type === 'questions'" :questions="part.questions || []" @click="emit('suggestionClick', $event)" />
        </template>
      </div>
      <div v-if="messageContent.content" class="msg-user-inline-actions">
        <button
          class="msg-user-copy-pill"
          :class="{ 'msg-user-copy-pill--copied': isCopied }"
          @click="copyMessage"
          :title="isCopied ? t('Message Copied') : t('Copy Message')"
          :aria-label="isCopied ? t('Message Copied') : t('Copy Message')"
        >
          <CheckIcon v-if="isCopied" class="w-3.5 h-3.5" />
          <CopyIcon v-else class="w-3.5 h-3.5" />
          <span>{{ isCopied ? t('Copied') : t('Copy') }}</span>
        </button>
      </div>
    </div>
  </div>
  <div v-else-if="message.type === 'assistant'" class="msg-enter-left flex flex-col gap-2 w-full group mt-3">
    <!-- Header: avatar + name + time -->
    <div class="flex items-center justify-between h-7">
      <div class="flex items-center gap-2">
        <div class="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 via-red-500 to-amber-500 p-[3px] shadow-sm">
          <div class="w-full h-full rounded-[5px] bg-white dark:bg-[#1e1e1e] flex items-center justify-center overflow-hidden">
            <RobotAvatar class="w-full h-full" :interactive="false" />
          </div>
        </div>
        <span class="font-sans font-bold text-xs bg-clip-text text-transparent bg-gradient-to-r from-blue-500 via-red-500 to-amber-500">{{ botName }}</span>
      </div>
      <div class="transition-opacity duration-200 text-[11px] text-[var(--text-tertiary)] opacity-40 group-hover:opacity-100 tabular-nums">
        {{ relativeTime(message.content.timestamp) }}
      </div>
    </div>
    <!-- Answer card -->
    <div class="relative rounded-2xl bg-white dark:bg-[#1e1e1e] border border-gray-100 dark:border-gray-800 shadow-sm overflow-hidden">
      <div class="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-blue-500 via-red-400 to-amber-400"></div>
      <div
        ref="markdownRef"
        class="p-4 markdown-content text-[15px] text-[var(--text-primary)] leading-relaxed"
        @click="handleMarkdownClick"
      >
        <template v-for="(part, index) in parseContent(messageContent.content)" :key="index">
          <div v-if="part.type === 'html'" v-html="part.content" class="message-html-content"></div>
          <molecule-viewer v-else-if="part.type === 'molecule'" :src="part.src || ''" class="w-full my-2" />
          <image-viewer v-else-if="part.type === 'image'" :src="part.src || ''" :alt="part.alt" class="w-full my-2" />
          <html-viewer v-else-if="part.type === 'html-file'" :src="part.src || ''" class="w-full my-2" />
          <suggested-questions v-else-if="part.type === 'questions'" :questions="part.questions || []" @click="emit('suggestionClick', $event)" />
        </template>
      </div>
    </div>

    <!-- Footer Bar - 操作按钮 + 统计信息 -->
    <div class="msg-footer-bar" v-if="!(isLast && isLoading)">
      <!-- 操作按钮组 - 圆角胶囊风格 -->
      <div class="msg-actions-capsule">
        <button
          class="msg-action-btn"
          :class="{ 'msg-action-btn--liked': feedback === 'like' }"
          @click="toggleFeedback('like')"
          :title="feedback === 'like' ? '取消' : '有帮助'"
        >
          <ThumbsUpIcon class="w-4 h-4" :class="{ 'fill-current': feedback === 'like' }" />
        </button>
        <button
          class="msg-action-btn"
          :class="{ 'msg-action-btn--disliked': feedback === 'dislike' }"
          @click="toggleFeedback('dislike')"
          :title="feedback === 'dislike' ? '取消' : '无帮助'"
        >
          <ThumbsDownIcon class="w-4 h-4" :class="{ 'fill-current': feedback === 'dislike' }" />
        </button>
        <div class="msg-action-divider"></div>
        <button
          class="msg-action-btn"
          :class="{ 'msg-action-btn--copied': isCopied }"
          @click="copyMessage"
          :title="isCopied ? '已复制' : '复制'"
        >
          <CheckIcon v-if="isCopied" class="w-4 h-4" />
          <CopyIcon v-else class="w-4 h-4" />
        </button>
        <button
          class="msg-action-btn"
          @click="handleConvertToPdf"
          title="转成PDF"
        >
          <PdfIcon :size="16" />
        </button>
        <template v-if="roundFiles.length > 0">
          <div class="msg-action-divider"></div>
          <button
            class="msg-action-btn msg-action-btn--files"
            @click="showFileListPanel()"
            :title="`查看本轮对话文件 (${roundFiles.length})`"
          >
            <FolderOpen class="w-4 h-4" />
            <span class="text-[11px] font-medium ml-0.5 tabular-nums">{{ roundFiles.length }}</span>
          </button>
        </template>
      </div>

      <!-- 统计信息组 - 统一胶囊风格 -->
      <div v-if="messageContent.statistics && (messageContent.statistics.total_duration_ms || messageContent.statistics.tool_call_count || messageContent.statistics.input_tokens || messageContent.statistics.output_tokens)" class="msg-stats-capsule">
        <!-- Duration -->
        <span v-if="messageContent.statistics?.total_duration_ms" class="msg-stat-tag msg-stat-tag--time msg-stat-with-tooltip" :data-tooltip="`耗时: ${formatDuration(messageContent.statistics.total_duration_ms)}`">
          <ClockIcon class="w-3.5 h-3.5" />
          <span class="tabular-nums">{{ formatDuration(messageContent.statistics.total_duration_ms) }}</span>
        </span>
        <!-- Divider after duration (if any item follows) -->
        <div v-if="messageContent.statistics?.total_duration_ms && (messageContent.statistics?.tool_call_count || messageContent.statistics?.input_tokens || messageContent.statistics?.output_tokens)" class="msg-stat-divider"></div>
        <!-- Tool calls -->
        <span v-if="messageContent.statistics?.tool_call_count" class="msg-stat-tag msg-stat-tag--tools msg-stat-with-tooltip" :data-tooltip="`工具调用次数: ${messageContent.statistics.tool_call_count}次`">
          <WrenchIcon class="w-3.5 h-3.5" />
          <span class="tabular-nums">{{ messageContent.statistics.tool_call_count }}次</span>
        </span>
        <!-- Divider after tool_call (if tokens follow) -->
        <div v-if="messageContent.statistics?.tool_call_count && (messageContent.statistics?.input_tokens || messageContent.statistics?.output_tokens)" class="msg-stat-divider"></div>
        <!-- Tokens: Input ↓ / Output ↑ -->
        <span v-if="messageContent.statistics?.input_tokens || messageContent.statistics?.output_tokens" class="msg-stat-tag msg-stat-tag--tokens msg-stat-with-tooltip" :data-tooltip="`输入Token: ${messageContent.statistics.input_tokens || 0} | 输出Token: ${messageContent.statistics.output_tokens || 0}`">
          <ArrowDownIcon class="w-3.5 h-3.5 opacity-70" />
          <span class="tabular-nums">{{ formatTokenCount(messageContent.statistics.input_tokens || 0) }}</span>
          <span class="opacity-40 mx-0.5">·</span>
          <ArrowUpIcon class="w-3.5 h-3.5 opacity-70" />
          <span class="tabular-nums">{{ formatTokenCount(messageContent.statistics.output_tokens || 0) }}</span>
        </span>
      </div>
    </div>
  </div>
  <div v-else-if="message.type === 'tool'" class="hidden"></div>
  <div v-else-if="message.type === 'step'" class="hidden"></div>
  <AttachmentsMessage v-else-if="message.type === 'attachments'" :content="attachmentsContent"/>

  <!-- Markdown 增强功能组件 -->
  <MarkdownEnhancements ref="markdownEnhancementsRef" />

</template>

<script setup lang="ts">
import { Message, MessageContent, AttachmentsContent, ToolContent } from '../types/message';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import hljs from 'highlight.js';
import katex from 'katex';
import mermaid from 'mermaid';
import { CheckIcon, ThumbsUpIcon, ThumbsDownIcon, CopyIcon, ClockIcon, WrenchIcon, ArrowDownIcon, ArrowUpIcon, FolderOpen } from 'lucide-vue-next';
import PdfIcon from './icons/PdfIcon.vue';
import { computed, ref, onMounted, onUnmounted, nextTick, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRelativeTime } from '../composables/useTime';
import AttachmentsMessage from './AttachmentsMessage.vue';
import ImageViewer from './ImageViewer.vue';
import HtmlViewer from './HtmlViewer.vue';
import MoleculeViewer from './MoleculeViewer.vue';
import SuggestedQuestions from './SuggestedQuestions.vue';
import { transformSrc, domPurifyConfig } from '../utils/content';
import { formatMarkdown } from '../utils/markdownFormatter';
import MarkdownEnhancements from './MarkdownEnhancements.vue';
import { useFilePanel } from '../composables/useFilePanel';
import { copyToClipboard } from '../utils/dom';
import { showErrorToast, showSuccessToast } from '../utils/toast';

import RobotAvatar from './icons/RobotAvatar.vue';

// Markdown 增强组件引用
const markdownEnhancementsRef = ref<InstanceType<typeof MarkdownEnhancements> | null>(null);
const markdownRef = ref<HTMLElement | null>(null);

// Mermaid 是否已初始化
let mermaidInitialized = false;
// Mermaid 图表缓存（避免重复渲染）
const mermaidCache = new Map<string, string>();
let mermaidCounter = 0;

/**
 * 初始化 Mermaid（延迟初始化，只在需要时执行）
 */
function initMermaid() {
  if (mermaidInitialized) {
    console.log('[Mermaid] Already initialized');
    return;
  }

  console.log('[Mermaid] Initializing...');
  try {
    mermaid.initialize({
      startOnLoad: false,
      theme: 'dark',
      securityLevel: 'loose',
      fontFamily: 'inherit',
      flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
        curve: 'basis'
      },
      sequence: {
        useMaxWidth: true,
        diagramMarginX: 10,
        diagramMarginY: 10
      },
      gantt: {
        useMaxWidth: true
      }
    });
    mermaidInitialized = true;
    console.log('[Mermaid] Initialized successfully');
  } catch (e) {
    console.error('[Mermaid] Initialization failed:', e);
  }
}

/**
 * 渲染 KaTeX 数学公式
 */
function renderKaTeX(formula: string, displayMode: boolean = false): string {
  try {
    return katex.renderToString(formula, {
      displayMode,
      throwOnError: false,
      output: 'html',
      strict: false,
      trust: true
    });
  } catch (e) {
    console.warn('KaTeX render error:', e);
    // 返回原始公式作为后备
    return displayMode
      ? `<div class="katex-error">$$${formula}$$</div>`
      : `<span class="katex-error">$${formula}$</span>`;
  }
}

/**
 * 预处理文本：将数学公式转换为占位符
 */
function preprocessMath(text: string): { text: string; mathBlocks: Map<string, string> } {
  const mathBlocks = new Map<string, string>();
  let result = text;

  try {
    // 处理块级公式 $$...$$
    // 只匹配多行或包含数学符号的内容
    result = result.replace(/\$\$([\s\S]+?)\$\$/g, (_, formula) => {
      const trimmed = formula.trim();
      // 检查是否像数学公式
      const hasMathChars = /[\^\\\_\/\+\-\=\<\>\(\)\[\]\{\}]/.test(trimmed);
      const hasGreekLetters = /alpha|beta|gamma|delta|epsilon|theta|lambda|mu|pi|sigma|omega/i.test(trimmed);

      if (!hasMathChars && !hasGreekLetters && trimmed.length < 3) {
        // 不像数学公式，保留原样
        return `$$${formula}$$`;
      }

      const id = `MATH_BLOCK_${mermaidCounter++}`;
      const rendered = renderKaTeX(trimmed, true);
      mathBlocks.set(id, `<div class="katex-display">${rendered}</div>`);
      console.log('[KaTeX] Block formula:', trimmed.substring(0, 50));
      return id;
    });

    // 处理行内公式 $...$
    // 严格匹配：必须是合理的数学表达式
    result = result.replace(/\$([^\$\n]+?)\$/g, (fullMatch, formula) => {
      const trimmed = formula.trim();

      // 排除条件：
      // 1. 内容为空
      // 2. 只包含数字（货币符号如 $100）
      // 3. 包含 Markdown 语法字符
      // 4. 长度太短且不含数学符号
      if (!trimmed || /^\d+(\.\d+)?$/.test(trimmed)) {
        return fullMatch; // 货币符号，保留原样
      }
      if (trimmed.includes('**') || trimmed.includes('__') || trimmed.includes('##')) {
        return fullMatch; // Markdown 语法，保留原样
      }
      if (trimmed.length < 2 && !/[\^\\\_]/.test(trimmed)) {
        return fullMatch; // 太短且不是数学符号
      }

      // 检查是否像数学公式
      const hasMathChars = /[\^\\\_\/\+\-\=\<\>\(\)\[\]\{\}]/.test(trimmed);
      const hasGreekLetters = /alpha|beta|gamma|delta|epsilon|theta|lambda|mu|pi|sigma|omega|infty|frac|sqrt/i.test(trimmed);
      const hasSubscript = /[a-zA-Z]_[a-zA-Z0-9]/.test(trimmed);

      if (!hasMathChars && !hasGreekLetters && !hasSubscript) {
        // 不像数学公式，保留原样
        return fullMatch;
      }

      const id = `MATH_INLINE_${mermaidCounter++}`;
      try {
        const rendered = renderKaTeX(trimmed, false);
        mathBlocks.set(id, `<span class="katex-inline">${rendered}</span>`);
        console.log('[KaTeX] Inline formula:', trimmed.substring(0, 30));
        return id;
      } catch (e) {
        console.warn('[KaTeX] Failed to render:', trimmed);
        return fullMatch; // 渲染失败，保留原样
      }
    });

    if (mathBlocks.size > 0) {
      console.log('[KaTeX] Preprocessed', mathBlocks.size, 'formulas');
    }
  } catch (e) {
    console.error('[KaTeX] Preprocess error:', e);
    // 返回原始文本
    return { text: text, mathBlocks: new Map() };
  }

  return { text: result, mathBlocks };
}

/**
 * 后处理文本：将占位符替换回渲染后的公式
 */
function postprocessMath(text: string, mathBlocks: Map<string, string>): string {
  let result = text;
  mathBlocks.forEach((html, id) => {
    result = result.replace(id, html);
  });
  return result;
}

// 配置 marked
const renderer = new marked.Renderer();

// 自定义代码块渲染 - 添加语言标签、行号、折叠和复制按钮
// marked.js v15+ 使用 token 对象，兼容新旧 API
renderer.code = function(token: { text: string; lang?: string } | string, language?: string) {
  // 兼容新旧 API：v15+ 传入 token 对象，旧版本传入 (code, language) 字符串
  let code: string;
  let lang: string;

  try {
    if (typeof token === 'object' && token !== null) {
      // marked.js v15+ API - token 对象
      const tokenObj = token as any;
      // 确保获取有效的代码内容
      code = tokenObj.text ?? tokenObj.raw ?? '';
      // 尝试多个可能的属性名
      lang = tokenObj.lang || tokenObj.language || 'plaintext';
    } else if (typeof token === 'string') {
      // 旧版 API - 字符串参数
      code = token;
      lang = language || 'plaintext';
    } else {
      // 未知类型，返回空内容
      code = '';
      lang = 'plaintext';
    }

    // 确保 code 是有效的字符串
    if (code === null || code === undefined) {
      code = '';
    }
    code = String(code);
  } catch (e) {
    console.error('[Markdown] Code block render error:', e);
    code = '';
    lang = 'plaintext';
  }

  // 特殊处理 Mermaid 图表
  if (lang === 'mermaid') {
    const id = `mermaid-${mermaidCounter++}`;
    // 返回占位符，稍后异步渲染
    return `<div class="mermaid-wrapper" data-mermaid-id="${id}" data-mermaid-code="${encodeURIComponent(code)}">
      <div class="mermaid-loading">
        <svg class="animate-spin h-5 w-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span>正在渲染图表...</span>
      </div>
      <div class="mermaid-content" id="${id}"></div>
    </div>`;
  }

  let highlightedCode = code;

  // 代码高亮
  if (lang && hljs.getLanguage(lang)) {
    try {
      highlightedCode = hljs.highlight(code, { language: lang }).value;
    } catch {
      // 忽略错误
    }
  } else {
    highlightedCode = hljs.highlightAuto(code).value;
  }

  // 转义 HTML 属性中的特殊字符
  const escapedCode = code
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
    .replace(/`/g, '&#96;');

  // 生成行号
  const lines = highlightedCode.split('\n');
  const lineCount = lines.length;
  const lineNumbers = Array.from({ length: lineCount }, (_, i) => i + 1).join('\n');

  // 判断是否需要折叠（超过 20 行）
  const shouldCollapse = lineCount > 20;
  const collapseClass = shouldCollapse ? 'code-block-collapsed' : '';

  return `<div class="code-block-wrapper ${collapseClass}" data-lines="${lineCount}">
    <div class="code-block-header">
      <span class="code-block-lang">${lang}</span>
      <span class="code-block-line-count">${lineCount} 行</span>
      <div class="code-block-actions">
        ${shouldCollapse ? `<button class="code-block-expand" onclick="this.closest('.code-block-wrapper').classList.toggle('code-block-collapsed')">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="7 13 12 18 17 13"></polyline><polyline points="7 6 12 11 17 6"></polyline></svg>
          <span class="expand-text">展开</span>
        </button>` : ''}
        <button class="code-block-fullscreen" title="全屏查看">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 3 21 3 21 9"></polyline><polyline points="9 21 3 21 3 15"></polyline><line x1="21" y1="3" x2="14" y2="10"></line><line x1="3" y1="21" x2="10" y2="14"></line></svg>
          <span>全屏</span>
        </button>
        <button class="code-block-copy" onclick="navigator.clipboard.writeText(decodeURIComponent(\`${encodeURIComponent(escapedCode)}\`)).then(() => { const el = this.querySelector('span'); el.textContent = '已复制!'; setTimeout(() => el.textContent = '复制', 2000); }).catch(() => this.querySelector('span').textContent = '失败')">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
          <span>复制</span>
        </button>
      </div>
    </div>
    <div class="code-block-content">
      <div class="code-block-lines"><pre>${lineNumbers}</pre></div>
      <pre class="code-block-pre"><code class="hljs language-${lang}">${highlightedCode}</code></pre>
    </div>
    ${shouldCollapse ? `<div class="code-block-expand-hint" onclick="this.closest('.code-block-wrapper').classList.remove('code-block-collapsed')">点击展开全部 ${lineCount} 行代码</div>` : ''}
  </div>`;
};

// 自定义链接渲染 - 在新标签页打开外部链接
// marked.js v15+ 使用 token 对象，兼容新旧 API
renderer.link = function(token: { href: string; title?: string | null; text: string } | string, title?: string | null, text?: string) {
  let href: string;
  let linkTitle: string | null | undefined;
  let linkText = '';

  try {
    if (typeof token === 'object' && token !== null) {
      // marked.js v15+ API - token 对象
      href = token.href ?? '#';
      linkTitle = token.title;
      linkText = token.text ?? '';
    } else if (typeof token === 'string') {
      // 旧版 API - 字符串参数
      href = token || '#';
      linkTitle = title;
      linkText = text || '';
    } else {
      href = '#';
      linkTitle = null;
      linkText = '';
    }

    // 安全检查 href
    if (!href || typeof href !== 'string') {
      href = '#';
    }
  } catch (e) {
    console.error('[Markdown] Link render error:', e);
    href = '#';
    linkText = linkText || '';
  }

  const isExternal = href.startsWith('http://') || href.startsWith('https://');
  const titleAttr = linkTitle ? ` title="${linkTitle}"` : '';
  const targetAttr = isExternal ? ' target="_blank" rel="noopener noreferrer"' : '';
  return `<a href="${href}"${titleAttr}${targetAttr}>${linkText}</a>`;
};

// 配置 marked
marked.setOptions({
  renderer,
  breaks: true,
  gfm: true,
});

const props = defineProps<{
  message: Message;
  sessionId?: string;
  mode?: string;
  isLast?: boolean;
  isLoading?: boolean;
}>();

const botName = computed(() => {
  if (props.mode === 'skills') {
    return 'ScienceClaw';
  }
  return 'ScienceClaw';
});

const emit = defineEmits<{
  (e: 'toolClick', tool: ToolContent): void;
  (e: 'suggestionClick', question: string): void;
  (e: 'convertToPdf'): void;
}>();

const { t } = useI18n();

// Feedback state
const feedback = ref<'like' | 'dislike' | null>(null);
const isCopied = ref(false);
let copyResetTimer: ReturnType<typeof setTimeout> | null = null;

const clearCopyResetTimer = () => {
  if (copyResetTimer) {
    clearTimeout(copyResetTimer);
    copyResetTimer = null;
  }
};

const showCopiedState = () => {
  clearCopyResetTimer();
  isCopied.value = true;
  copyResetTimer = setTimeout(() => {
    isCopied.value = false;
    copyResetTimer = null;
  }, 2000);
};

onUnmounted(() => {
  clearCopyResetTimer();
});

const toggleFeedback = (type: 'like' | 'dislike') => {
  if (feedback.value === type) {
    feedback.value = null;
  } else {
    feedback.value = type;
  }
};

const copyMessage = async () => {
  try {
    const text = messageContent.value?.content || '';
    if (!text.trim()) return;

    const success = await copyToClipboard(text);
    if (!success) {
      throw new Error('Copy message returned false');
    }

    showCopiedState();
    showSuccessToast(t('Message copied to clipboard'));
  } catch (err) {
    console.error('Failed to copy:', err);
    isCopied.value = false;
    clearCopyResetTimer();
    showErrorToast(t('Failed to copy message'));
  }
};

// 转成PDF
const handleConvertToPdf = () => {
  emit('convertToPdf');
};

// 本轮文件
const roundFiles = computed(() => messageContent.value.round_files || []);
const { showRoundFilesPanel, showFileListPanel } = useFilePanel();

// 处理 Markdown 内容区域的点击事件（图片 Lightbox + 代码块全屏）
const handleMarkdownClick = (event: MouseEvent) => {
  const target = event.target as HTMLElement;

  // 点击图片 - 打开 Lightbox
  if (target.tagName === 'IMG') {
    const img = target as HTMLImageElement;
    const src = img.getAttribute('src') || '';
    const alt = img.getAttribute('alt') || '';
    if (src && markdownEnhancementsRef.value) {
      markdownEnhancementsRef.value.openLightbox(src, alt);
    }
    return;
  }

  // 点击代码块全屏按钮
  const fullscreenBtn = target.closest('.code-block-fullscreen');
  if (fullscreenBtn) {
    const wrapper = fullscreenBtn.closest('.code-block-wrapper');
    if (wrapper) {
      const codeEl = wrapper.querySelector('code');
      const preEl = wrapper.querySelector('pre');
      const langEl = wrapper.querySelector('.code-block-lang');

      if (codeEl && preEl && markdownEnhancementsRef.value) {
        const html = codeEl.innerHTML;
        const lang = langEl?.textContent || 'plaintext';
        const rawCode = preEl.textContent || '';
        markdownEnhancementsRef.value.openCodeFullscreen(html, lang, rawCode);
      }
    }
    return;
  }
};

// 格式化耗时
const formatDuration = (ms: number): string => {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const mins = Math.floor(ms / 60000);
  const secs = ((ms % 60000) / 1000).toFixed(0);
  return `${mins}m ${secs}s`;
};

// 格式化 token 数量
const formatTokenCount = (count: number): string => {
  if (count < 1000) return `${count}`;
  return `${(count / 1000).toFixed(1)}K`;
};

// For backward compatibility
const messageContent = computed(() => props.message.content as MessageContent);
const attachmentsContent = computed(() => props.message.content as AttachmentsContent);

const { relativeTime } = useRelativeTime();

// DOMPurify 配置
DOMPurify.setConfig(domPurifyConfig);

// 添加 DOMPurify hook 处理 molecule-viewer
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName.toLowerCase() === 'molecule-viewer') {
    if (node.hasAttribute('src')) {
      const src = node.getAttribute('src');
      if (src && (src.startsWith('/api/') || src.startsWith('http'))) {
        node.setAttribute('src', src);
      } else {
        node.removeAttribute('src');
      }
    }
  }
});

// 渲染 Markdown 为 HTML
const renderMarkdown = (text: string): string => {
  if (typeof text !== 'string') return '';

  const logPrefix = '[Markdown]';
  try {
    // 步骤1：格式化 Markdown
    let formatted = formatMarkdown(text);

    // 步骤2：预处理数学公式
    let mathBlocks: Map<string, string> | null = null;
    try {
      const result = preprocessMath(formatted);
      formatted = result.text;
      mathBlocks = result.mathBlocks;
    } catch (e) {
      console.warn(logPrefix, 'Math preprocessing failed:', e);
      mathBlocks = new Map();
    }

    // 步骤3：渲染为 HTML
    let html = marked(formatted) as string;

    // 步骤4：后处理：恢复数学公式
    if (mathBlocks && mathBlocks.size > 0) {
      try {
        html = postprocessMath(html, mathBlocks);
      } catch (e) {
        console.warn(logPrefix, 'Math postprocessing failed:', e);
      }
    }

    // 步骤5：清理 XSS
    const sanitized = DOMPurify.sanitize(html, domPurifyConfig);
    return sanitized;
  } catch (e) {
    console.error(logPrefix, 'Markdown rendering failed:', e);
    return DOMPurify.sanitize(text, domPurifyConfig);
  }
};

/**
 * 异步渲染 Mermaid 图表
 */
const renderMermaidDiagrams = async () => {
  const logPrefix = '[Mermaid]';

  if (!markdownRef.value) {
    console.log(logPrefix, 'markdownRef not ready');
    return;
  }

  // 确保 Mermaid 已初始化
  initMermaid();

  const mermaidWrappers = markdownRef.value.querySelectorAll('.mermaid-wrapper');
  if (mermaidWrappers.length === 0) {
    console.log(logPrefix, 'No mermaid diagrams found');
    return;
  }

  console.log(logPrefix, 'Found', mermaidWrappers.length, 'mermaid diagrams');

  for (let i = 0; i < mermaidWrappers.length; i++) {
    const wrapper = mermaidWrappers[i];
    const code = decodeURIComponent(wrapper.getAttribute('data-mermaid-code') || '');
    const contentEl = wrapper.querySelector('.mermaid-content') as HTMLElement;
    const loadingEl = wrapper.querySelector('.mermaid-loading') as HTMLElement;

    if (!code || !contentEl) {
      console.warn(logPrefix, `Diagram ${i + 1}: missing code or content element`);
      continue;
    }

    console.log(logPrefix, `Diagram ${i + 1}:`, code.substring(0, 50) + '...');

    // 检查缓存
    if (mermaidCache.has(code)) {
      console.log(logPrefix, `Diagram ${i + 1}: using cache`);
      contentEl.innerHTML = mermaidCache.get(code)!;
      if (loadingEl) loadingEl.style.display = 'none';
      contentEl.style.display = 'block';
      continue;
    }

    try {
      const startTime = performance.now();
      // 使用 mermaid.render 渲染
      const { svg } = await mermaid.render(`mermaid-svg-${Date.now()}-${i}`, code);
      mermaidCache.set(code, svg);
      contentEl.innerHTML = svg;
      if (loadingEl) loadingEl.style.display = 'none';
      contentEl.style.display = 'block';
      const elapsed = (performance.now() - startTime).toFixed(2);
      console.log(logPrefix, `Diagram ${i + 1}: rendered in ${elapsed}ms`);
    } catch (e) {
      console.error(logPrefix, `Diagram ${i + 1}: render error:`, e);
      if (loadingEl) {
        loadingEl.innerHTML = `
          <div class="mermaid-error">
            <svg class="h-5 w-5 text-red-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span>图表渲染失败</span>
          </div>
          <pre class="mermaid-raw-code">${code}</pre>
        `;
      }
    }
  }
};

// 监听内容变化，渲染 Mermaid 图表（仅在组件挂载后）
watch(
  () => messageContent.value?.content,
  () => {
    nextTick(() => {
      if (markdownRef.value) {
        renderMermaidDiagrams();
      }
    });
  }
);

onMounted(() => {
  // 组件挂载后渲染 Mermaid 图表
  nextTick(() => {
    renderMermaidDiagrams();
  });
});

// 解析内容
const parseContent = (markdown: string) => {
  // Extract suggested questions
  const questions: string[] = [];
  const suggestionRegex = /<suggested_questions>([\s\S]*?)<\/suggested_questions>/;
  const match = markdown.match(suggestionRegex);

  let contentToRender = markdown;

  if (match) {
    const questionsXml = match[1];
    const qRegex = /<question>(.*?)<\/question>/g;
    let qMatch;
    while ((qMatch = qRegex.exec(questionsXml)) !== null) {
      questions.push(qMatch[1].trim());
    }
    contentToRender = markdown.replace(suggestionRegex, '');
  }

  // 渲染 Markdown
  const html = renderMarkdown(contentToRender);

  // 解析 HTML
  const parser = new DOMParser();
  const doc = parser.parseFromString(`<body>${html}</body>`, 'text/html');
  const body = doc.body;

  interface Part {
    type: string;
    content?: string;
    src?: string;
    alt?: string;
    questions?: string[];
  }

  const escapeHtml = (text: string) => {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  };

  const processNode = (node: Node): Part[] => {
    if (node.nodeType === Node.TEXT_NODE) {
      const text = node.textContent || '';
      if (!text.trim()) return [];
      return [{ type: 'html', content: escapeHtml(text) }];
    }

    if (node.nodeType === Node.ELEMENT_NODE) {
      const el = node as HTMLElement;
      const tagName = el.tagName.toLowerCase();

      // 特殊组件
      if (tagName === 'molecule-viewer') {
        return [{ type: 'molecule', src: transformSrc(el.getAttribute('src') || '') }];
      }
      if (tagName === 'html-viewer') {
        return [{ type: 'html-file', src: transformSrc(el.getAttribute('src') || '') }];
      }
      if (tagName === 'img') {
        return [{ type: 'image', src: transformSrc(el.getAttribute('src') || ''), alt: el.getAttribute('alt') || '' }];
      }

      // 处理子节点
      let childParts: Part[] = [];
      node.childNodes.forEach(child => {
        childParts = childParts.concat(processNode(child));
      });

      const hasSpecialComponent = childParts.some(p => p.type !== 'html');

      if (hasSpecialComponent) {
        return childParts;
      } else {
        return [{ type: 'html', content: el.outerHTML }];
      }
    }

    return [];
  };

  // 处理所有节点
  let rawParts: Part[] = [];
  body.childNodes.forEach(node => {
    rawParts = rawParts.concat(processNode(node));
  });

  // 合并相邻的 HTML 部分
  const mergedParts: Part[] = [];
  let currentHtmlContent = '';

  rawParts.forEach(part => {
    if (part.type === 'html') {
      currentHtmlContent += part.content || '';
    } else {
      if (currentHtmlContent) {
        mergedParts.push({ type: 'html', content: currentHtmlContent });
        currentHtmlContent = '';
      }
      mergedParts.push(part);
    }
  });

  if (currentHtmlContent) {
    mergedParts.push({ type: 'html', content: currentHtmlContent });
  }

  // 添加建议问题
  if (questions.length > 0) {
    mergedParts.push({ type: 'questions', questions });
  }

  return mergedParts.length > 0 ? mergedParts : [{ type: 'html', content: '' }];
};
</script>

<style>
.duration-300 { animation-duration: .3s; transition-duration: .3s; }

.msg-enter-left { animation: msgSlideLeft 0.3s ease-out both; }
.msg-enter-right { animation: msgSlideRight 0.3s ease-out both; }

@keyframes msgSlideLeft {
  from { opacity: 0; transform: translateX(-8px); }
  to { opacity: 1; transform: translateX(0); }
}
@keyframes msgSlideRight {
  from { opacity: 0; transform: translateX(8px); }
  to { opacity: 1; transform: translateX(0); }
}

/* 用户消息操作栏 */
.msg-user-inline-actions {
  @apply flex justify-end w-full pr-1 pt-1;
}

.msg-user-copy-pill {
  @apply inline-flex items-center gap-1.5 h-8 px-3 rounded-full;
  @apply bg-white/90 dark:bg-gray-800/80 backdrop-blur-sm;
  @apply border border-blue-100/80 dark:border-gray-700/70;
  @apply text-[12px] font-medium text-gray-500 dark:text-gray-300;
  @apply shadow-sm shadow-blue-500/10;
  @apply transition-all duration-150;
  @apply hover:-translate-y-0.5 hover:shadow-md hover:shadow-blue-500/15;
}

.msg-user-copy-pill:hover {
  @apply text-blue-600 dark:text-blue-300;
}

.msg-user-copy-pill--copied {
  @apply bg-emerald-50 text-emerald-600 border-emerald-200;
  @apply dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-800/60;
}

/* 底部操作栏 */
.msg-footer-bar {
  @apply mt-1.5 flex items-center gap-2 opacity-60 transition-opacity duration-200;
}

.group:hover .msg-footer-bar {
  @apply opacity-100;
}

.msg-actions-capsule {
  @apply inline-flex items-center gap-0.5 h-9 px-1.5;
  @apply bg-gray-100/80 dark:bg-gray-800/60;
  @apply backdrop-blur-sm;
  @apply border border-gray-200/50 dark:border-gray-700/50;
  @apply rounded-full;
}

.msg-action-btn {
  @apply relative flex items-center justify-center;
  @apply w-7 h-7 rounded-md;
  @apply text-gray-400 dark:text-gray-500;
  @apply hover:bg-gray-200/60 dark:hover:bg-gray-700/60;
  @apply hover:text-gray-600 dark:hover:text-gray-300;
  @apply transition-all duration-150;
  @apply active:scale-95;
}

.msg-action-btn--liked {
  @apply bg-green-100/80 dark:bg-green-900/30;
  @apply text-green-600 dark:text-green-400;
  @apply hover:bg-green-200/80 dark:hover:bg-green-900/40;
}

.msg-action-btn--disliked {
  @apply bg-red-100/80 dark:bg-red-900/30;
  @apply text-red-600 dark:text-red-400;
  @apply hover:bg-red-200/80 dark:hover:bg-red-900/40;
}

.msg-action-btn--copied {
  @apply text-green-600 dark:text-green-400;
}

.msg-action-btn--files {
  @apply flex items-center gap-0;
  @apply w-auto px-1.5;
  @apply text-blue-600 dark:text-blue-400;
  @apply hover:bg-blue-100/80 dark:hover:bg-blue-900/30;
}

.msg-action-divider {
  @apply w-px h-4 mx-0.5;
  @apply bg-gray-300/60 dark:bg-gray-600/60;
}

.msg-stats-capsule {
  @apply inline-flex items-center gap-0 h-9 px-2;
  @apply bg-gray-100/80 dark:bg-gray-800/60;
  @apply backdrop-blur-sm;
  @apply border border-gray-200/50 dark:border-gray-700/50;
  @apply rounded-full;
}

.msg-stat-tag {
  @apply inline-flex items-center gap-1;
  @apply text-[12px] font-medium;
}

.msg-stat-tag--time { @apply text-blue-600 dark:text-blue-400; }
.msg-stat-tag--tools { @apply text-emerald-600 dark:text-emerald-400; }
.msg-stat-tag--tokens { @apply text-violet-600 dark:text-violet-400; }

.msg-stat-with-tooltip {
  position: relative;
  cursor: default;
}

.msg-stat-with-tooltip::after {
  content: attr(data-tooltip);
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  line-height: 1.4;
  white-space: nowrap;
  color: #fff;
  background: rgba(30, 41, 59, 0.95);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.2s ease, visibility 0.2s ease;
  z-index: 100;
  pointer-events: none;
}

.dark .msg-stat-with-tooltip::after {
  background: rgba(51, 65, 85, 0.95);
}

.msg-stat-with-tooltip::before {
  content: '';
  position: absolute;
  bottom: calc(100% + 2px);
  left: 50%;
  transform: translateX(-50%);
  border: 6px solid transparent;
  border-top-color: rgba(30, 41, 59, 0.95);
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.2s ease, visibility 0.2s ease;
  z-index: 100;
}

.dark .msg-stat-with-tooltip::before {
  border-top-color: rgba(51, 65, 85, 0.95);
}

.msg-stat-with-tooltip:hover::after,
.msg-stat-with-tooltip:hover::before {
  opacity: 1;
  visibility: visible;
}

.msg-stat-divider {
  @apply w-px h-3.5 mx-3;
  @apply bg-gray-300/60 dark:bg-gray-600/60;
}

.message-html-content-user :deep(a) {
  color: inherit;
  text-decoration: underline;
}

.message-html-content-user :deep(code:not(pre code)) {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 0.375rem;
  padding: 0 0.25rem;
}

/* ================================
   Markdown 内容样式 - 精美版
   ================================ */
.markdown-content {
  max-width: 100%;
  word-wrap: break-word;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
}

/* ===== 标题样式 ===== */
.markdown-content h1 {
  font-size: 1.65em;
  font-weight: 800;
  margin: 1.6em 0 0.7em;
  padding-bottom: 0.4em;
  border-bottom: 2px solid;
  border-image: linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899) 1;
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  letter-spacing: -0.02em;
}

.dark .markdown-content h1 {
  background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 50%, #f472b6 100%);
  -webkit-background-clip: text;
  background-clip: text;
}

.markdown-content h2 {
  font-size: 1.4em;
  font-weight: 700;
  margin: 1.4em 0 0.6em;
  padding-bottom: 0.25em;
  border-bottom: 1px solid;
  border-image: linear-gradient(90deg, #3b82f6 0%, transparent 100%) 1;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 0.4em;
}

.markdown-content h2::before {
  content: '';
  display: inline-block;
  width: 4px;
  height: 1em;
  background: linear-gradient(180deg, #3b82f6, #8b5cf6);
  border-radius: 2px;
}

.markdown-content h3 {
  font-size: 1.2em;
  font-weight: 600;
  margin: 1.3em 0 0.5em;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 0.3em;
}

.markdown-content h3::before {
  content: '▸';
  color: #3b82f6;
  font-size: 0.8em;
}

.markdown-content h4 {
  font-size: 1.1em;
  font-weight: 600;
  margin: 1.1em 0 0.4em;
  color: var(--text-secondary);
}

/* ===== 段落 ===== */
.markdown-content p {
  margin: 0.75em 0;
  line-height: 1.8;
  color: var(--text-primary);
}

/* ===== 链接 ===== */
.markdown-content a {
  color: #3b82f6;
  text-decoration: none;
  position: relative;
  transition: color 0.2s;
}

.markdown-content a::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 0;
  height: 1.5px;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
  transition: width 0.3s ease;
}

.markdown-content a:hover {
  color: #2563eb;
}

.markdown-content a:hover::after {
  width: 100%;
}

/* ===== 列表样式 ===== */
.markdown-content ul,
.markdown-content ol {
  margin: 0.8em 0;
  padding-left: 0;
  list-style: none;
}

.markdown-content ul {
  counter-reset: ul-item;
}

.markdown-content ul > li {
  position: relative;
  padding-left: 1.6em;
  margin: 0.4em 0;
  line-height: 1.7;
}

.markdown-content ul > li::before {
  content: '';
  position: absolute;
  left: 0.3em;
  top: 0.65em;
  width: 6px;
  height: 6px;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  border-radius: 50%;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
}

.markdown-content ul > li::marker {
  display: none;
}

.markdown-content ol {
  counter-reset: ol-item;
}

.markdown-content ol > li {
  position: relative;
  padding-left: 2.2em;
  margin: 0.4em 0;
  line-height: 1.7;
  list-style: none;
}

.markdown-content ol > li::before {
  counter-increment: ol-item;
  content: counter(ol-item);
  position: absolute;
  left: 0;
  top: 0.1em;
  width: 1.6em;
  height: 1.6em;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  color: white;
  font-size: 0.75em;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
}

/* 嵌套列表 */
.markdown-content li ul,
.markdown-content li ol {
  margin: 0.3em 0;
}

/* ===== 引用块 ===== */
.markdown-content blockquote {
  margin: 1.2em 0;
  padding: 1em 1.2em;
  border: none;
  border-left: 4px solid;
  border-image: linear-gradient(180deg, #3b82f6, #8b5cf6, #ec4899) 1;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.05) 0%, rgba(139, 92, 246, 0.05) 100%);
  border-radius: 0 12px 12px 0;
  position: relative;
  overflow: hidden;
}

.markdown-content blockquote::before {
  content: '"';
  position: absolute;
  top: -0.1em;
  left: 0.3em;
  font-size: 3em;
  font-family: Georgia, serif;
  color: rgba(59, 130, 246, 0.15);
  line-height: 1;
}

.dark .markdown-content blockquote {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%);
}

.markdown-content blockquote p {
  margin: 0;
  color: var(--text-secondary);
  font-style: italic;
}

.markdown-content blockquote p:not(:last-child) {
  margin-bottom: 0.5em;
}

/* ===== 表格 ===== */
.markdown-content table {
  width: 100%;
  margin: 1.2em 0;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 0.9em;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.markdown-content thead {
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
}

.markdown-content th {
  color: white;
  font-weight: 600;
  text-align: left;
  padding: 0.8em 1em;
  text-transform: uppercase;
  font-size: 0.8em;
  letter-spacing: 0.05em;
}

.markdown-content td {
  padding: 0.7em 1em;
  border-bottom: 1px solid var(--border-light);
  background: var(--background-white-main);
}

.dark .markdown-content td {
  background: #1a1a1a;
}

.markdown-content tr:last-child td {
  border-bottom: none;
}

.markdown-content tr:nth-child(even) td {
  background: rgba(0, 0, 0, 0.02);
}

.dark .markdown-content tr:nth-child(even) td {
  background: rgba(255, 255, 255, 0.02);
}

/* ===== 行内代码 ===== */
.markdown-content code:not(pre code) {
  background: linear-gradient(135deg, rgba(236, 72, 153, 0.1) 0%, rgba(168, 85, 247, 0.1) 100%);
  border: 1px solid rgba(236, 72, 153, 0.2);
  border-radius: 6px;
  padding: 0.2em 0.5em;
  font-size: 0.85em;
  font-family: 'Fira Code', 'JetBrains Mono', 'SF Mono', Consolas, Monaco, monospace;
  color: #db2777;
  font-weight: 500;
}

.dark .markdown-content code:not(pre code) {
  background: linear-gradient(135deg, rgba(236, 72, 153, 0.15) 0%, rgba(168, 85, 247, 0.15) 100%);
  border-color: rgba(236, 72, 153, 0.3);
  color: #f472b6;
}

/* ===== 代码块 ===== */
.markdown-content .code-block-wrapper {
  margin: 1.2em 0;
  border-radius: 12px;
  overflow: hidden;
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.1),
    0 2px 4px -1px rgba(0, 0, 0, 0.06);
  border: 1px solid var(--border-main);
  transition: box-shadow 0.3s, transform 0.3s;
}

.markdown-content .code-block-wrapper:hover {
  box-shadow:
    0 10px 15px -3px rgba(0, 0, 0, 0.1),
    0 4px 6px -2px rgba(0, 0, 0, 0.05);
  transform: translateY(-1px);
}

.markdown-content .code-block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5em 1em;
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.dark .markdown-content .code-block-header {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
}

.markdown-content .code-block-lang {
  color: #94a3b8;
  text-transform: uppercase;
  font-size: 0.7em;
  font-weight: 600;
  letter-spacing: 0.1em;
  display: flex;
  align-items: center;
  gap: 0.4em;
}

.markdown-content .code-block-lang::before {
  content: '';
  width: 8px;
  height: 8px;
  background: linear-gradient(135deg, #22c55e, #16a34a);
  border-radius: 50%;
  box-shadow: 0 0 8px rgba(34, 197, 94, 0.5);
}

.markdown-content .code-block-copy {
  display: flex;
  align-items: center;
  gap: 0.4em;
  padding: 0.4em 0.8em;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  border-radius: 6px;
  color: #94a3b8;
  font-size: 0.75em;
  cursor: pointer;
  transition: all 0.2s;
}

.markdown-content .code-block-copy:hover {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  transform: scale(1.02);
}

.markdown-content .code-block-copy:active {
  transform: scale(0.98);
}

/* 代码块操作按钮组 */
.markdown-content .code-block-actions {
  display: flex;
  align-items: center;
  gap: 0.5em;
}

/* 全屏按钮 */
.markdown-content .code-block-fullscreen {
  display: flex;
  align-items: center;
  gap: 0.4em;
  padding: 0.4em 0.8em;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  border-radius: 6px;
  color: #94a3b8;
  font-size: 0.75em;
  cursor: pointer;
  transition: all 0.2s;
}

.markdown-content .code-block-fullscreen:hover {
  background: rgba(59, 130, 246, 0.3);
  color: #60a5fa;
  transform: scale(1.02);
}

.markdown-content .code-block-fullscreen:active {
  transform: scale(0.98);
}

.markdown-content .code-block-pre {
  margin: 0;
  padding: 1.2em;
  overflow-x: auto;
  background: #0d1117 !important;
  font-feature-settings: 'liga' 1, 'calt' 1;
}

.markdown-content .code-block-pre code {
  font-family: 'Fira Code', 'JetBrains Mono', 'SF Mono', Consolas, Monaco, monospace;
  font-size: 0.875em;
  line-height: 1.7;
  background: transparent !important;
  padding: 0 !important;
  color: #e6edf3;
}

/* 代码块行数标签 */
.markdown-content .code-block-line-count {
  font-size: 0.65em;
  color: #64748b;
  margin-left: auto;
  margin-right: 0.5em;
}

/* 代码块内容区域 */
.markdown-content .code-block-content {
  display: flex;
  overflow: hidden;
}

/* 行号区域 */
.markdown-content .code-block-lines {
  flex-shrink: 0;
  padding: 1.2em 0;
  background: rgba(255, 255, 255, 0.03);
  border-right: 1px solid rgba(255, 255, 255, 0.05);
  text-align: right;
  user-select: none;
}

.markdown-content .code-block-lines pre {
  margin: 0;
  padding: 0 0.8em 0 0.8em;
  color: #4a5568;
  font-family: 'Fira Code', 'JetBrains Mono', 'SF Mono', Consolas, Monaco, monospace;
  font-size: 0.875em;
  line-height: 1.7;
  counter-reset: line;
}

/* 更新代码块 pre 样式 */
.markdown-content .code-block-pre {
  margin: 0;
  padding: 1.2em;
  overflow-x: auto;
  background: #0d1117 !important;
  font-feature-settings: 'liga' 1, 'calt' 1;
  flex: 1;
  min-width: 0;
}

/* 代码块折叠样式 */
.markdown-content .code-block-wrapper.code-block-collapsed .code-block-content {
  max-height: 380px;
  overflow: hidden;
  position: relative;
}

.markdown-content .code-block-wrapper.code-block-collapsed .code-block-content::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 100px;
  background: linear-gradient(to bottom, transparent, #0d1117);
  pointer-events: none;
}

/* 展开提示 */
.markdown-content .code-block-expand-hint {
  padding: 0.8em;
  text-align: center;
  background: linear-gradient(to right, #1e293b, #334155);
  color: #60a5fa;
  font-size: 0.85em;
  cursor: pointer;
  transition: all 0.2s;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.markdown-content .code-block-expand-hint:hover {
  background: linear-gradient(to right, #334155, #475569);
  color: #93c5fd;
}

/* 展开按钮 */
.markdown-content .code-block-expand {
  display: flex;
  align-items: center;
  gap: 0.4em;
  padding: 0.4em 0.8em;
  background: rgba(139, 92, 246, 0.2);
  border: none;
  border-radius: 6px;
  color: #a78bfa;
  font-size: 0.75em;
  cursor: pointer;
  transition: all 0.2s;
}

.markdown-content .code-block-expand:hover {
  background: rgba(139, 92, 246, 0.3);
  color: #c4b5fd;
  transform: scale(1.02);
}

/* 展开状态下隐藏展开按钮 */
.markdown-content .code-block-wrapper:not(.code-block-collapsed) .code-block-expand svg {
  transform: rotate(180deg);
}

.markdown-content .code-block-wrapper:not(.code-block-collapsed) .expand-text {
  display: none;
}

.markdown-content .code-block-wrapper.code-block-collapsed .expand-text::before {
  content: '展开';
}

.markdown-content .code-block-wrapper:not(.code-block-collapsed) .code-block-expand-hint {
  display: none;
}

/* ===== 分割线 ===== */
.markdown-content hr {
  border: none;
  height: 2px;
  background: linear-gradient(90deg, transparent, #3b82f6, #8b5cf6, #ec4899, transparent);
  margin: 2em 0;
  border-radius: 1px;
}

/* ===== 图片 ===== */
.markdown-content img {
  max-width: 100%;
  height: auto;
  border-radius: 12px;
  margin: 1em 0;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s, box-shadow 0.3s;
}

.markdown-content img:hover {
  transform: scale(1.02);
  box-shadow: 0 10px 20px -5px rgba(0, 0, 0, 0.15);
}

/* ===== 强调文本 ===== */
.markdown-content strong {
  font-weight: 700;
  color: var(--text-primary);
  background: linear-gradient(135deg, transparent 60%, rgba(251, 191, 36, 0.3) 60%);
  padding: 0 0.1em;
}

.markdown-content em {
  font-style: italic;
  color: var(--text-secondary);
}

/* ===== 删除线 ===== */
.markdown-content del {
  color: var(--text-tertiary);
  text-decoration: line-through rgba(239, 68, 68, 0.5);
}

/* ===== 键盘按键 ===== */
.markdown-content kbd {
  display: inline-block;
  padding: 0.2em 0.5em;
  font-size: 0.85em;
  font-family: inherit;
  background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
  border: 1px solid #dee2e6;
  border-radius: 4px;
  box-shadow:
    0 1px 1px rgba(0, 0, 0, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.5);
  color: var(--text-primary);
}

.dark .markdown-content kbd {
  background: linear-gradient(180deg, #374151 0%, #1f2937 100%);
  border-color: #4b5563;
}

/* ===== KaTeX 数学公式 ===== */
.markdown-content .katex-display {
  display: block;
  margin: 1.2em 0;
  padding: 1em 1.2em;
  overflow-x: auto;
  overflow-y: hidden;
  text-align: center;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.03) 0%, rgba(139, 92, 246, 0.03) 100%);
  border-radius: 12px;
  border: 1px solid var(--border-light);
}

.dark .markdown-content .katex-display {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.05) 0%, rgba(139, 92, 246, 0.05) 100%);
}

.markdown-content .katex-inline {
  display: inline;
  padding: 0.1em 0.3em;
  background: rgba(139, 92, 246, 0.08);
  border-radius: 4px;
}

.dark .markdown-content .katex-inline {
  background: rgba(139, 92, 246, 0.12);
}

.markdown-content .katex {
  font-size: 1.1em;
}

.markdown-content .katex-display .katex {
  font-size: 1.25em;
}

.markdown-content .katex-error {
  color: #ef4444;
  font-family: 'Fira Code', monospace;
  font-size: 0.9em;
  background: rgba(239, 68, 68, 0.1);
  padding: 0.5em;
  border-radius: 4px;
}

/* ===== Mermaid 图表 ===== */
.markdown-content .mermaid-wrapper {
  margin: 1.2em 0;
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  border-radius: 12px;
  padding: 1.5em;
  overflow: auto;
  border: 1px solid var(--border-main);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.dark .markdown-content .mermaid-wrapper {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}

.markdown-content .mermaid-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75em;
  padding: 2em;
  color: #94a3b8;
  font-size: 0.9em;
}

.markdown-content .mermaid-loading svg {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.markdown-content .mermaid-content {
  display: none;
  min-height: 100px;
}

.markdown-content .mermaid-content svg {
  max-width: 100%;
  height: auto;
  margin: 0 auto;
  display: block;
}

.markdown-content .mermaid-error {
  display: flex;
  align-items: center;
  gap: 0.5em;
  color: #ef4444;
  padding: 1em;
  background: rgba(239, 68, 68, 0.1);
  border-radius: 8px;
}

.markdown-content .mermaid-raw-code {
  margin-top: 1em;
  padding: 1em;
  background: #0d1117;
  border-radius: 8px;
  font-family: 'Fira Code', monospace;
  font-size: 0.85em;
  color: #e6edf3;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

/* 移动端适配 */
@media (max-width: 640px) {
  .msg-footer-bar {
    @apply opacity-100 flex-wrap;
  }
  .msg-action-btn { @apply w-8 h-8; }
  .msg-stats-capsule { @apply mt-1; }
  .markdown-content table { font-size: 0.85em; }
}
</style>
