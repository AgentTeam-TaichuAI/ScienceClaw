<template>
  <div class="flex flex-col gap-6 py-2 px-1">
    <div v-if="loading" class="flex justify-center py-12">
      <Loader2 class="size-8 animate-spin text-gray-300" />
    </div>

    <div v-else class="flex flex-col gap-6">
      <!-- Description -->
      <div class="p-4 bg-gradient-to-br from-cyan-50/60 to-teal-50/40 dark:from-cyan-900/20 dark:to-teal-900/15 border border-cyan-100/60 dark:border-cyan-800/30 rounded-2xl">
        <div class="flex items-start gap-3">
          <div class="size-9 rounded-xl bg-gradient-to-br from-cyan-100 to-teal-100 dark:from-cyan-900/50 dark:to-teal-900/50 flex items-center justify-center flex-shrink-0">
            <Brain class="size-4.5 text-cyan-600 dark:text-cyan-400" />
          </div>
          <div class="flex-1 min-w-0">
            <span class="text-sm font-bold text-gray-700 dark:text-gray-200">{{ t('Memory Desc Title') }}</span>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1 leading-relaxed">{{ t('Memory Desc') }}</p>
          </div>
        </div>
      </div>

      <!-- Sections -->
      <div v-for="(section, sIdx) in sections" :key="section.key" class="flex flex-col gap-3">
        <h3 class="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider px-1 flex items-center gap-2">
          <component :is="section.icon" class="size-3.5" />
          {{ t(section.label) }}
          <span class="h-px flex-1 bg-gradient-to-r from-gray-200 dark:from-gray-700 to-transparent"></span>
        </h3>

        <div class="flex flex-col gap-2">
          <!-- Existing items -->
          <div
            v-for="(_, iIdx) in section.items"
            :key="iIdx"
            class="group flex items-start gap-2"
          >
            <div class="flex-1 relative">
              <textarea
                v-model="section.items[iIdx]"
                rows="1"
                class="w-full px-3.5 py-2.5 bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700/50 rounded-xl text-sm text-gray-700 dark:text-gray-200 leading-relaxed resize-none focus:outline-none focus:ring-2 focus:ring-cyan-500/20 focus:border-cyan-400 dark:focus:border-cyan-500 transition-all placeholder:text-gray-300 dark:placeholder:text-gray-600"
                :placeholder="t('Memory Item Placeholder')"
                @input="autoResize($event)"
                @focus="autoResize($event)"
              />
            </div>
            <button
              class="mt-2 size-6 rounded-lg flex items-center justify-center text-gray-300 dark:text-gray-600 opacity-0 group-hover:opacity-100 hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all flex-shrink-0 cursor-pointer"
              @click="removeItem(sIdx, iIdx)"
            >
              <X :size="14" />
            </button>
          </div>

          <!-- Add item button -->
          <button
            class="flex items-center gap-2 px-3.5 py-2.5 border border-dashed border-gray-200 dark:border-gray-700/50 rounded-xl text-xs text-gray-400 dark:text-gray-500 hover:text-cyan-500 hover:border-cyan-300 dark:hover:border-cyan-700 hover:bg-cyan-50/50 dark:hover:bg-cyan-900/10 transition-all cursor-pointer"
            @click="addItem(sIdx)"
          >
            <Plus :size="14" />
            {{ t('Add Entry') }}
          </button>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="flex items-center justify-between px-1 pt-2">
        <button
          class="px-4 py-2 text-xs font-medium text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition-all cursor-pointer"
          @click="resetToDefaults"
        >
          {{ t('Reset Defaults') }}
        </button>
        <button
          class="px-5 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-cyan-500 to-teal-600 rounded-xl shadow-md shadow-cyan-500/20 hover:shadow-lg hover:shadow-cyan-500/30 active:scale-[0.97] transition-all duration-200 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          :disabled="saving || !hasChanges"
          @click="saveMemory"
        >
          <Loader2 v-if="saving" class="size-4 animate-spin" />
          <span v-else>{{ t('Save') }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';
import { Loader2, Brain, Plus, X, User, Sparkles, BookOpen } from 'lucide-vue-next';
import { getMemory, updateMemory } from '@/api/memory';
import { showSuccessToast, showErrorToast } from '@/utils/toast';

const { t } = useI18n();

const loading = ref(false);
const saving = ref(false);
const originalMarkdown = ref('');

interface Section {
  key: string;
  heading: string;
  label: string;
  icon: any;
  items: string[];
}

const sections = reactive<Section[]>([
  { key: 'preferences', heading: '## User Preferences', label: 'User Preferences', icon: User, items: [] },
  { key: 'patterns', heading: '## General Patterns', label: 'General Patterns', icon: Sparkles, items: [] },
  { key: 'notes', heading: '## Notes', label: 'Notes', icon: BookOpen, items: [] },
]);

function parseMarkdown(md: string) {
  const sectionMap: Record<string, string[]> = {
    preferences: [],
    patterns: [],
    notes: [],
  };

  let current: string | null = null;
  for (const line of md.split('\n')) {
    const trimmed = line.trim();
    if (/^##\s*User Preferences/i.test(trimmed)) {
      current = 'preferences';
    } else if (/^##\s*General Patterns/i.test(trimmed)) {
      current = 'patterns';
    } else if (/^##\s*Notes/i.test(trimmed)) {
      current = 'notes';
    } else if (/^##\s/.test(trimmed)) {
      current = null;
    } else if (current && trimmed) {
      const content = trimmed.replace(/^[-*]\s*/, '');
      if (content) {
        sectionMap[current].push(content);
      }
    }
  }

  for (const s of sections) {
    s.items = sectionMap[s.key] || [];
  }
}

function serializeToMarkdown(): string {
  const lines: string[] = ['# Global Memory (persists across all sessions)', ''];
  for (const s of sections) {
    lines.push(s.heading);
    lines.push('');
    for (const item of s.items) {
      const trimmed = item.trim();
      if (trimmed) {
        lines.push(`- ${trimmed}`);
      }
    }
    lines.push('');
  }
  return lines.join('\n');
}

const hasChanges = computed(() => serializeToMarkdown() !== originalMarkdown.value);

function addItem(sIdx: number) {
  sections[sIdx].items.push('');
  nextTick(() => {
    const allTextareas = document.querySelectorAll<HTMLTextAreaElement>(
      `.flex.flex-col.gap-2:nth-child(${sIdx + 1}) textarea`
    );
    const last = allTextareas[allTextareas.length - 1];
    if (last) last.focus();
  });
}

function removeItem(sIdx: number, iIdx: number) {
  sections[sIdx].items.splice(iIdx, 1);
}

function autoResize(event: Event) {
  const el = event.target as HTMLTextAreaElement;
  el.style.height = 'auto';
  el.style.height = el.scrollHeight + 'px';
}

const fetchMemory = async () => {
  loading.value = true;
  try {
    const data = await getMemory();
    parseMarkdown(data.content);
    originalMarkdown.value = serializeToMarkdown();
  } catch (err) {
    console.error(err);
    showErrorToast(t('Failed to load memory'));
  } finally {
    loading.value = false;
  }
};

const saveMemory = async () => {
  saving.value = true;
  try {
    const md = serializeToMarkdown();
    await updateMemory(md);
    originalMarkdown.value = md;
    showSuccessToast(t('Memory saved'));
  } catch (err: any) {
    console.error(err);
    if (err.response?.data?.detail) {
      showErrorToast(err.response.data.detail);
    } else {
      showErrorToast(t('Failed to save memory'));
    }
  } finally {
    saving.value = false;
  }
};

const resetToDefaults = () => {
  for (const s of sections) {
    s.items = [];
  }
};

onMounted(() => {
  fetchMemory();
});
</script>
