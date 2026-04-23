<template>
  <Teleport to="body">
    <Transition name="preview-fade">
      <div v-if="visible" class="fixed inset-0 z-[9999] flex items-center justify-center" @click.self="close">
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="close"></div>
        <div
          class="relative w-[720px] max-w-[90vw] max-h-[85vh] bg-white dark:bg-[#1e1e1e] rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 overflow-hidden flex flex-col"
          @click.stop
        >
          <!-- Header -->
          <header class="flex items-center justify-between px-5 py-3.5 border-b border-gray-100 dark:border-gray-800 flex-shrink-0">
            <div class="flex items-center gap-3 min-w-0 flex-1">
              <div class="size-9 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm"
                :class="fileColor">
                <component :is="fileTypeInfo.icon" class="size-4.5" />
              </div>
              <div class="flex flex-col min-w-0">
                <span class="text-sm font-semibold text-[var(--text-primary)] truncate">{{ file?.filename }}</span>
                <span class="text-xs text-[var(--text-tertiary)]">{{ fileTypeLabel }}</span>
              </div>
            </div>
            <div class="flex items-center gap-1 flex-shrink-0">
              <button
                @click="handleDownload"
                class="p-2 rounded-lg text-[var(--text-tertiary)] hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-blue-500 transition-all"
                :title="$t('Download')"
              >
                <Download class="size-4" />
              </button>
              <button
                @click="close"
                class="p-2 rounded-lg text-[var(--text-tertiary)] hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-[var(--text-primary)] transition-all"
              >
                <X class="size-4" />
              </button>
            </div>
          </header>

          <!-- Content -->
          <div class="flex-1 min-h-0 overflow-auto">
            <!-- Loading -->
            <div v-if="loading" class="flex items-center justify-center py-20">
              <div class="animate-spin rounded-full h-8 w-8 border-2 border-blue-500 border-t-transparent"></div>
            </div>

            <!-- Error -->
            <div v-else-if="error" class="flex flex-col items-center justify-center py-20 gap-3">
              <AlertCircle class="size-8 text-red-400" />
              <p class="text-sm text-[var(--text-tertiary)]">{{ error }}</p>
            </div>

            <!-- Image preview -->
            <div v-else-if="previewType === 'image'" class="flex items-center justify-center p-6 min-h-[300px]">
              <img :src="imageUrl" :alt="file?.filename" class="max-w-full max-h-[70vh] object-contain rounded-lg" />
            </div>

            <!-- Markdown preview -->
            <div v-else-if="previewType === 'markdown'" class="p-6">
              <div class="markdown-preview-content text-sm" v-html="renderedMarkdown"></div>
            </div>

            <!-- Text preview -->
            <div v-else-if="previewType === 'text'" class="p-6">
              <pre class="text-sm text-[var(--text-primary)] whitespace-pre-wrap break-words font-mono leading-relaxed bg-gray-50 dark:bg-gray-900/50 rounded-xl p-4">{{ textContent }}</pre>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted, onBeforeUnmount } from 'vue';
import { Download, X, AlertCircle } from 'lucide-vue-next';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import type { FileInfo } from '../api/file';
import { getFileDownloadUrl, triggerAuthenticatedDownload, fetchFileBlob } from '../api/file';
import { getFileType } from '../utils/fileType';

const props = defineProps<{
  file: FileInfo | null;
  visible: boolean;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const loading = ref(false);
const error = ref('');
const textContent = ref('');
const imageUrl = ref('');

const IMAGE_EXTS = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'bmp', 'ico'];
const MARKDOWN_EXTS = ['md'];
const TEXT_EXTS = ['txt', 'log', 'csv', 'json', 'xml', 'yaml', 'yml', 'sh', 'py', 'js', 'ts', 'html', 'css'];

const ext = computed(() => props.file?.filename?.split('.').pop()?.toLowerCase() || '');

const previewType = computed<'image' | 'markdown' | 'text' | 'unknown'>(() => {
  if (IMAGE_EXTS.includes(ext.value)) return 'image';
  if (MARKDOWN_EXTS.includes(ext.value)) return 'markdown';
  if (TEXT_EXTS.includes(ext.value)) return 'text';
  return 'unknown';
});

const fileTypeInfo = computed(() => getFileType(props.file?.filename || ''));

const fileColor = computed(() => {
  const e = ext.value;
  if (['py', 'js', 'ts', 'jsx', 'tsx', 'vue'].includes(e)) return 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400';
  if (['md', 'txt', 'log', 'csv'].includes(e)) return 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400';
  if (IMAGE_EXTS.includes(e)) return 'bg-violet-50 dark:bg-violet-900/20 text-violet-600 dark:text-violet-400';
  return 'bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400';
});

const fileTypeLabel = computed(() => {
  if (previewType.value === 'image') return 'Image';
  if (previewType.value === 'markdown') return 'Markdown';
  return 'Text';
});

const renderedMarkdown = computed(() => {
  if (!textContent.value) return '';
  try {
    const html = marked.parse(textContent.value);
    return DOMPurify.sanitize(html as string);
  } catch {
    return `<pre>${textContent.value}</pre>`;
  }
});

const loadContent = async () => {
  if (!props.file) return;
  loading.value = true;
  error.value = '';
  textContent.value = '';
  imageUrl.value = '';

  try {
    if (previewType.value === 'image') {
      imageUrl.value = await getFileDownloadUrl(props.file);
    } else {
      const blob = await fetchFileBlob(props.file);
      textContent.value = await blob.text();
    }
  } catch (e: any) {
    error.value = e?.message || 'Failed to load file';
  } finally {
    loading.value = false;
  }
};

const handleDownload = async () => {
  if (!props.file) return;
  try {
    await triggerAuthenticatedDownload(props.file);
  } catch (err) {
    console.error('Download failed:', err);
  }
};

const close = () => emit('close');

const onKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && props.visible) close();
};

onMounted(() => document.addEventListener('keydown', onKeydown));
onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown));

watch(() => [props.visible, props.file?.file_id], ([vis]) => {
  if (vis && props.file) {
    loadContent();
  }
}, { immediate: true });
</script>

<style scoped>
.preview-fade-enter-active,
.preview-fade-leave-active {
  transition: opacity 0.2s ease;
}
.preview-fade-enter-from,
.preview-fade-leave-to {
  opacity: 0;
}
</style>
