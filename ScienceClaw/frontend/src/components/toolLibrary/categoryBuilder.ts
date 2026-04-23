import type { ToolLibraryCategory, ToolLibrarySubcategory } from '../../api/toolLibrary';
import type {
  CategoryApplyResult,
  CategoryImportWarning,
  CategoryPreviewItem,
  CategoryPreviewSummary,
  CategoryTemplateDocument,
  CategoryTemplateParseResult,
  ParsedCategorySeed,
} from './types';

function jsonClone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value));
}

export function cloneCategories(categories: ToolLibraryCategory[]): ToolLibraryCategory[] {
  return jsonClone(categories || []);
}

export function normalizeCategoryLabel(value: string): string {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

export function normalizeCategoryKey(value: string): string {
  return normalizeCategoryLabel(value).toLocaleLowerCase();
}

export function slugifyCategoryLabel(value: string): string {
  return normalizeCategoryLabel(value)
    .toLowerCase()
    .replace(/[^a-z0-9\u4e00-\u9fa5]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60);
}

export function nextToolLibraryId(baseLabel: string, existingIds: Set<string>, prefix: string): string {
  const base = slugifyCategoryLabel(baseLabel) || prefix;
  let candidate = `${prefix}-${base}`;
  let index = 2;
  while (existingIds.has(candidate)) {
    candidate = `${prefix}-${base}-${index}`;
    index += 1;
  }
  return candidate;
}

export function reindexCategories(categories: ToolLibraryCategory[]): ToolLibraryCategory[] {
  return categories.map((category, categoryIndex) => ({
    ...category,
    order: categoryIndex,
    subcategories: category.subcategories.map((subcategory, subcategoryIndex) => ({
      ...subcategory,
      order: subcategoryIndex,
    })),
  }));
}

function uniqueNormalizedValues(values: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];

  for (const value of values) {
    const normalized = normalizeCategoryLabel(value);
    const key = normalizeCategoryKey(normalized);
    if (!key || seen.has(key)) {
      continue;
    }
    seen.add(key);
    result.push(normalized);
  }

  return result;
}

function ensureSeed(seedMap: Map<string, ParsedCategorySeed>, name: string): ParsedCategorySeed {
  const normalizedName = normalizeCategoryLabel(name);
  const key = normalizeCategoryKey(normalizedName);
  const existing = seedMap.get(key);
  if (existing) {
    return existing;
  }
  const created: ParsedCategorySeed = {
    name: normalizedName,
    subcategories: [],
  };
  seedMap.set(key, created);
  return created;
}

function addSubcategoryToSeed(seed: ParsedCategorySeed, subcategoryName: string): void {
  const normalized = normalizeCategoryLabel(subcategoryName);
  if (!normalized) {
    return;
  }
  const key = normalizeCategoryKey(normalized);
  if (seed.subcategories.some((item) => normalizeCategoryKey(item) === key)) {
    return;
  }
  seed.subcategories.push(normalized);
}

function splitDelimitedCategoryLine(line: string): { categoryName: string; subcategoryName: string } | null {
  const gtMatch = line.match(/^(.+?)\s*>\s*(.+)$/);
  if (gtMatch) {
    return {
      categoryName: normalizeCategoryLabel(gtMatch[1]),
      subcategoryName: normalizeCategoryLabel(gtMatch[2]),
    };
  }

  const slashMatch = line.match(/^(.+?)\s\/\s(.+)$/);
  if (slashMatch) {
    return {
      categoryName: normalizeCategoryLabel(slashMatch[1]),
      subcategoryName: normalizeCategoryLabel(slashMatch[2]),
    };
  }

  return null;
}

export function parseSubcategoryText(text: string): string[] {
  const values: string[] = [];
  for (const rawLine of String(text || '').split(/\r?\n/)) {
    if (!rawLine.trim()) {
      continue;
    }
    const normalized = normalizeCategoryLabel(rawLine);
    const delimited = splitDelimitedCategoryLine(normalized);
    values.push(delimited?.subcategoryName || normalized);
  }
  return uniqueNormalizedValues(values);
}

export function buildSingleCategorySeed(categoryName: string, subcategoryText = ''): ParsedCategorySeed | null {
  const normalizedName = normalizeCategoryLabel(categoryName);
  if (!normalizedName) {
    return null;
  }
  return {
    name: normalizedName,
    subcategories: parseSubcategoryText(subcategoryText),
  };
}

