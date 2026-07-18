/**
 * 从 AI 响应文本中提取 Mermaid 代码块
 * 支持多种格式：```mermaid ... ```、```mermaid\n...\n```、纯文本中的 graph/sequenceDiagram 等
 */

const MERMAID_KEYWORDS = [
  'graph ', 'flowchart ', 'sequenceDiagram', 'classDiagram',
  'stateDiagram', 'stateDiagram-v2', 'erDiagram', 'journey',
  'gantt', 'pie ', 'pie title', 'quadrantDiagram', 'xychart-beta',
  'mindmap', 'timeline', 'C4Context', 'sankey-beta',
];

/**
 * 从文本中提取第一个 Mermaid 代码块
 * 返回提取到的 mermaid 源码，或 null（没找到）
 */
export function extractMermaidCode(text: string): string | null {
  if (!text) return null;

  // 1. 优先匹配 ```mermaid ... ``` 代码块
  const mermaidBlock = text.match(/```mermaid\s*\n([\s\S]*?)```/i);
  if (mermaidBlock) {
    return mermaidBlock[1].trim();
  }

  // 2. 匹配 ```代码块（没指定语言但内容是 mermaid）
  const genericBlock = text.match(/```\s*\n?([\s\S]*?)```/i);
  if (genericBlock && isMermaidContent(genericBlock[1])) {
    return genericBlock[1].trim();
  }

  // 3. 全文检测：如果文本包含 mermaid 关键字和换行结构，尝试提取段落
  if (isMermaidContent(text)) {
    const lines = text.split('\n');
    const startIdx = lines.findIndex(l => MERMAID_KEYWORDS.some(k => l.trim().startsWith(k)));
    if (startIdx >= 0) {
      // 从关键字行开始，取连续的非空行
      const mermaidLines: string[] = [];
      for (let i = startIdx; i < lines.length; i++) {
        const line = lines[i].trim();
        if (line === '' && mermaidLines.length > 0) break;
        if (line !== '') mermaidLines.push(line);
      }
      if (mermaidLines.length >= 2) {
        return mermaidLines.join('\n');
      }
    }
  }

  return null;
}

/**
 * 判断一段文本是否像 Mermaid 语法
 */
function isMermaidContent(text: string): boolean {
  const trimmed = text.trim();
  return MERMAID_KEYWORDS.some(keyword => trimmed.startsWith(keyword));
}

/**
 * 从文本中移除 Mermaid 代码块，返回干净的对话文本
 */
export function stripMermaidFromText(text: string): string {
  if (!text) return text;

  // 移除 ```mermaid ... ```
  let result = text.replace(/```mermaid\s*\n[\s\S]*?```/gi, '');
  // 移除行末多余空行
  result = result.replace(/\n{3,}/g, '\n\n').trim();

  return result;
}
