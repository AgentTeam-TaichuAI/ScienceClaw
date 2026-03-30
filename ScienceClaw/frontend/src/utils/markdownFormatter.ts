/**
 * Markdown 格式化工具
 * 对 LLM 输出的 Markdown 进行预处理和清理
 */

/**
 * 预处理 Markdown 文本，修复 LLM 输出中的常见格式问题
 * @param text 原始 Markdown 文本
 * @returns 格式化后的 Markdown 文本
 */
export function formatMarkdown(text: string): string {
  if (!text || typeof text !== 'string') {
    return '';
  }
  return preprocessMarkdown(text);
}

/**
 * 同步版本（与异步版本相同，保持 API 兼容）
 */
export function formatMarkdownSync(text: string): string {
  return formatMarkdown(text);
}

const TABLE_ROW_PATTERN = new RegExp(`^\\|.*\\|$`);
const TABLE_DIVIDER_PATTERN = new RegExp(
  `^\\|[${['-', ':', '\\s', '\\|'].join('')}]+\\|$`,
);

/**
 * 预处理：清理 LLM 输出中的常见问题
 */
function preprocessMarkdown(text: string): string {
  let result = text;

  // 1. 移除开头的 ```markdown 或 ``` 标记（LLM 有时会错误地包裹整个输出）
  result = result.replace(/^```(?:markdown|md)?\s*\n?/i, '');
  result = result.replace(/\n?```\s*$/i, '');

  // 2. 修复连续的空行（超过2个空行压缩为2个）
  result = result.replace(/\n{3,}/g, '\n\n');

  // 3. 统一列表标记为 -
  result = result.replace(/^(\s*)[*+]\s/gm, '$1- ');

  // 4. 修复列表项的多余空格
  result = result.replace(/^(\s*)-\s{2,}/gm, '$1- ');

  // 5. 修复有序列表的空格
  result = result.replace(/^(\s*)(\d+)\.\s{2,}/gm, '$1$2. ');

  // 6. 确保标题前后有适当的空行
  result = result.replace(/([^\n])\n(#{1,6}\s)/g, '$1\n\n$2');
  result = result.replace(/(^#{1,6}\s[^\n]+)\n([^\n#])/gm, '$1\n\n$2');

  // 7. 修复代码块的语言标识符
  result = result.replace(/```(\w+)(\s*)\n/g, (_, lang) => '```' + lang.toLowerCase() + '\n');

  // 8. 修复行内代码的多余空格
  result = result.replace(/`\s+([^`]+?)\s+`/g, '`$1`');

  // 9. 修复链接格式
  result = result.replace(/\[([^\]]+)\]\s*\(\s*([^)\s]+)\s*\)/g, '[$1]($2)');

  // 10. 确保代码块闭合
  const codeBlockCount = (result.match(/```/g) || []).length;
  if (codeBlockCount % 2 !== 0) {
    result += '\n```';
  }

  // 11. 移除标点符号前的多余空格
  result = result.replace(/\s+([.,!?;:])/g, '$1');

  // 12. 修复表格格式
  result = normalizeTables(result);

  // 13. 确保引用块格式正确
  result = result.replace(/^>(\s*)(\S)/gm, '> $2');

  return result.trim();
}

/**
 * 规范化表格格式
 */
function normalizeTables(text: string): string {
  const lines = text.split('\n');
  const result: string[] = [];
  let inTable = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmedLine = line.trim();
    const isTableRow = TABLE_ROW_PATTERN.test(trimmedLine);
    const isTableDivider = TABLE_DIVIDER_PATTERN.test(trimmedLine);

    if (isTableRow || isTableDivider) {
      if (!inTable) {
        // 确保表格前有空行
        if (result.length > 0 && result[result.length - 1].trim() !== '') {
          result.push('');
        }
        inTable = true;
      }
      result.push(line);
    } else {
      if (inTable) {
        // 确保表格后有空行
        if (line.trim() !== '') {
          result.push('');
        }
        inTable = false;
      }
      result.push(line);
    }
  }

  return result.join('\n');
}

/**
 * 清理 Markdown 中的 XML 标签（如 <suggested_questions>）
 */
export function extractXmlTags(text: string): {
  cleanedText: string;
  tags: Record<string, string>;
} {
  const tags: Record<string, string> = {};
  let cleanedText = text;

  // 提取并移除 suggested_questions 标签
  const suggestionRegex = /<suggested_questions>([\s\S]*?)<\/suggested_questions>/;
  const match = cleanedText.match(suggestionRegex);
  if (match) {
    tags.suggested_questions = match[1];
    cleanedText = cleanedText.replace(suggestionRegex, '');
  }

  return { cleanedText, tags };
}

export default {
  formatMarkdown,
  formatMarkdownSync,
  extractXmlTags,
};
