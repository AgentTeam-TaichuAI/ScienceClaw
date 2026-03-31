import type { ToolKind, ToolLibraryAssignment, ToolLibraryCategory } from '../../api/toolLibrary';
import type {
  BrowseSource,
  CustomCategoryOption,
  TaxonomyOption,
  ToolCard,
  ToolLibraryFilterState,
} from './types';

export const UNCATEGORIZED_CATEGORY_ID = '__uncategorized__';

export function createDefaultToolLibraryFilterState(
  browseSource: BrowseSource = 'system',
): ToolLibraryFilterState {
  return {
    browseSource,
    system: {
      discipline: '',
      functionGroup: '',
    },
    custom: {
      categoryId: '',
      subcategoryId: '',
    },
  };
}

function searchCards(cards: ToolCard[], query: string): ToolCard[] {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) {
    return cards;
  }

  return cards.filter((card) => {
    const haystack = [
      card.name,
      card.description,
      card.disciplineLabel,
      card.functionGroupLabel,
      card.customCategoryName,
      card.customSubcategoryName,
      card.category,
      card.subcategory,
      ...card.tags,
    ]
      .join(' ')
      .toLowerCase();

    return haystack.includes(normalizedQuery);
  });
}

export function filterCardsForBrowse(
  cards: ToolCard[],
  filterState: ToolLibraryFilterState,
  searchQuery: string,
): ToolCard[] {
  let filtered = [...cards];

  if (filterState.browseSource === 'system') {
    if (filterState.system.discipline) {
      filtered = filtered.filter((card) => card.discipline === filterState.system.discipline);
    }
    if (filterState.system.functionGroup) {
      filtered = filtered.filter((card) => card.functionGroup === filterState.system.functionGroup);
    }
  } else {
    if (filterState.custom.categoryId === UNCATEGORIZED_CATEGORY_ID) {
      filtered = filtered.filter((card) => !card.customCategoryId);
    } else if (filterState.custom.categoryId) {
      filtered = filtered.filter((card) => card.customCategoryId === filterState.custom.categoryId);
    }

    if (filterState.custom.subcategoryId) {
      filtered = filtered.filter((card) => card.customSubcategoryId === filterState.custom.subcategoryId);
    }
  }

  return searchCards(filtered, searchQuery);
}

export function resolveBrowseSourceDefault(
  kind: ToolKind,
  assignments: ToolLibraryAssignment[],
  storedSource?: BrowseSource | null,
): BrowseSource {
  if (storedSource === 'system' || storedSource === 'custom') {
    return storedSource;
  }

  return assignments.some((assignment) => assignment.tool_kind === kind) ? 'custom' : 'system';
}

export type CustomBrowseState = {
  assignedCount: number;
  uncategorizedCount: number;
  categoryOptions: CustomCategoryOption[];
  subcategoryOptionsByCategory: Map<string, TaxonomyOption[]>;
};

export function buildCustomBrowseState(
  cards: ToolCard[],
  categories: ToolLibraryCategory[],
): CustomBrowseState {
  const categoryCounts = new Map<string, number>();
  const subcategoryCounts = new Map<string, Map<string, number>>();
  let assignedCount = 0;

  for (const card of cards) {
    if (!card.customCategoryId) {
      continue;
    }

    assignedCount += 1;
    categoryCounts.set(card.customCategoryId, (categoryCounts.get(card.customCategoryId) || 0) + 1);

    if (!card.customSubcategoryId) {
      continue;
    }

    if (!subcategoryCounts.has(card.customCategoryId)) {
      subcategoryCounts.set(card.customCategoryId, new Map());
    }

    const bucket = subcategoryCounts.get(card.customCategoryId)!;
    bucket.set(card.customSubcategoryId, (bucket.get(card.customSubcategoryId) || 0) + 1);
  }

  const sortedCategories = [...categories].sort((left, right) => {
    if (left.order !== right.order) {
      return left.order - right.order;
    }
    return left.name.localeCompare(right.name, 'zh-Hans-CN');
  });

  const categoryOptions: CustomCategoryOption[] = [];
  const subcategoryOptionsByCategory = new Map<string, TaxonomyOption[]>();

  for (const category of sortedCategories) {
    const sortedSubcategories = [...category.subcategories].sort((left, right) => {
      if (left.order !== right.order) {
        return left.order - right.order;
      }
      return left.name.localeCompare(right.name, 'zh-Hans-CN');
    });

    categoryOptions.push({
      id: category.id,
      label: category.name,
      labelZh: category.name,
      count: categoryCounts.get(category.id) || 0,
      subcategoryCount: sortedSubcategories.length,
    });

    subcategoryOptionsByCategory.set(
      category.id,
      sortedSubcategories.map((subcategory) => ({
        id: subcategory.id,
        label: subcategory.name,
        labelZh: subcategory.name,
        count: subcategoryCounts.get(category.id)?.get(subcategory.id) || 0,
      })),
    );
  }

  return {
    assignedCount,
    uncategorizedCount: Math.max(cards.length - assignedCount, 0),
    categoryOptions,
    subcategoryOptionsByCategory,
  };
}
