<template>
  <div class="flex flex-col gap-6 py-2 px-1">
    <div v-if="loading" class="flex justify-center py-12">
      <Loader2 class="size-8 animate-spin text-gray-300" />
    </div>

    <div v-else class="flex flex-col gap-6">
      <!-- 1. Model Capabilities -->
      <div class="flex flex-col gap-4">
        <h3 class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider px-1 flex items-center gap-2">
          {{ t('Model Params') }}
          <span class="h-px flex-1 bg-gradient-to-r from-gray-200 dark:from-gray-700 to-transparent"></span>
        </h3>

        <!-- Max Tokens -->
        <div class="p-5 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-2xl shadow-sm">
          <div class="flex items-start gap-4">
            <div class="size-10 rounded-xl bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/30 dark:to-indigo-900/30 flex items-center justify-center flex-shrink-0">
              <Sparkles class="size-5 text-blue-500" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm font-bold text-gray-700 dark:text-gray-200">{{ t('Max Tokens') }}</span>
                <span class="text-xs font-mono text-gray-400 bg-gray-50 dark:bg-gray-800 px-2 py-0.5 rounded-md border border-gray-100 dark:border-gray-700">
                  {{ formatTokens(form.max_tokens) }}
                </span>
              </div>
              <p class="text-xs text-gray-400 dark:text-gray-500 mb-3">{{ t('Max Tokens Desc') }}</p>
              <input
                type="range"
                v-model.number="form.max_tokens"
                :min="1024" :max="200000" :step="1024"
                class="w-full h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full appearance-none cursor-pointer accent-blue-500"
              />
              <div class="flex justify-between text-[10px] text-gray-300 dark:text-gray-600 mt-1">
                <span>1K</span>
                <span>100K</span>
                <span>200K</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Output Reserve -->
        <div class="p-5 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-2xl shadow-sm">
          <div class="flex items-start gap-4">
            <div class="size-10 rounded-xl bg-gradient-to-br from-cyan-50 to-sky-50 dark:from-cyan-900/30 dark:to-sky-900/30 flex items-center justify-center flex-shrink-0">
              <Shield class="size-5 text-cyan-500" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm font-bold text-gray-700 dark:text-gray-200">{{ t('Output Reserve') }}</span>
                <span class="text-xs font-mono text-gray-400 bg-gray-50 dark:bg-gray-800 px-2 py-0.5 rounded-md border border-gray-100 dark:border-gray-700">
                  {{ formatTokens(form.output_reserve) }}
                </span>
              </div>
              <p class="text-xs text-gray-400 dark:text-gray-500 mb-3">{{ t('Output Reserve Desc') }}</p>
              <input
                type="range"
                v-model.number="form.output_reserve"
                :min="2048" :max="65536" :step="1024"
                class="w-full h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full appearance-none cursor-pointer accent-cyan-500"
              />
              <div class="flex justify-between text-[10px] text-gray-300 dark:text-gray-600 mt-1">
                <span>2K</span>
                <span>32K</span>
                <span>64K</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 2. Context Management -->
      <div class="flex flex-col gap-4">
        <h3 class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider px-1 flex items-center gap-2">
          {{ t('Context Mgmt') }}
          <span class="h-px flex-1 bg-gradient-to-r from-gray-200 dark:from-gray-700 to-transparent"></span>
        </h3>

        <!-- Max History Rounds -->
        <div class="p-5 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-2xl shadow-sm">
          <div class="flex items-start gap-4">
            <div class="size-10 rounded-xl bg-gradient-to-br from-violet-50 to-purple-50 dark:from-violet-900/30 dark:to-purple-900/30 flex items-center justify-center flex-shrink-0">
              <History class="size-5 text-violet-500" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm font-bold text-gray-700 dark:text-gray-200">{{ t('History Rounds') }}</span>
                <span class="text-xs font-mono text-gray-400 bg-gray-50 dark:bg-gray-800 px-2 py-0.5 rounded-md border border-gray-100 dark:border-gray-700">
                  {{ form.max_history_rounds }}
                </span>
              </div>
              <p class="text-xs text-gray-400 dark:text-gray-500 mb-3">{{ t('History Rounds Desc') }}</p>
              <input
                type="range"
                v-model.number="form.max_history_rounds"
                :min="1" :max="30" :step="1"
                class="w-full h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full appearance-none cursor-pointer accent-violet-500"
              />
              <div class="flex justify-between text-[10px] text-gray-300 dark:text-gray-600 mt-1">
                <span>1</span>
                <span>15</span>
                <span>30</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Tool Output Limit -->
        <div class="p-5 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-2xl shadow-sm">
          <div class="flex items-start gap-4">
            <div class="size-10 rounded-xl bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-900/30 dark:to-teal-900/30 flex items-center justify-center flex-shrink-0">
              <FileText class="size-5 text-emerald-500" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm font-bold text-gray-700 dark:text-gray-200">{{ t('Tool Output Limit') }}</span>
                <span class="text-xs font-mono text-gray-400 bg-gray-50 dark:bg-gray-800 px-2 py-0.5 rounded-md border border-gray-100 dark:border-gray-700">
                  {{ formatTokens(form.max_output_chars) }}
                </span>
              </div>
              <p class="text-xs text-gray-400 dark:text-gray-500 mb-3">{{ t('Tool Output Limit Desc') }}</p>
              <input
                type="range"
                v-model.number="form.max_output_chars"
                :min="5000" :max="100000" :step="5000"
                class="w-full h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full appearance-none cursor-pointer accent-emerald-500"
              />
              <div class="flex justify-between text-[10px] text-gray-300 dark:text-gray-600 mt-1">
                <span>5K</span>
                <span>50K</span>
                <span>100K</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 3. Execution Control -->
      <div class="flex flex-col gap-4">
        <h3 class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider px-1 flex items-center gap-2">
          {{ t('Exec Control') }}
          <span class="h-px flex-1 bg-gradient-to-r from-gray-200 dark:from-gray-700 to-transparent"></span>
        </h3>

        <!-- Agent Stream Timeout -->
        <div class="p-5 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-2xl shadow-sm">
          <div class="flex items-start gap-4">
            <div class="size-10 rounded-xl bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-900/30 dark:to-orange-900/30 flex items-center justify-center flex-shrink-0">
              <Timer class="size-5 text-amber-500" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm font-bold text-gray-700 dark:text-gray-200">{{ t('Task Timeout') }}</span>
                <span class="text-xs font-mono text-gray-400 bg-gray-50 dark:bg-gray-800 px-2 py-0.5 rounded-md border border-gray-100 dark:border-gray-700">
                  {{ formatDuration(form.agent_stream_timeout) }}
                </span>
              </div>
              <p class="text-xs text-gray-400 dark:text-gray-500 mb-3">{{ t('Task Timeout Desc') }}</p>
              <input
                type="range"
                v-model.number="form.agent_stream_timeout"
                :min="60" :max="21600" :step="60"
                class="w-full h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full appearance-none cursor-pointer accent-amber-500"
              />
              <div class="flex justify-between text-[10px] text-gray-300 dark:text-gray-600 mt-1">
                <span>1 min</span>
                <span>3 h</span>
                <span>6 h</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Sandbox Exec Timeout -->
        <div class="p-5 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-2xl shadow-sm">
          <div class="flex items-start gap-4">
            <div class="size-10 rounded-xl bg-gradient-to-br from-rose-50 to-pink-50 dark:from-rose-900/30 dark:to-pink-900/30 flex items-center justify-center flex-shrink-0">
              <Terminal class="size-5 text-rose-500" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm font-bold text-gray-700 dark:text-gray-200">{{ t('Command Timeout') }}</span>
                <span class="text-xs font-mono text-gray-400 bg-gray-50 dark:bg-gray-800 px-2 py-0.5 rounded-md border border-gray-100 dark:border-gray-700">
                  {{ formatDuration(form.sandbox_exec_timeout) }}
                </span>
              </div>
              <p class="text-xs text-gray-400 dark:text-gray-500 mb-3">{{ t('Command Timeout Desc') }}</p>
              <input
                type="range"
                v-model.number="form.sandbox_exec_timeout"
                :min="30" :max="1800" :step="30"
                class="w-full h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full appearance-none cursor-pointer accent-rose-500"
              />
              <div class="flex justify-between text-[10px] text-gray-300 dark:text-gray-600 mt-1">
                <span>30s</span>
                <span>15 min</span>
                <span>30 min</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="flex flex-col gap-4">
        <h3 class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider px-1 flex items-center gap-2">
          {{ t('Research Workspace') }}
          <span class="h-px flex-1 bg-gradient-to-r from-gray-200 dark:from-gray-700 to-transparent"></span>
        </h3>

        <div class="p-5 bg-white dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-2xl shadow-sm">
          <div class="flex items-start gap-4">
            <div class="size-10 rounded-xl bg-gradient-to-br from-fuchsia-50 to-pink-50 dark:from-fuchsia-900/30 dark:to-pink-900/30 flex items-center justify-center flex-shrink-0">
              <FolderOpen class="size-5 text-fuchsia-500" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm font-bold text-gray-700 dark:text-gray-200">{{ t('Obsidian Vault Path') }}</span>
              </div>
              <p class="text-xs text-gray-400 dark:text-gray-500 mb-3">{{ t('Obsidian Vault Path Desc') }}</p>
              <div class="flex flex-col gap-2 md:flex-row">
                <input
                  v-model="form.obsidian_vault_dir"
                  type="text"
                  class="flex-1 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/60 px-3 py-2.5 text-sm text-gray-700 dark:text-gray-200 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-fuchsia-500/40 focus:border-fuchsia-400"
                  :placeholder="t('Obsidian Vault Path Placeholder')"
                />
                <div class="flex gap-2">
                  <button
                    type="button"
                    class="px-3 py-2 text-sm font-medium rounded-xl border border-fuchsia-200 dark:border-fuchsia-800 text-fuchsia-700 dark:text-fuchsia-300 hover:bg-fuchsia-50 dark:hover:bg-fuchsia-950/40 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    :disabled="bridgeBusy"
                    @click="browseObsidianVault"
                  >
                    <Loader2 v-if="bridgeBusy" class="size-4 animate-spin inline-block mr-1" />
                    {{ bridgeBusy ? t('Browsing...') : t('Browse') }}
                  </button>
                  <button
                    type="button"
                    class="px-3 py-2 text-sm font-medium rounded-xl border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-900/60 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    :disabled="bridgeTesting || !form.obsidian_vault_dir.trim()"
                    @click="validateObsidianVault"
                  >
                    <Loader2 v-if="bridgeTesting" class="size-4 animate-spin inline-block mr-1" />
                    {{ bridgeTesting ? t('Checking...') : t('Test Vault') }}
                  </button>
                </div>
              </div>
              <p class="text-[11px] text-gray-400 dark:text-gray-500 mt-2">
                {{ t('Obsidian Vault Path Hint') }}
              </p>
              <p
                v-if="!form.obsidian_vault_dir.trim()"
                class="text-[11px] text-amber-600 dark:text-amber-300 mt-1"
              >
                {{ t('Obsidian Vault Default Notice') }}
              </p>
              <p v-if="bridgeStatusMessage" class="text-[11px] text-gray-500 dark:text-gray-400 mt-1">
                {{ bridgeStatusMessage }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="flex items-center justify-between px-1 pt-2">
        <button
          class="px-4 py-2 text-xs font-medium text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition-all"
          @click="resetToDefaults"
        >
          {{ t('Reset Defaults') }}
        </button>
        <button
          class="px-5 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-blue-500 to-indigo-600 rounded-xl shadow-md shadow-blue-500/20 hover:shadow-lg hover:shadow-blue-500/30 active:scale-[0.97] transition-all duration-200 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          :disabled="saving || !hasChanges"
          @click="saveSettings"
        >
          <Loader2 v-if="saving" class="size-4 animate-spin" />
          <span v-else>{{ t('Save') }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { Loader2, Timer, Terminal, Sparkles, Shield, History, FileText, FolderOpen } from 'lucide-vue-next';
import { getTaskSettings, updateTaskSettings, type TaskSettings } from '@/api/taskSettings';
import { getDesktopBridgeHealth, pickObsidianVaultDirectory, testObsidianVault } from '@/api/desktopBridge';
import { showSuccessToast, showErrorToast } from '@/utils/toast';

const { t } = useI18n();

const loading = ref(false);
const saving = ref(false);
const bridgeBusy = ref(false);
const bridgeTesting = ref(false);
const bridgeStatusMessage = ref('');

const DEFAULTS: TaskSettings = {
  agent_stream_timeout: 10800,
  sandbox_exec_timeout: 900,
  max_tokens: 64000,
  output_reserve: 16384,
  max_history_rounds: 10,
  max_output_chars: 50000,
  obsidian_vault_dir: '',
};

const original = ref<TaskSettings>({ ...DEFAULTS });

const form = reactive<TaskSettings>({ ...DEFAULTS });

const hasChanges = computed(() => {
  return (Object.keys(DEFAULTS) as (keyof TaskSettings)[]).some(
    (key) => form[key] !== original.value[key]
  );
});

const fetchSettings = async () => {
  loading.value = true;
  try {
    const data = await getTaskSettings();
    Object.assign(form, data);
    original.value = { ...data };
  } catch (err) {
    console.error(err);
    showErrorToast(t('Failed to load task settings'));
  } finally {
    loading.value = false;
  }
};

const saveSettings = async () => {
  saving.value = true;
  try {
    const data = await updateTaskSettings({ ...form });
    Object.assign(form, data);
    original.value = { ...data };
    showSuccessToast(t('Task settings saved'));
  } catch (err: any) {
    console.error(err);
    if (err.response?.data?.detail) {
      showErrorToast(err.response.data.detail);
    } else {
      showErrorToast(t('Failed to save task settings'));
    }
  } finally {
    saving.value = false;
  }
};

const persistObsidianVaultPath = async (vaultDir: string) => {
  const data = await updateTaskSettings({ obsidian_vault_dir: vaultDir });
  Object.assign(form, data);
  original.value = { ...data };
};

const browseObsidianVault = async () => {
  bridgeBusy.value = true;
  try {
    const result = await pickObsidianVaultDirectory({
      title: t('Select Obsidian Vault'),
      initial_dir: form.obsidian_vault_dir,
    });
    if (result.cancelled) {
      bridgeStatusMessage.value = t('Directory selection cancelled');
      return;
    }
    if (result.path) {
      form.obsidian_vault_dir = result.path;
      try {
        await persistObsidianVaultPath(result.path);
        bridgeStatusMessage.value = t('Directory selected and saved');
        showSuccessToast(t('Task settings saved'));
      } catch (saveErr: any) {
        console.error(saveErr);
        bridgeStatusMessage.value = t('Directory selected. Click Save to persist');
        showErrorToast(saveErr.response?.data?.detail || t('Failed to save task settings'));
      }
    }
  } catch (err: any) {
    console.error(err);
    showErrorToast(err.response?.data?.detail || t('Failed to browse Obsidian vault'));
  } finally {
    bridgeBusy.value = false;
  }
};

const validateObsidianVault = async () => {
  if (!form.obsidian_vault_dir.trim()) return;
  bridgeTesting.value = true;
  try {
    const result = await testObsidianVault({
      vault_dir: form.obsidian_vault_dir.trim(),
      create_if_missing: false,
      bootstrap_materials: false,
    });
    bridgeStatusMessage.value = result.has_obsidian_config
      ? t('Obsidian vault is reachable')
      : t('Directory is reachable but .obsidian was not found');
    showSuccessToast(t('Obsidian vault check passed'));
  } catch (err: any) {
    console.error(err);
    showErrorToast(err.response?.data?.detail || t('Failed to validate Obsidian vault'));
  } finally {
    bridgeTesting.value = false;
  }
};

const formatDuration = (seconds: number): string => {
  if (seconds >= 3600) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return m > 0 ? `${h}h ${m}m` : `${h}h`;
  }
  if (seconds >= 60) {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return s > 0 ? `${m}m ${s}s` : `${m}m`;
  }
  return `${seconds}s`;
};

const formatTokens = (tokens: number): string => {
  return tokens >= 1000 ? `${(tokens / 1000).toFixed(0)}K` : `${tokens}`;
};

const resetToDefaults = () => {
  Object.assign(form, DEFAULTS);
};

onMounted(() => {
  fetchSettings();
  getDesktopBridgeHealth()
    .then((status) => {
      bridgeStatusMessage.value = status.available
        ? t('Desktop bridge is ready')
        : (status.error || t('Desktop bridge is unavailable'));
    })
    .catch(() => {
      bridgeStatusMessage.value = t('Desktop bridge is unavailable');
    });
});
</script>
