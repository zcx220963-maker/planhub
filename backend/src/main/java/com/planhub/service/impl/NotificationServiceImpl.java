package com.planhub.service.impl;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.planhub.entity.Notification;
import com.planhub.entity.User;
import com.planhub.exception.ResourceNotFoundException;
import com.planhub.mapper.NotificationMapper;
import com.planhub.mapper.UserMapper;
import com.planhub.service.NotificationService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
@Slf4j
public class NotificationServiceImpl implements NotificationService {
    private final NotificationMapper notificationMapper;
    private final UserMapper userMapper;

    @Override
    public IPage<Notification> getNotifications(Long userId, int page, int size) {
        Page<Notification> pageParam = new Page<>(page - 1, size);
        return notificationMapper.selectByUserIdOrderByCreatedAtDesc(userId, pageParam);
    }

    @Override
    public long getUnreadCount(Long userId) {
        return notificationMapper.countByUserIdAndIsRead(userId, false);
    }

    @Override
    @Transactional
    public void markAsRead(Long notificationId, Long userId) {
        Notification notification = notificationMapper.selectById(notificationId);
        if (notification == null) {
            throw new ResourceNotFoundException("通知", "id", notificationId);
        }
        
        if (!notification.getUserId().equals(userId)) {
            throw new SecurityException("无权访问此通知");
        }
        
        notificationMapper.markAsRead(notificationId);
    }

    @Override
    @Transactional
    public void markAllAsRead(Long userId) {
        notificationMapper.markAllAsRead(userId);
    }

    @Override
    @Transactional
    public void deleteNotification(Long notificationId, Long userId) {
        Notification notification = notificationMapper.selectById(notificationId);
        if (notification == null) {
            throw new ResourceNotFoundException("通知", "id", notificationId);
        }
        
        if (!notification.getUserId().equals(userId)) {
            throw new SecurityException("无权删除此通知");
        }
        
        notificationMapper.deleteById(notificationId);
    }
    
    @Override
    @Transactional
    public void markMultipleAsRead(List<Long> notificationIds, Long userId) {
        if (notificationIds == null || notificationIds.isEmpty()) {
            return;
        }
        notificationMapper.markMultipleAsRead(notificationIds, userId);
    }
    
    @Override
    @Transactional
    public void deleteMultipleNotifications(List<Long> notificationIds, Long userId) {
        if (notificationIds == null || notificationIds.isEmpty()) {
            return;
        }
        notificationMapper.deleteMultipleNotifications(notificationIds, userId);
    }

    @Override
    @Transactional
    public Notification createPostLikeNotification(Long postAuthorId, Long likerId, Long postId) {
        User liker = userMapper.selectById(likerId);
        String content = liker != null ? liker.getDisplayName() + " 点赞了你的帖子" : "有人点赞了你的帖子";
        
        Notification notification = Notification.builder()
                .userId(postAuthorId)
                .targetUserId(likerId)
                .postId(postId)
                .type(Notification.TYPE_POST_LIKE)
                .content(content)
                .isRead(false)
                .build();
        
        notificationMapper.insert(notification);
        return notification;
    }

    @Override
    @Transactional
    public Notification createPostCommentNotification(Long postAuthorId, Long commenterId, Long postId) {
        User commenter = userMapper.selectById(commenterId);
        String content = commenter != null ? commenter.getDisplayName() + " 评论了你的帖子" : "有人评论了你的帖子";
        
        Notification notification = Notification.builder()
                .userId(postAuthorId)
                .targetUserId(commenterId)
                .postId(postId)
                .type(Notification.TYPE_POST_COMMENT)
                .content(content)
                .isRead(false)
                .build();
        
        notificationMapper.insert(notification);
        return notification;
    }

    @Override
    @Transactional
    public Notification createCommentLikeNotification(Long commentAuthorId, Long likerId, Long commentId, Long postId) {
        User liker = userMapper.selectById(likerId);
        String content = liker != null ? liker.getDisplayName() + " 点赞了你的评论" : "有人点赞了你的评论";
        
        Notification notification = Notification.builder()
                .userId(commentAuthorId)
                .targetUserId(likerId)
                .postId(postId)
                .commentId(commentId)
                .type(Notification.TYPE_COMMENT_LIKE)
                .content(content)
                .isRead(false)
                .build();
        
        notificationMapper.insert(notification);
        return notification;
    }

    @Override
    @Transactional
    public Notification createCommentReplyNotification(Long parentCommentAuthorId, Long replierId, Long commentId, Long postId) {
        User replier = userMapper.selectById(replierId);
        String content = replier != null ? replier.getDisplayName() + " 回复了你的评论" : "有人回复了你的评论";
        
        Notification notification = Notification.builder()
                .userId(parentCommentAuthorId)
                .targetUserId(replierId)
                .postId(postId)
                .commentId(commentId)
                .type(Notification.TYPE_COMMENT_REPLY)
                .content(content)
                .isRead(false)
                .build();
        
        notificationMapper.insert(notification);
        return notification;
    }

    @Override
    @Transactional
    public Notification createPostShareNotification(Long postAuthorId, Long sharerId, Long originalPostId) {
        User sharer = userMapper.selectById(sharerId);
        String content = sharer != null ? sharer.getDisplayName() + " 转发了你的帖子" : "有人转发了你的帖子";
        
        Notification notification = Notification.builder()
                .userId(postAuthorId)
                .targetUserId(sharerId)
                .postId(originalPostId)
                .type(Notification.TYPE_POST_SHARE)
                .content(content)
                .isRead(false)
                .build();
        
        notificationMapper.insert(notification);
        return notification;
    }
}
