/**
 * Webhook management API (via task-service).
 */
import axios from 'axios';
import { getStoredToken } from './auth';

const TASK_SERVICE_BASE =
  (import.meta as any).env?.VITE_TASK_SERVICE_URL ?? '';

const client = axios.create({
  baseURL: TASK_SERVICE_BASE || '/task-service',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

client.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export type WebhookType = 'feishu' | 'dingtalk' | 'wecom' | 'telegram';

export interface TelegramWebhookConfigPublic {
  chat_id: string;
  has_bot_token: boolean;
  bot_token_masked: string;
}

export interface TelegramWebhookConfigInput {
  bot_token?: string;
  chat_id: string;
}

export interface Webhook {
  id: string;
  name: string;
  type: WebhookType;
  url: string;
  config: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface WebhookCreatePayload {
  name: string;
  type: WebhookType;
  url?: string;
  config?: Record<string, any>;
}

export interface WebhookUpdatePayload {
  name?: string;
  type?: WebhookType;
  url?: string;
  config?: Record<string, any>;
}

export async function listWebhooks(): Promise<Webhook[]> {
  const { data } = await client.get<Webhook[]>('/webhooks');
  return Array.isArray(data) ? data : [];
}

export async function createWebhook(payload: WebhookCreatePayload): Promise<Webhook> {
  const { data } = await client.post<Webhook>('/webhooks', payload);
  return data;
}

export async function updateWebhook(id: string, payload: WebhookUpdatePayload): Promise<Webhook> {
  const { data } = await client.put<Webhook>(`/webhooks/${id}`, payload);
  return data;
}

export async function deleteWebhook(id: string): Promise<void> {
  await client.delete(`/webhooks/${id}`);
}

export async function testWebhook(id: string): Promise<{ success: boolean; message: string }> {
  const { data } = await client.post<{ success: boolean; message: string }>(`/webhooks/${id}/test`);
  return data;
}
