import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Heart, MessageCircle, Share2, Send, Image, X, Flame, Clock, Calendar, Users } from 'lucide-react';
import { postApi, commentApi, chatApi, getImageUrl } from '../services/api';
import { useAuth } from '../context/AuthContext';
import type { Post, Comment, ChatConversation } from '../types';
import EmojiPicker from '../components/EmojiPicker';
import CommentItem from '../components/CommentItem';
import type { CommentWithReplies } from '../components/CommentItem';

const PostDetail: React.FC = () => {
  const { postId } = useParams<{ postId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const currentUserId = user?.id || 0;
  const [post, setPost] = useState<Post | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [showComments, setShowComments] = useState(true);
  const [newComment, setNewComment] = useState('');
  const [selectedCommentImages, setSelectedCommentImages] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [shareContent, setShareContent] = useState('');
  const [showShareModal, setShowShareModal] = useState(false);
  const [shareMode, setShareMode] = useState<'community' | 'chat'>('community');
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [selectedReceiver, setSelectedReceiver] = useState<number | null>(null);
  const [loadingConversations, setLoadingConversations] = useState(false);
  const [replyingTo, setReplyingTo] = useState<{ commentId: number; userName: string } | null>(null);
  const errorShownRef = useRef(false);
  const fetchingRef = useRef(false);
  const commentFileInputRef = useRef<HTMLInputElement>(null);

  const buildNestedComments = (commentsList: Comment[]): CommentWithReplies[] => {
    const commentMap = new Map<number, CommentWithReplies>();
    const nestedComments: CommentWithReplies[] = [];
    const childCommentIds = new Set<number>();

    commentsList.forEach(comment => {
      commentMap.set(comment.id, { ...comment, replies: [] });
      if (comment.parentCommentId !== undefined && comment.parentCommentId !== null) {
        childCommentIds.add(comment.id);
      }
    });

    commentsList.forEach(comment => {
      if (comment.parentCommentId !== undefined && comment.parentCommentId !== null && commentMap.has(comment.parentCommentId)) {
        const parent = commentMap.get(comment.parentCommentId)!;
        parent.replies!.push(commentMap.get(comment.id)!);
      }
    });

    commentsList.forEach(comment => {
      if (!childCommentIds.has(comment.id)) {
        nestedComments.push(commentMap.get(comment.id)!);
      }
    });

    return nestedComments;
  };

  const loadPostDetail = useCallback(async (id: number) => {
    if (fetchingRef.current) {
      console.log('Already fetching post detail, skipping...');
      return;
    }
    
    fetchingRef.current = true;
    setLoading(true);
    try {
      console.log('Loading post detail for id:', id);
      const postData = await postApi.getPostById(id);
      console.log('Post data loaded:', postData);
      setPost(postData);
      
      try {
        const commentData = await commentApi.getCommentsByPostId(id);
        console.log('Comment data loaded:', commentData);
        setComments(commentData);
      } catch (commentError) {
        console.warn('Failed to load comments, showing post anyway:', commentError);
        setComments([]);
      }
      
      errorShownRef.current = false;
    } catch (error) {
      console.error('Failed to load post detail:', error);
      if (!errorShownRef.current) {
        errorShownRef.current = true;
        alert(`加载帖子失败: ${error instanceof Error ? error.message : '未知错误'}`);
      }
    } finally {
      setLoading(false);
      fetchingRef.current = false;
    }
  }, []);

  useEffect(() => {
    if (postId) {
      setPost(null);
      setComments([]);
      errorShownRef.current = false;
      loadPostDetail(parseInt(postId));
    }
  }, [postId, loadPostDetail]);

  const parseMediaUrls = (mediaUrls: string | undefined): string[] => {
    if (!mediaUrls) return [];
    try {
      return JSON.parse(mediaUrls);
    } catch {
      return [];
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

  const handleLike = async () => {
    if (!post) return;
    try {
      if (post.liked) {
        const result = await postApi.unlikePost(post.id);
        setPost({ ...post, likes: result.likes, liked: false });
      } else {
        const result = await postApi.likePost(post.id);
        setPost({ ...post, likes: result.likes, liked: true });
      }
    } catch (err) {
      alert('操作失败');
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
    setShowShareModal(true);
    setShareMode('community');
    setSelectedReceiver(null);
    if (user) {
      await loadConversations();
    }
  };

  const handleConfirmShare = async () => {
    if (!post || !user) return;
    try {
      if (shareMode === 'community') {
        const sharedPost = await postApi.sharePost(post.id, post.userId, shareContent);
        alert('分享成功！');
        setShowShareModal(false);
        setShareContent('');
        navigate('/community');
      } else if (shareMode === 'chat' && selectedReceiver) {
        await chatApi.sharePostToChat(selectedReceiver, post.id, shareContent);
        alert('分享成功！');
        setShowShareModal(false);
        setShareContent('');
        setSelectedReceiver(null);
      }
    } catch (err) {
      alert('分享失败，请重试');
    }
  };

  const handleCommentImageSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      setUploading(true);
      try {
        const imageUrl = await postApi.uploadImage(files[0]);
        setSelectedCommentImages(prev => [...prev, imageUrl]);
      } catch (err) {
        alert('图片上传失败');
        console.error(err);
      } finally {
        setUploading(false);
      }
    }
  };

  const removeCommentImage = (index: number) => {
    setSelectedCommentImages(prev => prev.filter((_, i) => i !== index));
  };

  const handleCommentLike = async (commentId: number) => {
    try {
      const comment = comments.find(c => c.id === commentId);
      if (!comment) return;

      if (comment.liked) {
        const result = await commentApi.unlikeComment(commentId);
        setComments(comments.map(c => 
          c.id === commentId ? { ...c, liked: false, likeCount: result.likes } : c
        ));
      } else {
        const result = await commentApi.likeComment(commentId);
        setComments(comments.map(c => 
          c.id === commentId ? { ...c, liked: true, likeCount: result.likes } : c
        ));
      }
    } catch (err) {
      console.error('Failed to like comment:', err);
    }
  };

  const handleDeleteComment = async (commentId: number) => {
    try {
      const result = await commentApi.deleteComment(commentId);
      const updatedComments = await commentApi.getCommentsByPostId(post?.id || 0);
      setComments(updatedComments);
      setPost(prev => prev ? { ...prev, commentsCount: Math.max(0, prev.commentsCount - result.deletedCount) } : null);
    } catch (err) {
      alert('删除评论失败');
    }
  };

  const getAvatarUrl = (avatarUrl?: string) => {
    if (!avatarUrl) return null;
    if (avatarUrl.startsWith('http')) return avatarUrl;
    if (avatarUrl.startsWith('/')) return `http://localhost:8080${avatarUrl}`;
    return `http://localhost:8080/${avatarUrl}`;
  };

  const addEmojiToComment = (emoji: string) => {
    setNewComment(prev => prev + emoji);
  };

  const handleCreateComment = async () => {
    if (!post) return;
    if (!newComment.trim() && selectedCommentImages.length === 0) return;
    try {
      const parentCommentId = replyingTo?.commentId || undefined;
      const comment = await commentApi.createComment(post.id, {
        content: newComment,
        mediaUrls: selectedCommentImages.length > 0 ? selectedCommentImages : undefined,
        parentCommentId
      });
      
      const updatedComments = await commentApi.getCommentsByPostId(post.id);
      setComments(updatedComments);
      setPost(prev => prev ? { ...prev, commentsCount: prev.commentsCount + 1 } : null);
      setNewComment('');
      setSelectedCommentImages([]);
      setReplyingTo(null);
    } catch (err) {
      alert('评论失败');
    }
  };

  const handleReply = (commentId: number, userName: string) => {
    if (replyingTo?.commentId === commentId) {
      setReplyingTo(null);
      setNewComment('');
    } else {
      setReplyingTo({ commentId, userName });
      setNewComment(`@${userName} `);
    }
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

  if (!post) {
    return (
      <div style={styles.container}>
        <div style={styles.errorContainer}>
          <p style={styles.errorText}>帖子不存在</p>
          <button style={styles.backButton} onClick={() => navigate('/community')}>
            <ArrowLeft size={18} />
            <span>返回</span>
          </button>
        </div>
      </div>
    );
  }

  const displayName = post.user?.displayName || post.user?.username || `用户${post.userId}`;
  const avatarUrl = getAvatarUrl(post.user?.avatarUrl);
  const postImages = parseMediaUrls(post.mediaUrls);
  const postHashtags = parseHashtags(post.hashtags);
  const nestedComments = buildNestedComments(comments);

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <button style={styles.backButton} onClick={() => navigate(-1)}>
          <ArrowLeft size={20} />
          <span>返回</span>
        </button>
      </div>

      <div style={styles.postCard}>
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
            {!avatarUrl && (post.user?.displayName?.charAt(0) || post.user?.username?.charAt(0) || 'U').toUpperCase()}
          </div>
          <div style={styles.userInfo}>
            <span 
              style={styles.userName} 
              onClick={() => navigate(`/user/${post.userId}`)}
            >
              {displayName}
            </span>
            <span style={styles.postTime}>{new Date(post.createdAt).toLocaleString('zh-CN')}</span>
          </div>
        </div>

        <p style={styles.postContent}>{post.content}</p>
        
        {post.linkedPlan && (
          <div style={styles.linkedPlanContainer} onClick={() => navigate(`/plan/${post.linkedPlan.id}`)}>
            <div style={styles.linkedPlanLabel}>
              <Calendar size={14} />
              <span>关联计划</span>
            </div>
            <div style={styles.linkedPlan}>
              <div style={styles.linkedPlanHeader}>
                <span style={styles.linkedPlanTitle}>{post.linkedPlan.title}</span>
                <span style={styles.linkedPlanProgress}>{Math.round(post.linkedPlan.progressPercentage || 0)}%</span>
              </div>
              {post.linkedPlan.description && (
                <p style={styles.linkedPlanDescription}>{post.linkedPlan.description}</p>
              )}
              {post.linkedPlan.owner && (
                <div style={styles.linkedPlanOwner}>
                  <span>由 {post.linkedPlan.owner.displayName || post.linkedPlan.owner.username} 创建</span>
                </div>
              )}
            </div>
          </div>
        )}
        
        {postImages.length > 0 && (
          <div style={styles.postImagesContainer}>
            {postImages.map((url, index) => (
              <img
                key={index}
                src={getImageUrl(url)}
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
            onClick={handleLike}
          >
            <Heart size={18} fill={post.liked ? '#ef4444' : 'none'} />
            <span>{post.liked ? '已点赞' : '点赞'} ({post.likes || 0})</span>
          </button>
          <button style={styles.actionButton} onClick={() => setShowComments(!showComments)}>
            <MessageCircle size={18} />
            <span>评论 ({post.commentsCount || 0})</span>
          </button>
          <button style={styles.actionButton} onClick={handleShare}>
            <Share2 size={18} />
            <span>分享</span>
          </button>
        </div>

        {showComments && (
          <div style={styles.commentsSection}>
            {replyingTo && (
              <div style={styles.replyingToBar}>
                <span>回复 {replyingTo.userName}</span>
                <button 
                  style={styles.cancelReplyButton}
                  onClick={() => {
                    setReplyingTo(null);
                    setNewComment('');
                  }}
                >
                  <X size={14} />
                </button>
              </div>
            )}
            <div style={styles.commentInputWrapper}>
              <input
                type="file"
                accept="image/*"
                ref={commentFileInputRef}
                style={{ display: 'none' }}
                onChange={handleCommentImageSelect}
              />
              
              <button
                style={styles.commentImageButton}
                onClick={() => commentFileInputRef.current?.click()}
              >
                <Image size={16} />
              </button>
              
              <EmojiPicker onEmojiSelect={addEmojiToComment} />
              
              <input
                type="text"
                placeholder={replyingTo ? `回复 ${replyingTo.userName}...` : "写下你的评论..."}
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                style={styles.commentInput}
                onKeyPress={(e) => e.key === 'Enter' && handleCreateComment()}
              />
              <button style={styles.commentSubmitButton} onClick={handleCreateComment}>
                <Send size={16} />
              </button>
            </div>
            
            {selectedCommentImages.length > 0 && (
              <div style={styles.imagePreviewContainer}>
                {selectedCommentImages.map((url, index) => (
                  <div key={index} style={styles.imagePreview}>
                    <img src={getImageUrl(url)} style={styles.previewImage} alt="预览" />
                    <button
                      style={styles.removeImageButton}
                      onClick={() => removeCommentImage(index)}
                    >
                      <X size={16} />
                    </button>
                  </div>
                ))}
              </div>
            )}
            
            {comments.length > 0 ? (
              nestedComments.map((comment) => (
                <CommentItem 
                  key={comment.id}
                  comment={comment}
                  postId={post.id}
                  postAuthorId={post.userId}
                  currentUserId={currentUserId}
                  onLike={handleCommentLike}
                  onReply={handleReply}
                  onDelete={handleDeleteComment}
                  onSubmitComment={handleCreateComment}
                  isReplying={replyingTo?.commentId === comment.id}
                  newCommentText={newComment}
                  onCommentChange={setNewComment}
                  navigate={navigate}
                  getAvatarUrl={getAvatarUrl}
                  parseMediaUrls={parseMediaUrls}
                  replyingToCommentId={replyingTo?.commentId || null}
                />
              ))
            ) : (
              <p style={styles.noComments}>暂无评论，快来抢沙发吧！</p>
            )}
          </div>
        )}
      </div>

      {showShareModal && (
        <div style={styles.modalOverlay}>
          <div style={styles.modal}>
            <div style={styles.modalHeader}>
              <h2 style={styles.modalTitle}>分享</h2>
              <button
                style={styles.modalClose} onClick={() => setShowShareModal(false)}>
                <X size={20} />
              </button>
            </div>
            <div style={styles.modalContent}>
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

              <textarea
                value={shareContent}
                onChange={(e) => setShareContent(e.target.value)}
                style={styles.shareInput}
                placeholder="说点什么... (可选)"
                rows={4}
              />
              <div style={styles.originalPostPreview}>
                <p style={styles.originalPostLabel}>转发自:</p>
                <p style={styles.originalPostContent}>{post.content.substring(0, 100)}{post.content.length > 100 ? '...' : ''}</p>
              </div>
            </div>
            <div style={styles.modalActions}>
              <button
                style={styles.cancelButton} onClick={() => setShowShareModal(false)}>
                <X size={16} />
                <span>取消</span>
              </button>
              <button
                style={{
                  ...styles.confirmButton,
                  ...(shareMode === 'chat' && !selectedReceiver ? styles.confirmButtonDisabled : {})
                }} 
                onClick={handleConfirmShare}
                disabled={shareMode === 'chat' && !selectedReceiver}>
                <Share2 size={16} />
                <span>分享</span>
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
    background: '#f8fafc',
    padding: '24px',
  },
  header: {
    maxWidth: '800px',
    margin: '0 auto 24px',
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
  postCard: {
    maxWidth: '800px',
    margin: '0 auto',
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
    background: '#e2e8f0',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#475569',
    fontWeight: 'bold',
    fontSize: '18px',
    flexShrink: 0,
    cursor: 'pointer',
  },
  userAvatarSmall: {
    width: '40px',
    height: '40px',
    borderRadius: '50%',
    background: '#e2e8f0',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#475569',
    fontWeight: 'bold',
    fontSize: '14px',
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
    cursor: 'pointer',
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
  linkedPlanContainer: {
    marginBottom: '16px',
    cursor: 'pointer',
  },
  linkedPlanLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    color: '#64748b',
    fontSize: '13px',
    marginBottom: '8px',
  },
  linkedPlan: {
    padding: '16px',
    background: '#f8fafc',
    border: '1px solid #e2e8f0',
    borderRadius: '12px',
    transition: 'all 0.2s ease',
  },
  linkedPlanHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px',
  },
  linkedPlanTitle: {
    fontWeight: 'bold',
    color: '#0f172a',
    fontSize: '15px',
  },
  linkedPlanProgress: {
    fontSize: '13px',
    color: '#374151',
    fontWeight: 'bold',
  },
  linkedPlanDescription: {
    color: '#64748b',
    fontSize: '14px',
    margin: 0,
    marginBottom: '8px',
  },
  linkedPlanOwner: {
    color: '#94a3b8',
    fontSize: '12px',
  },
  postImagesContainer: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '12px',
    marginBottom: '16px',
  },
  postImage: {
    maxWidth: '100%',
    maxHeight: '400px',
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
    background: 'transparent',
    border: '1px solid #e2e8f0',
    color: '#374151',
    borderRadius: '20px',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
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
  replyingToBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 12px',
    background: '#f8fafc',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    fontSize: '14px',
    color: '#374151',
  },
  cancelReplyButton: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: '#64748b',
    padding: '4px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  commentInputWrapper: {
    display: 'flex',
    gap: '12px',
    alignItems: 'center',
  },
  commentImageButton: {
    background: 'transparent',
    border: 'none',
    color: '#64748b',
    cursor: 'pointer',
    padding: '8px',
    borderRadius: '8px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
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
    background: '#000000',
    border: '1px solid #000000',
    borderRadius: '8px',
    color: 'white',
    cursor: 'pointer',
  },
  commentImagePreviewContainer: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
  },
  commentImagePreview: {
    position: 'relative',
    width: '80px',
    height: '80px',
  },
  commentPreviewImage: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    borderRadius: '6px',
  },
  removeImageButton: {
    position: 'absolute',
    top: '4px',
    right: '4px',
    background: 'rgba(0, 0, 0, 0.5)',
    border: 'none',
    color: 'white',
    borderRadius: '50%',
    width: '24px',
    height: '24px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
  },
  noComments: {
    textAlign: 'center',
    color: '#94a3b8',
    fontSize: '14px',
    padding: '16px 0',
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
  shareInput: {
    width: '100%',
    padding: '12px',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    fontSize: '14px',
    color: '#0f172a',
    resize: 'vertical',
    fontFamily: 'inherit',
    marginBottom: '16px',
  },
  originalPostPreview: {
    padding: '12px',
    background: '#f8fafc',
    borderRadius: '8px',
    borderLeft: '3px solid #64748b',
  },
  originalPostLabel: {
    fontSize: '12px',
    color: '#64748b',
    marginBottom: '4px',
  },
  originalPostContent: {
    fontSize: '14px',
    color: '#0f172a',
    lineHeight: '1.5',
  },
  modalActions: {
    display: 'flex',
    gap: '12px',
    justifyContent: 'flex-end',
  },
  confirmButton: {
    padding: '10px 20px',
    background: '#000000',
    color: 'white',
    border: '1px solid #000000',
    borderRadius: '8px',
    fontSize: '14px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  cancelButton: {
    padding: '10px 20px',
    background: 'transparent',
    color: '#374151',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    fontSize: '14px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
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
    marginBottom: '16px',
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
  formGroup: {
    marginBottom: '16px',
  },
  label: {
    display: 'block',
    fontSize: '14px',
    fontWeight: '500',
    color: '#333',
    marginBottom: '8px',
  },
  confirmButtonDisabled: {
    background: '#cbd5e1',
    cursor: 'not-allowed',
  },
};

export default PostDetail;
