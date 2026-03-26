<template>
  <div class="flex flex-col h-full w-full overflow-hidden bg-[#f8f9fb] dark:bg-[#111] tasks-page-teal">

    <!-- ====== Hero Header ====== -->
    <div class="flex-shrink-0 relative overflow-hidden">
      <div class="absolute inset-0 bg-gradient-to-br from-sky-400 via-teal-400 to-cyan-500"></div>
      <div class="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNCI+PHBhdGggZD0iTTM2IDM0djZoLTZ2LTZoNnptMC0zMHY2aC02VjRoNnoiLz48L2c+PC9nPjwvc3ZnPg==')] opacity-50"></div>
      <div class="relative px-6 py-4">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-lg font-bold text-white flex items-center gap-2">
              <span class="inline-flex items-center justify-center size-7 rounded-lg bg-white/15 backdrop-blur-sm">
                <CalendarClock :size="14" class="text-white" />
              </span>
              {{ t('Scheduled Tasks') }}
            </h1>
            <p class="text-white/60 text-xs mt-0.5">{{ t('task header summary', { count: tasks.length }) }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- ====== Empty state: no tasks ====== -->
    <div v-if="showEmptyState" class="flex-1 flex flex-col items-center justify-center text-center px-6">
      <div class="size-20 rounded-3xl bg-sky-50 dark:bg-sky-900/20 flex items-center justify-center mb-5">
        <CalendarClock :size="36" class="text-sky-400" />
      </div>
      <h2 class="text-lg font-semibold text-[var(--text-primary)] mb-2">{{ t('No scheduled tasks yet') }}</h2>
      <p class="text-sm text-[var(--text-tertiary)] mb-6 max-w-xs">{{ t('Create a scheduled task to automate your workflows') }}</p>
      <button @click="handleNewTask"
        class="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-br from-sky-400 to-teal-500 text-white text-sm font-medium hover:shadow-lg hover:shadow-sky-400/25 transition-all">
        <Plus :size="16" />
        {{ t('New Scheduled Task') }}
      </button>
    </div>

    <!-- ====== Loading state ====== -->
    <div v-else-if="listLoading && tasks.length === 0 && !isCreating" class="flex-1 flex items-center justify-center">
      <div class="animate-pulse text-[var(--text-tertiary)] text-sm">{{ t('Loading...') }}</div>
    </div>

    <!-- ====== Service unavailable state ====== -->
    <div v-else-if="serviceUnavailable && tasks.length === 0 && !isCreating" class="flex-1 flex flex-col items-center justify-center text-center px-6">
      <AlertCircle :size="32" class="text-red-400 mb-3" />
      <p class="text-sm text-[var(--text-tertiary)]">{{ t('Task service is not available') }}</p>
    </div>

    <!-- ====== Three-column layout ====== -->
    <div v-else class="flex flex-1 min-h-0 overflow-hidden">

    <!-- ====== Column 1: Task List ====== -->
    <div class="flex flex-col w-[220px] flex-shrink-0 border-r border-gray-200/60 dark:border-gray-700/40 bg-white dark:bg-[#1a1a1a]">
      <!-- New task button + Search -->
      <div class="flex-shrink-0 px-3 pt-3 pb-2 space-y-2">
        <button @click="handleNewTask"
          class="w-full flex items-center gap-2 px-2 py-1.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
          <Plus :size="16" class="text-[var(--text-tertiary)]" />
          {{ t('New Task') }}
        </button>
        <div class="relative">
          <Search :size="13" class="absolute left-2 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)] pointer-events-none" />
          <input v-model="taskSearchQuery" type="text"
            class="w-full pl-7 pr-2 py-1 bg-transparent border-0 border-b border-gray-200 dark:border-gray-700 text-xs text-[var(--text-primary)] placeholder-[var(--text-tertiary)] focus:outline-none focus:border-sky-400 dark:focus:border-sky-400 transition-colors"
            :placeholder="t('Search tasks...')" />
        </div>
      </div>

      <!-- List -->
      <div class="flex-1 overflow-y-auto px-2 pb-2">
        <div v-if="listLoading" class="space-y-2 px-1">
          <div v-for="i in 4" :key="i" class="h-12 rounded-lg bg-gray-100 dark:bg-gray-800 animate-pulse"></div>
        </div>
        <div v-else-if="serviceUnavailable" class="flex flex-col items-center py-10 text-center px-3">
          <AlertCircle :size="22" class="text-red-400 mb-2" />
          <p class="text-[11px] text-[var(--text-tertiary)]">{{ t('Task service is not available') }}</p>
        </div>
        <div v-else-if="tasks.length === 0 && !isCreating" class="flex flex-col items-center py-12 text-center px-3">
          <CalendarClock :size="24" class="text-[var(--text-tertiary)] mb-2" />
          <p class="text-[11px] text-[var(--text-tertiary)]">{{ t('No scheduled tasks yet') }}</p>
        </div>
        <div v-else class="space-y-0.5">
          <!-- New task placeholder -->
          <div v-if="isCreating"
            class="flex items-center gap-2 px-2.5 py-2 rounded-lg border border-sky-100 dark:border-sky-800/50 bg-sky-50 dark:bg-sky-900/20">
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-1.5">
                <span class="text-[13px] font-medium text-sky-700 dark:text-sky-300 truncate">
                  {{ form.name || t('New Task') }}
                </span>
                <span class="size-1.5 rounded-full flex-shrink-0 bg-gray-300 dark:bg-gray-600"></span>
              </div>
              <p class="text-[10px] text-sky-500 dark:text-sky-400 truncate mt-0.5">{{ t('Configuring...') }}</p>
            </div>
          </div>
          <div
            v-for="task in filteredTasks" :key="task.id"
            class="flex items-center gap-1 px-2.5 py-2 rounded-lg cursor-pointer transition-all duration-150 group/item"
            :class="selectedTaskId === task.id
              ? 'bg-sky-50 dark:bg-sky-900/20 border border-sky-100 dark:border-sky-800/50'
              : 'hover:bg-gray-50 dark:hover:bg-gray-800/50 border border-transparent'"
          >
            <div class="min-w-0 flex-1" @click="selectTask(task)">
              <div class="flex items-center gap-1.5">
                <span class="size-1.5 rounded-full flex-shrink-0"
                  :class="task.status === 'enabled' ? 'bg-emerald-500' : 'bg-gray-300 dark:bg-gray-600'"></span>
                <span class="text-[13px] font-medium truncate"
                  :class="selectedTaskId === task.id ? 'text-sky-700 dark:text-sky-300' : 'text-[var(--text-primary)]'">
                  {{ task.name }}
                </span>
              </div>
              <p class="text-[10px] text-[var(--text-tertiary)] truncate mt-0.5">{{ task.schedule_desc || task.crontab }}</p>
            </div>
            <!-- Three-dot menu -->
            <div class="relative flex-shrink-0" :ref="el => setMenuRef(task.id, el as HTMLElement)">
              <button @click.stop="toggleTaskMenu(task.id)"
                class="size-6 rounded-md flex items-center justify-center text-[var(--text-tertiary)] opacity-0 group-hover/item:opacity-100 hover:bg-gray-200 dark:hover:bg-gray-700 transition-all"
                :class="{ '!opacity-100': taskMenuOpenId === task.id || selectedTaskId === task.id }">
                <MoreVertical :size="14" />
              </button>
              <Transition name="slide-fade">
                <div v-if="taskMenuOpenId === task.id"
                  class="absolute right-0 top-full mt-1 z-20 w-28 bg-white dark:bg-[#1e1e1e] border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg overflow-hidden">
                  <button @click.stop="toggleStatusFromMenu(task)"
                    class="w-full text-left px-3 py-2 text-xs hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                    :class="task.status === 'enabled' ? 'text-slate-600 dark:text-slate-400' : 'text-emerald-600 dark:text-emerald-400'">
                    {{ task.status === 'enabled' ? t('Disable') : t('Enable') }}
                  </button>
                  <button @click.stop="deleteFromMenu(task)"
                    class="w-full text-left px-3 py-2 text-xs text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                    {{ t('Delete') }}
                  </button>
                </div>
              </Transition>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ====== Column 2: Task Detail / Config ====== -->
    <div class="flex flex-col w-[360px] flex-shrink-0 min-w-0 border-r border-gray-200/60 dark:border-gray-700/40">
      <div v-if="!selectedTaskId && !isCreating" class="flex-1 flex flex-col items-center justify-center text-center px-6">
        <div class="size-14 rounded-2xl bg-sky-50 dark:bg-sky-900/20 flex items-center justify-center mb-3">
          <CalendarClock :size="24" class="text-sky-400" />
        </div>
        <p class="text-[var(--text-tertiary)] text-xs">{{ t('Select a task or create a new one') }}</p>
      </div>

      <template v-else>
        <div class="flex items-center px-4 py-3 border-b border-gray-100 dark:border-gray-800 bg-white dark:bg-[#1a1a1a] flex-shrink-0">
          <h3 class="text-sm font-semibold text-[var(--text-primary)]">
            {{ isCreating ? t('New Scheduled Task') : t('Task Detail') }}
          </h3>
        </div>

        <div class="flex-1 overflow-y-auto p-4">
          <div v-if="configLoading" class="flex justify-center py-16">
            <div class="animate-pulse text-[var(--text-tertiary)]">{{ t('Loading...') }}</div>
          </div>

          <form v-else @submit.prevent="submit" class="space-y-4">
            <div>
              <label class="block text-[11px] font-medium text-[var(--text-tertiary)] mb-1">{{ t('Task name') }}</label>
              <input v-model="form.name" type="text" required
                class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#1e1e1e] text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-sky-400/30 focus:border-sky-400 transition-colors"
                :placeholder="t('e.g. Daily AI News')" />
            </div>

            <!-- Model selector -->
            <div ref="modelDropdownRef">
              <label class="block text-[11px] font-medium text-[var(--text-tertiary)] mb-1">{{ t('Model') }}</label>
              <div class="relative">
                <button type="button" @click="modelDropdownOpen = !modelDropdownOpen"
                  class="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#1e1e1e] text-sm text-[var(--text-primary)] hover:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-400/30 focus:border-sky-400 transition-colors">
                  <template v-if="selectedModel">
                    <ProviderIcon :provider="selectedModel.provider" class="size-4 flex-shrink-0" />
                    <span class="flex-1 text-left truncate">{{ modelDisplayName(selectedModel) }}</span>
                    <span class="text-[10px] text-[var(--text-tertiary)]">{{ selectedModel.provider }}</span>
                  </template>
                  <template v-else>
                    <span class="flex-1 text-left text-[var(--text-tertiary)]">{{ t('Select model') }}</span>
                  </template>
                  <ChevronDown :size="14" class="flex-shrink-0 text-[var(--text-tertiary)]" />
                </button>
                <Transition name="slide-fade">
                  <div v-if="modelDropdownOpen"
                    class="absolute z-20 left-0 right-0 mt-1 bg-white dark:bg-[#1e1e1e] border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg overflow-hidden">
                    <div class="bg-[#f8f9fb] dark:bg-[#111] px-3 py-1.5 border-b border-gray-100 dark:border-gray-800">
                      <span class="text-[10px] font-medium text-[var(--text-tertiary)]">Select Model</span>
                    </div>
                    <div class="flex flex-col max-h-[240px] overflow-y-auto p-1">
                      <button v-for="model in models" :key="model.id" type="button"
                        @click="selectTaskModel(model.id)"
                        class="flex items-center gap-2.5 w-full px-2.5 py-2 rounded-md text-left transition-colors"
                        :class="form.model_config_id === model.id ? 'bg-sky-50 dark:bg-sky-900/20' : 'hover:bg-gray-50 dark:hover:bg-gray-800/50'">
                        <ProviderIcon :provider="model.provider" class="size-4 flex-shrink-0" />
                        <div class="flex-1 min-w-0">
                          <span class="text-xs font-medium text-[var(--text-primary)] truncate block">{{ modelDisplayName(model) }}</span>
                          <span class="text-[10px] text-[var(--text-tertiary)] truncate block">{{ model.provider }}</span>
                        </div>
                        <CheckCircle2 v-if="form.model_config_id === model.id" :size="14" class="flex-shrink-0 text-sky-500" />
                      </button>
                      <div v-if="models.length === 0" class="px-3 py-4 text-center text-[11px] text-[var(--text-tertiary)]">
                        {{ t('No models configured') }}
                      </div>
                    </div>
                  </div>
                </Transition>
              </div>
            </div>

            <div ref="scheduleComboRef">
              <label class="block text-[11px] font-medium text-[var(--text-tertiary)] mb-1">{{ t('Schedule') }}</label>
              <div class="relative">
                <input v-model="form.schedule_desc" type="text" required autocomplete="off" readonly
                  @click="openSchedulePanel"
                  class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#1e1e1e] text-sm text-[var(--text-primary)] cursor-pointer focus:outline-none focus:ring-2 focus:ring-sky-400/30 focus:border-sky-400 transition-colors"
                  :class="{ 'focus:border-red-400 dark:focus:border-red-500': scheduleError, 'focus:border-emerald-400 dark:focus:border-emerald-500': scheduleVerified }"
                  :placeholder="t('e.g. Every day at 9am')" />
                <CheckCircle2 v-if="scheduleVerified" :size="14" class="absolute right-2.5 top-1/2 -translate-y-1/2 text-emerald-500" />
              </div>
              <p v-if="scheduleError && !scheduleDropdownOpen" class="text-[11px] text-red-500 mt-1 flex items-center gap-1">
                <AlertCircle :size="11" /> {{ scheduleError }}
              </p>
              <p v-else-if="scheduleVerified" class="text-[11px] text-emerald-600 dark:text-emerald-400 mt-1 flex items-center gap-1">
                <CheckCircle2 :size="11" /> {{ t('Schedule verify success') }} {{ t('Next run time') }}：{{ scheduleVerifyNextRun?.replace(/\s*\(.*?\)\s*$/, '') }}
              </p>
              <Transition name="slide-fade">
                <div v-if="scheduleDropdownOpen" class="mt-2 bg-white dark:bg-[#1e1e1e] border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden shadow-sm">
                  <div v-if="scheduleSuggestions.length > 0" class="p-2.5 pb-1.5">
                    <p class="text-[10px] font-medium text-[var(--text-tertiary)] uppercase tracking-wider mb-1.5">{{ t('Recommended') }}</p>
                    <div v-for="(sug, i) in scheduleSuggestions" :key="'sug-' + i"
                      @click="pickScheduleSuggestion(sug)" @mouseenter="scheduleHighlight = i"
                      class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs cursor-pointer transition-colors mb-0.5"
                      :class="scheduleHighlight === i ? 'bg-sky-50 dark:bg-sky-900/20 text-sky-700 dark:text-sky-300' : 'text-[var(--text-primary)] hover:bg-gray-50 dark:hover:bg-gray-800'">
                      <Clock :size="12" class="flex-shrink-0 text-sky-400" /> {{ sug }}
                    </div>
                  </div>
                  <div class="border-t border-gray-100 dark:border-gray-800 mx-2.5"></div>
                  <div class="p-2.5">
                    <p class="text-[10px] font-medium text-[var(--text-tertiary)] uppercase tracking-wider mb-1.5">{{ t('Custom input') }}</p>
                    <div class="flex gap-1.5">
                      <input ref="scheduleCustomInputRef" v-model="scheduleCustomInput" type="text" autocomplete="off"
                        @keydown.enter.prevent="confirmCustomSchedule"
                        class="flex-1 min-w-0 px-2.5 py-1.5 rounded-md border border-gray-200 dark:border-gray-700 bg-[#f8f9fb] dark:bg-[#111] text-xs text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-sky-400/30 focus:border-sky-400"
                        :placeholder="t('e.g. Every day at 9am')" />
                      <button type="button" @click="confirmCustomSchedule" :disabled="!scheduleCustomInput?.trim()"
                        class="flex-shrink-0 px-3 py-1.5 rounded-md bg-gradient-to-r from-sky-400 to-teal-500 text-white text-xs font-medium disabled:opacity-50 transition-all">
                        {{ t('Confirm') }}
                      </button>
                    </div>
                  </div>
                </div>
              </Transition>
            </div>

            <div>
              <label class="block text-[11px] font-medium text-[var(--text-tertiary)] mb-1">{{ t('Prompt input') }}</label>
              <textarea v-model="form.prompt" required rows="8"
                class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#1e1e1e] text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-sky-400/30 focus:border-sky-400 resize-y transition-colors"
                :placeholder="t('The prompt sent to the model at scheduled time')" />
            </div>

            <div>
              <label class="block text-[11px] font-medium text-[var(--text-tertiary)] mb-1">{{ t('Notification webhooks') }}</label>
              <div v-if="selectedWebhooks.length > 0" class="space-y-1.5 mb-2">
                <div v-for="wh in selectedWebhooks" :key="wh.id"
                  class="flex items-center justify-between px-2.5 py-1.5 rounded-md bg-[#f8f9fb] dark:bg-[#111] border border-gray-200 dark:border-gray-700 text-xs">
                  <div class="flex items-center gap-1.5 min-w-0 flex-1">
                    <span class="px-1 py-0.5 rounded bg-gray-200 dark:bg-gray-700 text-[var(--text-tertiary)] text-[10px]">{{ webhookTypeLabel(wh.type) }}</span>
                    <span class="text-[var(--text-primary)] truncate">{{ wh.name }}</span>
                  </div>
                  <button type="button" @click="removeWebhook(wh.id)" class="p-0.5 rounded text-[var(--text-tertiary)] hover:text-red-500 transition-colors">
                    <X :size="12" />
                  </button>
                </div>
              </div>
              <div class="relative" ref="webhookDropdownRef">
                <button type="button" @click="toggleWebhookDropdown"
                  class="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg border border-dashed border-gray-300 dark:border-gray-600 text-[var(--text-secondary)] hover:border-sky-400 hover:text-sky-500 dark:hover:text-sky-400 transition-colors text-xs">
                  <Plus :size="14" /> {{ t('Add webhook') }}
                </button>
                <Transition name="slide-fade">
                  <div v-if="webhookDropdownOpen"
                    class="absolute z-10 left-0 right-0 mt-1 bg-white dark:bg-[#1e1e1e] border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg overflow-hidden max-h-[200px] overflow-y-auto">
                    <template v-if="availableWebhooks.length > 0">
                      <div v-for="wh in availableWebhooks" :key="wh.id" @click="addWebhook(wh.id)"
                        class="flex items-center gap-1.5 px-2.5 py-2 text-xs cursor-pointer hover:bg-sky-50 dark:hover:bg-sky-900/20 transition-colors">
                        <span class="px-1 py-0.5 rounded bg-gray-200 dark:bg-gray-700 text-[var(--text-tertiary)] text-[10px]">{{ webhookTypeLabel(wh.type) }}</span>
                        <span class="text-[var(--text-primary)] truncate">{{ wh.name }}</span>
                      </div>
                    </template>
                    <div class="border-t border-gray-100 dark:border-gray-800">
                      <button type="button" @click="openNotificationSettings"
                        class="w-full flex items-center gap-1.5 px-2.5 py-2 text-xs text-sky-600 dark:text-sky-400 hover:bg-sky-50 dark:hover:bg-sky-900/20 transition-colors">
                        <Settings2 :size="12" /> {{ t('Manage webhooks in Settings') }}
                      </button>
                    </div>
                  </div>
                </Transition>
              </div>
            </div>

            <!-- Notification events -->
            <div>
              <label class="block text-[11px] font-medium text-[var(--text-tertiary)] mb-2">{{ t('Notification events') }}</label>
              <div class="space-y-2">
                <label class="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked disabled
                    class="size-3.5 rounded border-gray-300 accent-sky-400 cursor-not-allowed opacity-60" />
                  <span class="text-xs text-[var(--text-secondary)]">{{ t('Notify on finish') }}</span>
                </label>
                <label class="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox"
                    :checked="form.event_config.includes('notify_on_start')"
                    @change="toggleEventConfig('notify_on_start')"
                    class="size-3.5 rounded border-gray-300 accent-sky-400 cursor-pointer" />
                  <span class="text-xs text-[var(--text-secondary)]">{{ t('Notify on start') }}</span>
                </label>
              </div>
            </div>

            <!-- Save: only show when form is dirty (or creating) -->
            <Transition name="slide-fade">
              <div v-if="isCreating || formDirty" class="flex items-center gap-2 pt-1">
                <button type="submit" :disabled="saving"
                  class="px-5 py-2 rounded-lg bg-gradient-to-r from-sky-400 to-teal-500 text-white text-sm font-medium hover:shadow-lg hover:shadow-sky-400/25 disabled:opacity-50 transition-all">
                  {{ saving ? t('Saving...') : t('Save') }}
                </button>
                <button v-if="isCreating" type="button" @click="cancelCreate"
                  class="px-5 py-2 rounded-lg bg-gray-100 dark:bg-gray-800 text-[var(--text-secondary)] text-sm hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors">
                  {{ t('Cancel') }}
                </button>
              </div>
            </Transition>
          </form>
        </div>
      </template>
    </div>

    <!-- ====== Column 3: Execution History ====== -->
    <div class="flex flex-col flex-1 min-w-0 bg-white dark:bg-[#1a1a1a]">
      <div v-if="!selectedTaskId || isCreating" class="flex-1 flex flex-col items-center justify-center text-center px-6">
        <Activity :size="24" class="text-[var(--text-tertiary)] mb-2" />
        <p class="text-xs text-[var(--text-tertiary)]">{{ t('Select a task to view runs') }}</p>
      </div>

      <template v-else>
        <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800 flex-shrink-0">
          <div class="flex items-center gap-3">
            <h3 class="text-sm font-semibold text-[var(--text-primary)]">{{ t('Run history') }}</h3>
            <span v-if="currentTask?.next_run && currentTask?.status === 'enabled'" class="text-xs font-medium text-[var(--text-tertiary)]">
              {{ t('Next run time') }}：{{ currentTask.next_run?.replace(/\s*\(.*?\)\s*$/, '') }}
            </span>
            <span v-if="countdownDisplay && currentTask?.status === 'enabled'" class="text-xs font-medium text-[var(--text-tertiary)]">
              {{ t('Countdown') }}：{{ countdownDisplay }}
            </span>
          </div>
          <button @click="refreshRuns" :disabled="runsLoading"
            class="p-1.5 rounded-lg text-[var(--text-tertiary)] hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-[var(--text-primary)] disabled:opacity-40 transition-colors"
            :title="t('Refresh')">
            <RefreshCw :size="14" :class="runsLoading ? 'animate-spin' : ''" />
          </button>
        </div>

        <div class="flex-1 overflow-y-auto" ref="runsScrollRef" @scroll="onRunsScroll">
          <div v-if="runsLoading && taskRuns.length === 0" class="flex justify-center py-10">
            <div class="animate-pulse text-[var(--text-tertiary)] text-xs">{{ t('Loading...') }}</div>
          </div>

          <div v-else-if="taskRuns.length === 0" class="flex flex-col items-center py-12 text-center px-4">
            <p class="text-xs text-[var(--text-tertiary)]">{{ t('No runs yet') }}</p>
          </div>

          <table class="w-full text-xs">
            <thead class="sticky top-0 bg-white dark:bg-[#1a1a1a] z-[1]">
              <tr class="text-[var(--text-tertiary)] border-b border-gray-100 dark:border-gray-800">
                <th class="text-left font-medium px-4 py-2">{{ t('Status') }}</th>
                <th class="text-left font-medium px-2 py-2">{{ t('Start time') }}</th>
                <th class="text-left font-medium px-2 py-2">{{ t('End time') }}</th>
                <th class="text-left font-medium px-2 py-2">{{ t('Duration') }}</th>
                <th class="text-right font-medium px-4 py-2">{{ t('Actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="run in taskRuns" :key="run.id"
                class="border-b border-gray-50 dark:border-gray-800/50 hover:bg-gray-50/50 dark:hover:bg-gray-800/20 transition-colors">
                <td class="px-4 py-2.5">
                  <span class="inline-flex items-center gap-1.5">
                    <span class="size-1.5 rounded-full" :class="runStatusDotClass(run.status)"></span>
                    <span class="font-medium" :class="runStatusTextClass(run.status)">
                      {{ runStatusLabel(run.status) }}
                    </span>
                  </span>
                </td>
                <td class="px-2 py-2.5 text-[var(--text-secondary)] tabular-nums whitespace-nowrap">{{ formatTime(run.start_time) }}</td>
                <td class="px-2 py-2.5 text-[var(--text-secondary)] tabular-nums whitespace-nowrap">{{ formatTime(run.end_time) }}</td>
                <td class="px-2 py-2.5 text-[var(--text-tertiary)] tabular-nums whitespace-nowrap">{{ calcDuration(run.start_time, run.end_time) }}</td>
                <td class="px-4 py-2.5 text-right whitespace-nowrap">
                  <template v-if="run.chat_id">
                    <button @click="openRunChat(run)" class="text-sky-600 dark:text-sky-400 hover:underline mr-2">{{ t('View') }}</button>
                    <button @click="copyRunChatLink(run)" class="text-[var(--text-tertiary)] hover:text-sky-400 transition-colors">
                      <Share2 :size="12" class="inline" />
                    </button>
                  </template>
                  <template v-else-if="run.result || run.error">
                    <button @click="viewRunResult(run)" class="text-sky-600 dark:text-sky-400 hover:underline">{{ t('View') }}</button>
                  </template>
                  <span v-else class="text-[var(--text-tertiary)]">-</span>
                </td>
              </tr>
            </tbody>
          </table>

          <!-- Loading more indicator -->
          <div v-if="runsLoadingMore" class="py-3 text-center">
            <span class="text-[11px] text-[var(--text-tertiary)] animate-pulse">{{ t('Loading...') }}</span>
          </div>
        </div>
      </template>
    </div>

    </div><!-- end three-column layout -->

    <!-- Result dialog -->
    <Dialog :open="resultDialogContent !== null" @update:open="(v: boolean) => { if (!v) resultDialogContent = null }">
      <DialogContent class="w-[600px]">
        <DialogHeader class="px-6 pt-5 pb-4"><DialogTitle>{{ t('Result') }}</DialogTitle></DialogHeader>
        <pre class="overflow-auto px-6 pb-6 text-sm whitespace-pre-wrap text-[var(--text-secondary)] max-h-[60vh]">{{ resultDialogContent }}</pre>
      </DialogContent>
    </Dialog>

    <!-- Delete confirm dialog -->
    <Teleport to="body">
      <Transition name="confirm-overlay">
        <div v-if="confirmDeleteTask" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" @click.self="confirmDeleteTask = null">
          <Transition name="confirm-card" appear>
            <div class="w-[360px] bg-white dark:bg-[#1e1e1e] rounded-xl shadow-2xl border border-gray-200/60 dark:border-gray-700/50 overflow-hidden">
              <div class="px-6 pt-6 pb-4">
                <div class="flex items-center gap-3 mb-3">
                  <div class="size-10 rounded-xl bg-red-50 dark:bg-red-900/20 flex items-center justify-center flex-shrink-0">
                    <AlertCircle :size="20" class="text-red-500" />
                  </div>
                  <h3 class="text-[15px] font-semibold text-[var(--text-primary)]">{{ t('Delete Task') }}</h3>
                </div>
                <p class="text-sm text-[var(--text-secondary)] leading-relaxed">
                  {{ t('Are you sure you want to delete') }} <span class="font-medium text-[var(--text-primary)]">"{{ confirmDeleteTask?.name }}"</span>{{ t('? This action cannot be undone.') }}
                </p>
              </div>
              <div class="flex items-center justify-end gap-2 px-6 py-4 bg-gray-50 dark:bg-[#161616] border-t border-gray-100 dark:border-gray-800">
                <button @click="confirmDeleteTask = null"
                  class="px-4 py-2 text-sm rounded-lg text-[var(--text-secondary)] hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                  {{ t('Cancel') }}
                </button>
                <button @click="confirmAndDelete" :disabled="deleting"
                  class="px-4 py-2 text-sm rounded-lg bg-red-500 text-white hover:bg-red-600 disabled:opacity-50 transition-colors font-medium">
                  {{ deleting ? t('Deleting...') : t('Delete') }}
                </button>
              </div>
            </div>
          </Transition>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { CalendarClock, Plus, AlertCircle, Clock, CheckCircle2, X, Settings2, Activity, Share2, RefreshCw, MoreVertical, Search, ChevronDown } from 'lucide-vue-next';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { listTasks, getTask, createTask, updateTask, deleteTask, validateSchedule, listTaskRuns, listTaskRunsByOffset } from '@/api/tasks';
import { listWebhooks } from '@/api/webhooks';
import { listModels } from '@/api/models';
import type { ModelConfig } from '@/api/models';
import type { Task, TaskRun } from '@/api/tasks';
import type { Webhook } from '@/api/webhooks';
import { getAuthStatus } from '@/api/auth';
import { useSettingsDialog } from '@/composables/useSettingsDialog';
import { showSuccessToast, showErrorToast } from '@/utils/toast';
import ProviderIcon from '@/components/icons/ProviderIcon.vue';

const { t } = useI18n();
const { openSettingsDialog } = useSettingsDialog();

// ---- List state ----
const tasks = ref<Task[]>([]);
const listLoading = ref(true);
const serviceUnavailable = ref(false);
const selectedTaskId = ref<string | null>(null);
const isCreating = ref(false);

const currentTask = computed(() => tasks.value.find(tk => tk.id === selectedTaskId.value) ?? null);
const showEmptyState = computed(() => !listLoading.value && !serviceUnavailable.value && tasks.value.length === 0 && !isCreating.value);

const taskSearchQuery = ref('');
const filteredTasks = computed(() => {
  const q = taskSearchQuery.value.trim().toLowerCase();
  if (!q) return tasks.value;
  return tasks.value.filter(t => t.name.toLowerCase().includes(q)).slice(0, 50);
});

// Task list context menu
const taskMenuOpenId = ref<string | null>(null);
const menuRefs = new Map<string, HTMLElement>();
function setMenuRef(taskId: string, el: HTMLElement | null) {
  if (el) menuRefs.set(taskId, el);
  else menuRefs.delete(taskId);
}
function toggleTaskMenu(taskId: string) {
  taskMenuOpenId.value = taskMenuOpenId.value === taskId ? null : taskId;
}
async function toggleStatusFromMenu(task: Task) {
  taskMenuOpenId.value = null;
  try {
    await updateTask(task.id, { status: task.status === 'enabled' ? 'disabled' : 'enabled' });
    await loadTasks();
    if (selectedTaskId.value === task.id) {
      form.value.status = task.status === 'enabled' ? 'disabled' : 'enabled';
      snapshotForm();
    }
  } catch (e) { console.error(e); }
}
const confirmDeleteTask = ref<Task | null>(null);
const deleting = ref(false);
function deleteFromMenu(task: Task) {
  taskMenuOpenId.value = null;
  confirmDeleteTask.value = task;
}
async function confirmAndDelete() {
  if (!confirmDeleteTask.value) return;
  deleting.value = true;
  try {
    await deleteTask(confirmDeleteTask.value.id);
    if (selectedTaskId.value === confirmDeleteTask.value.id) selectedTaskId.value = null;
    await loadTasks();
  } catch (e) { console.error(e); }
  deleting.value = false;
  confirmDeleteTask.value = null;
}

// ---- Config form state ----
const form = ref({ name: '', prompt: '', schedule_desc: '', webhook: '', webhook_ids: [] as string[], event_config: [] as string[], model_config_id: '', status: 'enabled' });
const savedSnapshot = ref('');
const configLoading = ref(false);
const saving = ref(false);

const formDirty = computed(() => {
  if (isCreating.value) return true;
  return JSON.stringify({ name: form.value.name, prompt: form.value.prompt, schedule_desc: form.value.schedule_desc, webhook_ids: form.value.webhook_ids, event_config: form.value.event_config, model_config_id: form.value.model_config_id, status: form.value.status }) !== savedSnapshot.value;
});

function snapshotForm() {
  savedSnapshot.value = JSON.stringify({ name: form.value.name, prompt: form.value.prompt, schedule_desc: form.value.schedule_desc, webhook_ids: form.value.webhook_ids, event_config: form.value.event_config, model_config_id: form.value.model_config_id, status: form.value.status });
}

// ---- Model selector ----
const models = ref<ModelConfig[]>([]);
const modelDropdownOpen = ref(false);
const modelDropdownRef = ref<HTMLElement | null>(null);
const selectedModel = computed(() => models.value.find(m => m.id === form.value.model_config_id) ?? null);
function selectTaskModel(modelId: string) {
  form.value.model_config_id = modelId;
  modelDropdownOpen.value = false;
}
function modelDisplayName(m: ModelConfig) {
  return m.name.toLowerCase() === 'system' ? m.model_name : m.name;
}

// Schedule combo
const scheduleVerifying = ref(false);
const scheduleError = ref('');
const scheduleSuggestions = ref<string[]>([]);
const scheduleVerifyNextRun = ref('');
const scheduleVerified = ref(false);
const scheduleDropdownOpen = ref(false);
const scheduleHighlight = ref(-1);
const scheduleComboRef = ref<HTMLElement | null>(null);
const scheduleCustomInput = ref('');
const scheduleCustomInputRef = ref<HTMLInputElement | null>(null);

// Webhook multi-select
const allWebhooks = ref<Webhook[]>([]);
const webhookDropdownOpen = ref(false);
const webhookDropdownRef = ref<HTMLElement | null>(null);
const selectedWebhooks = computed(() => allWebhooks.value.filter(wh => form.value.webhook_ids.includes(wh.id)));
const availableWebhooks = computed(() => allWebhooks.value.filter(wh => !form.value.webhook_ids.includes(wh.id)));
const TYPE_LABELS: Record<string, string> = { feishu: '飞书', dingtalk: '钉钉', wecom: '企微', telegram: 'Telegram' };
const webhookTypeLabel = (tp: string) => TYPE_LABELS[tp] || tp;

// ---- Runs state (infinite scroll) ----
const taskRuns = ref<TaskRun[]>([]);
const runsTotal = ref(0);
const runsLoading = ref(false);
const runsLoadingMore = ref(false);
const runsHasMore = computed(() => taskRuns.value.length < runsTotal.value);
const runsScrollRef = ref<HTMLElement | null>(null);
const resultDialogContent = ref<string | null>(null);

const RUNS_INITIAL_LIMIT = 100;
const RUNS_LOAD_MORE = 20;

// ========== List actions ==========
async function loadTasks() {
  listLoading.value = true;
  serviceUnavailable.value = false;
  try { tasks.value = await listTasks(); }
  catch { tasks.value = []; serviceUnavailable.value = true; }
  finally { listLoading.value = false; }
}

function selectTask(task: Task) {
  isCreating.value = false;
  selectedTaskId.value = task.id;
  loadTaskConfig(task.id);
  loadRuns(task.id);
}

function handleNewTask() {
  isCreating.value = true;
  selectedTaskId.value = null;
  resetForm();
}

function cancelCreate() {
  isCreating.value = false;
  selectedTaskId.value = null;
}

// ========== Config actions ==========
function resetForm() {
  form.value = { name: '', prompt: '', schedule_desc: '', webhook: '', webhook_ids: [], event_config: [], model_config_id: models.value.length > 0 ? models.value[0].id : '', status: 'enabled' };
  savedSnapshot.value = '';
  scheduleError.value = '';
  scheduleSuggestions.value = [];
  scheduleVerifyNextRun.value = '';
  scheduleVerified.value = false;
  scheduleDropdownOpen.value = false;
}

async function loadTaskConfig(taskId: string) {
  configLoading.value = true;
  try {
    const task = await getTask(taskId);
    form.value = {
      name: task.name,
      prompt: task.prompt,
      schedule_desc: task.schedule_desc,
      webhook: task.webhook || '',
      webhook_ids: task.webhook_ids || [],
      event_config: task.event_config || [],
      model_config_id: task.model_config_id || '',
      status: task.status,
    };
    snapshotForm();
    scheduleError.value = '';
    scheduleVerified.value = false;
    scheduleDropdownOpen.value = false;
  } catch (e) { console.error(e); }
  finally { configLoading.value = false; }
}


async function submit() {
  scheduleError.value = '';
  saving.value = true;
  try {
    const auth = await getAuthStatus();
    const userId = auth.user?.id;
    const payload = {
      name: form.value.name,
      prompt: form.value.prompt,
      schedule_desc: form.value.schedule_desc,
      webhook: form.value.webhook || undefined,
      webhook_ids: form.value.webhook_ids,
      event_config: form.value.event_config,
      model_config_id: form.value.model_config_id || undefined,
      status: form.value.status,
      user_id: userId,
    };
    if (isCreating.value) {
      const created = await createTask(payload);
      isCreating.value = false;
      await loadTasks();
      selectedTaskId.value = created.id;
      snapshotForm();
      loadRuns(created.id);
      showSuccessToast(t('Task created'));
    } else if (selectedTaskId.value) {
      await updateTask(selectedTaskId.value, payload);
      await loadTasks();
      snapshotForm();
      showSuccessToast(t('Saved'));
    }
  } catch (e: any) {
    const status = e?.response?.status;
    const detail = e?.response?.data?.detail;
    if (status === 400 && isScheduleParseError(detail)) {
      handleScheduleValidationError(detail);
      return;
    }
    showErrorToast(typeof detail === 'string' ? detail : e?.message ?? t('Save failed'));
  } finally {
    saving.value = false;
  }
}

// ========== Schedule helpers ==========
function isScheduleParseError(detail: unknown): boolean {
  if (detail && typeof detail === 'object' && 'message' in (detail as object)) return true;
  const s = typeof detail === 'string' ? detail : String(detail ?? '');
  return /crontab|解析|配置|大模型|parse|schedule|定时|描述/i.test(s);
}

function openSchedulePanel() {
  scheduleCustomInput.value = form.value.schedule_desc || '';
  scheduleDropdownOpen.value = true;
  scheduleHighlight.value = -1;
  setTimeout(() => scheduleCustomInputRef.value?.focus(), 50);
}

async function confirmCustomSchedule() {
  const val = scheduleCustomInput.value?.trim();
  if (!val) return;
  form.value.schedule_desc = val;
  scheduleDropdownOpen.value = false;
  scheduleSuggestions.value = [];
  scheduleHighlight.value = -1;
  scheduleError.value = '';
  scheduleVerified.value = false;
  await verifyScheduleClick();
}

function handleScheduleValidationError(detail: unknown) {
  if (detail && typeof detail === 'object' && 'message' in (detail as object)) {
    scheduleError.value = (detail as { message?: string }).message ?? t('Schedule description invalid');
    const sugs = (detail as { suggestions?: string[] }).suggestions;
    scheduleSuggestions.value = Array.isArray(sugs) ? sugs.filter(s => s && s.trim()) : [];
  } else {
    scheduleError.value = typeof detail === 'string' ? detail : t('Schedule description invalid');
    scheduleSuggestions.value = [];
  }
  scheduleHighlight.value = 0;
  scheduleDropdownOpen.value = scheduleSuggestions.value.length > 0;
  scheduleVerified.value = false;
}

async function pickScheduleSuggestion(suggestion: string) {
  form.value.schedule_desc = suggestion;
  scheduleDropdownOpen.value = false;
  scheduleSuggestions.value = [];
  scheduleHighlight.value = -1;
  scheduleError.value = '';
  scheduleVerified.value = false;
  await verifyScheduleClick();
}

async function verifyScheduleClick() {
  const desc = form.value.schedule_desc?.trim();
  if (!desc) return;
  scheduleVerifying.value = true;
  scheduleError.value = '';
  scheduleVerifyNextRun.value = '';
  scheduleVerified.value = false;
  scheduleDropdownOpen.value = false;
  try {
    const res = await validateSchedule(desc, form.value.model_config_id || undefined);
    if (res.valid && res.next_run) {
      scheduleVerifyNextRun.value = res.next_run;
      scheduleVerified.value = true;
      scheduleSuggestions.value = [];
    }
  } catch (e: any) {
    handleScheduleValidationError(e?.response?.data?.detail);
  } finally {
    scheduleVerifying.value = false;
  }
}

// ========== Webhook helpers ==========
function toggleWebhookDropdown() { webhookDropdownOpen.value = !webhookDropdownOpen.value; }
function addWebhook(id: string) {
  if (!form.value.webhook_ids.includes(id)) form.value.webhook_ids.push(id);
  webhookDropdownOpen.value = false;
}
function removeWebhook(id: string) { form.value.webhook_ids = form.value.webhook_ids.filter(wid => wid !== id); }

function toggleEventConfig(key: string) {
  const idx = form.value.event_config.indexOf(key);
  if (idx >= 0) form.value.event_config.splice(idx, 1);
  else form.value.event_config.push(key);
}
function openNotificationSettings() { webhookDropdownOpen.value = false; openSettingsDialog('notifications'); }

// ========== Runs (infinite scroll) ==========
async function loadRuns(taskId: string) {
  taskRuns.value = [];
  runsTotal.value = 0;
  runsLoading.value = true;
  try {
    const { items, total } = await listTaskRuns(taskId, 1, RUNS_INITIAL_LIMIT);
    taskRuns.value = items;
    runsTotal.value = total;
  } catch {
    taskRuns.value = [];
    runsTotal.value = 0;
  } finally {
    runsLoading.value = false;
  }
}

function refreshRuns() {
  if (selectedTaskId.value) {
    loadRuns(selectedTaskId.value);
  }
}

// ========== Countdown to next run ==========
const countdownDisplay = ref('');
let countdownTimer: ReturnType<typeof setInterval> | null = null;

function parseNextRun(str: string | undefined): Date | null {
  if (!str) return null;
  const clean = str.replace(/\s*\(.*?\)\s*$/, '').trim();
  const m = clean.match(/^(\d{4})[/-](\d{2})[/-](\d{2})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?$/);
  if (!m) return null;
  const d = new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0));
  return isNaN(d.getTime()) ? null : d;
}

function tickCountdown() {
  const target = parseNextRun(currentTask.value?.next_run);
  if (!target) { countdownDisplay.value = ''; return; }
  const diff = Math.floor((target.getTime() - Date.now()) / 1000);
  if (diff <= 0) {
    countdownDisplay.value = '00:00:00';
    if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null; }
    setTimeout(async () => {
      refreshRuns();
      await loadTasks();
      startCountdown();
    }, 2000);
    return;
  }
  const h = Math.floor(diff / 3600);
  const m = Math.floor((diff % 3600) / 60);
  const s = diff % 60;
  const pad = (n: number) => String(n).padStart(2, '0');
  countdownDisplay.value = `${pad(h)}:${pad(m)}:${pad(s)}`;
}

function startCountdown() {
  if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null; }
  tickCountdown();
  if (countdownDisplay.value) {
    countdownTimer = setInterval(tickCountdown, 1000);
  }
}

