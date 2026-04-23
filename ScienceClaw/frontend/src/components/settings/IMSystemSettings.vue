<template>
  <div class="flex flex-col gap-4 py-2 px-1 w-full">
    <div class="flex gap-1 border-b border-gray-200/60 dark:border-gray-700/40">
      <button
        v-for="tab in subTabs"
        :key="tab.key"
        @click="activeSubTab = tab.key"
        class="relative px-4 py-2.5 text-sm font-medium transition-colors duration-150 cursor-pointer"
        :class="activeSubTab === tab.key
          ? 'text-blue-600 dark:text-blue-400'
          : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'"
      >
        <span>{{ tab.label }}</span>
        <div
          v-if="activeSubTab === tab.key"
          class="absolute bottom-0 left-2 right-2 h-0.5 bg-blue-500 dark:bg-blue-400 rounded-full"
        />
      </button>
    </div>

    <div v-show="activeSubTab === 'wechat'">
      <WeChatClawBotSettings :is-admin="props.isAdmin" />
    </div>

    <div v-show="activeSubTab === 'settings'" class="flex flex-col gap-5">
      <div class="p-4 rounded-xl bg-gray-50/80 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 flex items-center justify-between">
        <div class="flex flex-col gap-1">
          <span class="text-sm font-semibold text-gray-700 dark:text-gray-200">账号绑定</span>
          <span class="text-xs text-gray-500 dark:text-gray-400">在绑定页统一管理飞书和 Telegram 的账号绑定关系。</span>
        </div>
        <button
          @click="navigateToBinding"
          class="px-4 py-2 rounded-xl text-sm font-medium bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-blue-200 dark:hover:border-blue-600 hover:text-blue-600 dark:hover:text-blue-400 transition-all duration-200 cursor-pointer"
        >
          去绑定
        </button>
      </div>

      <div v-if="loading" class="flex justify-center py-12">
        <span class="text-sm text-gray-500 dark:text-gray-400">正在加载 IM 设置...</span>
      </div>

      <template v-else-if="props.isAdmin">
        <section class="card">
          <div class="card-header">
            <span class="card-title">全局 IM</span>
            <label class="toggle">
              <input v-model="form.im_enabled" type="checkbox" />
              <span>{{ form.im_enabled ? '已启用' : '已关闭' }}</span>
            </label>
          </div>
          <div class="grid gap-4 md:grid-cols-2 mt-4">
            <label class="field">
              <span>响应超时（秒）</span>
              <input v-model.number="form.im_response_timeout" type="number" min="30" max="1800" class="input" />
            </label>
            <label class="field">
              <span>最大消息长度</span>
              <input v-model.number="form.im_max_message_length" type="number" min="500" max="20000" class="input" />
            </label>
          </div>
        </section>

        <section class="card">
          <div class="card-header">
            <span class="card-title">飞书</span>
            <label class="toggle">
              <input v-model="form.lark_enabled" type="checkbox" />
              <span>{{ form.lark_enabled ? '已启用' : '已关闭' }}</span>
            </label>
          </div>
          <div class="grid gap-4 md:grid-cols-2 mt-4">
            <label class="field">
              <span>LARK_APP_ID</span>
              <input v-model="form.lark_app_id" type="text" placeholder="cli_xxx" class="input" />
            </label>
            <label class="field">
              <span>LARK_APP_SECRET</span>
              <input v-model="larkSecretInput" type="password" placeholder="留空表示不修改" class="input" />
              <small class="hint">当前状态：{{ form.has_lark_app_secret ? '已配置' : '未配置' }}</small>
            </label>
          </div>
        </section>

        <section class="card">
          <div class="card-header">
            <span class="card-title">Telegram</span>
            <label class="toggle">
              <input v-model="form.telegram_enabled" type="checkbox" />
              <span>{{ form.telegram_enabled ? '已启用' : '已关闭' }}</span>
            </label>
          </div>
          <div class="grid gap-4 md:grid-cols-2 mt-4">
            <label class="field">
              <span>Bot Token</span>
              <input v-model="telegramBotTokenInput" type="password" placeholder="留空表示不修改" class="input" />
              <small class="hint">当前状态：{{ form.has_telegram_bot_token ? '已配置' : '未配置' }}</small>
            </label>
            <label class="field">
              <span>接入方式</span>
              <select v-model="form.telegram_ingress_mode" class="input">
                <option value="polling">Polling</option>
                <option value="webhook">Webhook</option>
              </select>
            </label>
            <label class="field">
              <span>Webhook Secret</span>
              <input v-model="telegramWebhookSecretInput" type="password" placeholder="留空表示不修改" class="input" />
              <small class="hint">用于校验 Telegram Webhook 请求。</small>
            </label>
            <label class="field">
              <span>公网 Base URL</span>
              <input v-model="form.telegram_public_base_url" type="url" placeholder="https://example.com" class="input" />
              <small class="hint">Webhook 模式下必填。</small>
            </label>
          </div>
          <div class="mt-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50/80 dark:bg-gray-900/40 px-4 py-3">
            <label class="toggle justify-between">
              <div class="flex flex-col gap-1">
                <span class="text-sm font-medium text-gray-700 dark:text-gray-200">向 Telegram 发送输出文件</span>
                <span class="text-xs text-gray-500 dark:text-gray-400">关闭后只发送文本结果，生成文件保留在 Web 端。</span>
              </div>
              <input v-model="form.telegram_send_output_files" type="checkbox" />
            </label>
          </div>
          <div
            v-if="telegramBotInfo?.configured && telegramBotInfo.bot_link"
            class="mt-4 rounded-xl border border-blue-200 dark:border-blue-900/50 bg-blue-50 dark:bg-blue-900/10 px-4 py-3 text-sm text-blue-700 dark:text-blue-300"
          >
            Bot 链接：
            <a :href="telegramBotInfo.bot_link" target="_blank" rel="noreferrer" class="underline">{{ telegramBotInfo.bot_link }}</a>
          </div>
        </section>

        <section class="card">
          <div class="card-header">
            <span class="card-title">进度推送</span>
          </div>
          <div class="grid gap-4 md:grid-cols-2 mt-4">
            <label class="field">
              <span>响应模式</span>
              <select v-model="form.im_progress_mode" class="input">
                <option value="text_multi">多条文本</option>
                <option value="card_entity">卡片实体</option>
              </select>
            </label>
            <label class="field">
              <span>详情级别</span>
              <select v-model="form.im_progress_detail_level" class="input">
                <option value="compact">简洁</option>
                <option value="detailed">详细</option>
              </select>
            </label>
            <label class="field">
              <span>推送间隔（毫秒）</span>
              <input v-model.number="form.im_progress_interval_ms" type="number" min="300" max="10000" class="input" />
            </label>
          </div>
          <div class="mt-4">
            <span class="text-sm font-medium text-gray-700 dark:text-gray-200">实时事件</span>
            <div class="flex flex-wrap gap-2 mt-2">
              <button
                v-for="option in realtimeEventOptions"
                :key="option.value"
                @click="toggleRealtimeEvent(option.value)"
                class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors cursor-pointer"
                :class="form.im_realtime_events.includes(option.value) ? 'bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-900/20 dark:border-emerald-800 dark:text-emerald-400' : 'bg-gray-50 border-gray-200 text-gray-500 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-400'"
              >
                {{ option.label }}
              </button>
            </div>
          </div>
        </section>

        <div class="flex items-center justify-between">
          <button @click="loadSettings" class="px-4 py-2 text-sm rounded-xl border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
            刷新
          </button>
          <button
            @click="saveSettings"
            :disabled="saving || !hasChanges"
            class="px-5 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-blue-500 to-indigo-600 rounded-xl shadow-md shadow-blue-500/20 hover:shadow-lg hover:shadow-blue-500/30 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ saving ? '保存中...' : '保存 IM 设置' }}
          </button>
        </div>
      </template>

      <div v-else class="card text-sm text-gray-600 dark:text-gray-300">
        系统级 IM 配置仅管理员可见。
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import {
  getIMSystemSettings,
  getTelegramBotInfo,
  updateIMSystemSettings,
  type IMSystemSettings,
  type TelegramBotInfo,
  type UpdateIMSystemSettingsRequest,
} from '@/api/im';
import { showErrorToast, showSuccessToast } from '@/utils/toast';
import WeChatClawBotSettings from './WeChatClawBotSettings.vue';

