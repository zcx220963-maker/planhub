import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, History, ChevronLeft, ChevronRight } from 'lucide-react';
import { agentApi } from '../services/api';
import VisualizationPanel from '../components/VisualizationPanel';
import { extractMermaidCode, stripMermaidFromText } from '../utils/mermaidExtractor';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
  trace?: any[];
  timestamp: Date;
  isStreaming?: boolean;
}

const AI_API_BASE = 'http://127.0.0.1:8000';

const AgentAssistant: React.FC = () => {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: '你好！我是 PlanHub 全智能助手\n\n我可以帮你：\n• 聊天对话\n• 查询知识库\n• 制定计划\n• 执行各种任务\n\n试试发送消息吧！',
      intent: 'greeting',
      timestamp: new Date()
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(() => `session_${Date.now()}`);
  const [useRag, setUseRag] = useState(false);
  const [usePlanMode, setUsePlanMode] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showVisualization, setShowVisualization] = useState(false);
  const [mermaidCode, setMermaidCode] = useState<string>('');
  const [visualTitle, setVisualTitle] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // 历史记录面板：默认展开
  const [showHistory, setShowHistory] = useState(true);
  const [conversations, setConversations] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // 加载历史记录
  const loadConversations = useCallback(async () => {
    setLoadingHistory(true);
    try {
      const userId = 'standalone_user';
      const res = await fetch(`${AI_API_BASE}/conversations?user_id=${userId}&module=orchestrator`);
      const data = await res.json();
      setConversations(data.conversations || []);
    } catch (err) {
      console.error('Load conversations error:', err);
    }
    setLoadingHistory(false);
  }, []);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // 加载某个历史会话
  const loadConversation = async (sid: string) => {
    try {
      const res = await fetch(`${AI_API_BASE}/conversations/${sid}`);
      const data = await res.json();
      if (data.history && data.history.length > 0) {
        const loadedMessages: Message[] = data.history.map((msg: any, idx: number) => ({
          id: `loaded_${idx}`,
          role: msg.role === 'user' ? 'user' : 'assistant',
          content: msg.content || '',
          timestamp: new Date(msg.timestamp || Date.now()),
        }));
        setMessages(loadedMessages);
        setSessionId(sid);
      }
    } catch (err) {
      console.error('Load conversation error:', err);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: Message = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: inputMessage,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    // 先插入一条空的 assistant 消息（流式填充内容用）
    const aiMsgId = `assistant_${Date.now()}`;
    setMessages(prev => [
      ...prev,
      { id: aiMsgId, role: 'assistant', content: '', isStreaming: true, timestamp: new Date() }
    ]);

    let lastContent = '';
    let finalSessionId = sessionId;

    // 使用 WebSocket 实时流式通信
    const ws = agentApi.chatWebSocket(
      inputMessage,
      sessionId,
      'anonymous',
      undefined,
      // onMessage
      (data) => {
        if (data.type === 'token') {
          // 逐 token 实时追加（无延迟、无轮询）
          lastContent += data.content || '';
          setMessages(prev =>
            prev.map(m =>
              m.id === aiMsgId
                ? { ...m, content: lastContent, isStreaming: true }
                : m
            )
          );
        } else if (data.type === 'node_complete') {
          // LLM 生成结束 → 立即解除加载状态
          setIsLoading(false);
          setMessages(prev =>
            prev.map(m =>
              m.id === aiMsgId
                ? { ...m, isStreaming: false }
                : m
            )
          );
        } else if (data.type === 'done') {
          // 最终完成
          lastContent = data.response || lastContent;
          finalSessionId = data.session_id || finalSessionId;

          // 提取 Mermaid 代码
          const mermaid = extractMermaidCode(lastContent);
          if (mermaid) {
            setMermaidCode(mermaid);
            setShowVisualization(true);
            const intentLabel: Record<string, string> = {
              plan: '📋 计划时间轴',
              visualize: '📊 可视化',
              chat: '💬 图解',
              rag: '📚 知识图谱',
            };
            setVisualTitle(intentLabel[data.intent || 'chat'] || '📊 可视化');
          }

          const displayContent = mermaid
            ? stripMermaidFromText(lastContent)
            : lastContent;

          setMessages(prev =>
            prev.map(m =>
              m.id === aiMsgId
                ? {
                    ...m,
                    content: displayContent,
                    isStreaming: false,
                    intent: data.intent,
                    trace: data.execution_trace,
                  }
                : m
            )
          );
          setSessionId(finalSessionId);
          setIsLoading(false);
        } else if (data.type === 'error') {
          setMessages(prev =>
            prev.map(m =>
              m.id === aiMsgId
                ? {
                    ...m,
                    content: `抱歉，请求失败：${data.detail || '未知错误'}`,
                    isStreaming: false,
                    intent: 'error',
                  }
                : m
            )
          );
          setIsLoading(false);
        }
      },
      // onError
      () => {
        setMessages(prev =>
          prev.map(m =>
            m.id === aiMsgId
              ? {
                  ...m,
                  content: '连接失败，请检查网络',
                  isStreaming: false,
                  intent: 'error',
                }
              : m
          )
        );
        setIsLoading(false);
      },
      // onClose
      () => {
        // 确保加载状态关闭
        setIsLoading(false);
        setMessages(prev =>
          prev.map(m =>
            m.id === aiMsgId && m.isStreaming
              ? { ...m, isStreaming: false }
              : m
          )
        );
      }
    );

    // 保存 ws 引用以便停止
    abortControllerRef.current = ws as any;
  };

  // 停止生成
  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      // WebSocket 或 AbortController 都支持 close/abort
      if (abortControllerRef.current instanceof WebSocket) {
        abortControllerRef.current.close();
      } else {
        abortControllerRef.current.abort();
      }
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleResetSession = async () => {
    try {
      await agentApi.resetSession(sessionId);
      setMessages([
        {
          id: '1',
          role: 'assistant',
          content: '会话已重置！我是 PlanHub 全智能助手 🤖\n\n我可以帮你：\n• 💬 聊天对话\n• 📚 查询知识库\n• 📋 制定计划\n• 🛠️ 执行各种任务\n\n试试发送消息吧！',
          intent: 'greeting',
          timestamp: new Date()
        }
      ]);
    } catch (error) {
      console.error('Reset Session Error:', error);
    }
  };

  const getIntentColor = (intent?: string) => {
    switch (intent) {
      case 'chat': return '#10b981';
      case 'tool': return '#3b82f6';
      case 'rag': return '#8b5cf6';
      case 'plan': return '#f59e0b';
      case 'error': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const getIntentLabel = (intent?: string) => {
    switch (intent) {
      case 'chat': return '💬 聊天';
      case 'tool': return '🛠️ 工具';
      case 'rag': return '📚 知识库';
      case 'plan': return '📋 计划';
      case 'error': return '❌ 错误';
      default: return '🤖 默认';
    }
  };

  return (
    <div style={{
      display: 'flex',
      height: '100%',
      backgroundColor: '#f9fafb',
      overflow: 'hidden',
    }}>
      {/* 最左侧：工具按钮栏 */}
      <div style={styles.toolbar}>
        <button
          style={styles.toolbarBtn}
          onClick={() => navigate('/plan-library')}
          title="计划库"
        >
          <BookOpen size={20} />
          <span style={styles.toolbarLabel}>计划库</span>
        </button>
        <button
          style={{
            ...styles.toolbarBtn,
            ...(showHistory ? styles.toolbarBtnActive : {}),
          }}
          onClick={() => setShowHistory(!showHistory)}
          title="历史记录"
        >
          <History size={20} />
          <span style={styles.toolbarLabel}>历史</span>
        </button>
      </div>

      {/* 历史记录面板（可收起） */}
      {showHistory && (
        <div style={styles.historyPanel}>
          <div style={styles.historyHeader}>
            <span style={styles.historyTitle}>历史记录</span>
            <button
              style={styles.historyCloseBtn}
              onClick={() => setShowHistory(false)}
              title="收起"
            >
              <ChevronLeft size={16} />
            </button>
          </div>
          <div style={styles.historyList}>
            {loadingHistory ? (
              <div style={styles.historyEmpty}>加载中...</div>
            ) : conversations.length === 0 ? (
              <div style={styles.historyEmpty}>暂无历史记录</div>
            ) : (
              conversations.map((conv: any) => (
                <div
                  key={conv.session_id}
                  style={{
                    ...styles.historyItem,
                    ...(conv.session_id === sessionId ? styles.historyItemActive : {}),
                  }}
                  onClick={() => loadConversation(conv.session_id)}
                >
                  <div style={styles.historyItemTitle}>
                    {conv.title || conv.session_id.slice(0, 8)}
                  </div>
                  <div style={styles.historyItemDate}>
                    {conv.last_time
                      ? new Date(conv.last_time).toLocaleDateString('zh-CN')
                      : ''}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* 中间：聊天区域 */}
      <div style={{
        flex: showVisualization ? '1' : '1 1 100%',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        minWidth: 0,
        transition: 'flex 0.3s ease',
      }}>
      {/* 头部 */}
      <div style={{
        padding: '20px 24px',
        backgroundColor: 'white',
        borderBottom: '1px solid #e5e7eb',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div>
          <h1 style={{
            margin: 0,
            fontSize: '24px',
            fontWeight: 700,
            color: '#111827',
            display: 'flex',
            alignItems: 'center',
            gap: '12px'
          }}>
            <span style={{ fontSize: '32px' }}>🤖</span>
            全智能助手
          </h1>
          <p style={{
            margin: '4px 0 0 0',
            fontSize: '14px',
            color: '#6b7280'
          }}>
            LangGraph 驱动 • 会话ID: {sessionId.slice(0, 20)}...
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={() => setShowSettings(!showSettings)}
            style={{
              padding: '8px 16px',
              backgroundColor: showSettings ? '#3b82f6' : '#f3f4f6',
              color: showSettings ? 'white' : '#374151',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: 500,
              transition: 'all 0.2s'
            }}
          >
            ⚙️ 设置
          </button>
          <button
            onClick={handleResetSession}
            style={{
              padding: '8px 16px',
              backgroundColor: '#fee2e2',
              color: '#dc2626',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: 500,
              transition: 'all 0.2s'
            }}
          >
            🔄 重置会话
          </button>
        </div>
      </div>

      {/* 设置面板 */}
      {showSettings && (
        <div style={{
          padding: '16px 24px',
          backgroundColor: '#f3f4f6',
          borderBottom: '1px solid #e5e7eb',
          display: 'flex',
          gap: '24px'
        }}>
          <label style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            cursor: 'pointer'
          }}>
            <input
              type="checkbox"
              checked={useRag}
              onChange={(e) => setUseRag(e.target.checked)}
              style={{
                width: '18px',
                height: '18px',
                cursor: 'pointer'
              }}
            />
            <span style={{ fontSize: '14px', color: '#374151' }}>
              📚 启用知识库 (RAG)
            </span>
          </label>
          <label style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            cursor: 'pointer'
          }}>
            <input
              type="checkbox"
              checked={usePlanMode}
              onChange={(e) => setUsePlanMode(e.target.checked)}
              style={{
                width: '18px',
                height: '18px',
                cursor: 'pointer'
              }}
            />
            <span style={{ fontSize: '14px', color: '#374151' }}>
              📋 启用计划模式
            </span>
          </label>
        </div>
      )}

      {/* 消息列表 */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px'
      }}>
        {messages.map((message) => (
          <div
            key={message.id}
            style={{
              display: 'flex',
              justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
              gap: '12px'
            }}
          >
            {message.role === 'assistant' && (
              <div style={{
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                backgroundColor: '#3b82f6',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '20px',
                flexShrink: 0
              }}>
                🤖
              </div>
            )}
            <div style={{
              maxWidth: '70%',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px'
            }}>
              {message.intent && message.intent !== 'greeting' && (
                <span style={{
                  fontSize: '12px',
                  padding: '4px 8px',
                  backgroundColor: getIntentColor(message.intent),
                  color: 'white',
                  borderRadius: '12px',
                  alignSelf: 'flex-start'
                }}>
                  {getIntentLabel(message.intent)}
                </span>
              )}
              <div style={{
                padding: '12px 16px',
                backgroundColor: message.role === 'user' ? '#3b82f6' : 'white',
                color: message.role === 'user' ? 'white' : '#111827',
                borderRadius: message.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
                whiteSpace: 'pre-wrap',
                lineHeight: '1.6',
                fontSize: '15px'
              }}>
                {message.content}
                {message.isStreaming && (
                  <span style={{
                    display: 'inline-block',
                    width: '2px',
                    height: '16px',
                    backgroundColor: '#3b82f6',
                    marginLeft: '2px',
                    animation: 'blink 1s step-end infinite',
                    verticalAlign: 'middle'
                  }} />
                )}
              </div>
              <span style={{
                fontSize: '12px',
                color: '#9ca3af',
                alignSelf: message.role === 'user' ? 'flex-end' : 'flex-start'
              }}>
                {message.timestamp.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
            {message.role === 'user' && (
              <div style={{
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                backgroundColor: '#10b981',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '20px',
                flexShrink: 0
              }}>
                👤
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div style={{
            display: 'flex',
            justifyContent: 'flex-start',
            gap: '12px'
          }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '50%',
              backgroundColor: '#3b82f6',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '20px'
            }}>
              🤖
            </div>
            <div style={{
              padding: '12px 16px',
              backgroundColor: 'white',
              borderRadius: '16px 16px 16px 4px',
              boxShadow: '0 1px 2px rgba(0,0,0,0.1)'
            }}>
              <div style={{ display: 'flex', gap: '4px' }}>
                <span style={{
                  width: '8px',
                  height: '8px',
                  backgroundColor: '#3b82f6',
                  borderRadius: '50%',
                  animation: 'bounce 1.4s infinite ease-in-out'
                }}></span>
                <span style={{
                  width: '8px',
                  height: '8px',
                  backgroundColor: '#3b82f6',
                  borderRadius: '50%',
                  animation: 'bounce 1.4s infinite ease-in-out 0.2s'
                }}></span>
                <span style={{
                  width: '8px',
                  height: '8px',
                  backgroundColor: '#3b82f6',
                  borderRadius: '50%',
                  animation: 'bounce 1.4s infinite ease-in-out 0.4s'
                }}></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 输入框 */}
      <div style={{
        padding: '16px 24px',
        backgroundColor: 'white',
        borderTop: '1px solid #e5e7eb'
      }}>
        <div style={{
          display: 'flex',
          gap: '12px',
          alignItems: 'flex-end'
        }}>
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
            disabled={isLoading}
            style={{
              flex: 1,
              padding: '12px 16px',
              border: '1px solid #d1d5db',
              borderRadius: '12px',
              fontSize: '15px',
              resize: 'none',
              outline: 'none',
              fontFamily: 'inherit',
              minHeight: '48px',
              maxHeight: '120px',
              opacity: isLoading ? 0.5 : 1
            }}
            rows={1}
          />
          {isLoading ? (
            <button
              onClick={handleStopGeneration}
              style={{
                padding: '12px 20px',
                backgroundColor: '#ef4444',
                color: 'white',
                border: 'none',
                borderRadius: '12px',
                cursor: 'pointer',
                fontSize: '15px',
                fontWeight: 600,
                transition: 'all 0.2s',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              <span>停止</span>
              <span style={{ fontSize: '14px' }}>⏹</span>
            </button>
          ) : (
            <button
              onClick={handleSendMessage}
              disabled={!inputMessage.trim()}
              style={{
                padding: '12px 24px',
                backgroundColor: !inputMessage.trim() ? '#d1d5db' : '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '12px',
                cursor: !inputMessage.trim() ? 'not-allowed' : 'pointer',
                fontSize: '15px',
                fontWeight: 600,
                transition: 'all 0.2s',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              <span>发送</span>
              <span style={{ fontSize: '18px' }}>🚀</span>
            </button>
          )}
        </div>
        <div style={{
          marginTop: '8px',
          fontSize: '12px',
          color: '#9ca3af',
          display: 'flex',
          gap: '16px'
        }}>
          <span>💡 提示：在设置中启用知识库或计划模式获得更强大的功能</span>
        </div>
      </div>

      <style>{`
        @keyframes bounce {
          0%, 80%, 100% {
            transform: scale(0);
          }
          40% {
            transform: scale(1);
          }
        }
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
      `}</style>
      </div>

      {/* 右侧：可视化面板 */}
      {showVisualization && (
        <div style={{
          width: '50%',
          minWidth: '400px',
          height: '100%',
          flexShrink: 0,
        }}>
          <VisualizationPanel
            mermaidCode={mermaidCode}
            title={visualTitle}
            onClose={() => setShowVisualization(false)}
          />
        </div>
      )}
    </div>
  );
};

export default AgentAssistant;

// 局部样式（新增的工具栏和历史面板）
const styles: Record<string, React.CSSProperties> = {
  toolbar: {
    width: '60px',
    backgroundColor: '#fff',
    borderRight: '1px solid #e5e7eb',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '16px 8px',
    gap: '8px',
    flexShrink: 0,
  },
  toolbarBtn: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '4px',
    width: '100%',
    padding: '10px 4px',
    border: '1px solid transparent',
    borderRadius: '10px',
    backgroundColor: 'transparent',
    cursor: 'pointer',
    color: '#64748b',
    fontSize: '11px',
    transition: 'all 0.15s',
  },
  toolbarBtnActive: {
    backgroundColor: '#eef2ff',
    color: '#6366f1',
    borderColor: '#c7d2fe',
  },
  toolbarLabel: {
    fontSize: '10px',
    fontWeight: 500,
    whiteSpace: 'nowrap',
  },
  historyPanel: {
    width: '220px',
    backgroundColor: '#fff',
    borderRight: '1px solid #e5e7eb',
    display: 'flex',
    flexDirection: 'column',
    flexShrink: 0,
  },
  historyHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '12px 16px',
    borderBottom: '1px solid #e5e7eb',
    flexShrink: 0,
  },
  historyTitle: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#1a1a2e',
  },
  historyCloseBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: '#94a3b8',
    padding: '4px',
    borderRadius: '4px',
    display: 'flex',
    alignItems: 'center',
  },
  historyList: {
    flex: 1,
    overflowY: 'auto',
    padding: '8px',
  },
  historyEmpty: {
    padding: '24px 16px',
    textAlign: 'center',
    fontSize: '13px',
    color: '#94a3b8',
  },
  historyItem: {
    padding: '10px 12px',
    borderRadius: '8px',
    cursor: 'pointer',
    marginBottom: '4px',
    transition: 'all 0.15s',
  },
  historyItemActive: {
    backgroundColor: '#eef2ff',
  },
  historyItemTitle: {
    fontSize: '13px',
    fontWeight: 500,
    color: '#1a1a2e',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    marginBottom: '2px',
  },
  historyItemDate: {
    fontSize: '11px',
    color: '#94a3b8',
  },
};
