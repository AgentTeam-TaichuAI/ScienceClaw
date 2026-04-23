<template>
  <div class="flex flex-col w-full gap-5">
    <div class="flex items-center justify-between">
      <div>
        <h3 class="text-base font-semibold text-gray-800 dark:text-gray-100">IM Account Binding</h3>
        <p class="text-xs text-gray-500 dark:text-gray-400">Bind your Lark and Telegram accounts for direct IM conversations.</p>
      </div>
      <button
        @click="$emit('back')"
        class="px-3 py-1.5 rounded-lg text-xs font-medium bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-blue-300 dark:hover:border-blue-600 transition-colors cursor-pointer"
      >
        Back
      </button>
    </div>

    <section class="panel">
      <div class="panel-header">
        <div>
          <h4 class="panel-title">Lark</h4>
          <p class="panel-subtitle">Paste the Lark open_id or the `/bind_lark ...` command returned by the bot.</p>
        </div>
        <span class="status" :class="larkStatus.bound ? 'status-on' : 'status-off'">
          {{ larkStatus.bound ? 'Bound' : 'Not bound' }}
        </span>
      </div>
      <div v-if="larkStatus.bound" class="panel-note">Current user ID: {{ larkStatus.platform_user_id }}</div>
      <input v-model="larkUserId" type="text" placeholder="ou_xxx or /bind_lark ou_xxx" class="input" />
      <div class="flex gap-2">
        <button @click="handleBindLark" :disabled="loading || !larkUserId.trim()" class="primary-button">
          {{ loading ? 'Binding...' : 'Bind Lark' }}
        </button>
        <button @click="refreshStatuses" :disabled="loading" class="secondary-button">Refresh</button>
        <button @click="handleUnbindLark" :disabled="loading || !larkStatus.bound" class="danger-button">Unbind</button>
      </div>
    </section>

    <section class="panel">
      <div class="panel-header">
        <div>
          <h4 class="panel-title">Telegram</h4>
          <p class="panel-subtitle">Open this page, then send any private message to the bot. If you are the only pending Telegram binding, the backend will link automatically.</p>
        </div>
        <span class="status" :class="telegramStatus.bound ? 'status-on' : 'status-off'">
          {{ telegramStatus.bound ? 'Bound' : 'Not bound' }}
        </span>
      </div>
      <div v-if="telegramBotInfo?.bot_link" class="panel-note">
        Bot link:
        <a :href="telegramBotInfo.bot_link" target="_blank" rel="noreferrer" class="underline text-blue-600 dark:text-blue-400">
          {{ telegramBotInfo.bot_link }}
        </a>
      </div>
      <div v-if="!telegramStatus.bound" class="rounded-xl border border-blue-200 dark:border-blue-900/40 bg-blue-50 dark:bg-blue-950/20 p-3 space-y-3">
        <div class="panel-note">
          Fast path: keep this page open, then send any private message to the bot. You can also click <strong>Connect Telegram</strong> to jump to the bot.
        </div>
        <div v-if="telegramBindLink?.deep_link" class="panel-note break-all">
          Deep link:
          <a :href="telegramBindLink.deep_link" target="_blank" rel="noreferrer" class="underline text-blue-600 dark:text-blue-400">
            {{ telegramBindLink.deep_link }}
          </a>
        </div>
        <div v-if="telegramBindLink?.expires_at" class="panel-note">
          Link expires at: {{ formatTimestamp(telegramBindLink.expires_at) }}
        </div>
        <div v-if="waitingForTelegramBind" class="panel-note text-blue-700 dark:text-blue-300">
          Waiting for Telegram confirmation. Send any private Telegram message and this page will refresh automatically.
        </div>
        <div class="flex gap-2 flex-wrap">
          <button @click="handleCreateTelegramBindLink" :disabled="loading || !telegramBotInfo?.configured" class="primary-button">
            {{ loading ? 'Preparing...' : 'Connect Telegram' }}
          </button>
          <button
            v-if="telegramBindLink?.deep_link"
            @click="openTelegramBindLink"
            :disabled="loading"
            class="secondary-button"
          >
            Open Again
          </button>
          <button @click="refreshStatuses" :disabled="loading" class="secondary-button">Refresh</button>
        </div>
      </div>
      <div v-if="telegramStatus.bound" class="panel-note">Current user ID: {{ telegramStatus.platform_user_id }}</div>
      <div class="panel-note">Manual fallback</div>
      <input v-model="telegramUserId" type="text" placeholder="123456789 or /bind_telegram 123456789" class="input" />
      <div class="flex gap-2">
        <button @click="handleBindTelegram" :disabled="loading || !telegramUserId.trim()" class="primary-button">
          {{ loading ? 'Binding...' : 'Bind Telegram' }}
        </button>
        <button @click="refreshStatuses" :disabled="loading" class="secondary-button">Refresh</button>
        <button @click="handleUnbindTelegram" :disabled="loading || !telegramStatus.bound" class="danger-button">Unbind</button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';
