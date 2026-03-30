<template>
  <div class="flex h-full w-full flex-col overflow-hidden bg-[var(--background-gray-main)]">
    <header class="relative overflow-hidden border-b border-white/10">
      <div class="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.25),_transparent_30%),radial-gradient(circle_at_78%_18%,_rgba(59,130,246,0.22),_transparent_34%),linear-gradient(135deg,_#111827_0%,_#0f172a_48%,_#1f2937_100%)]"></div>
      <div class="relative px-5 py-5 md:px-6">
        <div class="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div class="space-y-3">
            <div class="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-3 py-1 text-[11px] font-medium uppercase tracking-[0.18em] text-white/75 backdrop-blur-sm">
              Discipline-First Library
            </div>
            <div>
              <h1 class="text-3xl font-semibold text-white">Tool Cartography</h1>
              <p class="mt-2 max-w-3xl text-sm leading-7 text-white/75">
                Browse science and external tools by discipline first, then narrow within each slice by function group while keeping personal categories as a separate overlay.
              </p>
            </div>
          </div>

          <div class="w-full max-w-xl rounded-[28px] border border-white/10 bg-white/10 p-3 backdrop-blur-xl">
            <div class="flex flex-wrap items-center gap-2">
              <button
                v-for="tab in tabs"
                :key="tab.id"
                type="button"
                class="inline-flex items-center gap-2 rounded-2xl px-3 py-2 text-sm font-medium transition"
                :class="activeTab === tab.id ? 'bg-white text-slate-900 shadow-lg shadow-black/10' : 'bg-white/5 text-white/80 hover:bg-white/10 hover:text-white'"
                @click="activeTab = tab.id"
              >
                <span>{{ tab.label }}</span>
                <span class="rounded-full px-2 py-0.5 text-[11px]" :class="activeTab === tab.id ? 'bg-slate-900/10 text-slate-700' : 'bg-white/10 text-white/80'">
                  {{ tab.count }}
                </span>
              </button>
            </div>

            <div class="mt-3">
              <input
                v-model="searchQuery"
                type="text"
                class="w-full rounded-2xl border border-white/10 bg-white/10 px-4 py-3 text-sm text-white placeholder:text-white/40 focus:border-white/20 focus:bg-white/15 focus:outline-none"
                :placeholder="`Search ${activeTab === 'science' ? 'science' : 'external'} tools`"
              >
            </div>
          </div>
        </div>
      </div>
    </header>

    <div class="min-h-0 flex-1 p-3 md:p-4">
      <div class="flex h-full min-h-0 overflow-hidden rounded-[32px] border border-[var(--border-light)] bg-white/75 shadow-xl shadow-black/5 dark:bg-[#121212]">
        <ToolLibrarySidebar
          :region-label="currentRegionLabel"
          :description="currentDescription"
          :browse-source="currentBrowseSource"
          :system-options="disciplineOptions"
          :custom-category-options="customCategoryOptions"
          :custom-subcategory-options="customSubcategoryOptions"
          :custom-category-assignment-totals="customCategoryAssignmentTotals"
          :active-discipline="filters[activeTab].system.discipline"
          :active-custom-category-id="filters[activeTab].custom.categoryId"
          :active-custom-subcategory-id="filters[activeTab].custom.subcategoryId"
          :total-count="activeRegionTotal"
          :uncategorized-count="uncategorizedCount"
          :category-summary="categorySummary"
          @manage-categories="manageCategoriesOpen = true"
          @select-browse-source="setBrowseSource(activeTab, $event)"
          @select-custom-category="setCustomCategory(activeTab, $event)"
          @select-custom-subcategory="setCustomSubcategory(activeTab, $event)"
          @select-discipline="setDiscipline(activeTab, $event)"
          @delete-custom-categories="handleDeleteCustomCategories"
        />

        <ToolLibraryGrid
          :title="gridTitle"
          :subtitle="gridSubtitle"
          :loading="currentLoading"
          :cards="currentCards"
          :selected-names="currentSelection"
          :browse-source="currentBrowseSource"
          :active-slice-label="activeSliceLabel"
          :active-subslice-label="activeSubsliceLabel"
          :system-function-group-options="systemFunctionGroupOptions"
          :active-function-group="filters[activeTab].system.functionGroup"
          :custom-category-options="customCategoryOptions"
          :active-custom-category-id="filters[activeTab].custom.categoryId"
          :custom-subcategory-options="customSubcategoryOptions"
          :active-custom-subcategory-id="filters[activeTab].custom.subcategoryId"
          :uncategorized-count="uncategorizedCount"
          @assign-card="handleAssignCard"
          @assign-selected="handleAssignSelection"
          @create-category-selected="handleCreateCategoryFromSelection"
          @clear-card="clearAssignments($event.toolKind, [$event.name])"
          @clear-selected="clearAssignments(activeTab, [...currentSelection])"
          @delete-card="deleteExternalTool($event)"
          @manage-categories="manageCategoriesOpen = true"
          @open-card="openTool"
          @refresh="refreshCurrentTab"
          @reset-filters="resetFilters(activeTab)"
          @set-custom-category="setCustomCategory(activeTab, $event)"
          @set-custom-subcategory="setCustomSubcategory(activeTab, $event)"
          @set-function-group="setFunctionGroup(activeTab, $event)"
          @toggle-block="toggleExternalToolBlock($event)"
          @toggle-select="toggleToolSelection(activeTab, $event)"
          @toggle-visible="toggleVisibleSelection(activeTab)"
        />
      </div>
    </div>

    <Dialog :open="manageCategoriesOpen" @update:open="manageCategoriesOpen = $event">
      <DialogContent class="w-[min(1180px,96vw)] max-h-[88vh] overflow-hidden border border-[var(--border-light)] bg-[var(--background-gray-main)] p-0">
        <ToolLibraryCategoryManager
          :categories="preferences.custom_categories"
          :assignment-stats="categoryAssignmentStats"
          :discipline-presets="disciplineOptions"
          :function-group-presets="allFunctionGroupPresets"
          :current-slice-label="activeDiscipline?.labelZh || ''"
          :current-slice-children="systemFunctionGroupOptions"
          :selected-tool-count="currentSelectedCount"
          :selected-tool-names="currentSelection"
          :visible-tool-names="currentCards.map((card) => card.name)"
          :active-function-group-label="activeSystemFunctionGroupLabel"
          :active-search-query="searchQuery"
          :region-label="currentRegionLabel"
          @close="manageCategoriesOpen = false"
          @save="handleSaveCategories"
        />
      </DialogContent>
    </Dialog>

    <Dialog :open="assignmentOpen" @update:open="handleAssignmentDialogOpenChange">
      <DialogContent class="w-[min(680px,94vw)] border border-[var(--border-light)] bg-[var(--background-gray-main)] p-0">
        <div class="px-5 py-5">
          <ToolLibraryAssignmentDialog
            :categories="preferences.custom_categories"
            :kind="assignmentTarget.kind"
            :tool-names="assignmentTarget.toolNames"
            :initial-category-id="assignmentTarget.categoryId"
            :initial-subcategory-id="assignmentTarget.subcategoryId"
            :initial-create-open="assignmentCreateMode"
            :create-categories="handleInlineCreateCategories"
            @cancel="handleCloseAssignment"
            @submit="handleSubmitAssignment"
          />
        </div>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import type { ToolLibraryCategory } from '../api/toolLibrary';
