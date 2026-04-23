<template>
  <div class="flex-1 min-h-0 overflow-auto px-3 py-3">
    <!-- Result files -->
    <div v-if="outputFiles.length > 0">
      <div class="flex items-center gap-2 px-2 py-1.5 mb-1">
        <div class="w-1.5 h-1.5 rounded-full bg-emerald-500"></div>
        <span class="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">{{ $t('Result files') }}</span>
        <span class="text-[10px] text-[var(--text-tertiary)] tabular-nums">({{ outputFiles.length }})</span>
      </div>
      <div class="space-y-1">
        <div
          v-for="file in outputFiles"
          :key="file.file_id"
          class="file-card group flex items-center gap-3 p-3 rounded-xl transition-all duration-200 hover:bg-gray-50/80 dark:hover:bg-white/5"
          @click="onFileClick(file)"
        >
          <div
            class="size-10 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm"
            :class="getFileColor(file.filename)"
          >
            <component :is="getFileType(file.filename).icon" class="size-5" />
          </div>
          <div class="flex flex-col flex-1 min-w-0">
            <span class="text-sm font-medium text-[var(--text-primary)] truncate group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
              {{ file.filename }}
            </span>
            <span class="text-xs text-[var(--text-tertiary)] mt-0.5">{{ formatFileSize(file.size) }}</span>
          </div>
          <div class="flex items-center gap-1 flex-shrink-0">
            <button v-if="isPreviewable(file.filename)"
              @click.stop="openPreview(toFileInfo(file))"
              class="p-1.5 rounded-lg text-[var(--text-tertiary)] hover:bg-white dark:hover:bg-gray-800 hover:text-violet-500 hover:shadow-sm transition-all duration-200"
              :title="$t('Preview')"
            >
              <Eye class="size-4" />
            </button>
            <button
              @click.stop="downloadFile(file)"
              class="p-1.5 rounded-lg text-[var(--text-tertiary)] hover:bg-white dark:hover:bg-gray-800 hover:text-blue-500 hover:shadow-sm transition-all duration-200"
              :title="$t('Download')"
            >
              <Download class="size-4" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Process files -->
    <div v-if="processFiles.length > 0" :class="{ 'mt-4': outputFiles.length > 0 }">
      <button
        class="flex items-center gap-2 px-2 py-1.5 mb-1 w-full text-left hover:bg-gray-50 dark:hover:bg-white/5 rounded-lg transition-colors"
        @click="processExpanded = !processExpanded"
      >
        <ChevronRight class="w-3.5 h-3.5 text-[var(--text-tertiary)] transition-transform duration-200" :class="{ 'rotate-90': processExpanded }" />
        <div class="w-1.5 h-1.5 rounded-full bg-amber-500"></div>
        <span class="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">{{ $t('Process files') }}</span>
        <span class="text-[10px] text-[var(--text-tertiary)] tabular-nums">({{ processFiles.length }})</span>
      </button>
      <Transition name="section-expand">
        <div v-if="processExpanded" class="space-y-1">
          <div
            v-for="file in processFiles"
            :key="file.file_id"
            class="file-card group flex items-center gap-3 p-3 rounded-xl transition-all duration-200 hover:bg-gray-50/80 dark:hover:bg-white/5"
            @click="onFileClick(file)"
          >
            <div class="size-10 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400">
              <component :is="getFileType(file.filename).icon" class="size-5" />
            </div>
            <div class="flex flex-col flex-1 min-w-0">
              <span class="text-sm font-medium text-[var(--text-primary)] truncate group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                {{ file.filename }}
              </span>
              <span class="text-xs text-[var(--text-tertiary)] mt-0.5">{{ formatFileSize(file.size) }}</span>
            </div>
            <div class="flex items-center gap-1 flex-shrink-0">
              <button v-if="isPreviewable(file.filename)"
                @click.stop="openPreview(toFileInfo(file))"
                class="p-1.5 rounded-lg text-[var(--text-tertiary)] hover:bg-white dark:hover:bg-gray-800 hover:text-violet-500 hover:shadow-sm transition-all duration-200"
                :title="$t('Preview')"
              >
                <Eye class="size-4" />
              </button>
              <button
                @click.stop="downloadFile(file)"
                class="p-1.5 rounded-lg text-[var(--text-tertiary)] hover:bg-white dark:hover:bg-gray-800 hover:text-blue-500 hover:shadow-sm transition-all duration-200"
                :title="$t('Download')"
              >
                <Download class="size-4" />
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </div>

    <!-- Empty state -->
    <div v-if="outputFiles.length === 0 && processFiles.length === 0" class="flex-1 min-h-0 flex flex-col items-center justify-center gap-4 py-16">
      <div class="size-16 rounded-2xl bg-gray-50 dark:bg-gray-800 flex items-center justify-center">
        <FolderOpen class="size-7 text-gray-300 dark:text-gray-600" />
      </div>
      <div class="text-center">
        <p class="text-sm font-medium text-[var(--text-tertiary)]">{{ $t('No files in this round') }}</p>
      </div>
    </div>

    <FilePreviewModal :file="previewFile" :visible="previewVisible" @close="previewVisible = false" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { Download, FolderOpen, ChevronRight, Eye } from 'lucide-vue-next';
