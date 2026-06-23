import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, CheckCircle, Calendar, Heart, MessageCircle, Search, Trash2, ArrowLeft, CheckSquare, Square } from 'lucide-react';
import { activityApi, commentApi } from '../services/api';
import type { Activity } from '../types';

const Activities: React.FC = () => {
  const navigate = useNavigate();
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [selectedActivities, setSelectedActivities] = useState<Set<number>>(new Set());

  useEffect(() => {
    loadActivities();
  }, [page]);

  const loadActivities = () => {
    setLoading(true);
    activityApi.getActivities(page, 20)
      .then((data) => {
        if (data.length < 20) {
          setHasMore(false);
        }
        if (page === 1) {
          setActivities(data);
        } else {
          setActivities(prev => [...prev, ...data]);
        }
      })
      .catch(() => setActivities([]))
      .finally(() => setLoading(false));
  };

  const loadMore = () => {
    if (!hasMore || loading) return;
    setPage(prev => prev + 1);
  };

  const filteredActivities = activities.filter((activity) => {
    if (!searchTerm) return true;
    return activity.displayText?.toLowerCase().includes(searchTerm.toLowerCase());
  });

  const handleActivityClick = async (activity: Activity) => {
    if (!activity.targetId || !activity.targetType) return;
    
    switch (activity.targetType.toLowerCase()) {
      case 'plan':
        navigate(`/plan/${activity.targetId}`);
        break;
      case 'post':
        navigate(`/post/${activity.targetId}`);
        break;
      case 'comment':
        try {
          const postId = await commentApi.getPostIdByCommentId(activity.targetId);
          navigate(`/post/${postId}`);
        } catch (err) {
          console.error('Failed to get post id:', err);
          navigate('/community');
        }
        break;
      default:
        break;
    }
  };

  const handleDeleteActivity = async (activityId: number) => {
    if (!window.confirm('确定要删除这条活动记录吗？')) return;
    try {
      await activityApi.deleteActivity(activityId);
      setActivities(prev => prev.filter(a => a.id !== activityId));
      setSelectedActivities(prev => {
        const newSet = new Set(prev);
        newSet.delete(activityId);
        return newSet;
      });
      alert('删除成功');
    } catch (err) {
      alert('删除失败，请重试');
    }
  };

  const toggleActivitySelection = (activityId: number) => {
    setSelectedActivities(prev => {
      const newSet = new Set(prev);
      if (newSet.has(activityId)) {
        newSet.delete(activityId);
      } else {
        newSet.add(activityId);
      }
      return newSet;
    });
  };

  const toggleSelectAll = () => {
    if (selectedActivities.size === filteredActivities.length) {
      setSelectedActivities(new Set());
    } else {
      setSelectedActivities(new Set(filteredActivities.map(a => a.id)));
    }
  };

  const handleDeleteSelected = async () => {
    if (selectedActivities.size === 0) {
      alert('请先选择要删除的活动记录');
      return;
    }
    if (!window.confirm(`确定要删除选中的 ${selectedActivities.size} 条活动记录吗？`)) return;
    try {
      await activityApi.deleteActivities(Array.from(selectedActivities));
      setActivities(prev => prev.filter(a => !selectedActivities.has(a.id)));
      setSelectedActivities(new Set());
      alert('删除成功');
    } catch (err) {
      alert('删除失败，请重试');
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <button style={styles.backButton} onClick={() => navigate('/profile')}>
          <ArrowLeft size={20} />
          <span>返回</span>
        </button>
        <h1 style={styles.title}>活动记录</h1>
        <div style={styles.placeholder}></div>
      </div>

      <div style={styles.toolbar}>
        <div style={styles.searchWrapper}>
          <Search size={18} style={styles.searchIcon} />
          <input
            type="text"
            placeholder="搜索活动记录..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={styles.searchInput}
          />
        </div>
        {filteredActivities.length > 0 && (
          <div style={styles.batchActions}>
            <button 
              style={styles.batchButton}
              onClick={toggleSelectAll}
            >
              {selectedActivities.size === filteredActivities.length ? (
                <CheckSquare size={16} />
              ) : (
                <Square size={16} />
              )}
              <span>
                {selectedActivities.size === filteredActivities.length ? '取消全选' : '全选'}
              </span>
            </button>
            {selectedActivities.size > 0 && (
              <button 
                style={{ ...styles.batchButton, ...styles.deleteButton }}
                onClick={handleDeleteSelected}
              >
                <Trash2 size={16} />
                <span>删除选中 ({selectedActivities.size})</span>
              </button>
            )}
          </div>
        )}
      </div>

      {loading ? (
        <div style={styles.loading}>加载中...</div>
      ) : (
        <div style={styles.activitiesList}>
          {filteredActivities.map((activity) => (
            <div 
              key={activity.id} 
              style={{
                ...styles.activityItem,
                ...(selectedActivities.has(activity.id) ? styles.activityItemSelected : {})
              }}
              className="activity-item"
            >
              <button
                style={styles.checkboxButton}
                onClick={() => toggleActivitySelection(activity.id)}
              >
                {selectedActivities.has(activity.id) ? (
                  <CheckSquare size={18} />
                ) : (
                  <Square size={18} />
                )}
              </button>
              <div style={styles.activityIcon}>
                {activity.type === 'PLAN_CREATED' && <BookOpen size={16} />}
                {activity.type === 'PLAN_COMPLETED' && <CheckCircle size={16} />}
                {activity.type === 'PLAN_CHECKIN' && <Calendar size={16} />}
                {activity.type === 'POST_LIKED' && <Heart size={16} />}
                {activity.type === 'POST_COMMENTED' && <MessageCircle size={16} />}
                {activity.type === 'COMMENT_LIKED' && <Heart size={16} />}
                {activity.type === 'COMMENT_REPLIED' && <MessageCircle size={16} />}
              </div>
              <div 
                style={styles.activityContent}
                onClick={() => handleActivityClick(activity)}
              >
                <span style={styles.activityText}>{activity.displayText}</span>
                <span style={styles.activityTime}>{activity.createdAt}</span>
              </div>
              <button 
                style={styles.activityDeleteButton} 
                onClick={() => handleDeleteActivity(activity.id)}
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      )}

      {!loading && filteredActivities.length === 0 && (
        <div style={styles.emptyState}>
          <BookOpen size={48} style={{ color: '#cbd5e1' }} />
          <h3 style={styles.emptyTitle}>暂无活动记录</h3>
          <p style={styles.emptyDescription}>您还没有任何活动记录</p>
        </div>
      )}

      {!loading && hasMore && filteredActivities.length > 0 && (
        <div style={styles.loadMoreContainer}>
          <button style={styles.loadMoreButton} onClick={loadMore}>
            加载更多
          </button>
        </div>
      )}
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    minHeight: '100vh',
    background: '#f1f5f9',
    padding: '40px 20px',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  },
  header: {
    maxWidth: '800px',
    margin: '0 auto 30px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  backButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 20px',
    background: '#f1f5f9',
    border: '1px solid #e2e8f0',
    borderRadius: '10px',
    color: '#374151',
    fontSize: '15px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  title: {
    fontSize: '32px',
    fontWeight: '700',
    color: '#000000',
    margin: 0,
  },
  placeholder: {
    width: '100px',
  },
  toolbar: {
    maxWidth: '800px',
    margin: '0 auto 20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  searchWrapper: {
    position: 'relative',
  },
  batchActions: {
    display: 'flex',
    gap: '12px',
    alignItems: 'center',
  },
  batchButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 16px',
    background: '#f1f5f9',
    border: '1px solid #e2e8f0',
    borderRadius: '10px',
    color: '#374151',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  deleteButton: {
    background: '#fef2f2',
    borderColor: '#fecaca',
    color: '#dc2626',
  },
  searchIcon: {
    position: 'absolute',
    left: '16px',
    top: '50%',
    transform: 'translateY(-50%)',
    color: '#94a3b8',
  },
  searchInput: {
    width: '100%',
    padding: '12px 12px 12px 48px',
    background: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: '10px',
    fontSize: '14px',
    color: '#1e293b',
    outline: 'none',
    boxSizing: 'border-box',
  },
  loading: {
    textAlign: 'center',
    padding: '60px',
    color: '#64748b',
    fontSize: '18px',
  },
  activitiesList: {
    maxWidth: '800px',
    margin: '0 auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  activityItem: {
    display: 'flex',
    gap: '12px',
    padding: '16px',
    background: 'white',
    borderRadius: '12px',
    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.1)',
    transition: 'all 0.2s ease',
  },
  activityItemSelected: {
    background: '#f0f9ff',
    boxShadow: '0 4px 20px rgba(59, 130, 246, 0.15)',
    border: '2px solid #3b82f6',
  },
  checkboxButton: {
    padding: '4px',
    background: 'none',
    border: 'none',
    color: '#64748b',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.2s ease',
  },
  activityIcon: {
    width: '40px',
    height: '40px',
    background: '#f1f5f9',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '16px',
    color: '#64748b',
    flexShrink: 0,
  },
  activityContent: {
    flex: 1,
    cursor: 'pointer',
  },
  activityText: {
    display: 'block',
    fontSize: '15px',
    color: '#0f172a',
    marginBottom: '4px',
    lineHeight: '1.5',
  },
  activityTime: {
    fontSize: '13px',
    color: '#64748b',
  },
  activityDeleteButton: {
    padding: '8px',
    background: '#fef2f2',
    border: 'none',
    borderRadius: '8px',
    color: '#ef4444',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  emptyState: {
    textAlign: 'center',
    padding: '60px',
    background: 'white',
    borderRadius: '16px',
    maxWidth: '400px',
    margin: '40px auto',
  },
  emptyTitle: {
    fontSize: '20px',
    fontWeight: '600',
    color: '#1a1a2e',
    margin: '20px 0 8px',
  },
  emptyDescription: {
    fontSize: '14px',
    color: '#666',
    margin: 0,
  },
  loadMoreContainer: {
    textAlign: 'center',
    padding: '20px',
  },
  loadMoreButton: {
    padding: '12px 32px',
    background: '#000000',
    border: 'none',
    borderRadius: '10px',
    color: '#ffffff',
    fontSize: '15px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
};

export default Activities;