import Dialog from '../components/ui/dialog/Dialog.vue';
import DialogContent from '../components/ui/dialog/DialogContent.vue';
import { UNCATEGORIZED_CATEGORY_ID } from '../components/toolLibrary/browseHelpers';
import ToolLibraryAssignmentDialog from '../components/toolLibrary/ToolLibraryAssignmentDialog.vue';
import ToolLibraryCategoryManager from '../components/toolLibrary/ToolLibraryCategoryManager.vue';
import ToolLibraryGrid from '../components/toolLibrary/ToolLibraryGrid.vue';
import ToolLibrarySidebar from '../components/toolLibrary/ToolLibrarySidebar.vue';
import { resolveCategorySelection } from '../components/toolLibrary/categoryBuilder';
import type { TaxonomyOption, ToolCard } from '../components/toolLibrary/types';
import { useToolLibrary } from '../components/toolLibrary/useToolLibrary';

const {
  activeTab,
  assignmentOpen,
  assignmentTarget,
  activeCustomCategory,
  activeCustomSubcategory,
  activeDiscipline,
  categoryAssignmentStats,
  categorySummary,
  currentBrowseSource,
  currentCards,
  currentDescription,
  currentLoading,
  currentRegionLabel,
  currentSelectedCount,
  currentSelection,
  customCategoryOptions,
  customSubcategoryOptions,
  disciplineOptions,
  externalTools,
  filters,
  loadAll,
  manageCategoriesOpen,
  openCardAssignment,
  openSelectedAssignment,
  openTool,
  preferences,
  refreshCurrentTab,
  resetFilters,
  saveCategories,
  searchQuery,
  scienceTools,
  setBrowseSource,
  setCustomCategory,
  setCustomSubcategory,
  setDiscipline,
  setFunctionGroup,
  submitAssignment,
  systemFunctionGroupOptions,
  toggleExternalToolBlock,
  toggleToolSelection,
  toggleVisibleSelection,
  clearAssignments,
  deleteExternalTool,
  uncategorizedCount,
} = useToolLibrary();

