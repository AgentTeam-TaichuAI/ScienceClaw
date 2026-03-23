<template>
  <div class="flex h-full transition-[width] duration-300 ease-in-out"
    :style="{ width: isLeftPanelShow ? '320px' : '60px' }">

    <!-- Navigation Rail -->
    <div class="nav-rail w-[60px] h-full flex flex-col items-center py-4 gap-3 border-r border-gray-200/60 dark:border-gray-700/40 z-20 flex-shrink-0 relative">
      <div class="absolute inset-0 bg-gray-50 dark:bg-[#111] -z-10"></div>

      <!-- Chat Tab -->
      <button @click="handleChatTabClick"
        class="nav-btn size-10 rounded-xl flex items-center justify-center transition-all duration-250 group relative"
        :class="isChatActive
          ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white shadow-md shadow-blue-500/25'
          : 'text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-600 dark:hover:text-gray-300'"
      >
        <MessageSquare :size="19" :stroke-width="isChatActive ? 2.5 : 1.8" />
        <div v-if="isChatActive" class="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-gradient-to-b from-blue-400 to-indigo-500 rounded-r-full"></div>
      </button>

      <!-- Skills Tab -->
      <button @click="handleSkillsTabClick"
        class="nav-btn size-10 rounded-xl flex items-center justify-center transition-all duration-250 group relative"
        :class="isSkillsActive
          ? 'bg-gradient-to-br from-violet-500 to-fuchsia-600 text-white shadow-md shadow-violet-500/25'
          : 'text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-600 dark:hover:text-gray-300'"
      >
        <Blocks :size="19" :stroke-width="isSkillsActive ? 2.5 : 1.8" />
        <div v-if="isSkillsActive" class="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-gradient-to-b from-violet-400 to-fuchsia-500 rounded-r-full"></div>
      </button>

      <!-- Tools Tab -->
      <button @click="handleToolsTabClick"
        class="nav-btn size-10 rounded-xl flex items-center justify-center transition-all duration-250 group relative"
        :class="isToolsActive
          ? 'bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-700 text-white shadow-md shadow-purple-500/25'
          : 'text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-600 dark:hover:text-gray-300'"
      >
        <Wrench :size="19" :stroke-width="isToolsActive ? 2.5 : 1.8" />
        <div v-if="isToolsActive" class="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-gradient-to-b from-blue-500 via-indigo-500 to-purple-600 rounded-r-full"></div>
      </button>

      <!-- Scheduled Tasks Tab -->
      <button @click="handleTasksTabClick"
        class="nav-btn size-10 rounded-xl flex items-center justify-center transition-all duration-250 group relative"
        :class="isTasksActive
          ? 'bg-gradient-to-br from-sky-400 to-teal-500 text-white shadow-md shadow-sky-400/25'
          : 'text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-600 dark:hover:text-gray-300'"
      >
        <CalendarClock :size="19" :stroke-width="isTasksActive ? 2.5 : 1.8" />
        <div v-if="isTasksActive" class="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-gradient-to-b from-sky-300 to-teal-400 rounded-r-full"></div>
      </button>

      <!-- Spacer -->
      <div class="flex-1"></div>

      <!-- Settings -->
      <button @click="openSettingsDialog()"
        class="nav-btn size-10 rounded-xl flex items-center justify-center transition-all duration-250 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-600 dark:hover:text-gray-300"
        :title="t('Settings')"
      >
        <Settings2 :size="19" :stroke-width="1.8" />
      </button>

      <!-- User Avatar -->
      <div class="relative flex items-center justify-center mb-1" @mouseenter="handleAvatarEnter" @mouseleave="handleAvatarLeave">
        <button
          class="size-9 rounded-full bg-gradient-to-br from-blue-500 via-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white text-sm shadow-md shadow-blue-500/20 cursor-pointer hover:shadow-lg hover:shadow-blue-500/30 transition-all"
        >
          {{ avatarLetter }}
        </button>
        <div v-if="showUserMenu" @mouseenter="handleAvatarEnter" @mouseleave="handleAvatarLeave"
          class="absolute bottom-full left-full ml-1 mb-0 z-50">
          <UserMenu />
        </div>
      </div>
    </div>

    <!-- Collapsible Drawer (Session List) -->
    <div
      class="drawer flex-1 flex flex-col h-full overflow-hidden transition-all duration-300 ease-in-out border-r border-gray-200/60 dark:border-gray-700/40 relative"
      :class="isLeftPanelShow ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-full w-0 pointer-events-none absolute left-[60px]'"
    >
      <div class="absolute inset-0 bg-white dark:bg-[#1a1a1a] -z-10"></div>

      <!-- Drawer Header - Minimal style -->
      <div class="flex items-center px-4 pt-4 pb-1 flex-shrink-0">
        <h2 class="text-sm font-semibold text-gray-900 dark:text-gray-100">
          {{ isTasksActive ? t('Scheduled Tasks') : t('Chats') }}
        </h2>
        <span class="ml-2 text-xs text-gray-400 tabular-nums">
          {{ isTasksActive ? scheduledTasks.length : stats.all }}
        </span>
      </div>

      <!-- Search Bar (Chat mode only) - Minimal style -->
      <div v-if="!isTasksActive" class="px-3 mb-2 flex-shrink-0">
        <div class="relative">
          <Search :size="14" class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
          <input
            v-model="searchQuery"
            type="text"
            :placeholder="t('Search chats...')"
            class="w-full h-8 pl-8 pr-3 text-sm bg-gray-100/40 dark:bg-white/5 border-0 border-b border-gray-200/40 dark:border-gray-700/30 rounded-none text-gray-700 dark:text-gray-200 placeholder-gray-400 focus:outline-none focus:border-blue-400/50 focus:bg-transparent transition-all"
          />
          <button
            v-if="searchQuery"
            @click="searchQuery = ''"
            class="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-gray-600"
          >
            <X :size="12" />
          </button>
        </div>
      </div>

      <!-- Filter Tabs (Chat mode only) -->
      <div v-if="!isTasksActive" class="px-3 mb-1 flex-shrink-0">
        <div class="filter-tabs flex gap-1 overflow-x-auto pb-1.5 scrollbar-hide">
          <button
            v-for="tab in filterTabs"
            :key="tab.key"
            @click="setFilter(tab.key)"
            class="filter-tab flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium whitespace-nowrap transition-all duration-150"
            :class="activeFilter === tab.key
              ? 'bg-blue-500 dark:bg-blue-600 text-white'
              : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'"
          >
            <component :is="tab.icon" :size="12" />
            <span>{{ tab.label }}</span>
            <span v-if="tab.count > 0"
              class="text-[10px] px-1 rounded"
              :class="activeFilter === tab.key
                ? 'bg-white/20 text-white'
                : 'bg-gray-200/80 dark:bg-gray-700/80 text-gray-600 dark:text-gray-300'">
              {{ tab.count }}
            </span>
          </button>
        </div>
      </div>

      <!-- New Task / New Chat Button -->
      <div class="px-3 mb-2 flex-shrink-0">
        <button @click="isTasksActive ? handleNewScheduledTaskClick() : handleNewTaskClick()"
          class="new-task-btn flex w-full items-center justify-center gap-2 rounded-lg h-9 px-3 bg-gradient-to-r from-blue-400/90 to-indigo-500/90 dark:from-blue-500/80 dark:to-indigo-600/80 text-white font-medium text-sm cursor-pointer transition-all duration-150 hover:from-blue-500 hover:to-indigo-600 dark:hover:from-blue-500 dark:hover:to-indigo-600 hover:shadow-md hover:shadow-blue-400/20 active:scale-[0.98]">
          <Plus class="h-4 w-4 flex-shrink-0" />
          <span class="whitespace-nowrap truncate">
            {{ isTasksActive ? t('New Scheduled Task') : t('New Task') }}
          </span>
          <div v-if="!isTasksActive" class="flex items-center gap-0.5 ml-auto opacity-60">
            <Command :size="11" />
            <span class="text-xs">K</span>
          </div>
        </button>
      </div>

      <!-- Scheduled Tasks List (when Tasks tab active) -->
      <template v-if="isTasksActive">
        <div v-if="scheduledTasks.length > 0" class="session-list flex flex-col flex-1 min-h-0 overflow-auto pt-1 pb-5 overflow-x-hidden px-1.5">
          <button
            v-for="(task, idx) in scheduledTasks"
            :key="task.id"
            class="session-entry w-full text-left px-3 py-2.5 rounded-xl flex items-center gap-2 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            :style="{ animationDelay: `${idx * 30}ms` }"
            @click="router.push('/chat/tasks')"
          >
            <CalendarClock :size="16" class="text-sky-500 flex-shrink-0" />
            <span class="text-sm truncate flex-1">{{ task.name }}</span>
            <span v-if="task.status === 'disabled'" class="text-[10px] text-gray-400">已停用</span>
          </button>
        </div>
        <div v-else class="flex flex-1 flex-col items-center justify-center gap-3 px-6">
          <div class="size-16 rounded-2xl bg-gradient-to-br from-sky-100 to-teal-50 dark:from-sky-900/20 dark:to-teal-900/20 flex items-center justify-center">
            <CalendarClock :size="28" class="text-sky-500 dark:text-sky-400" />
          </div>
          <p class="text-sm font-medium text-gray-400 dark:text-gray-500">{{ t('No scheduled tasks yet') }}</p>
          <p class="text-xs text-gray-300 dark:text-gray-600">{{ t('Create a scheduled task to run AI at fixed times') }}</p>
        </div>
      </template>

      <!-- Session List with Grouping (when Chat tab active) -->
      <template v-else>
        <div v-if="groupedSessions.length > 0" class="session-list flex flex-col flex-1 min-h-0 overflow-auto py-2 overflow-x-hidden">
          <template v-for="group in groupedSessions" :key="group.key">
            <!-- Group Header - Minimal style -->
            <div
              @click="toggleGroupCollapse(group.key)"
              class="group-header flex items-center gap-1.5 px-4 py-2 cursor-pointer select-none transition-colors duration-150"
            >
              <ChevronRight
                :size="12"
                class="text-gray-400 dark:text-gray-500 transition-transform duration-200 flex-shrink-0"
                :class="{ 'rotate-90': !group.collapsed }"
              />
              <span class="text-[11px] font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wider">{{ t(group.label) }}</span>
              <span class="text-[10px] text-gray-300 dark:text-gray-600 tabular-nums ml-auto">
                {{ group.sessions.length }}
              </span>
            </div>

            <!-- Group Sessions -->
            <div v-show="!group.collapsed" class="px-1">
              <SessionItem
                v-for="session in group.sessions"
                :key="session.session_id"
                :session="session"
                class="session-entry"
                @deleted="handleSessionDeleted"
                @updated="handleSessionUpdated"
              />
            </div>
          </template>
        </div>

        <!-- Empty State - Minimal style -->
        <div v-else class="flex flex-1 flex-col items-center justify-center gap-2 px-6 py-8">
          <div class="size-12 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-2">
            <MessageSquareDashed :size="20" class="text-gray-400 dark:text-gray-500" />
          </div>
          <p class="text-sm text-gray-500 dark:text-gray-400 text-center">
            {{ searchQuery ? t('No matching chats found') : t('Create a task to get started') }}
          </p>
          <p v-if="!searchQuery" class="text-xs text-gray-400 dark:text-gray-500">
            <kbd class="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-[10px]">⌘</kbd>
            <kbd class="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-[10px] ml-0.5">K</kbd>
          </p>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  Plus, Command, MessageSquareDashed, Blocks, MessageSquare,
  Wrench, CalendarClock, Settings2, Search, X, ChevronRight, Pin,
  Play
} from 'lucide-vue-next';
import SessionItem from './SessionItem.vue';
import UserMenu from './UserMenu.vue';
import { useLeftPanel } from '../composables/useLeftPanel';
import { useSessionGrouping, type FilterType } from '../composables/useSessionGrouping';
import { useSessionListUpdate } from '../composables/useSessionListUpdate';
import { useSessionNotifications } from '../composables/useSessionNotifications';
import { useSettingsDialog } from '../composables/useSettingsDialog';
import { useAuth } from '../composables/useAuth';
import { ref, onMounted, watch, onUnmounted, computed, markRaw } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { listSessions } from '../api/agent';
import { listTasks } from '../api/tasks';
import { ListSessionItem } from '../types/response';
import type { Task } from '../api/tasks';
import { useI18n } from 'vue-i18n';

