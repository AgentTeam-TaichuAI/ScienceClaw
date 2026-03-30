import { computed, reactive, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { getTools, blockTool, deleteTool } from '../../api/agent';
import { listTUTools, type TUTool } from '../../api/tooluniverse';
import {
  batchAssignToolLibrary,
  clearToolLibraryAssignments,
  getToolLibraryPreferences,
  updateToolLibraryPreferences,
  type ToolKind,
  type ToolLibraryCategory,
  type ToolLibraryPreferences,
} from '../../api/toolLibrary';
import type { ExternalToolItem } from '../../types/response';
import { showErrorToast, showSuccessToast } from '../../utils/toast';
import {
  buildCustomBrowseState,
  createDefaultToolLibraryFilterState,
  filterCardsForBrowse,
  resolveBrowseSourceDefault,
  UNCATEGORIZED_CATEGORY_ID,
} from './browseHelpers';
import type {
  AssignmentTarget,
  BrowseSource,
  TaxonomyOption,
  ToolCard,
  ToolLibraryFilterState,
} from './types';

const BROWSE_SOURCE_STORAGE_KEY = 'scienceclaw-tool-library-browse-sources';

type CategoryAssignmentStat = {
  total: number;
  science: number;
  external: number;
};

function buildAssignmentKey(kind: ToolKind, toolName: string): string {
  return `${kind}::${toolName}`;
}

function getErrorMessage(error: any, fallback: string): string {
  return error?.details?.detail || error?.message || fallback;
}

function readStoredBrowseSources(): Partial<Record<ToolKind, BrowseSource>> {
  try {
    const raw = localStorage.getItem(BROWSE_SOURCE_STORAGE_KEY);
    if (!raw) {
      return {};
    }

    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') {
      return {};
    }

    const result: Partial<Record<ToolKind, BrowseSource>> = {};
    for (const kind of ['science', 'external'] as const) {
      if (parsed[kind] === 'system' || parsed[kind] === 'custom') {
        result[kind] = parsed[kind];
      }
    }
    return result;
  } catch (error) {
    console.error('Failed to read tool-library browse source from localStorage:', error);
    return {};
  }
}

function writeStoredBrowseSources(value: Partial<Record<ToolKind, BrowseSource>>): void {
  try {
    localStorage.setItem(BROWSE_SOURCE_STORAGE_KEY, JSON.stringify(value));
  } catch (error) {
    console.error('Failed to save tool-library browse source to localStorage:', error);
  }
}

