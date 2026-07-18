/**
 * Plan Visualization Panel — 杂志风通用计划可视化面板
 *
 * 将 AI 生成的计划文本解析为精美杂志页面
 * 适用于：旅行、学习、健身、工作、项目等任意类型计划
 *
 * 特点：
 * - 大标题 Hero 区
 * - 章节卡片式布局
 * - 优雅排版 + 留白
 * - 流式实时渲染（逐字生长）
 */
import React, { useMemo } from 'react';

interface PlanVisualizationPanelProps {
  planText: string;
  isStreaming?: boolean;
  title?: string;
  onClose?: () => void;
}

// ─── 解析计划文本为结构化数据 ────────────────────────────────────────────────

interface PlanSection {
  heading: string;       // 标题（如"第一天"、"准备阶段"）
  subheading?: string;   // 副标题（日期、地点等）
  bullets: string[];     // 列表项
  paragraphs: string[];  // 纯文本段落
}

interface ParsedPlan {
  title: string;                // 主标题
  subtitle?: string;            // 副标题
  sections: PlanSection[];      // 各章节
  footer: string[];             // 底部注意事项等
}

function parsePlan(text: string): ParsedPlan {
  const lines = text.split('\n').map(l => l.trimEnd());

  let title = '';
  let subtitle = '';
  const sections: PlanSection[] = [];
  const footer: string[] = [];

  let current: PlanSection | null = null;
  let inFooter = false;

  for (const line of lines) {
    // h1 → 主标题
    const h1 = line.match(/^#\s+(.+)$/);
    if (h1 && !title) {
      title = cleanMd(h1[1]);
      continue;
    }

    // h2 → 新章节
    const h2 = line.match(/^##\s+(.+)$/);
    if (h2) {
      if (current) sections.push(current);
      current = { heading: cleanMd(h2[1]), bullets: [], paragraphs: [] };
      // 检测副标题（括号内容或日期）
      const subMatch = current.heading.match(/[（(](.+?)[）)]/);
      if (subMatch) {
        current.subheading = subMatch[1];
        current.heading = current.heading.replace(/[（(].+?[）)]/, '').trim();
      }
      inFooter = /注意|准备|提醒|tips|summary/i.test(current.heading);
      continue;
    }

    // h3 → 子标题（归入当前章节的段落）
    const h3 = line.match(/^###\s+(.+)$/);
    if (h3 && current) {
      current.paragraphs.push(`**${cleanMd(h3[1])}**`);
      continue;
    }

    // 分割线 → 标记底部区域
    if (/^---+$/.test(line)) {
      if (current) { sections.push(current); current = null; }
      inFooter = true;
      continue;
    }

    // 列表项
    const bullet = line.match(/^[-*+]\s+(.+)$/) || line.match(/^\d+\.\s+(.+)$/);
    if (bullet) {
      const item = cleanMd(bullet[1]);
      if (inFooter) {
        footer.push(item);
      } else if (current) {
        current.bullets.push(item);
      }
      continue;
    }

    // 空行跳过
    if (!line.trim()) continue;

    // 普通段落
    const cleaned = cleanMd(line);
    if (!cleaned) continue;

    if (!title && !current) {
      // 第一个非空行且还没标题 → 可能是主标题
      title = cleaned;
    } else if (inFooter) {
      footer.push(cleaned);
    } else if (current) {
      current.paragraphs.push(cleaned);
    } else if (!subtitle) {
      subtitle = cleaned;
    }
  }

  if (current) sections.push(current);

  return { title, subtitle, sections, footer };
}

function cleanMd(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank">$1</a>')
    .trim();
}

// ─── 提取关键信息（用于 Hero 区统计）─────────────────────────────────────────

function extractStats(sections: PlanSection[]): { label: string; value: string }[] {
  const stats: { label: string; value: string }[] = [];

  // 尝试提取天数/阶段数
  const dayCount = sections.filter(s =>
    /天|日|day|阶段|周|step|phase/i.test(s.heading)
  ).length;
  if (dayCount > 0) stats.push({ label: '阶段', value: `${dayCount}` });

  // 提取列表项总数
  const totalItems = sections.reduce((sum, s) => sum + s.bullets.length, 0);
  if (totalItems > 0) stats.push({ label: '任务', value: `${totalItems}` });

  return stats;
}

// ─── 配色方案（按章节循环）───────────────────────────────────────────────────

const SECTION_ACCOLORS = [
  { bg: '#eef2ff', border: '#6366f1', dot: '#6366f1' },  // 靛蓝
  { bg: '#ecfdf5', border: '#10b981', dot: '#10b981' },  // 翠绿
  { bg: '#fef3c7', border: '#f59e0b', dot: '#f59e0b' },  // 琥珀
  { bg: '#fce7f3', border: '#ec4899', dot: '#ec4899' },  // 粉红
  { bg: '#e0e7ff', border: '#8b5cf6', dot: '#8b5cf6' },  // 紫罗兰
  { bg: '#cffafe', border: '#06b6d4', dot: '#06b6d4' },  // 青色
];

// ─── 样式 ─────────────────────────────────────────────────────────────────────

const STYLES = `
.magazine-page {
  --font-serif: 'Georgia', 'Noto Serif SC', 'Source Han Serif SC', serif;
  --font-sans: -apple-system, 'SF Pro Display', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  --gray-900: #1a1a2e;
  --gray-700: #374151;
  --gray-500: #6b7280;
  --gray-300: #d1d5db;
  --gray-100: #f3f4f6;
  --white: #ffffff;

  font-family: var(--font-sans);
  color: var(--gray-900);
  line-height: 1.75;
  max-width: 680px;
  margin: 0 auto;
  padding: 0 0 60px 0;
}

/* ── Hero 区 ─────────────────────────────── */
.mag-hero {
  padding: 48px 36px 36px;
  text-align: center;
  position: relative;
}
.mag-hero::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 60px;
  height: 3px;
  background: linear-gradient(90deg, #6366f1, #ec4899);
  border-radius: 2px;
}
.mag-hero-title {
  font-family: var(--font-serif);
  font-size: 32px;
  font-weight: 800;
  color: var(--gray-900);
  margin: 0 0 12px 0;
  letter-spacing: -0.02em;
  line-height: 1.3;
}
.mag-hero-subtitle {
  font-size: 15px;
  color: var(--gray-500);
  margin: 0;
  font-weight: 400;
  letter-spacing: 0.02em;
}
.mag-hero-stats {
  display: flex;
  justify-content: center;
  gap: 32px;
  margin-top: 24px;
}
.mag-stat {
  text-align: center;
}
.mag-stat-value {
  font-size: 28px;
  font-weight: 800;
  color: #6366f1;
  font-family: var(--font-serif);
}
.mag-stat-label {
  font-size: 11px;
  color: var(--gray-500);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 600;
  margin-top: 2px;
}

/* ── 章节卡片 ────────────────────────────── */
.mag-section {
  margin: 36px 24px 0;
  padding: 28px 28px 24px;
  border-radius: 16px;
  border: 1px solid var(--gray-100);
  background: var(--white);
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  transition: box-shadow 0.2s;
}
.mag-section:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
}
.mag-section-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.mag-section-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.mag-section-title {
  font-family: var(--font-serif);
  font-size: 20px;
  font-weight: 700;
  color: var(--gray-900);
  margin: 0;
}
.mag-section-sub {
  font-size: 13px;
  color: var(--gray-500);
  margin-left: auto;
  font-weight: 500;
  background: var(--gray-100);
  padding: 3px 10px;
  border-radius: 20px;
  white-space: nowrap;
}

/* ── 列表项 ─────────────────────────────── */
.mag-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.mag-list li {
  position: relative;
  padding: 8px 0 8px 20px;
  font-size: 15px;
  color: var(--gray-700);
  line-height: 1.7;
  border-bottom: 1px solid #f9fafb;
}
.mag-list li:last-child {
  border-bottom: none;
}
.mag-list li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 16px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--dot-color, #6366f1);
  opacity: 0.7;
}

/* ── 段落 ───────────────────────────────── */
.mag-paragraph {
  font-size: 15px;
  color: var(--gray-700);
  margin: 0 0 10px 0;
  line-height: 1.8;
}
.mag-paragraph strong {
  color: var(--gray-900);
}

/* ── 底部区 ─────────────────────────────── */
.mag-footer {
  margin: 40px 24px 0;
  padding: 24px 28px;
  background: linear-gradient(135deg, #f8fafc, #f1f5f9);
  border-radius: 16px;
  border: 1px solid #e2e8f0;
}
.mag-footer-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--gray-900);
  margin: 0 0 12px 0;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.mag-footer ul {
  list-style: none;
  margin: 0;
  padding: 0;
}
.mag-footer li {
  font-size: 13px;
  color: var(--gray-500);
  padding: 5px 0 5px 16px;
  position: relative;
  line-height: 1.6;
}
.mag-footer li::before {
  content: '·';
  position: absolute;
  left: 0;
  color: var(--gray-500);
  font-weight: 700;
}

/* ── 流式光标 ──────────────────────────── */
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
.mag-cursor {
  display: inline-block;
  width: 2px;
  height: 20px;
  background: #6366f1;
  margin-left: 2px;
  vertical-align: text-bottom;
  animation: blink 1s infinite;
}

/* ── 空状态 ────────────────────────────── */
.mag-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--gray-300);
  gap: 16px;
  padding: 40px;
  text-align: center;
}
.mag-empty-icon { font-size: 56px; opacity: 0.25; }
.mag-empty p { font-size: 14px; color: var(--gray-500); margin: 0; }
`;

// ─── 组件 ─────────────────────────────────────────────────────────────────────

const PlanVisualizationPanel: React.FC<PlanVisualizationPanelProps> = ({
  planText,
  isStreaming = false,
  title = '计划预览',
  onClose,
}) => {
  const parsed = useMemo(() => parsePlan(planText), [planText]);
  const stats = useMemo(() => extractStats(parsed.sections), [parsed.sections]);

  return (
    <div style={panelContainerStyle}>
      <style>{STYLES}</style>

      {/* 头部 */}
      <div style={headerStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 20 }}>📰</span>
          <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: '#1a1a2e' }}>
            {title}
          </h3>
          {isStreaming && (
            <span style={streamingBadge}>生成中...</span>
          )}
        </div>
        {onClose && (
          <button onClick={onClose} style={closeBtnStyle}>✕</button>
        )}
      </div>

      {/* 内容 */}
      <div style={contentStyle}>
        {parsed.title ? (
          <div className="magazine-page">

            {/* Hero */}
            <div className="mag-hero">
              <h1
                className="mag-hero-title"
                dangerouslySetInnerHTML={{ __html: parsed.title + (isStreaming ? '<span class="mag-cursor"></span>' : '') }}
              />
              {parsed.subtitle && (
                <p className="mag-hero-subtitle" dangerouslySetInnerHTML={{ __html: parsed.subtitle }} />
              )}
              {stats.length > 0 && (
                <div className="mag-hero-stats">
                  {stats.map((s, i) => (
                    <div key={i} className="mag-stat">
                      <div className="mag-stat-value">{s.value}</div>
                      <div className="mag-stat-label">{s.label}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 章节 */}
            {parsed.sections.map((sec, idx) => {
              const color = SECTION_ACCOLORS[idx % SECTION_ACCOLORS.length];
              return (
                <div key={idx} className="mag-section">
                  <div className="mag-section-head">
                    <div className="mag-section-dot" style={{ background: color.dot }} />
                    <h2
                      className="mag-section-title"
                      dangerouslySetInnerHTML={{ __html: sec.heading }}
                    />
                    {sec.subheading && (
                      <span className="mag-section-sub">{sec.subheading}</span>
                    )}
                  </div>
                  {sec.paragraphs.length > 0 && (
                    <div style={{ marginBottom: sec.bullets.length > 0 ? 12 : 0 }}>
                      {sec.paragraphs.map((p, pi) => (
                        <p
                          key={pi}
                          className="mag-paragraph"
                          dangerouslySetInnerHTML={{ __html: p }}
                        />
                      ))}
                    </div>
                  )}
                  {sec.bullets.length > 0 && (
                    <ul className="mag-list">
                      {sec.bullets.map((b, bi) => (
                        <li
                          key={bi}
                          style={{ '--dot-color': color.dot }}
                          dangerouslySetInnerHTML={{ __html: b }}
                        />
                      ))}
                    </ul>
                  )}
                </div>
              );
            })}

            {/* 底部 */}
            {parsed.footer.length > 0 && (
              <div className="mag-footer">
                <div className="mag-footer-title">▎重要提醒</div>
                <ul>
                  {parsed.footer.map((f, fi) => (
                    <li key={fi} dangerouslySetInnerHTML={{ __html: f }} />
                  ))}
                </ul>
              </div>
            )}

          </div>
        ) : (
          <div className="mag-empty">
            <span className="mag-empty-icon">★</span>
            <p>计划生成后，这里会实时展示杂志风格的预览页面</p>
            <p style={{ fontSize: 12, color: '#94a3b8' }}>支持任意类型的计划</p>
          </div>
        )}
      </div>
    </div>
  );
};

// ─── 样式常量 ─────────────────────────────────────────────────────────────────

const panelContainerStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  height: '100%',
  backgroundColor: '#fcfcfd',
  borderLeft: '1px solid #e5e7eb',
};

const headerStyle: React.CSSProperties = {
  padding: '14px 20px',
  borderBottom: '1px solid #e5e7eb',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  flexShrink: 0,
  background: 'white',
};

const streamingBadge: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 600,
  color: 'white',
  background: 'linear-gradient(135deg, #6366f1, #ec4899)',
  padding: '3px 10px',
  borderRadius: 20,
  letterSpacing: 0.5,
};

const closeBtnStyle: React.CSSProperties = {
  padding: '4px 10px',
  backgroundColor: '#fef2f2',
  color: '#dc2626',
  border: 'none',
  borderRadius: 6,
  cursor: 'pointer',
  fontSize: 14,
  fontWeight: 600,
};

const contentStyle: React.CSSProperties = {
  flex: 1,
  overflow: 'auto',
};

export default PlanVisualizationPanel;