const { t } = useI18n()
const { isLeftPanelShow, toggleLeftPanel } = useLeftPanel()
const { setOnSessionTitleUpdate } = useSessionListUpdate()
const { onSessionCreated, onSessionUpdated } = useSessionNotifications()
const { openSettingsDialog } = useSettingsDialog()
const { currentUser } = useAuth()

const showUserMenu = ref(false)
let avatarLeaveTimer: ReturnType<typeof setTimeout> | null = null
const avatarLetter = computed(() => currentUser.value?.fullname?.charAt(0)?.toUpperCase() || 'U')
function clearAvatarTimer() {
  if (avatarLeaveTimer) { clearTimeout(avatarLeaveTimer); avatarLeaveTimer = null; }
}
function handleAvatarEnter() {
  clearAvatarTimer()
  showUserMenu.value = true
}
function handleAvatarLeave() {
  clearAvatarTimer()
  avatarLeaveTimer = setTimeout(() => { showUserMenu.value = false }, 200)
}
const route = useRoute()
const router = useRouter()

const sessions = ref<ListSessionItem[]>([])
const scheduledTasks = ref<Task[]>([])

// 使用会话分组 composable
const {
  activeFilter,
  searchQuery,
  groupedSessions,
  stats,
  toggleGroupCollapse,
  setFilter,
} = useSessionGrouping(sessions)

