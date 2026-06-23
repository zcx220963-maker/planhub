import React, { useState, useEffect } from 'react';
import { Send, Zap, ArrowLeft, Loader2, Plus, MessageSquare, Search, CheckCircle, History, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import SearchResultCard from '../components/SearchResultCard';

const Assistant = () => {
    const navigate = useNavigate();
    const { user } = useAuth();
    // AI 服务基础 URL - 通过 Java 后端安全网关转发，不再直接调用 Python
    const AI_API_BASE = 'http://localhost:8080/api/ai';

    // 获取带 JWT Token 的请求 Header
    const getAuthHeaders = () => {
      const token = localStorage.getItem('token');
      const headers = new Headers();
      headers.set('Content-Type', 'application/json');
      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
        console.log('[DEBUG] Assistant - Token found, adding Authorization header');
      } else {
        console.log('[DEBUG] Assistant - No token found in localStorage');
      }
      return headers;
    };

    const [query, setQuery] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; content: string; timestamp?: string; searchResults?: any }[]>([
        { role: 'assistant', content: '你好！我是 PlanHub 的智能助手，我可以帮您：\n\n- 创建计划\n- 发布帖子\n- 搜索计划和帖子\n- 打卡\n\n请告诉我您需要什么帮助？' }
    ]);
    const [sessionId, setSessionId] = useState<string>('');
    const [showHistory, setShowHistory] = useState(true);
    const [conversations, setConversations] = useState<any[]>([]);
    const [isLoadingHistory, setIsLoadingHistory] = useState(false);

    useEffect(() => {
        loadConversations();
    }, []);

    const loadConversations = async () => {
        setIsLoadingHistory(true);
        try {
            const userId = user?.id || 'anonymous';
            // 经过 Java 安全网关: GET /api/ai/conversations -> Python /conversations
            const response = await fetch(`${AI_API_BASE}/conversations?user_id=${userId}&module=assistant`, {
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
            { role: 'assistant', content: '你好！我是 PlanHub 的智能助手，我可以帮您：\n\n- 创建计划\n- 发布帖子\n- 搜索计划和帖子\n- 打卡\n\n请告诉我您需要什么帮助？' }
        ]);
        setSessionId('');
        setQuery('');
    };

    const loadConversation = async (convSessionId: string) => {
    try {
      // 经过 Java 安全网关: GET /api/ai/assistant/history/{id} -> Python /assistant/history/{id}
      const response = await fetch(`${AI_API_BASE}/assistant/history/${convSessionId}`, {
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
      // 经过 Java 安全网关: DELETE /api/ai/conversations/{id} -> Python /conversations/{id}
      await fetch(`${AI_API_BASE}/conversations/${convSessionId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });
      loadConversations();
      if (sessionId === convSessionId) {
        setMessages([
          { role: 'assistant', content: '你好！我是 PlanHub 的智能助手，我可以帮您：\n\n- 创建计划\n- 发布帖子\n- 搜索计划和帖子\n- 打卡\n\n请告诉我您需要什么帮助？' }
        ]);
        setSessionId('');
      }
    } catch (error) {
      console.error('Delete conversation error:', error);
    }
  };

  const handleSend = async (customQuery?: string) => {
    const messageToSend = customQuery || query;
    if (!messageToSend.trim() || isLoading) return;

    setIsLoading(true);
    setMessages(prev => [...prev, { role: 'user', content: messageToSend, timestamp: new Date().toISOString() }]);
    setQuery('');

    try {
      const userId = user?.id || 'anonymous';
      let currentSessionId: string;
      
      if (sessionId) {
        currentSessionId = sessionId;
      } else {
        currentSessionId = `assistant:${userId}:${userId}_assistant_${Date.now()}`;
      }
      
      setSessionId(currentSessionId);

      // 经过 Java 安全网关: POST /api/ai/assistant -> Python /assistant
      // 不再直接调用 localhost:8000，JWT 验证由 Java 处理
      const response = await fetch(`${AI_API_BASE}/assistant`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ query: messageToSend, session_id: currentSessionId, user_id: userId }),
      });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            const assistantMessage = data.reply || data.response || data.content || '抱歉，我不知道该怎么回答';

            setMessages(prev => [...prev, { role: 'assistant', content: assistantMessage, timestamp: new Date().toISOString() }]);
            loadConversations();

            if (data.need_jump && data.jump_data) {
                const jumpData = data.jump_data;
                console.log('=== Jump Data ===');
                console.log('Jump data:', jumpData);
                console.log('Jump type:', jumpData.type);
                console.log('Jump id:', jumpData.id, 'type:', typeof jumpData.id);
                console.log('Jump id as string:', String(jumpData.id));
                
                if (jumpData.type === 'plan') {
                    const targetPath = '/plan/' + String(jumpData.id);
                    console.log('Navigating to plan:', targetPath);
                    setTimeout(() => {
                        navigate(targetPath);
                    }, 500);
                } else if (jumpData.type === 'post') {
                    const targetPath = '/post/' + String(jumpData.id);
                    console.log('Navigating to post:', targetPath);
                    setTimeout(() => {
                        navigate(targetPath);
                    }, 500);
                }
            }
        } catch (error) {
            console.error('Assistant error:', error);
            setMessages(prev => [...prev, { role: 'assistant', content: '抱歉，发生了错误，请稍后再试。' }]);
        } finally {
            setIsLoading(false);
        }
    };

    const formatTime = (timestamp: string) => {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    };

    // 解析消息内容，将搜索结果中的标题转换为可点击的超链接
    const parseMessageContent = (content: string) => {
        // 匹配搜索结果格式：序号. 标题\n   [查看详情](/path)
        // 例如：1. 学习 React 高级特性\n     [查看详情](/plan/123)
        const searchResultRegex = /(\d+)\.\s+(.+?)\n\s+\[查看详情\]\(\/(plan|post)\/(\d+)\)/g;

        // DEBUG: 打印内容和匹配结果
        console.log('[DEBUG] parseMessageContent called with:', JSON.stringify(content));
        console.log('[DEBUG] Regex:', searchResultRegex);

        const parts: (string | JSX.Element)[] = [];
        let lastIndex = 0;
        let match;

        // 重置 lastIndex，避免 g 标志导致的状态问题
        searchResultRegex.lastIndex = 0;

        while ((match = searchResultRegex.exec(content)) !== null) {
            console.log('[DEBUG] Match found:', match);
            // 添加匹配前的文本
            if (match.index > lastIndex) {
                parts.push(content.slice(lastIndex, match.index));
            }

            // 提取信息
            const [_, displayId, title, type, realId] = match;
            const path = `/${type}/${realId}`;

            // 创建可点击的超链接（标题就是超链接）
            parts.push(
                <span key={`result-${match.index}`} style={{ display: 'block', marginLeft: '8px', marginBottom: '4px' }}>
                    {displayId}.{' '}
                    <button
                        onClick={(e) => {
                            e.preventDefault();
                            navigate(path);
                        }}
                        style={{
                            background: 'none',
                            border: 'none',
                            color: type === 'plan' ? '#667eea' : '#10b981',
                            cursor: 'pointer',
                            textDecoration: 'underline',
                            padding: '2px 4px',
                            fontSize: 'inherit',
                            fontFamily: 'inherit',
                            borderRadius: '4px',
                            transition: 'all 0.2s',
                            fontWeight: 500,
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.background = '#f1f5f9';
                            e.currentTarget.style.textDecoration = 'none';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.background = 'none';
                            e.currentTarget.style.textDecoration = 'underline';
                        }}
                        title={`查看${type === 'plan' ? '计划' : '帖子'}详情 (ID: ${realId})`}
                    >
                        {title}
                    </button>
                </span>
            );

            lastIndex = match.index + match[0].length;
        }

        // 添加剩余文本
        if (lastIndex < content.length) {
            parts.push(content.slice(lastIndex));
        }

        console.log('[DEBUG] Parts:', parts.length, parts);

        // 如果没有找到匹配的搜索结果，返回原始文本
        return parts.length > 0 ? <>{parts}</> : content;
    };

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
        headerTitle: {
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
        },
        title: {
            fontSize: '20px',
            fontWeight: 'bold',
            color: '#0f172a',
            margin: 0,
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
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '10px 24px',
            border: 'none',
            background: '#ffffff',
            fontSize: '15px',
            fontWeight: '600',
            borderRadius: '6px',
            transition: 'all 0.2s ease',
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
            marginLeft: 'auto',
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
        content: {
            flex: 1,
            padding: '24px',
            maxWidth: '800px',
            margin: '0 auto',
            width: '100%',
            display: 'flex',
            flexDirection: 'column',
            gap: '24px',
            overflowY: 'auto',
        },
        quickActions: {
            background: 'white',
            borderRadius: '12px',
            padding: '20px',
            border: '1px solid #e2e8f0',
        },
        sectionTitle: {
            fontSize: '16px',
            fontWeight: 'bold',
            color: '#0f172a',
            marginBottom: '16px',
            marginTop: 0,
        },
        actionGrid: {
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
            gap: '12px',
        },
        actionButton: {
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '8px',
            padding: '16px 20px',
            background: '#f1f5f9',
            border: '1px solid #e2e8f0',
            borderRadius: '12px',
            color: '#333333',
            fontSize: '14px',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
        },
        actionButtonDisabled: {
            opacity: 0.5,
            cursor: 'not-allowed',
        },
        messagesContainer: {
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            background: 'white',
            borderRadius: '12px',
            padding: '20px',
            border: '1px solid #e2e8f0',
            overflowY: 'auto',
            minHeight: '300px',
        },
        message: {
            display: 'flex',
            gap: '12px',
            maxWidth: '80%',
        },
        userMessage: {
            alignSelf: 'flex-end',
        },
        assistantMessage: {
            alignSelf: 'flex-start',
        },
        userMessageContent: {
            padding: '12px 16px',
            borderRadius: '16px 16px 4px 16px',
            fontSize: '15px',
            lineHeight: '1.6',
            background: '#f1f5f9',
            color: '#333333',
            border: '1px solid #e2e8f0',
            position: 'relative' as const,
        },
        assistantMessageContent: {
            padding: '12px 16px',
            borderRadius: '16px 16px 16px 4px',
            fontSize: '15px',
            lineHeight: '1.6',
            background: '#f1f5f9',
            color: '#0f172a',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            position: 'relative' as const,
        },
        messageTime: {
            display: 'block',
            fontSize: '11px',
            opacity: 0.7,
            marginTop: '4px',
            textAlign: 'right',
        },
        inputSection: {
            background: 'white',
            borderRadius: '12px',
            padding: '20px',
            border: '1px solid #e2e8f0',
        },
        inputContainer: {
            display: 'flex',
            gap: '12px',
        },
        input: {
            flex: 1,
            padding: '14px 18px',
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
            width: '52px',
            height: '52px',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
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
    };

    return (
        <div style={styles.container}>
            <div style={styles.header}>
                <button style={styles.backButton} onClick={() => navigate('/dashboard')}>
                    <ArrowLeft size={20} />
                </button>

                {/* 左上角切换按钮 */}
                <div style={styles.tabSwitchContainer}>
                    <button
                        style={{
                            ...styles.tabButton,
                        }}
                        onClick={() => navigate('/langgraph')}
                    >
                        plan助手
                    </button>
                    <button
                        style={{
                            ...styles.tabButton,
                        }}
                        onClick={() => navigate('/chatbot')}
                    >
                        问答助手
                    </button>
                    <button
                        style={{
                            ...styles.tabButtonActive,
                        }}
                    >
                        智能助手
                    </button>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginLeft: 'auto' }}>
                    <button
                        style={styles.toggleButton}
                        onClick={() => setShowHistory(!showHistory)}
                    >
                        <History size={20} />
                        <span>{showHistory ? '隐藏' : '显示'}历史</span>
                    </button>
                </div>
            </div>

            <div style={styles.mainContent}>
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
                                            <div style={styles.conversationPreview}>{conv.preview}</div>
                                            <div style={styles.conversationMeta}>
                                                <span style={styles.messageCount}>{conv.message_count} 条消息</span>
                                                <span style={styles.conversationTime}>{conv.updated_at ? formatTime(conv.updated_at) : ''}</span>
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

                <div style={styles.content}>
                    <div style={styles.quickActions}>
                        <h3 style={styles.sectionTitle}>快捷操作</h3>
                        <div style={styles.actionGrid}>
                            <button
                                style={{ ...styles.actionButton, ...(isLoading ? styles.actionButtonDisabled : {}) }}
                                onClick={() => handleSend('帮我创建计划')}
                                disabled={isLoading}
                            >
                                <Plus size={18} />
                                <span>创建计划</span>
                            </button>
                            <button
                                style={{ ...styles.actionButton, ...(isLoading ? styles.actionButtonDisabled : {}) }}
                                onClick={() => handleSend('我要发帖')}
                                disabled={isLoading}
                            >
                                <MessageSquare size={18} />
                                <span>发布帖子</span>
                            </button>
                            <button
                                style={{ ...styles.actionButton, ...(isLoading ? styles.actionButtonDisabled : {}) }}
                                onClick={() => handleSend('搜索计划和帖子')}
                                disabled={isLoading}
                            >
                                <Search size={18} />
                                <span>搜索计划和帖子</span>
                            </button>
                            <button
                                style={{ ...styles.actionButton, ...(isLoading ? styles.actionButtonDisabled : {}) }}
                                onClick={() => handleSend('我要打卡')}
                                disabled={isLoading}
                            >
                                <CheckCircle size={18} />
                                <span>打卡</span>
                            </button>
                        </div>
                    </div>

                    <div style={styles.messagesContainer}>
                        {messages.map((msg, index) => (
                            <div
                                key={index}
                                style={{ ...styles.message, ...(msg.role === 'user' ? styles.userMessage : styles.assistantMessage) }}
                            >
                                <div style={msg.role === 'user' ? styles.userMessageContent as React.CSSProperties : styles.assistantMessageContent as React.CSSProperties}>
                                    {msg.role === 'assistant' ? parseMessageContent(msg.content) : msg.content}
                                    {msg.timestamp && (
                                        <span style={styles.messageTime}>{formatTime(msg.timestamp)}</span>
                                    )}
                                </div>
                            </div>
                        ))}
                        {isLoading && (
                            <div style={{ ...styles.message, ...styles.assistantMessage }}>
                                <div style={styles.assistantMessageContent}>
                                    <Loader2 size={20} style={{ animation: 'spin 1s linear infinite' }} />
                                </div>
                            </div>
                        )}
                    </div>

                    <div style={styles.inputSection}>
                        <div style={styles.inputContainer}>
                            <input
                                type="text"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                                placeholder="告诉我您需要什么帮助..."
                                style={styles.input}
                                disabled={isLoading}
                            />
                            <button
                                style={{ ...styles.sendButton, ...(isLoading || !query.trim() ? styles.sendButtonDisabled : {}) }}
                                onClick={() => handleSend()}
                                disabled={isLoading || !query.trim()}
                            >
                                {isLoading ? <Loader2 size={20} style={{ animation: 'spin 1s linear infinite' }} /> : <Send size={20} />}
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <style>{`
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    );
};

const RefreshIcon: React.FC = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>
        <path d="M21 3v5h-5"/>
        <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>
        <path d="M8 16H3v5"/>
    </svg>
);

export default Assistant;
