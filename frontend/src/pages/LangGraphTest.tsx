import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  Zap,
  Loader2,
  Bot,
  Target,
  MessageSquare,
  Search,
  History,
  Trash2,
  Activity,
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
import PlanVisualizationPanel from '../components/PlanVisualizationPanel';
import PlanLibrary from './PlanLibrary';

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
  isStreaming?: boolean;
  streamResponse?: string;
  planMetadata?: {
    plan_summary: string;
    api_sources: { tool: string; success: boolean; summary: string }[];
    doc_sources: { name: string; chunks: number }[];
    tool_success_count: number;
    tool_total_count: number;
    tool_fail_log: { tool: string; error: string }[];
  };
}

// ─── 日志分类器（根据内容返回图标、标签、颜色）────────────────────────────────

interface LogCategory {
  icon: string;
  label: string;
  color: string;
  borderColor: string;
}

function categorizeLog(content: string): LogCategory {
  // 失败/错误
  if (/✗|失败|错误|异常|未连接|无法/i.test(content)) {
    return { icon: '✕', label: '遇到问题', color: '#e11d48', borderColor: '#fecdd3' };
  }
  // 成功完成
  if (/✓|完成|已生成|已选择|检索到|返回数据/i.test(content)) {
    return { icon: '✓', label: '完成', color: '#059669', borderColor: '#a7f3d0' };
  }
  // HTML / 杂志生成
  if (/杂志|HTML|html|预览|页面/i.test(content)) {
    return { icon: '◈', label: '排版设计', color: '#7c3aed', borderColor: '#ddd6fe' };
  }
  // 工具调用
  if (/调用|工具|tool/i.test(content)) {
    return { icon: '⚙', label: '工具调用', color: '#2563eb', borderColor: '#bfdbfe' };
  }
  // 文档检索
  if (/文档|检索|知识库|doc/i.test(content)) {
    return { icon: '❖', label: '知识检索', color: '#d97706', borderColor: '#fde68a' };
  }
  // 分析/思考
  if (/分析|选择|推理|了解|需求/i.test(content)) {
    return { icon: '◆', label: '智能分析', color: '#4f46e5', borderColor: '#c7d2fe' };
  }
  // 默认 — 生成中
  return { icon: '✦', label: '进行中', color: '#6366f1', borderColor: '#e0e7ff' };
}

