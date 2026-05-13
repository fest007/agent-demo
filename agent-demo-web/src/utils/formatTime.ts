const BEIJING_TIMEZONE = "Asia/Shanghai";

/**
 * 格式化为固定北京时间，展示完整年月日与时分。
 */
export function formatTime(date: Date): string {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) return "";

  const parts = new Intl.DateTimeFormat("zh-CN", {
    timeZone: BEIJING_TIMEZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  })
    .formatToParts(date)
    .reduce<Record<string, string>>((acc, part) => {
      if (part.type !== "literal") acc[part.type] = part.value;
      return acc;
    }, {});

  return `${parts.year}年${parts.month}月${parts.day}日 ${parts.hour}:${parts.minute}`;
}
