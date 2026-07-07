import React, { useState, useRef, useEffect } from 'react';
import { agentApi } from '../services/api';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
  trace?: any[];
  timestamp: Date;
}

const AgentAssistant: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: '你好！我是 PlanHub 全智能助手 🤖\n\n我可以帮你：\n• 💬 聊天对话\n• 📚 查询知识库\n• 📋 制定计划\n• 🛠️ 执行各种任务\n\n试试发送消息吧！',
      intent: 'greeting',
      timestamp: new Date()
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => `session_${Date.now()}`);
  const [useRag, setUseRag] = useState(false);
  const [usePlanMode, setUsePlanMode] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 检测 AI 消息是否处于计划生成引导流程
  // 匹配多种确认引导语：
  //   - plan_generator: "请点击确认，我将为您生成计划"
  //   - plan_mode_confirm: "回复「是」开始制定，或回复「否」继续聊天"
  //   - plan_mode_confirm: "你想制定一个关于什么的计划呢？"
  const isPlanGuideMessage = (msg: Message) => {
    if (msg.role !== 'assistant') return false;
    const content = msg.content;
    // plan_generator 引导语（含 "请点击确认"）
    if (content.includes('请点击确认')) return true;
    // plan_mode_confirm 引导语（意图确认阶段）
    if (content.includes('开始制定') || content.includes('回复「是」')) return true;
    // plan_mode_confirm 首次询问（"你想制定..." / "请问您想制定..."）
    if (content.includes('关于什么的计划') || content.includes('关于什么计划')) return true;
    return false;
  };

  // 点击「确认」超链接 → 直接向后端发送特殊指令进入计划确认
  const handleConfirmPlan = async () => {
    if (isLoading) return;
    const userMessage: Message = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: '确认',
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    try {
      const response = await agentApi.chat(
        '__CONFIRM_PLAN__',
        sessionId,
        useRag,
        usePlanMode
      );
      const assistantMessage: Message = {
        id: `assistant_${Date.now()}`,
        role: 'assistant',
        content: response.response || '好的，正在为您生成计划...',
        intent: response.intent,
        trace: response.trace,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error: any) {
      console.error('Agent API Error:', error);
      const errorMessage: Message = {
        id: `error_${Date.now()}`,
        role: 'assistant',
        content: `抱歉，发生了错误：${error.response?.data?.detail || error.message || '未知错误'}`,
        intent: 'error',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // 渲染 AI 消息内容：如果处于计划引导流程，在末尾追加一个可点击的「确认」按钮
  const renderAssistantContent = (msg: Message) => {
    if (!isPlanGuideMessage(msg)) {
      return msg.content;
    }
    // 匹配多种引导语中的可点击词，替换成超链接
    // 优先级：确认 >「是」> 开始制定
    const patterns = [
      { regex: /确认/g, label: '确认' },
      { regex: /「是」/g, label: '「是」' },
      { regex: /开始制定/g, label: '开始制定' },
    ];

    for (const { regex, label } of patterns) {
      if (regex.test(msg.content)) {
        // 重置 lastIndex（因为 RegExp 带 g 标志会保存状态）
        regex.lastIndex = 0;
        const parts = msg.content.split(regex);
        // split 后 parts.length-1 = 匹配次数，每段之间插入超链接
        if (parts.length >= 2) {
          const result: React.ReactNode[] = [];
          result.push(<span key="0">{parts[0]}</span>);
          for (let i = 1; i < parts.length; i++) {
            result.push(
              <a
                key={`link_${i}`}
                onClick={handleConfirmPlan}
                style={{
                  color: '#3b82f6',
                  cursor: 'pointer',
                  textDecoration: 'underline',
                  fontWeight: 600
                }}
                title="点击确认进入下一步"
              >
                {label}
              </a>
            );
            result.push(<span key={`text_${i}`}>{parts[i]}</span>);
          }
          return result;
        }
      }
    }

    // 兜底：如果文本里没有可匹配关键词但在 plan_guide 流程中，在末尾追加按钮
    return (
      <span>
        {msg.content}
        <a
          onClick={handleConfirmPlan}
          style={{
            color: '#3b82f6',
            cursor: 'pointer',
            textDecoration: 'underline',
            fontWeight: 600,
            marginLeft: '4px'
          }}
          title="点击确认进入下一步"
        >
          [确认]
        </a>
      </span>
    );
  };

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

    try {
      const response = await agentApi.chat(
        inputMessage,
        sessionId,
        useRag,
        usePlanMode
      );

      const assistantMessage: Message = {
        id: `assistant_${Date.now()}`,
        role: 'assistant',
        content: response.response || '抱歉，没有收到有效回复',
        intent: response.intent,
        trace: response.trace,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error: any) {
      console.error('Agent API Error:', error);
      const errorMessage: Message = {
        id: `error_${Date.now()}`,
        role: 'assistant',
        content: `抱歉，发生了错误：${error.response?.data?.detail || error.message || '未知错误'}`,
        intent: 'error',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
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
      flexDirection: 'column',
      height: '100%',
      backgroundColor: '#f9fafb'
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
                {message.role === 'assistant' ? renderAssistantContent(message) : message.content}
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
          <button
            onClick={handleSendMessage}
            disabled={!inputMessage.trim() || isLoading}
            style={{
              padding: '12px 24px',
              backgroundColor: (!inputMessage.trim() || isLoading) ? '#d1d5db' : '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '12px',
              cursor: (!inputMessage.trim() || isLoading) ? 'not-allowed' : 'pointer',
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
      `}</style>
    </div>
  );
};

export default AgentAssistant;