// 筛选标签配置
const filterTabs = computed(() => [
  {
    key: 'all' as FilterType,
    label: t('All'),
    icon: markRaw(MessageSquare),
    count: stats.value.all,
  },
  {
    key: 'pinned' as FilterType,
    label: t('Pinned'),
    icon: markRaw(Pin),
    count: stats.value.pinned,
  },
  {
    key: 'running' as FilterType,
    label: t('Running'),
    icon: markRaw(Play),
    count: stats.value.running,
  },
])

// Navigation State
const isChatActive = computed(() => route.path === '/' || route.path.startsWith('/chat/session') || (route.path.startsWith('/chat') && !route.path.includes('skills') && !route.path.includes('tools') && !route.path.startsWith('/chat/tasks')))
const isSkillsActive = computed(() => route.path.includes('/chat/skills'))
const isToolsActive = computed(() => route.path.includes('/chat/tools') && !route.path.startsWith('/chat/tasks'))
const isTasksActive = computed(() => route.path.startsWith('/chat/tasks'))

const handleChatTabClick = () => {
  if (isChatActive.value && isLeftPanelShow.value) {
     toggleLeftPanel()
     return
  }

  if (!isLeftPanelShow.value) {
     toggleLeftPanel()
  }

  if (!isChatActive.value) {
      router.push('/')
  }
}