type SubTabKey = 'wechat' | 'settings';
type RealtimeEvent = IMSystemSettings['im_realtime_events'][number];

const subTabs = [
  { key: 'wechat' as SubTabKey, label: '微信' },
  { key: 'settings' as SubTabKey, label: '飞书 / Telegram' },
];

const activeSubTab = ref<SubTabKey>('wechat');

const props = withDefaults(defineProps<{ isAdmin?: boolean }>(), {
  isAdmin: false,
});

const emit = defineEmits<{
  navigateToBinding: []
}>();

const loading = ref(false);
const saving = ref(false);
const larkSecretInput = ref('');
const telegramBotTokenInput = ref('');
const telegramWebhookSecretInput = ref('');
const telegramBotInfo = ref<TelegramBotInfo | null>(null);

const realtimeEventOptions: Array<{ value: RealtimeEvent; label: string }> = [
  { value: 'plan_update', label: '执行计划' },
  { value: 'planning_message', label: '计划说明' },
  { value: 'tool_call', label: '工具调用' },
  { value: 'tool_result', label: '工具结果' },
  { value: 'error', label: '错误信息' },
];

const form = reactive<IMSystemSettings>({
  im_enabled: false,
  im_response_timeout: 300,
  im_max_message_length: 4000,
  lark_enabled: false,
  lark_app_id: '',
  has_lark_app_secret: false,
  lark_app_secret_masked: '',
  wechat_enabled: false,
  telegram_enabled: false,
  has_telegram_bot_token: false,
  telegram_bot_token_masked: '',
  telegram_ingress_mode: 'polling',
  has_telegram_webhook_secret: false,
  telegram_webhook_secret_masked: '',
  telegram_public_base_url: '',
  telegram_send_output_files: false,
  im_progress_mode: 'card_entity',
  im_progress_detail_level: 'detailed',
  im_progress_interval_ms: 1200,
  im_realtime_events: ['plan_update', 'planning_message', 'tool_call', 'tool_result', 'error'],
});

