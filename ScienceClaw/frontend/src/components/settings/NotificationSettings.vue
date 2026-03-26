<template>
  <div class="flex flex-col gap-4 w-full">
    <p class="text-sm text-[var(--text-tertiary)]">
      Manage task notification channels for Feishu, DingTalk, WeCom, and Telegram.
    </p>

    <div v-if="loading" class="flex justify-center py-8">
      <div class="animate-pulse text-[var(--text-tertiary)]">Loading...</div>
    </div>

    <template v-else>
      <div
        v-for="webhook in webhooks"
        :key="webhook.id"
        class="w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-[#f8f9fb] dark:bg-[#111] p-4"
      >
        <template v-if="editingId !== webhook.id">
          <div class="flex items-center justify-between gap-3">
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2.5">
                <span class="font-medium text-[var(--text-primary)] truncate">{{ webhook.name }}</span>
                <span class="text-xs px-2 py-0.5 rounded-full bg-gray-200 dark:bg-gray-700 text-[var(--text-tertiary)]">
                  {{ typeLabel(webhook.type) }}
                </span>
              </div>
              <p class="text-xs text-[var(--text-tertiary)] mt-1.5 truncate">{{ describeWebhook(webhook) }}</p>
            </div>
            <div class="flex items-center gap-1.5 shrink-0">
              <button
                @click="handleTest(webhook)"
                :disabled="testingId === webhook.id"
                class="text-xs px-2.5 py-1 rounded-lg border border-blue-500 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 disabled:opacity-50 transition-colors"
              >
                {{ testingId === webhook.id ? 'Sending...' : 'Test' }}
              </button>
              <button @click="startEdit(webhook)" class="px-2.5 py-1 rounded-lg text-xs border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800">
                Edit
              </button>
              <button @click="handleDelete(webhook)" class="px-2.5 py-1 rounded-lg text-xs border border-red-200 text-red-500 hover:bg-red-50 dark:border-red-900/50 dark:hover:bg-red-900/20">
                Delete
              </button>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="space-y-3">
            <div class="flex gap-2">
              <input v-model="editForm.name" type="text" placeholder="Channel name" class="flex-1 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#1e1e1e] text-sm text-[var(--text-primary)] focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500" />
              <select v-model="editForm.type" class="w-40 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#1e1e1e] text-sm text-[var(--text-primary)] focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500">
                <option value="feishu">Feishu</option>
                <option value="dingtalk">DingTalk</option>
                <option value="wecom">WeCom</option>
                <option value="telegram">Telegram</option>
              </select>
            </div>

            <template v-if="usesLegacyUrl(editForm.type)">
              <input v-model="editForm.url" type="url" placeholder="Webhook URL" class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#1e1e1e] text-sm text-[var(--text-primary)] focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500" />
            </template>
            <template v-else>
              <input v-model="editForm.config.chat_id" type="text" placeholder="Telegram chat id" class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#1e1e1e] text-sm text-[var(--text-primary)] focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500" />
              <input v-model="editForm.config.bot_token" type="password" placeholder="Leave blank to keep existing bot token" class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#1e1e1e] text-sm text-[var(--text-primary)] focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500" />
            </template>

            <p v-if="editError" class="text-xs text-red-500">{{ editError }}</p>
            <div class="flex gap-2 justify-end">
              <button @click="cancelEdit" class="px-3 py-1.5 rounded-lg text-sm text-[var(--text-secondary)] hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors">Cancel</button>
              <button @click="saveEdit" :disabled="savingEdit" class="px-3 py-1.5 rounded-lg text-sm bg-gradient-to-r from-blue-500 to-indigo-600 text-white font-medium disabled:opacity-50 transition-all">
                {{ savingEdit ? 'Saving...' : 'Save' }}
              </button>
            </div>
          </div>
        </template>
      </div>

      <div v-if="webhooks.length === 0 && !showCreateForm" class="text-center py-8 text-[var(--text-tertiary)] text-sm">
        No notification channels configured.
      </div>

      <div v-if="showCreateForm" class="w-full rounded-xl border-2 border-dashed border-blue-300 dark:border-blue-700 bg-blue-50/50 dark:bg-blue-900/10 p-4 space-y-3">
        <p class="text-sm font-medium text-[var(--text-primary)]">New notification channel</p>
        <div class="flex gap-2">
          <input v-model="createForm.name" type="text" placeholder="Channel name" class="flex-1 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#1e1e1e] text-sm text-[var(--text-primary)] focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500" />
          <select v-model="createForm.type" class="w-40 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#1e1e1e] text-sm text-[var(--text-primary)] focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500">
            <option value="feishu">Feishu</option>
            <option value="dingtalk">DingTalk</option>
            <option value="wecom">WeCom</option>
            <option value="telegram">Telegram</option>
          </select>
        </div>
        <template v-if="usesLegacyUrl(createForm.type)">
          <input v-model="createForm.url" type="url" placeholder="Webhook URL" class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#1e1e1e] text-sm text-[var(--text-primary)] focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500" />
        </template>
        <template v-else>
          <input v-model="createForm.config.chat_id" type="text" placeholder="Telegram chat id" class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#1e1e1e] text-sm text-[var(--text-primary)] focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500" />
          <input v-model="createForm.config.bot_token" type="password" placeholder="Telegram bot token" class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#1e1e1e] text-sm text-[var(--text-primary)] focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500" />
        </template>
        <p v-if="createError" class="text-xs text-red-500">{{ createError }}</p>
        <div class="flex gap-2 justify-end">
          <button @click="resetCreateForm" class="px-3 py-1.5 rounded-lg text-sm text-[var(--text-secondary)] hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors">Cancel</button>
          <button @click="handleCreate" :disabled="creating" class="px-3 py-1.5 rounded-lg text-sm bg-gradient-to-r from-blue-500 to-indigo-600 text-white font-medium disabled:opacity-50 transition-all">
            {{ creating ? 'Creating...' : 'Create' }}
          </button>
        </div>
      </div>

      <button
        v-if="!showCreateForm"
        @click="showCreateForm = true"
        class="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-dashed border-gray-300 dark:border-gray-600 text-[var(--text-secondary)] hover:border-blue-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors text-sm"
      >
        Add notification channel
      </button>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { createWebhook, deleteWebhook, listWebhooks, testWebhook, updateWebhook, type Webhook, type WebhookType } from '@/api/webhooks';
