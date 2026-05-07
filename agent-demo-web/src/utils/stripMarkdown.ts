/**
 * 去除 Markdown 语法，返回纯文本
 * 用于 TTS 语音合成前的文本清理
 */
export function stripMarkdown(text: string): string {
  let result = text;

  // 1. 代码块（保留内容，去掉围栏）
  result = result.replace(/```[\w]*\n?([\s\S]*?)```/g, "$1");

  // 2. 行内代码
  result = result.replace(/`([^`]+)`/g, "$1");

  // 3. 图片 ![alt](url) → alt
  result = result.replace(/!\[([^\]]*)\]\([^)]+\)/g, "$1");

  // 4. 链接 [text](url) → text
  result = result.replace(/\[([^\]]*)\]\([^)]+\)/g, "$1");

  // 5. 标题
  result = result.replace(/^#{1,6}\s+/gm, "");

  // 6. 粗体
  result = result.replace(/\*\*(.+?)\*\*/g, "$1");
  result = result.replace(/__(.+?)__/g, "$1");

  // 7. 斜体（粗体已处理，不会误匹配）
  result = result.replace(/\*(.+?)\*/g, "$1");
  result = result.replace(/_(.+?)_/g, "$1");

  // 8. 删除线
  result = result.replace(/~~(.+?)~~/g, "$1");

  // 9. 引用
  result = result.replace(/^>\s?/gm, "");

  // 10. 水平线
  result = result.replace(/^[-*_]{3,}\s*$/gm, "");

  // 11. 无序列表标记
  result = result.replace(/^[\s]*[-*+]\s+/gm, "");

  // 12. 有序列表标记
  result = result.replace(/^[\s]*\d+\.\s+/gm, "");

  // 13. 表格分隔行
  result = result.replace(/^\|?[\s-:|]+\|[\s-:|]*\|?\s*$/gm, "");

  // 14. 表格行的首尾管道符
  result = result.replace(/^\|\s*/gm, "");
  result = result.replace(/\s*\|$/gm, "");

  // 15. HTML 标签
  result = result.replace(/<[^>]+>/g, "");

  // 16. 多余空行
  result = result.replace(/\n{3,}/g, "\n\n");

  return result.trim();
}
