import type { ExternalToolItem } from '../../types/response';
import type { TUTool } from '../../api/tooluniverse';
import type {
  ToolKind,
  ToolLibraryAssignment,
  ToolLibraryCategory,
  ToolLibrarySubcategory,
  ToolLibraryPreferences,
} from '../../api/toolLibrary';

export type { ToolKind, ToolLibraryAssignment, ToolLibraryCategory, ToolLibraryPreferences };
export type { ToolLibrarySubcategory };

export type BrowseSource = 'system' | 'custom';

export interface TaxonomyOption {
  id: string;
  label: string;
  labelZh: string;
  count: number;
}

export interface CustomCategoryOption extends TaxonomyOption {
  subcategoryCount: number;
  isVirtual?: boolean;
}

export interface SystemFilterState {
  discipline: string;
  functionGroup: string;
}

export interface CustomFilterState {
  categoryId: string;
  subcategoryId: string;
}

export interface ToolLibraryFilterState {
  browseSource: BrowseSource;
  system: SystemFilterState;
  custom: CustomFilterState;
}

export interface ToolCard {
  toolKind: ToolKind;
  name: string;
  description: string;
  routeName: string;
  category: string;
  subcategory: string;
  tags: string[];
  discipline: string;
  disciplineLabel: string;
  functionGroup: string;
  functionGroupLabel: string;
  blocked: boolean;
  sourceFile: string;
  customCategoryId: string;
  customCategoryName: string;
  customSubcategoryId: string;
  customSubcategoryName: string;
  rawTool: TUTool | ExternalToolItem;
}

export interface AssignmentTarget {
  kind: ToolKind;
  toolNames: string[];
  categoryId: string;
  subcategoryId: string;
}

export type CategoryCreateMode = 'single' | 'batch' | 'copy' | 'context';

export interface ParsedCategorySeed {
  name: string;
  subcategories: string[];
}

export interface CategoryTemplateItem {
  name: string;
  subcategories: string[];
}

export interface CategoryTemplateDocument {
  kind: 'tool-library-category-template';
  version: 1;
  generatedAt: string;
  categories: CategoryTemplateItem[];
}

export interface CategoryImportWarning {
  line: number;
  raw: string;
  message: string;
}

export interface CategoryTemplateParseResult {
  seeds: ParsedCategorySeed[];
  warnings: CategoryImportWarning[];
}

export interface CategoryPreviewItem {
  name: string;
  action: 'create' | 'merge' | 'skip';
  createdSubcategories: string[];
  mergedSubcategories: string[];
  skippedSubcategories: string[];
}

export interface CategoryPreviewSummary {
  categoriesCreated: number;
  categoriesMerged: number;
  categoriesSkipped: number;
  subcategoriesCreated: number;
  subcategoriesMerged: number;
  subcategoriesSkipped: number;
}

export interface CategoryApplyResult {
  categories: ToolLibraryCategory[];
  preview: CategoryPreviewItem[];
  summary: CategoryPreviewSummary;
}

export interface CategoryContextOption {
  id: 'discipline' | 'function-group' | 'search-result' | 'selected-tools';
  label: string;
  description: string;
  categoryName: string;
  subcategories: string[];
  disabled?: boolean;
}

export interface CategorySelectionMatch {
  categoryId: string;
  subcategoryId: string;
  categoryName: string;
  subcategoryName: string;
}

export type ToolLibraryDraftCategory = ToolLibraryCategory;
export type ToolLibraryDraftSubcategory = ToolLibrarySubcategory;
