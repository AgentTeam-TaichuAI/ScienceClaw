<template>
  <div class="flex flex-col gap-4 py-2 px-1 w-full">
    <!-- Sub-tab navigation -->
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
        <div class="flex items-center gap-2">
          <component :is="tab.icon" :size="15" />
          <span>{{ tab.label }}</span>
        </div>
        <div
          v-if="activeSubTab === tab.key"
          class="absolute bottom-0 left-2 right-2 h-0.5 bg-blue-500 dark:bg-blue-400 rounded-full"
        />
      </button>
    </div>

    <!-- WeChat panel -->
    <div v-show="activeSubTab === 'wechat'">
      <WeChatClawBotSettings :is-admin="props.isAdmin" />
    </div>

    <!-- Feishu panel -->
    <div v-show="activeSubTab === 'feishu'" class="flex flex-col gap-5">
      <div v-if="loading" class="flex justify-center py-12">
        <Loader2 class="size-8 animate-spin text-gray-300" />
      </div>
      <template v-else>
        <div class="p-4 rounded-xl bg-gray-50/80 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 flex items-center justify-between">
          <div class="flex flex-col gap-1">
            <span class="text-sm font-semibold text-gray-700 dark:text-gray-200">飞书账号绑定</span>
            <span class="text-xs text-gray-500 dark:text-gray-400">在 Web 端维护飞书用户 ID 绑定关系</span>
          </div>
          <button
            @click="navigateToBinding"
            class="px-4 py-2 rounded-xl text-sm font-medium bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 shadow-sm hover:shadow-md hover:border-blue-200 dark:hover:border-blue-600 hover:text-blue-600 dark:hover:text-blue-400 transition-all duration-200 cursor-pointer">
            去绑定
          </button>
        </div>

        <template v-if="props.isAdmin">
          <div class="p-5 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-2xl shadow-sm">
            <div class="flex items-center justify-between">
              <span class="text-sm font-bold text-gray-700 dark:text-gray-200">IM 总开关</span>
              <button
                @click="form.im_enabled = !form.im_enabled"
                class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors cursor-pointer"
                :class="form.im_enabled ? 'bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-900/20 dark:border-emerald-800 dark:text-emerald-400' : 'bg-gray-50 border-gray-200 text-gray-500 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-400'">
                {{ form.im_enabled ? '已开启' : '已关闭' }}
              </button>
            </div>
          </div>

          <div class="p-5 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-2xl shadow-sm">
            <div class="flex items-center justify-between mb-2">
              <span class="text-sm font-bold text-gray-700 dark:text-gray-200">IM 响应超时</span>
              <span class="text-xs font-mono text-gray-400">{{ form.im_response_timeout }}s</span>
            </div>
            <input
              type="range"
              v-model.number="form.im_response_timeout"
              :min="30"
              :max="1800"
              :step="30"
              class="w-full h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full appearance-none cursor-pointer accent-blue-500" />
          </div>

          <div class="p-5 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-2xl shadow-sm">
            <div class="flex items-center justify-between mb-2">
              <span class="text-sm font-bold text-gray-700 dark:text-gray-200">IM 最大消息长度</span>
              <span class="text-xs font-mono text-gray-400">{{ form.im_max_message_length }}</span>
            </div>
            <input
              type="range"
              v-model.number="form.im_max_message_length"
              :min="500"
              :max="20000"
              :step="100"
              class="w-full h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full appearance-none cursor-pointer accent-indigo-500" />
          </div>

          <div class="p-5 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-2xl shadow-sm">
            <div class="flex items-center justify-between">
              <span class="text-sm font-bold text-gray-700 dark:text-gray-200">飞书开关</span>
              <button
                @click="form.lark_enabled = !form.lark_enabled"
                class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors cursor-pointer"
                :class="form.lark_enabled ? 'bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-900/20 dark:border-emerald-800 dark:text-emerald-400' : 'bg-gray-50 border-gray-200 text-gray-500 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-400'">
                {{ form.lark_enabled ? '已开启' : '已关闭' }}
              </button>
            </div>
            <div class="mt-4">
              <label class="text-xs text-gray-500 dark:text-gray-400">LARK_APP_ID</label>
              <input
                v-model="form.lark_app_id"
                placeholder="cli_xxx"
                class="mt-1 w-full h-10 rounded-xl bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 px-3 text-sm text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300 dark:focus:border-blue-600" />
            </div>
            <div class="mt-4">
              <label class="text-xs text-gray-500 dark:text-gray-400">LARK_APP_SECRET</label>
              <input
                v-model="secretInput"
                type="password"
                placeholder="留空表示不修改"
                class="mt-1 w-full h-10 rounded-xl bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 px-3 text-sm text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300 dark:focus:border-blue-600" />
              <p class="mt-1 text-xs text-gray-400 dark:text-gray-500">
                当前密钥状态：{{ form.has_lark_app_secret ? '已配置' : '未配置' }}
              </p>
            </div>
          </div>

          <div class="p-5 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-2xl shadow-sm">
            <div class="flex items-center justify-between mb-2">
              <span class="text-sm font-bold text-gray-700 dark:text-gray-200">响应模式</span>
            </div>
            <div class="flex gap-2">
              <button
                @click="form.im_progress_mode = 'text_multi'"
                class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors cursor-pointer"
                :class="form.im_progress_mode === 'text_multi' ? 'bg-blue-50 border-blue-200 text-blue-700 dark:bg-blue-900/20 dark:border-blue-800 dark:text-blue-400' : 'bg-gray-50 border-gray-200 text-gray-500 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-400'">
                多条文本
              </button>
              <button
                @click="form.im_progress_mode = 'card_entity'"
                class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors cursor-pointer"
                :class="form.im_progress_mode === 'card_entity' ? 'bg-blue-50 border-blue-200 text-blue-700 dark:bg-blue-900/20 dark:border-blue-800 dark:text-blue-400' : 'bg-gray-50 border-gray-200 text-gray-500 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-400'">
                卡片实体
              </button>
            </div>
            <div class="mt-4">
              <div class="text-xs text-gray-500 dark:text-gray-400 mb-2">卡片详情级别</div>
              <div class="flex gap-2">
                <button
                  @click="form.im_progress_detail_level = 'compact'"
                  class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors cursor-pointer"
                  :class="form.im_progress_detail_level === 'compact' ? 'bg-violet-50 border-violet-200 text-violet-700 dark:bg-violet-900/20 dark:border-violet-800 dark:text-violet-400' : 'bg-gray-50 border-gray-200 text-gray-500 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-400'">
                  简洁
                </button>
                <button
                  @click="form.im_progress_detail_level = 'detailed'"
                  class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors cursor-pointer"
                  :class="form.im_progress_detail_level === 'detailed' ? 'bg-violet-50 border-violet-200 text-violet-700 dark:bg-violet-900/20 dark:border-violet-800 dark:text-violet-400' : 'bg-gray-50 border-gray-200 text-gray-500 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-400'">
                  详细
                </button>
              </div>
            </div>
            <p class="mt-2 text-xs text-gray-400 dark:text-gray-500">
              卡片实体模式需要飞书应用开通 cardkit:card:write 权限；未开通时系统会自动降级为普通卡片或文本。
            </p>
            <div class="mt-4">
              <div class="flex items-center justify-between mb-2">
                <span class="text-xs text-gray-500 dark:text-gray-400">进度推送间隔</span>
                <span class="text-xs font-mono text-gray-400">{{ form.im_progress_interval_ms }}ms</span>
              </div>
              <input
                type="range"
                v-model.number="form.im_progress_interval_ms"
                :min="300"
                :max="10000"
                :step="100"
                class="w-full h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full appearance-none cursor-pointer accent-violet-500" />
            </div>
            <div class="mt-4">
              <div class="text-xs text-gray-500 dark:text-gray-400 mb-2">实时发送内容</div>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="option in realtimeEventOptions"
                  :key="option.value"
                  @click="toggleRealtimeEvent(option.value)"
                  class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors cursor-pointer"
                  :class="form.im_realtime_events.includes(option.value) ? 'bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-900/20 dark:border-emerald-800 dark:text-emerald-400' : 'bg-gray-50 border-gray-200 text-gray-500 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-400'">
                  {{ option.label }}
                </button>
              </div>
              <p class="mt-2 text-xs text-gray-400 dark:text-gray-500">
                仅勾选的内容会在任务执行中实时推送；不勾选时只在最后发送最终结果。未勾选事件仍会纳入执行统计。
              </p>
            </div>
          </div>

          <div class="flex items-center justify-between">
            <button
              @click="loadSettings"
              class="px-4 py-2 text-xs font-medium text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition-all cursor-pointer">
              刷新
            </button>
            <button
              @click="saveSettings"
              :disabled="saving || !hasChanges"
              class="px-5 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-blue-500 to-indigo-600 rounded-xl shadow-md shadow-blue-500/20 hover:shadow-lg hover:shadow-blue-500/30 active:scale-[0.97] transition-all duration-200 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed">
              <Loader2 v-if="saving" class="size-4 animate-spin" />
              <span v-else>保存</span>
            </button>
          </div>
        </template>

        <div v-else class="p-5 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-2xl shadow-sm">
          <p class="text-sm text-gray-600 dark:text-gray-300">系统级 IM 配置仅管理员可见。</p>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, markRaw, onMounted, reactive, ref } from 'vue';