export function parseCategoryBatchText(text: string): {
  seeds: ParsedCategorySeed[];
  warnings: CategoryImportWarning[];
} {
  const seedMap = new Map<string, ParsedCategorySeed>();
  const warnings: CategoryImportWarning[] = [];
  let lastSeedKey = '';

  String(text || '')
    .split(/\r?\n/)
    .forEach((rawLine, index) => {
      if (!rawLine.trim()) {
        return;
      }

      if (/^\s+/.test(rawLine)) {
        if (!lastSeedKey || !seedMap.has(lastSeedKey)) {
          warnings.push({
            line: index + 1,
            raw: rawLine,
            message: 'Indented subcategory lines need a category line above them.',
          });
          return;
        }
        addSubcategoryToSeed(seedMap.get(lastSeedKey)!, rawLine);
        return;
      }

      const normalized = normalizeCategoryLabel(rawLine);
      const delimited = splitDelimitedCategoryLine(normalized);
      if (delimited) {
        const seed = ensureSeed(seedMap, delimited.categoryName);
        addSubcategoryToSeed(seed, delimited.subcategoryName);
        lastSeedKey = normalizeCategoryKey(seed.name);
        return;
      }

      const seed = ensureSeed(seedMap, normalized);
      lastSeedKey = normalizeCategoryKey(seed.name);
    });

  return {
    seeds: Array.from(seedMap.values()),
    warnings,
  };
}

export function buildCopySeed(
  category: ToolLibraryCategory | null | undefined,
  existingCategories: ToolLibraryCategory[],
  includeSubcategories: boolean,
): ParsedCategorySeed | null {
  if (!category) {
    return null;
  }

  const existingKeys = new Set(existingCategories.map((item) => normalizeCategoryKey(item.name)));
  const baseName = normalizeCategoryLabel(category.name);
  let candidateName = `${baseName} Copy`;
  let index = 2;
  while (existingKeys.has(normalizeCategoryKey(candidateName))) {
    candidateName = `${baseName} Copy ${index}`;
    index += 1;
  }

  return {
    name: candidateName,
    subcategories: includeSubcategories
      ? uniqueNormalizedValues(category.subcategories.map((subcategory) => subcategory.name))
      : [],
  };
}

export function buildCategoryTemplate(categories: ToolLibraryCategory[]): CategoryTemplateDocument {
  const normalizedCategories = reindexCategories(cloneCategories(categories))
    .map((category) => ({
      name: normalizeCategoryLabel(category.name),
      subcategories: uniqueNormalizedValues(category.subcategories.map((subcategory) => subcategory.name)),
    }))
    .filter((category) => category.name);

  return {
    kind: 'tool-library-category-template',
    version: 1,
    generatedAt: new Date().toISOString(),
    categories: normalizedCategories,
  };
}

export function serializeCategoryTemplate(categories: ToolLibraryCategory[]): string {
  return JSON.stringify(buildCategoryTemplate(categories), null, 2);
}

export function parseCategoryTemplateJson(text: string): CategoryTemplateParseResult {
  let parsed: unknown;
  try {
    parsed = JSON.parse(String(text || ''));
  } catch (error) {
    throw new Error('Invalid JSON. Use a template file or a JSON array of categories.');
  }

  const rawCategories = Array.isArray(parsed)
    ? parsed
    : parsed && typeof parsed === 'object' && Array.isArray((parsed as { categories?: unknown[] }).categories)
      ? (parsed as { categories: unknown[] }).categories
      : null;

  if (!rawCategories) {
    throw new Error('Template JSON must be an array of categories or an object with a categories array.');
  }

  const seedMap = new Map<string, ParsedCategorySeed>();
  const warnings: CategoryImportWarning[] = [];

  rawCategories.forEach((rawCategory, index) => {
    if (!rawCategory || typeof rawCategory !== 'object') {
      warnings.push({
        line: index + 1,
        raw: JSON.stringify(rawCategory),
        message: 'Each template entry must be an object with a category name.',
      });
      return;
    }

    const categoryRecord = rawCategory as {
      name?: unknown;
      subcategories?: unknown;
    };
    const categoryName = normalizeCategoryLabel(typeof categoryRecord.name === 'string' ? categoryRecord.name : '');
    if (!categoryName) {
      warnings.push({
        line: index + 1,
        raw: JSON.stringify(rawCategory),
        message: 'Template entries need a non-empty "name" field.',
      });
      return;
    }

    const seed = ensureSeed(seedMap, categoryName);
    if (categoryRecord.subcategories == null) {
      return;
    }
    if (!Array.isArray(categoryRecord.subcategories)) {
      warnings.push({
        line: index + 1,
        raw: JSON.stringify(rawCategory),
        message: '"subcategories" must be an array when provided.',
      });
      return;
    }

    categoryRecord.subcategories.forEach((rawSubcategory) => {
      if (typeof rawSubcategory === 'string') {
        addSubcategoryToSeed(seed, rawSubcategory);
        return;
      }
      if (rawSubcategory && typeof rawSubcategory === 'object' && typeof (rawSubcategory as { name?: unknown }).name === 'string') {
        addSubcategoryToSeed(seed, (rawSubcategory as { name: string }).name);
        return;
      }
      warnings.push({
        line: index + 1,
        raw: JSON.stringify(rawSubcategory),
        message: 'Subcategories must be strings or objects with a "name" field.',
      });
    });
  });

  return {
    seeds: Array.from(seedMap.values()),
    warnings,
  };
}

