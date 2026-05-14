import { api } from "./client";
import type { SkillInfo } from "@/types";
import type { ModelSelection } from "@/stores/appStore";

export async function listSkills(): Promise<SkillInfo[]> {
  return api.get("/skills/list");
}

export async function getSkillDetail(name: string): Promise<SkillInfo> {
  return api.get(`/skills/${name}`);
}

export async function updateSkill(name: string, data: { description?: string; content?: string }) {
  return api.put(`/skills/${name}`, data);
}

function modelPayload(selection?: ModelSelection) {
  const customBaseUrl = selection?.customBaseUrl?.trim();
  const customApiKey = selection?.customApiKey?.trim();
  return {
    model_provider: selection?.providerId,
    model: selection?.modelId,
    api_key_id: selection?.apiKeyId,
    custom_base_url: customBaseUrl || undefined,
    custom_api_key: customApiKey || undefined,
  };
}

export async function generateSkill(description: string, selection?: ModelSelection) {
  return api.post("/skills/generate", { description, ...modelPayload(selection) });
}