const handleSkillsTabClick = () => {
  if (isLeftPanelShow.value) {
    toggleLeftPanel()
  }
  router.push('/chat/skills')
}

const handleToolsTabClick = () => {
  if (isLeftPanelShow.value) {
    toggleLeftPanel()
  }
  router.push('/chat/tools')
}

const handleTasksTabClick = () => {
  if (isLeftPanelShow.value) {
    toggleLeftPanel()
  }
  router.push('/chat/tasks')
  fetchScheduledTasks()
}

const handleNewScheduledTaskClick = () => {
  router.push('/chat/tasks')
}

const fetchScheduledTasks = async () => {
  try {
    scheduledTasks.value = await listTasks()
  } catch (e) {
    console.error('Failed to fetch scheduled tasks:', e)
    scheduledTasks.value = []
  }
}

// Function to fetch sessions data
const updateSessions = async () => {
  try {
    const response = await listSessions()
    sessions.value = response
  } catch (error) {
    console.error('Failed to fetch sessions:', error)
  }
}

const handleNewTaskClick = () => {
  router.push('/')
}

const handleSessionDeleted = (sessionId: string) => {
  sessions.value = sessions.value.filter(session => session.session_id !== sessionId);
}

const handleSessionUpdated = (updatedSession: ListSessionItem) => {
  const index = sessions.value.findIndex(s => s.session_id === updatedSession.session_id)
  if (index !== -1) {
    sessions.value[index] = updatedSession
  }
}

