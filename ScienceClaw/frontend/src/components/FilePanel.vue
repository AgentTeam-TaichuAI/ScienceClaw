<template>
  <div ref="filePanelRef" class="h-full flex-shrink-0 relative z-20"
    :style="{ 'width': panelWidth + 'px', 'max-width': isShow ? '100%' : '0px', 'opacity': isShow ? '1' : '0', 'transition': isResizing ? 'none' : '0.3s ease-in-out' }">
    <!-- Resize Handle - 增大触摸区域 -->
    <div
      v-if="isShow"
      class="absolute left-0 top-0 bottom-0 w-2 cursor-ew-resize z-30 group"
      @mousedown="startResize"
    >
      <div class="absolute left-0 top-0 bottom-0 w-1 bg-transparent group-hover:bg-blue-500/50 transition-colors"></div>
      <div class="absolute left-0 top-1/2 -translate-y-1/2 flex flex-col items-center justify-center gap-1 py-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <div class="w-0.5 h-1 rounded-full bg-gray-400 dark:bg-gray-500 group-hover:bg-blue-500 transition-colors"></div>
        <div class="w-0.5 h-1 rounded-full bg-gray-400 dark:bg-gray-500 group-hover:bg-blue-500 transition-colors"></div>
        <div class="w-0.5 h-1 rounded-full bg-gray-400 dark:bg-gray-500 group-hover:bg-blue-500 transition-colors"></div>
      </div>
    </div>
    <div class="h-full ml-2" :style="{ 'width': isShow ? 'calc(100% - 8px)' : '0px' }">
      <div v-if="isShow" class="bg-white dark:bg-[#1a1a1a] overflow-hidden shadow-lg ltr:border-l rtl:border-r border-gray-200/50 dark:border-gray-700/50 flex flex-col h-full w-full rounded-l-xl">
        <!-- List Mode -->
        <div v-if="isListMode" class="flex flex-col h-full w-full">
          <!-- Header with gradient accent -->
          <header class="relative flex items-center pt-5 pr-4 pl-4 pb-3 border-b border-gray-100 dark:border-gray-800">
            <div class="absolute top-0 left-4 right-4 h-[2px] rounded-full bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500"></div>
            <div class="flex items-center gap-3">
              <div class="size-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-md shadow-blue-500/20">
                <FolderOpen class="size-4.5 text-white" />
              </div>
              <h1 class="text-base font-bold text-[var(--text-primary)]">{{ $t('All Files in This Task') }}</h1>
            </div>
            <div class="flex-1"></div>
            <div class="flex items-center gap-2">
              <button @click="hideFilePanel"
                class="p-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 transition-all duration-200 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                <X class="size-4.5" />
              </button>
            </div>
          </header>
          <div class="flex-1 min-h-0 flex flex-col overflow-hidden">
            <SessionFileListContent @file-click="handleFileClick" />
          </div>
        </div>

        <!-- Round Files Mode -->
        <div v-else-if="isRoundFilesMode" class="flex flex-col h-full w-full">
          <header class="relative flex items-center pt-5 pr-4 pl-4 pb-3 border-b border-gray-100 dark:border-gray-800">
            <div class="absolute top-0 left-4 right-4 h-[2px] rounded-full bg-gradient-to-r from-emerald-500 via-blue-500 to-indigo-500"></div>
            <div class="flex items-center gap-3">
              <button @click="showFileListPanel"
                class="p-2 -ml-2 rounded-xl text-gray-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all duration-200 flex-shrink-0"
                :title="$t('All Files in This Task')">
                <ArrowLeft class="size-4.5" />
              </button>
              <div class="flex flex-col">
                <h1 class="text-base font-bold text-[var(--text-primary)]">{{ $t('Files in this round') }}</h1>
                <span class="text-xs text-[var(--text-tertiary)]">{{ roundFiles.length }} {{ $t('files') }}</span>
              </div>
            </div>
            <div class="flex-1"></div>
            <div class="flex items-center gap-2">
              <button @click="hideFilePanel"
                class="p-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 transition-all duration-200 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                <X class="size-4.5" />
              </button>
            </div>
          </header>
          <div class="flex-1 min-h-0 flex flex-col overflow-hidden">
            <RoundFileListContent :files="roundFiles" @file-click="handleFileClick" />
          </div>
        </div>

        <!-- Single File Mode -->
        <div v-else-if="fileInfo && fileType" class="flex flex-col h-full w-full overflow-hidden">
          <!-- Header with gradient accent -->
          <header class="relative flex items-center px-5 pt-5 pb-3 border-b border-gray-100 dark:border-gray-800 flex-shrink-0">
            <div class="absolute top-0 left-5 right-5 h-[2px] rounded-full bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500"></div>
            <div class="flex items-center gap-3 flex-1 min-w-0">
              <button @click="goBackFromFile"
                class="p-2 -ml-2 rounded-xl text-gray-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all duration-200 flex-shrink-0"
                :title="$t('Back to file list')">
                <ArrowLeft class="size-4.5" />
              </button>
              <div class="size-10 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm"
                :class="getFileColorClass(fileInfo.filename)">
                <component :is="fileType.icon" class="size-5" />
              </div>
              <div class="flex flex-col min-w-0 flex-1">
                <span class="text-sm font-semibold text-[var(--text-primary)] truncate" :title="fileInfo.filename">{{ fileInfo.filename }}</span>
                <span class="text-xs text-[var(--text-tertiary)] mt-0.5">{{ getFileTypeText(fileInfo.filename) }}</span>
              </div>
            </div>
            <div class="flex items-center gap-1 flex-shrink-0">
              <button @click="download"
                class="p-2.5 rounded-xl text-gray-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all duration-200"
                :title="$t('Download')">
                <Download class="size-4.5" />
              </button>
              <button @click="hideFilePanel"
                class="p-2.5 rounded-xl text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all duration-200">
                <X class="size-4.5" />
              </button>
            </div>
          </header>
          <!-- File Preview Content with Scroll -->
          <div class="flex-1 min-h-0 overflow-auto">
            <component :is="fileType.preview" :file="fileInfo" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { Download, X, FolderOpen, ArrowLeft } from 'lucide-vue-next'