import {
  bindLarkAccount,
  bindTelegramAccount,
  createTelegramBindLink,
  getLarkBindingStatus,
  getTelegramBindingStatus,
  getTelegramBotInfo,
  unbindLarkAccount,
  unbindTelegramAccount,
  type PlatformBindingStatus,
  type TelegramBindLink,
  type TelegramBotInfo,
} from '@/api/im';
import { showErrorToast, showSuccessToast } from '@/utils/toast';

defineEmits<{
  back: []
}>();

const loading = ref(false);
const larkStatus = ref<PlatformBindingStatus>({ bound: false });
const telegramStatus = ref<PlatformBindingStatus>({ bound: false });
const telegramBotInfo = ref<TelegramBotInfo | null>(null);
const telegramBindLink = ref<TelegramBindLink | null>(null);
const waitingForTelegramBind = ref(false);
const larkUserId = ref('');
const telegramUserId = ref('');
let telegramBindPollTimer: number | null = null;

function stopTelegramBindPolling(resetWaiting = true) {
  if (telegramBindPollTimer !== null) {
    window.clearInterval(telegramBindPollTimer);
    telegramBindPollTimer = null;
  }
  if (resetWaiting) {
    waitingForTelegramBind.value = false;
  }
}

function startTelegramBindPolling() {
  stopTelegramBindPolling(false);
  waitingForTelegramBind.value = true;
  telegramBindPollTimer = window.setInterval(async () => {
    try {
      const telegram = await getTelegramBindingStatus();
      telegramStatus.value = telegram;
      if (telegram.bound) {
        if (telegram.platform_user_id) {
          telegramUserId.value = telegram.platform_user_id;
        }
        stopTelegramBindPolling();
        showSuccessToast('Telegram account bound successfully');
      }
    } catch {
      // Keep polling quietly. The normal refresh path still surfaces errors.
    }
  }, 2500);
}

function openTelegramBindLink() {
  if (!telegramBindLink.value?.deep_link) return;
  window.open(telegramBindLink.value.deep_link, '_blank', 'noopener,noreferrer');
}

function formatTimestamp(timestamp?: number) {
  if (!timestamp) return '';
  return new Date(timestamp * 1000).toLocaleString();
}

async function ensureTelegramAutoBindReady() {
  if (telegramStatus.value.bound) return;
  if (!telegramBotInfo.value?.configured) return;
  try {
    telegramBindLink.value = await createTelegramBindLink();
    startTelegramBindPolling();
  } catch {
    // Keep the page usable even if auto-prepare fails.
  }
}