export function applyCategorySeeds(
  categories: ToolLibraryCategory[],
  seeds: ParsedCategorySeed[],
): CategoryApplyResult {
  const working = reindexCategories(cloneCategories(categories));
  const categoryIds = new Set(working.map((category) => category.id));
  const categoryMap = new Map<string, ToolLibraryCategory>();
  const previewMap = new Map<string, CategoryPreviewItem>();

  for (const category of working) {
    categoryMap.set(normalizeCategoryKey(category.name), category);
  }

  const upsertPreview = (name: string): CategoryPreviewItem => {
    const key = normalizeCategoryKey(name);
    const existing = previewMap.get(key);
    if (existing) {
      return existing;
    }
    const created: CategoryPreviewItem = {
      name: normalizeCategoryLabel(name),
      action: 'skip',
      createdSubcategories: [],
      mergedSubcategories: [],
      skippedSubcategories: [],
    };
    previewMap.set(key, created);
    return created;
  };

  for (const rawSeed of seeds) {
    const seedName = normalizeCategoryLabel(rawSeed.name);
    const seedKey = normalizeCategoryKey(seedName);
    if (!seedKey) {
      continue;
    }

    let category = categoryMap.get(seedKey);
    const preview = upsertPreview(seedName);

    if (!category) {
      category = {
        id: nextToolLibraryId(seedName, categoryIds, 'cat'),
        name: seedName,
        order: working.length,
        subcategories: [],
      };
      working.push(category);
      categoryIds.add(category.id);
      categoryMap.set(seedKey, category);
      preview.action = 'create';
      preview.name = category.name;
    }

    const subIds = new Set(category.subcategories.map((subcategory) => subcategory.id));
    const subcategoryMap = new Map<string, ToolLibrarySubcategory>();
    for (const subcategory of category.subcategories) {
      subcategoryMap.set(normalizeCategoryKey(subcategory.name), subcategory);
    }

    for (const rawSubcategory of rawSeed.subcategories || []) {
      const subcategoryName = normalizeCategoryLabel(rawSubcategory);
      const subcategoryKey = normalizeCategoryKey(subcategoryName);
      if (!subcategoryKey) {
        continue;
      }

      if (subcategoryMap.has(subcategoryKey)) {
        if (!preview.skippedSubcategories.some((item) => normalizeCategoryKey(item) === subcategoryKey)) {
          preview.skippedSubcategories.push(subcategoryName);
        }
        continue;
      }

      const createdSubcategory: ToolLibrarySubcategory = {
        id: nextToolLibraryId(subcategoryName, subIds, 'sub'),
        name: subcategoryName,
        order: category.subcategories.length,
      };
      category.subcategories.push(createdSubcategory);
      subIds.add(createdSubcategory.id);
      subcategoryMap.set(subcategoryKey, createdSubcategory);

      if (preview.action === 'create') {
        preview.createdSubcategories.push(subcategoryName);
      } else {
        preview.action = 'merge';
        preview.mergedSubcategories.push(subcategoryName);
      }
    }
  }

  const normalizedPreview = Array.from(previewMap.values()).map((item) => ({
    ...item,
    createdSubcategories: uniqueNormalizedValues(item.createdSubcategories),
    mergedSubcategories: uniqueNormalizedValues(item.mergedSubcategories),
    skippedSubcategories: uniqueNormalizedValues(item.skippedSubcategories),
  }));

  const summary: CategoryPreviewSummary = {
    categoriesCreated: normalizedPreview.filter((item) => item.action === 'create').length,
    categoriesMerged: normalizedPreview.filter((item) => item.action === 'merge').length,
    categoriesSkipped: normalizedPreview.filter((item) => item.action === 'skip').length,
    subcategoriesCreated: normalizedPreview.reduce((total, item) => total + item.createdSubcategories.length, 0),
    subcategoriesMerged: normalizedPreview.reduce((total, item) => total + item.mergedSubcategories.length, 0),
    subcategoriesSkipped: normalizedPreview.reduce((total, item) => total + item.skippedSubcategories.length, 0),
  };

  return {
    categories: reindexCategories(working),
    preview: normalizedPreview,
    summary,
  };
}

