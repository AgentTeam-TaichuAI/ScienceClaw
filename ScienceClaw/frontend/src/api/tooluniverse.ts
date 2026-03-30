import { apiClient } from './client';
import { i18n } from '../composables/useI18n';

function _lang(): string {
  return i18n.global.locale.value || 'en';
}

export interface TUTool {
  name: string;
  description: string;
  category: string;
  category_zh?: string;
  tool_type?: string;
  family?: string;
  action?: string;
  function_group?: string;
  function_group_zh?: string;
  discipline?: string;
  discipline_zh?: string;
  system_group?: string;
  system_group_zh?: string;
  system_subgroup?: string;
  system_subgroup_zh?: string;
  param_count: number;
  required_params?: string[];
  has_examples?: boolean;
  has_return_schema?: boolean;
}

export interface TUToolSpec {
  name: string;
  description: string;
  parameters: {
    type: string;
    properties: Record<string, {
      type: string;
      description: string;
      required?: boolean;
      enum?: string[];
    }>;
    required?: string[];
  };
  test_examples: Record<string, any>[];
  return_schema: any;
  category: string;
  category_zh?: string;
  tool_type?: string;
  family?: string;
  action?: string;
  function_group?: string;
  function_group_zh?: string;
  discipline?: string;
  discipline_zh?: string;
  system_group?: string;
  system_group_zh?: string;
  system_subgroup?: string;
  system_subgroup_zh?: string;
  source_file: string;
}

export interface TUCategory {
  name: string;
  name_zh?: string;
  count: number;
}

export async function listTUTools(search?: string, category?: string): Promise<{
  tools: TUTool[];
  total: number;
  categories: string[];
}> {
  const params: Record<string, string> = { lang: _lang() };
  if (search) params.search = search;
  if (category) params.category = category;
  const resp = await apiClient.get('/tooluniverse/tools', { params });
  return resp.data;
}

export async function getTUToolSpec(toolName: string): Promise<TUToolSpec> {
  const resp = await apiClient.get(`/tooluniverse/tools/${encodeURIComponent(toolName)}`, {
    params: { lang: _lang() },
  });
  return resp.data;
}

export async function runTUTool(toolName: string, args: Record<string, any>): Promise<{
  success: boolean;
  result: any;
}> {
  const resp = await apiClient.post(`/tooluniverse/tools/${encodeURIComponent(toolName)}/run`, {
    arguments: args,
  });
  return resp.data;
}

export async function listTUCategories(): Promise<TUCategory[]> {
  const resp = await apiClient.get('/tooluniverse/categories', {
    params: { lang: _lang() },
  });
  return resp.data.categories;
}