import { Loader2, MessageCircle, Bird } from 'lucide-vue-next';
import { getIMSystemSettings, updateIMSystemSettings, type IMSystemSettings, type UpdateIMSystemSettingsRequest } from '@/api/im';
import { showErrorToast, showSuccessToast } from '@/utils/toast';
import WeChatClawBotSettings from './WeChatClawBotSettings.vue';

type SubTabKey = 'wechat' | 'feishu';

const subTabs = [
  { key: 'wechat' as SubTabKey, label: '微信', icon: markRaw(MessageCircle) },
  { key: 'feishu' as SubTabKey, label: '飞书', icon: markRaw(Bird) },
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
const secretInput = ref('');
type RealtimeEvent = IMSystemSettings['im_realtime_events'][number];
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
  im_progress_mode: 'card_entity',
  im_progress_detail_level: 'detailed',
  im_progress_interval_ms: 1200,
  im_realtime_events: ['plan_update'],
});

const original = ref<IMSystemSettings>({ ...form });
const normalizeRealtimeEvents = (events: RealtimeEvent[]) => [...new Set(events)].sort().join('|');

const hasChanges = computed(() => {
  return (
    form.im_enabled !== original.value.im_enabled ||
    form.im_response_timeout !== original.value.im_response_timeout ||
    form.im_max_message_length !== original.value.im_max_message_length ||
    form.lark_enabled !== original.value.lark_enabled ||
    form.lark_app_id !== original.value.lark_app_id ||
    form.im_progress_mode !== original.value.im_progress_mode ||
    form.im_progress_detail_level !== original.value.im_progress_detail_level ||
    form.im_progress_interval_ms !== original.value.im_progress_interval_ms ||
    normalizeRealtimeEvents(form.im_realtime_events) !== normalizeRealtimeEvents(original.value.im_realtime_events) ||
    secretInput.value.trim().length > 0
  );
});

