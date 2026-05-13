export function statusText(status: string) {
  if (status === "succeeded") return "已完成";
  if (status === "failed") return "失败";
  if (status === "running") return "生成中";
  return "排队中";
}

export function statusColor(status: string) {
  if (status === "succeeded") return "green";
  if (status === "failed") return "red";
  if (status === "running") return "blue";
  return "default";
}
