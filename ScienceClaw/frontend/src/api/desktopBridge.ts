import { apiClient, type ApiResponse } from './client';

export interface DesktopBridgeHealth {
  available: boolean;
  bridge_url: string;
  status?: string;
  error?: string;
}

export interface PickDirectoryResult {
  cancelled: boolean;
  path: string;
  bridge_url?: string;
}

export interface ObsidianVaultTestResult {
  vault_dir: string;
  has_obsidian_config: boolean;
  materials_root: string;
  created_dirs: string[];
  bridge_url?: string;
}

export async function getDesktopBridgeHealth(): Promise<DesktopBridgeHealth> {
  const response = await apiClient.get<ApiResponse<DesktopBridgeHealth>>('/desktop/bridge/health');
  return response.data.data;
}

export async function pickObsidianVaultDirectory(payload: {
  title?: string;
  initial_dir?: string;
} = {}): Promise<PickDirectoryResult> {
  const response = await apiClient.post<ApiResponse<PickDirectoryResult>>('/desktop/obsidian/pick-directory', payload);
  return response.data.data;
}

export async function testObsidianVault(payload: {
  vault_dir: string;
  create_if_missing?: boolean;
  bootstrap_materials?: boolean;
}): Promise<ObsidianVaultTestResult> {
  const response = await apiClient.post<ApiResponse<ObsidianVaultTestResult>>('/desktop/obsidian/test-vault', payload);
  return response.data.data;
}
