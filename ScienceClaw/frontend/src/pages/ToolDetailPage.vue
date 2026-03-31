<template>
  <div class="flex h-full w-full flex-col overflow-hidden bg-[var(--background-gray-main)]">
    <div class="relative overflow-hidden border-b border-white/10">
      <div class="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(248,113,113,0.26),_transparent_34%),radial-gradient(circle_at_80%_20%,_rgba(59,130,246,0.24),_transparent_36%),linear-gradient(135deg,_#0f172a_0%,_#111827_48%,_#1f2937_100%)]"></div>
      <div class="relative flex items-center gap-4 px-6 py-5">
        <button
          type="button"
          class="rounded-2xl border border-white/10 bg-white/10 p-2 text-white/75 transition hover:bg-white/15 hover:text-white"
          @click="goBack"
        >
          <ArrowLeft class="size-5" />
        </button>
        <div class="flex size-12 items-center justify-center rounded-2xl bg-white/15 text-lg font-semibold text-white shadow-lg shadow-black/20 backdrop-blur-sm">
          {{ toolName.charAt(0).toUpperCase() }}
        </div>
        <div class="min-w-0">
          <div class="text-[11px] uppercase tracking-[0.18em] text-white/55">External Tool Runner</div>
          <h1 class="truncate text-lg font-semibold text-white">{{ toolName }}</h1>
          <p class="mt-1 truncate text-sm text-white/70">{{ spec?.description || 'Load proxy schema and test the tool directly from this page.' }}</p>
        </div>
      </div>
    </div>

    <div class="grid min-h-0 flex-1 grid-cols-1 xl:grid-cols-[minmax(0,1.25fr)_minmax(360px,0.9fr)]">
      <section class="min-h-0 overflow-y-auto px-5 py-5 md:px-6">
        <div class="mx-auto max-w-4xl space-y-5">
          <div v-if="loading" class="space-y-4">
            <div v-for="i in 3" :key="i" class="animate-pulse rounded-[28px] border border-[var(--border-light)] bg-white/70 p-5 dark:bg-white/5">
              <div class="h-4 w-32 rounded bg-black/10 dark:bg-white/10"></div>
              <div class="mt-4 h-3 rounded bg-black/5 dark:bg-white/10"></div>
              <div class="mt-2 h-3 w-5/6 rounded bg-black/5 dark:bg-white/10"></div>
            </div>
          </div>

          <div v-else-if="loadError" class="rounded-[28px] border border-red-200 bg-red-50 p-5 text-sm text-red-700 dark:border-red-400/20 dark:bg-red-400/10 dark:text-red-300">
            {{ loadError }}
          </div>

          <template v-else-if="spec">
            <article class="rounded-[28px] border border-[var(--border-light)] bg-white/90 p-5 shadow-sm dark:bg-[#171717]">
              <div class="flex flex-wrap items-start justify-between gap-4">
                <div class="space-y-3">
                  <div class="flex flex-wrap gap-2">
                    <span v-if="spec.discipline_zh" class="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-[11px] font-medium text-emerald-700 dark:border-emerald-400/20 dark:bg-emerald-400/10 dark:text-emerald-300">
                      {{ spec.discipline_zh }}
                    </span>
                    <span v-if="spec.function_group_zh" class="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-[11px] font-medium text-sky-700 dark:border-sky-400/20 dark:bg-sky-400/10 dark:text-sky-300">
                      {{ spec.function_group_zh }}
                    </span>
                    <span v-if="spec.category" class="rounded-full border border-[var(--border-light)] bg-white/70 px-3 py-1 text-[11px] text-[var(--text-secondary)] dark:bg-white/5">
                      {{ spec.category }}
                    </span>
                    <span v-if="spec.subcategory" class="rounded-full border border-[var(--border-light)] bg-white/70 px-3 py-1 text-[11px] text-[var(--text-secondary)] dark:bg-white/5">
                      {{ spec.subcategory }}
                    </span>
                  </div>
                  <p class="max-w-3xl text-sm leading-7 text-[var(--text-secondary)]">
                    {{ spec.description || 'No description available yet.' }}
                  </p>
                </div>

                <div class="min-w-[220px] rounded-[24px] border border-[var(--border-light)] bg-[var(--background-gray-main)] p-4 dark:bg-white/5">
                  <div class="text-[11px] uppercase tracking-[0.16em] text-[var(--text-tertiary)]">Metadata</div>
                  <div class="mt-3 grid gap-2 text-sm text-[var(--text-secondary)]">
                    <div class="flex items-center justify-between gap-3">
                      <span>Runner</span>
                      <span class="font-mono text-[12px] text-[var(--text-primary)]">{{ spec.runner || 'structured_proxy' }}</span>
                    </div>
                    <div class="flex items-center justify-between gap-3">
                      <span>Parameters</span>
                      <span class="font-mono text-[12px] text-[var(--text-primary)]">{{ paramEntries.length }}</span>
                    </div>
                    <div class="flex items-center justify-between gap-3">
                      <span>Required</span>
                      <span class="font-mono text-[12px] text-[var(--text-primary)]">{{ requiredParams.length }}</span>
                    </div>
                    <div v-if="spec.tags?.length" class="pt-2">
                      <div class="mb-2 text-[11px] uppercase tracking-[0.14em] text-[var(--text-tertiary)]">Tags</div>
                      <div class="flex flex-wrap gap-1.5">
                        <span
                          v-for="tag in spec.tags"
                          :key="tag"
                          class="rounded-full border border-[var(--border-light)] bg-white/70 px-2.5 py-1 text-[11px] text-[var(--text-secondary)] dark:bg-white/5"
                        >
                          {{ tag }}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </article>

            <article class="rounded-[28px] border border-[var(--border-light)] bg-white/90 shadow-sm dark:bg-[#171717]">
              <div class="flex items-center justify-between border-b border-[var(--border-light)] px-5 py-4">
                <div>
                  <h2 class="text-base font-semibold text-[var(--text-primary)]">Parameters</h2>
                  <p class="mt-1 text-sm text-[var(--text-secondary)]">Submit arguments directly to the existing sandbox proxy runner.</p>
                </div>
                <span class="rounded-full bg-black/5 px-2.5 py-1 text-[11px] font-medium text-[var(--text-secondary)] dark:bg-white/10">
                  {{ paramEntries.length }} fields
                </span>
              </div>

              <div v-if="!paramEntries.length" class="px-5 py-10 text-sm text-[var(--text-secondary)]">
                This tool does not declare any input fields. Run it directly from the action bar below.
              </div>

              <div v-else class="grid gap-5 px-5 py-5 md:grid-cols-2">
                <div v-for="field in paramEntries" :key="field.name" class="space-y-2">
                  <div class="flex items-center gap-2">
                    <label class="text-sm font-medium text-[var(--text-primary)]">{{ field.name }}</label>
                    <span class="rounded-full bg-black/5 px-2 py-0.5 text-[10px] font-medium text-[var(--text-secondary)] dark:bg-white/10">
                      {{ field.type }}
                    </span>
                    <span
                      v-if="field.required"
                      class="rounded-full border border-red-200 bg-red-50 px-2 py-0.5 text-[10px] font-medium text-red-600 dark:border-red-400/20 dark:bg-red-400/10 dark:text-red-300"
                    >
                      required
                    </span>
                  </div>
                  <p v-if="field.description" class="text-xs leading-6 text-[var(--text-tertiary)]">{{ field.description }}</p>

                  <select v-if="field.enum?.length" v-model="formValues[field.name]" class="runner-input">
                    <option value="">Select…</option>
                    <option v-for="option in field.enum" :key="option" :value="option">{{ option }}</option>
                  </select>

                  <button
                    v-else-if="field.type === 'boolean'"
                    type="button"
                    class="flex items-center gap-3 rounded-2xl border border-[var(--border-light)] bg-[var(--background-gray-main)] px-4 py-3 text-sm text-[var(--text-secondary)] transition hover:bg-white dark:bg-white/5 dark:hover:bg-white/10"
                    @click="formValues[field.name] = !formValues[field.name]"
                  >
                    <span
                      class="relative inline-flex h-6 w-11 items-center rounded-full transition"
                      :class="formValues[field.name] ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-600'"
                    >
                      <span
                        class="inline-block h-4 w-4 rounded-full bg-white shadow transition"
                        :class="formValues[field.name] ? 'translate-x-6' : 'translate-x-1'"
                      />
                    </span>
                    <span class="font-mono text-[12px]">{{ String(formValues[field.name]) }}</span>
                  </button>

                  <textarea
                    v-else-if="field.type === 'array' || field.type === 'object'"
                    v-model="formValues[field.name]"
                    class="runner-input min-h-[110px] font-mono text-[13px]"
                    :placeholder="jsonPlaceholder(field.type)"
                  />

                  <input
                    v-else-if="field.type === 'integer' || field.type === 'number'"
                    v-model="formValues[field.name]"
                    type="number"
                    class="runner-input"
                    :placeholder="`Enter ${field.name}`"
                  >

                  <input
                    v-else
                    v-model="formValues[field.name]"
                    type="text"
                    class="runner-input"
                    :placeholder="`Enter ${field.name}`"
                  >
                </div>
              </div>

              <div class="flex flex-wrap items-center gap-3 border-t border-[var(--border-light)] bg-[var(--background-gray-main)] px-5 py-4 dark:bg-black/10">
                <button
                  type="button"
                  class="inline-flex items-center gap-2 rounded-2xl bg-slate-900 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100"
                  :disabled="running"
                  @click="runTool"
                >
                  <Play v-if="!running" :size="16" />
                  <span v-else class="size-4 animate-spin rounded-full border-2 border-white/30 border-t-white dark:border-slate-500/30 dark:border-t-slate-900"></span>
                  {{ running ? 'Running…' : 'Run Tool' }}
                </button>

                <button
                  type="button"
                  class="rounded-2xl border border-[var(--border-light)] bg-white/70 px-4 py-2.5 text-sm text-[var(--text-secondary)] transition hover:bg-white dark:bg-white/5 dark:hover:bg-white/10"
                  @click="applyExample"
                  :disabled="!spec.examples?.length"
                >
                  Use Example
                </button>

                <button
                  type="button"
                  class="rounded-2xl border border-[var(--border-light)] bg-white/70 px-4 py-2.5 text-sm text-[var(--text-secondary)] transition hover:bg-white dark:bg-white/5 dark:hover:bg-white/10"
                  @click="clearForm"
                >
                  Clear
                </button>

                <span v-if="execTime !== null" class="ml-auto text-xs text-[var(--text-tertiary)]">
                  {{ execTime }} ms
                </span>
              </div>
            </article>

            <article class="rounded-[28px] border border-[var(--border-light)] bg-white/90 shadow-sm dark:bg-[#171717]">
              <button
                type="button"
                class="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
                @click="toggleSource"
              >
                <div class="flex items-center gap-3">
                  <div class="flex size-10 items-center justify-center rounded-2xl bg-black/5 text-[var(--text-secondary)] dark:bg-white/10">
                    <FileCode :size="18" />
                  </div>
                  <div>
                    <h2 class="text-base font-semibold text-[var(--text-primary)]">Source</h2>
                    <p class="text-sm text-[var(--text-secondary)]">Keep the raw file nearby without making it the main screen.</p>
                  </div>
                </div>
                <ChevronDown class="size-5 text-[var(--text-tertiary)] transition" :class="sourceOpen ? 'rotate-180' : ''" />
              </button>

              <div v-if="sourceOpen" class="border-t border-[var(--border-light)] px-5 py-5">
                <div v-if="sourceLoading" class="text-sm text-[var(--text-secondary)]">Loading source…</div>
                <div v-else-if="sourceError" class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-400/20 dark:bg-red-400/10 dark:text-red-300">
                  {{ sourceError }}
                </div>
                <pre
                  v-else
                  class="max-h-[520px] overflow-auto rounded-[24px] border border-[var(--border-light)] bg-[#0f172a] p-4 text-[12px] leading-6 text-slate-100"
                ><code>{{ sourceContent }}</code></pre>
              </div>
            </article>
          </template>
        </div>
      </section>

      <aside class="min-h-0 border-t border-[var(--border-light)] bg-white/80 xl:border-l xl:border-t-0 dark:bg-[#151515]">
        <div class="flex h-full flex-col">
          <div class="flex items-center justify-between border-b border-[var(--border-light)] px-5 py-4">
            <div class="flex items-center gap-3">
              <div class="flex size-10 items-center justify-center rounded-2xl bg-black/5 text-[var(--text-secondary)] dark:bg-white/10">
                <Terminal :size="18" />
              </div>
              <div>
                <h2 class="text-base font-semibold text-[var(--text-primary)]">Result</h2>
                <p class="text-sm text-[var(--text-secondary)]">Structured output from the sandbox proxy.</p>
              </div>
            </div>
            <button
              v-if="resultText"
              type="button"
              class="rounded-2xl border border-[var(--border-light)] bg-white/70 px-3 py-1.5 text-xs text-[var(--text-secondary)] transition hover:bg-white dark:bg-white/5 dark:hover:bg-white/10"
              @click="copyResult"
            >
              {{ copied ? 'Copied' : 'Copy JSON' }}
            </button>
          </div>

          <div class="min-h-0 flex-1 overflow-y-auto px-5 py-5">
            <div v-if="running" class="flex h-full min-h-[260px] flex-col items-center justify-center gap-3 text-center">
              <div class="relative size-12">
                <div class="absolute inset-0 rounded-full border-2 border-slate-200 dark:border-slate-700"></div>
                <div class="absolute inset-0 animate-spin rounded-full border-2 border-slate-900 border-t-transparent dark:border-white dark:border-t-transparent"></div>
              </div>
              <div class="text-sm text-[var(--text-secondary)]">Executing the external proxy tool…</div>
            </div>

            <div v-else-if="resultError" class="space-y-4">
              <div class="rounded-[24px] border border-red-200 bg-red-50 p-4 text-sm leading-7 text-red-700 dark:border-red-400/20 dark:bg-red-400/10 dark:text-red-300">
                {{ resultError }}
              </div>
              <div v-if="stdout" class="space-y-2">
                <div class="text-xs font-medium uppercase tracking-[0.16em] text-[var(--text-tertiary)]">Runner stdout</div>
                <pre class="overflow-auto rounded-[24px] border border-[var(--border-light)] bg-[#0f172a] p-4 text-[12px] leading-6 text-slate-100"><code>{{ stdout }}</code></pre>
              </div>
            </div>

            <div v-else-if="resultText" class="space-y-4">
              <pre class="overflow-auto rounded-[24px] border border-[var(--border-light)] bg-[#0f172a] p-4 text-[12px] leading-6 text-slate-100"><code>{{ resultText }}</code></pre>
              <div v-if="stdout" class="space-y-2">
                <div class="text-xs font-medium uppercase tracking-[0.16em] text-[var(--text-tertiary)]">Runner stdout</div>
                <pre class="overflow-auto rounded-[24px] border border-[var(--border-light)] bg-[#0b1220] p-4 text-[12px] leading-6 text-slate-100"><code>{{ stdout }}</code></pre>
              </div>
            </div>

            <div v-else class="flex h-full min-h-[260px] flex-col items-center justify-center gap-3 text-center">
              <div class="flex size-16 items-center justify-center rounded-3xl bg-black/5 text-[var(--text-tertiary)] dark:bg-white/10">
                <Terminal :size="26" />
              </div>
              <div>
                <div class="text-sm font-medium text-[var(--text-primary)]">No results yet</div>
                <div class="mt-1 text-sm text-[var(--text-secondary)]">Run the tool once and structured output will appear here.</div>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ArrowLeft, ChevronDown, FileCode, Play, Terminal } from 'lucide-vue-next';
