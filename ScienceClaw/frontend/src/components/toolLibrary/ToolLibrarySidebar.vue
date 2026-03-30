<template>
  <aside class="flex h-full w-[248px] shrink-0 flex-col border-r border-[var(--border-light)] bg-white/80 md:w-[260px] xl:w-[272px] dark:bg-[#161616]">
    <div class="border-b border-[var(--border-light)] px-4 py-4">
      <div class="text-[11px] uppercase tracking-[0.18em] text-[var(--text-tertiary)]">Browse</div>
      <h2 class="mt-2 text-lg font-semibold text-[var(--text-primary)]">{{ regionLabel }} Library</h2>
      <p class="mt-1 text-sm text-[var(--text-secondary)]">{{ description }}</p>
    </div>

    <div class="border-b border-[var(--border-light)] px-4 py-4">
      <div class="mb-3 text-[11px] uppercase tracking-[0.18em] text-[var(--text-tertiary)]">Browse Track</div>
      <div class="grid grid-cols-2 gap-2">
        <button
          type="button"
          class="rounded-[20px] border px-3 py-3 text-left transition"
          :class="browseSource === 'system' ? activeButtonClass : idleButtonClass"
          @click="$emit('select-browse-source', 'system')"
        >
          <div class="text-sm font-semibold text-[var(--text-primary)]">System</div>
          <div class="mt-1 text-xs text-[var(--text-secondary)]">Auto taxonomy</div>
        </button>
        <button
          type="button"
          class="rounded-[20px] border px-3 py-3 text-left transition"
          :class="browseSource === 'custom' ? activeButtonClass : idleButtonClass"
          @click="$emit('select-browse-source', 'custom')"
        >
          <div class="text-sm font-semibold text-[var(--text-primary)]">My Categories</div>
          <div class="mt-1 text-xs text-[var(--text-secondary)]">Your personal tree</div>
        </button>
      </div>
    </div>

    <div class="border-b border-[var(--border-light)] px-4 py-4">
      <div class="flex items-center justify-between gap-3">
        <div>
          <div class="text-[11px] uppercase tracking-[0.18em] text-[var(--text-tertiary)]">My Categories</div>
          <div class="mt-2 text-sm text-[var(--text-primary)]">{{ categorySummary.categoryCount }} shared buckets</div>
          <div class="mt-1 text-xs text-[var(--text-secondary)]">{{ categorySummary.assignedCount }} tools assigned in {{ regionLabel.toLowerCase() }}</div>
        </div>
        <button
          type="button"
          class="rounded-2xl border border-[var(--border-light)] bg-[var(--background-gray-main)] px-3 py-2 text-sm text-[var(--text-secondary)] transition hover:bg-white dark:bg-white/5 dark:hover:bg-white/10"
          @click="$emit('manage-categories')"
        >
          Edit Tree
        </button>
      </div>
    </div>

    <div class="min-h-0 flex-1 overflow-y-auto px-3 py-4">
      <template v-if="browseSource === 'system'">
        <div class="mb-3 px-2 text-[11px] uppercase tracking-[0.18em] text-[var(--text-tertiary)]">System Classification</div>
        <button
          type="button"
          class="mb-3 w-full rounded-[22px] border px-4 py-3 text-left transition"
          :class="!activeDiscipline ? activeButtonClass : idleButtonClass"
          @click="$emit('select-discipline', '')"
        >
          <div class="flex items-center justify-between gap-3">
            <div>
              <div class="text-sm font-semibold text-[var(--text-primary)]">All Disciplines</div>
              <div class="mt-1 text-xs text-[var(--text-secondary)]">Browse every tool in the region</div>
            </div>
            <span class="rounded-full bg-black/5 px-2.5 py-1 text-[11px] text-[var(--text-secondary)] dark:bg-white/10">{{ totalCount }}</span>
          </div>
        </button>

        <div class="space-y-2">
          <button
            v-for="option in systemOptions"
            :key="option.id"
            type="button"
            class="w-full rounded-[22px] border px-4 py-3 text-left transition"
            :class="activeDiscipline === option.id ? activeButtonClass : idleButtonClass"
            @click="$emit('select-discipline', option.id)"
          >
            <div class="flex items-center justify-between gap-3">
              <div class="min-w-0">
                <div class="truncate text-sm font-semibold text-[var(--text-primary)]">{{ option.labelZh }}</div>
                <div class="mt-1 truncate text-xs text-[var(--text-secondary)]">{{ option.label }}</div>
              </div>
              <span class="rounded-full bg-black/5 px-2.5 py-1 text-[11px] text-[var(--text-secondary)] dark:bg-white/10">{{ option.count }}</span>
            </div>
          </button>
        </div>
      </template>

      <template v-else>
        <div class="mb-3 px-2 text-[11px] uppercase tracking-[0.18em] text-[var(--text-tertiary)]">My Category Tree</div>
        <div class="space-y-2">
          <button
            type="button"
            class="w-full rounded-[22px] border px-4 py-3 text-left transition"
            :class="!activeCustomCategoryId ? activeButtonClass : idleButtonClass"
            @click="$emit('select-custom-category', '')"
          >
            <div class="flex items-center justify-between gap-3">
              <div>
                <div class="text-sm font-semibold text-[var(--text-primary)]">All Categories</div>
                <div class="mt-1 text-xs text-[var(--text-secondary)]">Browse every tool with your own categories</div>
              </div>
              <span class="rounded-full bg-black/5 px-2.5 py-1 text-[11px] text-[var(--text-secondary)] dark:bg-white/10">{{ totalCount }}</span>
            </div>
          </button>

          <button
            type="button"
            class="w-full rounded-[22px] border px-4 py-3 text-left transition"
            :class="activeCustomCategoryId === UNCATEGORIZED_CATEGORY_ID ? activeButtonClass : idleButtonClass"
            @click="$emit('select-custom-category', UNCATEGORIZED_CATEGORY_ID)"
          >
            <div class="flex items-center justify-between gap-3">
              <div>
                <div class="text-sm font-semibold text-[var(--text-primary)]">Uncategorized</div>
                <div class="mt-1 text-xs text-[var(--text-secondary)]">Tools that still need a custom home</div>
              </div>
              <span class="rounded-full bg-black/5 px-2.5 py-1 text-[11px] text-[var(--text-secondary)] dark:bg-white/10">{{ uncategorizedCount }}</span>
            </div>
          </button>
        </div>

        <div v-if="customCategoryOptions.length" class="mt-4 rounded-[22px] border border-[var(--border-light)] bg-white/70 px-3 py-3 dark:bg-white/5">
          <div class="flex flex-wrap gap-2">
            <button
              type="button"
              class="sidebar-action-button"
              @click="toggleAllCustomCategories"
            >
              {{ allCustomCategoriesSelected ? 'Clear All' : 'Select All' }}
            </button>
            <button
              type="button"
              class="sidebar-action-button"
              :disabled="!selectedCategoryIds.length"
              @click="clearSelectedCategories"
            >
              Clear
            </button>
          </div>

          <div v-if="selectedCategoryIds.length" class="mt-3 rounded-[18px] border border-[var(--border-light)] bg-[var(--background-gray-main)] px-3 py-3 text-xs text-[var(--text-secondary)] dark:bg-[#151515]">
            <div>{{ selectedCategoryIds.length }} categories selected</div>
            <div>{{ selectedCategoryAssignmentCount }} assignments will be removed</div>
          </div>

          <button
            type="button"
            class="sidebar-delete-button mt-3 w-full"
            :disabled="!selectedCategoryIds.length"
            @click="emitDeleteSelectedCategories"
          >
            Delete Selected ({{ selectedCategoryIds.length }})
          </button>
        </div>

        <div class="mt-4 space-y-2">
          <div
            v-for="option in customCategoryOptions"
            :key="option.id"
            class="flex items-stretch gap-2"
          >
            <label class="custom-select-box" :class="selectedCategoryIds.includes(option.id) ? customSelectBoxActiveClass : ''">
              <input
                type="checkbox"
                class="custom-select-checkbox"
                :checked="selectedCategoryIds.includes(option.id)"
                @change="toggleSelectedCategory(option.id)"
              >
            </label>
            <button
              type="button"
              class="min-w-0 flex-1 rounded-[22px] border px-4 py-3 text-left transition"
              :class="activeCustomCategoryId === option.id ? activeButtonClass : idleButtonClass"
              @click="$emit('select-custom-category', option.id)"
            >
              <div class="flex items-center justify-between gap-3">
                <div class="min-w-0">
                  <div class="truncate text-sm font-semibold text-[var(--text-primary)]">{{ option.labelZh }}</div>
                  <div class="mt-1 truncate text-xs text-[var(--text-secondary)]">{{ option.subcategoryCount }} subcategories</div>
                </div>
                <span class="rounded-full bg-black/5 px-2.5 py-1 text-[11px] text-[var(--text-secondary)] dark:bg-white/10">{{ option.count }}</span>
              </div>
            </button>
          </div>
        </div>

        <div v-if="activeCustomCategoryId && activeCustomCategoryId !== UNCATEGORIZED_CATEGORY_ID && customSubcategoryOptions.length" class="mt-5">
          <div class="mb-3 px-2 text-[11px] uppercase tracking-[0.18em] text-[var(--text-tertiary)]">Subcategories</div>
          <div class="space-y-2">
            <button
              type="button"
              class="w-full rounded-[20px] border px-4 py-3 text-left transition"
              :class="!activeCustomSubcategoryId ? activeButtonClass : idleButtonClass"
              @click="$emit('select-custom-subcategory', '')"
            >
              <div class="flex items-center justify-between gap-3">
                <div>
                  <div class="text-sm font-semibold text-[var(--text-primary)]">All Subcategories</div>
                  <div class="mt-1 text-xs text-[var(--text-secondary)]">Stay inside the current custom category</div>
                </div>
              </div>
            </button>

            <button
              v-for="option in customSubcategoryOptions"
              :key="option.id"
              type="button"
              class="w-full rounded-[20px] border px-4 py-3 text-left transition"
              :class="activeCustomSubcategoryId === option.id ? activeButtonClass : idleButtonClass"
              @click="$emit('select-custom-subcategory', option.id)"
            >
              <div class="flex items-center justify-between gap-3">
                <div class="min-w-0">
                  <div class="truncate text-sm font-semibold text-[var(--text-primary)]">{{ option.labelZh }}</div>
                  <div class="mt-1 truncate text-xs text-[var(--text-secondary)]">{{ option.label }}</div>
                </div>
                <span class="rounded-full bg-black/5 px-2.5 py-1 text-[11px] text-[var(--text-secondary)] dark:bg-white/10">{{ option.count }}</span>
              </div>
            </button>
          </div>
        </div>
      </template>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { UNCATEGORIZED_CATEGORY_ID } from './browseHelpers';
