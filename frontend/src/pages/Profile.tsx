import React, { useState, useEffect, useRef } from 'react';
import { Calendar, Edit2, Bell, Shield, Globe, Save, X, Camera, CheckCircle, Heart, MessageCircle, BookOpen, MessageSquare, Users, FileText, ClipboardList } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { planApi, userApi, postApi, activityApi, commentApi } from '../services/api';
import { useNavigate } from 'react-router-dom';
import type { Plan, Activity, Post, User, LikedItemResponse } from '../types';

const Profile: React.FC = () => {
  const { user, updateUser } = useAuth();
  const navigate = useNavigate();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [posts, setPosts] = useState<Post[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [isEditing, setIsEditing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isEditingBio, setIsEditingBio] = useState(false);
  const [showPrivacySettings, setShowPrivacySettings] = useState(false);
  const [showActivities, setShowActivities] = useState(true);
  const [showFollowersList, setShowFollowersList] = useState(true);
  const [showFollowingList, setShowFollowingList] = useState(true);
  const [followers, setFollowers] = useState<User[]>([]);
  const [following, setFollowing] = useState<User[]>([]);
  const [showFollowers, setShowFollowers] = useState(false);
  const [showFollowing, setShowFollowing] = useState(false);
  const [listLoading, setListLoading] = useState(false);
  const [followerCount, setFollowerCount] = useState(0);
  const [followingCount, setFollowingCount] = useState(0);
  const [showLikedContent, setShowLikedContent] = useState(true);
  const [likedContent, setLikedContent] = useState<LikedItemResponse[]>([]);
  const [likedLoading, setLikedLoading] = useState(false);
  const [showAboutModal, setShowAboutModal] = useState(false);
  const [showLikedModal, setShowLikedModal] = useState(false);
  const [likedFilter, setLikedFilter] = useState<'all' | 'post' | 'plan'>('post');
  const [editForm, setEditForm] = useState({
    username: '',
    displayName: '',
    bio: '',
    location: '',
    websiteUrl: '',
  });
  const [bioText, setBioText] = useState('');
  const [hoveredActivityId, setHoveredActivityId] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleEditAvatar = () => {
    fileInputRef.current?.click();
  };

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !user) return;

    if (!file.type.startsWith('image/')) {
      alert('请选择图片文件');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      alert('图片大小不能超过5MB');
      return;
    }

    setIsUploading(true);

    try {
      const imageUrl = await postApi.uploadImage(file);
      const updatedUser = await userApi.updateAvatar(user.id, imageUrl);
      if (updateUser) {
        updateUser(updatedUser);
      }
      alert('头像更新成功');
    } catch (err) {
      alert('头像上传失败，请重试');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };



  const handleViewAllPosts = () => {
    navigate('/my-posts');
  };

  const handlePostClick = (postId: number) => {
    navigate(`/post/${postId}`);
  };

  const handleStatClick = (statLabel: string) => {
    switch(statLabel) {
      case '创建的计划':
        navigate('/my-plans');
        break;
      case '完成的计划':
        navigate('/my-plans?status=completed');
        break;
      case '进行中的计划':
        navigate('/my-plans?status=active');
        break;
      case '发布的帖子':
        handleViewAllPosts();
        break;
      case '粉丝':
        loadFollowers().catch(err => console.error('加载粉丝失败:', err));
        break;
      case '关注':
        loadFollowing().catch(err => console.error('加载关注失败:', err));
        break;
    }
  };

  const handleChangePassword = () => {
    navigate('/change-password');
  };

  const handleNotifications = () => {
    navigate('/notifications');
  };

  const handleChat = () => {
    navigate('/notifications?tab=chat');
  };

  const handlePrivacySettings = () => {
    // 从用户数据中读取初始值
    if (user) {
      let privacySettings = {};
      // privacySettings 在用户对象中是一个 JSON 字符串，需要解析
      if (user.privacySettings && typeof user.privacySettings === 'string') {
        try {
          privacySettings = JSON.parse(user.privacySettings);
        } catch (e) {
          console.error('解析隐私设置失败:', e);
        }
      }
      setShowActivities((privacySettings as any).showActivities !== undefined ? (privacySettings as any).showActivities : true);
      setShowFollowersList((privacySettings as any).showFollowers !== undefined ? (privacySettings as any).showFollowers : true);
      setShowFollowingList((privacySettings as any).showFollowing !== undefined ? (privacySettings as any).showFollowing : true);
      setShowLikedContent((privacySettings as any).showLikedContent !== undefined ? (privacySettings as any).showLikedContent : true);
    }
    setShowPrivacySettings(true);
  };
  
  const loadLikedContent = async () => {
    if (!user) return;
    setLikedLoading(true);
    try {
      const data = await userApi.getLikedContent(user.id, user.id);
      setLikedContent(data);
    } catch (err) {
      console.error('Failed to load liked content:', err);
    } finally {
      setLikedLoading(false);
    }
  };

  const handleSavePrivacySettings = async () => {
    if (!user) return;
    try {
      const updatedUser = await userApi.updatePrivacySettings(user.id, { 
        showActivities,
        showFollowers: showFollowersList,
        showFollowing: showFollowingList,
        showLikedContent
      });
      // 更新 AuthContext 中的用户信息
      if (updateUser && updatedUser) {
        updateUser(updatedUser);
      }
      alert('隐私设置保存成功');
      setShowPrivacySettings(false);
    } catch (err) {
      console.error('保存隐私设置失败:', err);
      alert('保存隐私设置失败，请重试');
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
  
  const handleLikedItemClick = (item: LikedItemResponse) => {
    if (item.type === 'post') {
      navigate(`/post/${item.id}`);
    } else {
      navigate(`/plan/${item.id}`);
    }
  };

  const handleDeleteActivity = async (activityId: number) => {
    if (!window.confirm('确定要删除这条活动记录吗？')) return;
    try {
      await activityApi.deleteActivity(activityId);
      setActivities(prev => prev.filter(a => a.id !== activityId));
      alert('删除成功');
    } catch (err) {
      alert('删除失败，请重试');
    }
  };

  useEffect(() => {
    if (user) {
      planApi.getAllPlans()
        .then((data) => setPlans(data.filter(p => p.userId === user.id)))
        .catch(() => setPlans([]));
      
      postApi.getUserPosts(user.id)
        .then((data) => setPosts(data))
        .catch(() => setPosts([]));
      
      activityApi.getActivities(1, 20)
        .then((data) => setActivities(Array.isArray(data) ? data : []))
        .catch(() => setActivities([]));
      
      loadUserProfile().catch(err => console.error('加载用户资料失败:', err));
      loadLikedContent().catch(err => console.error('加载点赞内容失败:', err));
      
      setEditForm({
        username: user.username || '',
        displayName: user.displayName || '',
        bio: user.bio || '',
        location: user.location || '',
        websiteUrl: user.websiteUrl || '',
      });
      setBioText(user.bio || '');
    }
  }, [user]);

  const handleSave = async () => {
    if (!user) return;
    try {
      await userApi.updateUser(user.id, editForm);
      if (updateUser) {
        updateUser({ ...user, ...editForm });
      }
      setIsEditing(false);
      alert('资料更新成功');
    } catch (err) {
      alert('资料更新失败');
    }
  };

  const handleSaveBio = async () => {
    if (!user) return;
    try {
      await userApi.updateUser(user.id, { bio: bioText });
      if (updateUser) {
        updateUser({ ...user, bio: bioText });
      }
      setEditForm(prev => ({ ...prev, bio: bioText }));
      setIsEditingBio(false);
      alert('个人简介更新成功');
    } catch (err) {
      alert('个人简介更新失败');
    }
  };

  const handleCancelBioEdit = () => {
    setBioText(user?.bio || '');
    setIsEditingBio(false);
  };

  const loadFollowers = async () => {
    if (!user) return;
    setListLoading(true);
    try {
      const data = await userApi.getFollowers(user.id);
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
    if (!user) return;
    setListLoading(true);
    try {
      const data = await userApi.getFollowing(user.id);
      setFollowing(data);
      setShowFollowing(true);
      setShowFollowers(false);
    } catch (err) {
      console.error('Failed to load following:', err);
    } finally {
      setListLoading(false);
    }
  };

  const loadUserProfile = async () => {
    if (!user) return;
    try {
      const profile = await userApi.getUserProfile(user.id, user.id);
      setFollowerCount(profile.followerCount || 0);
      setFollowingCount(profile.followingCount || 0);
    } catch (err) {
      console.error('Failed to load user profile:', err);
    }
  };

  const getAvatarUrl = (avatarUrl?: string) => {
    if (!avatarUrl) return null;
    if (avatarUrl.startsWith('http')) return avatarUrl;
    if (avatarUrl.startsWith('/')) return `http://localhost:8080${avatarUrl}`;
    return `http://localhost:8080/${avatarUrl}`;
  };

  const stats = [
    { label: '创建的计划', value: plans.length },
    { label: '完成的计划', value: plans.filter(p => p.status === 'COMPLETED').length },
    { label: '粉丝', value: followerCount },
    { label: '关注', value: followingCount },
  ];

  return (
    <div style={styles.container}>
      <div style={styles.headerSection}>
        <div style={styles.coverPhoto}></div>
        <div style={styles.profileInfo}>
          <div style={styles.avatarWrapper}>
            <div style={{
              ...styles.avatar,
              ...(getAvatarUrl(user?.avatarUrl) ? {
                backgroundImage: `url(${getAvatarUrl(user?.avatarUrl)})`,
                backgroundSize: 'cover',
                backgroundPosition: 'center',
              } : {})
            }}>
              {!getAvatarUrl(user?.avatarUrl) && (user?.username?.charAt(0).toUpperCase() || 'U')}
            </div>
            <button style={styles.editAvatarButton} onClick={handleEditAvatar} disabled={isUploading}>
              <Camera size={16} />
            </button>
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: 'none' }}
              accept="image/*"
              onChange={handleAvatarChange}
            />
          </div>

          <div style={styles.userDetails}>
            {isEditing ? (
              <div style={styles.editForm}>
                <input
                  type="text"
                  value={editForm.username}
                  onChange={(e) => setEditForm({ ...editForm, username: e.target.value })}
                  style={styles.editInput}
                  placeholder="用户名"
                />
                <input
                  type="text"
                  value={editForm.displayName}
                  onChange={(e) => setEditForm({ ...editForm, displayName: e.target.value })}
                  style={styles.editInputSmall}
                  placeholder="显示名称"
                />
              </div>
            ) : (
              <h1 style={styles.userName}>{user?.username || '用户名'}</h1>
            )}
            <p style={styles.userEmail}>{user?.displayName || user?.username || '用户'}</p>
            <div style={styles.userMeta}>
              <span style={styles.metaItem}>
                <Calendar size={14} />
                <span>{user?.bio || '欢迎来到 PlanHub'}</span>
              </span>
            </div>
          </div>

          <div style={styles.actionButtons}>
            {isEditing ? (
              <>
                <button style={styles.saveButton} onClick={handleSave}>
                  <Save size={16} />
                  <span>保存</span>
                </button>
                <button style={styles.cancelButton} onClick={() => setIsEditing(false)}>
                  <X size={16} />
                  <span>取消</span>
                </button>
              </>
            ) : (
              <>
                <button style={styles.aboutButton} onClick={() => setShowAboutModal(true)}>
                  <span>关于我</span>
                </button>
                <button style={styles.editButton} onClick={() => setIsEditing(true)}>
                  <Edit2 size={16} />
                  <span>编辑资料</span>
                </button>
                <button style={styles.chatButton} onClick={handleChat}>
                  <MessageSquare size={16} />
                  <span>消息</span>
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      <div style={styles.statsRow}>
        {stats.map((stat, index) => (
          <div 
            key={index} 
            style={{
              ...styles.statItem,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
            onClick={() => handleStatClick(stat.label)}
          >
            <span style={styles.statValue}>{stat.value}</span>
            <span style={styles.statLabel}>{stat.label}</span>
          </div>
        ))}
      </div>

      {/* 粉丝和关注列表 */}
      {showFollowers && (
        <div style={styles.listCard}>
          <div style={styles.listHeader}>
            <Users size={20} style={{ color: '#333333' }} />
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
              {followers.map((follower) => (
                <div 
                  key={follower.id} 
                  style={styles.listUserItem}
                  onClick={() => navigate(`/user/${follower.id}`)}
                >
                  <div style={{
                    ...styles.listUserAvatar,
                    ...(getAvatarUrl(follower.avatarUrl) ? {
                      backgroundImage: `url(${getAvatarUrl(follower.avatarUrl)})`,
                      backgroundSize: 'cover',
                      backgroundPosition: 'center',
                    } : {})
                  }}>
                    {!getAvatarUrl(follower.avatarUrl) && (follower.displayName?.charAt(0) || follower.username.charAt(0)).toUpperCase()}
                  </div>
                  <div style={styles.listUserInfo}>
                    <div style={styles.listUserName}>{follower.displayName || follower.username}</div>
                    <div style={styles.listUserUsername}>@{follower.username}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {showFollowing && (
        <div style={styles.listCard}>
          <div style={styles.listHeader}>
            <Users size={20} style={{ color: '#333333' }} />
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
              {following.map((followingUser) => (
                <div 
                  key={followingUser.id} 
                  style={styles.listUserItem}
                  onClick={() => navigate(`/user/${followingUser.id}`)}
                >
                  <div style={{
                    ...styles.listUserAvatar,
                    ...(getAvatarUrl(followingUser.avatarUrl) ? {
                      backgroundImage: `url(${getAvatarUrl(followingUser.avatarUrl)})`,
                      backgroundSize: 'cover',
                      backgroundPosition: 'center',
                    } : {})
                  }}>
                    {!getAvatarUrl(followingUser.avatarUrl) && (followingUser.displayName?.charAt(0) || followingUser.username.charAt(0)).toUpperCase()}
                  </div>
                  <div style={styles.listUserInfo}>
                    <div style={styles.listUserName}>{followingUser.displayName || followingUser.username}</div>
                    <div style={styles.listUserUsername}>@{followingUser.username}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div style={styles.contentSection}>
        <div style={styles.leftPanel}>
          <div style={styles.sectionCard}>
            <div style={styles.sectionHeader}>
              <h2 style={styles.sectionTitle}>我的点赞</h2>
              {likedContent.length > 3 && (
                <button style={styles.viewAllButton} onClick={() => setShowLikedModal(true)}>查看全部</button>
              )}
            </div>

            <div style={styles.postsList}>
              {likedLoading ? (
                <p style={styles.emptyText}>加载中...</p>
              ) : likedContent.length === 0 ? (
                <p style={styles.emptyText}>暂无点赞内容</p>
              ) : (
                likedContent.slice(0, 3).map((item) => (
                  <div 
                    key={`${item.type}-${item.id}`} 
                    style={styles.postItem}
                    onClick={() => handleLikedItemClick(item)}
                  >
                    <div style={styles.postIcon}>
                      {item.type === 'post' ? <FileText size={16} /> : <ClipboardList size={16} />}
                    </div>
                    <div style={styles.postInfo}>
                      <h4 style={styles.postTitle}>
                        {item.title && item.title.length > 35 ? item.title.substring(0, 35) + '...' : (item.title || '')}
                      </h4>
                      <span style={styles.postTime}>
                        {item.type === 'post' ? '帖子' : '计划'} · {item.createdAt ? new Date(item.createdAt).toLocaleDateString('zh-CN') : ''}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div style={styles.sectionCard}>
            <div style={styles.sectionHeader}>
              <h2 style={styles.sectionTitle}>我的帖子</h2>
              <button style={styles.viewAllButton} onClick={handleViewAllPosts}>查看全部</button>
            </div>

            <div style={styles.postsList}>
              {posts.length === 0 ? (
                <p style={styles.emptyText}>暂无帖子</p>
              ) : (
                posts.slice(0, 3).map((post: any) => (
                  <div 
                    key={post.id} 
                    style={styles.postItem}
                    onClick={() => handlePostClick(post.id)}
                  >
                    <div style={styles.postIcon}>
                      <MessageSquare size={16} />
                    </div>
                    <div style={styles.postInfo}>
                      <h4 style={styles.postTitle}>{post.content.length > 30 ? post.content.substring(0, 30) + '...' : post.content}</h4>
                      <span style={styles.postTime}>
                        {post.createdAt ? new Date(post.createdAt).toLocaleDateString('zh-CN') : ''}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        <div style={styles.rightPanel}>
          <div style={styles.sectionCard}>
            <h2 style={styles.sectionTitle}>账户安全</h2>
            <div style={styles.securityOptions}>
              <button style={styles.securityOption} onClick={handleChangePassword}>
                <Shield size={20} />
                <div style={styles.securityOptionContent}>
                  <span style={styles.securityOptionTitle}>修改密码</span>
                  <span style={styles.securityOptionDesc}>定期更新密码保护账户安全</span>
                </div>
              </button>
              <button style={styles.securityOption} onClick={handleNotifications}>
                <Bell size={20} />
                <div style={styles.securityOptionContent}>
                  <span style={styles.securityOptionTitle}>通知设置</span>
                  <span style={styles.securityOptionDesc}>管理通知偏好</span>
                </div>
              </button>
              <button style={styles.securityOption} onClick={handlePrivacySettings}>
                <Globe size={20} />
                <div style={styles.securityOptionContent}>
                  <span style={styles.securityOptionTitle}>隐私设置</span>
                  <span style={styles.securityOptionDesc}>控制个人信息可见性</span>
                </div>
              </button>
            </div>
          </div>

          <div style={styles.sectionCard}>
            <div style={styles.sectionHeader}>
              <h2 style={styles.sectionTitle}>活动记录</h2>
              <button style={styles.viewAllButton} onClick={() => navigate('/activities')}>查看全部</button>
            </div>
            <div style={styles.activityList}>
              {!Array.isArray(activities) || activities.length === 0 ? (
                <p style={styles.emptyText}>暂无活动记录</p>
              ) : (
                activities.slice(0, 2).map((activity) => (
                  <div 
                    key={activity.id} 
                    style={{
                      ...styles.activityItem,
                      background: hoveredActivityId === activity.id ? '#f8fafc' : 'transparent'
                    }}
                    onMouseEnter={() => setHoveredActivityId(activity.id)}
                    onMouseLeave={() => setHoveredActivityId(null)}
                    onClick={() => handleActivityClick(activity)}
                  >
                    <div style={styles.activityIcon}>
                      {activity.type === 'PLAN_CREATED' && <BookOpen size={16} />}
                      {activity.type === 'PLAN_COMPLETED' && <CheckCircle size={16} />}
                      {activity.type === 'PLAN_CHECKIN' && <Calendar size={16} />}
                      {activity.type === 'POST_LIKED' && <Heart size={16} />}
                      {activity.type === 'POST_COMMENTED' && <MessageCircle size={16} />}
                      {activity.type === 'COMMENT_LIKED' && <Heart size={16} />}
                      {activity.type === 'COMMENT_REPLIED' && <MessageCircle size={16} />}
                    </div>
                    <div style={styles.activityContent}>
                      <span style={styles.activityText}>{activity.displayText}</span>
                      <span style={styles.activityTime}>{activity.createdAt}</span>
                    </div>
                    <button 
                      style={{
                        ...styles.activityDeleteButton, 
                        opacity: hoveredActivityId === activity.id ? 1 : 0
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteActivity(activity.id).catch(err => console.error('删除活动失败:', err));
                      }}
                    >
                      <X size={14} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 隐私设置弹窗 */}
      {showPrivacySettings && (
        <div style={styles.modalOverlay}>
          <div style={styles.modal}>
            <div style={styles.modalHeader}>
              <h2 style={styles.modalTitle}>隐私设置</h2>
              <button
                style={styles.modalClose} onClick={() => setShowPrivacySettings(false)}>
                <X size={20} />
              </button>
            </div>
            <div style={styles.modalContent}>
              <div style={styles.settingItem}>
                <div style={styles.settingLabel}>
                  <span>显示活动记录</span>
                </div>
                <div style={styles.settingToggle}>
                  <button
                    style={{
                      ...styles.toggleButton,
                      ...(showActivities ? styles.toggleButtonActive : {}),
                    }}
                    onClick={() => setShowActivities(true)}
                  >
                    是
                  </button>
                  <button
                    style={{
                      ...styles.toggleButton,
                      ...(!showActivities ? styles.toggleButtonActive : {}),
                    }}
                    onClick={() => setShowActivities(false)}
                  >
                    否
                  </button>
                </div>
              </div>
              <div style={styles.settingItem}>
                <div style={styles.settingLabel}>
                  <span>显示粉丝列表</span>
                </div>
                <div style={styles.settingToggle}>
                  <button
                    style={{
                      ...styles.toggleButton,
                      ...(showFollowersList ? styles.toggleButtonActive : {}),
                    }}
                    onClick={() => setShowFollowersList(true)}
                  >
                    是
                  </button>
                  <button
                    style={{
                      ...styles.toggleButton,
                      ...(!showFollowersList ? styles.toggleButtonActive : {}),
                    }}
                    onClick={() => setShowFollowersList(false)}
                  >
                    否
                  </button>
                </div>
              </div>
              <div style={styles.settingItem}>
                <div style={styles.settingLabel}>
                  <span>显示关注列表</span>
                </div>
                <div style={styles.settingToggle}>
                  <button
                    style={{
                      ...styles.toggleButton,
                      ...(showFollowingList ? styles.toggleButtonActive : {}),
                    }}
                    onClick={() => setShowFollowingList(true)}
                  >
                    是
                  </button>
                  <button
                    style={{
                      ...styles.toggleButton,
                      ...(!showFollowingList ? styles.toggleButtonActive : {}),
                    }}
                    onClick={() => setShowFollowingList(false)}
                  >
                    否
                  </button>
                </div>
              </div>
              <div style={styles.settingItem}>
                <div style={styles.settingLabel}>
                  <span>显示点赞内容</span>
                </div>
                <div style={styles.settingToggle}>
                  <button
                    style={{
                      ...styles.toggleButton,
                      ...(showLikedContent ? styles.toggleButtonActive : {}),
                    }}
                    onClick={() => setShowLikedContent(true)}
                  >
                    是
                  </button>
                  <button
                    style={{
                      ...styles.toggleButton,
                      ...(!showLikedContent ? styles.toggleButtonActive : {}),
                    }}
                    onClick={() => setShowLikedContent(false)}
                  >
                    否
                  </button>
                </div>
              </div>
            </div>
            <div style={styles.modalActions}>
              <button
                style={styles.saveButton} onClick={handleSavePrivacySettings}>
                <Save size={16} />
                <span>保存</span>
              </button>
              <button
                style={styles.cancelButton} onClick={() => setShowPrivacySettings(false)}>
                <X size={16} />
                <span>取消</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 关于我弹窗 */}
      {showAboutModal && (
        <div style={styles.modalOverlay} onClick={() => setShowAboutModal(false)}>
          <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h2 style={styles.modalTitle}>关于我</h2>
              <button
                style={styles.modalClose} onClick={() => setShowAboutModal(false)}>
                <X size={20} />
              </button>
            </div>
            <div style={styles.modalContent}>
              {isEditingBio ? (
                <div style={styles.bioEditSection}>
                  <textarea
                    value={bioText}
                    onChange={(e) => setBioText(e.target.value)}
                    style={styles.bioTextarea}
                    placeholder="介绍一下自己..."
                    rows={6}
                    autoFocus
                  />
                  <div style={styles.bioEditActions}>
                    <button style={styles.bioSaveButton} onClick={handleSaveBio}>
                      <Save size={14} />
                      <span>保存</span>
                    </button>
                    <button style={styles.bioCancelButton} onClick={handleCancelBioEdit}>
                      <X size={14} />
                      <span>取消</span>
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <p style={styles.aboutText}>
                    {user?.bio || '暂无个人简介'}
                  </p>
                  <button style={styles.editBioButton} onClick={() => setIsEditingBio(true)}>
                    <Edit2 size={14} />
                    <span>编辑简介</span>
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 我的点赞弹窗 */}
      {showLikedModal && (
        <div style={styles.modalOverlay} onClick={() => setShowLikedModal(false)}>
          <div style={{...styles.modal, maxHeight: '70vh'}} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h2 style={styles.modalTitle}>我的点赞</h2>
              <button
                style={styles.modalClose} onClick={() => setShowLikedModal(false)}>
                <X size={20} />
              </button>
            </div>
            <div style={styles.modalContent}>
              {/* 筛选按钮 */}
              <div style={{display: 'flex', gap: '12px', marginBottom: '20px'}}>
                <button
                  style={{
                    ...styles.toggleButton,
                    ...(likedFilter === 'all' ? styles.toggleButtonActive : {})
                  }}
                  onClick={() => setLikedFilter('all')}
                >
                  全部
                </button>
                <button
                  style={{
                    ...styles.toggleButton,
                    ...(likedFilter === 'post' ? styles.toggleButtonActive : {})
                  }}
                  onClick={() => setLikedFilter('post')}
                >
                  帖子
                </button>
                <button
                  style={{
                    ...styles.toggleButton,
                    ...(likedFilter === 'plan' ? styles.toggleButtonActive : {})
                  }}
                  onClick={() => setLikedFilter('plan')}
                >
                  计划
                </button>
              </div>
              
              {/* 点赞内容列表 */}
              <div style={{maxHeight: '50vh', overflow: 'auto'}}>
                {likedLoading ? (
                  <p style={styles.emptyText}>加载中...</p>
                ) : likedContent.filter(item => likedFilter === 'all' || item.type === likedFilter).length === 0 ? (
                  <p style={styles.emptyText}>暂无点赞内容</p>
                ) : (
                  likedContent
                    .filter(item => likedFilter === 'all' || item.type === likedFilter)
                    .map((item) => (
                      <div
                        key={`${item.type}-${item.id}`}
                        style={styles.postItem}
                        onClick={() => {
                          handleLikedItemClick(item);
                          setShowLikedModal(false);
                        }}
                      >
                        <div style={styles.postIcon}>
                          {item.type === 'post' ? <FileText size={16} /> : <ClipboardList size={16} />}
                        </div>
                        <div style={styles.postInfo}>
                          <h4 style={styles.postTitle}>
                            {item.title && item.title.length > 50 ? item.title.substring(0, 50) + '...' : (item.title || '')}
                          </h4>
                          <span style={styles.postTime}>
                            {item.type === 'post' ? '帖子' : '计划'} · {item.createdAt ? new Date(item.createdAt).toLocaleDateString('zh-CN') : ''}
                          </span>
                        </div>
                      </div>
                    ))
                )}
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
    minHeight: '100%',
  },
  headerSection: {
    position: 'relative',
    marginBottom: '32px',
  },
  coverPhoto: {
    height: '200px',
    background: '#333333',
    borderRadius: '16px',
  },
  profileInfo: {
    display: 'flex',
    gap: '24px',
    marginTop: '-80px',
    position: 'relative',
    background: 'white',
    borderRadius: '16px',
    padding: '32px',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)',
    border: '1px solid #e2e8f0',
  },
  avatarWrapper: {
    position: 'relative',
  },
  avatar: {
    width: '120px',
    height: '120px',
    background: '#333333',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
    fontSize: '48px',
    fontWeight: 'bold',
    border: '4px solid white',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
  },
  editAvatarButton: {
    position: 'absolute',
    bottom: '8px',
    right: '8px',
    width: '36px',
    height: '36px',
    background: 'white',
    border: 'none',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#64748b',
    cursor: 'pointer',
    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
  },
  userDetails: {
    flex: 1,
  },
  editForm: {
    marginBottom: '8px',
  },
  editInput: {
    padding: '8px 12px',
    border: '1px solid #2563eb',
    borderRadius: '8px',
    fontSize: '24px',
    fontWeight: 'bold',
    color: '#0f172a',
    width: '300px',
    marginBottom: '8px',
  },
  editInputSmall: {
    padding: '8px 12px',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    fontSize: '16px',
    color: '#0f172a',
    width: '300px',
  },
  editTextarea: {
    width: '100%',
    padding: '12px',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    fontSize: '14px',
    color: '#0f172a',
    resize: 'vertical',
    fontFamily: 'inherit',
    background: '#f8fafc',
  },
  userName: {
    fontSize: '28px',
    fontWeight: 'bold',
    color: '#0f172a',
    marginBottom: '8px',
  },
  userEmail: {
    fontSize: '16px',
    color: '#64748b',
    marginBottom: '12px',
  },
  userMeta: {
    display: 'flex',
    gap: '24px',
  },
  metaItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '14px',
    color: '#64748b',
  },
  actionButtons: {
    display: 'flex',
    gap: '12px',
  },
  editButton: {
    padding: '12px 20px',
    background: 'transparent',
    color: '#374151',
    border: '1px solid #e2e8f0',
    borderRadius: '10px',
    fontSize: '15px',
    fontWeight: 'medium',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    transition: 'all 0.3s ease',
  },
  saveButton: {
    padding: '12px 20px',
    background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
    color: 'white',
    border: 'none',
    borderRadius: '10px',
    fontSize: '15px',
    fontWeight: 'medium',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    transition: 'all 0.3s ease',
  },
  cancelButton: {
    padding: '12px 20px',
    background: '#333333',
    color: 'white',
    border: 'none',
    borderRadius: '10px',
    fontSize: '15px',
    fontWeight: 'medium',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    transition: 'all 0.3s ease',
  },
  aboutButton: {
    padding: '12px 24px',
    background: 'transparent',
    color: '#374151',
    border: '1px solid #e2e8f0',
    borderRadius: '10px',
    fontSize: '15px',
    fontWeight: 'medium',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    transition: 'all 0.3s ease',
  },
  chatButton: {
    padding: '12px 24px',
    background: 'transparent',
    color: '#374151',
    border: '1px solid #e2e8f0',
    borderRadius: '10px',
    fontSize: '15px',
    fontWeight: 'medium',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    transition: 'all 0.3s ease',
  },
  statsRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '20px',
    marginBottom: '32px',
  },
  statItem: {
    background: 'white',
    borderRadius: '16px',
    padding: '24px',
    textAlign: 'center',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)',
    border: '1px solid #e2e8f0',
  },
  statValue: {
    display: 'block',
    fontSize: '32px',
    fontWeight: 'bold',
    color: '#0f172a',
    marginBottom: '8px',
  },
  statLabel: {
    fontSize: '14px',
    color: '#64748b',
  },
  contentSection: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gridTemplateRows: 'repeat(2, 1fr)',
    gap: '24px',
    alignItems: 'stretch',
  },
  leftPanel: {
    display: 'contents',
  },
  rightPanel: {
    display: 'contents',
  },
  sectionCard: {
    background: 'white',
    borderRadius: '16px',
    padding: '24px',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)',
    border: '1px solid #e2e8f0',
    display: 'flex',
    flexDirection: 'column',
  },
  sectionHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
  },
  sectionTitle: {
    fontSize: '20px',
    fontWeight: 'bold',
    color: '#0f172a',
    marginBottom: '20px',
  },
  editBioButton: {
    padding: '6px 12px',
    background: 'transparent',
    border: '1px solid #e2e8f0',
    borderRadius: '6px',
    color: '#374151',
    fontSize: '13px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    marginBottom: 0,
    transition: 'all 0.2s ease',
  },
  bioEditSection: {
    marginTop: '8px',
  },
  bioTextarea: {
    width: '100%',
    padding: '12px',
    border: '1px solid #2563eb',
    borderRadius: '8px',
    fontSize: '14px',
    color: '#0f172a',
    resize: 'vertical',
    fontFamily: 'inherit',
    background: '#f8fafc',
    marginBottom: '12px',
  },
  bioEditActions: {
    display: 'flex',
    gap: '12px',
    justifyContent: 'flex-end',
  },
  bioSaveButton: {
    padding: '8px 16px',
    background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '13px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  },
  bioCancelButton: {
    padding: '8px 16px',
    background: '#333333',
    color: '#64748b',
    border: 'none',
    borderRadius: '8px',
    fontSize: '13px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  },
  viewAllButton: {
    padding: '8px 16px',
    background: 'transparent',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    color: '#374151',
    fontSize: '14px',
    cursor: 'pointer',
    marginBottom: 0,
  },
  aboutText: {
    fontSize: '15px',
    color: '#64748b',
    lineHeight: '1.6',
  },
  emptyText: {
    fontSize: '14px',
    color: '#94a3b8',
    textAlign: 'center',
    padding: '20px 0',
  },
  securityOptions: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    flex: 1,
  },
  securityOption: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    padding: '16px',
    background: '#f8fafc',
    border: 'none',
    borderRadius: '12px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  securityOptionContent: {
    flex: 1,
    textAlign: 'left',
  },
  securityOptionTitle: {
    display: 'block',
    fontSize: '15px',
    fontWeight: 'bold',
    color: '#0f172a',
    marginBottom: '4px',
  },
  securityOptionDesc: {
    fontSize: '13px',
    color: '#64748b',
  },
  postsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    flex: 1,
  },
  activityList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    flex: 1,
  },
  postItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    padding: '16px',
    background: '#f8fafc',
    borderRadius: '12px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  postIcon: {
    width: '36px',
    height: '36px',
    background: '#e2e8f0',
    borderRadius: '8px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#475569',
  },
  postInfo: {
    flex: 1,
  },
  postTitle: {
    fontSize: '15px',
    fontWeight: 'bold',
    color: '#0f172a',
    marginBottom: '4px',
  },
  postTime: {
    fontSize: '13px',
    color: '#64748b',
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
  },
  modal: {
    background: 'white',
    borderRadius: '16px',
    padding: '24px',
    width: '100%',
    maxWidth: '500px',
    maxHeight: '90vh',
    overflow: 'auto',
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
  },
  modalTitle: {
    fontSize: '20px',
    fontWeight: 'bold',
    color: '#0f172a',
    margin: 0,
  },
  modalClose: {
    padding: '8px',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: '#64748b',
    borderRadius: '8px',
    transition: 'all 0.2s ease',
  },
  modalContent: {
    marginBottom: '24px',
  },
  settingItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px',
    background: '#f8fafc',
    borderRadius: '12px',
    marginBottom: '12px',
  },
  settingLabel: {
    fontSize: '15px',
    color: '#0f172a',
  },
  settingToggle: {
    display: 'flex',
    gap: '8px',
  },
  toggleButton: {
    padding: '8px 20px',
    background: 'transparent',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    color: '#374151',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  toggleButtonActive: {
    background: '#000000',
    borderColor: '#000000',
    color: '#ffffff',
  },
  modalActions: {
    display: 'flex',
    gap: '12px',
    justifyContent: 'flex-end',
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
  listUserItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '12px',
    background: '#f8fafc',
    borderRadius: '10px',
    cursor: 'pointer',
    transition: 'background 0.2s ease',
  },
  listUserAvatar: {
    width: '40px',
    height: '40px',
    background: '#333333',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
    fontSize: '16px',
    fontWeight: 'bold',
    flexShrink: 0,
  },
  listUserInfo: {
    flex: 1,
  },
  listUserName: {
    fontSize: '15px',
    fontWeight: 'medium',
    color: '#1e293b',
  },
  listUserUsername: {
    fontSize: '13px',
    color: '#64748b',
  },
};

export default Profile;
