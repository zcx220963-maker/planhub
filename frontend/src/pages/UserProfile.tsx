
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Mail, ClipboardList, FileText, MapPin, Calendar, CheckCircle, Heart, MessageCircle, BookOpen, Users, UserPlus, UserMinus, MessageSquare, Star } from 'lucide-react';
import { userApi, chatApi, commentApi } from '../services/api';
import type { UserProfileResponse, PlanSummary, PostSummary, Activity, User, LikedItemResponse } from '../types';
import { useAuth } from '../context/AuthContext';

const UserProfile: React.FC = () => {
  const { userId } = useParams<{ userId: string }>();
  const navigate = useNavigate();
  const { user: currentUser } = useAuth();
  const [profile, setProfile] = useState<UserProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isFollowing, setIsFollowing] = useState(false);
  const [followLoading, setFollowLoading] = useState(false);
  const [showFollowers, setShowFollowers] = useState(false);
  const [showFollowing, setShowFollowing] = useState(false);
  const [followers, setFollowers] = useState<User[]>([]);
  const [following, setFollowing] = useState<User[]>([]);
  const [listLoading, setListLoading] = useState(false);
  const [likedContent, setLikedContent] = useState<LikedItemResponse[]>([]);
  const [likedLoading, setLikedLoading] = useState(false);

  useEffect(() => {
    if (userId) {
      loadProfile(parseInt(userId));
      loadLikedContent(parseInt(userId));
    }
  }, [userId]);

  const loadProfile = async (id: number) => {
    console.log('=== 开始加载用户资料 ===', { id, currentUserId: currentUser?.id });
    setLoading(true);
    setError(null);
    try {
      const data = await userApi.getUserProfile(id, currentUser?.id);
      console.log('=== 成功获取用户资料 ===', data);
      console.log('=== 活动记录详细内容 ===', data.activities);
      console.log('=== showActivities ===', data.showActivities);
      console.log('=== activities 长度 ===', data.activities?.length);
      setProfile(data);
      setIsFollowing(data.isFollowing || false);
    } catch (err) {
      console.error('=== 获取用户资料失败 ===', err);
      const errorMessage = err instanceof Error ? err.message : '无法加载用户信息';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const loadLikedContent = async (id: number) => {
    setLikedLoading(true);
    try {
      const data = await userApi.getLikedContent(id, currentUser?.id);
      setLikedContent(data);
    } catch (err) {
      console.error('Failed to load liked content:', err);
    } finally {
      setLikedLoading(false);
    }
  };

  const handleFollow = async () => {
    if (!currentUser || !userId) return;
    setFollowLoading(true);
    try {
      if (isFollowing) {
        await userApi.unfollowUser(currentUser.id, parseInt(userId));
        setIsFollowing(false);
        if (profile) {
          setProfile({ ...profile, followerCount: profile.followerCount - 1 });
        }
      } else {
        await userApi.followUser(currentUser.id, parseInt(userId));
        setIsFollowing(true);
        if (profile) {
          setProfile({ ...profile, followerCount: profile.followerCount + 1 });
        }
      }
    } catch (err) {
      console.error('Failed to follow/unfollow:', err);
    } finally {
      setFollowLoading(false);
    }
  };

  const handleStartChat = async () => {
    if (!userId) return;
    try {
      await chatApi.sendMessage(parseInt(userId), '你好！');
      alert('已成功发起对话！');
      navigate('/notifications?tab=chat');
    } catch (err) {
      console.error('Failed to start chat:', err);
      alert('发起对话失败: ' + ((err as any).response?.data?.message || '未知错误'));
    }
  };

  const loadFollowers = async () => {
    if (!userId || !profile?.showFollowers) return;
    setListLoading(true);
    try {
      const data = await userApi.getFollowers(parseInt(userId));
      setFollowers(data);
      setShowFollowers(true);
      setShowFollowing(false);
    } catch (err) {
      console.error('Failed to load followers:', err);
    } finally {
      setListLoading(false);
    }
  };

  const loadFollowing = async () => {
    if (!userId || !profile?.showFollowing) return;
    setListLoading(true);
    try {
      const data = await userApi.getFollowing(parseInt(userId));
      setFollowing(data);
      setShowFollowing(true);
      setShowFollowers(false);
    } catch (err) {
      console.error('Failed to load following:', err);
    } finally {
      setListLoading(false);
    }
  };

  const handlePostClick = (post: PostSummary) => {
    navigate(`/post/${post.id}`);
  };

  const handlePlanClick = (plan: PlanSummary) => {
    navigate(`/plan/${plan.id}`);
  };

  const handleLikedItemClick = (item: LikedItemResponse) => {
    if (item.type === 'post') {
      navigate(`/post/${item.id}`);
    } else {
      navigate(`/plan/${item.id}`);
    }
  };

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

  const getActivityIcon = (type: string) => {
    const upperType = type?.toUpperCase() || "";
    switch (upperType) {
      case 'PLAN_CREATED':
        return <BookOpen size={16} />;
      case 'PLAN_COMPLETED':
        return <CheckCircle size={16} />;
      case 'PLAN_CHECKIN':
        return <Calendar size={16} />;
      case 'POST_LIKED':
        return <Heart size={16} />;
      case 'POST_COMMENTED':
        return <MessageCircle size={16} />;
      case 'COMMENT_LIKED':
        return <Heart size={16} />;
      case 'COMMENT_REPLIED':
        return <MessageCircle size={16} />;
      default:
        return <CheckCircle size={16} />;
    }
  };

  const handleBack = () => {
    navigate(-1);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ACTIVE':
        return '#10b981';
      case 'COMPLETED':
        return '#6366f1';
      case 'PAUSED':
        return '#f59e0b';
      default:
        return '#64748b';
    }
  };

  const getAvatarUrl = (avatarUrl?: string) => {
    if (!avatarUrl) return null;
    if (avatarUrl.startsWith('http')) return avatarUrl;
    if (avatarUrl.startsWith('/')) return `http://localhost:8080${avatarUrl}`;
    return `http://localhost:8080/${avatarUrl}`;
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

  if (error || !profile) {
    return (
      <div style={styles.container}>
        <div style={styles.errorContainer}>
          <p style={styles.errorText}>{error || '用户不存在'}</p>
          <button style={styles.backButton} onClick={handleBack}>
            <ArrowLeft size={18} />
            <span>返回</span>
          </button>
        </div>
      </div>
    );
  }

  const avatarInitial = (profile.displayName?.charAt(0) || profile.username.charAt(0) || 'U').toUpperCase();
  const avatarUrl = getAvatarUrl(profile.avatarUrl);
  const isOwnProfile = currentUser?.id === profile.id;

  return (
    <div style={styles.container}>
      <button style={styles.backButtonTop} onClick={handleBack}>
        <ArrowLeft size={20} />
        <span>返回</span>
      </button>

      <div style={styles.profileCard}>
        <div style={styles.avatarSection}>
          <div 
            style={{
              ...styles.avatar,
              ...(avatarUrl ? {
                backgroundImage: `url(${avatarUrl})`,
                backgroundSize: 'cover',
                backgroundPosition: 'center',
              } : {})
            }}
          >
            {!avatarUrl && (profile.displayName?.charAt(0) || profile.username.charAt(0) || 'U').toUpperCase()}
          </div>
          <h1 style={styles.displayName}>{profile.displayName || profile.username}</h1>
          <p style={styles.username}>@{profile.username}</p>
          
          <div style={styles.followStats}>
            <div 
              style={{
                ...styles.statItem,
                cursor: profile.showFollowers ? 'pointer' : 'default',
                opacity: profile.showFollowers ? 1 : 0.6,
              }} 
              onClick={() => {
                if (profile.showFollowers) {
                  loadFollowers();
                }
              }}
            >
              <span style={styles.statNumber}>{profile.followerCount || 0}</span>
              <span style={styles.statLabel}>粉丝</span>
            </div>
            <div style={styles.statDivider}></div>
            <div 
              style={{
                ...styles.statItem,
                cursor: profile.showFollowing ? 'pointer' : 'default',
                opacity: profile.showFollowing ? 1 : 0.6,
              }} 
              onClick={() => {
                if (profile.showFollowing) {
                  loadFollowing();
                }
              }}
            >
              <span style={styles.statNumber}>{profile.followingCount || 0}</span>
              <span style={styles.statLabel}>关注</span>
            </div>
          </div>
          
          {!isOwnProfile && currentUser && (
            <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
              <button
                style={isFollowing ? styles.unfollowButton : styles.followButton}
                onClick={handleFollow}
                disabled={followLoading}
              >
                {followLoading ? (
                  '...'
                ) : isFollowing ? (
                  <>
                    <UserMinus size={18} />
                    <span>取消关注</span>
                  </>
                ) : (
                  <>
                    <UserPlus size={18} />
                    <span>关注</span>
                  </>
                )}
              </button>
              <button
                style={styles.chatButton}
                onClick={handleStartChat}
              >
                <MessageSquare size={18} />
                <span>发起对话</span>
              </button>
            </div>
          )}
        </div>

        <div style={styles.infoSection}>
          <div style={styles.infoItem}>
            <Mail size={18} style={styles.infoIcon} />
            <span style={styles.infoText}>{profile.email}</span>
          </div>
          {profile.bio && (
            <div style={styles.bioSection}>
              <p style={styles.bioText}>{profile.bio}</p>
            </div>
          )}
        </div>
      </div>

      {showFollowers && profile.showFollowers && (
        <div style={styles.listCard}>
          <div style={styles.listHeader}>
            <Users size={20} style={{ color: '#64748b' }} />
            <h2 style={styles.listTitle}>粉丝列表</h2>
            <button style={styles.closeButton} onClick={() => setShowFollowers(false)}>✕</button>
          </div>
          {listLoading ? (
            <div style={styles.listLoading}>加载中...</div>
          ) : followers.length === 0 ? (
            <div style={styles.emptyState}>
              <Users size={32} style={{ color: '#cbd5e1' }} />
              <p style={styles.emptyText}>暂无粉丝</p>
            </div>
          ) : (
            <div style={styles.userList}>
              {followers.map((user) => (
                <div 
                  key={user.id} 
                  style={styles.userItem}
                  onClick={() => navigate(`/user/${user.id}`)}
                >
                  <div style={{
                    ...styles.userAvatar,
                    ...(getAvatarUrl(user.avatarUrl) ? {
                      backgroundImage: `url(${getAvatarUrl(user.avatarUrl)})`,
                      backgroundSize: 'cover',
                      backgroundPosition: 'center',
                    } : {})
                  }}>
                    {!getAvatarUrl(user.avatarUrl) && (user.displayName?.charAt(0) || user.username.charAt(0)).toUpperCase()}
                  </div>
                  <div style={styles.userInfo}>
                    <div style={styles.userName}>{user.displayName || user.username}</div>
                    <div style={styles.userUsername}>@{user.username}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {showFollowing && profile.showFollowing && (
        <div style={styles.listCard}>
          <div style={styles.listHeader}>
            <Users size={20} style={{ color: '#64748b' }} />
            <h2 style={styles.listTitle}>关注列表</h2>
            <button style={styles.closeButton} onClick={() => setShowFollowing(false)}>✕</button>
          </div>
          {listLoading ? (
            <div style={styles.listLoading}>加载中...</div>
          ) : following.length === 0 ? (
            <div style={styles.emptyState}>
              <Users size={32} style={{ color: '#cbd5e1' }} />
              <p style={styles.emptyText}>暂无关注</p>
            </div>
          ) : (
            <div style={styles.userList}>
              {following.map((user) => (
                <div 
                  key={user.id} 
                  style={styles.userItem}
                  onClick={() => navigate(`/user/${user.id}`)}
                >
                  <div style={{
                    ...styles.userAvatar,
                    ...(getAvatarUrl(user.avatarUrl) ? {
                      backgroundImage: `url(${getAvatarUrl(user.avatarUrl)})`,
                      backgroundSize: 'cover',
                      backgroundPosition: 'center',
                    } : {})
                  }}>
                    {!getAvatarUrl(user.avatarUrl) && (user.displayName?.charAt(0) || user.username.charAt(0)).toUpperCase()}
                  </div>
                  <div style={styles.userInfo}>
                    <div style={styles.userName}>{user.displayName || user.username}</div>
                    <div style={styles.userUsername}>@{user.username}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div style={styles.contentSections}>
        <div style={styles.section}>
          <div style={styles.sectionHeader}>
            <ClipboardList size={22} style={{ color: '#64748b' }} />
            <h2 style={styles.sectionTitle}>公开计划</h2>
            <span style={styles.sectionCount}>{profile.publicPlans?.length || 0}</span>
          </div>

          {profile.publicPlans && profile.publicPlans.length > 0 ? (
            <div style={styles.plansList}>
              {profile.publicPlans.map((plan) => (
                <div
                  key={plan.id}
                  style={styles.planCard}
                  onClick={() => handlePlanClick(plan)}
                >
                  <div style={styles.planHeader}>
                    <h3 style={styles.planTitle}>{plan.title}</h3>
                    <span
                    style={{
                      ...styles.planStatus,
                    }}
                  >
                    {plan.status === 'ACTIVE' ? '进行中' : plan.status === 'COMPLETED' ? '已完成' : '已暂停'}
                  </span>
                  </div>
                  {plan.description && (
                    <p style={styles.planDescription}>{plan.description}</p>
                  )}
                  <div style={styles.planFooter}>
                    <div style={styles.planProgress}>
                      <div style={styles.progressBar}>
                        <div
                          style={{
                            ...styles.progressFill,
                            width: `${plan.progressPercentage}%`,
                            background: '#000000',
                          }}
                        ></div>
                      </div>
                      <span style={styles.progressText}>{plan.progressPercentage}%</span>
                    </div>
                    {plan.targetDate && (
                      <div style={styles.planDate}>
                        <Calendar size={14} />
                        <span>{plan.targetDate}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={styles.emptyState}>
              <ClipboardList size={32} style={{ color: '#94a3b8' }} />
              <p style={styles.emptyText}>暂无公开计划</p>
            </div>
          )}
        </div>

        <div style={styles.section}>
          <div style={styles.sectionHeader}>
            <FileText size={22} style={{ color: '#64748b' }} />
            <h2 style={styles.sectionTitle}>公开帖子</h2>
            <span style={styles.sectionCount}>{profile.publicPosts?.length || 0}</span>
          </div>

          {profile.publicPosts && profile.publicPosts.length > 0 ? (
            <div style={styles.postsList}>
              {profile.publicPosts.map((post) => (
                <div
                  key={post.id}
                  style={styles.postCard}
                  onClick={() => handlePostClick(post)}
                >
                  <p style={styles.postContent}>{post.content}</p>
                  {post.hashtags && (
                    <div style={styles.hashtags}>
                      {post.hashtags.split(',').slice(0, 3).map((tag, index) => (
                        <span key={index} style={styles.hashtag}>
                          #{tag.trim()}
                        </span>
                      ))}
                    </div>
                  )}
                  <div style={styles.postFooter}>
                    <span style={styles.postStat}>❤️ {post.likes}</span>
                    <span style={styles.postStat}>💬 {post.commentsCount}</span>
                    <span style={styles.postDate}>
                      {post.createdAt ? new Date(post.createdAt).toLocaleDateString('zh-CN') : ''}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={styles.emptyState}>
              <FileText size={32} style={{ color: '#94a3b8' }} />
              <p style={styles.emptyText}>暂无公开帖子</p>
            </div>
          )}
        </div>

        <div style={styles.section}>
          <div style={styles.sectionHeader}>
            <CheckCircle size={22} style={{ color: '#64748b' }} />
            <h2 style={styles.sectionTitle}>活动记录</h2>
            <span style={styles.sectionCount}>{profile.activities?.length || 0}</span>
          </div>

          {profile.showActivities && profile.activities && profile.activities.length > 0 ? (
            <div style={styles.activityList}>
              {profile.activities.map((activity) => (
                <div
                  key={activity.id}
                  style={styles.activityItem}
                  onClick={() => handleActivityClick(activity)}
                >
                  <div style={styles.activityIcon}>
                    {getActivityIcon(activity.type)}
                  </div>
                  <div style={styles.activityContent}>
                    <span style={styles.activityText}>{activity.displayText}</span>
                    <span style={styles.activityTime}>{activity.createdAt}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : !profile.showActivities ? (
            <div style={styles.emptyState}>
              <CheckCircle size={32} style={{ color: '#cbd5e1' }} />
              <p style={styles.emptyText}>该用户已隐藏活动记录</p>
            </div>
          ) : (
            <div style={styles.emptyState}>
              <CheckCircle size={32} style={{ color: '#cbd5e1' }} />
              <p style={styles.emptyText}>暂无活动记录</p>
            </div>
          )}
        </div>

        <div style={styles.section}>
          <div style={styles.sectionHeader}>
            <Heart size={22} style={{ color: '#ef4444' }} />
            <h2 style={styles.sectionTitle}>点赞内容</h2>
            <span style={styles.sectionCount}>{likedContent.length}</span>
          </div>

          {likedLoading ? (
            <div style={styles.emptyState}>
              <div style={styles.loadingSpinner}></div>
              <p style={styles.emptyText}>加载中...</p>
            </div>
          ) : profile.showLikedContent && likedContent.length > 0 ? (
            <div style={styles.likedList}>
              {likedContent.map((item) => (
                <div
                  key={`${item.type}-${item.id}`}
                  style={styles.likedCard}
                  onClick={() => handleLikedItemClick(item)}
                >
                  <div style={styles.likedIcon}>
                    {item.type === 'post' ? <FileText size={20} /> : <ClipboardList size={20} />}
                  </div>
                  <div style={styles.likedContent}>
                    <h4 style={styles.likedTitle}>
                      {item.title || item.content?.substring(0, 50) || (item.type === 'post' ? '帖子' : '计划')}
                    </h4>
                    {item.content && item.content.length > 50 && (
                      <p style={styles.likedDescription}>{item.content.substring(0, 100)}...</p>
                    )}
                    <div style={styles.likedFooter}>
                      <span style={styles.likedType}>
                        {item.type === 'post' ? '帖子' : '计划'}
                      </span>
                      {item.status && (
                        <span style={styles.likedStatus}>
                          {item.status === 'ACTIVE' ? '进行中' : item.status === 'COMPLETED' ? '已完成' : item.status}
                        </span>
                      )}
                      <span style={styles.likedDate}>
                        {item.likedAt ? new Date(item.likedAt).toLocaleDateString('zh-CN') : ''}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : !profile.showLikedContent ? (
            <div style={styles.emptyState}>
              <Heart size={32} style={{ color: '#cbd5e1' }} />
              <p style={styles.emptyText}>该用户已隐藏点赞内容</p>
            </div>
          ) : (
            <div style={styles.emptyState}>
              <Heart size={32} style={{ color: '#cbd5e1' }} />
              <p style={styles.emptyText}>暂无点赞内容</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    minHeight: '100%',
    paddingBottom: '40px',
  },
  backButtonTop: {
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
    marginBottom: '24px',
    transition: 'all 0.3s ease',
  },
  loadingContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '60px 20px',
  },
  loadingSpinner: {
    width: '48px',
    height: '48px',
    border: '4px solid #e2e8f0',
    borderTop: '4px solid #667eea',
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
    padding: '60px 20px',
  },
  errorText: {
    color: '#ef4444',
    fontSize: '16px',
    marginBottom: '24px',
  },
  backButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '12px 24px',
    background: 'transparent',
    border: '1px solid #e2e8f0',
    borderRadius: '10px',
    color: '#374151',
    fontSize: '15px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  profileCard: {
    background: 'white',
    borderRadius: '16px',
    padding: '32px',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)',
    border: '1px solid #e2e8f0',
    marginBottom: '24px',
  },
  avatarSection: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    marginBottom: '24px',
  },
  avatar: {
    width: '100px',
    height: '100px',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
    fontSize: '36px',
    fontWeight: 'bold',
    marginBottom: '16px',
  },
  displayName: {
    fontSize: '24px',
    fontWeight: 'bold',
    color: '#0f172a',
    marginBottom: '4px',
  },
  username: {
    fontSize: '16px',
    color: '#64748b',
    marginBottom: '16px',
  },
  followStats: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '16px',
  },
  statItem: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '8px 20px',
    cursor: 'pointer',
    borderRadius: '8px',
    transition: 'background 0.2s ease',
  },
  statNumber: {
    fontSize: '20px',
    fontWeight: 'bold',
    color: '#1e293b',
  },
  statLabel: {
    fontSize: '13px',
    color: '#64748b',
  },
  statDivider: {
    width: '1px',
    height: '40px',
    background: '#e2e8f0',
  },
  followButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 24px',
    background: '#000000',
    border: '1px solid #000000',
    borderRadius: '10px',
    color: 'white',
    fontSize: '15px',
    fontWeight: 'medium',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  unfollowButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 24px',
    background: 'transparent',
    border: '1px solid #e2e8f0',
    borderRadius: '10px',
    color: '#374151',
    fontSize: '15px',
    fontWeight: 'medium',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  chatButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 24px',
    background: 'transparent',
    border: '1px solid #e2e8f0',
    borderRadius: '10px',
    color: '#374151',
    fontSize: '15px',
    fontWeight: 'medium',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  infoSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  infoItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    color: '#475569',
    fontSize: '15px',
  },
  infoIcon: {
    color: '#64748b',
  },
  infoText: {
    color: '#475569',
  },
  bioSection: {
    padding: '16px',
    background: '#f8fafc',
    borderRadius: '12px',
    marginTop: '8px',
  },
  bioText: {
    fontSize: '15px',
    color: '#475569',
    lineHeight: '1.6',
    margin: 0,
  },
  listCard: {
    background: 'white',
    borderRadius: '16px',
    padding: '24px',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)',
    border: '1px solid #e2e8f0',
    marginBottom: '24px',
  },
  listHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '20px',
  },
  listTitle: {
    fontSize: '18px',
    fontWeight: 'bold',
    color: '#0f172a',
    margin: 0,
    flex: 1,
  },
  closeButton: {
    background: 'none',
    border: 'none',
    fontSize: '20px',
    color: '#64748b',
    cursor: 'pointer',
    padding: '4px 8px',
  },
  listLoading: {
    textAlign: 'center',
    padding: '20px',
    color: '#64748b',
  },
  userList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  userItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '12px',
    background: '#f8fafc',
    borderRadius: '10px',
    cursor: 'pointer',
    transition: 'background 0.2s ease',
  },
  userAvatar: {
    width: '40px',
    height: '40px',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
    fontSize: '16px',
    fontWeight: 'bold',
    flexShrink: 0,
  },
  userInfo: {
    flex: 1,
  },
  userName: {
    fontSize: '15px',
    fontWeight: 'medium',
    color: '#1e293b',
  },
  userUsername: {
    fontSize: '13px',
    color: '#64748b',
  },
  contentSections: {
    display: 'flex',
    flexDirection: 'column',
    gap: '24px',
  },
  section: {
    background: 'white',
    borderRadius: '16px',
    padding: '24px',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)',
    border: '1px solid #e2e8f0',
  },
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '20px',
  },
  sectionTitle: {
    fontSize: '18px',
    fontWeight: 'bold',
    color: '#0f172a',
    margin: 0,
    flex: 1,
  },
  sectionCount: {
    background: '#f1f5f9',
    color: '#64748b',
    padding: '4px 12px',
    borderRadius: '20px',
    fontSize: '14px',
    fontWeight: 'medium',
  },
  plansList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  planCard: {
    padding: '20px',
    background: '#f8fafc',
    borderRadius: '12px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    border: '1px solid transparent',
  },
  planHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '12px',
  },
  planTitle: {
    fontSize: '16px',
    fontWeight: 'bold',
    color: '#0f172a',
    margin: 0,
    flex: 1,
    marginRight: '12px',
  },
  planStatus: {
    padding: '4px 12px',
    borderRadius: '20px',
    fontSize: '12px',
    fontWeight: 'medium',
    background: 'transparent',
    border: '1px solid #e2e8f0',
    color: '#374151',
  },
  planDescription: {
    fontSize: '14px',
    color: '#64748b',
    marginBottom: '16px',
    lineHeight: '1.5',
  },
  planFooter: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  planProgress: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    flex: 1,
    marginRight: '16px',
  },
  progressBar: {
    flex: 1,
    height: '8px',
    background: '#e2e8f0',
    borderRadius: '4px',
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: '4px',
    transition: 'width 0.3s ease',
  },
  progressText: {
    fontSize: '14px',
    fontWeight: 'medium',
    color: '#475569',
    minWidth: '45px',
  },
  planDate: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '13px',
    color: '#64748b',
  },
  postsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  postCard: {
    padding: '20px',
    background: '#f8fafc',
    borderRadius: '12px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    border: '1px solid transparent',
  },
  postContent: {
    fontSize: '15px',
    color: '#0f172a',
    lineHeight: '1.6',
    marginBottom: '12px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    display: '-webkit-box',
    WebkitLineClamp: 3,
    WebkitBoxOrient: 'vertical',
  },
  hashtags: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
    marginBottom: '12px',
  },
  hashtag: {
    fontSize: '13px',
    color: '#374151',
    background: 'transparent',
    border: '1px solid #e2e8f0',
    padding: '4px 10px',
    borderRadius: '12px',
  },
  postFooter: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    paddingTop: '12px',
    borderTop: '1px solid #e2e8f0',
  },
  postStat: {
    fontSize: '13px',
    color: '#64748b',
  },
  postDate: {
    fontSize: '13px',
    color: '#94a3b8',
    marginLeft: 'auto',
  },
  activityList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  activityItem: {
    display: 'flex',
    gap: '12px',
    padding: '12px',
    background: '#f8fafc',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'background 0.2s ease',
  },
  activityIcon: {
    width: '32px',
    height: '32px',
    background: '#e0f2fe',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#667eea',
    flexShrink: 0,
  },
  activityContent: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  activityText: {
    fontSize: '14px',
    color: '#1e293b',
  },
  activityTime: {
    fontSize: '12px',
    color: '#94a3b8',
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '40px 20px',
  },
  emptyText: {
    marginTop: '12px',
    color: '#94a3b8',
    fontSize: '14px',
  },
  likedList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  likedCard: {
    display: 'flex',
    gap: '16px',
    padding: '16px',
    background: '#f8fafc',
    borderRadius: '12px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    border: '1px solid transparent',
  },
  likedIcon: {
    width: '48px',
    height: '48px',
    background: '#e2e8f0',
    borderRadius: '12px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#475569',
    flexShrink: 0,
  },
  likedContent: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  likedTitle: {
    fontSize: '15px',
    fontWeight: 'bold',
    color: '#0f172a',
    margin: 0,
  },
  likedDescription: {
    fontSize: '13px',
    color: '#64748b',
    margin: 0,
    lineHeight: '1.5',
  },
  likedFooter: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    flexWrap: 'wrap',
  },
  likedType: {
    fontSize: '12px',
    color: '#667eea',
    background: '#e0f2fe',
    padding: '4px 10px',
    borderRadius: '10px',
    fontWeight: 'medium',
  },
  likedStatus: {
    fontSize: '12px',
    color: '#10b981',
    background: '#d1fae5',
    padding: '4px 10px',
    borderRadius: '10px',
    fontWeight: 'medium',
  },
  likedDate: {
    fontSize: '12px',
    color: '#94a3b8',
    marginLeft: 'auto',
  },
};

export default UserProfile;