import { getToolSpec, readToolFile, runExternalTool, type ExternalToolSpec } from '../api/agent';

type ParamField = {
  name: string;
  type: string;
  description: string;
  enum?: string[];
  required: boolean;
};

const route = useRoute();
const router = useRouter();
const toolName = decodeURIComponent(route.params.toolName as string);

const loading = ref(true);
const loadError = ref<string | null>(null);
const spec = ref<ExternalToolSpec | null>(null);
const running = ref(false);
const resultData = ref<any>(null);
const resultError = ref<string | null>(null);
const execTime = ref<number | null>(null);
const stdout = ref<string>('');
const copied = ref(false);
const sourceOpen = ref(false);
const sourceLoading = ref(false);
const sourceError = ref<string | null>(null);
const sourceContent = ref('');
const exampleIndex = ref(0);
const formValues = reactive<Record<string, any>>({});

const paramEntries = computed<ParamField[]>(() => {
  const properties = spec.value?.parameters?.properties || {};
  const required = new Set(spec.value?.parameters?.required || []);
  return Object.entries(properties).map(([name, info]: [string, any]) => ({
    name,
    type: info?.type || 'string',
    description: info?.description || '',
    enum: Array.isArray(info?.enum) ? info.enum : undefined,
    required: required.has(name),
  }));
});