// Handle keyboard shortcuts
const handleKeydown = (event: KeyboardEvent) => {
  if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
    event.preventDefault()
    handleNewTaskClick()
  }
}

let _refreshTimer: ReturnType<typeof setTimeout> | null = null
const debouncedRefresh = () => {
  if (_refreshTimer) clearTimeout(_refreshTimer)
  _refreshTimer = setTimeout(() => updateSessions(), 500)
}

onMounted(async () => {
  updateSessions()

  setOnSessionTitleUpdate((sessionId: string, title: string) => {
    const s = sessions.value.find((x) => x.session_id === sessionId)
    if (s) s.title = title
  })

  onSessionCreated(debouncedRefresh)
  onSessionUpdated(debouncedRefresh)

  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  setOnSessionTitleUpdate(null)
  window.removeEventListener('keydown', handleKeydown)
})

watch(() => route.path, async (newPath, oldPath) => {
  const wasChatSession = oldPath?.startsWith('/chat/') && !oldPath.includes('skills') && !oldPath.includes('tools') && !oldPath.startsWith('/chat/tasks')
  const isChatSession = newPath?.startsWith('/chat/') && !newPath.includes('skills') && !newPath.includes('tools') && !newPath.startsWith('/chat/tasks')
  if (!(wasChatSession && isChatSession)) {
    await updateSessions()
  }
  if (isTasksActive.value) {
    await fetchScheduledTasks()
  }
})
</script>

<style scoped>
.nav-btn {
  position: relative;
}
.nav-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 0.75rem;
  opacity: 0;
  background: radial-gradient(circle at center, rgba(99,102,241,0.08) 0%, transparent 70%);
  transition: opacity 0.2s;
}
.nav-btn:hover::before {
  opacity: 1;
}

.new-task-btn {
  position: relative;
}

@keyframes sessionFadeIn {
  from { opacity: 0; transform: translateY(-4px); }
  to   { opacity: 1; transform: translateY(0); }
}
.session-entry {
  animation: sessionFadeIn 0.2s ease-out both;
}

.session-list {
  scrollbar-width: thin;
  scrollbar-color: rgba(0,0,0,0.1) transparent;
}
.session-list::-webkit-scrollbar {
  width: 4px;
}
.session-list::-webkit-scrollbar-track {
  background: transparent;
}
.session-list::-webkit-scrollbar-thumb {
  background: rgba(0,0,0,0.1);
  border-radius: 4px;
}
.session-list:hover::-webkit-scrollbar-thumb {
  background: rgba(0,0,0,0.2);
}

/* Dark mode scrollbar */
:deep(.dark) .session-list {
  scrollbar-color: rgba(255,255,255,0.15) transparent;
}
:deep(.dark) .session-list::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.15);
}
:deep(.dark) .session-list:hover::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.25);
}

.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.scrollbar-hide::-webkit-scrollbar {
  display: none;
}

.scrollbar-thin {
  scrollbar-width: thin;
  scrollbar-color: rgba(0,0,0,0.15) transparent;
}
.scrollbar-thin::-webkit-scrollbar {
  height: 4px;
}
.scrollbar-thin::-webkit-scrollbar-track {
  background: transparent;
}
.scrollbar-thin::-webkit-scrollbar-thumb {
  background: rgba(0,0,0,0.15);
  border-radius: 4px;
}
.scrollbar-thin:hover::-webkit-scrollbar-thumb {
  background: rgba(0,0,0,0.25);
}

.group-header {
  user-select: none;
}

.group-header:hover {
  background: rgba(0, 0, 0, 0.02);
}

:deep(.dark) .group-header:hover {
  background: rgba(255, 255, 255, 0.05);
}
</style>
