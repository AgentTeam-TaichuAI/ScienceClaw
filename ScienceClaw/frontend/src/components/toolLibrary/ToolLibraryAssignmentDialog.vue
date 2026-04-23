<template>
  <div class="space-y-5">
    <div>
      <div class="text-[11px] uppercase tracking-[0.18em] text-[var(--text-tertiary)]">Assignment</div>
      <h3 class="mt-2 text-lg font-semibold text-[var(--text-primary)]">Assign {{ toolNames.length }} {{ kind }} tool<span v-if="toolNames.length !== 1">s</span></h3>
      <p class="mt-1 text-sm text-[var(--text-secondary)]">Personal categories stay shared as a tree, while assignments remain region-local.</p>
    </div>

    <div
      v-if="showSelectionFirstHint"
      class="rounded-[20px] border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-700 dark:border-sky-400/20 dark:bg-sky-400/10 dark:text-sky-200"
    >
      Create the category first in this dialog, then save the assignment to place the selected tools into it immediately.
    </div>

    <div class="space-y-4">
      <div>
        <label class="mb-2 block text-sm font-medium text-[var(--text-primary)]">Category</label>
        <select v-model="draftCategoryId" class="dialog-select">
          <option value="">Select a category</option>
          <option v-for="category in categorySnapshot" :key="category.id" :value="category.id">{{ category.name }}</option>
        </select>
      </div>

      <div v-if="availableSubcategories.length">
        <label class="mb-2 block text-sm font-medium text-[var(--text-primary)]">Subcategory</label>
        <select v-model="draftSubcategoryId" class="dialog-select">
          <option value="">No subcategory</option>
          <option v-for="subcategory in availableSubcategories" :key="subcategory.id" :value="subcategory.id">{{ subcategory.name }}</option>
        </select>
      </div>

      <div class="rounded-[24px] border border-[var(--border-light)] bg-[var(--background-gray-main)] px-4 py-4 text-sm text-[var(--text-secondary)] dark:bg-white/5">
        <div class="flex items-center justify-between gap-3">
          <div class="font-medium text-[var(--text-primary)]">Inline category creation</div>
          <button type="button" class="inline-toggle" @click="createOpen = !createOpen">
            {{ createOpen ? 'Hide Creator' : 'Create New Category' }}
          </button>
        </div>

        <div v-if="createOpen" class="mt-4 space-y-4">
          <div>
            <label class="mb-2 block text-sm font-medium text-[var(--text-primary)]">Category name</label>
            <input v-model="inlineCategoryName" type="text" class="dialog-input" placeholder="Examples: Reading Queue, Project Notes">
          </div>
          <div>
            <label class="mb-2 block text-sm font-medium text-[var(--text-primary)]">Optional subcategories</label>
            <textarea
              v-model="inlineSubcategoryText"
              class="dialog-textarea"
              rows="4"
              placeholder="One per line. You can also paste Category > Subcategory and only the subcategory part will be used."
            />
          </div>

          <div class="rounded-[18px] border border-[var(--border-light)] bg-white/70 px-3 py-3 text-xs text-[var(--text-secondary)] dark:bg-[#161616]">
            <div class="font-medium text-[var(--text-primary)]">Preview</div>
            <div class="mt-2">
              {{ inlinePreview.summary.categoriesCreated }} create / {{ inlinePreview.summary.categoriesMerged }} merge / {{ inlinePreview.summary.categoriesSkipped }} skip
            </div>
            <div>{{ inlinePreview.summary.subcategoriesCreated + inlinePreview.summary.subcategoriesMerged }} subcategories will be available after save</div>
          </div>

          <div v-if="createError" class="rounded-[18px] border border-red-200 bg-red-50 px-3 py-3 text-sm text-red-700 dark:border-red-400/20 dark:bg-red-400/10 dark:text-red-300">
            {{ createError }}
          </div>

          <button type="button" class="inline-create-button" :disabled="!inlineCreatorHasEffect || createPending" @click="createInlineCategory">
            {{ createPending ? 'Creating...' : 'Create And Select' }}
          </button>
        </div>
      </div>

      <div class="rounded-[24px] border border-[var(--border-light)] bg-[var(--background-gray-main)] px-4 py-4 text-sm text-[var(--text-secondary)] dark:bg-white/5">
        <div class="font-medium text-[var(--text-primary)]">Selected tools</div>
        <div class="mt-2 flex flex-wrap gap-2">
          <span
            v-for="toolName in toolNames.slice(0, 8)"
            :key="toolName"
            class="rounded-full border border-[var(--border-light)] bg-white/70 px-2.5 py-1 text-[11px] dark:bg-white/10"
          >
            {{ toolName }}
          </span>
          <span v-if="toolNames.length > 8" class="rounded-full bg-black/5 px-2.5 py-1 text-[11px] dark:bg-white/10">+{{ toolNames.length - 8 }} more</span>
        </div>
      </div>
    </div>

    <div class="flex justify-end gap-2 border-t border-[var(--border-light)] pt-4">
      <button
        type="button"
        class="rounded-2xl border border-[var(--border-light)] bg-white/70 px-4 py-2 text-sm text-[var(--text-secondary)] transition hover:bg-white dark:bg-white/5 dark:hover:bg-white/10"
        @click="$emit('cancel')"
      >
        Cancel
      </button>
      <button
        type="button"
        class="rounded-2xl bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100"
        :disabled="!draftCategoryId"
        @click="submit"
      >
        Save Assignment
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import type { ToolKind, ToolLibraryCategory } from '../../api/toolLibrary';
import { applyCategorySeeds, buildSingleCategorySeed } from './categoryBuilder';