const requiredParams = computed(() => paramEntries.value.filter((field) => field.required));

const resultText = computed(() => {
  if (resultData.value === null || resultData.value === undefined) {
    return '';
  }
  try {
    return JSON.stringify(resultData.value, null, 2);
  } catch {
    return String(resultData.value);
  }
});

function initializeForm(): void {
  for (const field of paramEntries.value) {
    if (field.type === 'boolean') {
      formValues[field.name] = false;
      continue;
    }
    formValues[field.name] = '';
  }
}

async function loadSpec(): Promise<void> {
  loading.value = true;
  loadError.value = null;
  try {
    spec.value = await getToolSpec(toolName);
    initializeForm();
  } catch (error: any) {
    loadError.value = error?.details?.detail || error?.message || 'Failed to load external tool specification.';
  } finally {
    loading.value = false;
  }
}

function normalizeFieldValue(field: ParamField, value: any): any {
  if (value === '' || value === null || value === undefined) {
    return undefined;
  }
  if (field.type === 'integer' || field.type === 'number') {
    return Number(value);
  }
  if (field.type === 'array' || field.type === 'object') {
    if (typeof value === 'string') {
      return JSON.parse(value);
    }
    return value;
  }
  return value;
}

function jsonPlaceholder(type: string): string {
  return type === 'array' ? '["value"]' : '{"key":"value"}';
}