const LangGraphTest = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  // 直连 Python AI 后端（不再经过 Java 中转）
  const AI_API_BASE = 'http://127.0.0.1:8000';
  const CONVERSATIONS_API = 'http://127.0.0.1:8000/conversations';
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

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
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [showDocPanel, setShowDocPanel] = useState(false);

  // 获取用户头像URL（走 Vite proxy，相对路径）
  const getFullAvatarUrl = (avatarUrl?: string) => {
    if (!avatarUrl) return null;
    if (avatarUrl.startsWith('http')) return avatarUrl;
    // /uploads/xxx 由 Java 的 ResourceHandler 直接返回，也需要走 proxy
    return avatarUrl.startsWith('/') ?avatarUrl : `/${avatarUrl}`;
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
  const [editingPlan, setEditingPlan] = useState(false);
  const [editedPlanText, setEditedPlanText] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: '您好！我是 LangGraph 智能助手，可以帮您处理以下任务：\n\n制定计划\n  - "帮我制定一个Python学习计划"\n  - "制定旅行计划"\n\n知识库问答\n  - 上传文档后，选择文档并提问\n  - "查询知识库关于XXX的文档"\n\n其他问题\n  - 任何日常对话或问题\n\n请告诉我您需要什么帮助？'
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
  const [showHistory, setShowHistory] = useState(true);
  const [showVisualization, setShowVisualization] = useState(false);
  const [showPlanLibrary, setShowPlanLibrary] = useState(false);
  const userPrefersHistoryClosed = useRef(false); // 用户是否主动偏好收起历史
  const [detailOpen, setDetailOpen] = useState(false); // 是否正在查看计划详情（HTML/打卡）
  const [mermaidCode, setMermaidCode] = useState<string>('');
  const [streamingPlanText, setStreamingPlanText] = useState<string>('');  // 流式计划文本（实时渲染）
  const [isPlanStreaming, setIsPlanStreaming] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string>('');  // iframe 预览 URL（后端生成的 HTML 页面）
  const [logs, setLogs] = useState<{ content: string; time: string }[]>([]);  // 实时执行日志
  const logsEndRef = useRef<HTMLDivElement>(null);
  const [conversations, setConversations] = useState<any[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [activeQuickAction, setActiveQuickAction] = useState<number | null>(null);

  // 判断是否处于计划流程中（从 debugInfo 的 executionTrace 推断）
  const isInPlanFlow = debugInfo?.executionTrace?.some(
    (t: any) => ["plan_mode_confirm", "plan_generator", "plan_confirmation"].includes(t.node)
  ) ?? false;

  // 快捷功能按钮配置（只保留 Python 后端能直接处理的功能）
  const quickActions = [
    {
      label: '制定计划',
      icon: '',
      text: '制定计划',
      description: '生成各类计划（保存到本地 + 推送通知）',
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
    setActiveQuickAction(index);
    // 「制定计划」不直接发送，而是填入提示语让用户填写具体内容
    if (text === '制定计划') {
      setQuery('我想制定一个关于');
    } else {
      setQuery(text);
    }
    // 自动聚焦输入框并把光标移到末尾
    setTimeout(() => {
      const input = document.querySelector('input[type="text"]') as HTMLInputElement;
      if (input) {
        input.focus();
        input.setSelectionRange(input.value.length, input.value.length);
      }
    }, 0);
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

  // 日志自动滚动到最新
  useEffect(() => {
    if (logs.length > 0) {
      logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  // 独立模式伪用户 ID — 所有 RAG 操作统一使用此 ID
  const STANDALONE_USER_ID = 'standalone_user';

  // 加载文档列表
  const loadDocuments = async () => {
    try {
      const response = await fetch(`${AI_API_BASE}/rag/documents?user_id=${STANDALONE_USER_ID}`, {
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
      // 独立模式下指定 user_id，确保与查询/长期记忆一致
      formData.append('user_id', STANDALONE_USER_ID);

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
  const handleDeleteDocument = async (docId: string) => {
    try {
      const response = await fetch(`${AI_API_BASE}/rag/documents/${docId}?user_id=${STANDALONE_USER_ID}`, {
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
  const toggleDocSelection = (docId: string) => {
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
      const userId = user?.id || 'standalone_user';
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
        content: '您好！我是 LangGraph 智能助手，可以帮您处理以下任务：\n\n制定计划\n  - "帮我制定一个Python学习计划"\n  - "制定旅行计划"\n\n知识库问答\n  - 上传文档后，选择文档并提问\n  - "查询知识库关于XXX的文档"\n\n其他问题\n  - 任何日常对话或问题\n\n请告诉我您需要什么帮助？'
      }
    ]);
    setSessionId('');
    setDebugInfo(null);
    setQuery('');
    setLogs([]);
  };

  const loadConversation = async (convSessionId: string) => {
    try {
      // Python GET /conversations/{session_id} 返回 { history: [...], ... }
      const response = await fetch(`${CONVERSATIONS_API}/${convSessionId}`, {
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

  const sendMessage = async (text: string, showUserMsg: boolean = true) => {
    if (!text.trim() || isLoading) return;

    let messagesToAdd: Message[] = [];

    if (showUserMsg) {
      const userMessage: Message = {
        role: 'user',
        content: text,
        timestamp: new Date().toISOString()
      };
      messagesToAdd.push(userMessage);
    }

    const streamingMsg: Message = {
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      isStreaming: true
    };
    messagesToAdd.push(streamingMsg);

    setMessages(prev => [...prev, ...messagesToAdd]);
    setIsLoading(true);

    setDebugInfo({
      intent: '',
      confidence: 0,
      selectedAgent: '',
      blockedByCapability: false,
      executionTrace: [],
      toolsCalled: [],
      sessionId: sessionId || '',
      isStreaming: true,
      streamResponse: '',
    });

    // 使用 WebSocket 实时流式通信（替代旧的 SSE fetch）
    const token = localStorage.getItem('token') || '';
    const WS_URL = `${AI_API_BASE.replace('http', 'ws')}/orchestrator/ws/chat`;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    let lastContent = '';
    let lastTrace: any[] = [];
    let finalSessionId = sessionId;
    let finalIntent = '';
    let finalConfidence = 0;

    ws.onopen = () => {
      ws.send(JSON.stringify({
        message: text,
        session_id: sessionId || undefined,
        user_id: user?.id || 'standalone_user',
        doc_ids: selectedDocIds.length > 0 ? selectedDocIds : undefined,
        authorization: token ? `Bearer ${token}` : '',
      }));
    };

    ws.onmessage = (event) => {
      let data: any;
      try {
        data = JSON.parse(event.data);
      } catch {
        return;
      }

      if (data.type === 'token') {
        // 段落缓冲追加（后端已按换行 flush，频率远低于逐 token）
        lastContent += data.content || '';
        // 直接更新最后一条消息的 content，不触发整个消息列表重渲染
        setMessages(prev => {
          const lastIdx = prev.length - 1;
          if (prev[lastIdx]?.role === 'assistant') {
            // 只修改最后一条，但用新引用触发渲染
            const updated = { ...prev[lastIdx], content: lastContent };
            return [...prev.slice(0, lastIdx), updated];
          }
          return prev;
        });
        // 实时更新可视化面板
        if (showVisualization) {
          setStreamingPlanText(lastContent);
        }
      } else if (data.type === 'log') {
        // 执行日志：实时显示代理执行进度
        const time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        setLogs(prev => [...prev, { content: data.content, time }]);
      } else if (data.type === 'streaming_complete') {
        // LLM 流式生成结束：立即停止打字机动画（无需等待整个图执行完）
        setMessages(prev => {
          const newMsgs = [...prev];
          const lastIdx = newMsgs.length - 1;
          if (newMsgs[lastIdx]?.role === 'assistant' && newMsgs[lastIdx].isStreaming) {
            newMsgs[lastIdx] = { ...newMsgs[lastIdx], isStreaming: false };
          }
          return newMsgs;
        });
        setIsPlanStreaming(false);
      } else if (data.type === 'html_preview_ready') {
        // HTML 生成完毕，自动打开右侧预览面板
        setPreviewUrl(data.preview_url);
        setShowVisualization(true);
      } else if (data.type === 'node_complete') {
        // LLM 生成结束（但流程可能还在继续）
        setMessages(prev => {
          const newMsgs = [...prev];
          const lastIdx = newMsgs.length - 1;
          if (newMsgs[lastIdx]?.role === 'assistant') {
            newMsgs[lastIdx] = { ...newMsgs[lastIdx], isStreaming: false };
          }
          return newMsgs;
        });
      } else if (data.type === 'done') {
        // 完整流程结束
        lastContent = data.response || lastContent;
        finalSessionId = data.session_id || finalSessionId;
        finalIntent = data.intent || finalIntent;
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
          isStreaming: false,
          streamResponse: lastContent,
          planMetadata: data.plan_metadata || undefined,
        });

        // 最终文本更新到可视化面板
        if (showVisualization) {
          setStreamingPlanText(lastContent);
          setIsPlanStreaming(false);
        }

        // 如果后端生成了 HTML 预览页面，自动切换到 iframe 预览
        if (data.preview_url) {
          setPreviewUrl(data.preview_url);
          setShowVisualization(true);
        }

        setIsLoading(false);
        wsRef.current = null;
      } else if (data.type === 'error') {
        lastContent = `抱歉，发生错误：${data.detail || '未知错误'}`;
        setMessages(prev => {
          const newMsgs = [...prev];
          const lastIdx = newMsgs.length - 1;
          if (newMsgs[lastIdx]?.role === 'assistant') {
            newMsgs[lastIdx] = { ...newMsgs[lastIdx], content: lastContent, isStreaming: false };
          }
          return newMsgs;
        });
        setDebugInfo(prev => ({
          ...(prev || { intent: '', confidence: 0, selectedAgent: '', blockedByCapability: false, executionTrace: [], toolsCalled: [], sessionId: '' }),
          isStreaming: false,
        }));
        setIsLoading(false);
        wsRef.current = null;
      }
    };

    ws.onerror = () => {
      console.error('WebSocket error');
      setMessages(prev => {
        const newMsgs = [...prev];
        const lastIdx = newMsgs.length - 1;
        if (newMsgs[lastIdx]?.role === 'assistant') {
          newMsgs[lastIdx] = {
            ...newMsgs[lastIdx],
            content: '连接失败，请检查 AI 服务是否启动 (python main.py)',
            isStreaming: false
          };
        }
        return newMsgs;
      });
      setIsLoading(false);
      wsRef.current = null;
    };

    ws.onclose = () => {
      // 如果连接关闭但还没收到 done/error，确保状态恢复
      if (isLoading) {
        setIsLoading(false);
        setMessages(prev => {
          const newMsgs = [...prev];
          const lastIdx = newMsgs.length - 1;
          if (newMsgs[lastIdx]?.role === 'assistant' && newMsgs[lastIdx]?.isStreaming) {
            newMsgs[lastIdx] = { ...newMsgs[lastIdx], isStreaming: false };
          }
          return newMsgs;
        });
      }
      wsRef.current = null;
    };
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;
    const msg = query;
    setQuery('');
    await sendMessage(msg);
  };

  const handleConfirmAction = async (answer: string) => {
    // 点击确认后立即打开右侧可视化窗口（计划生成过程中实时展示）
    if (answer === '是') {
      setShowVisualization(true);
      setStreamingPlanText('');
      setIsPlanStreaming(true);
      setPreviewUrl('');  // 清空旧的预览 URL，等待新的
      setLogs([]);  // 清空旧日志，准备记录本次执行
    }
    const payload = answer === '是' ? '__click_confirm__' : '__click_reject__';
    await sendMessage(payload, false);
  };

  const getLastNodeTrace = () => {
    if (!debugInfo?.executionTrace || debugInfo.executionTrace.length === 0) return null;
    
    const relevantNodes = ["plan_mode_confirm", "plan_generator", "plan_confirmation"];
    
    for (let i = debugInfo.executionTrace.length - 1; i >= 0; i--) {
      const trace = debugInfo.executionTrace[i];
      if (relevantNodes.includes(trace.node)) {
        return trace;
      }
    }
    
    return debugInfo.executionTrace[debugInfo.executionTrace.length - 1];
  };

  const shouldShowConfirm = (msg: Message) => {
    if (msg.isStreaming) return false;
    if (msg !== messages[messages.length - 1]) return false;
    
    const lastTrace = getLastNodeTrace();
    if (!lastTrace) {
      const patterns = [
        '点击下方按钮选择',
        '点击下方确认按钮',
        '请点击确认',
        '点击「确认」',
        '点击确认按钮',
      ];
      return patterns.some(p => msg.content.includes(p));
    }
    
    const node = lastTrace.node;
    
    if (node === 'plan_mode_confirm') return true;
    if (node === 'plan_generator' && (lastTrace.collecting_info || lastTrace.current_status === 'collecting')) {
      if (lastTrace.is_first_entry) return false;
      return true;
    }
    if (node === 'plan_confirmation' && (lastTrace.waiting_for_confirmation || lastTrace.action === 'asked_user')) return true;
    
    const patterns = [
      '点击下方按钮选择',
      '点击下方确认按钮',
      '请点击确认',
      '点击「确认」',
      '点击确认按钮',
    ];
    return patterns.some(p => msg.content.includes(p));
  };

  const shouldShowModify = (msg: Message) => {
    const lastTrace = getLastNodeTrace();
    if (lastTrace?.node === 'plan_confirmation' && lastTrace.waiting_for_confirmation) {
      return true;
    }
    return msg.content.includes('是否要将此计划创建到 PlanHub 平台');
  };

  const extractPlanText = (content: string): string => {
    let text = content;
    const genMatch = text.match(/计划已生成！\s*\n([\s\S]*?)\n\s*---\s*\n\s*是否要将此计划创建/);
    if (genMatch) {
      let plan = genMatch[1];
      plan = plan.replace(/\n\n__DATA_SOURCES__[\s\S]*?__END_DATA_SOURCES__/, '');
      return plan.trim();
    }
    const modMatch = text.match(/计划已修改！\s*\n([\s\S]*?)\n\s*---\s*\n\s*是否要将此计划创建/);
    if (modMatch) {
      let plan = modMatch[1];
      plan = plan.replace(/\n\n__DATA_SOURCES__[\s\S]*?__END_DATA_SOURCES__/, '');
      return plan.trim();
    }
    return text;
  };

  const parseDataSources = (content: string) => {
    const match = content.match(/__DATA_SOURCES__\n([\s\S]*?)\n__END_DATA_SOURCES__/);
    if (!match) return null;
    const data = match[1];
    const result: { toolData: string[]; toolFails: string[]; docData: string[] } = {
      toolData: [],
      toolFails: [],
      docData: [],
    };
    let currentSection: 'toolData' | 'toolFails' | 'docData' | null = null;
    for (const line of data.split('\n')) {
      if (line === '__TOOL_DATA__') {
        currentSection = 'toolData';
        continue;
      }
      if (line === '__TOOL_FAILS__') {
        currentSection = 'toolFails';
        continue;
      }
      if (line === '__DOC_DATA__') {
        currentSection = 'docData';
        continue;
      }
      if (currentSection) {
        result[currentSection].push(line);
      }
    }
    result.toolData = result.toolData.filter(s => s.trim());
    result.toolFails = result.toolFails.filter(s => s.trim());
    result.docData = result.docData.filter(s => s.trim());
    return result;
  };

  const handleStartEdit = (content: string) => {
    setEditedPlanText(extractPlanText(content));
    setEditingPlan(true);
  };

  const handleSaveModifiedPlan = async () => {
    const text = editedPlanText;
    setEditingPlan(false);
    setEditedPlanText('');
    await sendMessage(`__modify_plan__:${text}`, false);
  };

  const handleCancelEdit = () => {
    setEditingPlan(false);
    setEditedPlanText('');
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
      plan_writer: { label: '生成计划文本', icon: <FileText size={14} />, color: '#059669' },
      plan_confirmation: { label: '确认计划', icon: <CheckCircle size={14} />, color: '#14b8a6' },
      extract_plan_title: { label: '提取计划标题', icon: <Bookmark size={14} />, color: '#0ea5e9' },
      create_plan_to_platform: { label: '创建到平台', icon: <Rocket size={14} />, color: '#8b5cf6' },
      chat: { label: '日常对话', icon: <MessageSquare size={14} />, color: '#64748b' },
      assistant: { label: '通用助手', icon: <Bot size={14} />, color: '#6366f1' },
      rag: { label: '知识库查询', icon: <Search size={14} />, color: '#06b6d4' },
      doc_retriever: { label: '检索文档', icon: <Search size={14} />, color: '#0891b2' },
      tool_calls: { label: '工具调用', icon: <Wrench size={14} />, color: '#f59e0b' },
      tool_executor: { label: '执行工具', icon: <Wrench size={14} />, color: '#d97706' },
      memory_save: { label: '保存记忆', icon: <Save size={14} />, color: '#6b7280' },
    };

    const base = nodes[nodeName] || { label: nodeName, icon: <Settings size={14} />, color: '#6b7280' };

    const details: string[] = [];

    if (trace?.intent) {
      details.push(`意图识别: ${getIntentLabel(trace.intent)}`);
    }
    if (typeof trace?.confidence === 'number') {
      details.push(`置信度: ${(trace.confidence * 100).toFixed(1)}%`);
    }
    if (trace?.selected_agent) {
      details.push(`路由至: ${getIntentLabel(trace.selected_agent)}`);
    }
    if (trace?.plan_type) {
      details.push(`计划类型: ${getPlanTypeLabel(trace.plan_type)}`);
    }
    if (trace?.progress) {
      details.push(`进度: ${trace.progress}`);
    }
    if (trace?.plan_generated) {
      details.push('计划生成完成');
    }
    if (trace?.extracted_title) {
      details.push(`提取标题: ${trace.extracted_title}`);
    }
    if (trace?.plan_created) {
      details.push(`已创建计划ID: ${trace.plan_id || '未知'}`);
    }
    if (trace?.response_length) {
      details.push(`回复长度: ${trace.response_length} 字`);
    }
    if (trace?.error) {
      details.push(`错误: ${trace.error}`);
    }
    if (trace?.need_clarification) {
      details.push('需要用户补充信息');
    }
    if (trace?.waiting_for_confirmation) {
      details.push('等待用户确认');
    }
    if (trace?.collecting_info) {
      details.push('正在收集计划信息...');
    }
    if (trace?.first_time) {
      details.push('首次进入该节点');
    }
    if (trace?.result_count !== undefined) {
      details.push(`返回 ${trace.result_count} 条结果`);
    }
    if (trace?.rag_fallback_to_chat) {
      details.push('知识库无结果，降级为日常对话');
    }
    if (trace?.current_status) {
      details.push(`状态: ${trace.current_status}`);
    }
    if (trace?.session_id) {
      details.push(`会话: ${trace.session_id.slice(0, 8)}...`);
    }

    return { ...base, details };
  };

  const getPlanTypeLabel = (planType: string) => {
    const labels: Record<string, string> = {
      travel: '旅行计划',
      fitness: '健身计划',
      work: '工作计划',
      study: '学习计划',
      custom: '自定义计划',
      food: '美食计划',
    };
    return labels[planType] || planType;
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
        {/* 左上角历史切换按钮 */}
        <button
          style={{
            ...styles.historyToggleBtn,
            ...(detailOpen ? styles.historyToggleBtnDisabled : {}),
          }}
          onClick={() => {
            if (detailOpen) return; // 查看详情时禁止操作
            const next = !showHistory;
            userPrefersHistoryClosed.current = !next; // 记录用户主动偏好
            setShowHistory(next);
          }}
          title={detailOpen ? '查看计划详情时不可用' : '历史记录'}
        >
          <History size={20} />
        </button>

        {/* 左上角切换按钮 + 计划库按钮 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={styles.tabSwitchContainer}>
            <button
              style={{
                ...styles.tabButton,
                ...styles.tabButtonActive
              }}
            >
              plan助手
            </button>
          </div>

          {/* 计划库按钮 */}
          <button
            style={{
              ...styles.headerToolBtn,
              ...(showPlanLibrary ? styles.headerToolBtnActive : {}),
            }}
            onClick={() => {
              if (showPlanLibrary) {
                // 关闭计划库时：重置详情状态，并按用户偏好还原历史
                setDetailOpen(false);
                if (!userPrefersHistoryClosed.current) setShowHistory(true);
              }
              setShowPlanLibrary(!showPlanLibrary);
            }}
            title="计划库"
          >
            <BookOpen size={16} />
            <span>计划库</span>
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

          {/* 显示/隐藏可视化面板 */}
          <button
            style={{
              ...styles.toggleButton,
              background: showVisualization ? '#10b981' : '#f1f5f9',
              color: showVisualization ? 'white' : '#64748b',
            }}
            onClick={() => setShowVisualization(!showVisualization)}
            title={showVisualization ? '隐藏可视化' : '显示可视化'}
          >
            <Activity size={18} />
            <span>可视化</span>
          </button>
        </div>
      </div>

      <div style={styles.mainContent}>
        {/* 左侧 - 会话历史列表（默认展开，开可视化/计划库时自动收起） */}
        {showHistory && !showVisualization && (
          <div style={styles.sidebar}>
            <div style={styles.sidebarHeader}>
              <span style={styles.sidebarTitle}>对话历史</span>
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

        {/* 计划库内嵌面板（70%，仅在 showPlanLibrary 时显示） */}
        {showPlanLibrary && (
          <div style={styles.planLibraryPanel}>
            <PlanLibrary
              inline
              onClose={() => setShowPlanLibrary(false)}
              onDetailChange={(open) => {
                setDetailOpen(open);
                if (open) {
                  // 进入详情：强制收起历史
                  setShowHistory(false);
                } else {
                  // 退出详情：用户没主动收起过 → 自动展开
                  if (!userPrefersHistoryClosed.current) {
                    setShowHistory(true);
                  }
                }
              }}
            />
          </div>
        )}

        {/* 中间 - 聊天区域 */}
        <div style={showPlanLibrary ? styles.chatPanelNarrow : styles.chatArea}>
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
                  {!isUser && (
                    <div style={{
                      ...styles.avatar,
                      ...styles.assistantAvatar,
                    }}>
                      <img src="/robot-icon.png" alt="对话机器人" style={{ width: 36, height: 36 }} />
                    </div>
                  )}
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
                      {msg.role === 'assistant'
                        ? parseMessageContent(
                            msg.content
                              .replace(/\n\n__DATA_SOURCES__[\s\S]*?__END_DATA_SOURCES__/, '')
                          )
                        : msg.content}
                      {msg.isStreaming && (
                        <span style={{ display: 'inline-block', marginLeft: 4, animation: 'blink 1s infinite' }}>▊</span>
                      )}
                    </div>
                    {!isUser && !msg.isStreaming && parseDataSources(msg.content) && (
                      <div style={{
                        marginTop: '12px',
                        padding: '12px',
                        backgroundColor: '#f9fafb',
                        border: '1px solid #e5e7eb',
                        borderRadius: '8px',
                        fontSize: '13px',
                      }}>
                        {(() => {
                          const ds = parseDataSources(msg.content)!;
                          return (
                            <>
                              {ds.toolData.length > 0 && (
                                <div style={{ marginBottom: ds.docData.length > 0 ? '12px' : 0 }}>
                                  <div style={{ fontWeight: 600, color: '#059669', marginBottom: '6px' }}>
                                    调用成功的工具（{ds.toolData.length}个）
                                  </div>
                                  <div style={{
                                    color: '#374151',
                                    whiteSpace: 'pre-wrap',
                                    maxHeight: '200px',
                                    overflowY: 'auto',
                                    backgroundColor: 'white',
                                    padding: '8px 10px',
                                    borderRadius: '6px',
                                    border: '1px solid #e5e7eb',
                                  }}>
                                    {ds.toolData.join('\n')}
                                  </div>
                                </div>
                              )}
                              {ds.toolFails.length > 0 && (
                                <div style={{ marginBottom: ds.docData.length > 0 ? '12px' : 0 }}>
                                  <div style={{ fontWeight: 600, color: '#dc2626', marginBottom: '6px' }}>
                                    调用失败的工具（{ds.toolFails.length}个）
                                  </div>
                                  <div style={{
                                    color: '#374151',
                                    whiteSpace: 'pre-wrap',
                                    maxHeight: '120px',
                                    overflowY: 'auto',
                                    backgroundColor: 'white',
                                    padding: '8px 10px',
                                    borderRadius: '6px',
                                    border: '1px solid #e5e7eb',
                                  }}>
                                    {ds.toolFails.join('\n')}
                                  </div>
                                </div>
                              )}
                              {ds.docData.length > 0 && (
                                <div>
                                  <div style={{ fontWeight: 600, color: '#0891b2', marginBottom: '6px' }}>
                                    知识库检索到的文档片段（{ds.docData.length}条）
                                  </div>
                                  <div style={{
                                    color: '#374151',
                                    whiteSpace: 'pre-wrap',
                                    maxHeight: '300px',
                                    overflowY: 'auto',
                                    backgroundColor: 'white',
                                    padding: '8px 10px',
                                    borderRadius: '6px',
                                    border: '1px solid #e5e7eb',
                                  }}>
                                    {ds.docData.join('\n\n---\n\n')}
                                  </div>
                                </div>
                              )}
                            </>
                          );
                        })()}
                      </div>
                    )}
                    {!isUser && shouldShowConfirm(msg) && !editingPlan && (
                      <div style={{ marginTop: '12px' }}>
                        <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '8px' }}>
                          不想回答？创建计划请点击
                        </div>
                        <div style={{ display: 'flex', gap: '12px' }}>
                        <button
                          onClick={() => handleConfirmAction('是')}
                          disabled={isLoading}
                          style={{
                            padding: '8px 24px',
                            backgroundColor: '#3b82f6',
                            color: 'white',
                            border: 'none',
                            borderRadius: '8px',
                            cursor: isLoading ? 'not-allowed' : 'pointer',
                            fontSize: '14px',
                            fontWeight: 600,
                            opacity: isLoading ? 0.6 : 1,
                            transition: 'all 0.2s',
                          }}
                        >
                          确认
                        </button>
                        {shouldShowModify(msg) && (
                          <button
                            onClick={() => handleStartEdit(msg.content)}
                            disabled={isLoading}
                            style={{
                              padding: '8px 24px',
                              backgroundColor: 'transparent',
                              color: '#3b82f6',
                              border: '1px solid #3b82f6',
                              borderRadius: '8px',
                              cursor: isLoading ? 'not-allowed' : 'pointer',
                              fontSize: '14px',
                              fontWeight: 500,
                              opacity: isLoading ? 0.6 : 1,
                              transition: 'all 0.2s',
                            }}
                          >
                            修改
                          </button>
                        )}
                        <button
                          onClick={() => handleConfirmAction('否')}
                          disabled={isLoading}
                          style={{
                            padding: '8px 24px',
                            backgroundColor: '#f3f4f6',
                            color: '#374151',
                            border: '1px solid #d1d5db',
                            borderRadius: '8px',
                            cursor: isLoading ? 'not-allowed' : 'pointer',
                            fontSize: '14px',
                            fontWeight: 500,
                            opacity: isLoading ? 0.6 : 1,
                            transition: 'all 0.2s',
                          }}
                        >
                          取消
                        </button>
                        </div>
                      </div>
                    )}
                    {!isUser && !msg.isStreaming && editingPlan && shouldShowModify(msg) && msg === messages[messages.length - 1] && (
                      <div style={{ marginTop: '12px' }}>
                        <textarea
                          value={editedPlanText}
                          onChange={(e) => setEditedPlanText(e.target.value)}
                          style={{
                            width: '100%',
                            minHeight: '300px',
                            padding: '12px',
                            border: '1px solid #d1d5db',
                            borderRadius: '8px',
                            fontSize: '14px',
                            lineHeight: '1.6',
                            resize: 'vertical',
                            fontFamily: 'inherit',
                          }}
                          placeholder="请在此修改计划内容..."
                        />
                        <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
                          <button
                            onClick={handleSaveModifiedPlan}
                            disabled={isLoading || !editedPlanText.trim()}
                            style={{
                              padding: '8px 24px',
                              backgroundColor: '#3b82f6',
                              color: 'white',
                              border: 'none',
                              borderRadius: '8px',
                              cursor: isLoading ? 'not-allowed' : 'pointer',
                              fontSize: '14px',
                              fontWeight: 600,
                              opacity: isLoading ? 0.6 : 1,
                            }}
                          >
                            保存修改
                          </button>
                          <button
                            onClick={handleCancelEdit}
                            disabled={isLoading}
                            style={{
                              padding: '8px 24px',
                              backgroundColor: '#f3f4f6',
                              color: '#374151',
                              border: '1px solid #d1d5db',
                              borderRadius: '8px',
                              cursor: isLoading ? 'not-allowed' : 'pointer',
                              fontSize: '14px',
                              fontWeight: 500,
                            }}
                          >
                            取消
                          </button>
                        </div>
                      </div>
                    )}
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
                  <img src="/robot-icon.png" alt="AI" style={{ width: 36, height: 36 }} />
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

        {/* 右侧 - 计划预览面板（生成中显示日志，生成完毕后显示 HTML） */}
        {showVisualization && !showPlanLibrary && (
          <div style={styles.visualizationPanel}>
            {previewUrl ? (
              /* HTML 生成完毕 → 显示 iframe */
              <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
                <div style={{
                  padding: '8px 12px',
                  background: '#f8fafc',
                  borderBottom: '1px solid #e2e8f0',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexShrink: 0,
                }}>
                  <span style={{ fontSize: '12px', color: '#64748b', fontWeight: 500 }}>
                    杂志风预览
                  </span>
                  <button
                    onClick={() => {
                      setShowVisualization(false);
                      setPreviewUrl('');
                      setStreamingPlanText('');
                      setIsPlanStreaming(false);
                      setLogs([]);
                    }}
                    style={{
                      background: 'none', border: 'none', cursor: 'pointer',
                      color: '#94a3b8', padding: '4px', borderRadius: '4px',
                    }}
                    title="关闭预览"
                  >
                    <X size={14} />
                  </button>
                </div>
                <iframe
                  src={AI_API_BASE + previewUrl}
                  style={{
                    flex: 1,
                    border: 'none',
                    width: '100%',
                    background: '#fff',
                  }}
                  title="计划预览"
                  sandbox="allow-same-origin"
                />
              </div>
            ) : (
              /* 生成中 → 显示执行日志（杂志风时间线） */
              <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#faf9f6' }}>
                {/* 头部 — 进度状态条 */}
                <div style={{
                  padding: '14px 20px',
                  background: 'white',
                  borderBottom: '1px solid #e5e7eb',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  flexShrink: 0,
                }}>
                  <div style={{
                    width: 18,
                    height: 18,
                    borderRadius: '50%',
                    border: '2px solid #e5e7eb',
                    borderTopColor: '#6366f1',
                    animation: 'spin 0.8s linear infinite',
                    flexShrink: 0,
                  }} />
                  <div style={{ flex: 1 }}>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: '#1a1a2e' }}>
                      正在为您精心策划
                    </span>
                    {logs.length > 0 && (
                      <span style={{ fontSize: '12px', color: '#94a3b8', marginLeft: 8 }}>
                        已完成 {logs.length} 步
                      </span>
                    )}
                  </div>
                </div>

                {/* 日志时间线 */}
                <div style={{
                  flex: 1,
                  overflowY: 'auto',
                  padding: '20px 20px 24px',
                }}>
                  {logs.length === 0 ? (
                    <div style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      height: '100%',
                      gap: 12,
                      color: '#94a3b8',
                    }}>
                      <div style={{
                        width: 48,
                        height: 48,
                        borderRadius: '50%',
                        background: '#f1f5f9',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 20,
                      }}>✦</div>
                      <span style={{ fontSize: 13 }}>准备就绪，正在启动...</span>
                    </div>
                  ) : (
                    <div style={{ position: 'relative' }}>
                      {/* 时间线竖线 */}
                      <div style={{
                        position: 'absolute',
                        left: 9,
                        top: 18,
                        bottom: 0,
                        width: 2,
                        background: 'linear-gradient(180deg, #e0e7ff, #f1f5f9)',
                        borderRadius: 1,
                      }} />
                      {logs.map((log, i) => {
                        const cat = categorizeLog(log.content);
                        return (
                          <div
                            key={i}
                            style={{
                              display: 'flex',
                              gap: 12,
                              marginBottom: 14,
                              position: 'relative',
                              paddingLeft: 32,
                              animation: i === logs.length - 1 ? 'fadeSlideIn 0.3s ease' : undefined,
                            }}
                          >
                            {/* 时间点 */}
                            <div style={{
                              position: 'absolute',
                              left: 3,
                              top: 4,
                              width: 14,
                              height: 14,
                              borderRadius: '50%',
                              background: cat.color,
                              border: '3px solid white',
                              boxShadow: `0 0 0 2px ${cat.color}33`,
                              zIndex: 1,
                            }} />
                            {/* 内容卡片 */}
                            <div className="log-card" style={{
                              flex: 1,
                              background: 'white',
                              borderRadius: 10,
                              padding: '10px 14px',
                              border: `1px solid ${cat.borderColor}`,
                              boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
                              transition: 'box-shadow 0.2s, transform 0.2s',
                            }}>
                              <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 6,
                                marginBottom: 3,
                              }}>
                                <span style={{ fontSize: 12, lineHeight: 1 }}>{cat.icon}</span>
                                <span style={{
                                  fontSize: 10,
                                  fontWeight: 600,
                                  color: cat.color,
                                  textTransform: 'uppercase',
                                  letterSpacing: 0.5,
                                }}>{cat.label}</span>
                                <span style={{
                                  fontSize: 10,
                                  color: '#c7c9cc',
                                  marginLeft: 'auto',
                                }}>{log.time}</span>
                              </div>
                              <div style={{
                                fontSize: 13,
                                color: '#374151',
                                lineHeight: 1.6,
                              }}>{log.content}</div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                  <div ref={logsEndRef} />
                </div>
              </div>
            )}
          </div>
        )}

        {/* 右侧 - 文档管理面板 */}
        {showDocPanel && !showPlanLibrary && (
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
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .log-card:hover {
          box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
          transform: translateY(-1px);
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
  historyToggleBtn: {
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
  historyToggleBtnDisabled: {
    opacity: 0.4,
    cursor: 'not-allowed',
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
  headerToolBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '8px 14px',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    background: '#fff',
    color: '#64748b',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
  headerToolBtnActive: {
    background: '#eef2ff',
    borderColor: '#c7d2fe',
    color: '#6366f1',
  },
  sidebarHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '16px 20px',
    borderBottom: '1px solid #e2e8f0',
  },
  sidebarTitle: {
    fontSize: '15px',
    fontWeight: 600,
    color: '#0f172a',
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
    background: '#eef2ff',
    border: '1px solid #c7d2fe',
    boxShadow: '0 0 0 2px rgba(99, 102, 241, 0.15)',
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
  planLibraryPanel: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    borderRight: '1px solid #e2e8f0',
  },
  chatPanelNarrow: {
    width: '30%',
    flexShrink: 0,
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
  // 可视化面板样式（与 chatArea 等宽，各占一半）
  visualizationPanel: {
    flex: 1,
    background: 'white',
    borderLeft: '2px solid #e2e8f0',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    minWidth: 0,  // 防止 flex 子项溢出
    transition: 'flex 0.3s ease',
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
