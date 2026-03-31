<template>
  <div class="flex max-h-[80vh] flex-col">
    <div class="border-b border-[var(--border-light)] px-5 py-4">
      <div class="text-[11px] uppercase tracking-[0.18em] text-[var(--text-tertiary)]">Custom Categories</div>
      <h3 class="mt-2 text-lg font-semibold text-[var(--text-primary)]">Flexible personal overlay for {{ regionLabel.toLowerCase() }} tools</h3>
      <p class="mt-1 text-sm text-[var(--text-secondary)]">
        Keep the shared two-level tree, but create it faster with batch import, copying, context seeding, and drag-to-reorder editing.
      </p>
    </div>

    <div class="grid min-h-0 flex-1 grid-cols-1 gap-0 lg:grid-cols-[360px_minmax(0,1fr)]">
      <aside class="min-h-0 overflow-y-auto border-b border-[var(--border-light)] bg-[var(--background-gray-main)] px-5 py-5 lg:border-b-0 lg:border-r dark:bg-white/5">
        <div class="space-y-4">
          <div>
            <label class="mb-2 block text-sm font-medium text-[var(--text-primary)]">Search</label>
            <input v-model="searchQuery" type="text" class="manager-input" placeholder="Filter categories or subcategories">
          </div>

          <div class="rounded-[24px] border border-[var(--border-light)] bg-white/80 p-4 dark:bg-[#181818]">
            <div class="flex flex-wrap gap-2">
              <button type="button" class="manager-action template-import-button" @click="openTemplateImport">
                Import JSON
              </button>
              <button
                type="button"
                class="manager-action template-export-button"
                :disabled="!draftCategories.length"
                @click="exportTemplate"
              >
                Export JSON
              </button>
              <input
                ref="templateFileInput"
                type="file"
                class="hidden"
                accept=".json,application/json"
                @change="handleTemplateImport"
              >
            </div>
            <p class="mt-3 text-xs text-[var(--text-secondary)]">
              Reuse a personal two-level category tree across projects without changing the saved data model.
            </p>
          </div>

          <div
            v-if="managerNotice || templateWarnings.length"
            class="rounded-[24px] border p-4 text-sm"
            :class="noticeToneClass(managerNotice?.tone || 'info')"
          >
            <div class="font-medium">{{ managerNotice?.message || 'Import warnings' }}</div>
            <ul v-if="templateWarnings.length" class="mt-2 list-disc pl-4">
              <li v-for="warning in templateWarnings" :key="`${warning.line}-${warning.message}`">
                Entry {{ warning.line }}: {{ warning.message }}
              </li>
            </ul>
          </div>

          <div class="rounded-[24px] border border-[var(--border-light)] bg-white/80 p-4 dark:bg-[#181818]">
            <div class="flex flex-wrap gap-2">
              <button
                v-for="mode in createModes"
                :key="mode.id"
                type="button"
                class="mode-chip"
                :class="createMode === mode.id ? 'mode-chip-active' : ''"
                @click="createMode = mode.id"
              >
                {{ mode.label }}
              </button>
            </div>

            <div class="mt-4 space-y-4">
              <template v-if="createMode === 'single'">
                <div>
                  <label class="mb-2 block text-sm font-medium text-[var(--text-primary)]">Category name</label>
                  <input v-model="singleCategoryName" type="text" class="manager-input" placeholder="Examples: Reading Queue, Lab Notes">
                </div>
                <div>
                  <label class="mb-2 block text-sm font-medium text-[var(--text-primary)]">Subcategories</label>
                  <textarea
                    v-model="singleSubcategoryText"
                    class="manager-textarea"
                    rows="5"
                    placeholder="One per line. Paste plain lines or use Category > Subcategory and only the subcategory part will be kept."
                  />
                </div>
              </template>

              <template v-else-if="createMode === 'batch'">
                <div>
                  <label class="mb-2 block text-sm font-medium text-[var(--text-primary)]">Batch paste</label>
                  <textarea
                    v-model="batchText"
                    class="manager-textarea"
                    rows="9"
                    placeholder="Examples:&#10;Literature&#10;Literature > Papers To Read&#10;Materials / CIF Notes&#10;Experiments&#10;  Synthesis&#10;  Characterization"
                  />
                </div>
              </template>

              <template v-else-if="createMode === 'copy'">
                <div>
                  <label class="mb-2 block text-sm font-medium text-[var(--text-primary)]">Source category</label>
                  <select v-model="copyCategoryId" class="manager-select">
                    <option value="">Select a category</option>
                    <option v-for="category in draftCategories" :key="category.id" :value="category.id">{{ category.name }}</option>
                  </select>
                </div>
                <label class="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
                  <input v-model="copyIncludeSubcategories" type="checkbox" class="h-4 w-4 rounded border-[var(--border-light)]">
                  Copy subcategories too
                </label>
              </template>

              <template v-else>
                <div>
                  <label class="mb-2 block text-sm font-medium text-[var(--text-primary)]">Context source</label>
                  <div class="space-y-2">
                    <button
                      v-for="option in contextOptions"
                      :key="option.id"
                      type="button"
                      class="context-option"
                      :class="contextSourceId === option.id ? 'context-option-active' : ''"
                      :disabled="option.disabled"
                      @click="selectContextOption(option.id)"
                    >
                      <div class="font-medium text-[var(--text-primary)]">{{ option.label }}</div>
                      <div class="mt-1 text-xs text-[var(--text-secondary)]">{{ option.description }}</div>
                    </button>
                  </div>
                </div>

                <div>
                  <label class="mb-2 block text-sm font-medium text-[var(--text-primary)]">Generated category name</label>
                  <input v-model="contextCategoryName" type="text" class="manager-input" placeholder="Category name for this generated draft">
                </div>

                <div class="rounded-[20px] border border-[var(--border-light)] bg-[var(--background-gray-main)] px-3 py-3 text-xs text-[var(--text-secondary)] dark:bg-white/5">
                  <div class="font-medium text-[var(--text-primary)]">Seeded subcategories</div>
                  <div class="mt-2 flex flex-wrap gap-2">
                    <span
                      v-for="subcategory in activeContextSubcategories.slice(0, 10)"
                      :key="subcategory"
                      class="rounded-full border border-[var(--border-light)] bg-white/70 px-2.5 py-1 dark:bg-white/10"
                    >
                      {{ subcategory }}
                    </span>
                    <span v-if="activeContextSubcategories.length > 10" class="rounded-full bg-black/5 px-2.5 py-1 dark:bg-white/10">
                      +{{ activeContextSubcategories.length - 10 }} more
                    </span>
                    <span v-if="!activeContextSubcategories.length" class="text-[var(--text-secondary)]">No subcategories available for this source.</span>
                  </div>
                </div>
              </template>

              <div v-if="currentCreatorWarnings.length" class="rounded-[20px] border border-amber-200 bg-amber-50 px-3 py-3 text-sm text-amber-700 dark:border-amber-400/20 dark:bg-amber-400/10 dark:text-amber-200">
                <div class="font-medium">Import warnings</div>
                <ul class="mt-2 list-disc pl-4">
                  <li v-for="warning in currentCreatorWarnings" :key="`${warning.line}-${warning.message}`">
                    Line {{ warning.line }}: {{ warning.message }}
                  </li>
                </ul>
              </div>

              <div class="rounded-[20px] border border-[var(--border-light)] bg-[var(--background-gray-main)] px-4 py-4 dark:bg-white/5">
                <div class="flex items-center justify-between gap-3">
                  <div>
                    <div class="text-sm font-medium text-[var(--text-primary)]">Apply preview</div>
                    <div class="mt-1 text-xs text-[var(--text-secondary)]">
                      {{ stagedPreview.summary.categoriesCreated }} create / {{ stagedPreview.summary.categoriesMerged }} merge / {{ stagedPreview.summary.categoriesSkipped }} skip
                    </div>
                  </div>
                  <button type="button" class="manager-primary" :disabled="!creatorHasEffect" @click="applyCreator">
                    Apply To Draft
                  </button>
                </div>

                <div class="mt-3 grid grid-cols-2 gap-2 text-xs text-[var(--text-secondary)]">
                  <div>{{ stagedPreview.summary.subcategoriesCreated }} new subcategories</div>
                  <div>{{ stagedPreview.summary.subcategoriesMerged }} merged into existing</div>
                  <div>{{ stagedPreview.summary.subcategoriesSkipped }} skipped duplicates</div>
                  <div>{{ creatorSeedCount }} valid category seeds</div>
                </div>

                <div v-if="stagedPreview.preview.length" class="mt-3 space-y-2">
                  <div
                    v-for="item in stagedPreview.preview"
                    :key="item.name"
                    class="rounded-[18px] border border-[var(--border-light)] bg-white/80 px-3 py-3 dark:bg-[#161616]"
                  >
                    <div class="flex items-center justify-between gap-2">
                      <div class="font-medium text-[var(--text-primary)]">{{ item.name }}</div>
                      <span class="preview-pill" :class="previewPillClass(item.action)">
                        {{ previewLabel(item.action) }}
                      </span>
                    </div>
                    <div v-if="item.createdSubcategories.length" class="mt-2 text-xs text-[var(--text-secondary)]">
                      New: {{ item.createdSubcategories.join(', ') }}
                    </div>
                    <div v-if="item.mergedSubcategories.length" class="mt-2 text-xs text-[var(--text-secondary)]">
                      Merge in: {{ item.mergedSubcategories.join(', ') }}
                    </div>
                    <div v-if="item.skippedSubcategories.length" class="mt-2 text-xs text-[var(--text-secondary)]">
                      Skip: {{ item.skippedSubcategories.join(', ') }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="rounded-[24px] border border-[var(--border-light)] bg-white/80 p-4 text-sm dark:bg-[#181818]">
            <div class="font-medium text-[var(--text-primary)]">Draft summary</div>
            <div class="mt-3 space-y-2 text-[var(--text-secondary)]">
              <div>{{ filteredCategories.length }} categories in view</div>
              <div>{{ draftCategories.length }} categories in draft</div>
              <div>{{ previewAssignments.science }} science assignments remain valid</div>
              <div>{{ previewAssignments.external }} external assignments remain valid</div>
              <div v-if="selectedToolCount">{{ selectedToolCount }} selected tools can be quick-assigned during save</div>
            </div>
          </div>

          <div class="rounded-[24px] border border-[var(--border-light)] bg-white/80 p-4 text-sm dark:bg-[#181818]">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div class="font-medium text-[var(--text-primary)]">Bulk delete</div>
                <div class="mt-1 text-xs text-[var(--text-secondary)]">Select categories from the current left-side view and remove them in one action.</div>
              </div>
              <span class="rounded-full bg-black/5 px-2.5 py-1 text-[11px] text-[var(--text-secondary)] dark:bg-white/10">
                {{ selectedCategoryIds.length }} selected
              </span>
            </div>

            <div class="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                class="manager-action bulk-select-visible-button"
                :disabled="!filteredCategories.length"
                @click="toggleAllVisibleCategories"
              >
                {{ allVisibleCategoriesSelected ? 'Clear View Selection' : 'Select View' }}
              </button>
              <button
                type="button"
                class="manager-action bulk-clear-selection-button"
                :disabled="!selectedCategoryIds.length"
                @click="clearSelectedCategories"
              >
                Clear Selection
              </button>
            </div>

            <div class="mt-4 max-h-[220px] space-y-2 overflow-y-auto pr-1">
              <label
                v-for="category in filteredCategories"
                :key="category.id"
                class="category-multiselect-row"
              >
                <input
                  type="checkbox"
                  class="category-select-toggle"
                  :checked="selectedCategoryIds.includes(category.id)"
                  @change="toggleSelectedCategory(category.id)"
                >
                <div class="min-w-0 flex-1">
                  <div class="truncate font-medium text-[var(--text-primary)]">{{ category.name || 'Untitled category' }}</div>
                  <div class="mt-1 text-xs text-[var(--text-secondary)]">{{ category.subcategories.length }} subcategories</div>
                </div>
                <span class="rounded-full bg-black/5 px-2.5 py-1 text-[11px] text-[var(--text-secondary)] dark:bg-white/10">
                  {{ assignmentStats.get(category.id)?.total || 0 }}
                </span>
              </label>

              <div
                v-if="!filteredCategories.length"
                class="rounded-[18px] border border-dashed border-[var(--border-light)] bg-[var(--background-gray-main)] px-3 py-3 text-xs text-[var(--text-secondary)] dark:bg-white/5"
              >
                No categories match the current search.
              </div>
            </div>

            <div class="mt-4 rounded-[20px] border border-[var(--border-light)] bg-[var(--background-gray-main)] px-3 py-3 text-xs text-[var(--text-secondary)] dark:bg-white/5">
              <div>{{ selectedCategoryIds.length }} categories selected</div>
              <div>{{ selectedCategoryAssignmentCount }} assignments would be removed with them</div>
            </div>

            <button
              type="button"
              class="manager-delete bulk-delete-button mt-3 w-full"
              :disabled="!selectedCategoryIds.length"
              @click="removeSelectedCategories"
            >
              Delete Selected ({{ selectedCategoryIds.length }})
            </button>
          </div>

          <div v-if="validationErrors.length" class="rounded-[24px] border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-400/20 dark:bg-red-400/10 dark:text-red-300">
            <div class="font-medium">Validation</div>
            <ul class="mt-2 list-disc pl-4">
              <li v-for="error in validationErrors" :key="error">{{ error }}</li>
            </ul>
          </div>
        </div>
      </aside>

      <div class="min-h-0 overflow-y-auto px-5 py-5">
        <div
          v-if="lastRemovedEntry"
          class="undo-banner mb-4 rounded-[24px] border border-[var(--border-light)] bg-white/85 p-4 shadow-sm dark:bg-[#171717]"
        >
          <div class="text-sm font-medium text-[var(--text-primary)]">Undo last delete</div>
          <p class="mt-1 text-sm text-[var(--text-secondary)]">{{ lastRemovedMessage }}</p>
          <div class="mt-3 flex flex-wrap gap-2">
            <button type="button" class="manager-primary undo-restore-button" @click="restoreLastRemoved">
              Restore
            </button>
            <button type="button" class="manager-action undo-dismiss-button" @click="dismissLastRemoved">
              Dismiss
            </button>
          </div>
        </div>

        <div v-if="!filteredCategories.length" class="flex min-h-[320px] flex-col items-center justify-center rounded-[28px] border border-dashed border-[var(--border-light)] bg-white/60 px-6 text-center dark:bg-white/5">
          <div class="text-base font-semibold text-[var(--text-primary)]">No categories in this view</div>
          <p class="mt-2 max-w-md text-sm text-[var(--text-secondary)]">Use the creator on the left to batch-build a draft, then refine names and ordering here.</p>
        </div>

        <div v-else class="space-y-4">
          <article
            v-for="category in filteredCategories"
            :key="category.id"
            class="rounded-[28px] border border-[var(--border-light)] bg-white/90 shadow-sm dark:bg-[#171717]"
            draggable="true"
            @dragstart="startCategoryDrag(category.id)"
            @dragover.prevent
            @drop="dropCategory(category.id)"
            @dragend="clearCategoryDrag"
          >
            <div class="border-b border-[var(--border-light)] px-5 py-4">
              <div class="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
                <div class="flex flex-1 items-start gap-3">
                  <div class="drag-handle" title="Drag to reorder">::</div>
                  <div class="flex-1">
                    <label class="mb-2 block text-xs uppercase tracking-[0.16em] text-[var(--text-tertiary)]">Category Name</label>
                    <input v-model="category.name" type="text" class="manager-input" placeholder="Category name">
                  </div>
                </div>
                <div class="flex flex-wrap gap-2">
                  <span class="rounded-full bg-black/5 px-2.5 py-1 text-[11px] text-[var(--text-secondary)] dark:bg-white/10">
                    {{ assignmentStats.get(category.id)?.total || 0 }} assigned
                  </span>
                  <button
                    v-if="selectedToolCount"
                    type="button"
                    class="selection-chip"
                    :class="quickAssignCategoryId === category.id ? 'selection-chip-active' : ''"
                    @click="quickAssignCategoryId = quickAssignCategoryId === category.id ? '' : category.id"
                  >
                    {{ quickAssignCategoryId === category.id ? 'Selected For Quick Assign' : 'Quick Assign Selection' }}
                  </button>
                  <button type="button" class="manager-action" @click="addSubcategory(category.id)">Add subcategory</button>
                  <button type="button" class="manager-action" @click="toggleBulkSubcategoryEditor(category.id)">
                    {{ bulkSubcategoryOpenId === category.id ? 'Close Bulk Add' : 'Bulk Add Subcategories' }}
                  </button>
                  <button type="button" class="manager-delete category-delete-button" @click="removeCategory(category.id)">
                    Delete ({{ assignmentStats.get(category.id)?.total || 0 }})
                  </button>
                </div>
              </div>
            </div>

            <div class="space-y-3 px-5 py-5">
              <div
                v-if="bulkSubcategoryOpenId === category.id"
                class="rounded-[22px] border border-[var(--border-light)] bg-[var(--background-gray-main)] px-4 py-4 dark:bg-white/5"
              >
                <div class="flex flex-col gap-3 lg:flex-row lg:items-start">
                  <div class="flex-1">
                    <label class="mb-2 block text-sm font-medium text-[var(--text-primary)]">Paste subcategories for {{ category.name || 'this category' }}</label>
                    <textarea
                      v-model="bulkSubcategoryDrafts[category.id]"
                      class="manager-textarea"
                      rows="5"
                      placeholder="One per line. You can also paste Category > Subcategory and only the subcategory part will be used."
                    />
                  </div>
                  <div class="min-w-[220px] rounded-[20px] border border-[var(--border-light)] bg-white/80 px-3 py-3 text-xs text-[var(--text-secondary)] dark:bg-[#161616]">
                    <div class="font-medium text-[var(--text-primary)]">Bulk add preview</div>
                    <div class="mt-2">{{ bulkSubcategoryNames(category.id).length }} parsed names</div>
                    <div>{{ bulkSubcategoryPreview(category.id).summary.subcategoriesMerged }} will be added</div>
                    <div>{{ bulkSubcategoryPreview(category.id).summary.subcategoriesSkipped }} duplicates skipped</div>
                    <button type="button" class="manager-primary mt-3 w-full" :disabled="!bulkSubcategoryPreview(category.id).summary.subcategoriesMerged" @click="applyBulkSubcategories(category.id)">
                      Add To Category
                    </button>
                  </div>
                </div>
              </div>

              <div v-if="!category.subcategories.length" class="rounded-[22px] border border-dashed border-[var(--border-light)] bg-[var(--background-gray-main)] px-4 py-4 text-sm text-[var(--text-secondary)] dark:bg-white/5">
                No subcategories yet.
              </div>
              <div
                v-for="subcategory in category.subcategories"
                :key="subcategory.id"
                class="flex flex-col gap-3 rounded-[22px] border border-[var(--border-light)] bg-[var(--background-gray-main)] px-4 py-4 md:flex-row md:items-center dark:bg-white/5"
                draggable="true"
                @dragstart="startSubcategoryDrag(category.id, subcategory.id)"
                @dragover.prevent
                @drop="dropSubcategory(category.id, subcategory.id)"
                @dragend="clearSubcategoryDrag"
              >
                <div class="drag-handle shrink-0" title="Drag to reorder">::</div>
                <input v-model="subcategory.name" type="text" class="manager-input flex-1" placeholder="Subcategory name">
                <button
                  type="button"
                  class="manager-delete subcategory-delete-button"
                  @click="removeSubcategory(category.id, subcategory.id)"
                >
                  Delete
                </button>
              </div>
            </div>
          </article>
        </div>
      </div>
    </div>

    <div class="flex justify-end gap-2 border-t border-[var(--border-light)] px-5 py-4">
      <button
        type="button"
        class="rounded-2xl border border-[var(--border-light)] bg-white/70 px-4 py-2 text-sm text-[var(--text-secondary)] transition hover:bg-white dark:bg-white/5 dark:hover:bg-white/10"
        @click="$emit('close')"
      >
        Cancel
      </button>
      <button
        type="button"
        class="rounded-2xl bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100"
        :disabled="validationErrors.length > 0"
        @click="submit"
      >
        Save Categories
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import {
  appendSubcategoriesToCategory,
  applyCategorySeeds,
  buildCopySeed,
  buildSingleCategorySeed,
  cloneCategories,
  moveItemById,
  nextToolLibraryId,
  normalizeCategoryKey,
  normalizeCategoryLabel,
  parseCategoryBatchText,
  parseCategoryTemplateJson,
  parseSubcategoryText,
  reindexCategories,
  serializeCategoryTemplate,
  validateCategoryDraft,
} from './categoryBuilder';
import type {
  CategoryApplyResult,
  CategoryContextOption,
  CategoryCreateMode,
  CategoryImportWarning,
  ParsedCategorySeed,
  TaxonomyOption,
  ToolLibraryCategory,
  ToolLibrarySubcategory,
} from './types';

type CategoryAssignmentStat = {
  total: number;
  science: number;
  external: number;
};

type ManagerNotice = {
  tone: 'success' | 'error' | 'info';
  message: string;
};

type LastRemovedEntry =
  | {
      kind: 'category';
      category: ToolLibraryCategory;
      index: number;
      quickAssignSelected: boolean;
      bulkEditorOpen: boolean;
    }
  | {
      kind: 'category-batch';
      categories: Array<{
        category: ToolLibraryCategory;
        index: number;
        quickAssignSelected: boolean;
        bulkEditorOpen: boolean;
      }>;
    }
  | {
      kind: 'subcategory';
      categoryId: string;
      categoryName: string;
      subcategory: ToolLibrarySubcategory;
      index: number;
    };

const props = defineProps<{
  categories: ToolLibraryCategory[];
  assignmentStats: Map<string, CategoryAssignmentStat>;
  disciplinePresets: TaxonomyOption[];
  functionGroupPresets: TaxonomyOption[];
  currentSliceLabel: string;
  currentSliceChildren: TaxonomyOption[];
  selectedToolCount: number;
  selectedToolNames: string[];
  visibleToolNames: string[];
  activeFunctionGroupLabel: string;
  activeSearchQuery: string;
  regionLabel: string;
}>();

const emit = defineEmits<{
  (event: 'close'): void;
  (event: 'save', payload: { categories: ToolLibraryCategory[]; quickAssignCategoryId: string }): void;
}>();

const createModes: Array<{ id: CategoryCreateMode; label: string }> = [
  { id: 'single', label: 'Single' },
  { id: 'batch', label: 'Batch' },
  { id: 'copy', label: 'Copy' },
  { id: 'context', label: 'Context' },
];

const searchQuery = ref('');
const draftCategories = ref<ToolLibraryCategory[]>([]);
const quickAssignCategoryId = ref('');
const templateFileInput = ref<HTMLInputElement | null>(null);
const managerNotice = ref<ManagerNotice | null>(null);
const templateWarnings = ref<CategoryImportWarning[]>([]);
const lastRemovedEntry = ref<LastRemovedEntry | null>(null);
const selectedCategoryIds = ref<string[]>([]);

const createMode = ref<CategoryCreateMode>('single');
const singleCategoryName = ref('');
const singleSubcategoryText = ref('');
const batchText = ref('');
const copyCategoryId = ref('');
const copyIncludeSubcategories = ref(true);
const contextSourceId = ref<CategoryContextOption['id']>('discipline');
const contextCategoryName = ref('');

const bulkSubcategoryOpenId = ref('');
const bulkSubcategoryDrafts = reactive<Record<string, string>>({});

const draggedCategoryId = ref('');
const draggedSubcategory = ref<{ categoryId: string; subcategoryId: string }>({
  categoryId: '',
  subcategoryId: '',
});

watch(
  () => props.categories,
  (value) => {
    draftCategories.value = cloneCategories(value);
    if (quickAssignCategoryId.value && !draftCategories.value.some((category) => category.id === quickAssignCategoryId.value)) {
      quickAssignCategoryId.value = '';
    }
    lastRemovedEntry.value = null;
    managerNotice.value = null;
    templateWarnings.value = [];
  },
  { immediate: true, deep: true },
);

watch(
  draftCategories,
  (value) => {
    const validIds = new Set(value.map((category) => category.id));
    selectedCategoryIds.value = selectedCategoryIds.value.filter((categoryId) => validIds.has(categoryId));
  },
  { deep: true },
);

const contextOptions = computed<CategoryContextOption[]>(() => [
  {
    id: 'discipline',
    label: 'Current discipline',
    description: props.currentSliceLabel
      ? `Create "${props.currentSliceLabel}" with the current function-group slice as subcategories.`
      : 'Pick a discipline in the main library first.',
    categoryName: props.currentSliceLabel || 'Current Discipline',
    subcategories: props.currentSliceChildren.map((option) => option.labelZh || option.label),
    disabled: !props.currentSliceLabel,
  },
  {
    id: 'function-group',
    label: 'Current function group',
    description: props.activeFunctionGroupLabel
      ? `Create "${props.activeFunctionGroupLabel}" and seed visible tool names as subcategories.`
      : 'Select a function-group chip in the main library first.',
    categoryName: props.activeFunctionGroupLabel || 'Current Function Group',
    subcategories: props.visibleToolNames,
    disabled: !props.activeFunctionGroupLabel || !props.visibleToolNames.length,
  },
  {
    id: 'search-result',
    label: 'Current search result',
    description: props.activeSearchQuery
      ? `Seed from the tools currently matched by "${props.activeSearchQuery}".`
      : 'Type a search query in the main library first.',
    categoryName: props.activeSearchQuery ? `Search ${props.activeSearchQuery}` : 'Search Results',
    subcategories: props.visibleToolNames,
    disabled: !props.activeSearchQuery || !props.visibleToolNames.length,
  },
  {
    id: 'selected-tools',
    label: 'Selected tools',
    description: props.selectedToolNames.length
      ? 'Turn the currently selected tools into a draft category immediately.'
      : 'Select one or more tools in the main library first.',
    categoryName: props.selectedToolNames.length ? `${props.regionLabel} Selection` : 'Selected Tools',
    subcategories: props.selectedToolNames,
    disabled: !props.selectedToolNames.length,
  },
]);

const activeContextOption = computed(
  () => contextOptions.value.find((option) => option.id === contextSourceId.value) || contextOptions.value[0],
);

const activeContextSubcategories = computed(() => activeContextOption.value?.subcategories || []);

watch(
  contextOptions,
  (options) => {
    const current = options.find((option) => option.id === contextSourceId.value && !option.disabled);
    const next = current || options.find((option) => !option.disabled) || options[0];
    if (!next) {
      return;
    }
    if (next.id !== contextSourceId.value) {
      contextSourceId.value = next.id;
    }
    contextCategoryName.value = next.categoryName;
  },
  { immediate: true, deep: true },
);

const copySourceCategory = computed(
  () => draftCategories.value.find((category) => category.id === copyCategoryId.value) || null,
);

const creatorPayload = computed((): {
  seeds: ParsedCategorySeed[];
  warnings: CategoryImportWarning[];
} => {
  if (createMode.value === 'single') {
    const seed = buildSingleCategorySeed(singleCategoryName.value, singleSubcategoryText.value);
    return { seeds: seed ? [seed] : [], warnings: [] };
  }

  if (createMode.value === 'batch') {
    return parseCategoryBatchText(batchText.value);
  }

  if (createMode.value === 'copy') {
    const seed = buildCopySeed(copySourceCategory.value, draftCategories.value, copyIncludeSubcategories.value);
    return { seeds: seed ? [seed] : [], warnings: [] };
  }

  const seed = buildSingleCategorySeed(
    contextCategoryName.value,
    activeContextSubcategories.value.join('\n'),
  );
  return {
    seeds: seed ? [seed] : [],
    warnings: activeContextOption.value?.disabled
      ? [{ line: 0, raw: '', message: activeContextOption.value.description }]
      : [],
  };
});

const creatorSeedCount = computed(() => creatorPayload.value.seeds.length);
const currentCreatorWarnings = computed(() => creatorPayload.value.warnings.filter((warning) => warning.message));
const stagedPreview = computed<CategoryApplyResult>(() => applyCategorySeeds(draftCategories.value, creatorPayload.value.seeds));
const creatorHasEffect = computed(() => {
  const summary = stagedPreview.value.summary;
  return creatorSeedCount.value > 0 && (
    summary.categoriesCreated > 0 ||
    summary.categoriesMerged > 0 ||
    summary.subcategoriesCreated > 0 ||
    summary.subcategoriesMerged > 0
  );
});

const filteredCategories = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();
  if (!query) {
    return draftCategories.value;
  }
  return draftCategories.value.filter((category) => {
    const haystack = [
      category.name,
      ...category.subcategories.map((subcategory) => subcategory.name),
    ]
      .join(' ')
      .toLowerCase();
    return haystack.includes(query);
  });
});