function stopCountdown() {
  if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null; }
  countdownDisplay.value = '';
}

watch([() => selectedTaskId.value, () => currentTask.value?.next_run, () => currentTask.value?.status], ([tid, nr, status]) => {
  if (tid && nr && status === 'enabled') startCountdown(); else stopCountdown();
}, { immediate: true });

async function loadMoreRuns() {
  const tid = selectedTaskId.value;
  if (!tid || runsLoadingMore.value || !runsHasMore.value) return;
  runsLoadingMore.value = true;
  try {
    const offset = taskRuns.value.length;
    const { items, total } = await listTaskRunsByOffset(tid, offset, RUNS_LOAD_MORE);
    if (items.length > 0) {
      const existingIds = new Set(taskRuns.value.map(r => r.id));
      const newItems = items.filter(r => !existingIds.has(r.id));
      taskRuns.value.push(...newItems);
    }
    runsTotal.value = total;
  } catch { /* ignore */ }
  finally { runsLoadingMore.value = false; }
}

function onRunsScroll() {
  const el = runsScrollRef.value;
  if (!el || !runsHasMore.value || runsLoadingMore.value) return;
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 40) {
    loadMoreRuns();
  }
}

// ========== Run status helpers ==========
function runStatusDotClass(status: string): string {
  switch (status) {
    case 'success': return 'bg-emerald-500';
    case 'running': return 'bg-sky-400 animate-pulse';
    case 'pending': return 'bg-amber-400 animate-pulse';
    default: return 'bg-red-500';
  }
}
function runStatusTextClass(status: string): string {
  switch (status) {
    case 'success': return 'text-emerald-600 dark:text-emerald-400';
    case 'running': return 'text-sky-600 dark:text-sky-400';
    case 'pending': return 'text-amber-600 dark:text-amber-400';
    default: return 'text-red-600 dark:text-red-400';
  }
}
function runStatusLabel(status: string): string {
  switch (status) {
    case 'success': return t('Success');
    case 'running': return t('Running');
    case 'pending': return t('Pending');
    default: return t('Failed');
  }
}