import type { BrowseSource, CustomCategoryOption, TaxonomyOption } from './types';

const activeButtonClass = 'border-slate-900/10 bg-slate-900/5 dark:border-white/20 dark:bg-white/10';
const idleButtonClass = 'border-[var(--border-light)] bg-[var(--background-gray-main)] hover:bg-white dark:bg-white/5 dark:hover:bg-white/10';
const customSelectBoxActiveClass = 'border-slate-900/20 bg-slate-900/6 dark:border-white/20 dark:bg-white/10';

const props = defineProps<{
  regionLabel: string;
  description: string;
  browseSource: BrowseSource;
  systemOptions: TaxonomyOption[];
  customCategoryOptions: CustomCategoryOption[];
  customSubcategoryOptions: TaxonomyOption[];
  customCategoryAssignmentTotals: Map<string, number>;
  activeDiscipline: string;
  activeCustomCategoryId: string;
  activeCustomSubcategoryId: string;
  totalCount: number;
  uncategorizedCount: number;
  categorySummary: {
    categoryCount: number;
    assignedCount: number;
  };
}>();

const emit = defineEmits<{
  (event: 'manage-categories'): void;
  (event: 'select-browse-source', browseSource: BrowseSource): void;
  (event: 'select-discipline', disciplineId: string): void;
  (event: 'select-custom-category', categoryId: string): void;
  (event: 'select-custom-subcategory', subcategoryId: string): void;
  (event: 'delete-custom-categories', categoryIds: string[]): void;
}>();

