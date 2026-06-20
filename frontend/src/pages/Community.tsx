import React, { useState, useEffect, useRef } from 'react';
import { Heart, MessageCircle, Share2, Send, Image, X, Flame, Clock, Zap, Book, Trash2, Calendar, Users } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { postApi, commentApi, planApi, chatApi, getImageUrl } from '../services/api';
import type { Post, Comment, Plan, ChatConversation, PlanInfo } from '../types';
import EmojiPicker from '../components/EmojiPicker';
import { useAuth } from '../context/AuthContext';
import CommentItem from '../components/CommentItem';
import type { CommentWithReplies } from '../components/CommentItem';

const Community: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const currentUserId = user?.id || 0;
  const [posts, setPosts] = useState<Post[]>([]);
  
  useEffect(() => {
    console.log('Posts state updated:', posts);
  }, [posts]);
  const [comments, setComments] = useState<{ [key: number]: Comment[] }>({});
  const [newPostContent, setNewPostContent] = useState('');
  const [newComment, setNewComment] = useState<{ [key: number]: string }>({});
  const [showComments, setShowComments] = useState<{ [key: number]: boolean }>({});
  const [replyingTo, setReplyingTo] = useState<{ [key: number]: number | null }>({});
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'all' | 'latest' | 'popular'>('all');
  const [selectedImages, setSelectedImages] = useState<string[]>([]);
  const [selectedCommentImages, setSelectedCommentImages] = useState<{ [key: number]: string[] }>({});
  const [uploading, setUploading] = useState(false);
  const [selectedHashtags, setSelectedHashtags] = useState<string[]>([]);
  const [hashtagInput, setHashtagInput] = useState('');
  const [showHashtagSuggestions, setShowHashtagSuggestions] = useState(false);
  const [trendingTopics, setTrendingTopics] = useState<string[]>([]);
  const [shareModal, setShareModal] = useState<{ postId: number; userId: number; content: string } | null>(null);
  const [shareContent, setShareContent] = useState('');
  const [shareMode, setShareMode] = useState<'community' | 'chat'>('community');
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [selectedReceiver, setSelectedReceiver] = useState<number | null>(null);
  const [loadingConversations, setLoadingConversations] = useState(false);
  const [userPlans, setUserPlans] = useState<PlanInfo[]>([]);
  const [publicPlans, setPublicPlans] = useState<PlanInfo[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);
  const [showPlanSelector, setShowPlanSelector] = useState(false);
  const [planTab, setPlanTab] = useState<'my' | 'public'>('my');
  const [planSearch, setPlanSearch] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
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

  const getAvatarUrl = (avatarUrl?: string) => {
    if (!avatarUrl) return null;
    if (avatarUrl.startsWith('http')) return avatarUrl;
    if (avatarUrl.startsWith('/')) return `http://localhost:8080${avatarUrl}`;
    return `http://localhost:8080/${avatarUrl}`;
  };

  useEffect(() => {
    loadPosts();
    loadTrendingTopics();
    if (currentUserId) {
      loadUserPlans();
    }
  }, [activeTab, currentUserId]);

  useEffect(() => {
    if (showPlanSelector) {
      if (planTab === 'my' && currentUserId) {
        loadUserPlans();
      } else if (planTab === 'public') {
        loadPublicPlans();
      }
    }
  }, [showPlanSelector, planTab, planSearch, currentUserId]);

  const loadPosts = () => {
    setLoading(true);
    let promise;
    switch (activeTab) {
      case 'latest':
        promise = postApi.getLatestPosts(10);
        break;
      case 'popular':
        promise = postApi.getPopularPosts(10);
        break;
      default:
        promise = postApi.getAllPosts();
    }
    promise
      .then((data) => {
        console.log('Posts loaded:', data);
        console.log('Posts length:', data.length);
        setPosts(data);
      })
      .catch((error) => {
        console.error('Error loading posts:', error);
        setPosts([]);
      })
      .finally(() => setLoading(false));
  };

  const loadTrendingTopics = () => {
    postApi.getTrendingHashtags()
      .then((data) => {
        if (data.length > 0) {
          setTrendingTopics(data);
        } else {
          setTrendingTopics(['#计划管理', '#时间管理', '#目标设定', '#效率提升', '#团队协作']);
        }
      })
      .catch(() => {
        setTrendingTopics(['#计划管理', '#时间管理', '#目标设定', '#效率提升', '#团队协作']);
      });
  };

  const loadUserPlans = () => {
    planApi.getUserPlans(currentUserId, planSearch)
      .then((data) => {
        setUserPlans(data);
      })
      .catch(() => {
        setUserPlans([]);
      });
  };

  const loadPublicPlans = () => {
    planApi.getPublicPlans(planSearch)
      .then((data) => {
        setPublicPlans(data);
      })
      .catch(() => {
        setPublicPlans([]);
      });
  };

  const toggleComments = async (postId: number) => {
    setShowComments(prev => ({ ...prev, [postId]: !prev[postId] }));
    if (!comments[postId]) {
      const data = await commentApi.getCommentsByPostId(postId);
      setComments(prev => ({ ...prev, [postId]: data }));
    }
  };

  const handleImageSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      setUploading(true);
      try {
        const imageUrl = await postApi.uploadImage(files[0]);
        setSelectedImages(prev => [...prev, imageUrl]);
      } catch (err) {
        alert('图片上传失败');
        console.error(err);
      } finally {
        setUploading(false);
      }
    }
  };

  const handleCommentImageSelect = async (postId: number, e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      setUploading(true);
      try {
        const imageUrl = await postApi.uploadImage(files[0]);
        setSelectedCommentImages(prev => ({
          ...prev,
          [postId]: [...(prev[postId] || []), imageUrl]
        }));
      } catch (err) {
        alert('图片上传失败');
        console.error(err);
      } finally {
        setUploading(false);
      }
    }
  };

  const removeImage = (index: number) => {
    setSelectedImages(prev => prev.filter((_, i) => i !== index));
  };

  const removeCommentImage = (postId: number, index: number) => {
    setSelectedCommentImages(prev => ({
      ...prev,
      [postId]: prev[postId].filter((_, i) => i !== index)
    }));
  };

  const addEmojiToPost = (emoji: string) => {
    setNewPostContent(prev => prev + emoji);
  };

  const addEmojiToComment = (postId: number, emoji: string) => {
    setNewComment(prev => ({
      ...prev,
      [postId]: (prev[postId] || '') + emoji
    }));
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

  const handleHashtagAdd = () => {
    const trimmed = hashtagInput.trim();
    if (trimmed && !selectedHashtags.includes(trimmed)) {
      setSelectedHashtags(prev => [...prev, trimmed]);
      setHashtagInput('');
    }
  };

  const handleHashtagRemove = (hashtag: string) => {
    setSelectedHashtags(prev => prev.filter(h => h !== hashtag));
  };

  const handleCreatePost = async () => {
    if (!newPostContent.trim() && selectedImages.length === 0 && selectedHashtags.length === 0 && !selectedPlanId) return;
    try {
      const newPost = await postApi.createPost({
        content: newPostContent || "", // 确保content不为null
        mediaUrls: selectedImages.length > 0 ? selectedImages : undefined,
        postType: selectedImages.length > 0 ? 'image' : 'text',
        hashtags: selectedHashtags.length > 0 ? selectedHashtags : undefined,
        linkedPlanId: selectedPlanId || undefined
      });
      setPosts([newPost, ...posts]);
      setNewPostContent('');
      setSelectedImages([]);
      setSelectedHashtags([]);
      setSelectedPlanId(null);
      setShowPlanSelector(false);
    } catch (err) {
      alert('发布失败');
    }
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

  const handleCreateComment = async (postId: number) => {
    const content = newComment[postId];
    const images = selectedCommentImages[postId] || [];
    if (!content?.trim() && images.length === 0) return;
    try {
      const parentCommentId = replyingTo[postId] || undefined;
      await commentApi.createComment(postId, {
        content: content || '',
        mediaUrls: images.length > 0 ? images : undefined,
        parentCommentId
      });
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
      setSelectedCommentImages(prev => ({ ...prev, [postId]: [] }));
    } catch (err) {
      alert('评论失败');
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

  const handleDeletePost = async (postId: number) => {
    if (!window.confirm('确定要删除这条动态吗？')) return;
    try {
      await postApi.deletePost(postId);
      setPosts(posts.filter(p => p.id !== postId));
    } catch (err) {
      alert('删除失败');
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

  const handleShare = (postId: number, userId: number) => {
    setShareModal({ postId, userId, content: '' });
    setShareContent('');
    setShareMode('community');
    setSelectedReceiver(null);
    if (user) {
      loadConversations();
    }
  };

  const handleConfirmShare = async () => {
    if (!shareModal) return;
    try {
      if (shareMode === 'community') {
        await postApi.sharePost(shareModal.postId, shareModal.userId, shareContent);
        alert('分享成功！');
        setShareModal(null);
        setShareContent('');
        loadPosts();
      } else if (shareMode === 'chat' && selectedReceiver) {
        await chatApi.sharePostToChat(selectedReceiver, shareModal.postId, shareContent);
        alert('分享成功！');
        setShareModal(null);
        setShareContent('');
        setSelectedReceiver(null);
      }
    } catch (err) {
      alert('分享失败，请重试');
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

  const parseHashtags = (hashtags: string | undefined): string[] => {
    if (!hashtags) return [];
    try {
      return JSON.parse(hashtags);
    } catch {
      return [];
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.feedContainer}>
        <div style={styles.mainFeed}>
          <div style={styles.createPostCard}>
            <div style={styles.postHeader}>
              <div style={styles.userAvatar}>U</div>
              <textarea
                placeholder="分享你的想法..."
                value={newPostContent}
                onChange={(e) => setNewPostContent(e.target.value)}
                style={styles.postInput}
                rows={3}
              />
            </div>
            
            {selectedImages.length > 0 && (
              <div style={styles.imagePreviewContainer}>
                {selectedImages.map((url, index) => (
                  <div key={index} style={styles.imagePreview}>
                    <img src={getImageUrl(url)} style={styles.previewImage} alt="预览" />
                    <button
                      style={styles.removeImageButton}
                      onClick={() => removeImage(index)}
                    >
                      <X size={16} />
                    </button>
                  </div>
                ))}
              </div>
            )}
            
            {selectedHashtags.length > 0 && (
              <div style={styles.selectedHashtags}>
                {selectedHashtags.map((hashtag, index) => (
                  <span key={index} style={styles.selectedHashtag}>
                    #{hashtag}
                    <button 
                      style={styles.removeHashtagButton} 
                      onClick={() => handleHashtagRemove(hashtag)}
                    >
                      <X size={14} />
                    </button>
                  </span>
                ))}
              </div>
            )}
            
            {selectedPlanId && (
              <div style={styles.selectedPlan}>
                <Calendar size={16} />
                <span>{userPlans.find(p => p.id === selectedPlanId)?.title || '已选择计划'}</span>
                <button 
                  style={styles.removePlanButton} 
                  onClick={() => setSelectedPlanId(null)}
                >
                  <X size={14} />
                </button>
              </div>
            )}
            
            {showPlanSelector && (
              <div style={styles.planSelector}>
                <div style={styles.planSelectorHeader}>
                  <span>选择计划</span>
                  <button 
                    style={styles.closePlanSelector}
                    onClick={() => setShowPlanSelector(false)}
                  >
                    <X size={16} />
                  </button>
                </div>
                
                <div style={styles.planTabs}>
                <button
                  style={{
                    ...styles.planTab,
                    ...(planTab === 'my' ? styles.planTabActive : {})
                  }}
                  onClick={() => setPlanTab('my')}
                >
                  我的公开计划
                </button>
                <button
                  style={{
                    ...styles.planTab,
                    ...(planTab === 'public' ? styles.planTabActive : {})
                  }}
                  onClick={() => setPlanTab('public')}
                >
                  他人公开计划
                </button>
              </div>

              <div style={styles.planSearchWrapper}>
                <input
                  type="text"
                  placeholder="搜索计划..."
                  value={planSearch}
                  onChange={(e) => setPlanSearch(e.target.value)}
                  style={styles.planSearchInput}
                />
              </div>

              <div style={styles.planList}>
                {(planTab === 'my' ? userPlans : publicPlans).length === 0 ? (
                  <p style={styles.noPlans}>{planTab === 'my' ? '您还没有公开计划' : '暂无公开计划'}</p>
                ) : (
                    (planTab === 'my' ? userPlans : publicPlans).map((plan) => (
                      <button
                        key={plan.id}
                        style={{
                          ...styles.planItem,
                          ...(selectedPlanId === plan.id ? styles.planItemActive : {})
                        }}
                        onClick={() => {
                          setSelectedPlanId(plan.id);
                          setShowPlanSelector(false);
                        }}
                      >
                        <div style={styles.planItemLeft}>
                          <span style={styles.planTitle}>{plan.title}</span>
                          {plan.description && (
                            <span style={styles.planDescription}>{plan.description}</span>
                          )}
                          {plan.owner && (
                            <span style={styles.planOwner}>
                              by {plan.owner.displayName || plan.owner.username}
                            </span>
                          )}
                        </div>
                        <span style={styles.planProgress}>{Math.round(plan.progressPercentage || 0)}%</span>
                      </button>
                    ))
                  )}
                </div>
              </div>
            )}
            
            <div style={styles.hashtagInputWrapper}>
              <input
                type="text"
                placeholder="添加话题标签..."
                value={hashtagInput}
                onChange={(e) => setHashtagInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleHashtagAdd())}
                style={styles.hashtagInput}
              />
              <button style={styles.hashtagAddButton} onClick={handleHashtagAdd}>
                添加
              </button>
            </div>
            
            <div style={styles.postActions}>
              <input
                type="file"
                accept="image/*"
                ref={fileInputRef}
                style={{ display: 'none' }}
                onChange={handleImageSelect}
              />
              <button 
                style={styles.postActionButton}
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
              >
                <Image size={18} />
                <span>图片</span>
              </button>
              
              <button 
                style={styles.postActionButton}
                onClick={() => setShowPlanSelector(!showPlanSelector)}
              >
                <Calendar size={18} />
                <span>计划</span>
              </button>
              
              <EmojiPicker onEmojiSelect={addEmojiToPost} />
              
              <button 
                style={styles.postSubmitButton} 
                onClick={handleCreatePost}
                disabled={uploading}
              >
                <Send size={18} />
                <span>发布</span>
              </button>
            </div>
          </div>

          <div style={styles.tabContainer}>
            <button
              style={{ ...styles.tabButton, ...(activeTab === 'all' ? styles.activeTab : {}) }}
              onClick={() => setActiveTab('all')}
            >
              全部
            </button>
            <button
              style={{ ...styles.tabButton, ...(activeTab === 'latest' ? styles.activeTab : {}) }}
              onClick={() => setActiveTab('latest')}
            >
              <Clock size={16} />
              最新
            </button>
            <button
              style={{ ...styles.tabButton, ...(activeTab === 'popular' ? styles.activeTab : {}) }}
              onClick={() => setActiveTab('popular')}
            >
              <Flame size={16} />
              热门
            </button>
          </div>

          {loading ? (
            <div style={styles.loading}>加载中...</div>
          ) : posts.length === 0 ? (
            <div style={styles.emptyState}>
              <p>暂无动态，快来发布第一条吧！</p>
            </div>
          ) : (
            posts.map((post) => {
              const displayName = post.user?.displayName || post.user?.username || `用户${post.userId}`;
              const avatarUrl = getAvatarUrl(post.user?.avatarUrl);
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
                      {!avatarUrl && (post.user?.displayName?.charAt(0) || post.user?.username?.charAt(0) || 'U').toUpperCase()}
                    </div>
                    <div style={styles.userInfo}>
                      <span style={styles.userName} onClick={() => navigate(`/user/${post.userId}`)}>
                        {displayName}
                      </span>
                      <span style={styles.postTime}>{new Date(post.createdAt).toLocaleString('zh-CN')}</span>
                    </div>
                    <button style={styles.deleteButton} onClick={() => handleDeletePost(post.id)}>
                      <X size={16} />
                    </button>
                  </div>

                  <p style={styles.postContent}>{post.content}</p>
                  
                  {post.originalPost && (
                    <div style={styles.repostContainer} onClick={() => navigate(`/post/${post.originalPost.id}`)}>
                      <div style={styles.repostLabel}>
                        <Share2 size={14} />
                        <span>转发自 {post.originalAuthor?.displayName || post.originalAuthor?.username || '用户' + post.originalAuthorId}</span>
                      </div>
                      <div style={styles.originalPost}>
                        {post.originalPost.user && (
                          <div style={styles.originalPostHeader}>
                            <div 
                              style={{
                                ...styles.userAvatarSmall,
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
                              <img key={index} src={getImageUrl(url)} style={styles.originalPostImage} alt={`原帖图片 ${index + 1}`} />
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
                        <input
                          type="file"
                          accept="image/*"
                          ref={(el) => {
                            if (el) commentFileInputRef.current = el;
                          }}
                          style={{ display: 'none' }}
                          onChange={(e) => handleCommentImageSelect(post.id, e)}
                        />
                        
                        <button
                          style={styles.commentImageButton}
                          onClick={() => commentFileInputRef.current?.click()}
                        >
                          <Image size={16} />
                        </button>
                        
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
                      
                      {(selectedCommentImages[post.id] || []).length > 0 && (
                        <div style={styles.commentImagePreviewContainer}>
                          {(selectedCommentImages[post.id] || []).map((url, index) => (
                            <div key={index} style={styles.commentImagePreview}>
                              <img src={getImageUrl(url)} style={styles.commentPreviewImage} alt="预览" />
                              <button
                                style={styles.removeImageButton}
                                onClick={() => removeCommentImage(post.id, index)}
                              >
                                <X size={14} />
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                      
                      {comments[post.id] && comments[post.id].length > 0 ? (
                        buildNestedComments(comments[post.id]).map((comment) => (
                          <CommentItem 
                            key={comment.id} 
                            comment={comment} 
                            postId={post.id}
                            postAuthorId={post.userId}
                            currentUserId={currentUserId}
                            onLike={(commentId) => handleCommentLike(post.id, commentId)}
                            onReply={(commentId, userName) => {
                              setNewComment(prev => ({ ...prev, [post.id]: `@${userName} ` }));
                              setReplyingTo({ ...replyingTo, [post.id]: commentId });
                            }}
                            onDelete={(commentId) => handleDeleteComment(post.id, commentId)}
                            onSubmitComment={() => handleCreateComment(post.id)}
                            isReplying={replyingTo[post.id] === comment.id}
                            newCommentText={newComment[post.id] || ''}
                            onCommentChange={(value) => setNewComment({ ...newComment, [post.id]: value })}
                            navigate={navigate}
                            getAvatarUrl={getAvatarUrl}
                            parseMediaUrls={parseMediaUrls}
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

        <div style={styles.sidebar}>
          <div style={styles.sidebarCard}>
            <h3 style={styles.sidebarTitle}>
              <Flame size={18} />
              <span>热门话题</span>
            </h3>
            <div style={styles.trendingList}>
              {trendingTopics.map((topic, index) => {
                const hashtag = topic.replace('#', '');
                return (
                  <button
                    key={index}
                    style={styles.trendingItem}
                    onClick={() => navigate(`/hashtag/${hashtag}`)}
                  >
                    <span style={styles.trendingNumber}>{index + 1}</span>
                    <span>{topic}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <div style={styles.sidebarCard}>
            <h3 style={styles.sidebarTitle}>
              <img src="/robot-icon.png" alt="Plan助手" style={{ width: 28, height: 28, mixBlendMode: 'multiply' }} />
              <span>Plan 助手</span>
            </h3>
            <p style={styles.assistantDescription}>
              智能 AI 助手，帮你更好地使用 PlanHub
            </p>
            <div style={styles.assistantButtons}>
              <button
                style={styles.assistantButton}
                onClick={() => navigate('/chatbot')}
              >
                <div style={{ width: 24, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <img src="/robot-icon.png" alt="Plan 助手" style={{ width: 24, height: 24, mixBlendMode: 'multiply' }} />
                </div>
                <span>Plan 助手</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {shareModal && (
        <div style={styles.modalOverlay} onClick={() => setShareModal(null)}>
          <div style={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h3 style={styles.modalTitle}>分享</h3>
              <button style={styles.closeButton} onClick={() => setShareModal(null)}>
                <X size={20} />
              </button>
            </div>

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
              <button
                style={{
                  ...styles.confirmButton,
                  ...(shareMode === 'chat' && !selectedReceiver ? styles.confirmButtonDisabled : {})
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
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    minHeight: '100%',
  },
  feedContainer: {
    display: 'grid',
    gridTemplateColumns: '1fr 300px',
    gap: '24px',
  },
  mainFeed: {
    display: 'flex',
    flexDirection: 'column',
    gap: '24px',
  },
  createPostCard: {
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
    background: '#333333',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
    fontWeight: 'bold',
    fontSize: '18px',
    flexShrink: 0,
    cursor: 'pointer',
  },
  userAvatarSmall: {
    width: '32px',
    height: '32px',
    background: '#333333',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
    fontWeight: 'bold',
    fontSize: '12px',
    flexShrink: 0,
    cursor: 'pointer',
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
  deleteButton: {
    background: 'transparent',
    border: 'none',
    color: '#94a3b8',
    cursor: 'pointer',
    padding: '4px',
    borderRadius: '4px',
  },
  postInput: {
    flex: 1,
    border: 'none',
    resize: 'none',
    fontSize: '15px',
    lineHeight: '1.6',
    color: '#0f172a',
    background: '#f8fafc',
    borderRadius: '12px',
    padding: '12px',
  },
  imagePreviewContainer: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '12px',
    marginTop: '16px',
  },
  imagePreview: {
    position: 'relative',
    width: '100px',
    height: '100px',
  },
  previewImage: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    borderRadius: '8px',
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
  postActions: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    marginTop: '16px',
    paddingTop: '16px',
    borderTop: '1px solid #e2e8f0',
  },
  postActionButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 16px',
    background: '#f1f5f9',
    border: 'none',
    borderRadius: '8px',
    color: '#64748b',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  postSubmitButton: {
    marginLeft: 'auto',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 20px',
    background: '#333333',
    border: 'none',
    borderRadius: '8px',
    color: 'white',
    fontSize: '14px',
    fontWeight: 'medium',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  tabContainer: {
    display: 'flex',
    gap: '8px',
    background: 'white',
    borderRadius: '12px',
    padding: '8px',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)',
    border: '1px solid #e2e8f0',
  },
  tabButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '10px 20px',
    background: 'transparent',
    border: 'none',
    borderRadius: '8px',
    color: '#64748b',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  activeTab: {
    background: '#333333',
    color: 'white',
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
  postCard: {
    background: 'white',
    borderRadius: '16px',
    padding: '24px',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)',
    border: '1px solid #e2e8f0',
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
    background: '#333333',
    border: 'none',
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
  commentImagesContainer: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
    marginTop: '8px',
  },
  commentImage: {
    maxWidth: '200px',
    maxHeight: '150px',
    borderRadius: '6px',
    objectFit: 'cover',
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
  noComments: {
    textAlign: 'center',
    color: '#94a3b8',
    fontSize: '14px',
    padding: '16px 0',
  },
  nestedCommentItem: {
    paddingLeft: '40px',
  },
  repliesContainer: {
    marginTop: '12px',
    paddingLeft: '20px',
    borderLeft: '2px solid #e2e8f0',
  },
  showRepliesButton: {
    background: 'none',
    border: 'none',
    color: '#64748b',
    fontSize: '13px',
    cursor: 'pointer',
    padding: '8px 0',
    marginTop: '4px',
    textDecoration: 'underline',
  },
  hideRepliesButton: {
    background: 'none',
    border: 'none',
    color: '#64748b',
    fontSize: '13px',
    cursor: 'pointer',
    padding: '8px 0',
    marginTop: '8px',
    textDecoration: 'underline',
  },
  replyInputWrapper: {
    display: 'flex',
    gap: '12px',
    alignItems: 'center',
    marginTop: '12px',
  },
  replyInput: {
    flex: 1,
    padding: '10px 16px',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    fontSize: '14px',
    background: '#f8fafc',
  },
  replySubmitButton: {
    padding: '10px 16px',
    background: '#333333',
    border: 'none',
    borderRadius: '8px',
    color: 'white',
    cursor: 'pointer',
  },
  sidebar: {
    position: 'sticky',
    top: '24px',
    height: 'fit-content',
  },
  sidebarCard: {
    background: 'white',
    borderRadius: '16px',
    padding: '24px',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)',
    border: '1px solid #e2e8f0',
    marginBottom: '24px',
  },
  sidebarTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    fontSize: '18px',
    fontWeight: 'bold',
    color: '#0f172a',
    marginBottom: '20px',
  },
  trendingList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  trendingItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '8px',
    background: '#f8fafc',
    borderRadius: '8px',
    border: 'none',
    cursor: 'pointer',
    fontSize: '14px',
    color: '#0f172a',
    transition: 'all 0.3s ease',
    textAlign: 'left',
  },
  trendingNumber: {
    width: '24px',
    height: '24px',
    background: '#e2e8f0',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '12px',
    fontWeight: 'bold',
    color: '#64748b',
  },
  joinButton: {
    width: '100%',
    padding: '12px',
    background: '#333333',
    border: 'none',
    borderRadius: '10px',
    color: 'white',
    fontSize: '15px',
    fontWeight: 'medium',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  selectedHashtags: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
    marginTop: '12px',
  },
  selectedHashtag: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '6px 12px',
    background: '#f1f5f9',
    color: '#333333',
    borderRadius: '20px',
    fontSize: '14px',
  },
  removeHashtagButton: {
    background: 'transparent',
    border: 'none',
    color: '#333333',
    cursor: 'pointer',
    padding: '2px',
  },
  selectedPlan: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 12px',
    background: '#f1f5f9',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    color: '#333333',
    fontSize: '14px',
    marginTop: '12px',
  },
  removePlanButton: {
    background: 'transparent',
    border: 'none',
    color: '#ef4444',
    cursor: 'pointer',
    padding: '2px',
    marginLeft: 'auto',
  },
  planSelector: {
    position: 'relative',
    background: '#f8fafc',
    border: '1px solid #e2e8f0',
    borderRadius: '12px',
    padding: '16px',
    marginTop: '12px',
  },
  planSelectorHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px',
    paddingBottom: '8px',
    borderBottom: '1px solid #e2e8f0',
  },
  closePlanSelector: {
    background: 'transparent',
    border: 'none',
    color: '#64748b',
    cursor: 'pointer',
    padding: '4px',
  },
  planTabs: {
    display: 'flex',
    gap: '8px',
    marginBottom: '12px',
  },
  planTab: {
    flex: 1,
    padding: '8px 16px',
    background: 'white',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    color: '#64748b',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  planTabActive: {
    background: '#333333',
    borderColor: '#333333',
    color: 'white',
  },
  planSearchWrapper: {
    marginBottom: '12px',
  },
  planSearchInput: {
    width: '100%',
    padding: '10px 12px',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    fontSize: '14px',
    background: 'white',
    outline: 'none',
    transition: 'all 0.2s ease',
    '&:focus': {
      borderColor: '#333333',
    },
  },
  planList: {
    maxHeight: '200px',
    overflowY: 'auto',
  },
  noPlans: {
    textAlign: 'center',
    color: '#64748b',
    padding: '20px',
    margin: 0,
  },
  planItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    width: '100%',
    padding: '12px',
    background: 'white',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    marginBottom: '8px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    textAlign: 'left',
  },
  planItemActive: {
    borderColor: '#333333',
    background: '#f1f5f9',
  },
  planItemLeft: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    overflow: 'hidden',
  },
  planTitle: {
    fontWeight: '500',
    color: '#0f172a',
    fontSize: '14px',
  },
  planDescription: {
    fontSize: '12px',
    color: '#64748b',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  planOwner: {
    fontSize: '11px',
    color: '#94a3b8',
    marginTop: '2px',
  },
  planProgress: {
    fontSize: '13px',
    color: '#333333',
    fontWeight: 'bold',
    flexShrink: 0,
  },
  linkedPlanContainer: {
    marginBottom: '16px',
    cursor: 'pointer',
  },
  linkedPlanLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '13px',
    color: '#64748b',
    marginBottom: '8px',
  },
  linkedPlan: {
    background: '#f8fafc',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    padding: '12px',
    transition: 'all 0.2s ease',
    '&:hover': {
      borderColor: '#333333',
    },
  },
  linkedPlanHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px',
  },
  linkedPlanTitle: {
    fontWeight: 'bold',
    fontSize: '15px',
    color: '#0f172a',
  },
  linkedPlanProgress: {
    fontSize: '14px',
    color: '#333333',
    fontWeight: 'bold',
  },
  linkedPlanDescription: {
    fontSize: '13px',
    color: '#64748b',
    margin: '0 0 8px 0',
    lineHeight: '1.5',
  },
  linkedPlanOwner: {
    fontSize: '12px',
    color: '#94a3b8',
  },
  hashtagInputWrapper: {
    display: 'flex',
    gap: '8px',
    marginTop: '12px',
  },
  hashtagInput: {
    flex: 1,
    padding: '8px 12px',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    fontSize: '14px',
    background: '#f8fafc',
  },
  hashtagAddButton: {
    padding: '8px 16px',
    background: '#f1f5f9',
    border: '1px solid #94a3b8',
    borderRadius: '8px',
    color: '#333333',
    fontSize: '14px',
    cursor: 'pointer',
  },
  hashtagsContainer: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
    marginBottom: '16px',
  },
  hashtag: {
    padding: '6px 12px',
    background: '#f1f5f9',
    color: '#333333',
    borderRadius: '20px',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
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
    background: '#333333',
    border: 'none',
    borderRadius: '8px',
    color: 'white',
    fontSize: '14px',
    cursor: 'pointer',
  },
  repostContainer: {
    marginTop: '16px',
    border: '1px solid #e2e8f0',
    borderRadius: '12px',
    overflow: 'hidden',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
  },
  repostLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '8px 12px',
    background: '#f1f5f9',
    fontSize: '12px',
    color: '#64748b',
  },
  originalPost: {
    padding: '12px',
    background: '#fafafa',
  },
  originalPostHeader: {
    display: 'flex',
    gap: '10px',
    alignItems: 'center',
    marginBottom: '8px',
  },
  originalPostUserInfo: {
    display: 'flex',
    flexDirection: 'column',
  },
  originalPostUserName: {
    fontSize: '13px',
    fontWeight: 'bold',
    color: '#0f172a',
  },
  originalPostTime: {
    fontSize: '11px',
    color: '#94a3b8',
  },
  originalPostContent: {
    fontSize: '14px',
    color: '#334155',
    lineHeight: '1.5',
    marginBottom: '10px',
  },
  originalPostImages: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
    marginBottom: '10px',
  },
  originalPostImage: {
    maxWidth: '150px',
    maxHeight: '150px',
    borderRadius: '6px',
    objectFit: 'cover',
  },
  originalPostStats: {
    display: 'flex',
    gap: '16px',
    fontSize: '12px',
    color: '#64748b',
  },
  assistantDescription: {
    fontSize: '13px',
    color: '#64748b',
    marginBottom: '16px',
    lineHeight: '1.5',
  },
  assistantButtons: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  assistantButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '12px 16px',
    background: '#f1f5f9',
    border: '1px solid #e2e8f0',
    borderRadius: '10px',
    color: '#000000',
    fontSize: '14px',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
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
    border: '2px solid #e2e8f0',
    borderRadius: '12px',
    background: 'white',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    fontSize: '14px',
    fontWeight: '500',
    color: '#64748b',
  },
  shareModeButtonActive: {
    borderColor: '#333333',
    background: '#f0f4ff',
    color: '#333333',
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

export default Community;
