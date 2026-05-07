import { api } from "./client";
import type { SkillInfo } from "@/types";

export async function listSkills(): Promise<SkillInfo[]> {
  return api.get("/skills/list");
}

export async function getSkillDetail(name: string): Promise<SkillInfo> {
  return api.get(`/skills/${name}`);
}

export async function updateSkill(name: string, data: { description?: string; content?: string }) {
  return api.put(`/skills/${name}`, data);
}

export async function generateSkill(description: string) {
  return api.post("/skills/generate", { description });
}
