import React, { useState, useRef, useEffect } from 'react';
import { Send, ArrowLeft, Loader2, History, Trash2, Plus, BookOpen, Zap, Calendar, Bot } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import DocumentManager from '../components/DocumentManager';

const ChatBot: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const getFullAvatarUrl = (avatarUrl?: string) => {
    if (!avatarUrl) return null;
    if (avatarUrl.startsWith('http')) return avatarUrl;
    if (avatarUrl.startsWith('/')) return `http://localhost:8080${avatarUrl}`;
    return `http://localhost:8080/${avatarUrl}`;
  };

  // AI 服务基础 URL - 通过 Java 后端安全网关转发，不再直接调用 Python
  const AI_API_BASE = 'http://localhost:8080/api/ai';

  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; content: string; timestamp?: string }[]>([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [showHistory, setShowHistory] = useState(true);
  const [conversations, setConversations] = useState<any[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 知识库相关状态
  const [useRag, setUseRag] = useState(false);  // 是否启用知识库
  const [showDocPanel, setShowDocPanel] = useState(false);  // 是否显示文档面板
  const [documents, setDocuments] = useState<any[]>([]);  // 已上传文档列表
  const [selectedDocIds, setSelectedDocIds] = useState<number[]>([]);  // 选中的文档ID
  const [isUploading, setIsUploading] = useState(false);  // 是否正在上传

  // 计划生成相关状态
  const [usePlanMode, setUsePlanMode] = useState(false);  // 是否启用计划生成模式

  // 获取带 JWT Token 的请求 Header
  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    const headers = new Headers();
    headers.set('Content-Type', 'application/json');
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
      console.log('[DEBUG] Token found, adding Authorization header');
    } else {
      console.log('[DEBUG] No token found in localStorage');
    }
    return headers;
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  useEffect(() => {
    loadConversations();
    loadDocuments();  // 加载文档列表
  }, []);

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
        loadDocuments();  // 刷新文档列表
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
        loadDocuments();  // 刷新文档列表
        setSelectedDocIds(prev => prev.filter(id => id !== docId));  // 从选中列表中移除
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
      // 经过 Java 安全网关: GET /api/ai/conversations -> Python /conversations
      const response = await fetch(`${AI_API_BASE}/conversations?user_id=${userId}&module=chat`, {
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
    setMessages([]);
    setSessionId('');
    setInput('');
  };

  const loadConversation = async (convSessionId: string) => {
    try {
      // 经过 Java 安全网关: GET /api/ai/chat/history/{id} -> Python /chat/history/{id}
      const response = await fetch(`${AI_API_BASE}/chat/history/${convSessionId}`, {
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
        setMessages([]);
        setSessionId('');
      }
    } catch (error) {
      console.error('Delete conversation error:', error);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage, timestamp: new Date().toISOString() }]);
    setIsLoading(true);
    setStreamingContent('');

    try {
      const userId = user?.id || 'anonymous';
      let currentSessionId: string;

      if (sessionId) {
        currentSessionId = sessionId;
      } else {
        currentSessionId = `chat:${userId}:${userId}_chat_${Date.now()}`;
      }

      setSessionId(currentSessionId);

      let fullResponse = '';
      let useRagFallback = false;

      // ─── 计划生成模式（可叠加 RAG）──────────────────────────────
      if (usePlanMode) {
        console.log(`[DEBUG] Plan mode enabled, useRag=${useRag}`);

        const planResponse = await fetch(`${AI_API_BASE}/chat/plan`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({
            message: userMessage,
            session_id: currentSessionId,
            user_id: String(userId),
            use_rag: useRag,  // 传递 RAG 开关状态
            doc_ids: selectedDocIds.length > 0 ? selectedDocIds : undefined,
          }),
        });

        if (planResponse.ok) {
          const planData = await planResponse.json();
          fullResponse = planData.response || planData.message || '生成计划失败';

          // 一次性显示结果（不逐字模拟流式）
          setMessages(prev => [...prev, { role: 'assistant', content: fullResponse, timestamp: new Date().toISOString() }]);
          setStreamingContent('');
          loadConversations();
          setIsLoading(false);
          return;
        } else {
          console.error(`[ERROR] Plan generation failed: ${planResponse.status}`);
          // 回退到普通对话
          useRagFallback = true;
        }
      }

      // 如果启用知识库，先尝试 RAG 查询
      if (useRag && !usePlanMode) {
        try {
          console.log(`[DEBUG] RAG mode enabled, querying knowledge base first...`);

          const ragResponse = await fetch(`${AI_API_BASE}/rag/query`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
              question: userMessage,
              session_id: currentSessionId,
              user_id: String(userId),  // 确保 user_id 是字符串
              doc_ids: selectedDocIds.length > 0 ? selectedDocIds : undefined,
              top_k: 3,
              use_rerank: false,
              use_compression: false,
            }),
          });

          if (ragResponse.ok) {
            const ragData = await ragResponse.json();
            console.log(`[DEBUG] RAG response:`, ragData);

            // 检查 RAG 是否有有效回答
            if (ragData.answer && !ragData.answer.includes('未找到相关信息') && !ragData.answer.includes('暂无文档')) {
              // RAG 有有效回答，使用 RAG 结果
              fullResponse = ragData.answer;
              console.log(`[DEBUG] RAG query successful, returning answer (length: ${fullResponse.length})`);

              // 逐字显示，模拟流式效果
              for (let i = 0; i < fullResponse.length; i++) {
                setStreamingContent(fullResponse.slice(0, i + 1));
                await new Promise(resolve => setTimeout(resolve, 20));
              }

              setMessages(prev => [...prev, { role: 'assistant', content: fullResponse, timestamp: new Date().toISOString() }]);
              setStreamingContent('');
              loadConversations();
              setIsLoading(false);
              return;  // 直接返回，不继续调用 ChatBot
            } else {
              // RAG 没有有效回答，先提示用户，然后回退到 Chat API
              console.log(`[DEBUG] RAG query returned no useful results, showing message and falling back to chat`);

              // 显示"知识库中没有相关信息"的提示
              const ragNoResultMsg = "知识库中没有找到相关内容，稍等一下，小助手正在为您思考...";
              setMessages(prev => [...prev, { role: 'assistant', content: ragNoResultMsg, timestamp: new Date().toISOString() }]);

              // 逐字显示提示信息
              for (let i = 0; i < ragNoResultMsg.length; i++) {
                setStreamingContent(ragNoResultMsg.slice(0, i + 1));
                await new Promise(resolve => setTimeout(resolve, 15));
              }

              // 短暂延迟，让用户看到提示
              await new Promise(resolve => setTimeout(resolve, 500));

              useRagFallback = true;
            }
          } else {
            // RAG 请求失败（404, 500等）
            console.log(`[WARN] RAG request failed with status: ${ragResponse.status}, showing message and falling back to chat`);

            // 显示错误提示
            const ragErrorMsg = "知识库查询失败，小助手正在自行思考...";
            setMessages(prev => [...prev, { role: 'assistant', content: ragErrorMsg, timestamp: new Date().toISOString() }]);

            // 逐字显示提示信息
            for (let i = 0; i < ragErrorMsg.length; i++) {
              setStreamingContent(ragErrorMsg.slice(0, i + 1));
              await new Promise(resolve => setTimeout(resolve, 15));
            }

            // 短暂延迟
            await new Promise(resolve => setTimeout(resolve, 500));

            useRagFallback = true;
          }
        } catch (e) {
          console.log(`[WARN] RAG query failed with exception: ${e}, showing message and falling back to chat`);

          // 显示错误提示
          const ragErrorMsg = "知识库查询出错，小助手正在自行思考...";
          setMessages(prev => [...prev, { role: 'assistant', content: ragErrorMsg, timestamp: new Date().toISOString() }]);

          // 逐字显示提示信息
          for (let i = 0; i < ragErrorMsg.length; i++) {
            setStreamingContent(ragErrorMsg.slice(0, i + 1));
            await new Promise(resolve => setTimeout(resolve, 15));
          }

          // 短暂延迟
          await new Promise(resolve => setTimeout(resolve, 500));

          useRagFallback = true;
        }
      }

      // 普通对话模式（或 RAG 查不到时回退）
      if (!useRag || useRagFallback) {
        console.log(`[DEBUG] Calling Chat API: ${AI_API_BASE}/chat/stream, useRag=${useRag}, useRagFallback=${useRagFallback}`);

        // 如果是 RAG 回退，先清除提示信息，准备显示大模型回答
        if (useRagFallback && messages.length > 0) {
          const lastMsg = messages[messages.length - 1];
          if (lastMsg && lastMsg.role === 'assistant' &&
              (lastMsg.content.includes('知识库中没有相关信息') ||
               lastMsg.content.includes('知识库查询失败') ||
               lastMsg.content.includes('知识库查询出错'))) {
            // 移除上一条提示信息
            setMessages(prev => prev.slice(0, -1));
          }
        }

        // 构建当前会话的对话历史（只包含最近的几轮，避免知识库内容污染）
        // 注意：这里传递的是当前会话的消息历史，后端会据此构建上下文
        const currentConversationHistory = messages.slice(-40).map(msg => ({
          role: msg.role,
          content: msg.content
        }));

        const response = await fetch(`${AI_API_BASE}/chat/stream`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({
            message: userMessage,
            session_id: currentSessionId,
            user_id: userId,
            use_rag: false,  // 明确传递 use_rag=false，避免后端默认启用
            conversation_history: currentConversationHistory,  // 传递当前会话的上下文历史
          }),
        });

        console.log(`[DEBUG] Chat API response status: ${response.status}`);
        if (!response.ok) {
          const errorText = await response.text();
          console.error(`[ERROR] Chat API failed: ${response.status} - ${errorText}`);
          throw new Error('Network response was not ok');
        }

        // Chat API 返回 SSE 流
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (reader) {
          let done = false;
          while (!done) {
            const { value, done: doneReading } = await reader.read();
            done = doneReading;

            if (value) {
              const chunk = decoder.decode(value);
              const lines = chunk.split('\n');

              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  const dataStr = line.slice(6).trim();
                  if (dataStr && dataStr !== '[DONE]') {
                    try {
                      const data = JSON.parse(dataStr);
                      if (data.content) {
                        fullResponse += data.content;
                        setStreamingContent(fullResponse);
                      }
                      if (data.done) {
                        break;
                      }
                    } catch (e) {
                      // 忽略解析错误
                    }
                  }
                }
              }
            }
          }
        }

        setMessages(prev => [...prev, { role: 'assistant', content: fullResponse, timestamp: new Date().toISOString() }]);
        setStreamingContent('');
        loadConversations();
      }

    } catch (error) {
      console.error('Chat error:', error);
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
              ...styles.tabButtonActive,
            }}
          >
            问答助手
          </button>
          <button
            style={{
              ...styles.tabButton,
            }}
            onClick={() => navigate('/assistant')}
          >
            智能助手
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginLeft: 'auto' }}>
          {/* 知识库开关 + 文档管理按钮（二合一） */}
          <button
            style={{
              ...styles.toggleButton,
              background: useRag ? '#10b981' : '#f1f5f9',
              color: useRag ? 'white' : '#64748b',
            }}
            onClick={() => {
              const newUseRag = !useRag;
              setUseRag(newUseRag);
              if (newUseRag) {
                setShowDocPanel(true);  // 开启知识库时自动展开文档面板
              } else {
                setShowDocPanel(false);  // 关闭知识库时自动收起文档面板
              }
            }}
            title={useRag ? '知识库已开启，点击关闭' : '知识库已关闭，点击开启'}
          >
            <BookOpen size={18} />
            <span>{useRag ? '知识库: 开' : '知识库: 关'}</span>
          </button>

          {/* 计划生成开关 */}
          <button
            style={{
              ...styles.toggleButton,
              background: usePlanMode ? '#8b5cf6' : '#f1f5f9',
              color: usePlanMode ? 'white' : '#64748b',
            }}
            onClick={() => {
              const newUsePlanMode = !usePlanMode;
              setUsePlanMode(newUsePlanMode);
              if (newUsePlanMode) {
                // 开启时显示提示
                setMessages(prev => [...prev, {
                  role: 'assistant',
                  content: '计划生成模式已开启！你可以说：\n"制定学习计划"\n"制定健康计划"\n"制定旅行计划"\n"制定工作计划"\n"制定财务计划"\n\n我会引导你逐步完善计划信息。',
                  timestamp: new Date().toISOString()
                }]);
              } else {
                // 关闭时显示提示
                setMessages(prev => [...prev, {
                  role: 'assistant',
                  content: '计划生成模式已关闭，返回普通对话模式。',
                  timestamp: new Date().toISOString()
                }]);
              }
            }}
            title={usePlanMode ? '计划生成模式已开启，点击关闭' : '计划生成模式已关闭，点击开启'}
          >
            <Calendar size={18} />
            <span>{usePlanMode ? '计划: 开' : '计划: 关'}</span>
          </button>

          {/* 显示/隐藏历史 */}
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

        <div style={styles.chatArea}>
          <div style={styles.messagesContainer}>
            {messages.length === 0 ? (
              <div style={styles.welcome}>
                <div style={{ marginBottom: '16px' }}>
                  <Bot size={72} color="#000000" />
                </div>
                <h2>欢迎使用 问答助手</h2>
                <p>有什么问题我可以帮助你？</p>
              </div>
            ) : (
              <>
                {messages.map((msg, index) => (
                  <div
                    key={index}
                    style={{
                      ...styles.message,
                      ...(msg.role === 'user' ? styles.userMessage : styles.assistantMessage),
                    }}
                  >
                    <div style={{
                      ...styles.avatar,
                      ...(msg.role === 'user' ? styles.userAvatar : styles.assistantAvatar),
                    }}>
                      {msg.role === 'user' ? (
                        user?.avatarUrl ? (
                          <img src={getFullAvatarUrl(user.avatarUrl) || ''} alt="用户头像" style={{ width: 40, height: 40, borderRadius: '50%', objectFit: 'cover' }} />
                        ) : (
                          <span style={{ fontSize: '16px', fontWeight: 'bold', color: '#ffffff' }}>
                            {user?.displayName?.[0] || user?.username?.[0] || '?'}
                          </span>
                        )
                      ) : (
                        <Bot size={36} color="#000000" />
                      )}
                    </div>
                    <div style={{ ...styles.messageContent, ...(msg.role === 'user' ? styles.userMessageContent : styles.assistantMessageContent) }}>
                      {msg.content}
                      {msg.timestamp && (
                        <span style={styles.messageTime}>{formatTime(msg.timestamp)}</span>
                      )}
                    </div>
                  </div>
                ))}
                {isLoading && streamingContent && (
                  <div style={{ ...styles.message, ...styles.assistantMessage }}>
                    <div style={{ ...styles.avatar, ...styles.assistantAvatar }}>
                      <Bot size={36} color="#000000" />
                    </div>
                    <div style={styles.assistantMessageContent}>
                      {streamingContent}
                      <span style={styles.cursor}>▊</span>
                    </div>
                  </div>
                )}
              </>
            )}
            {isLoading && !streamingContent && (
              <div style={{ ...styles.message, ...styles.assistantMessage }}>
                <div style={{ ...styles.avatar, ...styles.assistantAvatar }}>
                  <Bot size={36} color="#000000" />
                </div>
                <div style={styles.assistantMessageContent}>
                  <Loader2 size={20} style={{ animation: 'spin 1s linear infinite' }} />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div style={styles.inputContainer}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
              placeholder="输入你的消息..."
              style={styles.input}
              disabled={isLoading}
            />
            <button
              style={{
                ...styles.sendButton,
                ...(isLoading || !input.trim() ? styles.sendButtonDisabled : {}),
              }}
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
            >
              <Send size={20} />
            </button>
          </div>
        </div>

        {/* 右侧文档管理面板 */}
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

const RefreshIcon: React.FC = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>
    <path d="M21 3v5h-5"/>
    <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>
    <path d="M8 16H3v5"/>
  </svg>
);

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
  chatArea: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  messagesContainer: {
    flex: 1,
    overflowY: 'auto',
    padding: '24px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  welcome: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1,
    color: '#64748b',
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
    background: '#333333',
  },
  assistantAvatar: {
    background: 'transparent',
  },
  messageContent: {
    padding: '12px 16px',
    borderRadius: '16px',
    fontSize: '15px',
    lineHeight: '1.5',
    position: 'relative',
  },
  userMessageContent: {
    background: '#f1f5f9',
    color: '#333333',
    border: '1px solid #e2e8f0',
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
  cursor: {
    display: 'inline-block',
    animation: 'blink 1s infinite',
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
    background: '#f1f5f9',
    border: 'none',
    borderRadius: '12px',
    color: '#333333',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  sendButtonDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
  },
};

export default ChatBot;