const validationErrors = computed(() => validateCategoryDraft(draftCategories.value));
const allVisibleCategoriesSelected = computed(() =>
  filteredCategories.value.length > 0
  && filteredCategories.value.every((category) => selectedCategoryIds.value.includes(category.id))
);
const selectedCategoryAssignmentCount = computed(() =>
  selectedCategoryIds.value.reduce((total, categoryId) => total + (props.assignmentStats.get(categoryId)?.total || 0), 0)
);

const previewAssignments = computed(() => {
  const validCategoryIds = new Set(draftCategories.value.map((category) => category.id));
  let science = 0;
  let external = 0;

  for (const category of draftCategories.value) {
    const stat = props.assignmentStats.get(category.id);
    if (!validCategoryIds.has(category.id) || !stat) {
      continue;
    }
    science += stat.science;
    external += stat.external;
  }

  return { science, external };
});

const lastRemovedMessage = computed(() => {
  if (!lastRemovedEntry.value) {
    return '';
  }
  if (lastRemovedEntry.value.kind === 'category') {
    return `Restore category "${lastRemovedEntry.value.category.name}" and its ${lastRemovedEntry.value.category.subcategories.length} subcategories.`;
  }
  if (lastRemovedEntry.value.kind === 'category-batch') {
    const totalSubcategories = lastRemovedEntry.value.categories.reduce(
      (count, entry) => count + entry.category.subcategories.length,
      0,
    );
    return `Restore ${lastRemovedEntry.value.categories.length} categories and ${totalSubcategories} subcategories from the last bulk delete.`;
  }
  return `Restore subcategory "${lastRemovedEntry.value.subcategory.name}" under "${lastRemovedEntry.value.categoryName}".`;
});

