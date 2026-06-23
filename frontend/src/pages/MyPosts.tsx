import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { MessageSquare, Heart, Calendar, Search, Clock, Flame, Share2 } from 'lucide-react';
import { postApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import type { Post } from '../types';

const getAvatarUrl = (avatarUrl?: string) => {
  if (!avatarUrl) return null;
  if (avatarUrl.startsWith('http')) return avatarUrl;
  if (avatarUrl.startsWith('/')) return `http://localhost:8080${avatarUrl}`;
  return `http://localhost:8080/${avatarUrl}`;
};

const MyPosts: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<'time' | 'hot'>('time');

  useEffect(() => {
    loadPosts();
  }, [sortBy]);

  const loadPosts = () => {
    setLoading(true);
    if (user?.id) {
      postApi.getUserPosts(user.id, sortBy)
        .then((data) => {
          setPosts(data);
        })
        .catch(() => setPosts([]))
        .finally(() => setLoading(false));
    } else {
      setPosts([]);
      setLoading(false);
    }
  };

  const filteredPosts = posts.filter((post: any) => {
    const matchesSearch = searchTerm === '' || 
      post.content.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (post.hashtags && post.hashtags.toLowerCase().includes(searchTerm.toLowerCase()));
    return matchesSearch;
  });

  const handlePostClick = (postId: number) => {
    navigate(`/post/${postId}`);
  };

  const getHashtags = (hashtags: string | undefined) => {
    if (!hashtags) return [];
    try {
      if (typeof hashtags === 'string') {
        if (hashtags.startsWith('[')) {
          return JSON.parse(hashtags);
        }
        return hashtags.split(',').map((t: string) => t.trim());
      }
      return hashtags;
    } catch {
      return [];
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>我的帖子</h1>
          <p style={styles.subtitle}>管理和查看您发布的所有帖子</p>
        </div>
      </div>

      <div style={styles.toolbar}>
        <div style={styles.searchWrapper}>
          <Search size={18} style={styles.searchIcon} />
          <input
            type="text"
            placeholder="搜索帖子内容..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={styles.searchInput}
          />
        </div>
        <div style={styles.sortWrapper}>
          <button
            style={{
              ...styles.sortButton,
              ...(sortBy === 'time' ? styles.sortButtonActive : {}),
            }}
            onClick={() => setSortBy('time')}
          >
            <Clock size={16} />
            <span>最新发布</span>
          </button>
          <button
            style={{
              ...styles.sortButton,
              ...(sortBy === 'hot' ? styles.sortButtonActive : {}),
            }}
            onClick={() => setSortBy('hot')}
          >
            <Flame size={16} />
            <span>热度最高</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div style={styles.loading}>加载中...</div>
      ) : (
        <div style={styles.postsList}>
          {filteredPosts.map((post: any) => (
            <div 
              key={post.id} 
              style={styles.postCard}
              onClick={() => handlePostClick(post.id)}
            >
              <div style={styles.postHeader}>
                <div style={styles.postIcon}>
                  <MessageSquare size={20} />
                </div>
                <div style={styles.postMeta}>
                  <span style={styles.postContent}>
                    {post.content.length > 100 ? post.content.substring(0, 100) + '...' : post.content}
                  </span>
                  <span style={styles.postDate}>
                    {post.createdAt ? new Date(post.createdAt).toLocaleDateString('zh-CN') : ''}
                  </span>
                </div>
              </div>

              {post.hashtags && getHashtags(post.hashtags).length > 0 && (
                <div style={styles.hashtags}>
                  {getHashtags(post.hashtags).slice(0, 5).map((tag: string, index: number) => (
                    <span key={index} style={styles.hashtag}>
                      #{tag}
                    </span>
                  ))}
                </div>
              )}

              {post.originalPost && (
                <div style={styles.repostContainer} onClick={(e) => {
                  e.stopPropagation();
                  navigate(`/post/${post.originalPost.id}`);
                }}>
                  <div style={styles.repostLabel}>
                    <Share2 size={14} />
                    <span>转发自 {post.originalAuthor?.displayName || post.originalAuthor?.username || '用户' + post.originalAuthorId}</span>
                  </div>
                  <div style={styles.originalPost}>
                    {post.originalPost.user && (
                      <div style={styles.originalPostHeader}>
                        <div 
                          style={{
                            ...styles.originalPostAvatar,
                            ...(post.originalPost.user.avatarUrl ? {
                              backgroundImage: `url(${getAvatarUrl(post.originalPost.user.avatarUrl)})`,
                              backgroundSize: 'cover',
                              backgroundPosition: 'center',
                            } : {})
                          }}
                        >
                          {!post.originalPost.user.avatarUrl && (post.originalPost.user.displayName?.charAt(0) || post.originalPost.user.username?.charAt(0) || 'U').toUpperCase()}
                        </div>
                        <div style={styles.originalPostUserInfo}>
                          <span style={styles.originalPostUserName}>{post.originalPost.user.displayName || post.originalPost.user.username}</span>
                          <span style={styles.originalPostTime}>{new Date(post.originalPost.createdAt).toLocaleString('zh-CN')}</span>
                        </div>
                      </div>
                    )}
                    <p style={styles.originalPostContent}>{post.originalPost.content}</p>
                    {post.originalPost.mediaUrls && JSON.parse(post.originalPost.mediaUrls).length > 0 && (
                      <div style={styles.originalPostImages}>
                        {JSON.parse(post.originalPost.mediaUrls).map((url: string, index: number) => (
                          <img key={index} src={url} style={styles.originalPostImage} alt={`原帖图片 ${index + 1}`} />
                        ))}
                      </div>
                    )}
                    <div style={styles.originalPostStats}>
                      <span>{post.originalPost.likes} 点赞</span>
                      <span>{post.originalPost.commentsCount} 评论</span>
                    </div>
                  </div>
                </div>
              )}

              <div style={styles.postStats}>
                <span style={styles.stat}>
                  <Heart size={16} />
                  {post.likes || 0} 点赞
                </span>
                <span style={styles.stat}>
                  <Calendar size={16} />
                  {post.commentsCount || 0} 评论
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && filteredPosts.length === 0 && (
        <div style={styles.emptyState}>
          <MessageSquare size={48} style={{ color: '#cbd5e1' }} />
          <h3 style={styles.emptyTitle}>暂无帖子</h3>
          <p style={styles.emptyDescription}>您还没有发布任何帖子</p>
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
    maxWidth: '1200px',
    margin: '0 auto 30px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  title: {
    fontSize: '32px',
    fontWeight: '700',
    color: '#000000',
    margin: '0 0 8px',
  },
  subtitle: {
    fontSize: '16px',
    color: '#64748b',
    margin: 0,
  },
  toolbar: {
    maxWidth: '1200px',
    margin: '0 auto 20px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '20px',
    flexWrap: 'wrap',
  },
  sortWrapper: {
    display: 'flex',
    gap: '12px',
    alignItems: 'center',
  },
  sortButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 20px',
    background: '#f1f5f9',
    border: '1px solid #e2e8f0',
    borderRadius: '10px',
    color: '#64748b',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  sortButtonActive: {
    background: '#000000',
    borderColor: '#000000',
    color: '#ffffff',
    fontWeight: '600',
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
  postsList: {
    maxWidth: '1200px',
    margin: '0 auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  postCard: {
    background: 'white',
    borderRadius: '16px',
    padding: '24px',
    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.1)',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  postHeader: {
    display: 'flex',
    gap: '16px',
    marginBottom: '16px',
  },
  postIcon: {
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
  postMeta: {
    flex: 1,
  },
  postContent: {
    display: 'block',
    fontSize: '15px',
    color: '#0f172a',
    lineHeight: '1.6',
    marginBottom: '8px',
  },
  postDate: {
    fontSize: '13px',
    color: '#64748b',
  },
  hashtags: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
    marginBottom: '16px',
  },
  hashtag: {
    padding: '4px 12px',
    background: '#f1f5f9',
    borderRadius: '20px',
    fontSize: '13px',
    color: '#475569',
    fontWeight: '500',
  },
  postStats: {
    display: 'flex',
    gap: '24px',
    paddingTop: '12px',
    borderTop: '1px solid #e2e8f0',
  },
  stat: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '14px',
    color: '#64748b',
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
  repostContainer: {
    margin: '16px 0',
    border: '1px solid #e2e8f0',
    borderRadius: '12px',
    overflow: 'hidden',
    cursor: 'pointer',
    backgroundColor: '#f8fafc',
  },
  repostLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 12px',
    background: '#f1f5f9',
    color: '#64748b',
    fontSize: '13px',
    fontWeight: '500',
  },
  originalPost: {
    padding: '12px',
  },
  originalPostHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    marginBottom: '10px',
  },
  originalPostAvatar: {
    width: '32px',
    height: '32px',
    background: '#e2e8f0',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#475569',
    fontSize: '14px',
    fontWeight: 'bold',
    flexShrink: 0,
  },
  originalPostUserInfo: {
    flex: 1,
  },
  originalPostUserName: {
    display: 'block',
    fontSize: '14px',
    fontWeight: '600',
    color: '#0f172a',
  },
  originalPostTime: {
    fontSize: '12px',
    color: '#64748b',
  },
  originalPostContent: {
    fontSize: '14px',
    color: '#334155',
    lineHeight: '1.5',
    marginBottom: '12px',
    wordBreak: 'break-word',
  },
  originalPostImages: {
    display: 'flex',
    gap: '8px',
    marginBottom: '12px',
    flexWrap: 'wrap',
  },
  originalPostImage: {
    width: '100px',
    height: '100px',
    objectFit: 'cover',
    borderRadius: '8px',
  },
  originalPostStats: {
    display: 'flex',
    gap: '16px',
    fontSize: '12px',
    color: '#64748b',
    paddingTop: '8px',
    borderTop: '1px solid #e2e8f0',
  },
};

export default MyPosts;
