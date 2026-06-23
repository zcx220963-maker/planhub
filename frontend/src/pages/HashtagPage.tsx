import React, { useState, useEffect } from 'react';
import { Heart, MessageCircle, Share2, Send, X, ArrowLeft, Trash2 } from 'lucide-react';
import { useParams, useNavigate } from 'react-router-dom';
import { postApi, commentApi } from '../services/api';
import type { Post, Comment } from '../types';
import EmojiPicker from '../components/EmojiPicker';
import { useAuth } from '../context/AuthContext';

interface CommentWithReplies extends Comment {
  replies?: CommentWithReplies[];
}

interface CommentItemProps {
  comment: CommentWithReplies;
  postId: number;
  postAuthorId: number;
  currentUserId: number;
  onLike: (commentId: number) => void;
  onReply: (commentId: number) => void;
  onDelete: (commentId: number) => void;
  onSubmitComment: () => void;
  isReplying: boolean;
  newComment: string;
  onCommentChange: (value: string) => void;
  navigate: (path: string) => void;
  getAvatarUrl: (avatarUrl?: string) => string | null;
  isNested?: boolean;
  replyingToCommentId: number | null;
}

const CommentItem: React.FC<CommentItemProps> = ({
  comment,
  postId,
  postAuthorId,
  currentUserId,
  onLike,
  onReply,
  onDelete,
  onSubmitComment,
  isReplying,
  newComment,
  onCommentChange,
  navigate,
  getAvatarUrl,
  isNested = false,
  replyingToCommentId,
}) => {
  const commentDisplayName = comment.user?.displayName || comment.user?.username || `用户${comment.userId}`;
  const commentAvatarUrl = getAvatarUrl(comment.user?.avatarUrl);
  const commentAvatarInitial = (comment.user?.displayName?.charAt(0) || comment.user?.username?.charAt(0) || 'U').toUpperCase();
  const hasReplies = comment.replies && comment.replies.length > 0;
  const canDelete = comment.userId === currentUserId || postAuthorId === currentUserId;

  const handleDelete = () => {
    if (window.confirm('确定要删除这条评论吗？')) {
      onDelete(comment.id);
    }
  };

  return (
    <div style={{ ...styles.commentItem, ...(isNested ? styles.nestedCommentItem : {}) }}>
      <div 
        style={{
          ...styles.userAvatarSmall,
          ...(commentAvatarUrl ? {
            backgroundImage: `url(${commentAvatarUrl})`,
            backgroundSize: 'cover',
            backgroundPosition: 'center',
          } : {})
        }}
        onClick={() => navigate(`/user/${comment.userId}`)}
      >
        {!commentAvatarUrl && commentAvatarInitial}
      </div>
      <div style={styles.commentContent}>
        <span style={styles.commentUserName} onClick={() => navigate(`/user/${comment.userId}`)}>{commentDisplayName}</span>
        <span style={styles.commentText}>{comment.content}</span>
        <span style={styles.commentTime}>
          {new Date(comment.createdAt).toLocaleString('zh-CN')}
        </span>
        <div style={styles.commentActions}>
          <button 
            style={{
              ...styles.commentActionButton,
              color: comment.liked ? '#ef4444' : '#64748b',
            }}
            onClick={() => onLike(comment.id)}
          >
            <Heart size={14} fill={comment.liked ? '#ef4444' : 'none'} />
            <span>{comment.likeCount || 0}</span>
          </button>
          <button 
            style={styles.commentActionButton}
            onClick={() => onReply(comment.id)}
          >
            <MessageCircle size={14} />
            <span>{comment.replyCount || 0}</span>
          </button>
          {canDelete && (
            <button
              style={{
                ...styles.commentActionButton,
                color: '#ef4444',
              }}
              onClick={handleDelete}
            >
              <Trash2 size={14} />
              <span>删除</span>
            </button>
          )}
        </div>
        
        {isReplying && (
          <div style={styles.replyInputWrapper}>
            <input
              type="text"
              placeholder={`回复 @${commentDisplayName}...`}
              style={styles.replyInput}
              value={newComment}
              onChange={(e) => onCommentChange(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  onSubmitComment();
                }
              }}
            />
            <button 
              style={styles.replySubmitButton}
              onClick={onSubmitComment}
            >
              <Send size={14} />
            </button>
          </div>
        )}
          
        {hasReplies && (
          <div style={styles.repliesContainer}>
            {comment.replies.map((reply) => (
              <CommentItem 
                key={reply.id}
                comment={reply}
                postId={postId}
                postAuthorId={postAuthorId}
                currentUserId={currentUserId}
                onLike={onLike}
                onReply={onReply}
                onDelete={onDelete}
                onSubmitComment={onSubmitComment}
                isReplying={replyingToCommentId === reply.id}
                newComment={newComment}
                onCommentChange={onCommentChange}
                navigate={navigate}
                getAvatarUrl={getAvatarUrl}
                isNested={true}
                replyingToCommentId={replyingToCommentId}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const HashtagPage: React.FC = () => {
  const { hashtag } = useParams<{ hashtag: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const currentUserId = user?.id || 0;
  const [posts, setPosts] = useState<Post[]>([]);
  const [comments, setComments] = useState<{ [key: number]: Comment[] }>({});
  const [newComment, setNewComment] = useState<{ [key: number]: string }>({});
  const [showComments, setShowComments] = useState<{ [key: number]: boolean }>({});
  const [replyingTo, setReplyingTo] = useState<{ [key: number]: number | null }>({});
  const [loading, setLoading] = useState(true);
  const [shareModal, setShareModal] = useState<{ postId: number; userId: number; content: string } | null>(null);
  const [shareContent, setShareContent] = useState('');

  useEffect(() => {
    loadPosts();
  }, [hashtag]);

  const loadPosts = () => {
    setLoading(true);
    if (!hashtag) {
      setPosts([]);
      setLoading(false);
      return;
    }
    postApi.getPostsByHashtag(hashtag)
      .then((data) => setPosts(data))
      .catch(() => setPosts([]))
      .finally(() => setLoading(false));
  };

  const toggleComments = async (postId: number) => {
    if (!comments[postId]) {
      const data = await commentApi.getCommentsByPostId(postId);
      console.log('Comments data:', data);
      console.log('Has parentCommentId:', data.some(c => c.parentCommentId !== undefined && c.parentCommentId !== null));
      setComments({ ...comments, [postId]: data });
    }
    setShowComments({ ...showComments, [postId]: !showComments[postId] });
  };

  const addEmojiToComment = (postId: number, emoji: string) => {
    setNewComment(prev => ({
      ...prev,
      [postId]: (prev[postId] || '') + emoji
    }));
  };

  const handleLike = async (postId: number) => {
    const post = posts.find(p => p.id === postId);
    if (!post) return;

    try {
      if (post.liked) {
        const result = await postApi.unlikePost(postId);
        setPosts(posts.map(p =>
          p.id === postId ? { ...p, likes: result.likes, liked: false } : p
        ));
      } else {
        const result = await postApi.likePost(postId);
        setPosts(posts.map(p =>
          p.id === postId ? { ...p, likes: result.likes, liked: true } : p
        ));
      }
    } catch (err) {
      alert('操作失败');
    }
  };

  const handleDeleteComment = async (postId: number, commentId: number) => {
    try {
      const result = await commentApi.deleteComment(commentId);
      const updatedComments = await commentApi.getCommentsByPostId(postId);
      setComments({
        ...comments,
        [postId]: updatedComments
      });
      setPosts(posts.map(post =>
        post.id === postId ? { ...post, commentsCount: Math.max(0, post.commentsCount - result.deletedCount) } : post
      ));
    } catch (err) {
      alert('删除评论失败');
    }
  };

  const handleCommentLike = async (postId: number, commentId: number) => {
    try {
      const comment = (comments[postId] || []).find(c => c.id === commentId);
      if (!comment) return;

      if (comment.liked) {
        const result = await commentApi.unlikeComment(commentId);
        setComments({
          ...comments,
          [postId]: (comments[postId] || []).map(c =>
            c.id === commentId ? { ...c, liked: false, likeCount: result.likes } : c
          )
        });
      } else {
        const result = await commentApi.likeComment(commentId);
        setComments({
          ...comments,
          [postId]: (comments[postId] || []).map(c =>
            c.id === commentId ? { ...c, liked: true, likeCount: result.likes } : c
          )
        });
      }
    } catch (err) {
      console.error('Failed to like comment:', err);
    }
  };

  const handleCreateComment = async (postId: number) => {
    const content = newComment[postId];
    if (!content?.trim()) return;
    try {
      const parentCommentId = replyingTo[postId] || undefined;
      await commentApi.createComment(postId, { content, parentCommentId });
      const updatedComments = await commentApi.getCommentsByPostId(postId);
      setComments({
        ...comments,
        [postId]: updatedComments
      });
      setPosts(posts.map(post =>
        post.id === postId ? { ...post, commentsCount: post.commentsCount + 1 } : post
      ));
      setNewComment({ ...newComment, [postId]: '' });
      setReplyingTo({ ...replyingTo, [postId]: null });
    } catch (err) {
      alert('评论失败');
    }
  };

  const handleShare = (postId: number, userId: number) => {
    setShareModal({ postId, userId, content: '' });
    setShareContent('');
  };

  const handleConfirmShare = async () => {
    if (!shareModal) return;
    try {
      await postApi.sharePost(shareModal.postId, shareModal.userId, shareContent);
      alert('分享成功！');
      setShareModal(null);
      setShareContent('');
      loadPosts();
    } catch (err) {
      alert('分享失败，请重试');
    }
  };

  const parseHashtags = (hashtags: string | undefined): string[] => {
    if (!hashtags) return [];
    try {
      return JSON.parse(hashtags);
    } catch {
      return [];
    }
  };

  const parseMediaUrls = (mediaUrls: string | undefined): string[] => {
    if (!mediaUrls) return [];
    try {
      return JSON.parse(mediaUrls);
    } catch {
      return [];
    }
  };

  const buildNestedComments = (commentsList: Comment[]): Comment[] => {
    const commentMap = new Map<number, Comment>();
    const nestedComments: Comment[] = [];
    const childCommentIds = new Set<number>();

    commentsList.forEach(comment => {
      commentMap.set(comment.id, { ...comment, replies: [] as Comment[] });
      if (comment.parentCommentId !== undefined && comment.parentCommentId !== null) {
        childCommentIds.add(comment.id);
      }
    });

    commentsList.forEach(comment => {
      if (comment.parentCommentId !== undefined && comment.parentCommentId !== null && commentMap.has(comment.parentCommentId)) {
        const parent = commentMap.get(comment.parentCommentId)!;
        parent.replies.push(commentMap.get(comment.id)!);
      }
    });

    commentsList.forEach(comment => {
      if (!childCommentIds.has(comment.id)) {
        nestedComments.push(commentMap.get(comment.id)!);
      }
    });

    return nestedComments;
  };

  const getAvatarUrl = (avatarUrl?: string) => {
    if (!avatarUrl) return null;
    if (avatarUrl.startsWith('http')) return avatarUrl;
    if (avatarUrl.startsWith('/')) return `http://localhost:8080${avatarUrl}`;
    return `http://localhost:8080/${avatarUrl}`;
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <button style={styles.backButton} onClick={() => navigate('/community')}>
          <ArrowLeft size={20} />
        </button>
        <div style={styles.headerContent}>
          <h1 style={styles.hashtagTitle}>#{hashtag}</h1>
          <p style={styles.postCount}>{posts.length} 条相关帖子</p>
        </div>
      </div>

      <div style={styles.content}>
        <div style={styles.postsContainer}>
          {loading ? (
            <div style={styles.loading}>加载中...</div>
          ) : posts.length === 0 ? (
            <div style={styles.emptyState}>
              <p>暂无 #{hashtag} 相关的帖子</p>
            </div>
          ) : (
            posts.map((post) => {
              const displayName = post.user?.displayName || post.user?.username || `用户${post.userId}`;
              const avatarUrl = getAvatarUrl(post.user?.avatarUrl);
              const avatarInitial = (post.user?.displayName?.charAt(0) || post.user?.username?.charAt(0) || 'U').toUpperCase();
              const postImages = parseMediaUrls(post.mediaUrls);
              const postHashtags = parseHashtags(post.hashtags);

              return (
                <div key={post.id} style={styles.postCard}>
                  <div style={styles.postHeader}>
                    <div 
                      style={{
                        ...styles.userAvatar,
                        ...(avatarUrl ? {
                          backgroundImage: `url(${avatarUrl})`,
                          backgroundSize: 'cover',
                          backgroundPosition: 'center',
                        } : {})
                      }} 
                      onClick={() => navigate(`/user/${post.userId}`)}
                    >
                      {!avatarUrl && avatarInitial}
                    </div>
                    <div style={styles.userInfo}>
                      <span style={styles.userName} onClick={() => navigate(`/user/${post.userId}`)}>{displayName}</span>
                      <span style={styles.postTime}>{new Date(post.createdAt).toLocaleString('zh-CN')}</span>
                    </div>
                  </div>

                  <p style={styles.postContent}>{post.content}</p>
                  
                  {postImages.length > 0 && (
                    <div style={styles.postImagesContainer}>
                      {postImages.map((url, index) => (
                        <img
                          key={index}
                          src={url}
                          style={styles.postImage}
                          alt={`图片 ${index + 1}`}
                        />
                      ))}
                    </div>
                  )}

                  {postHashtags.length > 0 && (
                    <div style={styles.hashtagsContainer}>
                      {postHashtags.map((tag, index) => (
                        <span key={index} style={styles.hashtag} onClick={() => navigate(`/hashtag/${tag}`)}>
                          #{tag}
                        </span>
                      ))}
                    </div>
                  )}

                  <div style={styles.postStats}>
                    <span style={styles.statItem}>{post.likes} 点赞</span>
                    <span style={styles.statItem}>{post.commentsCount} 评论</span>
                  </div>

                  <div style={styles.postActionsBar}>
                    <button
                      style={{ ...styles.actionButton, color: post.liked ? '#ef4444' : '#64748b' }}
                      onClick={() => handleLike(post.id)}
                    >
                      <Heart size={18} fill={post.liked ? '#ef4444' : 'none'} />
                      <span>{post.liked ? '已点赞' : '点赞'} ({post.likes || 0})</span>
                    </button>
                    <button style={styles.actionButton} onClick={() => toggleComments(post.id)}>
                      <MessageCircle size={18} />
                      <span>评论 ({post.commentsCount || 0})</span>
                    </button>
                    <button style={styles.actionButton} onClick={() => handleShare(post.id, post.userId)}>
                      <Share2 size={18} />
                      <span>分享</span>
                    </button>
                  </div>

                  {showComments[post.id] && (
                    <div style={styles.commentsSection}>
                      <div style={styles.commentInputWrapper}>
                        <EmojiPicker onEmojiSelect={(emoji) => addEmojiToComment(post.id, emoji)} />
                        <input
                          type="text"
                          placeholder="写下你的评论..."
                          value={newComment[post.id] || ''}
                          onChange={(e) => setNewComment({ ...newComment, [post.id]: e.target.value })}
                          style={styles.commentInput}
                          onKeyPress={(e) => e.key === 'Enter' && handleCreateComment(post.id)}
                        />
                        <button style={styles.commentSubmitButton} onClick={() => handleCreateComment(post.id)}>
                          <Send size={16} />
                        </button>
                      </div>
                      
                      {comments[post.id] && comments[post.id].length > 0 ? (
                        buildNestedComments(comments[post.id]).map((comment) => (
                          <CommentItem 
                            key={comment.id} 
                            comment={comment} 
                            postId={post.id}
                            postAuthorId={post.userId}
                            currentUserId={currentUserId}
                            onLike={(commentId) => handleCommentLike(post.id, commentId)}
                            onReply={(commentId) => {
                              const commentDisplayName = comment.user?.displayName || comment.user?.username || `用户${comment.userId}`;
                              setNewComment(prev => ({ ...prev, [post.id]: `@${commentDisplayName} ` }));
                              setReplyingTo({ ...replyingTo, [post.id]: commentId });
                            }}
                            onDelete={(commentId) => handleDeleteComment(post.id, commentId)}
                            onSubmitComment={() => handleCreateComment(post.id)}
                            isReplying={replyingTo[post.id] === comment.id}
                            newComment={newComment[post.id] || ''}
                            onCommentChange={(value) => setNewComment({ ...newComment, [post.id]: value })}
                            navigate={navigate}
                            getAvatarUrl={getAvatarUrl}
                            replyingToCommentId={replyingTo[post.id] || null}
                          />
                        ))
                      ) : (
                        <p style={styles.noComments}>暂无评论，快来抢沙发吧！</p>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {shareModal && (
        <div style={styles.modalOverlay} onClick={() => setShareModal(null)}>
          <div style={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h3 style={styles.modalTitle}>分享到社区</h3>
              <button style={styles.closeButton} onClick={() => setShareModal(null)}>
                <X size={20} />
              </button>
            </div>
            <textarea
              style={styles.shareTextarea}
              placeholder="说点什么..."
              value={shareContent}
              onChange={(e) => setShareContent(e.target.value)}
              rows={4}
            />
            <div style={styles.modalActions}>
              <button style={styles.cancelButton} onClick={() => setShareModal(null)}>
                取消
              </button>
              <button style={styles.confirmButton} onClick={handleConfirmShare}>
                分享
              </button>
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
    background: '#f1f5f9',
  },
  header: {
    background: 'white',
    padding: '16px 24px',
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.05)',
    position: 'sticky',
    top: 0,
    zIndex: 100,
  },
  backButton: {
    background: '#f1f5f9',
    border: 'none',
    borderRadius: '8px',
    padding: '8px',
    cursor: 'pointer',
    color: '#334155',
  },
  headerContent: {
    display: 'flex',
    flexDirection: 'column',
  },
  hashtagTitle: {
    fontSize: '20px',
    fontWeight: 'bold',
    color: '#0f172a',
    margin: 0,
  },
  postCount: {
    fontSize: '14px',
    color: '#64748b',
    margin: 4,
  },
  content: {
    padding: '24px',
    maxWidth: '800px',
    margin: '0 auto',
  },
  postsContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '24px',
  },
  postCard: {
    background: 'white',
    borderRadius: '16px',
    padding: '24px',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)',
    border: '1px solid #e2e8f0',
  },
  postHeader: {
    display: 'flex',
    gap: '16px',
    alignItems: 'flex-start',
  },
  userAvatar: {
    width: '48px',
    height: '48px',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
    fontWeight: 'bold',
    fontSize: '18px',
    flexShrink: 0,
  },
  userAvatarSmall: {
    width: '32px',
    height: '32px',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
    fontWeight: 'bold',
    fontSize: '12px',
    flexShrink: 0,
  },
  userInfo: {
    display: 'flex',
    flexDirection: 'column',
    flex: 1,
  },
  userName: {
    fontSize: '15px',
    fontWeight: 'bold',
    color: '#0f172a',
  },
  postTime: {
    fontSize: '13px',
    color: '#64748b',
  },
  postContent: {
    fontSize: '16px',
    color: '#0f172a',
    lineHeight: '1.6',
    margin: '16px 0',
  },
  postImagesContainer: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '12px',
    marginBottom: '16px',
  },
  postImage: {
    maxWidth: '100%',
    maxHeight: '300px',
    borderRadius: '8px',
    objectFit: 'cover',
  },
  hashtagsContainer: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
    marginBottom: '16px',
  },
  hashtag: {
    padding: '6px 12px',
    background: '#e0f2fe',
    color: '#0369a1',
    borderRadius: '20px',
    fontSize: '14px',
    cursor: 'pointer',
  },
  postStats: {
    display: 'flex',
    gap: '20px',
    marginBottom: '12px',
  },
  statItem: {
    fontSize: '14px',
    color: '#64748b',
  },
  postActionsBar: {
    display: 'flex',
    gap: '24px',
    paddingTop: '16px',
    borderTop: '1px solid #e2e8f0',
  },
  actionButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    color: '#64748b',
    background: 'transparent',
    border: 'none',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    padding: '8px 0',
  },
  commentsSection: {
    marginTop: '20px',
    paddingTop: '20px',
    borderTop: '1px solid #e2e8f0',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  commentInputWrapper: {
    display: 'flex',
    gap: '12px',
    alignItems: 'center',
  },
  commentInput: {
    flex: 1,
    padding: '10px 16px',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    fontSize: '14px',
    background: '#f8fafc',
  },
  commentSubmitButton: {
    padding: '10px 16px',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    border: 'none',
    borderRadius: '8px',
    color: 'white',
    cursor: 'pointer',
  },
  commentItem: {
    display: 'flex',
    gap: '12px',
  },
  commentContent: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  commentUserName: {
    fontSize: '14px',
    fontWeight: 'bold',
    color: '#0f172a',
  },
  commentText: {
    fontSize: '14px',
    color: '#475569',
  },
  commentTime: {
    fontSize: '12px',
    color: '#94a3b8',
  },
  commentActions: {
    display: 'flex',
    gap: '16px',
    marginTop: '8px',
  },
  commentActionButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    background: 'none',
    border: 'none',
    fontSize: '12px',
    color: '#64748b',
    cursor: 'pointer',
    padding: '4px 8px',
    borderRadius: '4px',
    transition: 'all 0.2s ease',
  },
  replyInputWrapper: {
    display: 'flex',
    gap: '8px',
    marginTop: '12px',
    paddingLeft: '40px',
  },
  replyInput: {
    flex: 1,
    padding: '8px 12px',
    border: '1px solid #e2e8f0',
    borderRadius: '20px',
    fontSize: '13px',
    background: '#f8fafc',
  },
  replySubmitButton: {
    padding: '8px 12px',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    border: 'none',
    borderRadius: '20px',
    color: 'white',
    cursor: 'pointer',
  },
  nestedCommentItem: {
    paddingLeft: '40px',
  },
  repliesContainer: {
    marginTop: '12px',
    paddingLeft: '20px',
    borderLeft: '2px solid #e2e8f0',
  },

  noComments: {
    textAlign: 'center',
    color: '#94a3b8',
    fontSize: '14px',
    padding: '16px 0',
  },
  loading: {
    textAlign: 'center',
    padding: '40px',
    color: '#64748b',
  },
  emptyState: {
    textAlign: 'center',
    padding: '40px',
    background: 'white',
    borderRadius: '16px',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)',
    border: '1px solid #e2e8f0',
    color: '#64748b',
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
  },
  modalContent: {
    background: 'white',
    borderRadius: '16px',
    padding: '24px',
    width: '90%',
    maxWidth: '500px',
    boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
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
  closeButton: {
    background: 'transparent',
    border: 'none',
    color: '#64748b',
    cursor: 'pointer',
    padding: '4px',
    borderRadius: '4px',
  },
  shareTextarea: {
    width: '100%',
    padding: '12px',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    fontSize: '15px',
    resize: 'none',
    fontFamily: 'inherit',
    marginBottom: '16px',
  },
  modalActions: {
    display: 'flex',
    gap: '12px',
    justifyContent: 'flex-end',
  },
  cancelButton: {
    padding: '10px 20px',
    background: '#f1f5f9',
    border: 'none',
    borderRadius: '8px',
    color: '#64748b',
    fontSize: '14px',
    cursor: 'pointer',
  },
  confirmButton: {
    padding: '10px 20px',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    border: 'none',
    borderRadius: '8px',
    color: 'white',
    fontSize: '14px',
    cursor: 'pointer',
  },
};

export default HashtagPage;
