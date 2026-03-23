<template>
  <div class="flex flex-col gap-6 py-2 px-1 w-full">
    <div v-if="!props.isAdmin" class="p-5 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-2xl shadow-sm">
      <p class="text-sm text-gray-600 dark:text-gray-300">微信配置仅管理员可见。</p>
    </div>

    <template v-else>
      <div v-if="settingsLoading" class="flex justify-center py-12">
        <Loader2 class="size-8 animate-spin text-gray-300" />
      </div>
      <div v-else class="flex flex-col gap-5">
        <!-- Usage Guide -->
        <div class="p-5 bg-gradient-to-br from-blue-50/80 to-indigo-50/60 dark:from-blue-900/10 dark:to-indigo-900/10 border border-blue-100 dark:border-blue-800/40 rounded-2xl">
          <span class="text-sm font-bold text-gray-700 dark:text-gray-200">使用指南</span>
          <ol class="mt-3 flex flex-col gap-3 text-sm text-gray-600 dark:text-gray-300 list-none">
            <li class="flex gap-2.5">
              <span class="flex-shrink-0 size-5 rounded-full bg-blue-500 text-white text-xs font-bold flex items-center justify-center">1</span>
              <span>下载并更新到<strong class="text-gray-800 dark:text-gray-100">最新版微信</strong></span>
            </li>
            <li class="flex gap-2.5">
              <span class="flex-shrink-0 size-5 rounded-full bg-blue-500 text-white text-xs font-bold flex items-center justify-center">2</span>
              <div>
                <span>检查是否有 ClawBot 插件：点击微信右下角 <strong class="text-gray-800 dark:text-gray-100">我 → 设置 → 插件</strong>，如果能看到「微信 ClawBot」代表当前微信已支持对接</span>
                <p class="mt-1 text-xs text-amber-600 dark:text-amber-400">该功能目前在灰度中，部分用户可能暂时看不到此插件，请耐心等待微信更新</p>
              </div>
            </li>
            <li class="flex gap-2.5">
              <span class="flex-shrink-0 size-5 rounded-full bg-blue-500 text-white text-xs font-bold flex items-center justify-center">3</span>
              <span>点击下方「<strong class="text-gray-800 dark:text-gray-100">扫码连接</strong>」，使用微信扫码后会自动跳转打开微信 ClawBot AI 聊天窗口</span>
            </li>
            <li class="flex gap-2.5">
              <span class="flex-shrink-0 size-5 rounded-full bg-blue-500 text-white text-xs font-bold flex items-center justify-center">4</span>
              <span>发送消息，开始您的体验吧</span>
            </li>
          </ol>
        </div>

        <!-- Auto-start Toggle -->
        <div class="p-5 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-2xl shadow-sm">
          <div class="flex items-center justify-between">
            <div class="flex flex-col gap-1">
              <span class="text-sm font-bold text-gray-700 dark:text-gray-200">随系统自动启动</span>
              <span class="text-xs text-gray-400 dark:text-gray-500">开启后，服务启动时将自动恢复上次的微信连接</span>
            </div>
            <button
              @click="toggleAutoStart"
              :disabled="autoStartSaving"
              class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors cursor-pointer"
              :class="autoStartEnabled ? 'bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-900/20 dark:border-emerald-800 dark:text-emerald-400' : 'bg-gray-50 border-gray-200 text-gray-500 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-400'">
              <Loader2 v-if="autoStartSaving" class="size-3 animate-spin" />
              <template v-else>{{ autoStartEnabled ? '已开启' : '已关闭' }}</template>
            </button>
          </div>
        </div>

        <!-- QR Code Display -->
        <div
          v-if="ws.qr_image"
          class="p-5 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-2xl shadow-sm">
          <div class="flex flex-col items-center gap-4">
            <span class="text-sm font-bold text-gray-700 dark:text-gray-200">
              {{ ws.status === 'qr_scanned' ? '已扫码，请在微信上确认' : '使用微信扫描二维码' }}
            </span>
            <div class="p-3 bg-white rounded-xl shadow-inner">
              <img :src="ws.qr_image" alt="WeChat QR Code" class="w-56 h-56" />
            </div>
            <p class="text-xs text-gray-400">二维码有效期约 5 分钟，过期会自动刷新</p>
          </div>
        </div>

        <!-- Controls -->
        <div class="p-5 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-2xl shadow-sm">
          <span class="text-sm font-bold text-gray-700 dark:text-gray-200">连接控制</span>
          <div class="mt-3 flex items-center gap-2 flex-wrap">
            <!-- Start (QR Login) -->
            <button
              v-if="!ws.is_running && !ws.is_logging_in"
              @click="startLogin"
              :disabled="operating"
              class="px-4 py-2 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-green-500 to-emerald-600 shadow-md shadow-green-500/20 hover:shadow-lg hover:shadow-green-500/30 active:scale-[0.97] transition-all duration-200 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer">
              <Loader2 v-if="operating" class="size-4 animate-spin" />
              <QrCode v-else class="size-4" />
              <span>扫码连接</span>
            </button>

            <!-- Resume with saved token -->
            <button
              v-if="!ws.is_running && !ws.is_logging_in && ws.has_saved_token"
              @click="resumeConnection"
              :disabled="operating"
              class="px-4 py-2 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-blue-500 to-indigo-600 shadow-md shadow-blue-500/20 hover:shadow-lg hover:shadow-blue-500/30 active:scale-[0.97] transition-all duration-200 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer">
              <Loader2 v-if="operating" class="size-4 animate-spin" />
              <RotateCw v-else class="size-4" />
              <span>恢复连接</span>
            </button>

            <!-- Stop -->
            <button
              v-if="ws.is_running || ws.is_logging_in"
              @click="stopBridge"
              :disabled="operating"
              class="px-4 py-2 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-red-500 to-rose-600 shadow-md shadow-red-500/20 hover:shadow-lg hover:shadow-red-500/30 active:scale-[0.97] transition-all duration-200 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer">
              <Loader2 v-if="operating" class="size-4 animate-spin" />
              <Square v-else class="size-4" />
              <span>停止</span>
            </button>

            <!-- Logout -->
            <button
              v-if="ws.has_saved_token && !ws.is_running && !ws.is_logging_in"
              @click="logoutBridge"
              :disabled="operating"
              class="px-3 py-2 rounded-xl text-xs font-medium text-red-500 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all cursor-pointer">
              <span>清除凭据</span>
            </button>

          </div>

          <div v-if="ws.error" class="mt-3 p-3 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
            <p class="text-xs text-red-600 dark:text-red-400">{{ ws.error }}</p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue';
