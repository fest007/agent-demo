/**
 * 格式化时间为人类友好的字符串
 * 近期用相对时间，较久用绝对时间
 */
export function formatTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);

  if (diffSec < 60) return "刚刚";
  if (diffMin < 60) return `${diffMin}分钟前`;

  const timeStr = date.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

  if (diffHour < 24) return timeStr;

  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const msgDay = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const diffDay = Math.floor(
    (today.getTime() - msgDay.getTime()) / (1000 * 60 * 60 * 24)
  );

  if (diffDay === 1) return `昨天 ${timeStr}`;
  if (diffDay < 7) return `${diffDay}天前`;

  return (
    date.toLocaleDateString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
    }) +
    " " +
    timeStr
  );
}
