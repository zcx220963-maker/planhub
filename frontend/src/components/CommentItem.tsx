import React from 'react';
import { Heart, MessageCircle, Trash2, ChevronDown, ChevronUp } from 'lucide-react';
import type { Comment } from '../types';
import { getImageUrl } from '../services/api';

interface CommentWithReplies extends Comment {
  replies?: CommentWithReplies[];
}

export type { CommentWithReplies };

export interface CommentItemProps {
  comment: CommentWithReplies;
  postId: number;
  postAuthorId: number;
  currentUserId: number;
  onLike: (commentId: number) => void;
  onReply: (commentId: number, userName: string) => void;
  onDelete: (commentId: number) => void;
  isReplying: boolean;
  newCommentText: string;
  onCommentChange: (value: string) => void;
  onSubmitComment: () => void;
  navigate: (path: string) => void;
  getAvatarUrl: (avatarUrl?: string) => string | null;
  parseMediaUrls: (mediaUrls: string | undefined) => string[];
  replyingToCommentId: number | null;
  level?: number;
}

const CommentItem: React.FC<CommentItemProps> = ({
  comment,
  postId,
  postAuthorId,
  currentUserId,
  onLike,
  onReply,
  onDelete,
  isReplying,
  newCommentText,
  onCommentChange,
  onSubmitComment,
  navigate,
  getAvatarUrl,
  parseMediaUrls,
  replyingToCommentId,
  level = 0,
}) => {
  const [expanded, setExpanded] = React.useState(false);
  const commentDisplayName = comment.user?.displayName || comment.user?.username || `用户${comment.userId}`;
  const commentAvatarUrl = getAvatarUrl(comment.user?.avatarUrl);
  const commentImages = parseMediaUrls(comment.mediaUrls);
  const replyCount = comment.replies?.length || 0;
  const hasReplies = replyCount > 0;
  const canDelete = comment.userId === currentUserId || postAuthorId === currentUserId;
  const isTopLevel = level === 0;

  const handleDelete = () => {
    if (window.confirm('确定要删除这条评论吗？')) {
      onDelete(comment.id);
    }
  };

  const handleReplyClick = () => {
    if (hasReplies) {
      setExpanded(!expanded);
    }
    onReply(comment.id, commentDisplayName);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <div style={styles.commentItem}>
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
          {!commentAvatarUrl && (comment.user?.displayName?.charAt(0) || comment.user?.username?.charAt(0) || 'U').toUpperCase()}
        </div>
        <div style={styles.commentContent}>
          <span 
            style={styles.commentUserName}
            onClick={() => navigate(`/user/${comment.userId}`)}
          >
            {commentDisplayName}
          </span>
          <span style={styles.commentText}>{comment.content}</span>
          
          {commentImages.length > 0 && (
            <div style={styles.commentImagesContainer}>
              {commentImages.map((url, index) => (
                <img
                  key={index}
                  src={getImageUrl(url)}
                  style={styles.commentImage}
                  alt={`评论图片 ${index + 1}`}
                />
              ))}
            </div>
          )}
          
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
              style={{
                ...styles.commentActionButton,
                color: replyingToCommentId === comment.id ? '#000000' : '#64748b',
              }}
              onClick={handleReplyClick}
            >
              <MessageCircle size={14} />
              <span>回复 ({replyCount})</span>
              {hasReplies && (
                expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />
              )}
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
                value={newCommentText}
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
                <MessageCircle size={14} />
              </button>
            </div>
          )}
        </div>
      </div>
      {isTopLevel && hasReplies && expanded && (
        <div style={{ paddingLeft: '40px' }}>
          {comment.replies.map((reply) => (
            <div key={reply.id} style={styles.replyItem}>
              <div style={styles.commentItem}>
                <div 
                  style={{
                    ...styles.userAvatarSmall,
                    ...(getAvatarUrl(reply.user?.avatarUrl) ? {
                      backgroundImage: `url(${getAvatarUrl(reply.user?.avatarUrl)})`,
                      backgroundSize: 'cover',
                      backgroundPosition: 'center',
                    } : {})
                  }} 
                  onClick={() => navigate(`/user/${reply.userId}`)}
                >
                  {!getAvatarUrl(reply.user?.avatarUrl) && (reply.user?.displayName?.charAt(0) || reply.user?.username?.charAt(0) || 'U').toUpperCase()}
                </div>
                <div style={styles.commentContent}>
                  <span 
                    style={styles.commentUserName}
                    onClick={() => navigate(`/user/${reply.userId}`)}
                  >
                    {reply.user?.displayName || reply.user?.username || `用户${reply.userId}`}
                  </span>
                  <span style={styles.commentText}>{reply.content}</span>
                  
                  {parseMediaUrls(reply.mediaUrls).length > 0 && (
                    <div style={styles.commentImagesContainer}>
                      {parseMediaUrls(reply.mediaUrls).map((url, index) => (
                        <img
                          key={index}
                          src={getImageUrl(url)}
                          style={styles.commentImage}
                          alt={`评论图片 ${index + 1}`}
                        />
                      ))}
                    </div>
                  )}
                  
                  <span style={styles.commentTime}>
                    {new Date(reply.createdAt).toLocaleString('zh-CN')}
                  </span>
                  <div style={styles.commentActions}>
                    <button
                      style={{
                        ...styles.commentActionButton,
                        color: reply.liked ? '#ef4444' : '#64748b',
                      }}
                      onClick={() => onLike(reply.id)}
                    >
                      <Heart size={14} fill={reply.liked ? '#ef4444' : 'none'} />
                      <span>{reply.likeCount || 0}</span>
                    </button>
                    <button
                      style={{
                        ...styles.commentActionButton,
                        color: replyingToCommentId === reply.id ? '#000000' : '#64748b',
                      }}
                      onClick={() => onReply(reply.id, reply.user?.displayName || reply.user?.username || `用户${reply.userId}`)}
                    >
                      <MessageCircle size={14} />
                      <span>回复</span>
                    </button>
                    {(reply.userId === currentUserId || postAuthorId === currentUserId) && (
                      <button
                        style={{
                          ...styles.commentActionButton,
                          color: '#ef4444',
                        }}
                        onClick={() => {
                          if (window.confirm('确定要删除这条评论吗？')) {
                            onDelete(reply.id);
                          }
                        }}
                      >
                        <Trash2 size={14} />
                        <span>删除</span>
                      </button>
                    )}
                  </div>
                  
                  {replyingToCommentId === reply.id && (
                    <div style={styles.replyInputWrapper}>
                      <input
                        type="text"
                        placeholder={`回复 @${reply.user?.displayName || reply.user?.username || '用户'}...`}
                        style={styles.replyInput}
                        value={newCommentText}
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
                        <MessageCircle size={14} />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  commentItem: {
    display: 'flex',
    gap: '12px',
  },
  replyItem: {
    marginTop: '12px',
  },
  userAvatarSmall: {
    width: '32px',
    height: '32px',
    background: '#e2e8f0',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#475569',
    fontWeight: 'bold',
    fontSize: '12px',
    flexShrink: 0,
    cursor: 'pointer',
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
    cursor: 'pointer',
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
  replyInputWrapper: {
    display: 'flex',
    gap: '8px',
    marginTop: '8px',
    padding: '8px',
    background: '#f8fafc',
    borderRadius: '8px',
  },
  replyInput: {
    flex: 1,
    padding: '8px 12px',
    border: '1px solid #e2e8f0',
    borderRadius: '6px',
    fontSize: '14px',
  },
  replySubmitButton: {
    padding: '8px 12px',
    background: '#000000',
    border: '1px solid #000000',
    borderRadius: '6px',
    color: 'white',
    cursor: 'pointer',
  },
};

export default CommentItem;
