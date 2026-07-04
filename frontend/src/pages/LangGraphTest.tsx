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
  X,
  Database,
  HelpCircle,
  FileText,
  CheckCircle,
  Bookmark,
  Rocket,
  Wrench,
  Save
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
  isStreaming?: boolean;
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
  planMetadata?: {
    plan_summary: string;
    api_sources: { tool: string; success: boolean; summary: string }[];
    doc_sources: { name: string; chunks: number }[];
    tool_success_count: number;
    tool_total_count: number;
    tool_fail_log: { tool: string; error: string }[];
  };
}

const LangGraphTest = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const AI_API_BASE = 'http://localhost:8080/api/ai';
  const CONVERSATIONS_API = 'http://localhost:8080/api/ai/conversations';
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 解析消息内容，将 [text](/path) 和裸 /plan/123 /post/456 转为可点击链接
  const parseMessageContent = (content: string) => {
    const parts: (string | JSX.Element)[] = [];
    let lastIndex = 0;
    let keyIdx = 0;

    const makeBtn = (label: string, type: string, id: string) => {
      const path = `/${type}/${id}`;
      return (
        <button key={`link-${keyIdx++}`} onClick={() => navigate(path)} style={{
          background: 'none', border: 'none',
          color: type === 'plan' ? '#667eea' : '#10b981',
          cursor: 'pointer', textDecoration: 'underline', padding: '2px 4px',
          fontSize: 'inherit', fontFamily: 'inherit', borderRadius: '4px',
          fontWeight: 500,
        }}>
          {label}
        </button>
      );
    };

    // 匹配 markdown 链接 [显示文字](/plan/123) 或 [显示文字](/post/456)
    const mdLinkRegex = /\[([^\]]+)\]\(\s*\/(plan|post)\/(\d+)\s*\)/g;
    let match: RegExpExecArray | null;
    while ((match = mdLinkRegex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        parts.push(content.slice(lastIndex, match.index));
      }
      parts.push(makeBtn(match[1], match[2], match[3]));
      lastIndex = match.index + match[0].length;
    }

    // 匹配裸路径 /plan/123 或 /post/456
    const remaining = content.slice(lastIndex);
    let bareLastIndex = 0;
    const barePathRegex = /(^|\s)\/(plan|post)\/(\d+)(?=[\s，。！？,!?]|$)/g;
    while ((match = barePathRegex.exec(remaining)) !== null) {
      if (match.index > bareLastIndex) {
        parts.push(remaining.slice(bareLastIndex, match.index));
      }
      parts.push(makeBtn(`/${match[2]}/${match[3]}`, match[2], match[3]));
      bareLastIndex = match.index + match[0].length;
    }
    if (bareLastIndex < remaining.length) {
      parts.push(remaining.slice(bareLastIndex));
    }

    return parts.length > 0 ? <>{parts}</> : content;
  };

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
  // 多标签页隔离策略：
  // - 每个标签页有独立的 tab_id（sessionStorage）
  // - localStorage 存 {tab_id: session_id} 映射（持久化，关标签页再打开能恢复）
  // - 新标签页生成新 session_id，不影响旧标签页
  const [_tabId] = useState<string>(() => {
    let id = sessionStorage.getItem('orchestrator_tab_id');
    if (!id) {
      id = 'tab_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 6);
      sessionStorage.setItem('orchestrator_tab_id', id);
    }
    return id;
  });

  const [sessionId, setSessionIdState] = useState<string>(() => {
    const saved = localStorage.getItem('orchestrator_sessions');
    const sessions = saved ? JSON.parse(saved) : {};
    return sessions[_tabId] || '';
  });

  const setSessionId = (id: string) => {
    setSessionIdState(id);
    const saved = localStorage.getItem('orchestrator_sessions');
    const sessions = saved ? JSON.parse(saved) : {};
    if (id) {
      sessions[_tabId] = id;
    } else {
      delete sessions[_tabId];
    }
    localStorage.setItem('orchestrator_sessions', JSON.stringify(sessions));
  };
  const [debugInfo, setDebugInfo] = useState<DebugInfo | null>(null);
  const [showDebug, setShowDebug] = useState(false);
  const [showHistory, setShowHistory] = useState(true);
  const [conversations, setConversations] = useState<any[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [activeQuickAction, setActiveQuickAction] = useState<number | null>(null);

  // 判断是否处于计划流程中（从 debugInfo 的 executionTrace 推断）
  const isInPlanFlow = debugInfo?.executionTrace?.some(
    (t: any) => ["plan_mode_confirm", "plan_generator", "plan_confirmation"].includes(t.node)
  ) ?? false;

  // 快捷功能按钮配置
  const quickActions = [
    {
      label: '制定计划',
      icon: '',
      text: '制定计划',
      description: '生成各类计划',
    },
    {
      label: '搜索',
      icon: '',
      text: '搜索',
      description: '搜索计划和帖子'
    },
    {
      label: '我要打卡',
      icon: '',
      text: '我要打卡',
      description: '进行今日打卡'
    },
    {
      label: '发帖',
      icon: '',
      text: '发帖',
      description: '发布到社区'
    },
    {
      label: '知识库问答',
      icon: '',
      text: selectedDocIds.length > 0 
        ? '查询知识库' 
        : '请先在右侧选择要查询的文档',
      description: selectedDocIds.length > 0 
        ? '基于选中的文档问答' 
        : '请先选中文档'
    },
  ];

  // 快捷功能按钮点击处理
  const handleQuickAction = (text: string, index: number) => {
    if (isLoading) return;
    setQuery(text);
    setActiveQuickAction(index);
    // 自动聚焦输入框
    const input = document.querySelector('input[type="text"]') as HTMLInputElement;
    if (input) input.focus();
  };

  useEffect(() => {
    const init = async () => {
      await loadConversations();
      loadDocuments();
    };
    init();
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

    // 先插入一条空的 assistant 消息，流式过程中实时更新它
    const streamingMsg: Message = {
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      isStreaming: true
    };

    setMessages(prev => [...prev, userMessage, streamingMsg]);
    setQuery('');
    setIsLoading(true);

    try {
      const response = await fetch(`${AI_API_BASE}/orchestrator/stream`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          message: query,
          session_id: sessionId || undefined,
          user_id: user?.id || 'anonymous',
          doc_ids: selectedDocIds.length > 0 ? selectedDocIds : undefined,
        })
      });

      if (!response.ok) {
        throw new Error(`请求失败: ${response.status}`);
      }

      // 流式读取 SSE
      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let lastContent = '';
      let lastTrace: any[] = [];
      let finalSessionId = sessionId;
      let finalIntent = '';
      let finalConfidence = 0;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // 按 SSE 事件分割（\n\n 为事件分隔符）
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';

        for (const part of parts) {
          if (!part.trim()) continue;

          // 解析 SSE 格式：event: xxx\ndata: {...}
          let eventType = 'message';
          let dataStr = '';

          for (const line of part.split('\n')) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
              dataStr = line.slice(6).trim();
            }
          }

          if (!dataStr) continue;

          try {
            const data = JSON.parse(dataStr);

            if (eventType === 'response') {
              // 节点输出快照 → 更新 assistant 消息内容
              lastContent = data.content || lastContent;
              setMessages(prev => {
                const newMsgs = [...prev];
                const lastIdx = newMsgs.length - 1;
                if (newMsgs[lastIdx]?.role === 'assistant') {
                  newMsgs[lastIdx] = { ...newMsgs[lastIdx], content: lastContent };
                }
                return newMsgs;
              });
            } else if (eventType === 'trace') {
              lastTrace = [...lastTrace, ...(data.traces || [])];
            } else if (eventType === 'done') {
              // 最终完成
              lastContent = data.response || lastContent;
              finalSessionId = data.session_id || finalSessionId;
              finalIntent = data.intent || '';
              const execTrace = data.execution_trace || [];
              lastTrace = execTrace.length > 0 ? execTrace : lastTrace;

              setMessages(prev => {
                const newMsgs = [...prev];
                const lastIdx = newMsgs.length - 1;
                if (newMsgs[lastIdx]?.role === 'assistant') {
                  newMsgs[lastIdx] = {
                    ...newMsgs[lastIdx],
                    content: lastContent,
                    isStreaming: false,
                    intent: finalIntent || undefined,
                    confidence: finalConfidence || 0,
                    executionTrace: lastTrace,
                    blockedByCapability: false,
                  };
                }
                return newMsgs;
              });

              setSessionId(finalSessionId);
              setDebugInfo({
                intent: finalIntent,
                confidence: finalConfidence,
                selectedAgent: finalIntent,
                blockedByCapability: false,
                handoffReason: '',
                executionTrace: lastTrace,
                toolsCalled: lastTrace.flatMap((t: any) => t.tools_called || []),
                sessionId: finalSessionId,
                planMetadata: data.plan_metadata || undefined,
              });
            } else if (eventType === 'error') {
              lastContent = `抱歉，发生错误：${data.detail || '未知错误'}`;
              setMessages(prev => {
                const newMsgs = [...prev];
                const lastIdx = newMsgs.length - 1;
                if (newMsgs[lastIdx]?.role === 'assistant') {
                  newMsgs[lastIdx] = { ...newMsgs[lastIdx], content: lastContent, isStreaming: false };
                }
                return newMsgs;
              });
            }
          } catch {
            // JSON 解析失败，按纯文本处理
          }
        }
      }
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => {
        const newMsgs = [...prev];
        const lastIdx = newMsgs.length - 1;
        if (newMsgs[lastIdx]?.role === 'assistant') {
          newMsgs[lastIdx] = {
            ...newMsgs[lastIdx],
            content: `抱歉，请求失败：${error instanceof Error ? error.message : '未知错误'}`,
            isStreaming: false
          };
        }
        return newMsgs;
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancelPlan = async () => {
    if (!sessionId) return;
    try {
      const response = await fetch(`${AI_API_BASE}/orchestrator/cancel`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ session_id: sessionId }),
      });
      if (response.ok) {
        const cancelMsg: Message = {
          role: 'assistant',
          content: '已终止当前计划流程，您可以开始新的对话。',
          timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, cancelMsg]);
        setDebugInfo(null); // 清除调试面板，避免下次误判计划流程
      }
    } catch (error) {
      console.error('Cancel plan error:', error);
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

  const getNodeInfo = (nodeName: string, trace: any) => {
    const nodes: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
      memory_load: { label: '加载记忆', icon: <Database size={14} />, color: '#6b7280' },
      supervisor: { label: '意图识别', icon: <Target size={14} />, color: '#6366f1' },
      plan_mode_confirm: { label: '计划模式确认', icon: <HelpCircle size={14} />, color: '#f59e0b' },
      plan_generator: { label: '生成计划', icon: <FileText size={14} />, color: '#10b981' },
      plan_confirmation: { label: '确认计划', icon: <CheckCircle size={14} />, color: '#14b8a6' },
      extract_plan_title: { label: '提取计划标题', icon: <Bookmark size={14} />, color: '#0ea5e9' },
      create_plan_to_platform: { label: '创建到平台', icon: <Rocket size={14} />, color: '#8b5cf6' },
      chat: { label: '日常对话', icon: <MessageSquare size={14} />, color: '#64748b' },
      assistant: { label: '通用助手', icon: <Bot size={14} />, color: '#6366f1' },
      rag: { label: '知识库查询', icon: <Search size={14} />, color: '#06b6d4' },
      tool_calls: { label: '工具调用', icon: <Wrench size={14} />, color: '#f59e0b' },
      memory_save: { label: '保存记忆', icon: <Save size={14} />, color: '#6b7280' },
    };
    
    const base = nodes[nodeName] || { label: nodeName, icon: <Settings size={14} />, color: '#6b7280' };
    
    const details: string[] = [];
    
    if (trace?.intent) {
      details.push(`意图: ${getIntentLabel(trace.intent)}`);
    }
    if (typeof trace?.confidence === 'number') {
      details.push(`置信度: ${(trace.confidence * 100).toFixed(1)}%`);
    }
    if (trace?.selected_agent) {
      details.push(`路由到: ${getIntentLabel(trace.selected_agent)}`);
    }
    if (trace?.plan_type) {
      details.push(`计划类型: ${getIntentLabel(trace.plan_type)}`);
    }
    if (trace?.progress) {
      details.push(`进度: ${trace.progress}`);
    }
    if (trace?.plan_generated) {
      details.push('计划生成完成');
    }
    if (trace?.extracted_title) {
      details.push(`标题: ${trace.extracted_title}`);
    }
    if (trace?.plan_created) {
      details.push(`计划ID: ${trace.plan_id || '已创建'}`);
    }
    if (trace?.response_length) {
      details.push(`回复长度: ${trace.response_length} 字`);
    }
    if (trace?.error) {
      details.push(`错误: ${trace.error}`);
    }
    if (trace?.need_clarification) {
      details.push('需要用户澄清');
    }
    if (trace?.waiting_for_confirmation) {
      details.push('等待用户确认');
    }
    if (trace?.first_time) {
      details.push('首次进入');
    }
    if (trace?.result_count !== undefined) {
      details.push(`结果数量: ${trace.result_count}`);
    }
    
    return { ...base, details };
  };

  const getToolLabel = (toolName: string) => {
    const labels: Record<string, string> = {
      create_plan: '创建计划',
      create_post: '发帖',
      search_plans: '搜索计划',
      get_item_detail: '获取详情',
      get_user_activity: '获取用户动态',
      get_unchecked_plans: '获取未打卡计划',
      check_in_plan: '打卡',
      // 知识库相关
      knowledge_base: '知识库检索',
      // 天气
      get_weather_forecast: '天气预报 (Open-Meteo)',
      get_amap_weather: '天气详情 (高德)',
      // 位置与路线
      get_city_bikes: '共享单车 (CityBikes)',
      get_open_brewery: '特色饮品店',
      // 文化与学习
      search_open_library: '搜索书籍 (Open Library)',
      search_gutendex: '搜索电子书 (Gutendex)',
      search_crossref: '搜索学术论文 (Crossref)',
      search_poetrydb: '英文诗歌',
      // 营养与健康
      get_food_nutrition: '食物营养 (Open Food Facts)',
      get_fruit_nutrition: '水果营养',
      get_themealdb: '健康食谱 (TheMealDB)',
      get_wger_exercises: '推荐运动',
      calculate_bmi: 'BMI计算',
      // 日程与节假日
      get_china_holidays: '中国节假日',
      get_world_time: '世界时间',
      // 财务
      get_exchange_rates: '汇率查询',
      // 休闲与建议
      get_open_trivia: '趣味知识',
      get_bored_activity: '休闲活动',
      get_jinrishici: '今日诗词',
      get_hitokoto: '每日名句',
      get_quotable_quote: '名人名言',
      get_agify_prediction: '趣味测试',
      get_wikipedia_summary: '百科知识',
    };
    return labels[toolName] || toolName;
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
                      {msg.role === 'assistant' ? parseMessageContent(msg.content) : msg.content}
                      {msg.isStreaming && (
                        <span style={{ display: 'inline-block', marginLeft: 4, animation: 'blink 1s infinite' }}>▊</span>
                      )}
                    </div>
                    {msg.timestamp && (
                      <span style={styles.messageTime}>{formatTime(msg.timestamp)}</span>
                    )}
                  </div>
                </div>
              );
            })}

            {/* 加载状态（仅在非流式且正在加载时显示） */}
            {isLoading && !messages[messages.length - 1]?.isStreaming && (
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
            {/* 快捷功能按钮 */}
            <div style={styles.quickButtonsContainer}>
              {quickActions.map((action, index) => (
                <button
                  key={index}
                  type="button"
                  onClick={() => handleQuickAction(action.text, index)}
                  disabled={isLoading}
                  style={{
                    ...styles.quickButton,
                    ...(activeQuickAction === index ? styles.quickButtonActive : {}),
                  }}
                  title={action.description}
                >
                  {action.label}
                </button>
              ))}
            </div>

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

            {/* 终止按钮 — 仅在计划流程进行中显示 */}
            {isInPlanFlow && (
              <button
                type="button"
                onClick={handleCancelPlan}
                style={{
                  marginTop: '8px',
                  padding: '8px 16px',
                  backgroundColor: '#fee2e2',
                  color: '#dc2626',
                  border: '1px solid #fca5a5',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: 500,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  alignSelf: 'center',
                }}
              >
                <X size={16} />
                终止当前计划
              </button>
            )}
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

                  {/* 数据来源：API + 文档 */}
                  {debugInfo.planMetadata && (debugInfo.planMetadata.api_sources.length > 0 || debugInfo.planMetadata.doc_sources.length > 0) && (
                    <div>
                      <h4 style={styles.debugSectionTitle}>
                        数据来源
                      </h4>

                      {/* API 来源 */}
                      {debugInfo.planMetadata.api_sources.length > 0 && (
                        <div style={{ marginBottom: '12px' }}>
                          <div style={{ fontSize: '11px', fontWeight: 600, color: '#64748b', marginBottom: '6px' }}>
                            API 数据 ({debugInfo.planMetadata.tool_success_count}/{debugInfo.planMetadata.tool_total_count})
                          </div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            {debugInfo.planMetadata.api_sources.map((src: any, i: number) => (
                              <div key={i} style={{
                                display: 'flex', alignItems: 'center', gap: '8px',
                                padding: '6px 10px',
                                backgroundColor: src.success ? '#f0fdf4' : '#fef2f2',
                                borderRadius: '6px',
                                fontSize: '12px',
                              }}>
                                <span style={{ color: src.success ? '#16a34a' : '#dc2626' }}>
                                  {src.success ? '✓' : '✗'}
                                </span>
                                <span style={{ fontWeight: 500, color: '#1e293b' }}>{getToolLabel(src.tool)}</span>
                                {src.summary && (
                                  <span style={{ color: '#64748b', fontSize: '11px' }}>— {src.summary}</span>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* 文档来源 */}
                      {debugInfo.planMetadata.doc_sources.length > 0 && (
                        <div>
                          <div style={{ fontSize: '11px', fontWeight: 600, color: '#64748b', marginBottom: '6px' }}>
                            知识库文档
                          </div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            {debugInfo.planMetadata.doc_sources.map((src: any, i: number) => (
                              <div key={i} style={{
                                display: 'flex', alignItems: 'center', gap: '8px',
                                padding: '6px 10px',
                                backgroundColor: '#eff6ff',
                                borderRadius: '6px',
                                fontSize: '12px',
                              }}>
                                <span style={{ color: '#2563eb' }}>📄</span>
                                <span style={{ fontWeight: 500, color: '#1e293b' }}>{src.name}</span>
                                <span style={{ color: '#64748b', fontSize: '11px' }}>引用 {src.chunks} 段</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* 失败的工具（折叠显示） */}
                      {debugInfo.planMetadata.tool_fail_log.length > 0 && (
                        <details style={{ marginTop: '8px' }}>
                          <summary style={{ fontSize: '11px', color: '#92400e', cursor: 'pointer' }}>
                            ⚠ {debugInfo.planMetadata.tool_fail_log.length} 个工具调用失败
                          </summary>
                          <div style={{ marginTop: '4px', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                            {debugInfo.planMetadata.tool_fail_log.map((f: any, i: number) => (
                              <div key={i} style={{
                                padding: '4px 8px',
                                backgroundColor: '#fef2f2',
                                borderRadius: '4px',
                                fontSize: '11px',
                                color: '#991b1b',
                              }}>
                                {getToolLabel(f.tool)}: {f.error}
                              </div>
                            ))}
                          </div>
                        </details>
                      )}
                    </div>
                  )}

                  {/* 执行流程 */}
                  <div>
                    <h4 style={styles.debugSectionTitle}>
                      执行流程
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
                      {debugInfo.executionTrace.map((trace: any, index: number) => {
                        const nodeName = trace?.node || trace?.name || 'unknown';
                        const nodeInfo = getNodeInfo(nodeName, trace);
                        const isSuccess = trace?.success !== false;
                        const isLast = index === debugInfo.executionTrace.length - 1;
                        
                        return (
                          <div key={index} style={{ display: 'flex', position: 'relative' }}>
                            {/* 时间轴竖线 */}
                            {!isLast && (
                              <div style={{
                                position: 'absolute',
                                left: '15px',
                                top: '32px',
                                bottom: '-8px',
                                width: '2px',
                                backgroundColor: isSuccess ? '#e2e8f0' : '#fecaca',
                              }} />
                            )}
                            
                            {/* 节点图标 */}
                            <div style={{
                              width: '32px',
                              height: '32px',
                              borderRadius: '50%',
                              backgroundColor: isSuccess ? nodeInfo.color : '#ef4444',
                              color: 'white',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              flexShrink: 0,
                              zIndex: 1,
                              fontSize: '14px',
                              fontWeight: 600,
                              marginRight: '12px',
                            }}>
                              {isSuccess ? nodeInfo.icon : '✗'}
                            </div>
                            
                            {/* 节点内容 */}
                            <div style={{
                              flex: 1,
                              marginBottom: isLast ? '0' : '12px',
                              padding: '10px 12px',
                              backgroundColor: isSuccess ? '#f8fafc' : '#fef2f2',
                              borderRadius: '8px',
                              border: `1px solid ${isSuccess ? '#e2e8f0' : '#fecaca'}`,
                            }}>
                              <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                marginBottom: '4px',
                              }}>
                                <span style={{
                                  fontSize: '13px',
                                  fontWeight: 600,
                                  color: '#1e293b',
                                }}>
                                  {nodeInfo.label}
                                </span>
                                <span style={{
                                  fontSize: '11px',
                                  color: isSuccess ? '#64748b' : '#dc2626',
                                }}>
                                  {isSuccess ? '成功' : '失败'}
                                </span>
                              </div>
                              
                              {/* 关键信息 */}
                              {nodeInfo.details.length > 0 && (
                                <div style={{
                                  display: 'flex',
                                  flexDirection: 'column',
                                  gap: '2px',
                                  marginTop: '6px',
                                }}>
                                  {nodeInfo.details.map((detail: string, i: number) => (
                                    <div key={i} style={{
                                      fontSize: '11px',
                                      color: '#64748b',
                                      lineHeight: '1.4',
                                    }}>
                                      {detail}
                                    </div>
                                  ))}
                                </div>
                              )}
                              
                              {/* 工具调用 */}
                              {trace?.tools_called && Array.isArray(trace.tools_called) && trace.tools_called.length > 0 && (
                                <div style={{
                                  marginTop: '8px',
                                  paddingTop: '8px',
                                  borderTop: '1px dashed #e2e8f0',
                                }}>
                                  <div style={{
                                    fontSize: '11px',
                                    fontWeight: 600,
                                    color: '#475569',
                                    marginBottom: '4px',
                                  }}>
                                    调用工具
                                  </div>
                                  <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                                    {trace.tools_called.map((tool: string, i: number) => (
                                      <div key={i} style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '6px',
                                        fontSize: '11px',
                                        color: '#475569',
                                      }}>
                                        <span style={{ color: '#10b981' }}>✓</span>
                                        {getToolLabel(tool)}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
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
    flexDirection: 'column' as const,
    gap: '12px',
    padding: '20px 24px',
    background: 'white',
    boxShadow: '0 -2px 4px rgba(0, 0, 0, 0.05)',
  },
  quickButtonsContainer: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '8px',
    marginBottom: '4px',
  },
  quickButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '6px 14px',
    border: '1px solid #1e293b',
    borderRadius: '20px',
    background: 'white',
    color: '#1e293b',
    fontSize: '13px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    whiteSpace: 'nowrap' as const,
  },
  quickButtonActive: {
    background: 'rgba(30, 41, 59, 0.1)',
    border: '1px solid rgba(30, 41, 59, 0.3)',
    color: '#1e293b',
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
    background: 'white',
    border: '1px solid #1e293b',
    borderRadius: '12px',
    color: '#1e293b',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  sendButtonDisabled: {
    opacity: 0.4,
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