const selectedCategoryIds = ref<string[]>([]);

watch(
  () => props.customCategoryOptions.map((option) => option.id).join('|'),
  () => {
    const validIds = new Set(props.customCategoryOptions.map((option) => option.id));
    selectedCategoryIds.value = selectedCategoryIds.value.filter((categoryId) => validIds.has(categoryId));
  },
  { immediate: true },
);

watch(
  () => props.browseSource,
  (browseSource) => {
    if (browseSource !== 'custom') {
      selectedCategoryIds.value = [];
    }
  },
);

const allCustomCategoriesSelected = computed(() =>
  props.customCategoryOptions.length > 0
  && props.customCategoryOptions.every((option) => selectedCategoryIds.value.includes(option.id))
);

const selectedCategoryAssignmentCount = computed(() =>
  selectedCategoryIds.value.reduce(
    (total, categoryId) => total + (props.customCategoryAssignmentTotals.get(categoryId) || 0),
    0,
  )
);

function toggleSelectedCategory(categoryId: string): void {
  const next = new Set(selectedCategoryIds.value);
  if (next.has(categoryId)) {
    next.delete(categoryId);
  } else {
    next.add(categoryId);
  }
  selectedCategoryIds.value = Array.from(next);
}

function toggleAllCustomCategories(): void {
  if (allCustomCategoriesSelected.value) {
    selectedCategoryIds.value = [];
    return;
  }
  selectedCategoryIds.value = props.customCategoryOptions.map((option) => option.id);
}