async function refreshStatuses() {
  loading.value = true;
  try {
    const [lark, telegram] = await Promise.all([getLarkBindingStatus(), getTelegramBindingStatus()]);
    larkStatus.value = lark;
    telegramStatus.value = telegram;
    if (lark.bound && lark.platform_user_id) larkUserId.value = lark.platform_user_id;
    if (telegram.bound && telegram.platform_user_id) telegramUserId.value = telegram.platform_user_id;
    if (telegram.bound) {
      stopTelegramBindPolling();
      telegramBindLink.value = null;
    }
    try {
      telegramBotInfo.value = await getTelegramBotInfo();
    } catch {
      telegramBotInfo.value = null;
    }
    await ensureTelegramAutoBindReady();
  } catch (error: any) {
    showErrorToast(error?.response?.data?.detail || error?.message || 'Failed to load binding status');
  } finally {
    loading.value = false;
  }
}

async function handleCreateTelegramBindLink() {
  loading.value = true;
  try {
    telegramBindLink.value = await createTelegramBindLink();
    if (!telegramBindLink.value.deep_link) {
      await refreshStatuses();
      return;
    }
    startTelegramBindPolling();
    openTelegramBindLink();
    showSuccessToast('Telegram opened. Tap Start in Telegram to complete the binding.');
  } catch (error: any) {
    stopTelegramBindPolling();
    showErrorToast(error?.response?.data?.detail || error?.message || 'Failed to prepare Telegram binding');
  } finally {
    loading.value = false;
  }
}

async function handleBindLark() {
  loading.value = true;
  try {
    await bindLarkAccount({ lark_user_id: larkUserId.value.trim() });
    showSuccessToast('Lark account bound successfully');
    await refreshStatuses();
  } catch (error: any) {
    showErrorToast(error?.response?.data?.detail || error?.message || 'Failed to bind Lark account');
  } finally {
    loading.value = false;
  }
}

async function handleUnbindLark() {
  loading.value = true;
  try {
    await unbindLarkAccount();
    showSuccessToast('Lark account unbound');
    await refreshStatuses();
  } catch (error: any) {
    showErrorToast(error?.response?.data?.detail || error?.message || 'Failed to unbind Lark account');
  } finally {
    loading.value = false;
  }
}

async function handleBindTelegram() {
  loading.value = true;
  try {
    await bindTelegramAccount({ telegram_user_id: telegramUserId.value.trim() });
    showSuccessToast('Telegram account bound successfully');
    await refreshStatuses();
  } catch (error: any) {
    showErrorToast(error?.response?.data?.detail || error?.message || 'Failed to bind Telegram account');
  } finally {
    loading.value = false;
  }
}

async function handleUnbindTelegram() {
  loading.value = true;
  try {
    await unbindTelegramAccount();
    stopTelegramBindPolling();
    telegramBindLink.value = null;
    showSuccessToast('Telegram account unbound');
    await refreshStatuses();
  } catch (error: any) {
    showErrorToast(error?.response?.data?.detail || error?.message || 'Failed to unbind Telegram account');
  } finally {
    loading.value = false;
  }
}

onMounted(refreshStatuses);
onBeforeUnmount(() => stopTelegramBindPolling());
</script>

<style scoped>
.panel {
  @apply p-4 rounded-xl bg-gray-50/80 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 space-y-3;
}

.panel-header {
  @apply flex items-start justify-between gap-3;
}

.panel-title {
  @apply text-sm font-semibold text-gray-700 dark:text-gray-200;
}

.panel-subtitle {
  @apply text-xs text-gray-500 dark:text-gray-400;
}

.panel-note {
  @apply text-xs text-gray-500 dark:text-gray-400;
}

.input {
  @apply w-full h-10 rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 px-3 text-sm text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300 dark:focus:border-blue-600;
}

.status {
  @apply text-xs px-2 py-1 rounded-full border;
}

.status-on {
  @apply border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-400;
}

.status-off {
  @apply border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-400;
}

.primary-button {
  @apply px-4 py-2 rounded-xl text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors cursor-pointer;
}

.secondary-button {
  @apply px-4 py-2 rounded-xl text-sm font-medium bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-blue-300 dark:hover:border-blue-600 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed;
}

.danger-button {
  @apply px-4 py-2 rounded-xl text-sm font-medium bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors cursor-pointer;
}
</style>