function setManagerNotice(tone: ManagerNotice['tone'], message: string, warnings: CategoryImportWarning[] = []): void {
  managerNotice.value = { tone, message };
  templateWarnings.value = warnings;
}

function clearManagerNotice(): void {
  managerNotice.value = null;
  templateWarnings.value = [];
}

function noticeToneClass(tone: ManagerNotice['tone']): string {
  if (tone === 'success') {
    return 'manager-notice manager-notice-success';
  }
  if (tone === 'error') {
    return 'manager-notice manager-notice-error';
  }
  return 'manager-notice manager-notice-info';
}

function openTemplateImport(): void {
  templateFileInput.value?.click();
}

async function handleTemplateImport(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement | null;
  const file = input?.files?.[0];
  if (!file) {
    return;
  }

  try {
    const text = await file.text();
    const parsed = parseCategoryTemplateJson(text);
    if (!parsed.seeds.length) {
      setManagerNotice('error', 'The JSON file did not contain any valid categories to import.', parsed.warnings);
      return;
    }

    const result = applyCategorySeeds(draftCategories.value, parsed.seeds);
    draftCategories.value = result.categories;

    const changedCount = result.summary.categoriesCreated
      + result.summary.categoriesMerged
      + result.summary.subcategoriesCreated
      + result.summary.subcategoriesMerged;
    if (!changedCount) {
      setManagerNotice(
        parsed.warnings.length ? 'info' : 'success',
        'Template parsed successfully, but every category already exists in the current draft.',
        parsed.warnings,
      );
      return;
    }

    const tone: ManagerNotice['tone'] = parsed.warnings.length ? 'info' : 'success';
    setManagerNotice(
      tone,
      `Imported template into the current draft: ${result.summary.categoriesCreated} created, ${result.summary.categoriesMerged} merged, ${result.summary.subcategoriesCreated + result.summary.subcategoriesMerged} subcategories added.`,
      parsed.warnings,
    );
  } catch (error) {
    setManagerNotice(
      'error',
      error instanceof Error ? error.message : 'Failed to import the JSON template.',
    );
  } finally {
    if (input) {
      input.value = '';
    }
  }
}