import { useFilePanel } from '../composables/useFilePanel'
import { triggerAuthenticatedDownload, type FileInfo } from '../api/file'
import { getFileType, getFileTypeText } from '../utils/fileType'
import { eventBus } from '../utils/eventBus'
import { EVENT_SHOW_TOOL_PANEL } from '../constants/event'
import SessionFileListContent from './SessionFileListContent.vue'
import RoundFileListContent from './RoundFilesPopover.vue'

const {
  isShow,
  fileInfo,
  visible,
  showFilePanel,
  showFileListPanel,
  hideFilePanel,
  goBackFromFile,
  isListMode,
  isRoundFilesMode,
  roundFiles,
} = useFilePanel()

const handleFileClick = (file: FileInfo) => {
  console.log('FilePanel: handleFileClick', file);
  showFilePanel(file)
}

const filePanelRef = ref<HTMLElement>()

// Panel resize functionality
const DEFAULT_WIDTH = 450
const MIN_WIDTH = 300
const MAX_WIDTH = 800
const panelWidth = ref(DEFAULT_WIDTH)
const isResizing = ref(false)

const startResize = (e: MouseEvent) => {
  e.preventDefault()
  isResizing.value = true

  const startX = e.clientX
  const startWidth = panelWidth.value

  const onMouseMove = (e: MouseEvent) => {
    const deltaX = startX - e.clientX
    const newWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, startWidth + deltaX))
    panelWidth.value = newWidth
  }

  const onMouseUp = () => {
    isResizing.value = false
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }

  document.body.style.cursor = 'ew-resize'
  document.body.style.userSelect = 'none'
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

const fileType = computed(() => {
  if (!fileInfo.value) return null
  return getFileType(fileInfo.value.filename)
})

// Get file color class based on extension for single file mode
const getFileColorClass = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase() || '';
    if (['py', 'js', 'ts', 'jsx', 'tsx', 'vue'].includes(ext)) return 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400';
    if (['md', 'txt', 'log', 'csv'].includes(ext)) return 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400';
    if (['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'].includes(ext)) return 'bg-violet-50 dark:bg-violet-900/20 text-violet-600 dark:text-violet-400';
    if (['pdf'].includes(ext)) return 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400';
    if (['doc', 'docx'].includes(ext)) return 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400';
    if (['ppt', 'pptx'].includes(ext)) return 'bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400';
    if (['xls', 'xlsx'].includes(ext)) return 'bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400';
    if (['json', 'xml', 'yaml', 'yml'].includes(ext)) return 'bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400';
    if (['html', 'css', 'scss'].includes(ext)) return 'bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400';
    if (['mp4', 'avi', 'mov', 'webm'].includes(ext)) return 'bg-pink-50 dark:bg-pink-900/20 text-pink-600 dark:text-pink-400';
    if (['mp3', 'wav', 'flac', 'aac'].includes(ext)) return 'bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400';
    if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext)) return 'bg-yellow-50 dark:bg-yellow-900/20 text-yellow-600 dark:text-yellow-400';
    return 'bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400';
};

const download = async () => {
  if (!fileInfo.value) return
  try {
    await triggerAuthenticatedDownload(fileInfo.value)
  } catch (err) {
    console.error('Download failed:', err)
  }
}

onMounted(() => {
  eventBus.on(EVENT_SHOW_TOOL_PANEL, () => {
    visible.value = false
  })
})

onUnmounted(() => {
  eventBus.off(EVENT_SHOW_TOOL_PANEL)
})

defineExpose({
  showFilePanel,
  hideFilePanel,
  isShow
})
</script>
