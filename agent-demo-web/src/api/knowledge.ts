import { api } from "./client";
import type { KnowledgeDocument } from "@/types";

export async function uploadFile(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  // uploadFile 直接用 fetch（FormData 不能走 JSON 的 api 封装）
  const resp = await fetch("/api/knowledge/upload", { method: "POST", body: formData });
  return resp.json();
}

export async function ingestUrl(url: string) {
  return api.post("/knowledge/ingest-url", { url });
}

export async function ingestText(text: string, source: string = "manual") {
  return api.post("/knowledge/ingest-text", { text, source });
}

export async function listDocuments(): Promise<KnowledgeDocument[]> {
  return api.get("/knowledge/list");
}

export async function deleteDocument(source: string) {
  return api.delete(`/knowledge?source=${encodeURIComponent(source)}`);
}