import { showErrorToast, showSuccessToast } from '@/utils/toast';

type EditableWebhookForm = {
  name: string;
  type: WebhookType;
  url: string;
  config: {
    chat_id: string;
    bot_token: string;
  };
};

const loading = ref(true);
const webhooks = ref<Webhook[]>([]);
const showCreateForm = ref(false);
const creating = ref(false);
const editingId = ref<string | null>(null);
const savingEdit = ref(false);
const testingId = ref<string | null>(null);
const createError = ref('');
const editError = ref('');

const createForm = ref<EditableWebhookForm>(emptyForm());
const editForm = ref<EditableWebhookForm>(emptyForm());

function emptyForm(): EditableWebhookForm {
  return {
    name: '',
    type: 'feishu',
    url: '',
    config: {
      chat_id: '',
      bot_token: '',
    },
  };
}

function usesLegacyUrl(type: WebhookType): boolean {
  return type === 'feishu' || type === 'dingtalk' || type === 'wecom';
}

function typeLabel(type: WebhookType): string {
  return {
    feishu: 'Feishu',
    dingtalk: 'DingTalk',
    wecom: 'WeCom',
    telegram: 'Telegram',
  }[type];
}

function describeWebhook(webhook: Webhook): string {
  if (webhook.type === 'telegram') {
    return `chat_id: ${webhook.config?.chat_id || '-'} | token: ${webhook.config?.has_bot_token ? 'configured' : 'missing'}`;
  }
  return webhook.url;
}