const toggleRealtimeEvent = (event: RealtimeEvent) => {
  const current = new Set(form.im_realtime_events);
  if (current.has(event)) {
    current.delete(event);
  } else {
    current.add(event);
  }
  form.im_realtime_events = Array.from(current);
};

const navigateToBinding = () => {
  emit('navigateToBinding');
};

const loadSettings = async () => {
  loading.value = true;
  try {
    const data = await getIMSystemSettings();
    Object.assign(form, data);
    original.value = { ...data };
    secretInput.value = '';
  } catch (error: any) {
    showErrorToast(error?.response?.data?.detail || error?.message || '加载 IM 配置失败');
  } finally {
    loading.value = false;
  }
};

const saveSettings = async () => {
  saving.value = true;
  try {
    const payload: UpdateIMSystemSettingsRequest = {
      im_enabled: form.im_enabled,
      im_response_timeout: form.im_response_timeout,
      im_max_message_length: form.im_max_message_length,
      lark_enabled: form.lark_enabled,
      lark_app_id: form.lark_app_id.trim(),
      im_progress_mode: form.im_progress_mode,
      im_progress_detail_level: form.im_progress_detail_level,
      im_progress_interval_ms: form.im_progress_interval_ms,
      im_realtime_events: form.im_realtime_events,
    };
    if (secretInput.value.trim()) {
      payload.lark_app_secret = secretInput.value.trim();
    }
    const data = await updateIMSystemSettings(payload);
    Object.assign(form, data);
    original.value = { ...data };
    secretInput.value = '';
    showSuccessToast('IM 配置已保存并已重载');
  } catch (error: any) {
    showErrorToast(error?.response?.data?.detail || error?.message || '保存 IM 配置失败');
  } finally {
    saving.value = false;
  }
};

onMounted(() => {
  if (props.isAdmin) {
    loadSettings();
  }
});
</script>
