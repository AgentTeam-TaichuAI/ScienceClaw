import { apiClient, type ApiResponse } from './client';

export interface TaskSettings {
  agent_stream_timeout: number;
  sandbox_exec_timeout: number;
  max_tokens: number;
  output_reserve: number;
  max_history_rounds: number;
  max_output_chars: number;
  obsidian_vault_dir: string;
}

export type UpdateTaskSettingsRequest = Partial<TaskSettings>;

export async function getTaskSettings(): Promise<TaskSettings> {
  const response = await apiClient.get<ApiResponse<TaskSettings>>('/task-settings');
  return response.data.data;
}

export async function updateTaskSettings(data: UpdateTaskSettingsRequest): Promise<TaskSettings> {
  const response = await apiClient.put<ApiResponse<TaskSettings>>('/task-settings', data);
  return response.data.data;
}
