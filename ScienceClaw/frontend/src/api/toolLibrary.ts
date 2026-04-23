import { apiClient, type ApiResponse } from './client';

export type ToolKind = 'science' | 'external';

export interface ToolLibrarySubcategory {
  id: string;
  name: string;
  order: number;
}

export interface ToolLibraryCategory {
  id: string;
  name: string;
  order: number;
  subcategories: ToolLibrarySubcategory[];
}

export interface ToolLibraryAssignment {
  tool_kind: ToolKind;
  tool_name: string;
  category_id: string;
  subcategory_id: string;
}

export interface ToolLibraryPreferences {
  custom_categories: ToolLibraryCategory[];
  assignments: ToolLibraryAssignment[];
}

export interface UpdateToolLibraryPreferencesRequest {
  custom_categories: ToolLibraryCategory[];
}

export interface BatchAssignToolLibraryRequest {
  tool_kind: ToolKind;
  tool_names: string[];
  category_id: string;
  subcategory_id?: string;
}

export interface ClearToolLibraryAssignmentsRequest {
  tool_kind: ToolKind;
  tool_names: string[];
}

export async function getToolLibraryPreferences(): Promise<ToolLibraryPreferences> {
  const response = await apiClient.get<ApiResponse<ToolLibraryPreferences>>('/tool-library/preferences');
  return response.data.data;
}

export async function updateToolLibraryPreferences(
  payload: UpdateToolLibraryPreferencesRequest,
): Promise<ToolLibraryPreferences> {
  const response = await apiClient.put<ApiResponse<ToolLibraryPreferences>>('/tool-library/preferences', payload);
  return response.data.data;
}

export async function batchAssignToolLibrary(
  payload: BatchAssignToolLibraryRequest,
): Promise<ToolLibraryPreferences> {
  const response = await apiClient.post<ApiResponse<ToolLibraryPreferences>>('/tool-library/assignments/batch', payload);
  return response.data.data;
}

export async function clearToolLibraryAssignments(
  payload: ClearToolLibraryAssignmentsRequest,
): Promise<ToolLibraryPreferences> {
  const response = await apiClient.delete<ApiResponse<ToolLibraryPreferences>>('/tool-library/assignments', {
    data: payload,
  });
  return response.data.data;
}

