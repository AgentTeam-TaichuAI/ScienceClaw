<template>
  <div class="flex flex-col h-full w-full overflow-hidden tasks-page-teal">
    <!-- Header -->
    <div class="flex-shrink-0 px-6 py-5 border-b border-gray-100 dark:border-gray-800 bg-white dark:bg-[#1a1a1a]">
      <div class="max-w-2xl mx-auto">
        <h1 class="text-xl font-bold text-[var(--text-primary)] flex items-center gap-2.5">
          <span class="inline-flex items-center justify-center size-9 rounded-xl bg-gradient-to-br from-teal-500 to-cyan-600 shadow-sm">
            <CalendarClock :size="18" class="text-white" />
          </span>
          {{ isEdit ? t('Edit Task') : t('New Scheduled Task') }}
        </h1>
        <p class="text-[var(--text-tertiary)] text-sm mt-1 ml-[46px]">{{ t('Configure schedule, prompt and Feishu webhook') }}</p>
      </div>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto p-6 bg-[#f8f9fb] dark:bg-[#111]">
      <div class="max-w-2xl mx-auto">
        <div v-if="loading" class="flex justify-center py-16">
          <div class="animate-pulse text-[var(--text-tertiary)]">{{ t('Loading...') }}</div>
        </div>

        <form v-else @submit.prevent="submit" class="space-y-6">
          <!-- Task name -->
          <div class="rounded-2xl bg-white dark:bg-[#1e1e1e] border border-gray-100 dark:border-gray-800 p-5">
            <label class="block text-sm font-medium text-[var(--text-primary)] mb-2">{{ t('Task name') }}</label>
            <input
              v-model="form.name"
              type="text"
              required
              class="w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-[#f8f9fb] dark:bg-[#111] text-[var(--text-primary)] focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
              :placeholder="t('e.g. Daily AI News')"
            />
          </div>

          <!-- Model selector -->
          <div class="rounded-2xl bg-white dark:bg-[#1e1e1e] border border-gray-100 dark:border-gray-800 p-5" ref="modelDropdownRef">
            <label class="block text-sm font-medium text-[var(--text-primary)] mb-2">{{ t('Model') }}</label>
            <div class="relative">
              <button type="button" @click="modelDropdownOpen = !modelDropdownOpen"
                class="w-full flex items-center gap-2 px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-[#f8f9fb] dark:bg-[#111] text-[var(--text-primary)] hover:border-teal-400 focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors">
                <template v-if="selectedModel">
                  <ProviderIcon :provider="selectedModel.provider" class="size-5 flex-shrink-0" />
                  <span class="flex-1 text-left truncate text-sm">{{ modelDisplayName(selectedModel) }}</span>
                  <span class="text-[10px] text-[var(--text-tertiary)]">{{ selectedModel.provider }}</span>
                </template>
                <template v-else>
                  <span class="flex-1 text-left text-sm text-[var(--text-tertiary)]">{{ t('Select model') }}</span>
                </template>
                <ChevronDown :size="14" class="flex-shrink-0 text-[var(--text-tertiary)]" />
              </button>
              <Transition name="slide-fade">
                <div v-if="modelDropdownOpen"
                  class="absolute z-20 left-0 right-0 mt-1 bg-white dark:bg-[#1e1e1e] border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg overflow-hidden">
                  <div class="bg-[#f8f9fb] dark:bg-[#111] px-3 py-2 border-b border-gray-100 dark:border-gray-800">
                    <span class="text-xs font-medium text-[var(--text-tertiary)]">Select Model</span>
                  </div>
                  <div class="flex flex-col max-h-[300px] overflow-y-auto p-1">
                    <button v-for="model in models" :key="model.id" type="button"
                      @click="selectTaskModel(model.id)"
                      class="flex items-center gap-2.5 w-full px-3 py-2.5 rounded-lg text-left transition-colors"
                      :class="form.model_config_id === model.id ? 'bg-teal-50 dark:bg-teal-900/20' : 'hover:bg-gray-50 dark:hover:bg-gray-800/50'">
                      <ProviderIcon :provider="model.provider" class="size-5 flex-shrink-0" />
                      <div class="flex-1 min-w-0">
                        <span class="text-sm font-medium text-[var(--text-primary)] truncate block">{{ modelDisplayName(model) }}</span>
                        <span class="text-[10px] text-[var(--text-tertiary)] truncate block">{{ model.provider }}</span>
                      </div>
                      <CheckCircle2 v-if="form.model_config_id === model.id" :size="16" class="flex-shrink-0 text-teal-500" />
                    </button>
                    <div v-if="models.length === 0" class="px-4 py-6 text-center text-xs text-[var(--text-tertiary)]">
                      {{ t('No models configured') }}
                    </div>
                  </div>
                </div>
              </Transition>
            </div>
          </div>

          <!-- Schedule -->
          <div class="rounded-2xl bg-white dark:bg-[#1e1e1e] border border-gray-100 dark:border-gray-800 p-5" ref="scheduleComboRef">
            <label class="block text-sm font-medium text-[var(--text-primary)] mb-2">{{ t('Schedule') }}</label>
            <div class="flex gap-2">
              <div class="relative flex-1 min-w-0">
                <input
                  v-model="form.schedule_desc"
                  type="text"
                  required
                  autocomplete="off"
                  readonly
                  @click="openSchedulePanel"
                  class="w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-[#f8f9fb] dark:bg-[#111] text-[var(--text-primary)] cursor-pointer focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 transition-colors"
                  :class="{
                    'border-red-400 dark:border-red-500 focus:ring-red-500/30 focus:border-red-400': scheduleError,
                    'border-emerald-400 dark:border-emerald-500 focus:ring-emerald-500/30 focus:border-emerald-400': scheduleVerified
                  }"
                  :placeholder="t('e.g. Every day at 9am')"
                />
                <CheckCircle2 v-if="scheduleVerified" :size="16" class="absolute right-3 top-1/2 -translate-y-1/2 text-emerald-500" />
              </div>
              <button
                type="button"
                :disabled="scheduleVerifying || !form.schedule_desc?.trim()"
                @click="verifyScheduleClick"
                class="flex-shrink-0 px-4 py-2.5 rounded-xl border border-teal-500 text-teal-600 dark:text-teal-400 hover:bg-teal-50 dark:hover:bg-teal-900/20 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm transition-colors"
              >
                {{ scheduleVerifying ? t('Verifying...') : t('Verify') }}
              </button>
            </div>

            <!-- Feedback messages -->
            <p v-if="scheduleError && !scheduleDropdownOpen" class="text-xs text-red-500 mt-2 flex items-center gap-1">
              <AlertCircle :size="12" />
              {{ scheduleError }}
            </p>
            <p v-else-if="scheduleVerified" class="text-xs text-emerald-600 dark:text-emerald-400 mt-2 flex items-center gap-1">
              <CheckCircle2 :size="12" />
              {{ t('Schedule verify success') }} {{ t('Next run time') }}：{{ scheduleVerifyNextRun }}
            </p>

            <!-- Schedule selection panel -->
            <Transition name="slide-fade">
              <div
                v-if="scheduleDropdownOpen"
                class="mt-3 bg-[#f8f9fb] dark:bg-[#111] border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden"
              >
                <!-- Recommended -->
                <div v-if="scheduleSuggestions.length > 0" class="p-3 pb-2">
                  <p class="text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider mb-2">{{ t('Recommended') }}</p>
                  <div
                    v-for="(sug, i) in scheduleSuggestions"
                    :key="'sug-' + i"
                    @click="pickScheduleSuggestion(sug)"
                    class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm cursor-pointer transition-colors mb-1"
                    :class="scheduleHighlight === i
                      ? 'bg-teal-50 dark:bg-teal-900/20 text-teal-700 dark:text-teal-300'
                      : 'text-[var(--text-primary)] hover:bg-white dark:hover:bg-[#1e1e1e]'"
                    @mouseenter="scheduleHighlight = i"
                  >
                    <Clock :size="14" class="flex-shrink-0 text-teal-400" />
                    {{ sug }}
                  </div>
                </div>
                <!-- Divider -->
                <div class="border-t border-gray-200 dark:border-gray-700 mx-3"></div>
                <!-- Custom -->
                <div class="p-3">
                  <p class="text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider mb-2">{{ t('Custom input') }}</p>
                  <div class="flex gap-2">
                    <input
                      ref="scheduleCustomInputRef"
                      v-model="scheduleCustomInput"
                      type="text"
                      autocomplete="off"
                      @keydown.enter.prevent="confirmCustomSchedule"
                      class="flex-1 min-w-0 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#1e1e1e] text-sm text-[var(--text-primary)] focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500"
                      :placeholder="t('e.g. Every day at 9am')"
                    />
                    <button
                      type="button"
                      @click="confirmCustomSchedule"
                      :disabled="!scheduleCustomInput?.trim()"
                      class="flex-shrink-0 px-4 py-2 rounded-lg bg-gradient-to-r from-teal-500 to-cyan-600 text-white text-sm font-medium hover:shadow-md hover:shadow-teal-500/25 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    >
                      {{ t('Confirm') }}
                    </button>
                  </div>
                </div>
              </div>
            </Transition>
          </div>

          <!-- Prompt -->
          <div class="rounded-2xl bg-white dark:bg-[#1e1e1e] border border-gray-100 dark:border-gray-800 p-5">
            <label class="block text-sm font-medium text-[var(--text-primary)] mb-2">{{ t('Prompt input') }}</label>
            <textarea
              v-model="form.prompt"
              required
              rows="5"
              class="w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-[#f8f9fb] dark:bg-[#111] text-[var(--text-primary)] focus:ring-2 focus:ring-teal-500/30 focus:border-teal-500 resize-y transition-colors"
              :placeholder="t('The prompt sent to the model at scheduled time')"
            />
          </div>

          <!-- Notification Webhooks -->
          <div class="rounded-2xl bg-white dark:bg-[#1e1e1e] border border-gray-100 dark:border-gray-800 p-5">
            <label class="block text-sm font-medium text-[var(--text-primary)] mb-2">{{ t('Notification webhooks') }}</label>

            <!-- Selected webhooks -->
            <div v-if="selectedWebhooks.length > 0" class="space-y-2 mb-3">
              <div v-for="wh in selectedWebhooks" :key="wh.id"
                class="flex items-center justify-between px-3 py-2 rounded-lg bg-[#f8f9fb] dark:bg-[#111] border border-gray-200 dark:border-gray-700">
                <div class="flex items-center gap-2 min-w-0 flex-1">
                  <span class="text-xs px-1.5 py-0.5 rounded bg-gray-200 dark:bg-gray-700 text-[var(--text-tertiary)]">{{ webhookTypeLabel(wh.type) }}</span>
                  <span class="text-sm text-[var(--text-primary)] truncate">{{ wh.name }}</span>
                </div>
                <button type="button" @click="removeWebhook(wh.id)"
                  class="p-1 rounded-md text-[var(--text-tertiary)] hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                  <X :size="14" />
                </button>
              </div>
            </div>

            <!-- Add webhook dropdown -->
            <div class="relative" ref="webhookDropdownRef">
              <button type="button" @click="toggleWebhookDropdown"
                class="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-dashed border-gray-300 dark:border-gray-600 text-[var(--text-secondary)] hover:border-teal-400 hover:text-teal-600 dark:hover:text-teal-400 transition-colors text-sm">
                <Plus :size="16" />
                {{ t('Add webhook') }}
              </button>

              <Transition name="slide-fade">
                <div v-if="webhookDropdownOpen"
                  class="absolute z-10 left-0 right-0 mt-1 bg-white dark:bg-[#1e1e1e] border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg overflow-hidden max-h-[240px] overflow-y-auto">
                  <template v-if="availableWebhooks.length > 0">
                    <div v-for="wh in availableWebhooks" :key="wh.id"
                      @click="addWebhook(wh.id)"
                      class="flex items-center gap-2 px-3 py-2.5 text-sm cursor-pointer hover:bg-teal-50 dark:hover:bg-teal-900/20 transition-colors">
                      <span class="text-xs px-1.5 py-0.5 rounded bg-gray-200 dark:bg-gray-700 text-[var(--text-tertiary)]">{{ webhookTypeLabel(wh.type) }}</span>
                      <span class="text-[var(--text-primary)] truncate">{{ wh.name }}</span>
                    </div>
                  </template>
                  <div class="border-t border-gray-100 dark:border-gray-800">
                    <button type="button" @click="openNotificationSettings"
                      class="w-full flex items-center gap-2 px-3 py-2.5 text-sm text-teal-600 dark:text-teal-400 hover:bg-teal-50 dark:hover:bg-teal-900/20 transition-colors">
                      <Settings2 :size="14" />
                      {{ t('Manage webhooks in Settings') }}
                    </button>
                  </div>
                </div>
              </Transition>
            </div>

            <p v-if="allWebhooks.length === 0 && !webhookDropdownOpen" class="text-xs text-[var(--text-tertiary)] mt-2">
              {{ t('No webhooks configured. Add one in Settings > Notifications.') }}
            </p>
          </div>

          <!-- Status (edit only) -->
          <div v-if="isEdit" class="rounded-2xl bg-white dark:bg-[#1e1e1e] border border-gray-100 dark:border-gray-800 p-5">
            <label class="block text-sm font-medium text-[var(--text-primary)] mb-2">{{ t('Status') }}</label>
            <select
              v-model="form.status"
              class="w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-[#f8f9fb] dark:bg-[#111] text-[var(--text-primary)] focus:ring-2 focus:ring-teal-500/30"
            >
              <option value="enabled">{{ t('Enabled') }}</option>
              <option value="disabled">{{ t('Disabled') }}</option>
            </select>
          </div>

          <!-- Action buttons -->
          <div class="flex items-center gap-3 pt-2">
            <button
              type="submit"
              :disabled="saving"
              class="px-6 py-2.5 rounded-xl bg-gradient-to-r from-teal-500 to-cyan-600 text-white font-medium hover:shadow-lg hover:shadow-teal-500/25 disabled:opacity-50 transition-all duration-200"
            >
              {{ saving ? t('Saving...') : (isEdit ? t('Save') : t('Create')) }}
            </button>
            <button
              type="button"
              @click="router.push('/chat/tasks')"
              class="px-6 py-2.5 rounded-xl bg-gray-100 dark:bg-gray-800 text-[var(--text-secondary)] hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            >
              {{ t('Cancel') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { CalendarClock, Clock, CheckCircle2, AlertCircle, Plus, X, Settings2, ChevronDown } from 'lucide-vue-next';
import { getTask, createTask, updateTask, validateSchedule } from '@/api/tasks';
import { listWebhooks } from '@/api/webhooks';
import { listModels } from '@/api/models';
import type { ModelConfig } from '@/api/models';
import type { Webhook } from '@/api/webhooks';
import { getAuthStatus } from '@/api/auth';
import { useSettingsDialog } from '@/composables/useSettingsDialog';
import { showErrorToast } from '@/utils/toast';
import ProviderIcon from '@/components/icons/ProviderIcon.vue';

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const taskId = computed(() => route.params.id as string);
const isEdit = computed(() => !!taskId.value && taskId.value !== 'new');

const { openSettingsDialog } = useSettingsDialog();

const form = ref({
  name: '',
  prompt: '',
  schedule_desc: '',
  webhook: '',
  webhook_ids: [] as string[],
  model_config_id: '',
  status: 'enabled',
});
const loading = ref(true);
const saving = ref(false);

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

// Webhook multi-select
const allWebhooks = ref<Webhook[]>([]);
const webhookDropdownOpen = ref(false);
const webhookDropdownRef = ref<HTMLElement | null>(null);

const selectedWebhooks = computed(() =>
  allWebhooks.value.filter(wh => form.value.webhook_ids.includes(wh.id))
);
const availableWebhooks = computed(() =>
  allWebhooks.value.filter(wh => !form.value.webhook_ids.includes(wh.id))
);
const TYPE_LABELS: Record<string, string> = { feishu: '飞书', dingtalk: '钉钉', wecom: '企微', telegram: 'Telegram' };
const webhookTypeLabel = (t: string) => TYPE_LABELS[t] || t;

function toggleWebhookDropdown() {
  webhookDropdownOpen.value = !webhookDropdownOpen.value;
}
function addWebhook(id: string) {
  if (!form.value.webhook_ids.includes(id)) {
    form.value.webhook_ids.push(id);
  }
  webhookDropdownOpen.value = false;
}
function removeWebhook(id: string) {
  form.value.webhook_ids = form.value.webhook_ids.filter(wid => wid !== id);
}
function openNotificationSettings() {
  webhookDropdownOpen.value = false;
  openSettingsDialog('notifications');
}
function onClickOutsideWebhook(e: MouseEvent) {
  if (webhookDropdownRef.value && !webhookDropdownRef.value.contains(e.target as Node)) {
    webhookDropdownOpen.value = false;
  }
}
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

function onClickOutside(e: MouseEvent) {
  if (scheduleComboRef.value && !scheduleComboRef.value.contains(e.target as Node)) {
    scheduleDropdownOpen.value = false;
  }
  if (modelDropdownRef.value && !modelDropdownRef.value.contains(e.target as Node)) {
    modelDropdownOpen.value = false;
  }
  onClickOutsideWebhook(e);
}
onMounted(() => document.addEventListener('mousedown', onClickOutside));
onUnmounted(() => document.removeEventListener('mousedown', onClickOutside));

const loadTask = async () => {
  try {
    allWebhooks.value = await listWebhooks();
  } catch { allWebhooks.value = []; }
  try {
    models.value = await listModels();
  } catch { models.value = []; }
  if (!isEdit.value) {
    if (models.value.length > 0) form.value.model_config_id = models.value[0].id;
    loading.value = false;
    return;
  }
  try {
    const task = await getTask(taskId.value);
    form.value = {
      name: task.name,
      prompt: task.prompt,
      schedule_desc: task.schedule_desc,
      webhook: task.webhook || '',
      webhook_ids: task.webhook_ids || [],
      model_config_id: task.model_config_id || '',
      status: task.status,
    };
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
};

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

const verifyScheduleClick = async () => {
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
    const detail = e?.response?.data?.detail;
    handleScheduleValidationError(detail);
  } finally {
    scheduleVerifying.value = false;
  }
};

const submit = async () => {
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
      model_config_id: form.value.model_config_id || undefined,
      status: form.value.status,
      user_id: userId,
    };
    if (isEdit.value) {
      await updateTask(taskId.value, payload);
    } else {
      await createTask(payload);
    }
    router.push('/chat/tasks');
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
};

onMounted(loadTask);
</script>

<style scoped>
/* Override browser default accent color (blue) with teal to match page theme */
:deep(input[type="text"]),
:deep(input[type="textarea"]),
:deep(textarea) {
  caret-color: #14b8a6; /* teal-500 */
}

/* Text selection color in inputs */
:deep(input[type="text"]::selection),
:deep(textarea::selection) {
  background-color: rgba(20, 184, 166, 0.3); /* teal-500 with opacity */
}

:deep(input[type="text"]::-moz-selection),
:deep(textarea::-moz-selection) {
  background-color: rgba(20, 184, 166, 0.3); /* teal-500 with opacity */
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

.slide-fade-enter-active {
  transition: all 0.2s ease-out;
}
.slide-fade-leave-active {
  transition: all 0.15s ease-in;
}
.slide-fade-enter-from {
  opacity: 0;
  transform: translateY(-4px);
}
.slide-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
