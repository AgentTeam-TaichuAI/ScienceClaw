<template>
  <section class="flex min-h-0 flex-1 flex-col">
    <div class="border-b border-[var(--border-light)] px-5 py-4">
      <div class="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <div class="flex flex-wrap items-center gap-2">
            <h2 class="text-lg font-semibold text-[var(--text-primary)]">{{ title }}</h2>
            <span class="rounded-full bg-black/5 px-2.5 py-1 text-[11px] text-[var(--text-secondary)] dark:bg-white/10">{{ cards.length }} shown</span>
            <span v-if="selectedNames.length" class="rounded-full bg-black/5 px-2.5 py-1 text-[11px] text-[var(--text-secondary)] dark:bg-white/10">{{ selectedNames.length }} selected</span>
          </div>
          <p class="mt-1 text-sm text-[var(--text-secondary)]">{{ subtitle }}</p>
          <div class="mt-3 flex flex-wrap items-center gap-2">
            <span class="text-[11px] uppercase tracking-[0.18em] text-[var(--text-tertiary)]">Browse Track</span>
            <span class="rounded-full border border-slate-900/10 bg-slate-900 px-3 py-1 text-[11px] font-medium text-white dark:border-white/20 dark:bg-white dark:text-slate-900">
              {{ browseSource === 'system' ? 'System' : 'My Categories' }}
            </span>
            <span class="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-[11px] font-medium text-emerald-700 dark:border-emerald-400/20 dark:bg-emerald-400/10 dark:text-emerald-300">
              {{ activeSliceLabel }}
            </span>
            <span
              v-if="activeSubsliceLabel"
              class="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-[11px] font-medium text-sky-700 dark:border-sky-400/20 dark:bg-sky-400/10 dark:text-sky-300"
            >
              {{ activeSubsliceLabel }}
            </span>
          </div>
        </div>

        <div class="flex flex-wrap gap-2">
          <button
            type="button"
            class="rounded-2xl border border-[var(--border-light)] bg-white/70 px-3 py-2 text-sm text-[var(--text-secondary)] transition hover:bg-white dark:bg-white/5 dark:hover:bg-white/10"
            @click="$emit('refresh')"
          >
            Refresh
          </button>
          <button
            type="button"
            class="rounded-2xl border border-[var(--border-light)] bg-white/70 px-3 py-2 text-sm text-[var(--text-secondary)] transition hover:bg-white dark:bg-white/5 dark:hover:bg-white/10"
            @click="$emit('reset-filters')"
          >
            Reset
          </button>
          <button
            type="button"
            class="rounded-2xl border border-[var(--border-light)] bg-white/70 px-3 py-2 text-sm text-[var(--text-secondary)] transition hover:bg-white dark:bg-white/5 dark:hover:bg-white/10"
            @click="$emit('manage-categories')"
          >
            Edit My Categories
          </button>
          <button
            type="button"
            class="rounded-2xl border border-[var(--border-light)] bg-white/70 px-3 py-2 text-sm text-[var(--text-secondary)] transition hover:bg-white dark:bg-white/5 dark:hover:bg-white/10"
            @click="$emit('toggle-visible')"
          >
            {{ allVisibleSelected ? 'Clear Visible' : 'Select Visible' }}
          </button>
          <button
            v-if="selectedNames.length"
            type="button"
            class="rounded-2xl border border-slate-900/10 bg-slate-900/5 px-3 py-2 text-sm font-medium text-slate-900 transition hover:bg-slate-900/10 dark:border-white/20 dark:bg-white/10 dark:text-white dark:hover:bg-white/15"
            @click="$emit('create-category-selected')"
          >
            Create Category
          </button>
          <button
            v-if="selectedNames.length"
            type="button"
            class="rounded-2xl bg-slate-900 px-3 py-2 text-sm font-medium text-white transition hover:bg-slate-800 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100"
            @click="$emit('assign-selected')"
          >
            Assign Selected
          </button>
          <button
            v-if="selectedNames.length"
            type="button"
            class="rounded-2xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-700 transition hover:bg-amber-100 dark:border-amber-400/20 dark:bg-amber-400/10 dark:text-amber-300"
            @click="$emit('clear-selected')"
          >
            Clear Assignment
          </button>
        </div>
      </div>

      <div v-if="browseSource === 'system' && systemFunctionGroupOptions.length" class="mt-4">
        <div class="mb-2 text-[11px] uppercase tracking-[0.18em] text-[var(--text-tertiary)]">System Function Groups</div>
        <div class="flex flex-wrap gap-2">
          <button
            type="button"
            class="rounded-full border px-3 py-1.5 text-sm transition"
            :class="!activeFunctionGroup ? activeChipClass : idleChipClass"
            @click="$emit('set-function-group', '')"
          >
            All
          </button>
          <button
            v-for="option in systemFunctionGroupOptions"
            :key="option.id"
            type="button"
            class="rounded-full border px-3 py-1.5 text-sm transition"
            :class="activeFunctionGroup === option.id ? activeChipClass : idleChipClass"
            @click="$emit('set-function-group', option.id)"
          >
            {{ option.labelZh }} | {{ option.count }}
          </button>
        </div>
      </div>

      <template v-if="browseSource === 'custom'">
        <div class="mt-4">
          <div class="mb-2 text-[11px] uppercase tracking-[0.18em] text-[var(--text-tertiary)]">My Categories</div>
          <div class="flex flex-wrap gap-2">
            <button
              type="button"
              class="rounded-full border px-3 py-1.5 text-sm transition"
              :class="!activeCustomCategoryId ? activeChipClass : idleChipClass"
              @click="$emit('set-custom-category', '')"
            >
              All
            </button>
            <button
              type="button"
              class="rounded-full border px-3 py-1.5 text-sm transition"
              :class="activeCustomCategoryId === UNCATEGORIZED_CATEGORY_ID ? activeChipClass : idleChipClass"
              @click="$emit('set-custom-category', UNCATEGORIZED_CATEGORY_ID)"
            >
              Uncategorized | {{ uncategorizedCount }}
            </button>
            <button
              v-for="option in customCategoryOptions"
              :key="option.id"
              type="button"
              class="rounded-full border px-3 py-1.5 text-sm transition"
              :class="activeCustomCategoryId === option.id ? activeChipClass : idleChipClass"
              @click="$emit('set-custom-category', option.id)"
            >
              {{ option.labelZh }} | {{ option.count }}
            </button>
          </div>
        </div>

        <div v-if="activeCustomCategoryId && activeCustomCategoryId !== UNCATEGORIZED_CATEGORY_ID && customSubcategoryOptions.length" class="mt-4">
          <div class="mb-2 text-[11px] uppercase tracking-[0.18em] text-[var(--text-tertiary)]">Subcategories</div>
          <div class="flex flex-wrap gap-2">
            <button
              type="button"
              class="rounded-full border px-3 py-1.5 text-sm transition"
              :class="!activeCustomSubcategoryId ? activeChipClass : idleChipClass"
              @click="$emit('set-custom-subcategory', '')"
            >
              All
            </button>
            <button
              v-for="option in customSubcategoryOptions"
              :key="option.id"
              type="button"
              class="rounded-full border px-3 py-1.5 text-sm transition"
              :class="activeCustomSubcategoryId === option.id ? activeChipClass : idleChipClass"
              @click="$emit('set-custom-subcategory', option.id)"
            >
              {{ option.labelZh }} | {{ option.count }}
            </button>
          </div>
        </div>
      </template>
    </div>

    <div class="min-h-0 flex-1 overflow-y-auto px-5 py-5">
      <div v-if="loading" class="grid grid-cols-1 gap-4 xl:grid-cols-2 2xl:grid-cols-3">
        <div v-for="i in 6" :key="i" class="animate-pulse rounded-[28px] border border-[var(--border-light)] bg-white/80 p-5 dark:bg-white/5">
          <div class="h-4 w-1/2 rounded bg-black/8 dark:bg-white/10"></div>
          <div class="mt-3 h-3 rounded bg-black/6 dark:bg-white/10"></div>
          <div class="mt-2 h-3 w-5/6 rounded bg-black/6 dark:bg-white/10"></div>
          <div class="mt-5 h-10 rounded bg-black/6 dark:bg-white/10"></div>
        </div>
      </div>

      <div v-else-if="!cards.length" class="flex min-h-[320px] flex-col items-center justify-center gap-3 rounded-[30px] border border-dashed border-[var(--border-light)] bg-white/50 px-6 text-center dark:bg-white/5">
        <div class="text-base font-semibold text-[var(--text-primary)]">Nothing in this slice</div>
        <p class="max-w-md text-sm text-[var(--text-secondary)]">{{ emptyStateDescription }}</p>
      </div>

      <div v-else class="grid grid-cols-1 gap-4 xl:grid-cols-2 2xl:grid-cols-3">
        <article
          v-for="card in cards"
          :key="`${card.toolKind}:${card.name}`"
          class="group relative overflow-hidden rounded-[28px] border border-[var(--border-light)] bg-white/90 shadow-sm transition hover:-translate-y-0.5 hover:shadow-lg dark:bg-[#191919]"
        >
          <div class="absolute inset-x-0 top-0 h-1.5 bg-[linear-gradient(90deg,#0f172a_0%,#2563eb_45%,#f97316_100%)] opacity-80"></div>
          <div class="p-5">
            <div class="flex items-start gap-3">
              <input
                type="checkbox"
                class="mt-1 size-4 rounded border-[var(--border-light)] accent-slate-900 dark:accent-white"
                :checked="selectedNames.includes(card.name)"
                @change="$emit('toggle-select', card.name)"
              >

              <button type="button" class="min-w-0 flex-1 text-left" @click="$emit('open-card', card)">
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <h3 class="truncate text-sm font-semibold text-[var(--text-primary)]">{{ card.name }}</h3>
                    <div class="mt-1 truncate text-[11px] text-[var(--text-secondary)]">{{ card.functionGroupLabel }} / {{ card.disciplineLabel }}</div>
                  </div>
                  <span
                    v-if="card.toolKind === 'external' && card.blocked"
                    class="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[11px] font-medium text-amber-700 dark:border-amber-400/20 dark:bg-amber-400/10 dark:text-amber-300"
                  >
                    Blocked
                  </span>
                </div>
                <p class="mt-4 line-clamp-3 text-sm leading-7 text-[var(--text-secondary)]">{{ card.description || 'No description available yet.' }}</p>
              </button>
            </div>

            <div class="mt-4 flex flex-wrap gap-2">
              <span
                v-if="card.customCategoryName"
                class="rounded-full bg-slate-900 px-2.5 py-1 text-[11px] font-medium text-white dark:bg-[#f4dec1] dark:text-[#2f2416]"
              >
                {{ card.customCategoryName }}
              </span>
              <span
                v-if="card.customSubcategoryName"
                class="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[11px] font-medium text-amber-700 dark:border-amber-400/20 dark:bg-amber-400/10 dark:text-amber-300"
              >
                {{ card.customSubcategoryName }}
              </span>
              <span class="rounded-full border border-sky-200 bg-sky-50 px-2.5 py-1 text-[11px] font-medium text-sky-700 dark:border-sky-400/20 dark:bg-sky-400/10 dark:text-sky-300">
                {{ card.functionGroupLabel }}
              </span>
              <span class="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-medium text-emerald-700 dark:border-emerald-400/20 dark:bg-emerald-400/10 dark:text-emerald-300">
                {{ card.disciplineLabel }}
              </span>
              <span
                v-for="tag in card.tags.slice(0, 3)"
                :key="tag"
                class="rounded-full border border-[var(--border-light)] bg-white/70 px-2.5 py-1 text-[11px] text-[var(--text-secondary)] dark:bg-white/5"
              >
                {{ tag }}
              </span>
            </div>

            <div class="mt-5 flex flex-wrap gap-2">
              <button
                type="button"
                class="rounded-2xl border border-[var(--border-light)] bg-white/70 px-3 py-2 text-sm text-[var(--text-secondary)] transition hover:bg-white dark:bg-white/5 dark:hover:bg-white/10"
                @click="$emit('open-card', card)"
              >
                Open
              </button>
              <button
                type="button"
                class="rounded-2xl border border-[var(--border-light)] bg-white/70 px-3 py-2 text-sm text-[var(--text-secondary)] transition hover:bg-white dark:bg-white/5 dark:hover:bg-white/10"
                @click="$emit('assign-card', card)"
              >
                Assign
              </button>
              <button
                v-if="card.customCategoryId"
                type="button"
                class="rounded-2xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-700 transition hover:bg-amber-100 dark:border-amber-400/20 dark:bg-amber-400/10 dark:text-amber-300"
                @click="$emit('clear-card', card)"
              >
                Clear
              </button>
              <button
                v-if="card.toolKind === 'external'"
                type="button"
                class="rounded-2xl border border-[var(--border-light)] bg-white/70 px-3 py-2 text-sm text-[var(--text-secondary)] transition hover:bg-white dark:bg-white/5 dark:hover:bg-white/10"
                @click="$emit('toggle-block', card)"
              >
                {{ card.blocked ? 'Unblock' : 'Block' }}
              </button>
              <button
                v-if="card.toolKind === 'external'"
                type="button"
                class="rounded-2xl border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-600 transition hover:bg-red-100 dark:border-red-400/20 dark:bg-red-400/10 dark:text-red-300"
                @click="$emit('delete-card', card)"
              >
                Delete
              </button>
            </div>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { UNCATEGORIZED_CATEGORY_ID } from './browseHelpers';
