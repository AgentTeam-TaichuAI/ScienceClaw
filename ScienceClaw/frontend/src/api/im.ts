import { apiClient, type ApiResponse } from './client';

export interface LarkBindingStatus {
  bound: boolean;
  platform?: string;
  platform_user_id?: string;
  science_user_id?: string;
  status?: string;
  updated_at?: number;
}

export interface BindLarkRequest {
  lark_user_id: string;
  lark_union_id?: string;
}

export interface IMSystemSettings {
  im_enabled: boolean;
  im_response_timeout: number;
  im_max_message_length: number;
  lark_enabled: boolean;
  lark_app_id: string;
  has_lark_app_secret: boolean;
  lark_app_secret_masked: string;
  wechat_enabled: boolean;
  im_progress_mode: 'text_multi' | 'card_entity';
  im_progress_detail_level: 'compact' | 'detailed';
  im_progress_interval_ms: number;
  im_realtime_events: Array<'plan_update' | 'planning_message' | 'tool_call' | 'tool_result' | 'error'>;
}

export interface UpdateIMSystemSettingsRequest {
  im_enabled?: boolean;
  im_response_timeout?: number;
  im_max_message_length?: number;
  lark_enabled?: boolean;
  lark_app_id?: string;
  lark_app_secret?: string;
  wechat_enabled?: boolean;
  im_progress_mode?: 'text_multi' | 'card_entity';
  im_progress_detail_level?: 'compact' | 'detailed';
  im_progress_interval_ms?: number;
  im_realtime_events?: Array<'plan_update' | 'planning_message' | 'tool_call' | 'tool_result' | 'error'>;
}

export interface WeChatBridgeStatus {
  status: string;
  is_running: boolean;
  is_logging_in: boolean;
  error: string | null;
  started_at: number | null;
  qr_content: string | null;
  qr_image: string | null;
  account_id: string | null;
  has_saved_token: boolean;
  output_total: number;
  output_offset: number;
  output: string[];
}

export async function getLarkBindingStatus(): Promise<LarkBindingStatus> {
  const response = await apiClient.get<ApiResponse<LarkBindingStatus>>('/im/bind/lark/status');
  return response.data.data;
}

export async function bindLarkAccount(payload: BindLarkRequest): Promise<LarkBindingStatus> {
  const response = await apiClient.post<ApiResponse<LarkBindingStatus>>('/im/bind/lark', payload);
  return response.data.data;
}

export async function unbindLarkAccount(): Promise<{ removed: boolean }> {
  const response = await apiClient.delete<ApiResponse<{ removed: boolean }>>('/im/bind/lark');
  return response.data.data;
}

export async function getIMSystemSettings(): Promise<IMSystemSettings> {
  const response = await apiClient.get<ApiResponse<IMSystemSettings>>('/im/settings');
  return response.data.data;
}

export async function updateIMSystemSettings(payload: UpdateIMSystemSettingsRequest): Promise<IMSystemSettings> {
  const response = await apiClient.put<ApiResponse<IMSystemSettings>>('/im/settings', payload);
  return response.data.data;
}

export async function startWeChatBridge(): Promise<Record<string, any>> {
  const response = await apiClient.post<ApiResponse<Record<string, any>>>('/im/wechat/start');
  return response.data.data;
}

export async function resumeWeChatBridge(): Promise<Record<string, any>> {
  const response = await apiClient.post<ApiResponse<Record<string, any>>>('/im/wechat/resume');
  return response.data.data;
}

export async function stopWeChatBridge(): Promise<Record<string, any>> {
  const response = await apiClient.post<ApiResponse<Record<string, any>>>('/im/wechat/stop');
  return response.data.data;
}

export async function logoutWeChatBridge(): Promise<Record<string, any>> {
  const response = await apiClient.post<ApiResponse<Record<string, any>>>('/im/wechat/logout');
  return response.data.data;
}

export async function getWeChatBridgeStatus(outputOffset = 0): Promise<WeChatBridgeStatus> {
  const response = await apiClient.get<ApiResponse<WeChatBridgeStatus>>('/im/wechat/status', {
    params: { output_offset: outputOffset },
  });
  return response.data.data;
}