const props = defineProps<{
  categories: ToolLibraryCategory[];
  kind: ToolKind;
  toolNames: string[];
  initialCategoryId: string;
  initialSubcategoryId: string;
  initialCreateOpen?: boolean;
  createCategories: (payload: {
    categories: ToolLibraryCategory[];
    categoryName: string;
    subcategoryName: string;
  }) => Promise<{ categoryId: string; subcategoryId: string }>;
}>();

const emit = defineEmits<{
  (event: 'cancel'): void;
  (event: 'submit', payload: { categoryId: string; subcategoryId: string }): void;
}>();

const draftCategoryId = ref(props.initialCategoryId || '');
const draftSubcategoryId = ref(props.initialSubcategoryId || '');
const categorySnapshot = ref<ToolLibraryCategory[]>(props.categories);

const createOpen = ref(Boolean(props.initialCreateOpen));
const createPending = ref(false);
const createError = ref('');
const inlineCategoryName = ref('');
const inlineSubcategoryText = ref('');

watch(
  () => props.categories,
  (value) => {
    categorySnapshot.value = value;
  },
  { immediate: true, deep: true },
);

watch(
  () => [props.initialCategoryId, props.initialSubcategoryId, props.initialCreateOpen, props.toolNames.join('|')],
  () => {
    draftCategoryId.value = props.initialCategoryId || '';
    draftSubcategoryId.value = props.initialSubcategoryId || '';
    createOpen.value = Boolean(props.initialCreateOpen);
    createError.value = '';
  },
);

const availableSubcategories = computed(() =>
  categorySnapshot.value.find((category) => category.id === draftCategoryId.value)?.subcategories || []
);

watch(draftCategoryId, () => {
  if (!availableSubcategories.value.some((subcategory) => subcategory.id === draftSubcategoryId.value)) {
    draftSubcategoryId.value = '';
  }
});

const inlineSeed = computed(() => buildSingleCategorySeed(inlineCategoryName.value, inlineSubcategoryText.value));
const inlinePreview = computed(() => applyCategorySeeds(categorySnapshot.value, inlineSeed.value ? [inlineSeed.value] : []));
const showSelectionFirstHint = computed(() =>
  Boolean(props.initialCreateOpen) && props.toolNames.length > 0
);
const inlineCreatorHasEffect = computed(() => {
  const summary = inlinePreview.value.summary;
  return (
    Boolean(inlineSeed.value) &&
    (
      summary.categoriesCreated > 0 ||
      summary.categoriesMerged > 0 ||
      summary.subcategoriesCreated > 0 ||
      summary.subcategoriesMerged > 0
    )
  );
});

async function createInlineCategory(): Promise<void> {
  if (!inlineSeed.value || !inlineCreatorHasEffect.value || createPending.value) {
    return;
  }

  createPending.value = true;
  createError.value = '';

  try {
    const preferredSubcategoryName = inlineSeed.value.subcategories.length === 1 ? inlineSeed.value.subcategories[0] : '';
    const selection = await props.createCategories({
      categories: inlinePreview.value.categories,
      categoryName: inlineSeed.value.name,
      subcategoryName: preferredSubcategoryName,
    });

    categorySnapshot.value = inlinePreview.value.categories;
    draftCategoryId.value = selection.categoryId;
    draftSubcategoryId.value = selection.subcategoryId;
    inlineCategoryName.value = '';
    inlineSubcategoryText.value = '';
    createOpen.value = false;
  } catch (error: any) {
    createError.value = error?.message || 'Failed to create a category from the inline builder.';
  } finally {
    createPending.value = false;
  }
}

function submit(): void {
  if (!draftCategoryId.value) {
    return;
  }
  emit('submit', {
    categoryId: draftCategoryId.value,
    subcategoryId: draftSubcategoryId.value,
  });
}
</script>

<style scoped>
.dialog-select,
.dialog-input,
.dialog-textarea {
  width: 100%;
  border-radius: 1rem;
  border: 1px solid var(--border-light);
  background: rgba(255, 255, 255, 0.72);
  padding: 0.8rem 0.95rem;
  color: var(--text-primary);
}

.dialog-textarea {
  resize: vertical;
}

.inline-toggle,
.inline-create-button {
  border-radius: 1rem;
  border: 1px solid var(--border-light);
  padding: 0.7rem 0.95rem;
  font-size: 0.9rem;
  transition: background-color 160ms ease;
}

.inline-toggle {
  background: rgba(255, 255, 255, 0.72);
  color: var(--text-secondary);
}

.inline-create-button {
  background: rgb(15, 23, 42);
  border-color: rgb(15, 23, 42);
  color: white;
}

.inline-create-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.dark .dialog-select,
.dark .dialog-input,
.dark .dialog-textarea,
.dark .inline-toggle {
  background: rgba(255, 255, 255, 0.04);
}

.dark .inline-create-button {
  background: white;
  border-color: white;
  color: rgb(15, 23, 42);
}
</style>
