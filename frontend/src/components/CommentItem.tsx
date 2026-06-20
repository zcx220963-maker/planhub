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
  const hasReplies = comment.replies && comment.replies.length > 0;
  const canDelete = comment.userId === currentUserId || postAuthorId === currentUserId;
  const isTopLevel = level === 0;

  const handleDelete = () => {
    if (window.confirm('确定要删除这条评论吗？')) {
      onDelete(comment.id);
    }
  };

  const handleReplyClick = () => {
    // 如果有子评论并且是顶层评论，先展开/收起
    if (hasReplies && isTopLevel) {
      setExpanded(!expanded);
    }
    // 同时也触发回复
    onReply(comment.id, commentDisplayName);
  };

  const handleToggleExpand = (e: React.MouseEvent) => {
    e.stopPropagation(); // 阻止触发回复
    setExpanded(!expanded);
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
            {hasReplies && isTopLevel && (
              <button
                style={{
                  ...styles.commentActionButton,
                  color: '#64748b',
                }}
                onClick={handleToggleExpand}
              >
                {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>
            )}
            <button
              style={{
                ...styles.commentActionButton,
                color: replyingToCommentId === comment.id ? '#000000' : '#64748b',
              }}
              onClick={handleReplyClick}
            >
              <MessageCircle size={14} />
              <span>回复 ({comment.replyCount || 0})</span>
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
      {hasReplies && (isTopLevel ? expanded : true) && (
        <div style={{ paddingLeft: `${40 + level * 12}px` }}>
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
              newCommentText={newCommentText}
              onCommentChange={onCommentChange}
              navigate={navigate}
              getAvatarUrl={getAvatarUrl}
              parseMediaUrls={parseMediaUrls}
              replyingToCommentId={replyingToCommentId}
              level={level + 1}
            />
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
