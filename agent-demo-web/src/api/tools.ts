import { api } from "./client";

/** 获取所有工具的启用状态 */
export async function listTools(): Promise<Record<string, boolean>> {
  return api.get("/tools/list");
}

/** 切换工具启用/禁用状态 */
export async function toggleTool(toolName: string, enable: boolean) {
  return api.put(`/tools/${toolName}/toggle?enable=${enable}`);
}