export function useToolLibrary() {
  const router = useRouter();

  const activeTab = ref<ToolKind>('science');
  const searchQuery = ref('');
  const loading = reactive<Record<ToolKind, boolean>>({
    science: false,
    external: false,
  });
  const scienceTools = ref<TUTool[]>([]);
  const externalTools = ref<ExternalToolItem[]>([]);
  const preferences = ref<ToolLibraryPreferences>({
    custom_categories: [],
    assignments: [],
  });
  const filters = reactive<Record<ToolKind, ToolLibraryFilterState>>({
    science: createDefaultToolLibraryFilterState(),
    external: createDefaultToolLibraryFilterState(),
  });
  const selectedToolNames = reactive<Record<ToolKind, string[]>>({
    science: [],
    external: [],
  });
  const manageCategoriesOpen = ref(false);
  const assignmentOpen = ref(false);
  const assignmentTarget = ref<{ kind: ToolKind; toolNames: string[]; categoryId: string; subcategoryId: string }>({
    kind: 'science',
    toolNames: [],
    categoryId: '',
    subcategoryId: '',
  });
  const browseSourceInitialized = reactive<Record<ToolKind, boolean>>({
    science: false,
    external: false,
  });

  const assignmentMap = computed(() => {
    const map = new Map<string, { categoryId: string; subcategoryId: string }>();
    for (const assignment of preferences.value.assignments || []) {
      map.set(buildAssignmentKey(assignment.tool_kind, assignment.tool_name), {
        categoryId: assignment.category_id,
        subcategoryId: assignment.subcategory_id,
      });
    }
    return map;
  });

  const categoryMap = computed(() => {
    const map = new Map<string, ToolLibraryCategory>();
    for (const category of preferences.value.custom_categories || []) {
      map.set(category.id, category);
    }
    return map;
  });

  const categoryAssignmentStats = computed(() => {
    const stats = new Map<string, CategoryAssignmentStat>();
    for (const assignment of preferences.value.assignments || []) {
      const current = stats.get(assignment.category_id) || { total: 0, science: 0, external: 0 };
      current.total += 1;
      current[assignment.tool_kind] += 1;
      stats.set(assignment.category_id, current);
    }
    return stats;
  });

  function normalizeDiscipline(tool: TUTool | ExternalToolItem): { id: string; label: string } {
    const id = tool.discipline || tool.system_subgroup || 'other';
    const label = tool.discipline_zh || tool.system_subgroup_zh || id;
    return { id, label };
  }

  function normalizeFunctionGroup(tool: TUTool | ExternalToolItem): { id: string; label: string } {
    const id = tool.function_group || tool.system_group || 'analysis_workflow';
    const label = tool.function_group_zh || tool.system_group_zh || id;
    return { id, label };
  }

  function buildCard(tool: TUTool | ExternalToolItem, kind: ToolKind): ToolCard {
    const assignment = assignmentMap.value.get(buildAssignmentKey(kind, tool.name));
    const category = assignment?.categoryId ? categoryMap.value.get(assignment.categoryId) : undefined;
    const subcategory = category?.subcategories?.find((item) => item.id === assignment?.subcategoryId);
    const discipline = normalizeDiscipline(tool);
    const functionGroup = normalizeFunctionGroup(tool);

    return {
      toolKind: kind,
      name: tool.name,
      description: tool.description || '',
      routeName: kind === 'science'
        ? `/chat/science-tools/${encodeURIComponent(tool.name)}`
        : `/chat/tools/${encodeURIComponent(tool.name)}`,
      category: (tool as ExternalToolItem).category || '',
      subcategory: (tool as ExternalToolItem).subcategory || '',
      tags: Array.isArray((tool as ExternalToolItem).tags) ? [...((tool as ExternalToolItem).tags || [])] : [],
      discipline: discipline.id,
      disciplineLabel: discipline.label,
      functionGroup: functionGroup.id,
      functionGroupLabel: functionGroup.label,
      blocked: Boolean((tool as ExternalToolItem).blocked),
      sourceFile: (tool as ExternalToolItem).source_file || '',
      customCategoryId: assignment?.categoryId || '',
      customCategoryName: category?.name || '',
      customSubcategoryId: assignment?.subcategoryId || '',
      customSubcategoryName: subcategory?.name || '',
      rawTool: tool,
    };
  }

  const scienceCards = computed(() => scienceTools.value.map((tool) => buildCard(tool, 'science')));
  const externalCards = computed(() => externalTools.value.map((tool) => buildCard(tool, 'external')));

  function cardsForKind(kind: ToolKind): ToolCard[] {
    return kind === 'science' ? scienceCards.value : externalCards.value;
  }

  function buildTaxonomyOptions(kind: ToolKind, axis: 'discipline' | 'functionGroup'): TaxonomyOption[] {
    const counts = new Map<string, TaxonomyOption>();
    const cards = cardsForKind(kind);
    const relevantCards = axis === 'functionGroup' && filters[kind].system.discipline
      ? cards.filter((card) => card.discipline === filters[kind].system.discipline)
      : cards;

    for (const card of relevantCards) {
      const id = axis === 'discipline' ? card.discipline : card.functionGroup;
      const labelZh = axis === 'discipline' ? card.disciplineLabel : card.functionGroupLabel;
      const current = counts.get(id) || { id, label: id, labelZh, count: 0 };
      current.count += 1;
      counts.set(id, current);
    }

    return Array.from(counts.values()).sort((left, right) =>
      left.labelZh.localeCompare(right.labelZh, 'zh-Hans-CN')
    );
  }

  const customBrowseStates = computed(() => ({
    science: buildCustomBrowseState(scienceCards.value, preferences.value.custom_categories),
    external: buildCustomBrowseState(externalCards.value, preferences.value.custom_categories),
  }));

  function getCustomBrowseState(kind: ToolKind) {
    return customBrowseStates.value[kind];
  }

  function filterCards(kind: ToolKind): ToolCard[] {
    return filterCardsForBrowse(cardsForKind(kind), filters[kind], searchQuery.value);
  }

  const currentBrowseSource = computed(() => filters[activeTab.value].browseSource);
  const currentCards = computed(() => filterCards(activeTab.value));
  const currentSelection = computed(() => selectedToolNames[activeTab.value]);
  const currentSelectedCount = computed(() => currentSelection.value.length);

  const disciplineOptions = computed(() => buildTaxonomyOptions(activeTab.value, 'discipline'));
  const systemFunctionGroupOptions = computed(() => buildTaxonomyOptions(activeTab.value, 'functionGroup'));
  const functionGroupOptions = computed(() =>
    currentBrowseSource.value === 'system' ? systemFunctionGroupOptions.value : []
  );
  const customCategoryOptions = computed(() => getCustomBrowseState(activeTab.value).categoryOptions);
  const uncategorizedCount = computed(() => getCustomBrowseState(activeTab.value).uncategorizedCount);
  const customSubcategoryOptions = computed(() => {
    const categoryId = filters[activeTab.value].custom.categoryId;
    if (!categoryId || categoryId === UNCATEGORIZED_CATEGORY_ID) {
      return [];
    }
    return getCustomBrowseState(activeTab.value).subcategoryOptionsByCategory.get(categoryId) || [];
  });

  const activeDiscipline = computed(() =>
    disciplineOptions.value.find((option) => option.id === filters[activeTab.value].system.discipline) || null
  );
  const activeCustomCategory = computed(() =>
    customCategoryOptions.value.find((option) => option.id === filters[activeTab.value].custom.categoryId) || null
  );
  const activeCustomSubcategory = computed(() =>
    customSubcategoryOptions.value.find((option) => option.id === filters[activeTab.value].custom.subcategoryId) || null
  );

  const categorySummary = computed(() => {
    const assigned = preferences.value.assignments.filter((assignment) => assignment.tool_kind === activeTab.value);
    return {
      categoryCount: preferences.value.custom_categories.length,
      assignedCount: assigned.length,
    };
  });

  function syncFilterState(kind: ToolKind): void {
    const disciplineIds = new Set(buildTaxonomyOptions(kind, 'discipline').map((option) => option.id));
    if (filters[kind].system.discipline && !disciplineIds.has(filters[kind].system.discipline)) {
      filters[kind].system.discipline = '';
      filters[kind].system.functionGroup = '';
    }

    const functionGroupIds = new Set(buildTaxonomyOptions(kind, 'functionGroup').map((option) => option.id));
    if (filters[kind].system.functionGroup && !functionGroupIds.has(filters[kind].system.functionGroup)) {
      filters[kind].system.functionGroup = '';
    }

    const customState = getCustomBrowseState(kind);
    const categoryIds = new Set(customState.categoryOptions.map((option) => option.id));
    const categoryId = filters[kind].custom.categoryId;
    if (
      categoryId &&
      categoryId !== UNCATEGORIZED_CATEGORY_ID &&
      !categoryIds.has(categoryId)
    ) {
      filters[kind].custom.categoryId = '';
      filters[kind].custom.subcategoryId = '';
      return;
    }

    if (filters[kind].custom.categoryId === UNCATEGORIZED_CATEGORY_ID) {
      filters[kind].custom.subcategoryId = '';
      return;
    }

    const subcategoryIds = new Set(
      customState.subcategoryOptionsByCategory
        .get(filters[kind].custom.categoryId)
        ?.map((option) => option.id) || [],
    );
    if (filters[kind].custom.subcategoryId && !subcategoryIds.has(filters[kind].custom.subcategoryId)) {
      filters[kind].custom.subcategoryId = '';
    }
  }

  function initializeBrowseSources(): void {
    const storedSources = readStoredBrowseSources();
    for (const kind of ['science', 'external'] as const) {
      if (browseSourceInitialized[kind]) {
        continue;
      }
      filters[kind].browseSource = resolveBrowseSourceDefault(
        kind,
        preferences.value.assignments,
        storedSources[kind],
      );
      browseSourceInitialized[kind] = true;
    }
  }

  watch(
    [
      scienceCards,
      externalCards,
      () => preferences.value.custom_categories,
      () => preferences.value.assignments,
    ],
    () => {
      syncFilterState('science');
      syncFilterState('external');
    },
    { deep: true },
  );

  async function loadScienceTools(): Promise<void> {
    loading.science = true;
    try {
      const response = await listTUTools();
      scienceTools.value = response.tools;
    } catch (error: any) {
      showErrorToast(getErrorMessage(error, 'Failed to load science tools.'));
    } finally {
      loading.science = false;
    }
  }

  async function loadExternalTools(): Promise<void> {
    loading.external = true;
    try {
      externalTools.value = await getTools();
    } catch (error: any) {
      showErrorToast(getErrorMessage(error, 'Failed to load external tools.'));
    } finally {
      loading.external = false;
    }
  }

  async function loadPreferences(): Promise<void> {
    try {
      preferences.value = await getToolLibraryPreferences();
    } catch (error: any) {
      showErrorToast(getErrorMessage(error, 'Failed to load tool-library preferences.'));
    }
  }

  async function loadAll(): Promise<void> {
    await Promise.all([loadScienceTools(), loadExternalTools(), loadPreferences()]);
    initializeBrowseSources();
    syncFilterState('science');
    syncFilterState('external');
  }

  async function refreshCurrentTab(): Promise<void> {
    if (activeTab.value === 'science') {
      await loadScienceTools();
    } else {
      await loadExternalTools();
    }
    syncFilterState(activeTab.value);
  }

  function persistBrowseSources(): void {
    writeStoredBrowseSources({
      science: filters.science.browseSource,
      external: filters.external.browseSource,
    });
  }

  function setBrowseSource(kind: ToolKind, browseSource: BrowseSource): void {
    filters[kind].browseSource = browseSource;
    persistBrowseSources();
  }

  function openTool(card: ToolCard): void {
    router.push(card.routeName);
  }

  function setDiscipline(kind: ToolKind, disciplineId: string): void {
    filters[kind].browseSource = 'system';
    filters[kind].system.discipline = filters[kind].system.discipline === disciplineId ? '' : disciplineId;
    filters[kind].system.functionGroup = '';
    persistBrowseSources();
  }

  function setFunctionGroup(kind: ToolKind, groupId: string): void {
    filters[kind].browseSource = 'system';
    filters[kind].system.functionGroup = filters[kind].system.functionGroup === groupId ? '' : groupId;
    persistBrowseSources();
  }

  function setCustomCategory(kind: ToolKind, categoryId: string): void {
    filters[kind].browseSource = 'custom';
    filters[kind].custom.categoryId = filters[kind].custom.categoryId === categoryId ? '' : categoryId;
    filters[kind].custom.subcategoryId = '';
    persistBrowseSources();
  }

  function setCustomSubcategory(kind: ToolKind, subcategoryId: string): void {
    filters[kind].browseSource = 'custom';
    filters[kind].custom.subcategoryId = filters[kind].custom.subcategoryId === subcategoryId ? '' : subcategoryId;
    persistBrowseSources();
  }

  function resetFilters(kind: ToolKind): void {
    if (filters[kind].browseSource === 'system') {
      filters[kind].system.discipline = '';
      filters[kind].system.functionGroup = '';
      return;
    }

    filters[kind].custom.categoryId = '';
    filters[kind].custom.subcategoryId = '';
  }

  function isToolSelected(kind: ToolKind, toolName: string): boolean {
    return selectedToolNames[kind].includes(toolName);
  }

  function toggleToolSelection(kind: ToolKind, toolName: string): void {
    const next = new Set(selectedToolNames[kind]);
    if (next.has(toolName)) {
      next.delete(toolName);
    } else {
      next.add(toolName);
    }
    selectedToolNames[kind] = Array.from(next).sort();
  }

  function toggleVisibleSelection(kind: ToolKind): void {
    const visibleNames = filterCards(kind).map((card) => card.name);
    const selected = new Set(selectedToolNames[kind]);
    const allVisibleSelected = visibleNames.length > 0 && visibleNames.every((name) => selected.has(name));
    if (allVisibleSelected) {
      for (const name of visibleNames) {
        selected.delete(name);
      }
    } else {
      for (const name of visibleNames) {
        selected.add(name);
      }
    }
    selectedToolNames[kind] = Array.from(selected).sort();
  }

  function clearSelection(kind: ToolKind): void {
    selectedToolNames[kind] = [];
  }

  function openAssignmentDialog(kind: ToolKind, toolNames: string[], initialCategoryId = '', initialSubcategoryId = ''): void {
    if (!toolNames.length) {
      return;
    }
    assignmentTarget.value = {
      kind,
      toolNames,
      categoryId: initialCategoryId,
      subcategoryId: initialSubcategoryId,
    };
    assignmentOpen.value = true;
  }

  function openCardAssignment(card: ToolCard): void {
    openAssignmentDialog(card.toolKind, [card.name], card.customCategoryId, card.customSubcategoryId);
  }

  function openSelectedAssignment(): void {
    openAssignmentDialog(activeTab.value, [...currentSelection.value]);
  }

  async function submitAssignment(target: AssignmentTarget): Promise<void> {
    try {
      const nextPreferences = await batchAssignToolLibrary({
        tool_kind: target.kind,
        tool_names: target.toolNames,
        category_id: target.categoryId,
        subcategory_id: target.subcategoryId,
      });
      preferences.value = nextPreferences;
      assignmentOpen.value = false;
      clearSelection(target.kind);
      showSuccessToast(`Assigned ${target.toolNames.length} tool${target.toolNames.length === 1 ? '' : 's'} to your category.`);
    } catch (error: any) {
      showErrorToast(getErrorMessage(error, 'Failed to assign selected tools.'));
    }
  }

  async function clearAssignments(kind: ToolKind, toolNames: string[]): Promise<void> {
    if (!toolNames.length) {
      return;
    }
    try {
      const nextPreferences = await clearToolLibraryAssignments({
        tool_kind: kind,
        tool_names: toolNames,
      });
      preferences.value = nextPreferences;
      clearSelection(kind);
      showSuccessToast(`Cleared category assignment for ${toolNames.length} tool${toolNames.length === 1 ? '' : 's'}.`);
    } catch (error: any) {
      showErrorToast(getErrorMessage(error, 'Failed to clear category assignments.'));
    }
  }

  async function saveCategories(
    categories: ToolLibraryCategory[],
    quickAssign?: AssignmentTarget,
  ): Promise<ToolLibraryPreferences | null> {
    try {
      preferences.value = await updateToolLibraryPreferences({ custom_categories: categories });
      manageCategoriesOpen.value = false;
      showSuccessToast('Saved your custom category tree.');
      if (quickAssign) {
        await submitAssignment(quickAssign);
      }
      return preferences.value;
    } catch (error: any) {
      showErrorToast(getErrorMessage(error, 'Failed to save custom categories.'));
      return null;
    }
  }

  async function toggleExternalToolBlock(card: ToolCard): Promise<void> {
    if (card.toolKind !== 'external') {
      return;
    }
    try {
      await blockTool(card.name, !card.blocked);
      await loadExternalTools();
      showSuccessToast(card.blocked ? 'Tool unblocked.' : 'Tool blocked.');
    } catch (error: any) {
      showErrorToast(getErrorMessage(error, 'Failed to update blocked status.'));
    }
  }

  async function deleteExternalTool(card: ToolCard): Promise<void> {
    if (card.toolKind !== 'external') {
      return;
    }
    const confirmed = window.confirm(`Delete external tool "${card.name}"? This removes the file from the Tools directory.`);
    if (!confirmed) {
      return;
    }
    try {
      await deleteTool(card.name);
      if (preferences.value.assignments.some((assignment) => assignment.tool_kind === 'external' && assignment.tool_name === card.name)) {
        preferences.value = await clearToolLibraryAssignments({
          tool_kind: 'external',
          tool_names: [card.name],
        });
      }
      await loadExternalTools();
      showSuccessToast('External tool deleted.');
    } catch (error: any) {
      showErrorToast(getErrorMessage(error, 'Failed to delete external tool.'));
    }
  }

  const currentLoading = computed(() => loading[activeTab.value]);
  const currentRegionLabel = computed(() => activeTab.value === 'science' ? 'Science' : 'External');
  const currentDescription = computed(() => {
    const cards = cardsForKind(activeTab.value);
    if (filters[activeTab.value].browseSource === 'custom') {
      const customState = getCustomBrowseState(activeTab.value);
      return `${cards.length} ${currentRegionLabel.value.toLowerCase()} tools, ${customState.assignedCount} assigned in your categories and ${customState.uncategorizedCount} still uncategorized.`;
    }

    const disciplineCount = buildTaxonomyOptions(activeTab.value, 'discipline').length;
    return `${cards.length} ${currentRegionLabel.value.toLowerCase()} tools across ${disciplineCount} system disciplines.`;
  });

  return {
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
    functionGroupOptions,
    loadAll,
    loading,
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
    selectedToolNames,
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
    isToolSelected,
    uncategorizedCount,
  };
}