import type { RoundFileInfo } from '../types/event';
import { getFileType } from '../utils/fileType';
import { formatFileSize } from '../utils/fileType';
import { useFilePanel } from '../composables/useFilePanel';
import { triggerAuthenticatedDownload } from '../api/file';
import type { FileInfo } from '../api/file';
import FilePreviewModal from './FilePreviewModal.vue';

const props = defineProps<{
  files: RoundFileInfo[];
}>();

const emit = defineEmits<{
  (e: 'file-click', file: FileInfo): void;
}>();

const processExpanded = ref(false);
const previewFile = ref<FileInfo | null>(null);
const previewVisible = ref(false);
const { showFilePanel } = useFilePanel();

const PREVIEWABLE_EXTS = ['md', 'txt', 'log', 'csv', 'json', 'xml', 'yaml', 'yml', 'sh', 'py', 'js', 'ts', 'html', 'css', 'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'bmp', 'ico'];

const isPreviewable = (filename: string) => {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  return PREVIEWABLE_EXTS.includes(ext);
};

const openPreview = (file: FileInfo) => {
  previewFile.value = file;
  previewVisible.value = true;
};

const outputFiles = computed(() => props.files.filter(f => f.category === 'output'));
const processFiles = computed(() => props.files.filter(f => f.category === 'research_data'));

const getFileColor = (filename: string) => {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  if (['py', 'js', 'ts', 'jsx', 'tsx', 'vue'].includes(ext)) return 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400';
  if (['md', 'txt', 'log', 'csv'].includes(ext)) return 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400';
  if (['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'].includes(ext)) return 'bg-violet-50 dark:bg-violet-900/20 text-violet-600 dark:text-violet-400';
  if (['pdf', 'doc', 'docx', 'ppt', 'pptx'].includes(ext)) return 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400';
  if (['json', 'xml', 'yaml', 'yml'].includes(ext)) return 'bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400';
  if (['html', 'css', 'scss'].includes(ext)) return 'bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400';
  if (['xls', 'xlsx'].includes(ext)) return 'bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400';
  return 'bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400';
};

const toFileInfo = (rf: RoundFileInfo): FileInfo => ({
  file_id: rf.file_id,
  filename: rf.filename,
  size: rf.size,
  upload_date: rf.upload_date,
  file_url: rf.file_url,
});

const onFileClick = (file: RoundFileInfo) => {
  const fi = toFileInfo(file);
  emit('file-click', fi);
  showFilePanel(fi);
};

const downloadFile = async (file: RoundFileInfo) => {
  try {
    await triggerAuthenticatedDownload(toFileInfo(file));
  } catch (err) {
    console.error('Download failed:', err);
  }
};
</script>

<style scoped>
.file-card {
  animation: fileSlideIn 0.25s ease-out both;
}
@keyframes fileSlideIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.section-expand-enter-active,
.section-expand-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}
.section-expand-enter-from,
.section-expand-leave-to {
  opacity: 0;
  max-height: 0;
}
.section-expand-enter-to,
.section-expand-leave-from {
  opacity: 1;
  max-height: 800px;
}
</style>
