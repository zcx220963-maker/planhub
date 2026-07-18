/**
 * 可视化面板组件
 * - 接收 Mermaid 语法文本，渲染为流程图/时间轴/架构图等
 * - 支持缩放、拖拽、导出 SVG
 */
import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';

// Mermaid 初始化配置
mermaid.initialize({
  startOnLoad: true,
  theme: 'default',
  securityLevel: 'loose',
  flowchart: { useMaxWidth: true, htmlLabels: true, curve: 'basis' },
  themeVariables: {
    fontSize: '14px',
  },
});

interface VisualizationPanelProps {
  mermaidCode: string;
  title?: string;
  onClose?: () => void;
}

const VisualizationPanel: React.FC<VisualizationPanelProps> = ({
  mermaidCode,
  title = '可视化',
  onClose,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);

  useEffect(() => {
    if (!mermaidCode || !containerRef.current) return;

    const render = async () => {
      try {
        setError(null);
        const id = `mermaid-${Date.now()}`;
        const { svg } = await mermaid.render(id, mermaidCode);
        if (containerRef.current) {
          containerRef.current.innerHTML = svg;
        }
      } catch (err: any) {
        setError(err.message || '图表渲染失败');
        if (containerRef.current) {
          containerRef.current.innerHTML = '';
        }
      }
    };

    render();
  }, [mermaidCode]);

  const handleExportSVG = () => {
    if (!containerRef.current) return;
    const svg = containerRef.current.querySelector('svg');
    if (!svg) return;

    const serializer = new XMLSerializer();
    const svgString = serializer.serializeToString(svg);
    const blob = new Blob([svgString], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `${title || 'diagram'}.svg`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: '#ffffff',
        borderLeft: '1px solid #e5e7eb',
      }}
    >
      {/* 面板头部 */}
      <div
        style={{
          padding: '16px 20px',
          borderBottom: '1px solid #e5e7eb',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '20px' }}>📊</span>
          <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: '#111827' }}>
            {title}
          </h3>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {/* 缩放控制 */}
          <button
            onClick={() => setZoom(z => Math.max(0.5, z - 0.1))}
            style={btnStyle}
            title="缩小"
          >
            ➖
          </button>
          <span style={{ fontSize: '13px', color: '#6b7280', minWidth: '40px', textAlign: 'center' }}>
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={() => setZoom(z => Math.min(2, z + 0.1))}
            style={btnStyle}
            title="放大"
          >
            ➕
          </button>
          {/* 重置 */}
          <button
            onClick={() => setZoom(1)}
            style={btnStyle}
            title="重置缩放"
          >
            🔄
          </button>
          {/* 导出 */}
          <button
            onClick={handleExportSVG}
            style={{ ...btnStyle, backgroundColor: '#eff6ff', color: '#3b82f6' }}
            title="导出 SVG"
          >
            💾
          </button>
          {/* 关闭 */}
          {onClose && (
            <button
              onClick={onClose}
              style={{ ...btnStyle, backgroundColor: '#fef2f2', color: '#dc2626' }}
              title="关闭"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* 渲染区域 */}
      <div
        style={{
          flex: 1,
          overflow: 'auto',
          padding: '24px',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'flex-start',
          backgroundColor: '#fcfcfd',
        }}
      >
        {error ? (
          <div
            style={{
              padding: '20px',
              backgroundColor: '#fef2f2',
              borderRadius: '8px',
              color: '#dc2626',
              fontSize: '14px',
              maxWidth: '400px',
            }}
          >
            <strong>渲染失败：</strong>
            <br />
            {error}
          </div>
        ) : (
          <div
            ref={containerRef}
            style={{
              transform: `scale(${zoom})`,
              transformOrigin: 'top center',
              transition: 'transform 0.2s',
            }}
          />
        )}
      </div>
    </div>
  );
};

const btnStyle: React.CSSProperties = {
  padding: '4px 8px',
  backgroundColor: '#f3f4f6',
  color: '#374151',
  border: 'none',
  borderRadius: '6px',
  cursor: 'pointer',
  fontSize: '14px',
  fontWeight: 500,
  transition: 'all 0.2s',
};

export default VisualizationPanel;