import { Loader2, Square, QrCode, RotateCw } from 'lucide-vue-next';
import {
  getIMSystemSettings,
  updateIMSystemSettings,
  startWeChatBridge,
  resumeWeChatBridge,
  stopWeChatBridge,
  logoutWeChatBridge,
  getWeChatBridgeStatus,
  type WeChatBridgeStatus,
} from '@/api/im';
import { showErrorToast, showSuccessToast } from '@/utils/toast';

const props = withDefaults(defineProps<{ isAdmin?: boolean }>(), { isAdmin: false });

const settingsLoading = ref(false);
const autoStartEnabled = ref(false);
const autoStartSaving = ref(false);
const operating = ref(false);
const outputLines = ref<string[]>([]);
const outputOffset = ref(0);
const outputRef = ref<HTMLElement | null>(null);
let pollTimer: ReturnType<typeof setInterval> | null = null;

const ws = reactive<WeChatBridgeStatus>({
  status: 'idle',
  is_running: false,
  is_logging_in: false,
  error: null,
  started_at: null,
  qr_content: null,
  qr_image: null,
  account_id: null,
  has_saved_token: false,
  output_total: 0,
  output_offset: 0,
  output: [],
});

const scrollToBottom = () => {
  nextTick(() => {
    if (outputRef.value) {
      outputRef.value.scrollTop = outputRef.value.scrollHeight;
    }
  });
};

const loadSettings = async () => {
  settingsLoading.value = true;
  try {
    const data = await getIMSystemSettings();
    autoStartEnabled.value = data.wechat_enabled;
  } catch (error: any) {
    showErrorToast(error?.response?.data?.detail || error?.message || '加载配置失败');
  } finally {
    settingsLoading.value = false;
  }
};