const original = ref<IMSystemSettings>({ ...form });

const hasChanges = computed(() => {
  return (
    JSON.stringify({ ...form, im_realtime_events: [...form.im_realtime_events].sort() }) !==
      JSON.stringify({ ...original.value, im_realtime_events: [...original.value.im_realtime_events].sort() }) ||
    larkSecretInput.value.trim().length > 0 ||
    telegramBotTokenInput.value.trim().length > 0 ||
    telegramWebhookSecretInput.value.trim().length > 0
  );
});

function navigateToBinding() {
  emit('navigateToBinding');
}

function toggleRealtimeEvent(event: RealtimeEvent) {
  const current = new Set(form.im_realtime_events);
  if (current.has(event)) {
    current.delete(event);
  } else {
    current.add(event);
  }
  form.im_realtime_events = Array.from(current) as RealtimeEvent[];
}

async function refreshTelegramBotInfo() {
  try {
    telegramBotInfo.value = await getTelegramBotInfo();
  } catch {
    telegramBotInfo.value = null;
  }
}

async function loadSettings() {
  loading.value = true;
  try {
    const data = await getIMSystemSettings();
    Object.assign(form, data);
    original.value = { ...data, im_realtime_events: [...data.im_realtime_events] };
    larkSecretInput.value = '';
    telegramBotTokenInput.value = '';
    telegramWebhookSecretInput.value = '';
    if (props.isAdmin && data.has_telegram_bot_token) {
      await refreshTelegramBotInfo();
    } else {
      telegramBotInfo.value = null;
    }
  } catch (error: any) {
    showErrorToast(error?.response?.data?.detail || error?.message || '加载 IM 设置失败');
  } finally {
    loading.value = false;
  }
}

async function saveSettings() {
  saving.value = true;
  try {
    const payload: UpdateIMSystemSettingsRequest = {
      im_enabled: form.im_enabled,
      im_response_timeout: form.im_response_timeout,
      im_max_message_length: form.im_max_message_length,
      lark_enabled: form.lark_enabled,
      lark_app_id: form.lark_app_id.trim(),
      wechat_enabled: form.wechat_enabled,
      telegram_enabled: form.telegram_enabled,
      telegram_ingress_mode: form.telegram_ingress_mode,
      telegram_public_base_url: form.telegram_public_base_url.trim(),
      telegram_send_output_files: form.telegram_send_output_files,
      im_progress_mode: form.im_progress_mode,
      im_progress_detail_level: form.im_progress_detail_level,
      im_progress_interval_ms: form.im_progress_interval_ms,
      im_realtime_events: [...form.im_realtime_events].sort() as RealtimeEvent[],
    };
    if (larkSecretInput.value.trim()) {
      payload.lark_app_secret = larkSecretInput.value.trim();
    }
    if (telegramBotTokenInput.value.trim()) {
      payload.telegram_bot_token = telegramBotTokenInput.value.trim();
    }
    if (telegramWebhookSecretInput.value.trim()) {
      payload.telegram_webhook_secret = telegramWebhookSecretInput.value.trim();
    }

    const data = await updateIMSystemSettings(payload);
    Object.assign(form, data);
    original.value = { ...data, im_realtime_events: [...data.im_realtime_events] };
    larkSecretInput.value = '';
    telegramBotTokenInput.value = '';
    telegramWebhookSecretInput.value = '';
    if (data.has_telegram_bot_token) {
      await refreshTelegramBotInfo();
    } else {
      telegramBotInfo.value = null;
    }
    showSuccessToast('IM 设置已保存并重新加载');
  } catch (error: any) {
    showErrorToast(error?.response?.data?.detail || error?.message || '保存 IM 设置失败');
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  if (props.isAdmin) {
    loadSettings();
  }
});
</script>

<style scoped>
.card {
  @apply p-5 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-2xl shadow-sm;
}

.card-header {
  @apply flex items-center justify-between;
}

.card-title {
  @apply text-sm font-bold text-gray-700 dark:text-gray-200;
}

.field {
  @apply flex flex-col gap-1.5 text-sm text-gray-700 dark:text-gray-200;
}

.input {
  @apply h-10 rounded-xl bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 px-3 text-sm text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300 dark:focus:border-blue-600;
}

.hint {
  @apply text-xs text-gray-400 dark:text-gray-500;
}

.toggle {
  @apply flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300;
}
</style>