function formFromWebhook(webhook: Webhook): EditableWebhookForm {
  return {
    name: webhook.name,
    type: webhook.type,
    url: webhook.url || '',
    config: {
      chat_id: webhook.type === 'telegram' ? String(webhook.config?.chat_id || '') : '',
      bot_token: '',
    },
  };
}

function validateForm(form: EditableWebhookForm, requireTokenForTelegram: boolean): string {
  if (!form.name.trim()) return 'Channel name is required';
  if (usesLegacyUrl(form.type) && !form.url.trim()) return 'Webhook URL is required';
  if (form.type === 'telegram') {
    if (!form.config.chat_id.trim()) return 'Telegram chat id is required';
    if (requireTokenForTelegram && !form.config.bot_token.trim()) return 'Telegram bot token is required';
  }
  return '';
}

async function loadWebhooks() {
  loading.value = true;
  try {
    webhooks.value = await listWebhooks();
  } catch {
    webhooks.value = [];
  } finally {
    loading.value = false;
  }
}

function resetCreateForm() {
  showCreateForm.value = false;
  createError.value = '';
  createForm.value = emptyForm();
}

async function handleCreate() {
  createError.value = validateForm(createForm.value, createForm.value.type === 'telegram');
  if (createError.value) return;
  creating.value = true;
  try {
    await createWebhook({
      name: createForm.value.name.trim(),
      type: createForm.value.type,
      url: usesLegacyUrl(createForm.value.type) ? createForm.value.url.trim() : '',
      config: createForm.value.type === 'telegram'
        ? { chat_id: createForm.value.config.chat_id.trim(), bot_token: createForm.value.config.bot_token.trim() }
        : undefined,
    });
    resetCreateForm();
    await loadWebhooks();
    showSuccessToast('Notification channel created');
  } catch (e: any) {
    showErrorToast(e?.response?.data?.detail || 'Create failed');
  } finally {
    creating.value = false;
  }
}

function startEdit(webhook: Webhook) {
  editingId.value = webhook.id;
  editError.value = '';
  editForm.value = formFromWebhook(webhook);
}

function cancelEdit() {
  editingId.value = null;
  editError.value = '';
}

async function saveEdit() {
  if (!editingId.value) return;
  editError.value = validateForm(editForm.value, false);
  if (editError.value) return;
  savingEdit.value = true;
  try {
    await updateWebhook(editingId.value, {
      name: editForm.value.name.trim(),
      type: editForm.value.type,
      url: usesLegacyUrl(editForm.value.type) ? editForm.value.url.trim() : '',
      config: editForm.value.type === 'telegram'
        ? { chat_id: editForm.value.config.chat_id.trim(), bot_token: editForm.value.config.bot_token.trim() }
        : {},
    });
    cancelEdit();
    await loadWebhooks();
    showSuccessToast('Notification channel updated');
  } catch (e: any) {
    showErrorToast(e?.response?.data?.detail || 'Save failed');
  } finally {
    savingEdit.value = false;
  }
}

async function handleDelete(webhook: Webhook) {
  if (!window.confirm(`Delete ${webhook.name}?`)) return;
  try {
    await deleteWebhook(webhook.id);
    await loadWebhooks();
    showSuccessToast('Notification channel deleted');
  } catch (e: any) {
    showErrorToast(e?.response?.data?.detail || 'Delete failed');
  }
}

async function handleTest(webhook: Webhook) {
  testingId.value = webhook.id;
  try {
    const result = await testWebhook(webhook.id);
    showSuccessToast(result.message || 'Test message sent');
  } catch (e: any) {
    showErrorToast(e?.response?.data?.detail || 'Test failed');
  } finally {
    testingId.value = null;
  }
}

onMounted(loadWebhooks);
</script>