const toggleAutoStart = async () => {
  autoStartSaving.value = true;
  try {
    const next = !autoStartEnabled.value;
    await updateIMSystemSettings({ wechat_enabled: next });
    autoStartEnabled.value = next;
    showSuccessToast(next ? '已开启自动启动' : '已关闭自动启动');
  } catch (error: any) {
    showErrorToast(error?.response?.data?.detail || error?.message || '保存失败');
  } finally {
    autoStartSaving.value = false;
  }
};

const poll = async () => {
  try {
    const data = await getWeChatBridgeStatus(outputOffset.value);
    const wasConnected = ws.is_running;
    ws.status = data.status;
    ws.is_running = data.is_running;
    ws.is_logging_in = data.is_logging_in;
    ws.error = data.error;
    ws.started_at = data.started_at;
    ws.qr_content = data.qr_content;
    ws.qr_image = data.qr_image;
    ws.account_id = data.account_id;
    ws.has_saved_token = data.has_saved_token;
    ws.output_total = data.output_total;

    if (data.output.length > 0) {
      outputLines.value.push(...data.output);
      outputOffset.value = data.output_total;
      scrollToBottom();
    }

    if (!wasConnected && data.is_running && !autoStartEnabled.value) {
      autoStartEnabled.value = true;
      updateIMSystemSettings({ wechat_enabled: true }).catch(() => {});
    }

    if (data.status === 'idle' || data.status === 'error') {
      stopPolling();
    }
  } catch {
    // silent
  }
};

const startPolling = () => {
  stopPolling();
  pollTimer = setInterval(poll, 1500);
};

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
};

const startLogin = async () => {
  operating.value = true;
  outputLines.value = [];
  outputOffset.value = 0;
  try {
    const result = await startWeChatBridge();
    if (result.status === 'error') {
      showErrorToast(result.error || '启动失败');
      ws.error = result.error || '启动失败';
    } else {
      ws.is_logging_in = true;
      ws.status = result.status;
      ws.qr_content = result.qr_content;
      ws.qr_image = result.qr_image;
      startPolling();
    }
  } catch (error: any) {
    showErrorToast(error?.response?.data?.detail || error?.message || '启动失败');
  } finally {
    operating.value = false;
  }
};

const resumeConnection = async () => {
  operating.value = true;
  outputLines.value = [];
  outputOffset.value = 0;
  try {
    const result = await resumeWeChatBridge();
    if (result.status === 'connected') {
      ws.is_running = true;
      ws.status = 'connected';
      startPolling();
    } else {
      showErrorToast(result.message || '恢复连接失败，请重新扫码');
    }
  } catch (error: any) {
    showErrorToast(error?.response?.data?.detail || error?.message || '恢复失败');
  } finally {
    operating.value = false;
  }
};

const stopBridge = async () => {
  operating.value = true;
  try {
    await stopWeChatBridge();
    ws.is_running = false;
    ws.is_logging_in = false;
    ws.status = 'idle';
    ws.qr_content = null;
    ws.qr_image = null;
    stopPolling();
    await poll();
  } catch (error: any) {
    showErrorToast(error?.response?.data?.detail || error?.message || '停止失败');
  } finally {
    operating.value = false;
  }
};

const logoutBridge = async () => {
  operating.value = true;
  try {
    await logoutWeChatBridge();
    ws.has_saved_token = false;
    ws.account_id = null;
    showSuccessToast('已清除微信凭据');
    await poll();
  } catch (error: any) {
    showErrorToast(error?.response?.data?.detail || error?.message || '清除失败');
  } finally {
    operating.value = false;
  }
};

const loadStatus = async () => {
  try {
    const data = await getWeChatBridgeStatus(0);
    Object.assign(ws, data);
    if (data.output.length > 0) {
      outputLines.value = [...data.output];
      outputOffset.value = data.output_total;
      scrollToBottom();
    }
    if (data.is_running || data.is_logging_in) {
      startPolling();
    }
  } catch {
    // silent
  }
};

onMounted(() => {
  if (props.isAdmin) {
    loadSettings();
    loadStatus();
  }
});

onUnmounted(() => {
  stopPolling();
});
</script>