function buildArguments(): Record<string, any> {
  const args: Record<string, any> = {};
  for (const field of paramEntries.value) {
    const normalized = normalizeFieldValue(field, formValues[field.name]);
    if (normalized !== undefined) {
      args[field.name] = normalized;
    }
  }
  return args;
}

async function runTool(): Promise<void> {
  running.value = true;
  resultData.value = null;
  resultError.value = null;
  stdout.value = '';
  execTime.value = null;
  const startedAt = Date.now();

  try {
    const response = await runExternalTool(toolName, buildArguments());
    execTime.value = Date.now() - startedAt;
    stdout.value = response.stdout || '';
    if (response.success) {
      resultData.value = response.result;
    } else {
      resultError.value = typeof response.result === 'string'
        ? response.result
        : JSON.stringify(response.result, null, 2);
    }
  } catch (error: any) {
    execTime.value = Date.now() - startedAt;
    resultError.value = error?.details?.detail || error?.message || 'Failed to execute external tool.';
  } finally {
    running.value = false;
  }
}

function clearForm(): void {
  initializeForm();
}

function applyExample(): void {
  if (!spec.value?.examples?.length) {
    return;
  }
  const example = spec.value.examples[exampleIndex.value % spec.value.examples.length] || {};
  for (const field of paramEntries.value) {
    const exampleValue = example[field.name];
    if (exampleValue === undefined) {
      continue;
    }
    formValues[field.name] =
      field.type === 'array' || field.type === 'object'
        ? JSON.stringify(exampleValue, null, 2)
        : exampleValue;
  }
  exampleIndex.value += 1;
}