import type { BrowseSource, CustomCategoryOption, TaxonomyOption, ToolCard } from './types';

const activeChipClass = 'border-slate-900/10 bg-slate-900 text-white dark:border-white/20 dark:bg-white dark:text-slate-900';
const idleChipClass = 'border-[var(--border-light)] bg-white/70 text-[var(--text-secondary)] hover:bg-white dark:bg-white/5 dark:hover:bg-white/10';

const props = defineProps<{
  title: string;
  subtitle: string;
  loading: boolean;
  cards: ToolCard[];
  selectedNames: string[];
  browseSource: BrowseSource;
  activeSliceLabel: string;
  activeSubsliceLabel: string;
  systemFunctionGroupOptions: TaxonomyOption[];
  activeFunctionGroup: string;
  customCategoryOptions: CustomCategoryOption[];
  activeCustomCategoryId: string;
  customSubcategoryOptions: TaxonomyOption[];
  activeCustomSubcategoryId: string;
  uncategorizedCount: number;
}>();

defineEmits<{
  (event: 'assign-card', card: ToolCard): void;
  (event: 'assign-selected'): void;
  (event: 'create-category-selected'): void;
  (event: 'clear-card', card: ToolCard): void;
  (event: 'clear-selected'): void;
  (event: 'delete-card', card: ToolCard): void;
  (event: 'manage-categories'): void;
  (event: 'open-card', card: ToolCard): void;
  (event: 'refresh'): void;
  (event: 'reset-filters'): void;
  (event: 'set-function-group', groupId: string): void;
  (event: 'set-custom-category', categoryId: string): void;
  (event: 'set-custom-subcategory', subcategoryId: string): void;
  (event: 'toggle-block', card: ToolCard): void;
  (event: 'toggle-select', toolName: string): void;
  (event: 'toggle-visible'): void;
}>();

const allVisibleSelected = computed(() => props.cards.length > 0 && props.cards.every((card) => props.selectedNames.includes(card.name)));

const emptyStateDescription = computed(() => {
  if (props.browseSource === 'custom') {
    if (props.activeCustomCategoryId === UNCATEGORIZED_CATEGORY_ID) {
      return 'Everything in this region already has a custom category assignment.';
    }
    return 'Choose another custom category, clear the subcategory chip, or broaden the search query.';
  }

  return 'Choose another system discipline, reset the function-group filter, or broaden the search query.';
});
</script>
