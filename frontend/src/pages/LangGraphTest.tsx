import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  Zap,
  ArrowLeft,
  Loader2,
  Bot,
  Target,
  MessageSquare,
  Search,
  History,
  Trash2,
  Settings,
  Activity,
  ChevronRight,
  Shield,
  AlertTriangle,
  Plus,
  BookOpen,
  X
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import DocumentManager from '../components/DocumentManager';

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
  intent?: string;
  confidence?: number;
  executionTrace?: any[];
  blockedByCapability?: boolean;
  handoffReason?: string;
}

interface DebugInfo {
  intent: string;
  confidence: number;
  selectedAgent: string;
  blockedByCapability: boolean;
  handoffReason?: string;
  executionTrace: any[];
  toolsCalled: string[];
  sessionId: string;
}

const LangGraphTest = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const AI_API_BASE = 'http://localhost:8080/api/ai';
  const CONVERSATIONS_API = 'http://localhost:8080/api/ai/conversations';
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 知识库相关状态
  const [documents, setDocuments] = useState<any[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<number[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [showDocPanel, setShowDocPanel] = useState(false);

  // 获取用户头像URL
  const getFullAvatarUrl = (avatarUrl?: string) => {
    if (!avatarUrl) return null;
    if (avatarUrl.startsWith('http')) return avatarUrl;
    if (avatarUrl.startsWith('/')) return `http://localhost:8080${avatarUrl}`;
    return `http://localhost:8080/${avatarUrl}`;
  };

  // 获取带JWT Token的请求Header
  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    const headers = new Headers();
    headers.set('Content-Type', 'application/json');
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    return headers;
  };

  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: '您好！我是 LangGraph 智能助手，可以帮您处理以下任务：\n\n制定计划\n  - "帮我制定一个Python学习计划"\n  - "制定旅行计划"\n\n搜索和查询\n  - "搜索学习计划"\n  - "查询知识库关于XXX的文档"\n\n发帖和打卡\n  - "帮我发帖，内容：今天完成了健身"\n  - "我要打卡"\n\n其他问题\n  - 任何日常对话或问题\n\n请告诉我您需要什么帮助？'
    }
  ]);
  const [sessionId, setSessionId] = useState<string>('');
  const [debugInfo, setDebugInfo] = useState<DebugInfo | null>(null);
  const [showDebug, setShowDebug] = useState(false);
  const [showHistory, setShowHistory] = useState(true);
  const [conversations, setConversations] = useState<any[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  useEffect(() => {
    loadConversations();
    loadDocuments();
  }, []);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 加载文档列表
  const loadDocuments = async () => {
    try {
      const response = await fetch(`${AI_API_BASE}/rag/documents`, {
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        setDocuments(data.documents || []);
      }
    } catch (error) {
      console.error('Load documents error:', error);
    }
  };

  // 上传文档
  const handleUploadDocuments = async (files: FileList) => {
    setIsUploading(true);
    try {
      const formData = new FormData();
      for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
      }

      const response = await fetch(`${AI_API_BASE}/rag/upload/batch`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: formData,
      });

      if (response.ok) {
        const result = await response.json();
        alert(result.message || '文档上传成功！');
        loadDocuments();
      } else {
        alert('文档上传失败，请稍后再试。');
      }
    } catch (error) {
      console.error('Upload documents error:', error);
      alert('文档上传失败，请稍后再试。');
    } finally {
      setIsUploading(false);
    }
  };

  // 删除文档
  const handleDeleteDocument = async (docId: number) => {
    try {
      const response = await fetch(`${AI_API_BASE}/rag/documents/${docId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        loadDocuments();
        setSelectedDocIds(prev => prev.filter(id => id !== docId));
      } else {
        alert('删除失败，请稍后再试。');
      }
    } catch (error) {
      console.error('Delete document error:', error);
      alert('删除失败，请稍后再试。');
    }
  };

  // 切换文档选择
  const toggleDocSelection = (docId: number) => {
    setSelectedDocIds(prev => {
      if (prev.includes(docId)) {
        return prev.filter(id => id !== docId);
      } else {
        return [...prev, docId];
      }
    });
  };

  // 全选/取消全选
  const toggleSelectAll = () => {
    if (selectedDocIds.length === documents.length) {
      setSelectedDocIds([]);
    } else {
      setSelectedDocIds(documents.map(doc => doc.id));
    }
  };

  const loadConversations = async () => {
    setIsLoadingHistory(true);
    try {
      const userId = user?.id || 'anonymous';
      const response = await fetch(`${CONVERSATIONS_API}?user_id=${userId}&module=orchestrator`, {
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        setConversations(data.conversations || []);
      }
    } catch (error) {
      console.error('Load conversations error:', error);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const createNewConversation = () => {
    setMessages([
      {
        role: 'assistant',
        content: '您好！我是 LangGraph 智能助手，可以帮您处理以下任务：\n\n制定计划\n  - "帮我制定一个Python学习计划"\n  - "制定旅行计划"\n\n搜索和查询\n  - "搜索学习计划"\n  - "查询知识库关于XXX的文档"\n\n发帖和打卡\n  - "帮我发帖，内容：今天完成了健身"\n  - "我要打卡"\n\n其他问题\n  - 任何日常对话或问题\n\n请告诉我您需要什么帮助？'
      }
    ]);
    setSessionId('');
    setDebugInfo(null);
    setQuery('');
  };

  const loadConversation = async (convSessionId: string) => {
    try {
      const response = await fetch(`${AI_API_BASE}/orchestrator/history/${convSessionId}`, {
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        setMessages(data.history || []);
        setSessionId(convSessionId);
      }
    } catch (error) {
      console.error('Load conversation error:', error);
    }
  };

  const deleteConversation = async (convSessionId: string) => {
    try {
      await fetch(`${CONVERSATIONS_API}/${convSessionId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });
      loadConversations();
      if (sessionId === convSessionId) {
        createNewConversation();
      }
    } catch (error) {
      console.error('Delete conversation error:', error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: query,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setQuery('');
    setIsLoading(true);

    try {
      const response = await fetch(`${AI_API_BASE}/orchestrator/chat`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          message: query,
          session_id: sessionId || undefined,
          user_id: user?.id || 'anonymous',
          doc_ids: selectedDocIds.length > 0 ? selectedDocIds : undefined,
        })
      });

      if (response.ok) {
        const data = await response.json();

        const assistantMessage: Message = {
          role: 'assistant',
          content: data.response || '',
          timestamp: new Date().toISOString(),
          intent: data.intent || undefined,
          confidence: data.confidence || 0,
          executionTrace: data.execution_trace || [],
          blockedByCapability: data.blocked_by_capability || false,
          handoffReason: data.handoff_reason || undefined
        };

        setMessages(prev => [...prev, assistantMessage]);
        setSessionId(data.session_id || '');

        setDebugInfo({
          intent: data.intent || '',
          confidence: data.confidence || 0,
          selectedAgent: data.intent || '',
          blockedByCapability: data.blocked_by_capability || false,
          handoffReason: data.handoff_reason || '',
          executionTrace: Array.isArray(data.execution_trace) ? data.execution_trace : [],
          toolsCalled: Array.isArray(data.execution_trace)
            ? data.execution_trace.flatMap((t: any) => t.tools_called || [])
            : [],
          sessionId: data.session_id || ''
        });
      } else {
        throw new Error(`请求失败: ${response.status}`);
      }
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        role: 'assistant',
        content: `抱歉，请求失败：${error instanceof Error ? error.message : '未知错误'}`,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const formatTime = (timestamp: string) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  };

  const getIntentColor = (intent?: string) => {
    if (!intent) return '#6b7280';
    const colors: Record<string, string> = {
      learning: '#10b981',
      health: '#f59e0b',
      travel: '#3b82f6',
      work: '#8b5cf6',
      finance: '#ef4444',
      rag: '#06b6d4',
      assistant: '#6366f1',
      chat: '#6b7280',
      plan_creation: '#10b981'
    };
    return colors[intent] || '#6b7280';
  };

  const getIntentLabel = (intent?: string) => {
    if (!intent) return '未知';
    const labels: Record<string, string> = {
      learning: '学习计划',
      health: '健康计划',
      travel: '旅行计划',
      work: '工作计划',
      finance: '财务计划',
      rag: '知识查询',
      assistant: '通用助手',
      chat: '闲聊',
      plan_creation: '制定计划'
    };
    return labels[intent] || intent;
  };

  const getIntentIcon = (intent?: string) => {
    if (!intent) return <MessageSquare size={16} />;
    const icons: Record<string, React.ReactNode> = {
      learning: <Target size={16} />,
      health: <Activity size={16} />,
      travel: <Send size={16} />,
      work: <MessageSquare size={16} />,
      finance: <Zap size={16} />,
      rag: <Search size={16} />,
      assistant: <Bot size={16} />,
      chat: <MessageSquare size={16} />,
      plan_creation: <BookOpen size={16} />
    };
    return icons[intent] || <MessageSquare size={16} />;
  };

  return (
    <div style={styles.container}>
      {/* 头部 */}
      <div style={styles.header}>
        <button style={styles.backButton} onClick={() => navigate('/dashboard')}>
          <ArrowLeft size={20} />
        </button>

        {/* 左上角切换按钮 */}
        <div style={styles.tabSwitchContainer}>
          <button
            style={{
              ...styles.tabButton,
              ...styles.tabButtonActive
            }}
          >
            plan助手
          </button>
          <button
            style={styles.tabButton}
            onClick={() => navigate('/chatbot')}
          >
            问答助手
          </button>
          <button
            style={styles.tabButton}
            onClick={() => navigate('/assistant')}
          >
            智能助手
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginLeft: 'auto' }}>
          {/* 知识库文档管理 */}
          <button
            style={{
              ...styles.toggleButton,
              background: showDocPanel ? '#10b981' : '#f1f5f9',
              color: showDocPanel ? 'white' : '#64748b',
            }}
            onClick={() => setShowDocPanel(!showDocPanel)}
            title={showDocPanel ? '隐藏知识库' : '显示知识库'}
          >
            <BookOpen size={18} />
            <span>知识库</span>
            {documents.length > 0 && (
              <span style={{
                ...styles.badge,
                background: showDocPanel ? 'white' : '#10b981',
                color: showDocPanel ? '#10b981' : 'white'
              }}>
                {documents.length}
              </span>
            )}
          </button>

          {/* 显示/隐藏调试面板 */}
          <button
            style={{
              ...styles.toggleButton,
              background: showDebug ? '#6366f1' : '#f1f5f9',
              color: showDebug ? 'white' : '#64748b',
            }}
            onClick={() => setShowDebug(!showDebug)}
            title={showDebug ? '隐藏调试面板' : '显示调试面板'}
          >
            <Settings size={18} />
            <span>调试</span>
          </button>

          {/* 显示/隐藏历史 */}
          <button
            style={{
              ...styles.toggleButton,
              background: showHistory ? '#64748b' : '#f1f5f9',
              color: showHistory ? 'white' : '#64748b',
            }}
            onClick={() => setShowHistory(!showHistory)}
            title={showHistory ? '隐藏历史' : '显示历史'}
          >
            <History size={18} />
            <span>历史</span>
          </button>
        </div>
      </div>

      <div style={styles.mainContent}>
        {/* 左侧 - 会话历史 */}
        {showHistory && (
          <div style={styles.sidebar}>
            <div style={styles.sidebarHeader}>
              <h3>对话历史</h3>
              <div style={styles.headerActions}>
                <button
                  style={styles.newButton}
                  onClick={createNewConversation}
                  title="新建会话"
                >
                  <Plus size={16} />
                </button>
                <button style={styles.refreshButton} onClick={loadConversations}>
                  <RefreshIcon />
                </button>
              </div>
            </div>
            {isLoadingHistory ? (
              <div style={styles.loadingText}>加载中...</div>
            ) : conversations.length === 0 ? (
              <div style={styles.emptyText}>暂无对话记录</div>
            ) : (
              <div style={styles.conversationList}>
                {conversations.map((conv) => (
                  <div
                    key={conv.session_id}
                    style={{
                      ...styles.conversationItem,
                      ...(sessionId === conv.session_id && styles.conversationItemActive),
                    }}
                  >
                    <div style={styles.conversationInfo} onClick={() => loadConversation(conv.session_id)}>
                      <div style={styles.conversationPreview}>
                        {conv.preview || (conv.first_message ? conv.first_message.substring(0, 20) + '...' : '新会话')}
                      </div>
                      <div style={styles.conversationMeta}>
                        <span style={styles.messageCount}>{conv.message_count || '0'} 条消息</span>
                        <span style={styles.conversationTime}>
                          {conv.updated_at ? formatTime(conv.updated_at) : (conv.created_at ? formatTime(conv.created_at) : '')}
                        </span>
                      </div>
                    </div>
                    <button
                      style={styles.deleteButton}
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteConversation(conv.session_id);
                      }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 中间 - 聊天区域 */}
        <div style={styles.chatArea}>
          <div style={styles.messagesContainer}>
            {messages.map((msg, index) => {
              const isUser = msg.role === 'user';
              return (
                <div
                  key={index}
                  style={{
                    ...styles.message,
                    ...(isUser ? styles.userMessage : styles.assistantMessage),
                  }}
                >
                  <div style={{
                    ...styles.avatar,
                    ...(isUser ? styles.userAvatar : styles.assistantAvatar),
                  }}>
                    {isUser ? (
                      user?.avatarUrl ? (
                        <img src={getFullAvatarUrl(user.avatarUrl) || ''} alt="用户头像" style={{ width: 40, height: 40, borderRadius: '50%', objectFit: 'cover' }} />
                      ) : (
                        <span style={{ fontSize: '16px', fontWeight: 'bold', color: '#ffffff' }}>
                          {user?.displayName?.[0] || user?.username?.[0] || '?'}
                        </span>
                      )
                    ) : (
                      <img src="/robot-icon.png" alt="对话机器人" style={{ width: 36, height: 36 }} />
                    )}
                  </div>
                  <div style={{ ...styles.messageContent, ...(isUser ? styles.userMessageContent : styles.assistantMessageContent) }}>
                    {/* 意图标签 */}
                    {!isUser && msg.intent && (
                      <div style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        marginBottom: '8px',
                        padding: '4px 10px',
                        backgroundColor: msg.blockedByCapability ? '#fef3c7' : `${getIntentColor(msg.intent)}20`,
                        borderRadius: '6px',
                        fontSize: '12px',
                        fontWeight: 600,
                        color: msg.blockedByCapability ? '#d97706' : getIntentColor(msg.intent),
                      }}>
                        {msg.blockedByCapability && <Shield size={14} />}
                        {getIntentIcon(msg.intent)}
                        <span>{getIntentLabel(msg.intent)}</span>
                        <span style={{ marginLeft: '4px' }}>
                          {typeof msg.confidence === 'number' ? `${(msg.confidence * 100).toFixed(1)}%` : ''}
                        </span>
                      </div>
                    )}

                    {/* 降级提示 */}
                    {!isUser && msg.blockedByCapability && msg.handoffReason && (
                      <div style={{
                        padding: '6px 10px',
                        backgroundColor: '#fef3c7',
                        borderRadius: '6px',
                        fontSize: '12px',
                        color: '#92400e',
                        marginBottom: '8px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px'
                      }}>
                        <AlertTriangle size={14} />
                        <span>{msg.handoffReason}</span>
                      </div>
                    )}

                    <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                      {msg.content}
                    </div>
                    {msg.timestamp && (
                      <span style={styles.messageTime}>{formatTime(msg.timestamp)}</span>
                    )}
                  </div>
                </div>
              );
            })}

            {/* 加载状态 */}
            {isLoading && (
              <div style={{ ...styles.message, ...styles.assistantMessage }}>
                <div style={{ ...styles.avatar, ...styles.assistantAvatar }}>
                  <img src="/robot-icon.png" alt="对话机器人" style={{ width: 36, height: 36 }} />
                </div>
                <div style={styles.assistantMessageContent}>
                  <Loader2 size={20} style={{ animation: 'spin 1s linear infinite' }} />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* 输入区域 */}
          <div style={styles.inputContainer}>
            <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '12px', width: '100%' }}>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="输入你的需求，例如：我想制定一个Python学习计划..."
                style={styles.input}
                disabled={isLoading}
              />
              <button
                type="submit"
                disabled={isLoading || !query.trim()}
                style={{
                  ...styles.sendButton,
                  ...(isLoading || !query.trim() ? styles.sendButtonDisabled : {}),
                }}
              >
                <Send size={20} />
              </button>
            </form>
          </div>
        </div>

        {/* 右侧 - 调试面板 */}
        {showDebug && (
          <div style={styles.debugPanel}>
            <div style={styles.sidebarHeader}>
              <h3>调试信息</h3>
            </div>

            <div style={{ padding: '16px', flex: 1, overflow: 'auto' }}>
              {!debugInfo ? (
                <div style={{ textAlign: 'center', color: '#64748b', padding: '40px 0' }}>
                  <Bot size={48} color="#cbd5e1" />
                  <p style={{ marginTop: '12px' }}>发送消息后查看调试信息</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  {/* 意图识别 */}
                  <div>
                    <h4 style={styles.debugSectionTitle}>
                      意图识别
                    </h4>
                    <div style={styles.debugCard}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                        <div style={{
                          padding: '4px 8px',
                          backgroundColor: getIntentColor(debugInfo.intent),
                          color: 'white',
                          borderRadius: '4px',
                          fontSize: '12px',
                          fontWeight: 600
                        }}>
                          {getIntentLabel(debugInfo.intent)}
                        </div>
                        <ChevronRight size={16} color="#64748b" />
                        <div style={{
                          padding: '4px 8px',
                          backgroundColor: debugInfo.blockedByCapability ? '#f59e0b' : '#3b82f6',
                          color: 'white',
                          borderRadius: '4px',
                          fontSize: '12px',
                          fontWeight: 600
                        }}>
                          {debugInfo.blockedByCapability ? '已降级' : getIntentLabel(debugInfo.selectedAgent)}
                        </div>
                      </div>
                      <div style={{ fontSize: '12px', color: '#64748b' }}>
                        置信度: {typeof debugInfo.confidence === 'number' ? `${(debugInfo.confidence * 100).toFixed(1)}%` : 'N/A'}
                      </div>
                      {debugInfo.handoffReason && (
                        <div style={{
                          marginTop: '8px',
                          padding: '6px 10px',
                          backgroundColor: '#fef3c7',
                          borderRadius: '4px',
                          fontSize: '12px',
                          color: '#92400e'
                        }}>
                          {debugInfo.handoffReason}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* 工具调用 */}
                  {debugInfo.toolsCalled.length > 0 && (
                    <div>
                      <h4 style={styles.debugSectionTitle}>
                        工具调用
                      </h4>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {debugInfo.toolsCalled.map((tool, index) => (
                          <div
                            key={index}
                            style={{
                              padding: '8px 12px',
                              backgroundColor: '#f1f5f9',
                              borderRadius: '6px',
                              fontSize: '12px',
                              fontFamily: 'monospace',
                              color: '#475569'
                            }}
                          >
                            {tool}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 执行轨迹 */}
                  <div>
                    <h4 style={styles.debugSectionTitle}>
                      执行轨迹
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {debugInfo.executionTrace.map((trace: any, index: number) => (
                        <div
                          key={index}
                          style={styles.debugCard}
                        >
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            marginBottom: '8px'
                          }}>
                            <div style={{
                              width: '24px',
                              height: '24px',
                              backgroundColor: '#3b82f6',
                              color: 'white',
                              borderRadius: '50%',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontSize: '12px',
                              fontWeight: 600
                            }}>
                              {index + 1}
                            </div>
                            <span style={{ fontSize: '14px', fontWeight: 600, color: '#1e293b' }}>
                              {trace?.node || trace?.name || 'unknown'}
                            </span>
                            {trace?.success !== undefined && (
                              <span style={{
                                marginLeft: 'auto',
                                fontSize: '12px',
                                color: trace.success ? '#10b981' : '#ef4444'
                              }}>
                                {trace.success ? '✓' : '✗'}
                              </span>
                            )}
                          </div>
                          <div style={{
                            fontSize: '11px',
                            color: '#64748b',
                            marginLeft: '32px',
                            fontFamily: 'monospace',
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-all'
                          }}>
                            {(() => {
                              try {
                                const str = JSON.stringify(trace, null, 2);
                                return str.substring(0, 500) + (str.length > 500 ? '...' : '');
                              } catch (e) {
                                return String(trace);
                              }
                            })()}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 会话信息 */}
                  <div>
                    <h4 style={styles.debugSectionTitle}>
                      会话信息
                    </h4>
                    <div style={{
                      padding: '12px',
                      backgroundColor: '#f8fafc',
                      borderRadius: '8px',
                      fontSize: '12px',
                      color: '#64748b',
                      fontFamily: 'monospace',
                      wordBreak: 'break-all'
                    }}>
                      Session: {debugInfo.sessionId || 'N/A'}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 右侧 - 文档管理面板 */}
        {showDocPanel && (
          <DocumentManager
            documents={documents}
            selectedDocIds={selectedDocIds}
            onUpload={handleUploadDocuments}
            onDelete={handleDeleteDocument}
            onToggleSelection={toggleDocSelection}
            onToggleAll={toggleSelectAll}
            isUploading={isUploading}
          />
        )}
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes blink {
          0%, 50% { opacity: 1; }
          51%, 100% { opacity: 0; }
        }
      `}</style>
    </div>
  );
};

// 自定义刷新图标组件
const RefreshIcon: React.FC = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
    <path d="M21 3v5h-5" />
    <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
    <path d="M8 16H3v5" />
  </svg>
);

// 样式定义（参考 ChatBot 风格）
const styles: { [key: string]: React.CSSProperties } = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    background: '#f8fafc',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    padding: '20px 24px',
    background: 'white',
    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.05)',
  },
  backButton: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '40px',
    height: '40px',
    background: 'transparent',
    border: 'none',
    borderRadius: '50%',
    cursor: 'pointer',
    color: '#64748b',
    transition: 'all 0.2s ease',
  },
  tabSwitchContainer: {
    display: 'flex',
    alignItems: 'center',
    background: '#f1f5f9',
    borderRadius: '8px',
    padding: '2px',
  },
  tabButton: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '10px 24px',
    border: 'none',
    background: 'transparent',
    fontSize: '15px',
    fontWeight: '600',
    cursor: 'pointer',
    borderRadius: '6px',
    transition: 'all 0.2s ease',
    color: '#64748b',
    position: 'relative',
    zIndex: 1,
  },
  tabButtonActive: {
    background: '#ffffff',
    color: '#0f172a',
    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
    position: 'relative',
    zIndex: 2,
  },
  toggleButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 16px',
    background: '#f1f5f9',
    border: 'none',
    borderRadius: '8px',
    color: '#64748b',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  mainContent: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
  },
  sidebar: {
    width: '300px',
    background: 'white',
    borderRight: '1px solid #e2e8f0',
    display: 'flex',
    flexDirection: 'column',
  },
  sidebarHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '16px 20px',
    borderBottom: '1px solid #e2e8f0',
  },
  headerActions: {
    display: 'flex',
    gap: '8px',
  },
  newButton: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '32px',
    height: '32px',
    background: '#f1f5f9',
    border: '1px solid #e2e8f0',
    borderRadius: '6px',
    color: '#333333',
    cursor: 'pointer',
  },
  refreshButton: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '32px',
    height: '32px',
    background: '#f1f5f9',
    border: 'none',
    borderRadius: '6px',
    color: '#64748b',
    cursor: 'pointer',
  },
  loadingText: {
    padding: '20px',
    color: '#64748b',
    textAlign: 'center',
  },
  emptyText: {
    padding: '40px 20px',
    color: '#94a3b8',
    textAlign: 'center',
  },
  conversationList: {
    flex: 1,
    overflowY: 'auto',
    padding: '12px',
  },
  conversationItem: {
    display: 'flex',
    alignItems: 'center',
    padding: '12px',
    borderRadius: '8px',
    cursor: 'pointer',
    marginBottom: '4px',
    transition: 'all 0.2s ease',
  },
  conversationItemActive: {
    background: '#f1f5f9',
  },
  conversationInfo: {
    flex: 1,
    minWidth: 0,
  },
  conversationPreview: {
    fontSize: '14px',
    color: '#0f172a',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    marginBottom: '4px',
  },
  conversationMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '12px',
    color: '#94a3b8',
  },
  messageCount: {
    background: '#f1f5f9',
    padding: '2px 6px',
    borderRadius: '4px',
  },
  conversationTime: {},
  deleteButton: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '32px',
    height: '32px',
    background: 'transparent',
    border: '1px solid #e2e8f0',
    borderRadius: '6px',
    color: '#94a3b8',
    cursor: 'pointer',
    opacity: 1,
    transition: 'all 0.2s ease',
  },
  chatArea: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    background: '#f8fafc',
  },
  messagesContainer: {
    flex: 1,
    overflowY: 'auto',
    padding: '24px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  message: {
    display: 'flex',
    gap: '12px',
    maxWidth: '70%',
  },
  userMessage: {
    alignSelf: 'flex-end',
    flexDirection: 'row-reverse',
  },
  assistantMessage: {
    alignSelf: 'flex-start',
  },
  avatar: {
    width: '40px',
    height: '40px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
    flexShrink: 0,
  },
  userAvatar: {
    background: '#3b82f6',
  },
  assistantAvatar: {
    background: '#ffffff',
    border: '2px solid #e2e8f0',
  },
  messageContent: {
    padding: '12px 16px',
    borderRadius: '16px',
    fontSize: '15px',
    lineHeight: '1.5',
    position: 'relative',
  },
  userMessageContent: {
    background: '#3b82f6',
    color: 'white',
    border: '1px solid #3b82f6',
    borderRadius: '16px 16px 4px 16px',
  },
  assistantMessageContent: {
    background: 'white',
    color: '#0f172a',
    border: '1px solid #e2e8f0',
    borderRadius: '16px 16px 16px 4px',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
  messageTime: {
    display: 'block',
    fontSize: '11px',
    opacity: 0.7,
    marginTop: '4px',
    textAlign: 'right',
  },
  inputContainer: {
    display: 'flex',
    gap: '12px',
    padding: '20px 24px',
    background: 'white',
    boxShadow: '0 -2px 4px rgba(0, 0, 0, 0.05)',
  },
  input: {
    flex: 1,
    padding: '12px 16px',
    border: '1px solid #e2e8f0',
    borderRadius: '12px',
    fontSize: '15px',
    outline: 'none',
    transition: 'all 0.2s ease',
  },
  sendButton: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '48px',
    height: '48px',
    background: '#3b82f6',
    border: 'none',
    borderRadius: '12px',
    color: 'white',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  sendButtonDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
  },
  badge: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: '18px',
    height: '18px',
    padding: '0 4px',
    fontSize: '10px',
    fontWeight: 600,
    borderRadius: '9px',
  },
  // 调试面板样式
  debugPanel: {
    width: '350px',
    background: 'white',
    borderLeft: '1px solid #e2e8f0',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  debugSectionTitle: {
    margin: '0 0 10px 0',
    fontSize: '14px',
    fontWeight: 600,
    color: '#1e293b'
  },
  debugCard: {
    padding: '12px',
    backgroundColor: '#f8fafc',
    borderRadius: '8px',
    border: '1px solid #e2e8f0'
  },
};

export default LangGraphTest;
