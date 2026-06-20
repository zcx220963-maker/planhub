import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Edit2, Trash2, Calendar, CheckCircle, User as UserIcon, Heart, Share2, MessageCircle, Users } from 'lucide-react';
import { planApi, checkinApi, chatApi, userApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import type { Plan, PlanCheckin, ChatConversation, User } from '../types';

const PlanDetail: React.FC = () => {
  const { planId } = useParams<{ planId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [plan, setPlan] = useState<Plan | null>(null);
  const [checkins, setCheckins] = useState<PlanCheckin[]>([]);
  const [loading, setLoading] = useState(true);
  const [checkedInToday, setCheckedInToday] = useState(false);
  const [showCheckinModal, setShowCheckinModal] = useState(false);
  const [checkinFormData, setCheckinFormData] = useState({
    notes: '',
    moodRating: 3,
    energyRating: 3,
    progressNotes: '',
  });
  // 点赞和分享状态
  const [liked, setLiked] = useState(false);
  const [likeCount, setLikeCount] = useState(0);
  const [shareCount, setShareCount] = useState(0);
  const [showShareModal, setShowShareModal] = useState(false);
  const [shareContent, setShareContent] = useState('');
  const [shareMode, setShareMode] = useState<'community' | 'chat'>('community'); // 分享模式
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [selectedReceiver, setSelectedReceiver] = useState<number | null>(null);
  const [loadingConversations, setLoadingConversations] = useState(false);
  const [interactionLoading, setInteractionLoading] = useState(false);

  useEffect(() => {
    if (planId) {
      loadPlanDetail(parseInt(planId));
      loadInteractionStatus(parseInt(planId));
    }
  }, [planId]);

  const loadPlanDetail = async (id: number) => {
    setLoading(true);
    try {
      const planData = await planApi.getPlanById(id);
      setPlan(planData);
      const checkinData = await checkinApi.getCheckinsByPlanId(id);
      setCheckins(checkinData);
      
      // 检查今天是否已打卡
      try {
        const todayExists = await checkinApi.checkCheckinExists(id);
        setCheckedInToday(todayExists);
      } catch {
        setCheckedInToday(false);
      }
    } catch (error) {
      console.error('Failed to load plan detail:', error);
      navigate('/my-plans');
    } finally {
      setLoading(false);
    }
  };

  const loadInteractionStatus = async (id: number) => {
    try {
      const status = await planApi.getPlanInteractionStatus(id);
      setLiked(status.liked);
      setLikeCount(status.likeCount);
      setShareCount(status.shareCount);
    } catch (error) {
      console.error('Failed to load interaction status:', error);
    }
  };

  const handleLike = async () => {
    if (!planId || !user) return;
    setInteractionLoading(true);
    try {
      if (liked) {
        const result = await planApi.unlikePlan(parseInt(planId));
        setLiked(result.liked);
        setLikeCount(result.likeCount);
      } else {
        const result = await planApi.likePlan(parseInt(planId));
        setLiked(result.liked);
        setLikeCount(result.likeCount);
      }
    } catch (error) {
      console.error('Failed to toggle like:', error);
      alert('操作失败');
    } finally {
      setInteractionLoading(false);
    }
  };

  const loadConversations = async () => {
    if (!user) return;
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

  const handleShare = async () => {
    if (!planId || !user) return;
    setInteractionLoading(true);
    try {
      if (shareMode === 'community') {
        await planApi.sharePlanToCommunity(parseInt(planId), shareContent || undefined);
        alert('分享成功！');
      } else if (shareMode === 'chat' && selectedReceiver) {
        await chatApi.sharePlanToChat(selectedReceiver, parseInt(planId), shareContent || undefined);
        alert('分享成功！');
      }
      setShowShareModal(false);
      setShareContent('');
      setSelectedReceiver(null);
      // 刷新分享数
      loadInteractionStatus(parseInt(planId));
    } catch (error) {
      console.error('Failed to share plan:', error);
      alert('分享失败');
    } finally {
      setInteractionLoading(false);
    }
  };

  const openShareModal = async () => {
    setShowShareModal(true);
    setShareMode('community');
    setSelectedReceiver(null);
    if (user) {
      await loadConversations();
    }
  };

  const isOwner = plan && user && plan.userId === user.id;

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

  const openCheckinModal = () => {
    if (checkedInToday) {
      alert('今天已经打卡过了');
      return;
    }
    setShowCheckinModal(true);
  };

  const handleCheckinSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!planId) return;

    try {
      await checkinApi.checkin(parseInt(planId), {
        notes: checkinFormData.notes || '今日打卡',
        moodRating: checkinFormData.moodRating,
        energyRating: checkinFormData.energyRating,
        progressNotes: checkinFormData.progressNotes,
      });
      setCheckedInToday(true);
      // 刷新打卡记录
      const checkinData = await checkinApi.getCheckinsByPlanId(parseInt(planId));
      setCheckins(checkinData);
      setShowCheckinModal(false);
      alert('打卡成功！');
    } catch (err) {
      alert('打卡失败');
    }
  };

  const deletePlan = () => {
    if (!planId || !window.confirm('确定要删除这个计划吗？')) return;
    planApi.deletePlan(parseInt(planId))
      .then(() => {
        navigate('/my-plans');
      })
      .catch(() => alert('删除失败'));
  };

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loadingContainer}>
          <div style={styles.loadingSpinner}></div>
          <p style={styles.loadingText}>加载中...</p>
        </div>
      </div>
    );
  }

  if (!plan) {
    return (
      <div style={styles.container}>
        <div style={styles.errorContainer}>
          <p style={styles.errorText}>计划不存在</p>
          <button style={styles.backButton} onClick={() => navigate('/my-plans')}>
            <ArrowLeft size={18} />
            <span>返回</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <button style={styles.backButton} onClick={() => navigate(-1)}>
          <ArrowLeft size={20} />
          <span>返回</span>
        </button>
        
        {isOwner && (
          <div style={styles.actionButtons}>
            <button style={styles.editButton} onClick={() => navigate(`/my-plans?planId=${plan.id}`)}>
              <Edit2 size={18} />
              <span>编辑</span>
            </button>
            <button style={styles.deleteButton} onClick={deletePlan}>
              <Trash2 size={18} />
              <span>删除</span>
            </button>
          </div>
        )}
      </div>

      <div style={styles.content}>
        <div style={styles.planHeader}>
          <h1 style={styles.planTitle}>{plan.title}</h1>
          <span style={styles.statusBadge}>
            {getStatusText(plan.status)}
          </span>
        </div>

        {/* 点赞和分享按钮 */}
        <div style={styles.interactionSection}>
          <button
            style={{
              ...styles.interactionButton,
              ...(liked ? styles.interactionButtonActive : {}),
            }}
            onClick={handleLike}
            disabled={interactionLoading}
          >
            <Heart size={20} fill={liked ? '#ef4444' : 'none'} />
            <span>{likeCount}</span>
          </button>
          <button
            style={styles.interactionButton}
            onClick={openShareModal}
            disabled={interactionLoading}
          >
            <Share2 size={20} />
            <span>{shareCount}</span>
          </button>
        </div>

        {plan.description && (
          <p style={styles.planDescription}>{plan.description}</p>
        )}

        {/* 用户信息 */}
        <div style={styles.userInfo} onClick={() => navigate(`/user/${plan.userId}`)}>
          <div style={styles.userAvatar}>
                        <UserIcon size={20} color="#667eea" />
                      </div>
          <div style={styles.userDetails}>
            <span style={styles.userName}>查看创建者</span>
            <span style={styles.userAction}>点击访问用户页面</span>
          </div>
        </div>

        <div style={styles.infoGrid}>
          <div style={styles.infoItem}>
            <span style={styles.infoLabel}>类别</span>
            <span style={styles.infoValue}>{getCategoryText(plan.category)}</span>
          </div>
          <div style={styles.infoItem}>
            <span style={styles.infoLabel}>优先级</span>
            <span style={styles.infoValue}>
              {plan.priority === 'URGENT' ? '紧急' : plan.priority === 'HIGH' ? '高' : plan.priority === 'MEDIUM' ? '中' : '低'}
            </span>
          </div>
          <div style={styles.infoItem}>
            <span style={styles.infoLabel}>可见性</span>
            <span style={styles.infoValue}>
              {plan.visibility === 'PRIVATE' ? '私有' : plan.visibility === 'PUBLIC' ? '公开' : '好友'}
            </span>
          </div>
        </div>

        <div style={styles.infoGrid}>
          {plan.startDate && (
            <div style={styles.infoItem}>
              <span style={styles.infoLabel}>开始日期</span>
              <span style={styles.infoValue}>{plan.startDate}</span>
            </div>
          )}
          {plan.targetDate && (
            <div style={styles.infoItem}>
              <span style={styles.infoLabel}>目标日期</span>
              <span style={styles.infoValue}>{plan.targetDate}</span>
            </div>
          )}
          <div style={styles.infoItem}>
            <span style={styles.infoLabel}>计划天数</span>
            <span style={styles.infoValue}>{calculatePlanDays(plan) || '未设置'}</span>
          </div>
        </div>

        <div style={styles.progressSection}>
          <div style={styles.progressHeader}>
            <span style={styles.progressLabel}>完成进度</span>
            <span style={styles.progressValue}>{plan.progressPercentage}%</span>
          </div>
          <div style={styles.progressBar}>
            <div
              style={{
                ...styles.progressFill,
                width: `${plan.progressPercentage}%`,
                background: '#000000',
              }}
            ></div>
          </div>
          <div style={styles.progressStats}>
            <span>已打卡 {checkins.length} 次</span>
            {calculatePlanDays(plan) > 0 && (
              <span>完成比例 {Math.round((checkins.length / calculatePlanDays(plan)) * 100)}%</span>
            )}
          </div>
        </div>

        {plan.completionCriteria && (
          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>完成标准</h3>
            <p style={styles.sectionContent}>{plan.completionCriteria}</p>
          </div>
        )}

        {isOwner && (
          <div style={styles.checkinSection}>
            <button
              style={{
                ...styles.checkinButton,
                ...(checkedInToday ? styles.checkinButtonDisabled : {}),
              }}
              onClick={openCheckinModal}
              disabled={checkedInToday}
            >
              <Calendar size={20} />
              <span>{checkedInToday ? '今天已打卡' : '每日打卡'}</span>
            </button>
          </div>
        )}

        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>打卡记录</h3>
          {checkins.length === 0 ? (
            <div style={styles.emptyCheckins}>暂无打卡记录</div>
          ) : (
            <div style={styles.checkinsList}>
              {checkins.map((checkin, index) => (
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

      {/* 打卡模态框 */}
      {showCheckinModal && (
        <div style={styles.modalOverlay} onClick={() => setShowCheckinModal(false)}>
          <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h2 style={styles.modalTitle}>每日打卡</h2>
              <button style={styles.closeButton} onClick={() => setShowCheckinModal(false)}>
                <span style={{ fontSize: '24px' }}>×</span>
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

      {/* 分享模态框 */}
      {showShareModal && (
        <div style={styles.modalOverlay} onClick={() => setShowShareModal(false)}>
          <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h2 style={styles.modalTitle}>分享</h2>
              <button style={styles.closeButton} onClick={() => setShowShareModal(false)}>
                <span style={{ fontSize: '24px' }}>×</span>
              </button>
            </div>
            <div style={styles.form}>
              {/* 分享模式选择 */}
              <div style={styles.shareModeSelector}>
                <button
                  style={{
                    ...styles.shareModeButton,
                    ...(shareMode === 'community' ? styles.shareModeButtonActive : {})
                  }}
                  onClick={() => setShareMode('community')}
                >
                  <Users size={16} />
                  <span>分享到社区</span>
                </button>
                <button
                  style={{
                    ...styles.shareModeButton,
                    ...(shareMode === 'chat' ? styles.shareModeButtonActive : {})
                  }}
                  onClick={() => setShareMode('chat')}
                >
                  <MessageCircle size={16} />
                  <span>分享给好友</span>
                </button>
              </div>

              {/* 分享到聊天的用户选择 */}
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
                            ...(selectedReceiver === convo.otherUserId ? styles.userItemSelected : {})
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
                <label style={styles.label}>分享内容（可选）</label>
                <textarea
                  value={shareContent}
                  onChange={(e) => setShareContent(e.target.value)}
                  style={styles.textarea}
                  placeholder="说点什么吧..."
                  rows={4}
                />
              </div>
              <div style={styles.formActions}>
                <button type="button" style={styles.cancelButton} onClick={() => setShowShareModal(false)}>
                  取消
                </button>
                <button 
                  type="button" 
                  style={{
                    ...styles.submitButton,
                    ...(shareMode === 'chat' && !selectedReceiver ? styles.submitButtonDisabled : {})
                  }}
                  onClick={handleShare}
                  disabled={interactionLoading || (shareMode === 'chat' && !selectedReceiver)}
                >
                  {interactionLoading ? '分享中...' : '分享'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    minHeight: '100vh',
    background: '#f8fafc',
    padding: '24px',
  },
  loadingContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '60px',
  },
  loadingSpinner: {
    width: '40px',
    height: '40px',
    border: '3px solid #e2e8f0',
    borderTop: '3px solid #667eea',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  loadingText: {
    marginTop: '16px',
    color: '#64748b',
    fontSize: '16px',
  },
  errorContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '60px',
  },
  errorText: {
    color: '#ef4444',
    fontSize: '16px',
    marginBottom: '24px',
  },
  header: {
    maxWidth: '800px',
    margin: '0 auto 24px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  backButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 16px',
    background: 'white',
    border: '1px solid #e2e8f0',
    borderRadius: '10px',
    color: '#64748b',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  actionButtons: {
    display: 'flex',
    gap: '12px',
  },
  editButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 16px',
    background: 'transparent',
    border: '1px solid #e2e8f0',
    borderRadius: '10px',
    color: '#374151',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  deleteButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 16px',
    background: 'transparent',
    border: '1px solid #e2e8f0',
    borderRadius: '10px',
    color: '#ef4444',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  content: {
    maxWidth: '800px',
    margin: '0 auto',
  },
  planHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    marginBottom: '24px',
    background: 'white',
    padding: '24px',
    borderRadius: '16px',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)',
  },
  planTitle: {
    fontSize: '28px',
    fontWeight: '700',
    color: '#0f172a',
    margin: 0,
    flex: 1,
  },
  statusBadge: {
    padding: '8px 16px',
    borderRadius: '20px',
    fontSize: '14px',
    fontWeight: '600',
    color: '#374151',
    background: 'transparent',
    border: '1px solid #e2e8f0',
  },
  planDescription: {
    fontSize: '16px',
    color: '#64748b',
    lineHeight: '1.6',
    marginBottom: '24px',
    background: 'white',
    padding: '20px 24px',
    borderRadius: '12px',
  },
  userInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '16px 24px',
    background: 'white',
    borderRadius: '12px',
    marginBottom: '24px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  userAvatar: {
    width: '48px',
    height: '48px',
    background: '#ede9fe',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  userDetails: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  userName: {
    fontSize: '15px',
    fontWeight: '600',
    color: '#0f172a',
  },
  userAction: {
    fontSize: '13px',
    color: '#667eea',
  },
  infoGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '16px',
    marginBottom: '24px',
    background: 'white',
    padding: '20px 24px',
    borderRadius: '12px',
  },
  infoItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  infoLabel: {
    fontSize: '13px',
    color: '#94a3b8',
  },
  infoValue: {
    fontSize: '15px',
    fontWeight: '600',
    color: '#0f172a',
  },
  progressSection: {
    background: 'white',
    padding: '24px',
    borderRadius: '12px',
    marginBottom: '24px',
  },
  progressHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: '12px',
  },
  progressLabel: {
    fontSize: '15px',
    color: '#64748b',
  },
  progressValue: {
    fontSize: '15px',
    fontWeight: '700',
    color: '#0f172a',
  },
  progressBar: {
    height: '10px',
    background: '#e2e8f0',
    borderRadius: '5px',
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: '5px',
    transition: 'width 0.3s ease',
  },
  progressStats: {
    display: 'flex',
    justifyContent: 'space-between',
    marginTop: '12px',
    fontSize: '13px',
    color: '#64748b',
  },
  section: {
    background: 'white',
    padding: '24px',
    borderRadius: '12px',
    marginBottom: '24px',
  },
  sectionTitle: {
    fontSize: '18px',
    fontWeight: '700',
    color: '#0f172a',
    margin: '0 0 16px',
  },
  sectionContent: {
    fontSize: '15px',
    color: '#64748b',
    lineHeight: '1.6',
    margin: 0,
  },
  checkinSection: {
    display: 'flex',
    justifyContent: 'center',
    marginBottom: '24px',
  },
  checkinButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '14px 32px',
    background: 'transparent',
    border: '1px solid #e2e8f0',
    borderRadius: '12px',
    color: '#374151',
    fontSize: '16px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  checkinButtonDisabled: {
    background: '#d1d5db',
    cursor: 'not-allowed',
  },
  emptyCheckins: {
    textAlign: 'center',
    padding: '40px',
    color: '#94a3b8',
    fontSize: '14px',
    background: '#f8fafc',
    borderRadius: '8px',
  },
  checkinsList: {
    maxHeight: '400px',
    overflowY: 'auto',
  },
  checkinItem: {
    padding: '16px',
    background: '#f8fafc',
    borderRadius: '8px',
    marginBottom: '12px',
  },
  checkinDate: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '14px',
    fontWeight: '600',
    color: '#0f172a',
    marginBottom: '8px',
  },
  checkinNotes: {
    fontSize: '14px',
    color: '#64748b',
    marginLeft: '24px',
    marginBottom: '6px',
  },
  checkinRatings: {
    display: 'flex',
    gap: '16px',
    marginLeft: '24px',
    marginBottom: '6px',
  },
  checkinRating: {
    fontSize: '13px',
    color: '#64748b',
  },
  checkinProgressNotes: {
    fontSize: '13px',
    color: '#94a3b8',
    marginLeft: '24px',
    fontStyle: 'italic',
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    padding: '20px',
  },
  modal: {
    background: 'white',
    borderRadius: '16px',
    width: '100%',
    maxWidth: '500px',
    maxHeight: '90vh',
    overflow: 'auto',
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '20px 24px',
    borderBottom: '1px solid #f0f0f0',
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
    color: '#666',
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
    color: '#333',
    marginBottom: '8px',
  },
  textarea: {
    width: '100%',
    padding: '10px 14px',
    border: '1px solid #e0e0e0',
    borderRadius: '8px',
    fontSize: '14px',
    outline: 'none',
    resize: 'vertical',
    boxSizing: 'border-box',
  },
  ratingInput: {
    display: 'flex',
    gap: '4px',
  },
  starButton: {
    background: 'none',
    border: 'none',
    fontSize: '28px',
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
    background: 'transparent',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '500',
    color: '#374151',
    cursor: 'pointer',
  },
  submitButton: {
    flex: 1,
    padding: '12px',
    background: '#000000',
    border: '1px solid #000000',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '500',
    color: 'white',
    cursor: 'pointer',
  },
  interactionSection: {
    display: 'flex',
    gap: '16px',
    marginBottom: '24px',
  },
  interactionButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '12px 20px',
    background: 'white',
    border: '1px solid #e2e8f0',
    borderRadius: '12px',
    color: '#64748b',
    fontSize: '15px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  interactionButtonActive: {
    color: '#ef4444',
    borderColor: '#ef4444',
    background: '#fef2f2',
  },
  shareModeSelector: {
    display: 'flex',
    gap: '12px',
    marginBottom: '20px',
  },
  shareModeButton: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    padding: '12px',
    border: '1px solid #e2e8f0',
    borderRadius: '12px',
    background: 'transparent',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    fontSize: '14px',
    fontWeight: '500',
    color: '#374151',
  },
  shareModeButtonActive: {
    borderColor: '#000000',
    background: '#000000',
    color: '#ffffff',
  },
  userList: {
    maxHeight: '200px',
    overflowY: 'auto',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
  },
  userItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '12px',
    cursor: 'pointer',
    transition: 'background 0.2s ease',
    borderBottom: '1px solid #f1f5f9',
  },
  userItemSelected: {
    background: '#f0f4ff',
  },
  userAvatarSmall: {
    width: '40px',
    height: '40px',
    borderRadius: '50%',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
    fontWeight: 'bold',
    fontSize: '14px',
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
    color: '#94a3b8',
  },
  submitButtonDisabled: {
    background: '#cbd5e1',
    cursor: 'not-allowed',
  },
};

export default PlanDetail;