function clearSelectedCategories(): void {
  selectedCategoryIds.value = [];
}

function emitDeleteSelectedCategories(): void {
  if (!selectedCategoryIds.value.length) {
    return;
  }
  emit('delete-custom-categories', [...selectedCategoryIds.value]);
  selectedCategoryIds.value = [];
}
</script>

<style scoped>
.sidebar-action-button {
  border-radius: 9999px;
  border: 1px solid var(--border-light);
  background: rgba(255, 255, 255, 0.8);
  padding: 0.45rem 0.8rem;
  font-size: 0.75rem;
  color: var(--text-secondary);
  transition: background-color 160ms ease;
}

.sidebar-action-button:hover:not(:disabled) {
  background: white;
}

.sidebar-action-button:disabled,
.sidebar-delete-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.sidebar-delete-button {
  border-radius: 1rem;
  border: 1px solid rgba(248, 113, 113, 0.25);
  background: rgba(254, 242, 242, 1);
  padding: 0.7rem 0.95rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: rgb(220, 38, 38);
}

.custom-select-box {
  display: inline-flex;
  width: 2.5rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 1.35rem;
  border: 1px solid var(--border-light);
  background: rgba(255, 255, 255, 0.72);
}

.custom-select-checkbox {
  height: 1rem;
  width: 1rem;
  border-radius: 0.25rem;
  border: 1px solid var(--border-light);
  accent-color: rgb(15, 23, 42);
}

.dark .sidebar-action-button,
.dark .custom-select-box {
  background: rgba(255, 255, 255, 0.04);
}

.dark .sidebar-delete-button {
  background: rgba(248, 113, 113, 0.1);
  border-color: rgba(248, 113, 113, 0.2);
  color: rgb(252, 165, 165);
}
</style>
