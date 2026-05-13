import { api } from "./client";

export interface ApiKeyInfo {
  id: string;
  label: string;
  masked: string;
  provider: string;
}

export interface ModelInfo {
  id: string;
  label: string;
  purpose: string;
}

export interface ModelProviderInfo {
  id: string;
  label: string;
  base_url: string;
  keys: ApiKeyInfo[];
  models: ModelInfo[];
  default_model: string;
  fast_model: string;
  omni_model: string;
  quota_supported: boolean;
}

export interface QuotaResponse {
  provider: string;
  key_id: string;
  key_label: string;
  supported: boolean;
  status: string;
  total?: number | null;
  used?: number | null;
  remaining?: number | null;
  percent_remaining?: number | null;
  unit: string;
  message: string;
  raw?: Record<string, unknown>;
}

export interface RemoteModelInfo {
  id: string;
  label: string;
  capability: string;
  chat_supported: boolean;
  image_supported: boolean;
  video_supported: boolean;
  note: string;
}

export interface ModelListResponse {
  provider: string;
  base_url: string;
  status: string;
  message: string;
  models: RemoteModelInfo[];
}

export async function listApiKeys(): Promise<ApiKeyInfo[]> {
  return api.get("/settings/api-keys");
}

export async function listModelProviders(): Promise<ModelProviderInfo[]> {
  return api.get("/settings/model-providers");
}

export async function queryQuota(params: {
  keyId?: string;
  provider?: string;
  customBaseUrl?: string;
  customApiKey?: string;
}): Promise<QuotaResponse> {
  return api.post("/settings/quota", {
    key_id: params.keyId || "default",
    provider: params.provider || "mimo",
    custom_base_url: params.customBaseUrl,
    custom_api_key: params.customApiKey,
  });
}

export async function fetchRemoteModels(params: {
  provider: string;
  keyId?: string;
  customBaseUrl?: string;
  customApiKey?: string;
}): Promise<ModelListResponse> {
  return api.post("/settings/models", {
    provider: params.provider,
    key_id: params.keyId || "default",
    custom_base_url: params.customBaseUrl,
    custom_api_key: params.customApiKey,
  });
}