const displayTimezone = (import.meta as any).env?.VITE_DISPLAY_TIMEZONE || 'Asia/Shanghai';
function formatTime(iso?: string) {
  if (!iso) return '-';
  try {
    let s = String(iso).trim();
    if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(s) && !/Z|[+-]\d{2}:?\d{2}$/.test(s)) s = s.replace(/\.\d{3}$/, '') + 'Z';
    const d = new Date(s);
    if (Number.isNaN(d.getTime())) return iso;
    return new Intl.DateTimeFormat(undefined, { timeZone: displayTimezone, dateStyle: 'short', timeStyle: 'medium' }).format(d);
  } catch { return iso; }
}

function calcDuration(startIso?: string, endIso?: string): string {
  if (!startIso || !endIso) return '-';
  try {
    const toDate = (s: string) => {
      let v = s.trim();
      if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(v) && !/Z|[+-]\d{2}:?\d{2}$/.test(v)) v = v.replace(/\.\d{3}$/, '') + 'Z';
      return new Date(v);
    };
    const start = toDate(startIso);
    const end = toDate(endIso);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return '-';
    const diffMs = end.getTime() - start.getTime();
    if (diffMs < 0) return '-';
    if (diffMs < 1000) return `${diffMs}ms`;
    const secs = Math.floor(diffMs / 1000);
    if (secs < 60) return `${secs}s`;
    const mins = Math.floor(secs / 60);
    const remSecs = secs % 60;
    if (mins < 60) return remSecs > 0 ? `${mins}m ${remSecs}s` : `${mins}m`;
    const hrs = Math.floor(mins / 60);
    const remMins = mins % 60;
    return remMins > 0 ? `${hrs}h ${remMins}m` : `${hrs}h`;
  } catch { return '-'; }
}