function exportTemplate(): void {
  if (!draftCategories.value.length) {
    return;
  }
  const json = serializeCategoryTemplate(draftCategories.value);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `tool-library-categories-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
  setManagerNotice('success', `Exported ${draftCategories.value.length} categories to a reusable JSON template.`);
}

function makeUniqueRestoredLabel(label: string, existingLabels: string[]): string {
  const base = normalizeCategoryLabel(label) || 'Restored';
  const existingKeys = new Set(existingLabels.map((item) => normalizeCategoryKey(item)));
  if (!existingKeys.has(normalizeCategoryKey(base))) {
    return base;
  }
  let candidate = `${base} Restored`;
  let index = 2;
  while (existingKeys.has(normalizeCategoryKey(candidate))) {
    candidate = `${base} Restored ${index}`;
    index += 1;
  }
  return candidate;
}

function resetCreatorInputs(): void {
  if (createMode.value === 'single') {
    singleCategoryName.value = '';
    singleSubcategoryText.value = '';
    return;
  }
  if (createMode.value === 'batch') {
    batchText.value = '';
    return;
  }
  if (createMode.value === 'copy') {
    copyCategoryId.value = '';
    copyIncludeSubcategories.value = true;
    return;
  }
  contextCategoryName.value = activeContextOption.value?.categoryName || '';
}

function applyCreator(): void {
  if (!creatorHasEffect.value) {
    return;
  }
  draftCategories.value = stagedPreview.value.categories;
  clearManagerNotice();
  resetCreatorInputs();
}

function addSubcategory(categoryId: string, suggestedName = ''): void {
  const next = appendSubcategoriesToCategory(draftCategories.value, categoryId, [suggestedName || 'New Subcategory']);
  draftCategories.value = next.categories;
}

function toggleSelectedCategory(categoryId: string): void {
  const next = new Set(selectedCategoryIds.value);
  if (next.has(categoryId)) {
    next.delete(categoryId);
  } else {
    next.add(categoryId);
  }
  selectedCategoryIds.value = Array.from(next);
}

function toggleAllVisibleCategories(): void {
  const visibleIds = filteredCategories.value.map((category) => category.id);
  const next = new Set(selectedCategoryIds.value);
  if (allVisibleCategoriesSelected.value) {
    for (const categoryId of visibleIds) {
      next.delete(categoryId);
    }
  } else {
    for (const categoryId of visibleIds) {
      next.add(categoryId);
    }
  }
  selectedCategoryIds.value = Array.from(next);
}

function clearSelectedCategories(): void {
  selectedCategoryIds.value = [];
}

function removeCategory(categoryId: string): void {
  const categoryIndex = draftCategories.value.findIndex((category) => category.id === categoryId);
  const category = categoryIndex >= 0 ? draftCategories.value[categoryIndex] : null;
  if (!category) {
    return;
  }
  lastRemovedEntry.value = {
    kind: 'category',
    category: cloneCategories([category])[0],
    index: categoryIndex,
    quickAssignSelected: quickAssignCategoryId.value === categoryId,
    bulkEditorOpen: bulkSubcategoryOpenId.value === categoryId,
  };
  draftCategories.value = reindexCategories(
    draftCategories.value.filter((category) => category.id !== categoryId),
  );
  if (quickAssignCategoryId.value === categoryId) {
    quickAssignCategoryId.value = '';
  }
  if (bulkSubcategoryOpenId.value === categoryId) {
    bulkSubcategoryOpenId.value = '';
  }
  selectedCategoryIds.value = selectedCategoryIds.value.filter((id) => id !== categoryId);
}

function removeSelectedCategories(): void {
  const selectedIds = new Set(selectedCategoryIds.value);
  if (!selectedIds.size) {
    return;
  }

  const removedCategories = draftCategories.value
    .map((category, index) => ({ category, index }))
    .filter((entry) => selectedIds.has(entry.category.id))
    .map((entry) => ({
      category: cloneCategories([entry.category])[0],
      index: entry.index,
      quickAssignSelected: quickAssignCategoryId.value === entry.category.id,
      bulkEditorOpen: bulkSubcategoryOpenId.value === entry.category.id,
    }));

  if (!removedCategories.length) {
    return;
  }

  lastRemovedEntry.value = {
    kind: 'category-batch',
    categories: removedCategories,
  };
  draftCategories.value = reindexCategories(
    draftCategories.value.filter((category) => !selectedIds.has(category.id)),
  );
  if (selectedIds.has(quickAssignCategoryId.value)) {
    quickAssignCategoryId.value = '';
  }
  if (selectedIds.has(bulkSubcategoryOpenId.value)) {
    bulkSubcategoryOpenId.value = '';
  }
  selectedCategoryIds.value = [];
}

function removeSubcategory(categoryId: string, subcategoryId: string): void {
  const category = draftCategories.value.find((item) => item.id === categoryId);
  const subcategoryIndex = category?.subcategories.findIndex((item) => item.id === subcategoryId) ?? -1;
  const subcategory = subcategoryIndex >= 0 && category ? category.subcategories[subcategoryIndex] : null;
  if (!category || !subcategory) {
    return;
  }
  lastRemovedEntry.value = {
    kind: 'subcategory',
    categoryId,
    categoryName: category.name,
    subcategory: { ...subcategory },
    index: subcategoryIndex,
  };
  draftCategories.value = reindexCategories(
    draftCategories.value.map((category) => (
      category.id === categoryId
        ? { ...category, subcategories: category.subcategories.filter((subcategory) => subcategory.id !== subcategoryId) }
        : category
    )),
  );
}

function toggleBulkSubcategoryEditor(categoryId: string): void {
  bulkSubcategoryOpenId.value = bulkSubcategoryOpenId.value === categoryId ? '' : categoryId;
}

function bulkSubcategoryNames(categoryId: string): string[] {
  return parseSubcategoryText(bulkSubcategoryDrafts[categoryId] || '');
}

function bulkSubcategoryPreview(categoryId: string): CategoryApplyResult {
  return appendSubcategoriesToCategory(draftCategories.value, categoryId, bulkSubcategoryNames(categoryId));
}

function applyBulkSubcategories(categoryId: string): void {
  const preview = bulkSubcategoryPreview(categoryId);
  if (!preview.summary.subcategoriesMerged) {
    return;
  }
  draftCategories.value = preview.categories;
  bulkSubcategoryDrafts[categoryId] = '';
}

function restoreLastRemoved(): void {
  const entry = lastRemovedEntry.value;
  if (!entry) {
    return;
  }

  if (entry.kind === 'category') {
    const restoredCategory = restoreCategoryEntry(entry, [...draftCategories.value]);
    draftCategories.value = reindexCategories(restoredCategory.categories);
    lastRemovedEntry.value = null;
    if (restoredCategory.quickAssignCategoryId) {
      quickAssignCategoryId.value = restoredCategory.quickAssignCategoryId;
    }
    if (restoredCategory.bulkEditorOpenId) {
      bulkSubcategoryOpenId.value = restoredCategory.bulkEditorOpenId;
    }
    setManagerNotice('success', `Restored category "${restoredCategory.restoredNames[0]}".`);
    return;
  }

  if (entry.kind === 'category-batch') {
    const orderedEntries = [...entry.categories].sort((left, right) => left.index - right.index);
    let nextCategories = [...draftCategories.value];
    let restoredQuickAssignId = '';
    let restoredBulkEditorId = '';
    const restoredNames: string[] = [];

    for (const removedCategory of orderedEntries) {
      const restored = restoreCategoryEntry(removedCategory, nextCategories);
      nextCategories = restored.categories;
      restoredNames.push(...restored.restoredNames);
      if (restored.quickAssignCategoryId) {
        restoredQuickAssignId = restored.quickAssignCategoryId;
      }
      if (restored.bulkEditorOpenId) {
        restoredBulkEditorId = restored.bulkEditorOpenId;
      }
    }

    draftCategories.value = reindexCategories(nextCategories);
    if (restoredQuickAssignId) {
      quickAssignCategoryId.value = restoredQuickAssignId;
    }
    if (restoredBulkEditorId) {
      bulkSubcategoryOpenId.value = restoredBulkEditorId;
    }
    lastRemovedEntry.value = null;
    setManagerNotice('success', `Restored ${restoredNames.length} categories.`);
    return;
  }

  const category = draftCategories.value.find((item) => item.id === entry.categoryId);
  if (!category) {
    lastRemovedEntry.value = null;
    setManagerNotice('error', `Cannot restore "${entry.subcategory.name}" because "${entry.categoryName}" no longer exists in the draft.`);
    return;
  }

  const restoredSubcategory = { ...entry.subcategory };
  restoredSubcategory.name = makeUniqueRestoredLabel(
    restoredSubcategory.name,
    category.subcategories.map((subcategory) => subcategory.name),
  );
  const subcategoryIds = new Set(category.subcategories.map((subcategory) => subcategory.id));
  if (subcategoryIds.has(restoredSubcategory.id)) {
    restoredSubcategory.id = nextToolLibraryId(restoredSubcategory.name, subcategoryIds, 'sub');
  }

  draftCategories.value = reindexCategories(
    draftCategories.value.map((item) => {
      if (item.id !== entry.categoryId) {
        return item;
      }
      const nextSubcategories = [...item.subcategories];
      nextSubcategories.splice(Math.min(entry.index, nextSubcategories.length), 0, restoredSubcategory);
      return {
        ...item,
        subcategories: nextSubcategories,
      };
    }),
  );
  lastRemovedEntry.value = null;
  setManagerNotice('success', `Restored subcategory "${restoredSubcategory.name}".`);
}

function dismissLastRemoved(): void {
  lastRemovedEntry.value = null;
}

function restoreCategoryEntry(
  entry: Extract<LastRemovedEntry, { kind: 'category' }> | Extract<LastRemovedEntry, { kind: 'category-batch' }>['categories'][number],
  categories: ToolLibraryCategory[],
): {
  categories: ToolLibraryCategory[];
  restoredNames: string[];
  quickAssignCategoryId: string;
  bulkEditorOpenId: string;
} {
  const restoredCategory = cloneCategories([entry.category])[0];
  restoredCategory.name = makeUniqueRestoredLabel(
    restoredCategory.name,
    categories.map((category) => category.name),
  );
  const categoryIds = new Set(categories.map((category) => category.id));
  if (categoryIds.has(restoredCategory.id)) {
    restoredCategory.id = nextToolLibraryId(restoredCategory.name, categoryIds, 'cat');
  }

  const nextCategories = [...categories];
  nextCategories.splice(Math.min(entry.index, nextCategories.length), 0, restoredCategory);
  return {
    categories: nextCategories,
    restoredNames: [restoredCategory.name],
    quickAssignCategoryId: entry.quickAssignSelected ? restoredCategory.id : '',
    bulkEditorOpenId: entry.bulkEditorOpen ? restoredCategory.id : '',
  };
}

function selectContextOption(optionId: CategoryContextOption['id']): void {
  const option = contextOptions.value.find((item) => item.id === optionId);
  if (!option || option.disabled) {
    return;
  }
  contextSourceId.value = option.id;
  contextCategoryName.value = option.categoryName;
}

function startCategoryDrag(categoryId: string): void {
  draggedCategoryId.value = categoryId;
}

function dropCategory(targetCategoryId: string): void {
  if (!draggedCategoryId.value || draggedCategoryId.value === targetCategoryId) {
    return;
  }
  draftCategories.value = reindexCategories(
    moveItemById(draftCategories.value, draggedCategoryId.value, targetCategoryId),
  );
  draggedCategoryId.value = '';
}

function clearCategoryDrag(): void {
  draggedCategoryId.value = '';
}

function startSubcategoryDrag(categoryId: string, subcategoryId: string): void {
  draggedSubcategory.value = { categoryId, subcategoryId };
}

function dropSubcategory(categoryId: string, targetSubcategoryId: string): void {
  if (
    !draggedSubcategory.value.categoryId ||
    draggedSubcategory.value.categoryId !== categoryId ||
    draggedSubcategory.value.subcategoryId === targetSubcategoryId
  ) {
    return;
  }

  draftCategories.value = reindexCategories(
    draftCategories.value.map((category) => (
      category.id === categoryId
        ? {
            ...category,
            subcategories: moveItemById(
              category.subcategories,
              draggedSubcategory.value.subcategoryId,
              targetSubcategoryId,
            ),
          }
        : category
    )),
  );
  clearSubcategoryDrag();
}

function clearSubcategoryDrag(): void {
  draggedSubcategory.value = { categoryId: '', subcategoryId: '' };
}

function previewLabel(action: 'create' | 'merge' | 'skip'): string {
  if (action === 'create') {
    return 'Create';
  }
  if (action === 'merge') {
    return 'Merge';
  }
  return 'Skip';
}

function previewPillClass(action: 'create' | 'merge' | 'skip'): string {
  if (action === 'create') {
    return 'preview-pill-create';
  }
  if (action === 'merge') {
    return 'preview-pill-merge';
  }
  return 'preview-pill-skip';
}

function submit(): void {
  draftCategories.value = reindexCategories(
    draftCategories.value.map((category) => ({
      ...category,
      name: normalizeCategoryLabel(category.name),
      subcategories: category.subcategories.map((subcategory) => ({
        ...subcategory,
        name: normalizeCategoryLabel(subcategory.name),
      })),
    })),
  );
  lastRemovedEntry.value = null;

  emit('save', {
    categories: cloneCategories(draftCategories.value),
    quickAssignCategoryId: quickAssignCategoryId.value,
  });
}
</script>

<style scoped>
.manager-input,
.manager-textarea,
.manager-select {
  width: 100%;
  border-radius: 1rem;
  border: 1px solid var(--border-light);
  background: rgba(255, 255, 255, 0.72);
  padding: 0.8rem 0.95rem;
  color: var(--text-primary);
}

.manager-textarea {
  resize: vertical;
}

.manager-action,
.manager-primary {
  border-radius: 1rem;
  border: 1px solid var(--border-light);
  padding: 0.75rem 0.95rem;
  font-size: 0.95rem;
  transition: background-color 160ms ease, transform 160ms ease;
}

.manager-action {
  background: rgba(255, 255, 255, 0.72);
  color: var(--text-secondary);
  text-align: left;
}

.manager-action:hover:not(:disabled) {
  background: white;
}

.manager-primary {
  background: rgb(15, 23, 42);
  border-color: rgb(15, 23, 42);
  color: white;
}

.manager-notice {
  border-color: transparent;
}

.manager-notice-success {
  border-color: rgba(34, 197, 94, 0.2);
  background: rgba(34, 197, 94, 0.08);
  color: rgb(21, 128, 61);
}

.manager-notice-error {
  border-color: rgba(248, 113, 113, 0.25);
  background: rgba(254, 242, 242, 1);
  color: rgb(185, 28, 28);
}

.manager-notice-info {
  border-color: rgba(59, 130, 246, 0.18);
  background: rgba(59, 130, 246, 0.08);
  color: rgb(30, 64, 175);
}

.manager-primary:disabled,
.manager-action:disabled,
.context-option:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.manager-delete {
  border-radius: 1rem;
  border: 1px solid rgba(248, 113, 113, 0.25);
  background: rgba(254, 242, 242, 1);
  padding: 0.75rem 0.95rem;
  font-size: 0.95rem;
  color: rgb(220, 38, 38);
}

.manager-delete:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.mode-chip,
.selection-chip {
  border-radius: 9999px;
  border: 1px solid var(--border-light);
  background: rgba(255, 255, 255, 0.72);
  padding: 0.5rem 0.9rem;
  font-size: 0.8rem;
  color: var(--text-secondary);
  transition: background-color 160ms ease, color 160ms ease, border-color 160ms ease;
}

.mode-chip-active,
.selection-chip-active {
  background: rgb(15, 23, 42);
  border-color: rgb(15, 23, 42);
  color: white;
}

.context-option {
  width: 100%;
  border-radius: 1rem;
  border: 1px solid var(--border-light);
  background: rgba(255, 255, 255, 0.72);
  padding: 0.85rem 0.95rem;
  text-align: left;
}

.context-option-active {
  border-color: rgba(15, 23, 42, 0.25);
  background: rgba(15, 23, 42, 0.06);
}

.category-multiselect-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  border-radius: 1rem;
  border: 1px solid var(--border-light);
  background: rgba(255, 255, 255, 0.72);
  padding: 0.8rem 0.9rem;
  cursor: pointer;
  transition: background-color 160ms ease, border-color 160ms ease;
}

.category-multiselect-row:hover {
  background: white;
}

.category-select-toggle {
  height: 1rem;
  width: 1rem;
  flex-shrink: 0;
  border-radius: 0.25rem;
  border: 1px solid var(--border-light);
  accent-color: rgb(15, 23, 42);
}

.drag-handle {
  display: inline-flex;
  min-height: 2.75rem;
  align-items: center;
  justify-content: center;
  border-radius: 1rem;
  border: 1px dashed var(--border-light);
  padding: 0 0.8rem;
  color: var(--text-tertiary);
  cursor: grab;
  user-select: none;
}

.preview-pill {
  border-radius: 9999px;
  padding: 0.2rem 0.65rem;
  font-size: 0.75rem;
  font-weight: 600;
}

.preview-pill-create {
  background: rgba(34, 197, 94, 0.12);
  color: rgb(21, 128, 61);
}

.preview-pill-merge {
  background: rgba(59, 130, 246, 0.12);
  color: rgb(29, 78, 216);
}

.preview-pill-skip {
  background: rgba(148, 163, 184, 0.15);
  color: rgb(71, 85, 105);
}

.dark .manager-input,
.dark .manager-textarea,
.dark .manager-select,
.dark .manager-action,
.dark .context-option,
.dark .category-multiselect-row,
.dark .mode-chip,
.dark .selection-chip {
  background: rgba(255, 255, 255, 0.04);
}

.dark .category-multiselect-row:hover {
  background: rgba(255, 255, 255, 0.08);
}

.dark .manager-delete {
  background: rgba(248, 113, 113, 0.1);
  border-color: rgba(248, 113, 113, 0.2);
  color: rgb(252, 165, 165);
}

.dark .manager-notice-success {
  border-color: rgba(34, 197, 94, 0.25);
  background: rgba(34, 197, 94, 0.12);
  color: rgb(187, 247, 208);
}

.dark .manager-notice-error {
  border-color: rgba(248, 113, 113, 0.2);
  background: rgba(248, 113, 113, 0.1);
  color: rgb(252, 165, 165);
}

.dark .manager-notice-info {
  border-color: rgba(96, 165, 250, 0.22);
  background: rgba(59, 130, 246, 0.12);
  color: rgb(191, 219, 254);
}

.dark .manager-primary {
  background: white;
  border-color: white;
  color: rgb(15, 23, 42);
}
</style>
