import React, { useState, useEffect, useRef } from 'react';
import { Send, Book, ArrowLeft, Loader2, Upload, FileText, Trash2, Plus } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { planAssistantApi } from '../services/api';
import { useAuth } from '../context/AuthContext';

const RAG: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const AI_API_BASE = 'http://localhost:8080/api/ai';

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 获取带 JWT Token 的请求 Header
  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    const headers = new Headers();
    headers.set('Content-Type', 'application/json');
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    return headers;
  };

  // 当前输入
  const [input, setInput] = useState('');
  // 当前会话的消息列表（多轮对话）[{role: 'user'|'assistant', content: '...', sources: []}]
  const [messages, setMessages] = useState<Array<{ role: string; content: string; sources?: any[] }>>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [documents, setDocuments] = useState<any[]>([]);
  const [showHistory, setShowHistory] = useState(true);
  const [queryHistory, setQueryHistory] = useState<any[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [sessionId, setSessionId] = useState<string>('');
  const [selectedDocIds, setSelectedDocIds] = useState<number[]>([]);  // 选中的文档ID列表

  useEffect(() => {
    loadDocuments();
    loadQueryHistory();
  }, []);

  // 自动滚动到最新消息
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadDocuments = async () => {
    try {
      const userId = user?.id || 'anonymous';
      const result = await planAssistantApi.getDocuments(userId);
      setDocuments(result.documents || []);
    } catch (error) {
      console.error('Load documents error:', error);
    }
  };

  const loadQueryHistory = async () => {
    setIsLoadingHistory(true);
    try {
      const userId = user?.id || 'anonymous';
      const response = await fetch(`${AI_API_BASE}/conversations?user_id=${userId}&module=rag`, {
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        setQueryHistory(data.conversations || []);
      }
    } catch (error) {
      console.error('Load query history error:', error);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const handleQuery = async () => {
    if (!input.trim() || isLoading) return;

    const userQuestion = input.trim();
    setInput('');

    // 立即显示用户消息
    const newMessages = [...messages, { role: 'user', content: userQuestion }];
    setMessages(newMessages);
    setIsLoading(true);

    try {
      const userId = user?.id || 'anonymous';
      let currentSessionId = sessionId;
      
      if (!currentSessionId) {
        currentSessionId = `rag:${userId}:${Date.now()}`;
        setSessionId(currentSessionId);
      }

      // 发送问题到后端（带 session_id 实现多轮对话，带 doc_ids 实现指定文档查询）
      const result = await planAssistantApi.queryRAG(userQuestion, currentSessionId, userId, selectedDocIds);
      console.log('RAG 响应:', result);

      // 追加助手回答
      const answer = result.answer || result.response || '';
      const sources = result.sources || [];
      setMessages([...newMessages, { role: 'assistant', content: answer, sources }]);

      // 如果后端返回了 session_id，同步更新
      if (result.session_id) {
        setSessionId(result.session_id);
      }

      // 刷新历史列表
      loadQueryHistory();
    } catch (error) {
      console.error('RAG query error:', error);
      setMessages([...newMessages, { role: 'assistant', content: '抱歉，发生了错误，请稍后再试。' }]);
    } finally {
      setIsLoading(false);
    }
  };

  // 切换文档选择
  const toggleDocSelection = (docId: number) => {
    if (selectedDocIds.includes(docId)) {
      setSelectedDocIds(selectedDocIds.filter(id => id !== docId));
    } else {
      setSelectedDocIds([...selectedDocIds, docId]);
    }
  };

  // 全选/取消全选
  const toggleSelectAll = () => {
    if (selectedDocIds.length === documents.length) {
      setSelectedDocIds([]);
    } else {
      setSelectedDocIds(documents.map(doc => doc.id));
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);
    try {
      const formData = new FormData();
      for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
      }
      // 添加 user_id，确保文档上传到当前用户的知识库
      const userId = user?.id || 'anonymous';
      formData.append('user_id', userId);

      const response = await fetch(`${AI_API_BASE}/rag/upload/batch`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: formData
      });

      if (response.ok) {
        const result = await response.json();
        alert(result.message || '文档上传成功！');
        loadDocuments();
      } else {
        throw new Error('上传失败');
      }
    } catch (error) {
      console.error('Upload error:', error);
      alert('文档上传失败，请稍后再试。');
    } finally {
      setIsUploading(false);
    }
  };

  const deleteDocument = async (docId: number, docName: string) => {
    if (!confirm(`确定要删除文档 "${docName}" 吗？`)) return;
    try {
      const userId = user?.id || 'anonymous';
      const response = await fetch(`${AI_API_BASE}/rag/documents/${docId}?user_id=${userId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        alert('文档删除成功！');
        loadDocuments();
      }
    } catch (error) {
      console.error('Delete document error:', error);
      alert('文档删除失败，请稍后再试。');
    }
  };

  const deleteHistoryItem = async (convSessionId: string) => {
    try {
      await fetch(`${AI_API_BASE}/conversations/${encodeURIComponent(convSessionId)}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });
      loadQueryHistory();
      if (sessionId === convSessionId) {
        createNewConversation();
      }
    } catch (error) {
      console.error('Delete history error:', error);
    }
  };

  const loadConversation = async (convSessionId: string) => {
    console.log('Loading conversation:', convSessionId);
    try {
      const response = await fetch(`${AI_API_BASE}/conversations/${encodeURIComponent(convSessionId)}`, {
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        console.log('History data:', data);

        // 将完整的历史消息列表填充到 messages
        const history = data.history || [];
        const loadedMessages = history.map((msg: any) => ({
          role: msg.role,
          content: msg.content,
          sources: msg.sources || []
        }));

        setMessages(loadedMessages);
        setSessionId(convSessionId);
      }
    } catch (error) {
      console.error('Load conversation error:', error);
    }
  };

  const createNewConversation = () => {
    setInput('');
    setMessages([]);
    setSessionId('');
  };

  const formatTime = (timestamp: string) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  };

  // 获取会话的预览（用于左侧列表）
  const getConversationPreview = (conv: any) => {
    if (conv.title) return conv.title;
    const history = conv.history || [];
    const firstUser = history.find((m: any) => m.role === 'user');
    return firstUser ? (firstUser.content.length > 30 ? firstUser.content.substring(0, 30) + '...' : firstUser.content) : '新对话';
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <button style={styles.backButton} onClick={() => navigate('/dashboard')}>
          <ArrowLeft size={20} />
        </button>
        <div style={styles.headerTitle}>
          <Book size={24} />
          <h1 style={styles.title}>RAG 知识库</h1>
        </div>
        <button style={styles.toggleButton} onClick={() => setShowHistory(!showHistory)}>
          {showHistory ? '隐藏' : '显示'}历史
        </button>
      </div>

      <div style={styles.mainContent}>
        {/* 左侧：对话历史 */}
        {showHistory && (
          <div style={styles.sidebar}>
            <div style={styles.sidebarHeader}>
              <h3>对话历史</h3>
              <div style={styles.headerActions}>
                <button style={styles.newButton} onClick={createNewConversation} title="新建对话">
                  <Plus size={16} />
                </button>
              </div>
            </div>

            {isLoadingHistory ? (
              <div style={styles.loadingText}>加载中...</div>
            ) : queryHistory.length === 0 ? (
              <div style={styles.emptyText}>暂无对话记录</div>
            ) : (
              <div style={styles.conversationList}>
                {queryHistory.map((item) => (
                  <div
                    key={item.session_id}
                    style={{
                      ...styles.conversationItem,
                      ...(sessionId === item.session_id && styles.conversationItemActive),
                    }}
                  >
                    <div style={styles.conversationInfo} onClick={() => loadConversation(item.session_id)}>
                      <div style={styles.conversationPreview}>{getConversationPreview(item)}</div>
                      <div style={styles.conversationMeta}>
                        <span style={styles.messageCount}>{(item.history || []).length} 条消息</span>
                        <span style={styles.conversationTime}>{item.updated_at ? formatTime(item.updated_at) : ''}</span>
                      </div>
                    </div>
                    <button
                      style={styles.deleteButton}
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteHistoryItem(item.session_id);
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

        {/* 中间：对话区域 */}
        <div style={styles.chatArea}>
          <div style={styles.messagesArea}>
            {messages.length === 0 ? (
              <div style={styles.emptyChat}>
                <Book size={48} style={{ color: '#94a3b8', marginBottom: '16px' }} />
                <h2 style={{ fontSize: '20px', fontWeight: 'bold', color: '#0f172a', margin: 0, marginBottom: '8px' }}>
                  RAG 知识库助手
                </h2>
                <p style={{ fontSize: '14px', color: '#64748b', margin: 0, maxWidth: '400px', textAlign: 'center', lineHeight: 1.6 }}>
                  请上传文档后，基于文档内容进行问答。支持多轮对话，模型会记忆上下文。
                </p>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div
                  key={idx}
                  style={{
                    ...styles.messageRow,
                    ...(msg.role === 'user' ? styles.messageRowUser : styles.messageRowAssistant),
                  }}
                >
                  <div
                    style={{
                      ...styles.messageBubble,
                      ...(msg.role === 'user' ? styles.messageBubbleUser : styles.messageBubbleAssistant),
                    }}
                  >
                    <div style={styles.messageLabel}>
                      {msg.role === 'user' ? '你' : '知识库助手'}
                    </div>
                    <div style={styles.messageText}>{msg.content}</div>
                    {msg.sources && msg.sources.length > 0 && (
                      <div style={styles.messageSources}>
                        <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '8px' }}>参考来源：</div>
                        {msg.sources.map((src: any, sIdx: number) => (
                          <div key={sIdx} style={styles.sourceTag}>
                            {typeof src === 'string' ? src : src.content}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
            {isLoading && (
              <div style={{ ...styles.messageRow, ...styles.messageRowAssistant }}>
                <div style={{ ...styles.messageBubble, ...styles.messageBubbleAssistant }}>
                  <div style={styles.messageLabel}>知识库助手</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', color: '#64748b' }}>
                    <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
                    正在思考...
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* 输入框 */}
          <div style={styles.inputArea}>
            <div style={styles.inputContainer}>
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleQuery()}
                placeholder="输入你的问题..."
                style={styles.input}
                disabled={isLoading}
              />
              <button
                style={{
                  ...styles.sendButton,
                  ...((isLoading || !input.trim()) && styles.sendButtonDisabled),
                }}
                onClick={handleQuery}
                disabled={isLoading || !input.trim()}
              >
                <Send size={18} />
              </button>
            </div>
          </div>
        </div>

        {/* 右侧：文档管理 */}
        <div style={styles.rightSidebar}>
          <div style={styles.rightSidebarHeader}>
            <h3>文档管理</h3>
          </div>
          <div style={{ padding: '12px' }}>
            <label style={styles.uploadBox}>
              <input
                type="file"
                onChange={handleFileUpload}
                style={{ display: 'none' }}
                disabled={isUploading}
                multiple  // 支持多选
                accept=".txt,.md,.pdf,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.json,.csv"  // 限制文件类型
              />
              {isUploading ? (
                <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} />
              ) : (
                <>
                  <Upload size={24} />
                  <span style={{ fontSize: '14px' }}>上传文档</span>
                  <span style={{ fontSize: '12px', color: '#94a3b8' }}>支持 txt/pdf/docx 等</span>
                </>
              )}
            </label>
          </div>
          {documents.length > 0 ? (
            <div style={styles.documentList}>
              <div style={styles.docsSectionTitle}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={selectedDocIds.length === documents.length}
                    onChange={toggleSelectAll}
                    style={{ cursor: 'pointer' }}
                  />
                  已上传文档 ({documents.length})
                </label>
                {selectedDocIds.length > 0 && (
                  <span style={{ fontSize: '12px', color: '#1e88e5', marginLeft: '8px' }}>
                    已选 {selectedDocIds.length} 个
                  </span>
                )}
              </div>
              {documents.map((doc) => (
                <div key={doc.id} style={{ ...styles.documentItem, backgroundColor: selectedDocIds.includes(doc.id) ? '#f1f5f9' : 'transparent' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={selectedDocIds.includes(doc.id)}
                      onChange={() => toggleDocSelection(doc.id)}
                      style={{ cursor: 'pointer' }}
                    />
                    <div style={styles.documentInfo}>
                      <FileText size={16} />
                      <span style={{ fontSize: '13px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.name}</span>
                    </div>
                  </label>
                  <button style={styles.docDeleteButton} onClick={() => deleteDocument(doc.id, doc.name)} title="删除文档">
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
              {/* 使用说明 */}
              <div style={styles.selectionHint}>
                <span style={{ fontSize: '12px', color: '#64748b' }}>
                  {selectedDocIds.length > 0 ? (
                    '已选择文档进行问答，清空选择则使用全部文档'
                  ) : (
                    '选择文档后，AI 将只基于选中的文档进行回答'
                  )}
                </span>
              </div>
            </div>
          ) : (
            <div style={styles.noDocsHint}>
              暂无已上传文档
            </div>
          )}
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
    padding: '16px 24px',
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
    fontSize: '18px',
    fontWeight: 'bold',
    color: '#0f172a',
    margin: 0,
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
    width: '280px',
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
  loadingText: {
    padding: '20px',
    color: '#64748b',
    textAlign: 'center',
  },
  emptyText: {
    padding: '40px 20px',
    color: '#94a3b8',
    textAlign: 'center',
    fontSize: '13px',
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
  // 对话区域
  chatArea: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    background: '#f8fafc',
    minWidth: 0,
  },
  messagesArea: {
    flex: 1,
    overflowY: 'auto',
    padding: '32px',
    display: 'flex',
    flexDirection: 'column',
    gap: '24px',
    maxWidth: '800px',
    width: '100%',
    margin: '0 auto',
  },
  emptyChat: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    minHeight: '400px',
  },
  messageRow: {
    display: 'flex',
    width: '100%',
  },
  messageRowUser: {
    justifyContent: 'flex-end',
  },
  messageRowAssistant: {
    justifyContent: 'flex-start',
  },
  messageBubble: {
    maxWidth: '80%',
    borderRadius: '16px',
    padding: '16px 20px',
  },
  messageBubbleUser: {
    background: '#1e88e5',
    color: 'white',
    borderBottomRightRadius: '4px',
  },
  messageBubbleAssistant: {
    background: 'white',
    border: '1px solid #e2e8f0',
    borderBottomLeftRadius: '4px',
  },
  messageLabel: {
    fontSize: '11px',
    fontWeight: '600',
    marginBottom: '6px',
    opacity: 0.7,
  },
  messageText: {
    fontSize: '15px',
    lineHeight: 1.7,
    whiteSpace: 'pre-wrap',
  },
  messageSources: {
    marginTop: '16px',
    paddingTop: '12px',
    borderTop: '1px solid #e2e8f0',
  },
  sourceTag: {
    padding: '6px 12px',
    background: '#f1f5f9',
    color: '#475569',
    borderRadius: '8px',
    fontSize: '12px',
    marginBottom: '6px',
  },
  inputArea: {
    padding: '20px 32px 32px',
    background: 'white',
    borderTop: '1px solid #e2e8f0',
  },
  inputContainer: {
    display: 'flex',
    gap: '12px',
    maxWidth: '800px',
    margin: '0 auto',
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
    background: '#1e88e5',
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
  // 右侧文档管理栏
  rightSidebar: {
    width: '350px',
    background: 'white',
    borderLeft: '1px solid #e2e8f0',
    display: 'flex',
    flexDirection: 'column',
  },
  rightSidebarHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '16px 20px',
    borderBottom: '1px solid #e2e8f0',
  },
  uploadBox: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    padding: '24px',
    background: '#f8fafc',
    border: '2px dashed #cbd5e1',
    borderRadius: '12px',
    color: '#64748b',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  documentList: {
    flex: 1,
    overflowY: 'auto',
    padding: '12px',
  },
  docsSectionTitle: {
    fontSize: '12px',
    color: '#64748b',
    padding: '8px 4px',
    marginBottom: '8px',
    fontWeight: 500,
  },
  documentItem: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '10px 12px',
    borderBottom: '1px solid #f1f5f9',
    borderRadius: '8px',
    transition: 'background 0.2s',
  },
  documentInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    color: '#475569',
    overflow: 'hidden',
    flex: 1,
  },
  docDeleteButton: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '28px',
    height: '28px',
    background: 'transparent',
    border: 'none',
    borderRadius: '6px',
    color: '#94a3b8',
    cursor: 'pointer',
  },
  noDocsHint: {
    padding: '20px',
    textAlign: 'center',
    color: '#94a3b8',
    fontSize: '13px',
  },
  selectionHint: {
    padding: '12px',
    marginTop: '8px',
    background: '#f8fafc',
    borderRadius: '8px',
    textAlign: 'center',
  },
};

export default RAG;
