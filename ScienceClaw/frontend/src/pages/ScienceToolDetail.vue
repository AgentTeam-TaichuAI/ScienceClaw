<template>
  <div class="flex flex-col h-full w-full overflow-hidden">
    <!-- Hero Header -->
    <div class="flex-shrink-0 relative overflow-hidden">
      <div class="absolute inset-0" :style="{ background: heroGradient }"></div>
      <div class="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNCI+PHBhdGggZD0iTTM2IDM0djZoLTZ2LTZoNnptMC0zMHY2aC02VjRoNnoiLz48L2c+PC9nPjwvc3ZnPg==')] opacity-50"></div>
      <div class="relative px-6 py-4 flex items-center gap-4">
        <button @click="goBack" class="p-2 -ml-2 rounded-lg hover:bg-white/10 transition-colors text-white/70 hover:text-white">
          <ArrowLeft class="size-5" />
        </button>
        <div class="size-11 rounded-xl bg-white/15 backdrop-blur-sm flex items-center justify-center text-white text-lg font-bold shadow-lg">
          {{ toolName.charAt(0) }}
        </div>
        <div class="min-w-0">
          <h1 class="text-base font-bold text-white truncate">{{ toolName }}</h1>
          <p class="text-white/50 text-xs">Scientific Tool Library</p>
        </div>
      </div>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-hidden flex bg-[#f8f9fb] dark:bg-[#111]">
      <!-- Left: Spec & Form -->
      <div class="flex-1 overflow-y-auto">
        <div class="max-w-3xl mx-auto p-6 space-y-5">

          <!-- Loading Skeleton -->
          <template v-if="loading">
            <div class="bg-white dark:bg-[#1e1e1e] rounded-xl border border-gray-100 dark:border-gray-800 p-5 animate-pulse space-y-3">
              <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/3"></div>
              <div class="h-3 bg-gray-100 dark:bg-gray-800 rounded"></div>
              <div class="h-3 bg-gray-100 dark:bg-gray-800 rounded w-5/6"></div>
            </div>
            <div class="bg-white dark:bg-[#1e1e1e] rounded-xl border border-gray-100 dark:border-gray-800 p-5 animate-pulse space-y-4">
              <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4"></div>
              <div v-for="i in 3" :key="i" class="space-y-2">
                <div class="h-3 bg-gray-100 dark:bg-gray-800 rounded w-1/3"></div>
                <div class="h-9 bg-gray-100 dark:bg-gray-800 rounded"></div>
              </div>
            </div>
          </template>

          <template v-else-if="spec">
            <!-- Description + Metadata -->
            <div class="detail-card bg-white dark:bg-[#1e1e1e] rounded-xl border border-gray-100 dark:border-gray-800 p-5 shadow-sm" style="--delay:0ms">
              <div class="flex items-center gap-2 mb-3">
                <div class="size-6 rounded-lg bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center">
                  <svg class="size-3.5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                </div>
                <h2 class="text-sm font-semibold text-[var(--text-primary)]">Description</h2>
              </div>
              <p class="text-sm text-[var(--text-secondary)] leading-relaxed mb-3">{{ spec.description }}</p>
              <div class="flex flex-wrap gap-2">
                <span v-if="spec.category" class="text-[10px] px-2 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 font-medium">{{ spec.category }}</span>
                <span v-if="spec.source_file" class="text-[10px] px-2 py-1 rounded-lg bg-gray-50 dark:bg-gray-800 text-[var(--text-tertiary)] font-mono" :title="spec.source_file">{{ spec.source_file.split('/').pop() }}</span>
                <span v-if="spec.test_examples?.length" class="text-[10px] px-2 py-1 rounded-lg bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400">{{ spec.test_examples.length }} example{{ spec.test_examples.length > 1 ? 's' : '' }}</span>
                <span v-if="spec.return_schema" class="text-[10px] px-2 py-1 rounded-lg bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400">has return schema</span>
              </div>
            </div>

            <!-- Test Examples -->
            <div v-if="spec.test_examples?.length" class="detail-card bg-white dark:bg-[#1e1e1e] rounded-xl border border-gray-100 dark:border-gray-800 overflow-hidden shadow-sm" style="--delay:40ms">
              <div class="px-5 py-3.5 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <div class="size-6 rounded-lg bg-green-50 dark:bg-green-900/20 flex items-center justify-center">
                    <svg class="size-3.5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                  </div>
                  <h2 class="text-sm font-semibold text-[var(--text-primary)]">Examples</h2>
                </div>
              </div>
              <div class="p-4 space-y-2">
                <div v-for="(ex, i) in spec.test_examples.slice(0, 5)" :key="i" 
                  class="group flex items-center gap-3 px-3 py-2.5 rounded-lg bg-gray-50 dark:bg-gray-900/50 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors cursor-pointer"
                  @click="applyExample(ex)">
                  <pre class="text-xs font-mono text-[var(--text-secondary)] flex-1 truncate">{{ JSON.stringify(ex) }}</pre>
                  <span class="text-[10px] text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">Click to use</span>
                </div>
              </div>
            </div>

            <!-- Parameters Form -->
            <div class="detail-card bg-white dark:bg-[#1e1e1e] rounded-xl border border-gray-100 dark:border-gray-800 overflow-hidden shadow-sm" style="--delay:80ms">
              <div class="px-5 py-3.5 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <div class="size-6 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 flex items-center justify-center">
                    <svg class="size-3.5 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" /></svg>
                  </div>
                  <h2 class="text-sm font-semibold text-[var(--text-primary)]">Parameters</h2>
                </div>
                <span class="text-[10px] px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-800 text-[var(--text-tertiary)] tabular-nums">{{ paramEntries.length }}</span>
              </div>

              <div class="p-5 space-y-5">
                <div v-for="[name, info] in paramEntries" :key="name" class="group/field">
                  <label class="flex items-center gap-2 mb-1.5">
                    <span class="text-sm font-medium text-[var(--text-primary)]">{{ name }}</span>
                    <span v-if="isRequired(name)" class="text-[10px] px-1.5 py-0.5 rounded-md bg-gradient-to-r from-red-50 to-orange-50 dark:from-red-900/20 dark:to-orange-900/20 text-red-500 dark:text-red-400 font-semibold">required</span>
                    <span class="text-[10px] px-1.5 py-0.5 rounded-md bg-gray-50 dark:bg-gray-800/50 text-[var(--text-tertiary)] font-mono">{{ info.type }}</span>
                  </label>
                  <p v-if="info.description" class="text-xs text-[var(--text-tertiary)] mb-2 leading-relaxed">{{ info.description }}</p>
                  
                  <select v-if="info.enum" v-model="formValues[name]" class="form-input">
                    <option value="">Select...</option>
                    <option v-for="opt in info.enum" :key="opt" :value="opt">{{ opt }}</option>
                  </select>

                  <div v-else-if="info.type === 'boolean'" class="flex items-center gap-3">
                    <button @click="formValues[name] = !formValues[name]"
                      class="relative inline-flex h-6 w-11 items-center rounded-full transition-all duration-300 shadow-inner"
                      :class="formValues[name] ? 'bg-gradient-to-r from-blue-500 to-indigo-500' : 'bg-gray-200 dark:bg-gray-700'">
                      <span class="inline-block h-4 w-4 transform rounded-full bg-white transition-all duration-300 shadow-md"
                        :class="formValues[name] ? 'translate-x-6' : 'translate-x-1'"></span>
                    </button>
                    <span class="text-xs text-[var(--text-tertiary)] font-mono">{{ formValues[name] }}</span>
                  </div>

                  <input v-else-if="info.type === 'integer' || info.type === 'number'" 
                    v-model.number="formValues[name]" type="number" class="form-input" :placeholder="`Enter ${name}...`">

                  <textarea v-else-if="info.type === 'array'" v-model="formValues[name]"
                    class="form-input font-mono" rows="2" :placeholder='`["value1", "value2"]`'></textarea>

                  <input v-else v-model="formValues[name]" type="text" class="form-input" :placeholder="`Enter ${name}...`">
                </div>
              </div>

              <!-- Action Bar -->
              <div class="px-5 py-4 border-t border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-black/20 flex items-center gap-3">
                <button @click="runTool" :disabled="running"
                  class="run-btn flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-semibold text-white transition-all duration-300 shadow-lg"
                  :class="running ? 'bg-gray-400 shadow-none cursor-not-allowed' : 'bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-600 hover:shadow-xl hover:shadow-indigo-500/25 active:scale-[0.97]'">
                  <div v-if="running" class="size-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></div>
                  <Play v-else :size="16" />
                  {{ running ? 'Running...' : 'Run Tool' }}
                </button>
                <button @click="fillExample" 
                  class="group/fill flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-medium text-[var(--text-secondary)] border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#2a2a2a] hover:border-blue-300 hover:text-blue-600 hover:shadow-sm transition-all duration-200"
                  :disabled="!spec?.test_examples?.length">
                  <svg class="size-3.5 opacity-50 group-hover/fill:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                  Example
                  <span v-if="spec?.test_examples?.length > 1" class="text-[10px] opacity-50 tabular-nums">{{ (_exampleIdx % spec.test_examples.length) + 1 }}/{{ spec.test_examples.length }}</span>
                </button>
                <button @click="clearForm" class="px-4 py-2.5 rounded-xl text-sm text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] transition-colors">
                  Clear
                </button>
                <div v-if="execTime !== null" class="ml-auto flex items-center gap-1.5 text-xs text-[var(--text-tertiary)]">
                  <svg class="size-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                  {{ execTime }}ms
                </div>
              </div>
            </div>
          </template>

          <div v-else-if="error" class="detail-card bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800/50 rounded-xl p-5" style="--delay:0ms">
            <p class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>
          </div>
        </div>
      </div>

      <!-- Right: Results Panel -->
      <div class="w-[500px] border-l border-gray-100 dark:border-gray-800 bg-white dark:bg-[#1a1a1a] flex flex-col overflow-hidden flex-shrink-0">
        <div class="px-5 py-3.5 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div class="size-6 rounded-lg flex items-center justify-center"
              :class="resultError ? 'bg-red-50 dark:bg-red-900/20' : resultData !== null ? 'bg-green-50 dark:bg-green-900/20' : 'bg-gray-50 dark:bg-gray-800'">
              <svg v-if="resultError" class="size-3.5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              <svg v-else-if="resultData !== null" class="size-3.5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg>
              <Terminal v-else :size="14" class="text-gray-400" />
            </div>
            <h3 class="text-sm font-semibold text-[var(--text-primary)]">Result</h3>
          </div>
          <button v-if="resultData !== null" @click="copyResult" 
            class="text-xs px-2.5 py-1 rounded-lg border border-transparent hover:border-gray-200 dark:hover:border-gray-700 text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] transition-all duration-200">
            {{ copied ? 'Copied!' : 'Copy JSON' }}
          </button>
        </div>
        <div class="flex-1 overflow-auto">
          <!-- Empty -->
          <div v-if="resultData === null && !resultError && !running" class="flex flex-col items-center justify-center h-full gap-3 text-[var(--text-tertiary)]">
            <div class="size-20 rounded-2xl bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
              <Terminal :size="32" class="opacity-20" />
            </div>
            <div class="text-center">
              <p class="text-sm font-medium">No results yet</p>
              <p class="text-xs opacity-60 mt-1">Fill in parameters and click "Run Tool"</p>
            </div>
          </div>

          <!-- Running -->
          <div v-else-if="running" class="flex flex-col items-center justify-center h-full gap-3">
            <div class="relative size-12">
              <div class="absolute inset-0 rounded-full border-2 border-indigo-100 dark:border-indigo-900"></div>
              <div class="absolute inset-0 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin"></div>
            </div>
            <p class="text-sm text-[var(--text-tertiary)]">Executing tool...</p>
          </div>

          <!-- Error -->
          <div v-else-if="resultError" class="p-5 result-animate">
            <div class="bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800/50 rounded-xl p-4">
              <p class="text-sm text-red-600 dark:text-red-400 font-mono whitespace-pre-wrap leading-relaxed">{{ resultError }}</p>
            </div>
          </div>

          <!-- Success: Smart Result Display -->
          <div v-else-if="resultData !== null" class="result-animate">
            <!-- Array → Table -->
            <div v-if="isArrayResult" class="p-4">
              <div class="flex items-center justify-between mb-2">
                <span class="text-xs text-[var(--text-tertiary)]">{{ resultArray.length }} items</span>
                <button @click="resultView = resultView === 'table' ? 'json' : 'table'" class="text-[10px] px-2 py-1 rounded-lg bg-gray-100 dark:bg-gray-800 text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] transition-colors">
                  {{ resultView === 'table' ? 'JSON' : 'Table' }}
                </button>
              </div>
              <!-- Table view -->
              <div v-if="resultView === 'table'" class="border border-gray-100 dark:border-gray-800 rounded-xl overflow-auto max-h-[calc(100vh-280px)]">
                <table class="w-full text-xs">
                  <thead class="bg-gray-50 dark:bg-gray-900/50 sticky top-0">
                    <tr>
                      <th v-for="col in tableColumns" :key="col" class="px-3 py-2 text-left font-semibold text-[var(--text-tertiary)] border-b border-gray-100 dark:border-gray-800 whitespace-nowrap">{{ col }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, i) in resultArray.slice(0, 200)" :key="i" class="border-b border-gray-50 dark:border-gray-900 hover:bg-blue-50/30 dark:hover:bg-blue-900/10 transition-colors">
                      <td v-for="col in tableColumns" :key="col" class="px-3 py-2 text-[var(--text-secondary)] max-w-[300px] truncate" :title="String(row[col] ?? '')">
                        {{ formatCell(row[col]) }}
                      </td>
                    </tr>
                  </tbody>
                </table>
                <div v-if="resultArray.length > 200" class="text-center py-2 text-[10px] text-[var(--text-tertiary)]">Showing 200 of {{ resultArray.length }}</div>
              </div>
              <!-- JSON fallback -->
              <pre v-else class="text-xs font-mono text-[var(--text-primary)] whitespace-pre-wrap break-all leading-relaxed bg-gray-50 dark:bg-[#111] rounded-xl p-4 border border-gray-100 dark:border-gray-800 max-h-[calc(100vh-280px)] overflow-auto">{{ formattedResult }}</pre>
            </div>
            <!-- Object/String → JSON -->
            <div v-else class="p-4">
              <pre class="text-xs font-mono text-[var(--text-primary)] whitespace-pre-wrap break-all leading-relaxed bg-gray-50 dark:bg-[#111] rounded-xl p-4 border border-gray-100 dark:border-gray-800 max-h-[calc(100vh-280px)] overflow-auto">{{ formattedResult }}</pre>
            </div>
          </div>

          <!-- Return Schema -->
          <div v-if="spec?.return_schema && !running" class="border-t border-gray-100 dark:border-gray-800">
            <button @click="showSchema = !showSchema" class="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-gray-50/50 dark:hover:bg-white/5 transition-colors">
              <span class="text-[10px] font-semibold text-[var(--text-tertiary)] uppercase tracking-wider">Return Schema</span>
              <svg class="size-3.5 text-[var(--text-tertiary)] transition-transform duration-200" :class="showSchema && 'rotate-180'" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" /></svg>
            </button>
            <div v-if="showSchema" class="px-4 pb-4">
              <pre class="text-[10px] font-mono text-[var(--text-tertiary)] whitespace-pre-wrap bg-gray-50 dark:bg-[#111] rounded-lg p-3 max-h-48 overflow-auto leading-relaxed">{{ JSON.stringify(spec.return_schema, null, 2) }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { ArrowLeft, Play, Terminal } from 'lucide-vue-next';
import { getTUToolSpec, runTUTool, TUToolSpec } from '../api/tooluniverse';

const { locale } = useI18n();

const route = useRoute();
const router = useRouter();
const toolName = decodeURIComponent(route.params.toolName as string);

const loading = ref(true);
const error = ref<string | null>(null);
const spec = ref<TUToolSpec | null>(null);
const formValues = reactive<Record<string, any>>({});
const running = ref(false);
const resultData = ref<any>(null);
const resultError = ref<string | null>(null);
const execTime = ref<number | null>(null);
const copied = ref(false);
const resultView = ref<'table' | 'json'>('table');
const showSchema = ref(false);

const isArrayResult = computed(() => Array.isArray(resultData.value) && resultData.value.length > 0 && typeof resultData.value[0] === 'object');
const resultArray = computed(() => isArrayResult.value ? resultData.value as Record<string, any>[] : []);
const tableColumns = computed(() => {
  if (!isArrayResult.value) return [];
  const cols = new Set<string>();
  for (const row of resultArray.value.slice(0, 20)) {
    for (const k of Object.keys(row)) cols.add(k);
  }
  return Array.from(cols);
});
const formatCell = (val: any) => {
  if (val === null || val === undefined) return '-';
  if (typeof val === 'object') return JSON.stringify(val).slice(0, 80);
  return String(val);
};

const gradients = [
  'linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%)',
  'linear-gradient(135deg, #3b82f6 0%, #6366f1 50%, #8b5cf6 100%)',
  'linear-gradient(135deg, #06b6d4 0%, #3b82f6 50%, #6366f1 100%)',
  'linear-gradient(135deg, #10b981 0%, #06b6d4 50%, #3b82f6 100%)',
  'linear-gradient(135deg, #f59e0b 0%, #ef4444 50%, #ec4899 100%)',
];
const heroGradient = computed(() => {
  let h = 0; for (let i = 0; i < toolName.length; i++) h = toolName.charCodeAt(i) + ((h << 5) - h);
  return gradients[Math.abs(h) % gradients.length];
});

const goBack = () => router.back();
const paramEntries = computed(() => spec.value?.parameters?.properties ? Object.entries(spec.value.parameters.properties) : []);
const isRequired = (name: string) => (spec.value?.parameters?.required || []).includes(name);
const formattedResult = computed(() => {
  if (resultData.value === null) return '';
  try { return JSON.stringify(resultData.value, null, 2); } catch { return String(resultData.value); }
});

const loadSpec = async () => {
  loading.value = true;
  error.value = null;
  try {
    spec.value = await getTUToolSpec(toolName);
    for (const [name, info] of Object.entries(spec.value.parameters?.properties || {})) {
      if (!(name in formValues)) {
        formValues[name] = info.type === 'boolean' ? false : info.type === 'integer' || info.type === 'number' ? undefined : '';
      }
    }
  } catch (e: any) { error.value = e.message || 'Failed to load tool specification'; }
  finally { loading.value = false; }
};

onMounted(loadSpec);
watch(locale, loadSpec);

const buildArgs = (): Record<string, any> => {
  const args: Record<string, any> = {};
  for (const [name, info] of paramEntries.value) {
    const val = formValues[name];
    if (val === undefined || val === null || val === '') continue;
    if (info.type === 'array' && typeof val === 'string') { try { args[name] = JSON.parse(val); } catch { args[name] = val; } }
    else if ((info.type === 'integer' || info.type === 'number') && typeof val === 'string') args[name] = Number(val);
    else args[name] = val;
  }
  return args;
};

const runTool = async () => {
  running.value = true; resultData.value = null; resultError.value = null; execTime.value = null;
  const start = Date.now();
  try {
    const res = await runTUTool(toolName, buildArgs());
    execTime.value = Date.now() - start;
    if (res.success) resultData.value = res.result;
    else resultError.value = JSON.stringify(res.result, null, 2);
  } catch (e: any) { execTime.value = Date.now() - start; resultError.value = e.message || 'Execution failed'; }
  finally { running.value = false; }
};

const applyExample = (ex: Record<string, any>) => {
  const paramNames = new Set(paramEntries.value.map(([n]) => n));
  for (const [k, v] of Object.entries(ex)) {
    if (paramNames.has(k)) {
      const info = spec.value?.parameters?.properties?.[k];
      if (info?.type === 'array' && typeof v !== 'string') {
        formValues[k] = JSON.stringify(v);
      } else if (typeof v === 'object' && v !== null) {
        formValues[k] = JSON.stringify(v);
      } else {
        formValues[k] = v;
      }
    }
  }
};

const _exampleIdx = ref(0);

const fillExample = () => {
  const examples = spec.value?.test_examples;
  if (!examples || examples.length === 0) return;
  applyExample(examples[_exampleIdx.value % examples.length]);
  _exampleIdx.value++;
};

const clearForm = () => {
  for (const [name, info] of paramEntries.value) formValues[name] = info.type === 'boolean' ? false : '';
  resultData.value = null; resultError.value = null; execTime.value = null;
};

const copyResult = async () => {
  try { await navigator.clipboard.writeText(formattedResult.value); copied.value = true; setTimeout(() => { copied.value = false; }, 2000); } catch {}
};
</script>

<style scoped>
.form-input {
  @apply w-full px-3.5 py-2.5 text-sm border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-[#2a2a2a] transition-all duration-200;
}
.form-input:focus {
  @apply outline-none ring-2 ring-indigo-500/20 border-indigo-400;
}

.detail-card {
  animation: slideUp 0.4s ease-out both;
  animation-delay: var(--delay, 0ms);
}
@keyframes slideUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.result-animate {
  animation: resultFade 0.3s ease-out;
}
@keyframes resultFade {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.run-btn:not(:disabled):hover {
  background-size: 200% 100%;
  animation: shimmer 2s linear infinite;
}
@keyframes shimmer {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
</style>