const tabs = computed(() => [
  { id: 'science' as const, label: 'Science', count: scienceTools.value.length },
  { id: 'external' as const, label: 'External', count: externalTools.value.length },
]);

const assignmentCreateMode = ref(false);

const activeRegionTotal = computed(() => activeTab.value === 'science' ? scienceTools.value.length : externalTools.value.length);

const gridTitle = computed(() => {
  if (currentBrowseSource.value === 'custom') {
    const categoryId = filters[activeTab.value].custom.categoryId;
    if (!categoryId) {
      return `All ${currentRegionLabel.value} Tools`;
    }
    if (categoryId === UNCATEGORIZED_CATEGORY_ID) {
      return `Uncategorized ${currentRegionLabel.value} Tools`;
    }
    if (activeCustomSubcategory.value?.labelZh) {
      return `${activeCustomCategory.value?.labelZh || 'My Category'} | ${activeCustomSubcategory.value.labelZh}`;
    }
    return activeCustomCategory.value?.labelZh || `All ${currentRegionLabel.value} Tools`;
  }

  if (!filters[activeTab.value].system.discipline) {
    return `All ${currentRegionLabel.value} Tools`;
  }
  const discipline = activeDiscipline.value;
  if (!discipline) {
    return `All ${currentRegionLabel.value} Tools`;
  }
  if (activeSystemFunctionGroupLabel.value) {
    return `${discipline.labelZh} | ${activeSystemFunctionGroupLabel.value}`;
  }
  return discipline.labelZh;
});

const gridSubtitle = computed(() => {
  if (currentBrowseSource.value === 'custom') {
    const categoryId = filters[activeTab.value].custom.categoryId;
    if (!categoryId) {
      return 'Browse the full region through your own category system, then narrow with your category chips whenever you want.';
    }
    if (categoryId === UNCATEGORIZED_CATEGORY_ID) {
      return 'These tools are still waiting for a custom assignment, so this view helps you quickly tidy up your personal organization.';
    }
    if (!filters[activeTab.value].custom.subcategoryId) {
      return customSubcategoryOptions.value.length
        ? 'Subcategory chips narrow this custom category without leaving your personal browse track.'
        : 'This custom category currently has no subcategories, so every assigned tool stays in one bucket.';
    }
    return 'Showing the tools assigned to this exact custom category slice.';
  }

  if (!filters[activeTab.value].system.discipline) {
    return 'Browse every tool by the system taxonomy, or narrow the full region immediately with the function-group chips.';
  }
  if (!systemFunctionGroupOptions.value.length) {
    return 'This discipline does not need a secondary function-group slice right now.';
  }
  return 'Function-group chips narrow this discipline slice without changing the top-level browse axis.';
});

const activeSystemDisciplineLabel = computed(() =>
  activeDiscipline.value?.labelZh || 'All Disciplines'
);

const activeSystemFunctionGroupLabel = computed(() =>
  systemFunctionGroupOptions.value.find((option) => option.id === filters[activeTab.value].system.functionGroup)?.labelZh || ''
);

const activeCustomCategoryLabel = computed(() => {
  const categoryId = filters[activeTab.value].custom.categoryId;
  if (categoryId === UNCATEGORIZED_CATEGORY_ID) {
    return 'Uncategorized';
  }
  return activeCustomCategory.value?.labelZh || 'All Categories';
});

const activeSliceLabel = computed(() =>
  currentBrowseSource.value === 'custom' ? activeCustomCategoryLabel.value : activeSystemDisciplineLabel.value
);

const activeSubsliceLabel = computed(() =>
  currentBrowseSource.value === 'custom'
    ? activeCustomSubcategory.value?.labelZh || ''
    : activeSystemFunctionGroupLabel.value
);

const customCategoryAssignmentTotals = computed(() => {
  const totals = new Map<string, number>();
  for (const [categoryId, stats] of categoryAssignmentStats.value.entries()) {
    totals.set(categoryId, stats.total);
  }
  return totals;
});

