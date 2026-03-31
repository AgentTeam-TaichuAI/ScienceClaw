// File API service
import { apiClient, ApiResponse, API_CONFIG } from './client';
import { SignedUrlResponse } from '../types/response';

/**
 * File info type
 */
export interface FileInfo {
  file_id: string;
  filename: string;
  content_type?: string;
  size: number;
  upload_date: string;
  metadata?: Record<string, any>;
  file_url?: string;
  category?: 'result' | 'process' | 'system';
}



/**
 * Upload file to a session workspace (/home/scienceclaw/{sessionId}/)
 * @param file File to upload
 * @param sessionId Session ID to upload the file into
 * @returns Upload result with absolute path as file_id
 */
export async function uploadFile(file: File, sessionId: string): Promise<FileInfo> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<ApiResponse<FileInfo>>(`/sessions/${sessionId}/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data.data;
}

/**
 * Download file
 * @param fileId File ID
 * @returns File download result
 */
export async function downloadFile(fileId: string): Promise<Blob> {
  const response = await apiClient.get(`/files/${fileId}/download`, {
    responseType: 'blob',
  });
  
  return response.data;
}

/**
 * Delete file
 * @param fileId File ID
 * @returns Success status
 */
export async function deleteFile(fileId: string): Promise<boolean> {
  try {
    await apiClient.delete<ApiResponse<void>>(`/files/${fileId}`);
    return true;
  } catch (error) {
    console.error('Failed to delete file:', error);
    return false;
  }
}

/**
 * Get file information
 * @param fileId File ID
 * @returns File information or null if not found
 */
export async function getFileInfo(fileId: string): Promise<FileInfo | null> {
  try {
    const response = await apiClient.get<ApiResponse<FileInfo>>(`/files/${fileId}`);
    return response.data.data;
  } catch (error) {
    console.error('Failed to get file info:', error);
    return null;
  }
}

/**
 * Create file signed URL
 * @param fileId File ID to create signed URL for
 * @param expireMinutes URL expiration time in minutes (default: 15)
 * @returns Signed URL response for file download
 */
export async function createFileSignedUrl(fileId: string, expireMinutes: number = 15): Promise<SignedUrlResponse> {
  const response = await apiClient.post<ApiResponse<SignedUrlResponse>>(`/files/${fileId}/signed-url`, {
    expire_minutes: expireMinutes
  });
  return response.data.data;
}

/**
 * Get file download URL
 * @param file File info
 * @returns Promise resolving to file download URL string
 */
export async function getFileDownloadUrl(
  fileInfo: FileInfo,
): Promise<string> {
  if (fileInfo.file_url) {
    return `${API_CONFIG.host}${fileInfo.file_url}`;
  }
  const signedUrlResponse = await createFileSignedUrl(fileInfo.file_id);
  return `${API_CONFIG.host}${signedUrlResponse.signed_url}`;
}

/**
 * Fetch file content as a Blob using file_url or signed URL with authentication.
 */
export async function fetchFileBlob(fileInfo: FileInfo): Promise<Blob> {
  let requestUrl = fileInfo.file_url || '';
  if (!requestUrl) {
    const signed = await createFileSignedUrl(fileInfo.file_id);
    requestUrl = signed.signed_url;
  }
  requestUrl = requestUrl.replace(/^\/api\/v1/, '');
  const response = await apiClient.get(requestUrl, { responseType: 'blob' });
  return response.data;
}

/**
 * Download a file with authentication and trigger browser save dialog.
 * Uses apiClient (which attaches Bearer token) to fetch the file as a Blob,
 * then creates a temporary <a> element to trigger the download.
 */
export async function triggerAuthenticatedDownload(fileInfo: FileInfo): Promise<void> {
  const blob = await fetchFileBlob(fileInfo);
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fileInfo.filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
