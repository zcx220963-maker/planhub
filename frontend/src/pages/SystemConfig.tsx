import React, { useState, useEffect } from 'react';
import { Settings, Database, Shield, Cpu, CheckCircle, XCircle, Server, KeyRound, FileKey, Bot, HelpCircle } from 'lucide-react';

interface ConfigResponse {
  application?: { name?: string; profile?: string; port?: string };
  database?: { url_type?: string; url_masked?: string };
  ai_service?: {
    service_url?: string;
    internal_secret_configured?: boolean;
    internal_secret_header_name?: string;
  };
  security?: { jwt_secret_configured?: boolean; auth_mode?: string };
  features?: {
    rag_enabled?: boolean; ai_assistant_enabled?: boolean; chat_bot_enabled?: boolean;
  };
}

interface HealthResponse {
  status?: string;
  ai_service_reachable?: boolean;
}

const SystemConfig: React.FC = () => {
  const [config, setConfig] = useState<ConfigResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0'
    };
    if (token) headers['Authorization'] = 'Bearer ' + token;

    Promise.all([
      fetch('/api/config?t=' + Date.now(), { headers }).then(r => r.json()).catch(() => null),
      fetch('/api/config/health?t=' + Date.now(), { headers }).then(r => r.json()).catch(() => null),
    ]).then(([cfg, hlth]) => {
      console.log('Config API response:', cfg);
      console.log('Health API response:', hlth);
      setConfig(cfg);
      setHealth(hlth);
      setLoading(false);
    }).catch(err => {
      console.error('Failed to fetch config:', err);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>加载中...</div>;
  }

  return (
    <div style={{
      maxWidth: 960,
      margin: '0 auto',
      padding: '2rem',
      background: '#f8f9fa'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <Settings size={28} color="#333" />
        <h2 style={{ margin: 0, fontSize: 24 }}>系统配置</h2>
        <span style={{
          marginLeft: 'auto',
          padding: '4px 12px',
          fontSize: 12,
          color: '#15803d',
          background: '#dcfce7',
          borderRadius: 999,
          fontWeight: 600
        }}>
          只读 · 不可修改
        </span>
      </div>

      {/* 应用信息 */}
      <Card title="应用信息" icon={Server}>
        <Row label="应用名称" value={config?.application?.name} />
        <Row label="运行环境 (Profile)" value={config?.application?.profile} highlight />
        <Row label="服务端口" value={config?.application?.port} />
      </Card>

      {/* 数据库 */}
      <Card title="数据库" icon={Database}>
        <Row label="类型" value={config?.database?.url_type} />
        <Row label="连接地址 (已脱敏)" value={config?.database?.url_masked} mono />
      </Card>

      {/* AI 服务 */}
      <Card title="AI 服务" icon={Bot}>
        <Row label="AI 服务地址" value={config?.ai_service?.service_url} />
        <Row label="内部密钥 Header" value={config?.ai_service?.internal_secret_header_name} mono />
        <Row
          label="内部密钥状态"
          value={
            config?.ai_service?.internal_secret_configured ? '已配置 ✓' : '未配置 ⚠'}
          highlight={config?.ai_service?.internal_secret_configured ? true : false}
        />
        <Row
          label="AI 服务连通性"
          value={
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {health?.ai_service_reachable ? (
              <>
                <CheckCircle size={16} color="#16a34a" />
                <span style={{ color: '#16a34a' }}>正常</span>
              </>
            ) : (
              <>
                <XCircle size={16} color="#dc2626" />
                <span style={{ color: '#dc2626' }}>无法连接</span>
              </>
            )}
          </span>
          }
        />
      </Card>

      {/* 安全配置 */}
      <Card title="安全" icon={Shield}>
        <Row
          label="JWT 密钥"
          value={
            config?.security?.jwt_secret_configured ? '已配置 ✓' : '未配置'}
          highlight={config?.security?.jwt_secret_configured ? true : false}
        />
        <Row label="认证方式" value={config?.security?.auth_mode} mono />
      </Card>

      {/* 特性开关 */}
      <Card title="功能模块" icon={Cpu}>
        <FeatureRow label="RAG 知识库检索" enabled={config?.features?.rag_enabled} />
        <FeatureRow label="智能助手" enabled={config?.features?.ai_assistant_enabled} />
        <FeatureRow label="对话机器人" enabled={config?.features?.chat_bot_enabled} />
      </Card>

      <div style={{
        marginTop: 24,
        padding: 16,
        fontSize: 13,
        color: '#6b7280',
        background: '#fff',
        border: '1px solid #e5e7eb',
        borderRadius: 8
      }}>
        <HelpCircle size={16} style={{ verticalAlign: 'middle', marginRight: 8 }} />
        <strong>关于安全说明：</strong>
        所有密钥在当前页面不会泄露任何真实值，只展示"是否已配置"；
        密钥文件由管理员在服务端配置，前端无权访问。
      </div>
    </div>
  );
};

// ─── 小组件 ─────────────────────────────────────

const Card: React.FC<{
  title: string;
  icon: React.FC<{ size?: number; color?: string }>;
  children: React.ReactNode;
}> = ({ title, icon: Icon, children }) => (
  <div style={{
    background: '#ffffff',
    borderRadius: 12,
    border: '1px solid #e5e7eb',
    padding: '1.25rem 1.5rem',
    marginBottom: 16,
  }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
      <Icon size={18} color="#475569" />
      <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: '#1f2937' }}>{title}</h3>
    </div>
    {children}
  </div>
);

const Row: React.FC<{ label: string; value: React.ReactNode; highlight?: boolean; mono?: boolean }> = ({
  label, value, highlight, mono
}) => (
  <div style={{
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    padding: '10px 0', borderBottom: '1px dashed #f0f0f0'
  }}>
    <span style={{ fontSize: 14, color: '#6b7280' }}>{label}</span>
    <span style={{
      fontSize: 14,
      fontFamily: mono ? 'monospace' : 'inherit',
      color: highlight ? '#16a34a' : '#111827',
      maxWidth: '60%',
      textAlign: 'right',
      wordBreak: 'break-all'
    }}>{typeof value === 'string' && !value ? '—' : value}</span>
  </div>
);

const FeatureRow: React.FC<{ label: string; enabled?: boolean }> = ({ label, enabled }) => (
  <div style={{
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '10px 0', borderBottom: '1px dashed #f0f0f0'
  }}>
    <span style={{ fontSize: 14, color: '#374151' }}>{label}</span>
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      fontSize: 13, color: enabled ? '#16a34a' : '#dc2626'
    }}>
      {enabled ? '已启用' : '未启用'}
    </span>
  </div>
);

export default SystemConfig;