async function toggleSource(): Promise<void> {
  sourceOpen.value = !sourceOpen.value;
  if (!sourceOpen.value || sourceContent.value || sourceLoading.value) {
    return;
  }
  sourceLoading.value = true;
  sourceError.value = null;
  try {
    const response = await readToolFile(toolName);
    sourceContent.value = response.content;
  } catch (error: any) {
    sourceError.value = error?.details?.detail || error?.message || 'Failed to load source file.';
  } finally {
    sourceLoading.value = false;
  }
}

async function copyResult(): Promise<void> {
  if (!resultText.value) {
    return;
  }
  await navigator.clipboard.writeText(resultText.value);
  copied.value = true;
  window.setTimeout(() => {
    copied.value = false;
  }, 1500);
}

function goBack(): void {
  router.back();
}

onMounted(loadSpec);
</script>

<style scoped>
.runner-input {
  width: 100%;
  border-radius: 1rem;
  border: 1px solid var(--border-light);
  background: rgba(255, 255, 255, 0.72);
  padding: 0.85rem 1rem;
  font-size: 0.95rem;
  color: var(--text-primary);
  outline: none;
  transition: border-color 160ms ease, background-color 160ms ease, box-shadow 160ms ease;
}

.runner-input:focus {
  border-color: rgba(15, 23, 42, 0.18);
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 0 0 4px rgba(15, 23, 42, 0.06);
}

.dark .runner-input {
  background: rgba(255, 255, 255, 0.04);
}

.dark .runner-input:focus {
  background: rgba(255, 255, 255, 0.07);
  box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.04);
}
</style>