export function appendSubcategoriesToCategory(
  categories: ToolLibraryCategory[],
  categoryId: string,
  subcategoryNames: string[],
): CategoryApplyResult {
  const category = categories.find((item) => item.id === categoryId);
  if (!category) {
    return {
      categories: reindexCategories(cloneCategories(categories)),
      preview: [],
      summary: {
        categoriesCreated: 0,
        categoriesMerged: 0,
        categoriesSkipped: 0,
        subcategoriesCreated: 0,
        subcategoriesMerged: 0,
        subcategoriesSkipped: 0,
      },
    };
  }

  return applyCategorySeeds(categories, [
    {
      name: category.name,
      subcategories: subcategoryNames,
    },
  ]);
}

export function validateCategoryDraft(categories: ToolLibraryCategory[]): string[] {
  const errors: string[] = [];
  const seenCategoryNames = new Set<string>();

  for (const category of categories) {
    const normalizedCategoryName = normalizeCategoryLabel(category.name);
    const normalizedCategoryKey = normalizeCategoryKey(category.name);
    if (!normalizedCategoryName) {
      errors.push('Category names cannot be empty.');
    } else if (seenCategoryNames.has(normalizedCategoryKey)) {
      errors.push(`Duplicate category name: ${normalizedCategoryName}`);
    } else {
      seenCategoryNames.add(normalizedCategoryKey);
    }

    const seenSubcategoryNames = new Set<string>();
    for (const subcategory of category.subcategories) {
      const normalizedSubcategoryName = normalizeCategoryLabel(subcategory.name);
      const normalizedSubcategoryKey = normalizeCategoryKey(subcategory.name);
      if (!normalizedSubcategoryName) {
        errors.push(`Subcategory under "${normalizedCategoryName || normalizeCategoryLabel(category.name) || 'Untitled category'}" cannot be empty.`);
      } else if (seenSubcategoryNames.has(normalizedSubcategoryKey)) {
        errors.push(`Duplicate subcategory "${normalizedSubcategoryName}" under "${normalizeCategoryLabel(category.name) || 'Untitled category'}".`);
      } else {
        seenSubcategoryNames.add(normalizedSubcategoryKey);
      }
    }
  }

  return Array.from(new Set(errors));
}

export function moveItemById<T extends { id: string }>(items: T[], draggedId: string, targetId: string): T[] {
  if (!draggedId || !targetId || draggedId === targetId) {
    return [...items];
  }

  const next = [...items];
  const fromIndex = next.findIndex((item) => item.id === draggedId);
  const toIndex = next.findIndex((item) => item.id === targetId);
  if (fromIndex === -1 || toIndex === -1) {
    return next;
  }

  const [moved] = next.splice(fromIndex, 1);
  next.splice(toIndex, 0, moved);
  return next;
}

export function resolveCategorySelection(
  categories: ToolLibraryCategory[],
  categoryName: string,
  subcategoryName = '',
): { categoryId: string; subcategoryId: string } {
  const categoryKey = normalizeCategoryKey(categoryName);
  const subcategoryKey = normalizeCategoryKey(subcategoryName);
  const category = categories.find((item) => normalizeCategoryKey(item.name) === categoryKey);
  if (!category) {
    return { categoryId: '', subcategoryId: '' };
  }
  const subcategory = category.subcategories.find((item) => normalizeCategoryKey(item.name) === subcategoryKey);
  return {
    categoryId: category.id,
    subcategoryId: subcategory?.id || '',
  };
}
