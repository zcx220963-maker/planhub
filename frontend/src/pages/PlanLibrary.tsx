/**
 * PlanLibrary —— 计划库页面
 *
 * 布局：列表形式，每行一个计划
 * - 计划手册：点击后展开 iframe 预览 HTML
 * - 打卡详情：点击后展开日历 + 今日打卡按钮
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Calendar,
  CheckCircle,
  Circle,
  XCircle,
  ChevronLeft,
  ChevronRight,
  BookOpen,
  Flame,
  Trash2,
  Eye,
  ChevronDown,
  ChevronUp,
  Target,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const AI_API_BASE = 'http://127.0.0.1:8000';

interface Plan {
  id: number;
  title: string;
  description: string;
  category: string;
  priority: string;
  html_path: string;
  plan_text: string;
  created_at: string;
  checkin_count: number;
}

interface CalendarDay {
  status: string;
  note: string;
}

interface CalendarData {
  year: number;
  month: number;
  days: Record<string, CalendarDay>;
  total_days: number;
  checked_days: number;
  streak: number;
}

const PlanLibrary = ({ inline = false, onClose, onDetailChange }: { inline?: boolean; onClose?: () => void; onDetailChange?: (detailOpen: boolean) => void }) => {
  const navigate = useNavigate();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [expandedPlan, setExpandedPlan] = useState<number | null>(null); // 当前展开的计划 ID
  const [expandType, setExpandType] = useState<'html' | 'checkin' | null>(null); // 展开类型
  const [calendar, setCalendar] = useState<CalendarData | null>(null);
  const [currentMonth, setCurrentMonth] = useState({ year: new Date().getFullYear(), month: new Date().getMonth() + 1 });
  const [loading, setLoading] = useState(false);
  const [todayStatus, setTodayStatus] = useState<string>('');
  const [todayMap, setTodayMap] = useState<Record<number, string>>({}); // 每个计划的今日打卡状态

  // 加载计划列表
  const loadPlans = useCallback(async () => {
    try {
      const res = await fetch(`${AI_API_BASE}/plans?limit=50`);
      const data = await res.json();
      setPlans(data.plans || []);
    } catch (err) {
      console.error('加载计划失败:', err);
    }
  }, []);

  useEffect(() => {
    loadPlans();
  }, [loadPlans]);

  // 加载所有计划的今日打卡状态
  const loadAllTodayStatus = useCallback(async (planList: Plan[]) => {
    const map: Record<number, string> = {};
    for (const plan of planList) {
      try {
        const res = await fetch(`${AI_API_BASE}/plans/${plan.id}/today`);
        const data = await res.json();
        if (data.has_checkin) {
          map[plan.id] = data.checkin.status;
        }
      } catch { /* ignore */ }
    }
    setTodayMap(map);
  }, []);

  useEffect(() => {
    if (plans.length > 0) {
      loadAllTodayStatus(plans);
    }
  }, [plans, loadAllTodayStatus]);

  // 组件卸载时通知父组件重置 detailOpen
  useEffect(() => {
    return () => {
      onDetailChange?.(false);
    };
  }, []);

  // 加载日历数据
  const loadCalendar = useCallback(async (planId: number, year: number, month: number) => {
    try {
      const res = await fetch(`${AI_API_BASE}/plans/${planId}/calendar?year=${year}&month=${month}`);
      const data = await res.json();
      setCalendar(data);
    } catch (err) {
      console.error('加载日历失败:', err);
    }
  }, []);

  // 展开/收起计划
  const toggleExpand = (plan: Plan, type: 'html' | 'checkin') => {
    if (expandedPlan === plan.id && expandType === type) {
      // 收起
      setExpandedPlan(null);
      setExpandType(null);
      setCalendar(null);
      onDetailChange?.(false);
    } else {
      setExpandedPlan(plan.id);
      setExpandType(type);
      onDetailChange?.(true);
      if (type === 'checkin') {
        loadCalendar(plan.id, currentMonth.year, currentMonth.month);
        // 加载今日状态
        fetch(`${AI_API_BASE}/plans/${plan.id}/today`)
          .then(r => r.json())
          .then(d => setTodayStatus(d.has_checkin ? d.checkin.status : ''))
          .catch(() => setTodayStatus(''));
      }
    }
  };

  // 打卡
  const handleCheckin = async (planId: number, status: string) => {
    setLoading(true);
    try {
      await fetch(`${AI_API_BASE}/plans/checkin`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan_id: planId, status }),
      });
      // 刷新
      if (expandedPlan === planId) {
        loadCalendar(planId, currentMonth.year, currentMonth.month);
      }
      loadPlans();
      loadAllTodayStatus(plans);
    } catch (err) {
      console.error('打卡失败:', err);
    }
    setLoading(false);
  };

  // 删除计划
  const handleDelete = async (planId: number) => {
    if (!confirm('确定要删除这个计划吗？')) return;
    try {
      await fetch(`${AI_API_BASE}/plans/${planId}`, { method: 'DELETE' });
      if (expandedPlan === planId) {
        setExpandedPlan(null);
        setExpandType(null);
        onDetailChange?.(false);
      }
      loadPlans();
    } catch (err) {
      console.error('删除失败:', err);
    }
  };

  // 切换月份
  const changeMonth = (delta: number) => {
    if (!expandedPlan) return;
    let { year, month } = currentMonth;
    month += delta;
    if (month > 12) { month = 1; year++; }
    if (month < 1) { month = 12; year--; }
    setCurrentMonth({ year, month });
    loadCalendar(expandedPlan, year, month);
  };

  // 日历网格
  const generateCalendarGrid = () => {
    if (!calendar) return [];
    const { year, month, total_days, days } = calendar;
    const firstDay = new Date(year, month - 1, 1).getDay();
    const grid: { date: number; dateStr: string; data?: CalendarDay }[] = [];
    for (let i = 0; i < firstDay; i++) grid.push({ date: 0, dateStr: '' });
    for (let d = 1; d <= total_days; d++) {
      const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      grid.push({ date: d, dateStr, data: days[dateStr] || undefined });
    }
    return grid;
  };

  const weekDays = ['日', '一', '二', '三', '四', '五', '六'];
  const monthNames = ['一月', '二月', '三月', '四月', '五月', '六月',
    '七月', '八月', '九月', '十月', '十一月', '十二月'];

  // 当前选中的计划（用于右侧预览）
  const selectedPlan = expandedPlan ? plans.find(p => p.id === expandedPlan) : null;
  const hasDetail = selectedPlan && expandType; // 是否正在查看详情

  return (
    <div style={inline ? styles.inlineContainer : styles.container}>
      {/* 顶部导航 — inline 模式不显示 */}
      {!inline && (
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <button onClick={() => navigate('/')} style={styles.backBtn}>
            <ChevronLeft size={20} />
          </button>
          <BookOpen size={24} color="#6366f1" />
          <h1 style={styles.title}>计划库</h1>
        </div>
        <span style={styles.planCount}>{plans.length} 个计划</span>
      </header>
      )}

      {/* 主体：根据是否查看详情决定布局 */}
      <div style={styles.mainLayout}>
        {/* 左侧：计划列表（有详情时30%，无详情时80%居中） */}
        <div style={{
          ...styles.leftPanel,
          ...(hasDetail ? styles.leftPanelSplit : styles.leftPanelFull),
        }}>
          {plans.length === 0 ? (
            <div style={styles.emptyState}>
              <Target size={48} color="#e2e8f0" />
              <p style={styles.emptyText}>暂无计划</p>
              <p style={styles.emptyHint}>在对话中制定计划后会自动保存到这里</p>
            </div>
          ) : (
            plans.map(plan => {
              const isSelected = expandedPlan === plan.id;
              const todaySt = todayMap[plan.id];
              return (
                <div
                  key={plan.id}
                  style={{
                    ...styles.planCard,
                    ...(isSelected ? styles.planCardSelected : {}),
                  }}
                >
                  <div style={styles.planCardTitle}>{plan.title}</div>
                  <div style={styles.planCardMeta}>
                    <span style={styles.planDate}>
                      {new Date(plan.created_at).toLocaleDateString('zh-CN')}
                    </span>
                    {todaySt && (
                      <span style={{
                        ...styles.todayBadge,
                        background: todaySt === 'done' ? '#f0fdf4' : todaySt === 'skip' ? '#f8fafc' : '#fef2f2',
                        color: todaySt === 'done' ? '#059669' : todaySt === 'skip' ? '#64748b' : '#dc2626',
                      }}>
                        {todaySt === 'done' ? '已完成' : todaySt === 'skip' ? '已跳过' : '未完成'}
                      </span>
                    )}
                  </div>
                  {/* 操作按钮 */}
                  <div style={styles.planCardActions} onClick={e => e.stopPropagation()}>
                    <button
                      style={{
                        ...styles.smallBtn,
                        ...(isSelected && expandType === 'html' ? styles.smallBtnActive : {}),
                      }}
                      onClick={() => toggleExpand(plan, 'html')}
                      title="查看手册"
                    >
                      <Eye size={13} />
                    </button>
                    <button
                      style={{
                        ...styles.smallBtn,
                        ...(isSelected && expandType === 'checkin' ? styles.smallBtnActive : {}),
                      }}
                      onClick={() => {
                        toggleExpand(plan, 'checkin');
                      }}
                      title="打卡详情"
                    >
                      <Calendar size={13} />
                    </button>
                    <button
                      style={styles.smallBtn}
                      onClick={() => handleDelete(plan.id)}
                      title="删除"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* 右侧：预览/详情面板（70%，仅在查看详情时显示） */}
        {hasDetail && (
        <div style={styles.rightPanel}>
          {expandType === 'html' ? (
            /* HTML 预览 iframe */
            <div style={styles.htmlPreview}>
              <div style={styles.previewHeader}>
                <button
                  style={styles.closeDetailBtn}
                  onClick={() => { setExpandedPlan(null); setExpandType(null); onDetailChange?.(false); }}
                  title="返回列表"
                >
                  <ChevronLeft size={16} />
                </button>
                <span style={styles.previewTitle}>{selectedPlan.title}</span>
              </div>
              <iframe
                src={`${AI_API_BASE}/plans/${selectedPlan.id}/preview`}
                style={styles.previewFrame}
                title="计划预览"
                sandbox="allow-same-origin"
              />
            </div>
          ) : (
            /* 打卡详情 */
            /* 打卡详情 */
            <div style={styles.checkinDetail}>
              <div style={styles.checkinTop}>
                <div style={styles.checkinStats}>
                  <div style={styles.statItem}>
                    <Flame size={16} color="#f59e0b" />
                    <span style={styles.statVal}>{calendar?.streak || 0}</span>
                    <span style={styles.statLbl}>连续天数</span>
                  </div>
                  <div style={styles.statItem}>
                    <CheckCircle size={16} color="#10b981" />
                    <span style={styles.statVal}>{calendar?.checked_days || 0}</span>
                    <span style={styles.statLbl}>本月完成</span>
                  </div>
                  <div style={styles.statItem}>
                    <Calendar size={16} color="#6366f1" />
                    <span style={styles.statVal}>{selectedPlan.checkin_count}</span>
                    <span style={styles.statLbl}>累计打卡</span>
                  </div>
                </div>
                <div style={styles.todayCheckinBtns}>
                  <button
                    style={{ ...styles.todayBtn, ...styles.todayBtnDone, ...(todayStatus === 'done' ? styles.todayBtnActive : {}) }}
                    onClick={() => handleCheckin(selectedPlan.id, 'done')}
                    disabled={loading}
                  >
                    <CheckCircle size={14} /> 完成
                  </button>
                  <button
                    style={{ ...styles.todayBtn, ...styles.todayBtnSkip, ...(todayStatus === 'skip' ? styles.todayBtnActive : {}) }}
                    onClick={() => handleCheckin(selectedPlan.id, 'skip')}
                    disabled={loading}
                  >
                    <Circle size={14} /> 跳过
                  </button>
                  <button
                    style={{ ...styles.todayBtn, ...styles.todayBtnFail, ...(todayStatus === 'fail' ? styles.todayBtnActive : {}) }}
                    onClick={() => handleCheckin(selectedPlan.id, 'fail')}
                    disabled={loading}
                  >
                    <XCircle size={14} /> 未完成
                  </button>
                </div>
              </div>

              {/* 月份导航 */}
              <div style={styles.monthNav}>
                <button onClick={() => changeMonth(-1)} style={styles.monthBtn}><ChevronLeft size={16} /></button>
                <span style={styles.monthLabel}>{currentMonth.year}年 {monthNames[currentMonth.month - 1]}</span>
                <button onClick={() => changeMonth(1)} style={styles.monthBtn}><ChevronRight size={16} /></button>
              </div>

              {/* 日历 */}
              <div style={styles.calGrid}>
                {weekDays.map(d => <div key={d} style={styles.weekDay}>{d}</div>)}
                {generateCalendarGrid().map((cell, idx) => (
                  <div
                    key={idx}
                    style={{
                      ...styles.calDay,
                      ...(cell.data?.status === 'done' ? styles.calDayDone :
                          cell.data?.status === 'skip' ? styles.calDaySkip :
                          cell.data?.status === 'fail' ? styles.calDayFail : {}),
                      ...(cell.date === 0 ? styles.calDayEmpty : {}),
                    }}
                    title={cell.data?.note || ''}
                  >
                    {cell.date > 0 && (
                      <>
                        <span style={styles.calNum}>{cell.date}</span>
                        {cell.data?.status === 'done' && <CheckCircle size={9} color="#10b981" />}
                        {cell.data?.status === 'skip' && <Circle size={9} color="#94a3b8" />}
                        {cell.data?.status === 'fail' && <XCircle size={9} color="#ef4444" />}
                      </>
                    )}
                  </div>
                ))}
              </div>

              {/* 图例 */}
              <div style={styles.legend}>
                <span><CheckCircle size={11} color="#10b981" /> 完成</span>
                <span><Circle size={11} color="#94a3b8" /> 跳过</span>
                <span><XCircle size={11} color="#ef4444" /> 未完成</span>
              </div>
            </div>
          )}
        </div>
        )}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    background: '#f8fafc',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif',
  },
  inlineContainer: {
    display: 'flex',
    flexDirection: 'column',
    flex: 1,
    overflow: 'hidden',
    background: '#f8fafc',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '16px 24px',
    background: '#fff',
    borderBottom: '1px solid #e2e8f0',
    flexShrink: 0,
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  backBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: '#64748b',
    padding: '4px',
    borderRadius: '6px',
    display: 'flex',
    alignItems: 'center',
  },
  title: {
    fontSize: '20px',
    fontWeight: 700,
    color: '#1a1a2e',
    margin: 0,
  },
  planCount: {
    fontSize: '13px',
    color: '#64748b',
    background: '#f1f5f9',
    padding: '4px 12px',
    borderRadius: '12px',
  },
  // 主体左右分栏
  mainLayout: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
  },
  // 左侧计划列表容器
  leftPanel: {
    overflowY: 'auto',
    background: '#f8fafc',
    padding: '12px',
    transition: 'all 0.2s ease',
  },
  // 查看详情时：30% 宽度，右侧有边框
  leftPanelSplit: {
    width: '30%',
    minWidth: '240px',
    maxWidth: '360px',
    borderRight: '1px solid #e2e8f0',
  },
  // 未查看详情时：80% 宽度，居中
  leftPanelFull: {
    width: '80%',
    margin: '0 auto',
    borderRight: 'none',
  },
  planCard: {
    background: '#fff',
    borderRadius: '10px',
    border: '1px solid #e2e8f0',
    padding: '12px 14px',
    marginBottom: '8px',
    cursor: 'pointer',
    transition: 'all 0.15s',
    position: 'relative',
  },
  planCardSelected: {
    borderColor: '#6366f1',
    boxShadow: '0 0 0 2px rgba(99, 102, 241, 0.15)',
    background: '#fafaff',
  },
  planCardTitle: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#1a1a2e',
    marginBottom: '6px',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    paddingRight: '72px',
  },
  planCardMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  planCardActions: {
    position: 'absolute',
    top: '10px',
    right: '10px',
    display: 'flex',
    gap: '4px',
  },
  smallBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '28px',
    height: '28px',
    border: '1px solid #e2e8f0',
    borderRadius: '6px',
    background: '#fff',
    cursor: 'pointer',
    color: '#94a3b8',
    transition: 'all 0.15s',
  },
  smallBtnActive: {
    background: '#6366f1',
    borderColor: '#6366f1',
    color: '#fff',
  },
  // 右侧预览面板（70%）
  rightPanel: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    background: '#fff',
  },
  rightPlaceholder: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
  },
  rightPlaceholderText: {
    fontSize: '14px',
    color: '#94a3b8',
    margin: 0,
  },
  // HTML 预览
  htmlPreview: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    background: '#f8fafc',
  },
  previewHeader: {
    padding: '10px 16px',
    background: '#fff',
    borderBottom: '1px solid #e2e8f0',
    flexShrink: 0,
    display: 'flex',
    alignItems: 'center',
  },
  closeDetailBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: '#64748b',
    padding: '4px',
    borderRadius: '6px',
    display: 'flex',
    alignItems: 'center',
    marginRight: '8px',
  },
  previewTitle: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#1a1a2e',
  },
  previewFrame: {
    flex: 1,
    width: '100%',
    border: 'none',
    background: '#fff',
  },
  planDate: {
    fontSize: '12px',
    color: '#94a3b8',
    whiteSpace: 'nowrap',
  },
  todayBadge: {
    fontSize: '11px',
    fontWeight: 500,
    padding: '2px 8px',
    borderRadius: '10px',
    whiteSpace: 'nowrap',
  },
  // 打卡详情
  checkinDetail: {
    padding: '20px',
  },
  checkinTop: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '20px',
    flexWrap: 'wrap',
    gap: '12px',
  },
  checkinStats: {
    display: 'flex',
    gap: '16px',
  },
  statItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '8px 14px',
    background: '#f8fafc',
    borderRadius: '10px',
    border: '1px solid #e2e8f0',
  },
  statVal: {
    fontSize: '18px',
    fontWeight: 700,
    color: '#1a1a2e',
  },
  statLbl: {
    fontSize: '11px',
    color: '#64748b',
  },
  todayCheckinBtns: {
    display: 'flex',
    gap: '8px',
  },
  todayBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    padding: '8px 14px',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    background: '#fff',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 500,
    color: '#64748b',
    transition: 'all 0.15s',
  },
  todayBtnDone: { borderColor: '#a7f3d0', color: '#059669' },
  todayBtnSkip: { borderColor: '#e2e8f0', color: '#64748b' },
  todayBtnFail: { borderColor: '#fecaca', color: '#dc2626' },
  todayBtnActive: { borderWidth: '2px', fontWeight: 600 },
  // 月份
  monthNav: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '16px',
    marginBottom: '12px',
  },
  monthBtn: {
    background: '#fff',
    border: '1px solid #e2e8f0',
    borderRadius: '6px',
    cursor: 'pointer',
    padding: '4px',
    display: 'flex',
    alignItems: 'center',
    color: '#64748b',
  },
  monthLabel: {
    fontSize: '15px',
    fontWeight: 600,
    color: '#1a1a2e',
    minWidth: '120px',
    textAlign: 'center',
  },
  // 日历
  calGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(7, 1fr)',
    gap: '3px',
    marginBottom: '12px',
  },
  weekDay: {
    textAlign: 'center',
    fontSize: '11px',
    fontWeight: 600,
    color: '#94a3b8',
    padding: '4px 0',
  },
  calDay: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '2px',
    padding: '6px 0',
    borderRadius: '8px',
    minHeight: '38px',
    border: '2px solid transparent',
  },
  calDayEmpty: { visibility: 'hidden' },
  calDayDone: { background: '#f0fdf4', borderColor: '#a7f3d0' },
  calDaySkip: { background: '#f8fafc', borderColor: '#e2e8f0' },
  calDayFail: { background: '#fef2f2', borderColor: '#fecaca' },
  calNum: {
    fontSize: '12px',
    color: '#1a1a2e',
    fontWeight: 500,
  },
  legend: {
    display: 'flex',
    justifyContent: 'center',
    gap: '20px',
    paddingTop: '8px',
    borderTop: '1px solid #f1f5f9',
    fontSize: '11px',
    color: '#64748b',
  },
  // 空状态
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '80px 20px',
    textAlign: 'center',
  },
  emptyText: {
    fontSize: '16px',
    color: '#64748b',
    margin: '16px 0 4px',
  },
  emptyHint: {
    fontSize: '13px',
    color: '#94a3b8',
    margin: 0,
  },
};

export default PlanLibrary;
