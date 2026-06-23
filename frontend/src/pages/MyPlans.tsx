import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Plus, Edit2, Trash2, ChevronRight, Search, Filter, X, CheckCircle, Calendar, Share2, Users, MessageCircle, Heart } from 'lucide-react';
import { planApi, checkinApi, chatApi } from '../services/api';
import type { Plan, ChatConversation } from '../types';

const MyPlans: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingPlan, setEditingPlan] = useState<Plan | null>(null);
  const [formData, setFormData] = useState<Omit<Plan, 'id' | 'createdAt' | 'updatedAt'>>({
    userId: 0,
    title: '',
    description: '',
    category: 'PERSONAL',
    priority: 'MEDIUM',
    status: 'ACTIVE',
    targetDate: '',
    startDate: '',
    estimatedDurationDays: undefined,
    actualDurationDays: undefined,
    progressPercentage: 0,
    visibility: 'PRIVATE',
    completedAt: undefined,
  });
  const [checkedInToday, setCheckedInToday] = useState<{ [key: number]: boolean }>({});
  const [checkinCounts, setCheckinCounts] = useState<{ [key: number]: number }>({});
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [detailPlan, setDetailPlan] = useState<Plan | null>(null);
  const [detailCheckins, setDetailCheckins] = useState<any[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [showCheckinModal, setShowCheckinModal] = useState(false);
  const [checkinPlanId, setCheckinPlanId] = useState<number | null>(null);
  const [checkinFormData, setCheckinFormData] = useState({
    notes: '',
    moodRating: 3,
    energyRating: 3,
    progressNotes: '',
    tags: '',
  });

  // 分享功能状态
  const [showShareModal, setShowShareModal] = useState(false);
  const [shareContent, setShareContent] = useState('');
  const [shareMode, setShareMode] = useState<'community' | 'chat'>('community');
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [selectedReceiver, setSelectedReceiver] = useState<number | null>(null);
  const [loadingConversations, setLoadingConversations] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);

  useEffect(() => {
    const statusParam = searchParams.get('status');
    if (statusParam) {
      const statusMap: { [key: string]: string } = {
        'active': 'ACTIVE',
        'completed': 'COMPLETED',
        'pending': 'PENDING'
      };
      const mappedStatus = statusMap[statusParam.toLowerCase()] || 'all';
      setFilter(mappedStatus);
    }
    loadPlans();

    const planIdParam = searchParams.get('planId');
    if (planIdParam) {
      const planId = parseInt(planIdParam, 10);
      if (!isNaN(planId)) {
        planApi.getPlanById(planId)
          .then((plan) => {
            setDetailPlan(plan);
            setShowDetailModal(true);
          })
          .catch((err) => {
            console.error('Failed to load plan detail:', err);
          });
      }
    }

    const createParam = searchParams.get('create');
    if (createParam === 'true') {
      setShowModal(true);
    }
  }, [searchParams]);

  useEffect(() => {
    loadPlans();
  }, [filter]);

  // 计算两个日期之间的天数
  const calculateDays = (startDate: string, endDate: string): number => {
    if (!startDate || !endDate) return 0;
    const start = new Date(startDate);
    const end = new Date(endDate);
    const diffTime = Math.abs(end.getTime() - start.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays + 1; // 包含开始和结束日期
  };

  // 当开始日期或目标日期变化时，自动计算预计天数
  useEffect(() => {
    if (formData.startDate && formData.targetDate) {
      const days = calculateDays(formData.startDate, formData.targetDate);
      setFormData(prev => ({ ...prev, estimatedDurationDays: days }));
    }
  }, [formData.startDate, formData.targetDate]);

  const loadPlans = () => {
    setLoading(true);
    planApi.getAllPlans()
      .then(async (data) => {
        const plansWithLikeStatus = await Promise.all(
          data.map(async (plan) => {
            try {
              const status = await planApi.getPlanInteractionStatus(plan.id);
              return { 
                ...plan, 
                liked: status.liked, 
                likeCount: status.likeCount 
              };
            } catch (err) {
              return plan;
            }
          })
        );
        setPlans(plansWithLikeStatus);
        plansWithLikeStatus.forEach(plan => {
          checkCheckinStatus(plan.id);
        });
        const counts = await Promise.all(
          plansWithLikeStatus.map(async (plan) => {
            try {
              const checkins = await checkinApi.getCheckinsByPlanId(plan.id);
              return { planId: plan.id, count: checkins.length };
            } catch (err) {
              return { planId: plan.id, count: 0 };
            }
          })
        );
        const countMap: { [key: number]: number } = {};
        counts.forEach(item => {
          countMap[item.planId] = item.count;
        });
        setCheckinCounts(countMap);
      })
      .catch(() => setPlans([]))
      .finally(() => setLoading(false));
  };

  const checkCheckinStatus = async (planId: number) => {
    try {
      const exists = await checkinApi.checkCheckinExists(planId);
      setCheckedInToday(prev => ({ ...prev, [planId]: exists }));
    } catch (err) {
      console.error('Failed to check checkin status:', err);
    }
  };

  const openCheckinModal = (planId: number) => {
    if (checkedInToday[planId]) {
      alert('今天已经打卡过了');
      return;
    }
    setCheckinPlanId(planId);
    setCheckinFormData({
      notes: '',
      moodRating: 3,
      energyRating: 3,
      progressNotes: '',
      tags: '',
    });
    setShowCheckinModal(true);
  };

  const handleCheckinSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!checkinPlanId) return;

    try {
      await checkinApi.checkin(checkinPlanId, {
        notes: checkinFormData.notes || '今日打卡',
        moodRating: checkinFormData.moodRating,
        energyRating: checkinFormData.energyRating,
        progressNotes: checkinFormData.progressNotes,
      });
      setCheckedInToday(prev => ({ ...prev, [checkinPlanId]: true }));
      loadPlans();
      setShowCheckinModal(false);
      alert('打卡成功！');
    } catch (err) {
      alert('打卡失败');
    }
  };

  const openDetailModal = async (plan: Plan) => {
    setDetailPlan(plan);
    setShowDetailModal(true);
    setDetailLoading(true);
    try {
      const checkins = await checkinApi.getCheckinsByPlanId(plan.id);
      setDetailCheckins(checkins);
    } catch (err) {
      setDetailCheckins([]);
    } finally {
      setDetailLoading(false);
    }
  };

  const filteredPlans = plans.filter((plan) => {
    const matchesFilter = filter === 'all' || plan.status.toLowerCase() === filter.toLowerCase();
    const matchesSearch = plan.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (plan.description && plan.description.toLowerCase().includes(searchTerm.toLowerCase()));
    return matchesFilter && matchesSearch;
  });

  const deletePlan = (id: number) => {
    if (window.confirm('确定要删除这个计划吗？')) {
      planApi.deletePlan(id)
        .then(() => {
          setPlans(plans.filter(p => p.id !== id));
        })
        .catch(() => alert('删除失败'));
    }
  };

  // 分享功能
  const loadConversations = async () => {
    setLoadingConversations(true);
    try {
      const convos = await chatApi.getConversations();
      setConversations(convos);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    } finally {
      setLoadingConversations(false);
    }
  };

  const handleShare = (plan: Plan) => {
    setSelectedPlan(plan);
    setShareContent('');
    setShareMode('community');
    setSelectedReceiver(null);
    setShowShareModal(true);
    loadConversations();
  };

  const handleConfirmShare = async () => {
    if (!selectedPlan) return;
    try {
      if (shareMode === 'community') {
        await planApi.sharePlanToCommunity(selectedPlan.id, shareContent);
        alert('分享成功！');
      } else if (shareMode === 'chat' && selectedReceiver) {
        await chatApi.sharePlanToChat(selectedReceiver, selectedPlan.id, shareContent);
        alert('分享成功！');
      }
      setShowShareModal(false);
    } catch (err) {
      alert('分享失败，请重试');
    }
  };

  // 点赞功能
  const handleLike = async (plan: Plan) => {
    try {
      if (plan.liked) {
        const result = await planApi.unlikePlan(plan.id);
        setPlans(plans.map(p => 
          p.id === plan.id 
            ? { ...p, liked: result.liked, likeCount: result.likeCount } 
            : p
        ));
      } else {
        const result = await planApi.likePlan(plan.id);
        setPlans(plans.map(p => 
          p.id === plan.id 
            ? { ...p, liked: result.liked, likeCount: result.likeCount } 
            : p
        ));
      }
    } catch (err) {
      alert('操作失败，请重试');
    }
  };

  const openCreateModal = () => {
    setEditingPlan(null);
    setFormData({
      userId: 0,
      title: '',
      description: '',
      category: 'PERSONAL',
      priority: 'MEDIUM',
      status: 'ACTIVE',
      targetDate: '',
      startDate: '',
      estimatedDurationDays: undefined,
      actualDurationDays: undefined,
      progressPercentage: 0,
      visibility: 'PRIVATE',
      completedAt: undefined,
    });
    setShowModal(true);
  };

  const openEditModal = (plan: Plan) => {
    setEditingPlan(plan);

    // 计算预计天数
    let estimatedDays = plan.estimatedDurationDays;
    if (plan.startDate && plan.targetDate) {
      estimatedDays = calculateDays(plan.startDate, plan.targetDate);
    }

    setFormData({
      userId: plan.userId || 0,
      title: plan.title,
      description: plan.description || '',
      category: plan.category || 'PERSONAL',
      priority: plan.priority || 'MEDIUM',
      status: plan.status || 'ACTIVE',
      targetDate: plan.targetDate || '',
      startDate: plan.startDate || '',
      estimatedDurationDays: estimatedDays,
      actualDurationDays: checkinCounts[plan.id] || 0,
      progressPercentage: plan.progressPercentage || 0,
      visibility: plan.visibility || 'PRIVATE',
      completedAt: plan.completedAt,
    });
    setShowModal(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingPlan) {
      // 重新计算进度
      const checkinCount = checkinCounts[editingPlan.id] || 0;
      let newProgressPercentage = formData.progressPercentage;

      if (formData.targetDate && formData.startDate) {
        const totalDays = calculateDays(formData.startDate, formData.targetDate);
        if (totalDays > 0) {
          newProgressPercentage = Math.min(100, Math.round((checkinCount / totalDays) * 100));
        }
      } else if (formData.targetDate) {
        // 只有目标日期，没有开始日期，使用当前已打卡天数
        const targetDate = new Date(formData.targetDate);
        const startDate = new Date(editingPlan.startDate || editingPlan.createdAt);
        const totalDays = Math.max(1, Math.ceil((targetDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)));
        newProgressPercentage = Math.min(100, Math.round((checkinCount / totalDays) * 100));
      }

      planApi.updatePlan(editingPlan.id, {
        title: formData.title,
        description: formData.description,
        category: formData.category,
        priority: formData.priority,
        status: formData.status,
        targetDate: formData.targetDate || undefined,
        startDate: formData.startDate || undefined,
        estimatedDurationDays: formData.estimatedDurationDays,
        actualDurationDays: checkinCount,
        progressPercentage: newProgressPercentage,
        visibility: formData.visibility,
        completedAt: formData.completedAt,
      })
        .then((updated) => {
          setPlans(plans.map(p => p.id === updated.id ? updated : p));
          setShowModal(false);
        })
        .catch(() => alert('更新失败'));
    } else {
      const createData = {
        title: formData.title,
        description: formData.description,
        category: formData.category,
        priority: formData.priority,
        status: formData.status,
        targetDate: formData.targetDate || undefined,
        startDate: formData.startDate || undefined,
        estimatedDurationDays: formData.estimatedDurationDays,
        visibility: formData.visibility,
      };
      planApi.createPlan(createData)
        .then((newPlan) => {
          setPlans([newPlan, ...plans]);
          setShowModal(false);
        })
        .catch(() => alert('创建失败'));
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'COMPLETED': return '#10b981';
      case 'ACTIVE': return '#0ea5e9';
      case 'PENDING': return '#f59e0b';
      case 'PAUSED': return '#64748b';
      case 'CANCELLED': return '#ef4444';
      case 'DRAFT': return '#64748b';
      default: return '#64748b';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'COMPLETED': return '已完成';
      case 'ACTIVE': return '进行中';
      case 'PENDING': return '待开始';
      case 'PAUSED': return '已暂停';
      case 'CANCELLED': return '已取消';
      case 'DRAFT': return '草稿';
      default: return status;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'URGENT': return '#ef4444';
      case 'HIGH': return '#f97316';
      case 'MEDIUM': return '#f59e0b';
      case 'LOW': return '#10b981';
      default: return '#64748b';
    }
  };

  const getCategoryText = (category: string) => {
    switch (category) {
      case 'PERSONAL': return '个人';
      case 'LEARNING': return '学习';
      case 'FITNESS': return '健身';
      case 'HABIT': return '习惯';
      case 'CAREER': return '职业';
      case 'HEALTH': return '健康';
      case 'CREATIVE': return '创意';
      case 'OTHER': return '其他';
      default: return category;
    }
  };

  const filters = [
    { key: 'all', label: '全部' },
    { key: 'pending', label: '待开始' },
    { key: 'active', label: '进行中' },
    { key: 'completed', label: '已完成' },
  ];

  const calculatePlanDays = (plan: Plan) => {
    if (plan.startDate && plan.targetDate) {
      const start = new Date(plan.startDate);
      const end = new Date(plan.targetDate);
      return Math.max(0, Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1);
    }
    return 0;
  };

  const renderStars = (rating: number, max: number = 5) => {
    return Array.from({ length: max }, (_, i) => (
      <span key={i} style={{
        fontSize: '18px',
        color: i < rating ? '#fbbf24' : '#e5e7eb',
      }}>★</span>
    ));
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.headerContent}>
          <h1 style={styles.title}>我的计划</h1>
          <p style={styles.subtitle}>管理和追踪您的所有计划</p>
        </div>
        <div style={styles.headerRight}>
          <div style={styles.dateBadge}>
            <Calendar size={16} />
            <span>{new Date().toLocaleDateString('zh-CN')}</span>
          </div>
        </div>
      </div>

      <div style={styles.containerInner}>
      <div style={styles.toolbar}>
        <div style={styles.searchWrapper}>
          <Search size={18} style={styles.searchIcon} />
          <input
            type="text"
            placeholder="搜索计划..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={styles.searchInput}
          />
        </div>

        <div style={styles.filterWrapper}>
          <Filter size={18} style={styles.filterIcon} />
          <div style={styles.filterTabs}>
            {filters.map((f) => (
              <button
                key={f.key}
                onClick={() => setFilter(f.key)}
                style={{
                  ...styles.filterTab,
                  ...(filter === f.key && styles.filterTabActive),
                }}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading ? (
        <div style={styles.loading}>加载中...</div>
      ) : (
        <div style={styles.plansGrid} className="plans-grid">
          {filteredPlans.map((plan) => (
            <div key={plan.id} style={styles.planCard} className="plan-card">
              <div style={styles.cardHeader}>
                <div style={styles.badgeGroup}>
                  <div style={styles.daysRemainingBadge}>
                    <span>已打卡 {checkinCounts[plan.id] || 0} 天</span>
                  </div>
                  {plan.targetDate && (
                    <div style={styles.daysRemainingBadge}>
                      <span>还剩 {Math.max(0, Math.ceil((new Date(plan.targetDate).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24)))} 天</span>
                    </div>
                  )}
                </div>
                <div style={styles.headerActions}>
                  <button
                    className="like-btn"
                    style={{
                      ...styles.likeButton,
                      color: plan.liked ? '#ef4444' : '#666',
                    }}
                    onClick={() => handleLike(plan)}
                  >
                    <Heart size={18} fill={plan.liked ? '#ef4444' : 'none'} />
                    <span style={styles.likeCount}>{plan.likeCount || 0}</span>
                  </button>
                  <button
                    className="share-btn"
                    style={styles.shareButton}
                    onClick={() => handleShare(plan)}
                  >
                    <Share2 size={18} />
                  </button>
                </div>
              </div>

              <div style={styles.cardContent}>
                <h3 style={styles.planTitle}>{plan.title}</h3>
                <p style={styles.planDescription}>{plan.description || '暂无描述'}</p>

                <div style={styles.planMeta}>
                  <span style={styles.statusBadge}>
                    {getStatusText(plan.status)}
                  </span>
                  <span style={styles.cardDateBadge}>
                    {new Date(plan.createdAt).toLocaleDateString('zh-CN')}
                  </span>
                </div>

                <div style={styles.progressSection}>
                  <div style={styles.progressHeader}>
                    <span style={styles.progressLabel}>完成进度</span>
                    <span style={styles.progressValue}>{plan.progressPercentage}%</span>
                  </div>
                  <div style={styles.progressBar} className="progress-bar-bg">
                    <div
                      style={{
                        ...styles.progressFill,
                        width: `${plan.progressPercentage}%`,
                      }}
                      className="progress-fill"
                    ></div>
                  </div>
                </div>
              </div>

              <div style={styles.cardActions}>
                <button className="action-btn" style={styles.actionButton} onClick={() => openEditModal(plan)}>
                  <Edit2 size={16} />
                  <span>编辑</span>
                </button>
                <button className="action-btn" style={styles.actionButton} onClick={() => deletePlan(plan.id)}>
                  <Trash2 size={16} />
                  <span>删除</span>
                </button>
                <button
                  className="checkin-btn"
                  style={{
                    ...styles.checkinButton,
                    ...(checkedInToday[plan.id] ? styles.checkinButtonDisabled : {}),
                  }}
                  onClick={() => openCheckinModal(plan.id)}
                  disabled={checkedInToday[plan.id]}
                >
                  <Calendar size={16} />
                  <span>{checkedInToday[plan.id] ? '已打卡' : '打卡'}</span>
                </button>
                <button className="primary-btn" style={styles.actionButtonPrimary} onClick={() => openDetailModal(plan)}>
                  <span>查看详情</span>
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && filteredPlans.length === 0 && (
        <div style={styles.emptyState}>
          <div style={styles.emptyIcon}>
            <Plus size={48} />
          </div>
          <h3 style={styles.emptyTitle}>暂无计划</h3>
          <p style={styles.emptyDescription}>点击上方按钮创建您的第一个计划</p>
        </div>
      )}

      {showModal && (
        <div style={styles.modalOverlay} onClick={() => setShowModal(false)}>
          <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h2 style={styles.modalTitle}>{editingPlan ? '编辑计划' : '创建计划'}</h2>
              <button style={styles.closeButton} onClick={() => setShowModal(false)}>
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSubmit} style={styles.form}>
              <div style={styles.formGroup}>
                <label style={styles.label}>计划标题 *</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  style={styles.input}
                  placeholder="请输入计划标题"
                  required
                />
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>描述</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  style={styles.textarea}
                  placeholder="请输入计划描述"
                  rows={3}
                />
              </div>

              <div style={styles.formRow}>
                <div style={styles.formGroup}>
                  <label style={styles.label}>类别 *</label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value as Plan['category'] })}
                    style={styles.select}
                  >
                    <option value="PERSONAL">个人</option>
                    <option value="LEARNING">学习</option>
                    <option value="FITNESS">健身</option>
                    <option value="HABIT">习惯</option>
                    <option value="CAREER">职业</option>
                    <option value="HEALTH">健康</option>
                    <option value="CREATIVE">创意</option>
                    <option value="OTHER">其他</option>
                  </select>
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>优先级 *</label>
                  <select
                    value={formData.priority}
                    onChange={(e) => setFormData({ ...formData, priority: e.target.value as Plan['priority'] })}
                    style={styles.select}
                  >
                    <option value="LOW">低</option>
                    <option value="MEDIUM">中</option>
                    <option value="HIGH">高</option>
                    <option value="URGENT">紧急</option>
                  </select>
                </div>
              </div>

              <div style={styles.formRow}>
                <div style={styles.formGroup}>
                  <label style={styles.label}>状态 *</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value as Plan['status'] })}
                    style={styles.select}
                  >
                    <option value="DRAFT">草稿</option>
                    <option value="PENDING">待开始</option>
                    <option value="ACTIVE">进行中</option>
                    <option value="PAUSED">已暂停</option>
                    <option value="COMPLETED">已完成</option>
                    <option value="CANCELLED">已取消</option>
                  </select>
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>可见性 *</label>
                  <select
                    value={formData.visibility}
                    onChange={(e) => setFormData({ ...formData, visibility: e.target.value as Plan['visibility'] })}
                    style={styles.select}
                  >
                    <option value="PRIVATE">私有</option>
                    <option value="PUBLIC">公开</option>
                    <option value="FRIENDS">好友</option>
                  </select>
                </div>
              </div>

              <div style={styles.formRow}>
                <div style={styles.formGroup}>
                  <label style={styles.label}>开始日期</label>
                  <input
                    type="date"
                    value={formData.startDate}
                    onChange={(e) => setFormData({ ...formData, startDate: e.target.value })}
                    style={styles.input}
                  />
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>目标日期</label>
                  <input
                    type="date"
                    value={formData.targetDate}
                    onChange={(e) => setFormData({ ...formData, targetDate: e.target.value })}
                    style={styles.input}
                  />
                </div>
              </div>

              <div style={styles.formRow}>
                <div style={styles.formGroup}>
                  <label style={styles.label}>预计时长（天）</label>
                  <input
                    type="number"
                    value={formData.estimatedDurationDays || ''}
                    onChange={(e) => setFormData({ ...formData, estimatedDurationDays: e.target.value ? parseInt(e.target.value) : undefined })}
                    style={styles.input}
                    placeholder="根据开始和目标日期自动计算"
                    min="0"
                    readOnly={!!(formData.startDate && formData.targetDate)}
                  />
                  {formData.startDate && formData.targetDate && (
                    <span style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
                      自动计算：{calculateDays(formData.startDate, formData.targetDate)} 天
                    </span>
                  )}
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>实际天数</label>
                  <input
                    type="number"
                    value={checkinCounts[editingPlan?.id || 0] || 0}
                    style={styles.input}
                    placeholder="总打卡次数"
                    min="0"
                    readOnly
                  />
                  <span style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
                    总打卡次数
                  </span>
                </div>
              </div>

              {editingPlan && (
                <div style={styles.formGroup}>
                  <label style={styles.label}>完成进度</label>
                  <div style={styles.progressInputGroup}>
                    <input
                      type="number"
                      value={formData.progressPercentage}
                      onChange={(e) => setFormData({ ...formData, progressPercentage: parseInt(e.target.value) || 0 })}
                      style={styles.input}
                      placeholder="进度百分比"
                      min="0"
                      max="100"
                    />
                    <span style={styles.progressUnit}>%</span>
                  </div>
                </div>
              )}

              <div style={styles.formActions}>
                <button type="button" style={styles.cancelButton} onClick={() => setShowModal(false)}>
                  取消
                </button>
                <button type="submit" style={styles.submitButton}>
                  {editingPlan ? '保存修改' : '创建计划'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showCheckinModal && checkinPlanId && (
        <div style={styles.modalOverlay} onClick={() => setShowCheckinModal(false)}>
          <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h2 style={styles.modalTitle}>每日打卡</h2>
              <button style={styles.closeButton} onClick={() => setShowCheckinModal(false)}>
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleCheckinSubmit} style={styles.form}>
              <div style={styles.formGroup}>
                <label style={styles.label}>今日总结</label>
                <textarea
                  value={checkinFormData.notes}
                  onChange={(e) => setCheckinFormData({ ...checkinFormData, notes: e.target.value })}
                  style={styles.textarea}
                  placeholder="记录今天的收获和感受..."
                  rows={3}
                />
              </div>

              <div style={styles.formRow}>
                <div style={styles.formGroup}>
                  <label style={styles.label}>心情指数</label>
                  <div style={styles.ratingInput}>
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        type="button"
                        onClick={() => setCheckinFormData({ ...checkinFormData, moodRating: star })}
                        style={{
                          ...styles.starButton,
                          ...(checkinFormData.moodRating >= star ? styles.starButtonActive : {}),
                        }}
                      >
                        ★
                      </button>
                    ))}
                  </div>
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>精力指数</label>
                  <div style={styles.ratingInput}>
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        type="button"
                        onClick={() => setCheckinFormData({ ...checkinFormData, energyRating: star })}
                        style={{
                          ...styles.starButton,
                          ...(checkinFormData.energyRating >= star ? styles.starButtonActive : {}),
                        }}
                      >
                        ★
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>进度备注</label>
                <textarea
                  value={checkinFormData.progressNotes}
                  onChange={(e) => setCheckinFormData({ ...checkinFormData, progressNotes: e.target.value })}
                  style={styles.textarea}
                  placeholder="记录今天的进展..."
                  rows={2}
                />
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>标签</label>
                <input
                  type="text"
                  value={checkinFormData.tags}
                  onChange={(e) => setCheckinFormData({ ...checkinFormData, tags: e.target.value })}
                  style={styles.input}
                  placeholder="添加标签，用逗号分隔"
                />
              </div>

              <div style={styles.formActions}>
                <button type="button" style={styles.cancelButton} onClick={() => setShowCheckinModal(false)}>
                  取消
                </button>
                <button type="submit" style={styles.submitButton}>
                  完成打卡
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showDetailModal && detailPlan && (
        <div style={styles.modalOverlay} onClick={() => setShowDetailModal(false)}>
          <div style={styles.detailModal} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h2 style={styles.modalTitle}>计划详情</h2>
              <button style={styles.closeButton} onClick={() => setShowDetailModal(false)}>
                <X size={20} />
              </button>
            </div>
            <div style={styles.detailContent}>
              <div style={styles.detailSection}>
                <h3 style={styles.detailSectionTitle}>{detailPlan.title}</h3>
                <p style={styles.detailDescription}>{detailPlan.description || '暂无描述'}</p>
              </div>

              <div style={styles.detailRow}>
                <div style={styles.detailItem}>
                  <span style={styles.detailLabel}>类别</span>
                  <span style={styles.detailValue}>{getCategoryText(detailPlan.category)}</span>
                </div>
                <div style={styles.detailItem}>
                  <span style={styles.detailLabel}>优先级</span>
                  <span style={styles.detailValue}>
                    {detailPlan.priority === 'URGENT' ? '紧急' : detailPlan.priority === 'HIGH' ? '高' : detailPlan.priority === 'MEDIUM' ? '中' : '低'}
                  </span>
                </div>
                <div style={styles.detailItem}>
                  <span style={styles.detailLabel}>状态</span>
                  <span style={styles.detailValue}>
                    {getStatusText(detailPlan.status)}
                  </span>
                </div>
              </div>

              <div style={styles.detailRow}>
                <div style={styles.detailItem}>
                  <span style={styles.detailLabel}>开始日期</span>
                  <span style={styles.detailValue}>{detailPlan.startDate || '未设置'}</span>
                </div>
                <div style={styles.detailItem}>
                  <span style={styles.detailLabel}>目标日期</span>
                  <span style={styles.detailValue}>{detailPlan.targetDate || '未设置'}</span>
                </div>
                <div style={styles.detailItem}>
                  <span style={styles.detailLabel}>可见性</span>
                  <span style={styles.detailValue}>{detailPlan.visibility === 'PRIVATE' ? '私有' : detailPlan.visibility === 'PUBLIC' ? '公开' : '好友'}</span>
                </div>
              </div>

              <div style={styles.detailRow}>
                <div style={styles.detailItem}>
                  <span style={styles.detailLabel}>计划天数</span>
                  <span style={styles.detailValue}>{calculatePlanDays(detailPlan) || '未设置'} 天</span>
                </div>
                <div style={styles.detailItem}>
                  <span style={styles.detailLabel}>实际天数</span>
                  <span style={styles.detailValue}>{detailCheckins.length || 0} 天</span>
                </div>
              </div>

              {detailPlan.completionCriteria && (
                <div style={styles.detailSection}>
                  <h4 style={styles.detailSectionSubTitle}>完成标准</h4>
                  <p style={styles.detailDescription}>{detailPlan.completionCriteria}</p>
                </div>
              )}

              <div style={styles.detailSection}>
                <h4 style={styles.detailSectionSubTitle}>完成进度</h4>
                <div style={styles.detailProgressContainer}>
                  <div style={styles.detailProgressHeader}>
                    <span style={styles.detailProgressLabel}>当前进度</span>
                    <span style={styles.detailProgressValue}>{detailPlan.progressPercentage}%</span>
                  </div>
                  <div style={styles.detailProgressBar}>
                    <div
                      style={{
                        ...styles.detailProgressFill,
                        width: `${detailPlan.progressPercentage}%`,
                        background: '#000000',
                      }}
                    ></div>
                  </div>
                  <div style={styles.detailProgressStats}>
                    <span>已打卡 {detailCheckins.length} 次</span>
                    <span>计划共 {calculatePlanDays(detailPlan)} 天</span>
                    {calculatePlanDays(detailPlan) > 0 && (
                      <span>完成比例 {Math.round((detailCheckins.length / calculatePlanDays(detailPlan)) * 100)}%</span>
                    )}
                  </div>
                </div>
              </div>

              <div style={styles.detailSection}>
                <h4 style={styles.detailSectionSubTitle}>打卡记录</h4>
                {detailLoading ? (
                  <div style={styles.checkinsLoading}>加载中...</div>
                ) : detailCheckins.length === 0 ? (
                  <div style={styles.noCheckins}>暂无打卡记录</div>
                ) : (
                  <div style={styles.checkinsList}>
                    {detailCheckins.map((checkin, index) => (
                      <div key={checkin.id || index} style={styles.checkinItem}>
                        <div style={styles.checkinDate}>
                          <CheckCircle size={16} style={{ color: '#000000' }} />
                          <span>{new Date(checkin.checkinDate).toLocaleDateString('zh-CN')}</span>
                        </div>
                        {checkin.notes && (
                          <div style={styles.checkinNotes}>{checkin.notes}</div>
                        )}
                        <div style={styles.checkinRatings}>
                          {checkin.moodRating && (
                            <span style={styles.checkinRating}>
                              心情: {renderStars(checkin.moodRating)}
                            </span>
                          )}
                          {checkin.energyRating && (
                            <span style={styles.checkinRating}>
                              精力: {renderStars(checkin.energyRating)}
                            </span>
                          )}
                        </div>
                        {checkin.progressNotes && (
                          <div style={styles.checkinProgressNotes}>{checkin.progressNotes}</div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {showShareModal && selectedPlan && (
        <div style={styles.modalOverlay} onClick={() => setShowShareModal(false)}>
          <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h2 style={styles.modalTitle}>分享计划</h2>
              <button style={styles.closeButton} onClick={() => setShowShareModal(false)}>
                <X size={20} />
              </button>
            </div>
            
            {/* 分享模式选择 */}
            <div style={styles.shareModeSelector}>
              <button
                style={{
                  ...styles.shareModeButton,
                  ...(shareMode === 'community' ? styles.shareModeButtonActive : {}),
                }}
                onClick={() => setShareMode('community')}
              >
                <Users size={16} />
                <span>分享到社区</span>
              </button>
              <button
                style={{
                  ...styles.shareModeButton,
                  ...(shareMode === 'chat' ? styles.shareModeButtonActive : {}),
                }}
                onClick={() => setShareMode('chat')}
              >
                <MessageCircle size={16} />
                <span>分享给好友</span>
              </button>
            </div>

            {/* 分享给好友的用户选择 */}
            {shareMode === 'chat' && (
              <div style={styles.formGroup}>
                <label style={styles.label}>选择好友</label>
                {loadingConversations ? (
                  <div style={styles.loadingText}>加载中...</div>
                ) : conversations.length === 0 ? (
                  <div style={styles.emptyText}>暂无可分享的好友</div>
                ) : (
                  <div style={styles.userList}>
                    {conversations.map((convo) => (
                      <div
                        key={convo.id}
                        style={{
                          ...styles.userItem,
                          ...(selectedReceiver === convo.otherUserId ? styles.userItemSelected : {}),
                        }}
                        onClick={() => setSelectedReceiver(convo.otherUserId)}
                      >
                        <div style={styles.userAvatarSmall}>
                          {convo.otherUser.displayName?.charAt(0) || convo.otherUser.username?.charAt(0) || 'U'}
                        </div>
                        <div style={styles.userInfoSmall}>
                          <span style={styles.userNameSmall}>
                            {convo.otherUser.displayName || convo.otherUser.username}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div style={styles.formGroup}>
              <textarea
                style={styles.textarea}
                placeholder="说点什么..."
                value={shareContent}
                onChange={(e) => setShareContent(e.target.value)}
                rows={3}
              />
            </div>

            <div style={styles.formActions}>
              <button style={styles.cancelButton} onClick={() => setShowShareModal(false)}>
                取消
              </button>
              <button
                style={{
                  ...styles.submitButton,
                  ...(shareMode === 'chat' && !selectedReceiver ? styles.submitButtonDisabled : {}),
                }}
                onClick={handleConfirmShare}
                disabled={shareMode === 'chat' && !selectedReceiver}
              >
                分享
              </button>
            </div>
          </div>
        </div>
      )}

      </div>

      <style>{`
        .plan-card:hover {
          transform: translateY(-4px);
          box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);
        }
        .action-btn:hover {
          background: #e5e7eb !important;
        }
        .checkin-btn:hover:not(:disabled) {
          background: #1a1a1a !important;
        }
        .primary-btn:hover {
          background: #1a1a1a !important;
        }
        .like-btn:hover {
          background: #f3f4f6 !important;
        }
        .share-btn:hover {
          background: #f3f4f6 !important;
        }
        .filter-tab:hover:not(.filter-tab-active) {
          background: rgba(0, 0, 0, 0.05) !important;
        }
        .search-input::placeholder {
          color: #94a3b8 !important;
        }
        .form-input:focus, .form-textarea:focus, .form-select:focus {
          border-color: #333333 !important;
          box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.1) !important;
        }
        .submit-btn:hover:not(:disabled) {
          background: #1a1a1a !important;
        }
        .cancel-btn:hover {
          background: #e5e7eb !important;
        }
        .progress-fill {
          background: #333333 !important;
        }
        .progress-bar-bg {
          background: #e2e8f0 !important;
        }
        @media (max-width: 768px) {
          .plans-grid {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    minHeight: '100vh',
    backgroundColor: '#f8fafc',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '32px 40px',
    backgroundColor: '#ffffff',
    color: '#0f172a',
    borderBottom: '2px solid #e2e8f0',
    marginBottom: '32px',
  },
  headerContent: {
    display: 'flex',
    flexDirection: 'column',
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
  },
  title: {
    fontSize: '32px',
    fontWeight: '700',
    color: '#0f172a',
    margin: '0 0 8px',
  },
  subtitle: {
    fontSize: '16px',
    color: '#64748b',
    margin: 0,
  },
  dateBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '12px 20px',
    backgroundColor: '#f8fafc',
    borderRadius: '12px',
    fontSize: '14px',
    fontWeight: '500',
    border: '1px solid #e2e8f0',
    color: '#333333',
  },
  containerInner: {
    padding: '0 40px 40px',
    maxWidth: '1600px',
    margin: '0 auto',
  },
  toolbar: {
    margin: '0 0 24px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '20px',
    flexWrap: 'wrap',
  },
  searchWrapper: {
    flex: 1,
    minWidth: '250px',
    position: 'relative',
  },
  searchIcon: {
    position: 'absolute',
    left: '16px',
    top: '50%',
    transform: 'translateY(-50%)',
    color: '#64748b',
  },
  searchInput: {
    width: '100%',
    padding: '12px 12px 12px 48px',
    backgroundColor: '#ffffff',
    border: '1px solid #333333',
    borderRadius: '10px',
    fontSize: '14px',
    color: '#0f172a',
    outline: 'none',
    boxSizing: 'border-box',
  },
  filterWrapper: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  filterIcon: {
    color: '#333333',
  },
  filterTabs: {
    display: 'flex',
    backgroundColor: '#f1f5f9',
    borderRadius: '10px',
    padding: '4px',
    border: '1px solid #333333',
  },
  filterTab: {
    padding: '8px 16px',
    backgroundColor: 'transparent',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    color: '#64748b',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    fontWeight: '500',
  },
  filterTabActive: {
    backgroundColor: '#333333',
    color: '#ffffff',
  },
  loading: {
    textAlign: 'center',
    padding: '60px',
    color: '#64748b',
    fontSize: '16px',
  },
  plansGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))',
    gap: '24px',
  },
  planCard: {
    backgroundColor: '#ffffff',
    borderRadius: '16px',
    overflow: 'hidden',
    border: '1px solid #333333',
    transition: 'all 0.3s ease',
    position: 'relative',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 20px',
    borderBottom: '1px solid #e2e8f0',
  },
  badgeGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  headerActions: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  checkinDaysBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    padding: '8px 14px',
    backgroundColor: '#2D9CDB',
    color: '#ffffff',
    borderRadius: '10px',
    fontSize: '14px',
    fontWeight: '600',
    border: '1px solid #2D9CDB',
    boxShadow: '0 2px 4px rgba(45, 156, 219, 0.2)',
  },
  daysRemainingBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    padding: '8px 14px',
    backgroundColor: '#F5F7FA',
    color: '#555555',
    borderRadius: '10px',
    fontSize: '14px',
    fontWeight: '600',
    border: '1px solid #E5E7EB',
  },
  priorityIndicator: {
    width: '4px',
    height: '24px',
    borderRadius: '2px',
  },
  moreButton: {
    padding: '4px',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: '#666',
  },
  likeButton: {
    padding: '8px',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  },
  likeCount: {
    fontSize: '12px',
    fontWeight: '500',
  },
  shareButton: {
    padding: '8px',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: '#666',
    transition: 'all 0.3s ease',
    borderRadius: '50%',
  },
  shareButtonHover: {
    background: '#f0f0f0',
  },
  shareModeSelector: {
    display: 'flex',
    gap: '12px',
    marginBottom: '20px',
    padding: '0 24px',
  },
  shareModeButton: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    padding: '12px',
    border: '2px solid #e0e0e0',
    borderRadius: '12px',
    backgroundColor: '#ffffff',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    fontSize: '14px',
    fontWeight: '500',
    color: '#666',
  },
  shareModeButtonActive: {
    borderColor: '#333333',
    backgroundColor: '#333333',
    color: '#ffffff',
  },
  userList: {
    maxHeight: '200px',
    overflowY: 'auto',
    border: '1px solid #333333',
    borderRadius: '8px',
  },
  userItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '12px',
    cursor: 'pointer',
    transition: 'background 0.2s ease',
    borderBottom: '1px solid #f0f0f0',
  },
  userItemSelected: {
    backgroundColor: '#f1f5f9',
  },
  userAvatarSmall: {
    width: '32px',
    height: '32px',
    backgroundColor: '#333333',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#ffffff',
    fontWeight: 'bold',
    fontSize: '14px',
    flexShrink: 0,
  },
  userInfoSmall: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  userNameSmall: {
    fontSize: '14px',
    fontWeight: '500',
    color: '#0f172a',
  },
  loadingText: {
    padding: '20px',
    textAlign: 'center',
    color: '#64748b',
  },
  emptyText: {
    padding: '20px',
    textAlign: 'center',
    color: '#64748b',
  },
  submitButtonDisabled: {
    backgroundColor: '#d1d5db',
    cursor: 'not-allowed',
  },
  cardContent: {
    padding: '20px',
  },
  planTitle: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#0f172a',
    margin: '0 0 8px',
  },
  planDescription: {
    fontSize: '14px',
    color: '#64748b',
    margin: '0 0 16px',
    lineHeight: '1.5',
  },
  planMeta: {
    display: 'flex',
    gap: '12px',
    marginBottom: '16px',
  },
  statusBadge: {
    padding: '6px 14px',
    borderRadius: '20px',
    fontSize: '12px',
    fontWeight: '600',
    backgroundColor: '#f1f5f9',
    color: '#000000',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  dateBadge: {
    padding: '6px 14px',
    backgroundColor: '#f1f5f9',
    borderRadius: '20px',
    fontSize: '12px',
    fontWeight: '600',
    color: '#000000',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  progressSection: {
    marginTop: '12px',
  },
  progressHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: '8px',
  },
  progressLabel: {
    fontSize: '13px',
    color: '#64748b',
  },
  progressValue: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#0f172a',
  },
  progressBar: {
    height: '10px',
    backgroundColor: '#e2e8f0',
    borderRadius: '5px',
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: '5px',
    transition: 'width 0.6s ease',
    backgroundColor: '#333333',
  },
  cardActions: {
    display: 'flex',
    gap: '8px',
    padding: '16px 20px',
    borderTop: '1px solid #e2e8f0',
  },
  actionButton: {
    flex: 1,
    padding: '10px',
    backgroundColor: '#f1f5f9',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    fontSize: '14px',
    color: '#333333',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '6px',
    transition: 'all 0.3s ease',
    fontWeight: '500',
  },
  checkinButton: {
    flex: 1,
    padding: '10px',
    backgroundColor: '#f1f5f9',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    fontSize: '14px',
    color: '#333333',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '6px',
    transition: 'all 0.3s ease',
    fontWeight: '500',
  },
  checkinButtonDisabled: {
    backgroundColor: '#f1f5f9',
    border: '2px solid #000000',
    color: '#333333',
    cursor: 'not-allowed',
  },
  actionButtonPrimary: {
    flex: 2,
    padding: '10px',
    backgroundColor: '#f1f5f9',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    fontSize: '14px',
    color: '#333333',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '6px',
    transition: 'all 0.3s ease',
    fontWeight: '500',
  },
  emptyState: {
    textAlign: 'center',
    padding: '60px 40px',
    backgroundColor: '#ffffff',
    borderRadius: '20px',
    maxWidth: '400px',
    margin: '40px auto',
    border: '1px solid #333333',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)',
  },
  emptyIcon: {
    width: '80px',
    height: '80px',
    backgroundColor: '#333333',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    margin: '0 auto 20px',
    color: '#ffffff',
  },
  emptyTitle: {
    fontSize: '20px',
    fontWeight: '600',
    color: '#0f172a',
    margin: '0 0 8px',
  },
  emptyDescription: {
    fontSize: '14px',
    color: '#64748b',
    margin: 0,
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    padding: '20px',
  },
  modal: {
    backgroundColor: '#ffffff',
    borderRadius: '16px',
    width: '100%',
    maxWidth: '500px',
    maxHeight: '90vh',
    overflow: 'auto',
    border: '1px solid #333333',
  },
  detailModal: {
    backgroundColor: '#ffffff',
    borderRadius: '16px',
    width: '100%',
    maxWidth: '600px',
    maxHeight: '90vh',
    overflow: 'auto',
    border: '1px solid #333333',
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '20px 24px',
    borderBottom: '2px solid #333333',
  },
  modalTitle: {
    fontSize: '20px',
    fontWeight: '600',
    color: '#0f172a',
    margin: 0,
  },
  closeButton: {
    padding: '4px',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: '#64748b',
  },
  form: {
    padding: '24px',
  },
  formGroup: {
    marginBottom: '20px',
  },
  formRow: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '16px',
  },
  label: {
    display: 'block',
    fontSize: '14px',
    fontWeight: '500',
    color: '#0f172a',
    marginBottom: '8px',
  },
  input: {
    width: '100%',
    padding: '10px 14px',
    border: '1px solid #333333',
    borderRadius: '8px',
    fontSize: '14px',
    outline: 'none',
    boxSizing: 'border-box',
    backgroundColor: '#ffffff',
  },
  textarea: {
    width: '100%',
    padding: '10px 14px',
    border: '1px solid #333333',
    borderRadius: '8px',
    fontSize: '14px',
    outline: 'none',
    resize: 'vertical',
    boxSizing: 'border-box',
    backgroundColor: '#ffffff',
  },
  select: {
    width: '100%',
    padding: '10px 14px',
    border: '1px solid #333333',
    borderRadius: '8px',
    fontSize: '14px',
    outline: 'none',
    backgroundColor: '#ffffff',
    boxSizing: 'border-box',
  },
  progressInputGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  progressUnit: {
    fontSize: '14px',
    color: '#64748b',
    fontWeight: '500',
  },
  ratingInput: {
    display: 'flex',
    gap: '4px',
  },
  starButton: {
    background: 'none',
    border: 'none',
    fontSize: '24px',
    cursor: 'pointer',
    color: '#e5e7eb',
    padding: '4px',
  },
  starButtonActive: {
    color: '#fbbf24',
  },
  formActions: {
    display: 'flex',
    gap: '12px',
    marginTop: '24px',
  },
  cancelButton: {
    flex: 1,
    padding: '12px',
    backgroundColor: '#f1f5f9',
    border: '1px solid #333333',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '500',
    color: '#0f172a',
    cursor: 'pointer',
  },
  submitButton: {
    flex: 1,
    padding: '12px',
    backgroundColor: '#333333',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '500',
    color: '#ffffff',
    cursor: 'pointer',
  },
  detailContent: {
    padding: '24px',
  },
  detailSection: {
    marginBottom: '24px',
  },
  detailSectionTitle: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#0f172a',
    margin: '0 0 8px',
  },
  detailSectionSubTitle: {
    fontSize: '15px',
    fontWeight: '600',
    color: '#0f172a',
    margin: '0 0 12px',
  },
  detailDescription: {
    fontSize: '14px',
    color: '#64748b',
    lineHeight: '1.6',
    margin: 0,
  },
  detailRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '16px',
    marginBottom: '16px',
  },
  detailItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  detailLabel: {
    fontSize: '12px',
    color: '#64748b',
  },
  detailValue: {
    fontSize: '14px',
    fontWeight: '500',
    color: '#0f172a',
  },
  detailProgressContainer: {
    backgroundColor: '#f8fafc',
    borderRadius: '12px',
    padding: '16px',
    border: '1px solid #333333',
  },
  detailProgressHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: '8px',
  },
  detailProgressLabel: {
    fontSize: '14px',
    color: '#64748b',
  },
  detailProgressValue: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#0f172a',
  },
  detailProgressBar: {
    height: '10px',
    backgroundColor: '#e2e8f0',
    borderRadius: '5px',
    overflow: 'hidden',
  },
  detailProgressFill: {
    height: '100%',
    borderRadius: '5px',
    transition: 'width 0.6s ease',
    backgroundColor: '#333333',
  },
  detailProgressStats: {
    display: 'flex',
    justifyContent: 'space-between',
    marginTop: '12px',
    fontSize: '12px',
    color: '#64748b',
  },
  checkinsLoading: {
    textAlign: 'center',
    padding: '20px',
    color: '#64748b',
  },
  noCheckins: {
    textAlign: 'center',
    padding: '20px',
    color: '#64748b',
    backgroundColor: '#f8fafc',
    borderRadius: '8px',
    border: '1px solid #333333',
  },
  checkinsList: {
    maxHeight: '300px',
    overflowY: 'auto',
  },
  checkinItem: {
    padding: '12px',
    backgroundColor: '#f8fafc',
    borderRadius: '8px',
    marginBottom: '8px',
    border: '1px solid #e2e8f0',
  },
  checkinDate: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '14px',
    fontWeight: '500',
    color: '#0f172a',
    marginBottom: '4px',
  },
  checkinNotes: {
    fontSize: '13px',
    color: '#64748b',
    marginLeft: '24px',
    marginBottom: '4px',
  },
  checkinRatings: {
    display: 'flex',
    gap: '12px',
    marginLeft: '24px',
    marginBottom: '4px',
  },
  checkinRating: {
    fontSize: '12px',
    color: '#64748b',
  },
  checkinProgressNotes: {
    fontSize: '12px',
    color: '#64748b',
    marginLeft: '24px',
    fontStyle: 'italic',
  },
};

export default MyPlans;