const allFunctionGroupPresets = computed(() => {
  const seen = new Map<string, TaxonomyOption>();
  for (const kind of ['science', 'external'] as const) {
    for (const card of kind === 'science' ? currentAllScienceCards.value : currentAllExternalCards.value) {
      if (!seen.has(card.functionGroup)) {
        seen.set(card.functionGroup, {
          id: card.functionGroup,
          label: card.functionGroup,
          labelZh: card.functionGroupLabel,
          count: 0,
        });
      }
      const entry = seen.get(card.functionGroup)!;
      entry.count += 1;
    }
  }
  return Array.from(seen.values()).sort((left, right) => left.labelZh.localeCompare(right.labelZh, 'zh-Hans-CN'));
});

const currentAllScienceCards = computed(() => scienceTools.value.map((tool) => ({
  functionGroup: tool.function_group || tool.system_group || 'analysis_workflow',
  functionGroupLabel: tool.function_group_zh || tool.system_group_zh || tool.function_group || tool.system_group || 'analysis_workflow',
})));
const currentAllExternalCards = computed(() => externalTools.value.map((tool) => ({
  functionGroup: tool.function_group || tool.system_group || 'analysis_workflow',
  functionGroupLabel: tool.function_group_zh || tool.system_group_zh || tool.function_group || tool.system_group || 'analysis_workflow',
})));

function handleAssignCard(card: ToolCard): void {
  assignmentCreateMode.value = false;
  openCardAssignment(card);
}

function handleAssignSelection(): void {
  assignmentCreateMode.value = false;
  openSelectedAssignment();
}

function handleCreateCategoryFromSelection(): void {
  assignmentCreateMode.value = true;
  openSelectedAssignment();
}

function handleCloseAssignment(): void {
  assignmentCreateMode.value = false;
  assignmentOpen.value = false;
}

function handleAssignmentDialogOpenChange(nextOpen: boolean): void {
  assignmentOpen.value = nextOpen;
  if (!nextOpen) {
    assignmentCreateMode.value = false;
  }
}

function handleSubmitAssignment(payload: { categoryId: string; subcategoryId: string }): void {
  assignmentCreateMode.value = false;
  submitAssignment({
    kind: assignmentTarget.value.kind,
    toolNames: assignmentTarget.value.toolNames,
    categoryId: payload.categoryId,
    subcategoryId: payload.subcategoryId,
  });
}

function handleSaveCategories(payload: { categories: ToolLibraryCategory[]; quickAssignCategoryId: string }): void {
  const quickAssign = payload.quickAssignCategoryId && currentSelection.value.length
    ? {
        kind: activeTab.value,
        toolNames: [...currentSelection.value],
        categoryId: payload.quickAssignCategoryId,
        subcategoryId: '',
      }
    : undefined;
  saveCategories(payload.categories, quickAssign);
}

function handleDeleteCustomCategories(categoryIds: string[]): void {
  const uniqueIds = Array.from(new Set(categoryIds)).filter((categoryId) =>
    preferences.value.custom_categories.some((category) => category.id === categoryId),
  );
  if (!uniqueIds.length) {
    return;
  }

  const categoryNames = preferences.value.custom_categories
    .filter((category) => uniqueIds.includes(category.id))
    .map((category) => category.name);
  const affectedAssignments = uniqueIds.reduce(
    (total, categoryId) => total + (categoryAssignmentStats.value.get(categoryId)?.total || 0),
    0,
  );
  const categoryLabel = uniqueIds.length === 1
    ? `Delete "${categoryNames[0]}"?`
    : `Delete ${uniqueIds.length} categories?`;
  const assignmentLabel = `${affectedAssignments} assignment${affectedAssignments === 1 ? '' : 's'} will be cleared.`;
  const previewLabel = categoryNames.slice(0, 3).join(', ');
  const extraLabel = categoryNames.length > 3 ? ` and ${categoryNames.length - 3} more` : '';
  const confirmed = window.confirm(`${categoryLabel}\n\n${assignmentLabel}\n${previewLabel}${extraLabel}`);
  if (!confirmed) {
    return;
  }

  saveCategories(
    preferences.value.custom_categories.filter((category) => !uniqueIds.includes(category.id)),
  );
}

async function handleInlineCreateCategories(payload: {
  categories: ToolLibraryCategory[];
  categoryName: string;
  subcategoryName: string;
}): Promise<{ categoryId: string; subcategoryId: string }> {
  const saved = await saveCategories(payload.categories);
  if (!saved) {
    throw new Error('Failed to save the inline category draft.');
  }

  const selection = resolveCategorySelection(
    saved.custom_categories,
    payload.categoryName,
    payload.subcategoryName,
  );

  if (!selection.categoryId) {
    throw new Error('The new category could not be found after saving.');
  }

  return selection;
}

onMounted(loadAll);
</script>