function getChatSessionUrl(chatId: string): string {
  const base = ((import.meta as any).env?.BASE_URL ?? '/').replace(/\/+$/, '') || '';
  const path = ['share', chatId].join('/').replace(/\/+/g, '/');
  return `${window.location.origin}${base ? `${base}/${path}` : `/${path}`}`;
}

function openRunChat(run: TaskRun) {
  if (run.chat_id) window.open(getChatSessionUrl(run.chat_id), '_blank', 'noopener,noreferrer');
}

async function copyRunChatLink(run: TaskRun) {
  if (!run.chat_id) return;
  const url = getChatSessionUrl(run.chat_id);
  try { await navigator.clipboard.writeText(url); showSuccessToast(t('Link copied')); }
  catch { showSuccessToast(t('Link copied')); }
}

function viewRunResult(run: TaskRun) { resultDialogContent.value = run.result || run.error || ''; }

// ========== Click outside ==========
function onClickOutside(e: MouseEvent) {
  if (scheduleComboRef.value && !scheduleComboRef.value.contains(e.target as Node)) scheduleDropdownOpen.value = false;
  if (webhookDropdownRef.value && !webhookDropdownRef.value.contains(e.target as Node)) webhookDropdownOpen.value = false;
  if (modelDropdownRef.value && !modelDropdownRef.value.contains(e.target as Node)) modelDropdownOpen.value = false;
  if (taskMenuOpenId.value) {
    const menuEl = menuRefs.get(taskMenuOpenId.value);
    if (menuEl && !menuEl.contains(e.target as Node)) taskMenuOpenId.value = null;
  }
}

