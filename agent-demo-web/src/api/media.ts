import { api } from "./client";
import type { MediaTask } from "@/types";

export async function getMediaTask(taskId: string): Promise<MediaTask> {
  return api.get(`/media/tasks/${taskId}`);
}

export async function listMediaTasks(statuses = "pending,running"): Promise<{ tasks: MediaTask[] }> {
  return api.get(`/media/tasks?statuses=${encodeURIComponent(statuses)}`);
}