// ========== Init ==========
onMounted(async () => {
  document.addEventListener('mousedown', onClickOutside);
  try { allWebhooks.value = await listWebhooks(); } catch { allWebhooks.value = []; }
  try { models.value = await listModels(); } catch { models.value = []; }
  await loadTasks();
  if (tasks.value.length > 0 && !selectedTaskId.value) {
    selectTask(tasks.value[0]);
  }
});
onUnmounted(() => {
  document.removeEventListener('mousedown', onClickOutside);
  stopCountdown();
});
</script>

<style scoped>
/* Override browser default accent color (blue) with sky to match page theme */
:deep(input[type="text"]),
:deep(input[type="textarea"]),
:deep(textarea) {
  caret-color: #38bdf8; /* sky-400 */
}

/* Text selection color in inputs */
:deep(input[type="text"]::selection),
:deep(textarea::selection) {
  background-color: rgba(56, 189, 248, 0.3); /* sky-400 with opacity */
}

:deep(input[type="text"]::-moz-selection),
:deep(textarea::-moz-selection) {
  background-color: rgba(56, 189, 248, 0.3); /* sky-400 with opacity */
}

/* Remove browser autofill blue background */
:deep(input:-webkit-autofill),
:deep(input:-webkit-autofill:hover),
:deep(input:-webkit-autofill:focus),
:deep(textarea:-webkit-autofill),
:deep(textarea:-webkit-autofill:hover),
:deep(textarea:-webkit-autofill:focus) {
  -webkit-box-shadow: 0 0 0px 1000px #fff inset;
  transition: background-color 5000s ease-in-out 0s;
}

.slide-fade-enter-active { transition: all 0.2s ease-out; }
.slide-fade-leave-active { transition: all 0.15s ease-in; }
.slide-fade-enter-from, .slide-fade-leave-to { opacity: 0; transform: translateY(-4px); }

.confirm-overlay-enter-active { transition: opacity 0.2s ease-out; }
.confirm-overlay-leave-active { transition: opacity 0.15s ease-in; }
.confirm-overlay-enter-from, .confirm-overlay-leave-to { opacity: 0; }

.confirm-card-enter-active { transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1); }
.confirm-card-leave-active { transition: all 0.15s ease-in; }
.confirm-card-enter-from { opacity: 0; transform: scale(0.95) translateY(8px); }
.confirm-card-leave-to { opacity: 0; transform: scale(0.97) translateY(4px); }
</style>
