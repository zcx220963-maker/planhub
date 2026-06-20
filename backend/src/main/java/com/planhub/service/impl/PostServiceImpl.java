package com.planhub.service.impl;

import com.planhub.dto.request.CreateCommentRequest;
import com.planhub.dto.request.CreatePostRequest;
import com.planhub.dto.response.PostDetailResponse;
import com.planhub.entity.Activity;
import com.planhub.entity.CommentInteraction;
import com.planhub.entity.Plan;
import com.planhub.entity.Post;
import com.planhub.entity.PostComment;
import com.planhub.entity.PostInteraction;
import com.planhub.entity.User;
import com.planhub.exception.BusinessException;
import com.planhub.exception.ResourceNotFoundException;
import com.planhub.entity.TrendingTopic;
import com.planhub.mapper.CommentInteractionMapper;
import com.planhub.mapper.PlanMapper;
import com.planhub.mapper.PostCommentMapper;
import com.planhub.mapper.PostInteractionMapper;
import com.planhub.mapper.PostMapper;
import com.planhub.mapper.TrendingTopicMapper;
import com.planhub.mapper.UserMapper;
import com.planhub.service.PostService;
import com.planhub.service.NotificationService;
import com.planhub.service.ActivityService;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class PostServiceImpl implements PostService {
    private final PostMapper postMapper;
    private final PostCommentMapper postCommentMapper;
    private final PostInteractionMapper postInteractionMapper;
    private final CommentInteractionMapper commentInteractionMapper;
    private final UserMapper userMapper;
    private final PlanMapper planMapper;
    private final TrendingTopicMapper trendingTopicMapper;
    private final ObjectMapper objectMapper;
    private final NotificationService notificationService;
    private final ActivityService activityService;

    @Override
    public Post create(Long userId, CreatePostRequest request) {
        // 验证内容或图片至少有一个不为空
        boolean hasContent = request.getContent() != null && !request.getContent().trim().isEmpty();
        boolean hasMedia = request.getMediaUrls() != null && !request.getMediaUrls().isEmpty();
        
        if (!hasContent && !hasMedia) {
            throw new BusinessException("内容或图片不能为空");
        }
        
        Post.PostBuilder postBuilder = Post.builder()
                .userId(userId)
                .content(hasContent ? request.getContent().trim() : "")
                .postType(request.getPostType().toUpperCase())
                .location(request.getLocation())
                .privacy(request.getPrivacy().toUpperCase());
        
        if (request.getLinkedPlanId() != null) {
            Plan plan = planMapper.selectById(request.getLinkedPlanId());
            if (plan == null) {
                throw new ResourceNotFoundException("计划", "id", request.getLinkedPlanId());
            }
            
            if (!plan.getUserId().equals(userId) && 
                !Plan.Visibility.PUBLIC.equals(plan.getVisibility())) {
                throw new BusinessException("只能关联自己的计划或公开的计划");
            }
            
            postBuilder.linkedPlanId(request.getLinkedPlanId());
        }

        Post post = postBuilder.build();

        if (request.getHashtags() != null) {
            try {
                post.setHashtags(objectMapper.writeValueAsString(request.getHashtags()));
            } catch (JsonProcessingException e) {
                throw new RuntimeException("Failed to serialize hashtags");
            }
        }

        if (request.getMentions() != null) {
            try {
                post.setMentions(objectMapper.writeValueAsString(request.getMentions()));
            } catch (JsonProcessingException e) {
                throw new RuntimeException("Failed to serialize mentions");
            }
        }

        if (request.getMediaUrls() != null) {
            try {
                post.setMediaUrls(objectMapper.writeValueAsString(request.getMediaUrls()));
            } catch (JsonProcessingException e) {
                throw new RuntimeException("Failed to serialize media urls");
            }
        }

        postMapper.insert(post);
        
        syncHashtagsToTopics(request.getHashtags());
        
        return post;
    }

    private void syncHashtagsToTopics(List<String> hashtags) {
        if (hashtags == null || hashtags.isEmpty()) {
            return;
        }
        
        for (String hashtag : hashtags) {
            String tagName = hashtag.startsWith("#") ? hashtag.substring(1) : hashtag;
            tagName = tagName.trim();
            
            if (tagName.isEmpty()) {
                continue;
            }
            
            Optional<TrendingTopic> existingTopic = trendingTopicMapper.selectByTagName(tagName);
            if (existingTopic.isEmpty()) {
                TrendingTopic newTopic = TrendingTopic.builder()
                        .tagName(tagName)
                        .displayName(tagName)
                        .topicType("hashtag")
                        .postCount(0)
                        .engagementScore(java.math.BigDecimal.ZERO)
                        .trendDirection("stable")
                        .lastUpdated(java.time.LocalDateTime.now())
                        .isFeatured(false)
                        .build();
                trendingTopicMapper.insert(newTopic);
                log.info("Created new topic from hashtag: {}", tagName);
            }
        }
    }

    @Override
    public Post share(Long userId, Long originalPostId, Long originalAuthorId, String content) {
        Post originalPost = getById(originalPostId);
        
        Post sharedPost = Post.builder()
                .userId(userId)
                .content(content != null && !content.isEmpty() ? content : "")
                .originalPostId(originalPostId)
                .originalAuthorId(originalAuthorId)
                .postType("TEXT")
                .privacy("PUBLIC")
                .build();

        postMapper.insert(sharedPost);
        
        if (!userId.equals(originalAuthorId)) {
            notificationService.createPostShareNotification(originalAuthorId, userId, originalPostId);
        }
        
        return sharedPost;
    }

    @Override
    public Post getById(Long postId) {
        Post post = postMapper.selectPostById(postId);
        if (post == null) {
            throw new ResourceNotFoundException("帖子", "id", postId);
        }
        return post;
    }

    @Override
    public IPage<Post> getAll(String type, String sort, int page, int size) {
        Page<Post> pageParam = new Page<>(page - 1, size);
        
        if (type != null && !type.isEmpty()) {
            return postMapper.selectByPrivacyAndContentContainingOrPrivacyAndHashtagsContaining(
                type.toUpperCase(),
                "",
                type.toUpperCase(),
                "",
                pageParam
            );
        }
        
        return postMapper.selectAllPostsPage(pageParam);
    }

    @Override
    public List<Post> getLatestPosts(int limit) {
        Page<Post> pageParam = new Page<>(1, limit);
        IPage<Post> result = postMapper.selectAllPostsPage(pageParam);
        return result.getRecords();
    }

    @Override
    public List<Post> getPopularPosts(int limit) {
        Page<Post> pageParam = new Page<>(1, limit);
        return postMapper.selectPopularPosts(pageParam);
    }
    
    @Override
    public int getLikeCount(Long postId) {
        return (int) postInteractionMapper.countByPostIdAndInteractionType(postId, "like");
    }
    
    @Override
    public int getCommentCount(Long postId) {
        return (int) postCommentMapper.countByPostId(postId);
    }
    
    @Override
    public List<PostComment> getAllComments(Long postId) {
        return postCommentMapper.selectByPostId(postId);
    }

    @Override
    public void like(Long postId, Long userId) {
        if (postInteractionMapper.existsByPostIdAndUserIdAndInteractionType(postId, userId, "like")) {
            throw new BusinessException("已点赞");
        }

        PostInteraction interaction = PostInteraction.builder()
                .postId(postId)
                .userId(userId)
                .interactionType("like")  // 数据库中存储的是小写
                .build();

        postInteractionMapper.insert(interaction);

        Post post = postMapper.selectById(postId);
        if (post != null) {
            activityService.createActivity(userId, "POST_LIKED", postId, "POST", post.getContent());
            
            if (!post.getUserId().equals(userId)) {
                notificationService.createPostLikeNotification(post.getUserId(), userId, postId);
            }
        }
    }

    @Override
    public void unlike(Long postId, Long userId) {
        Optional<PostInteraction> optInteraction = postInteractionMapper
                .findByPostIdAndUserIdAndInteractionType(postId, userId, "like");
        PostInteraction interaction = optInteraction.orElse(null);
        if (interaction == null) {
            throw new ResourceNotFoundException("点赞记录", "postId", postId);
        }
        
        postInteractionMapper.deleteById(interaction.getId());
    }

    @Override
    public void bookmark(Long postId, Long userId) {
        if (postInteractionMapper.existsByPostIdAndUserIdAndInteractionType(postId, userId, "BOOKMARK")) {
            throw new BusinessException("已收藏");
        }

        PostInteraction interaction = PostInteraction.builder()
                .postId(postId)
                .userId(userId)
                .interactionType("BOOKMARK")
                .build();

        postInteractionMapper.insert(interaction);
    }

    @Override
    public void unbookmark(Long postId, Long userId) {
        Optional<PostInteraction> optInteraction = postInteractionMapper
                .findByPostIdAndUserIdAndInteractionType(postId, userId, "BOOKMARK");
        PostInteraction interaction = optInteraction.orElse(null);
        if (interaction == null) {
            throw new ResourceNotFoundException("收藏记录", "postId", postId);
        }
        
        postInteractionMapper.deleteById(interaction.getId());
    }

    @Override
    public PostComment createComment(Long postId, Long userId, CreateCommentRequest request) {
        boolean hasContent = request.getContent() != null && !request.getContent().trim().isEmpty();
        boolean hasMedia = request.getMediaUrls() != null && !request.getMediaUrls().isEmpty();
        
        if (!hasContent && !hasMedia) {
            throw new BusinessException("内容或图片不能为空");
        }
        
        PostComment comment = PostComment.builder()
                .postId(postId)
                .userId(userId)
                .content(hasContent ? request.getContent().trim() : "")
                .parentCommentId(request.getParentCommentId())
                .likeCount(0)
                .replyCount(0)
                .build();

        if (request.getMentions() != null) {
            try {
                comment.setMentions(objectMapper.writeValueAsString(request.getMentions()));
            } catch (JsonProcessingException e) {
                throw new RuntimeException("Failed to serialize mentions");
            }
        }

        if (request.getMediaUrls() != null && !request.getMediaUrls().isEmpty()) {
            try {
                comment.setMediaUrls(objectMapper.writeValueAsString(request.getMediaUrls()));
            } catch (JsonProcessingException e) {
                throw new RuntimeException("Failed to serialize mediaUrls");
            }
        }

        postCommentMapper.insert(comment);

        Post post = postMapper.selectById(postId);
        
        if (request.getParentCommentId() != null) {
            PostComment parentComment = postCommentMapper.selectById(request.getParentCommentId());
            if (parentComment != null) {
                parentComment.setReplyCount(parentComment.getReplyCount() != null ? parentComment.getReplyCount() + 1 : 1);
                postCommentMapper.updateById(parentComment);
                
                activityService.createActivity(userId, "COMMENT_REPLIED", postId, "POST", request.getContent());
                
                if (!parentComment.getUserId().equals(userId)) {
                    notificationService.createCommentReplyNotification(parentComment.getUserId(), userId, comment.getId(), postId);
                }
            }
        } else {
            activityService.createActivity(userId, "POST_COMMENTED", postId, "POST", request.getContent());
            
            if (post != null && !post.getUserId().equals(userId)) {
                notificationService.createPostCommentNotification(post.getUserId(), userId, postId);
            }
        }

        return comment;
    }

    @Override
    public IPage<PostComment> getComments(Long postId, int page, int size) {
        Page<PostComment> pageParam = new Page<>(page, size);
        return postCommentMapper.selectByPostId(pageParam, postId);
    }
    
    @Override
    public int deleteComment(Long commentId, Long userId) {
        PostComment comment = postCommentMapper.selectById(commentId);
        if (comment == null) {
            throw new ResourceNotFoundException("评论", "id", commentId);
        }
        
        Post post = postMapper.selectById(comment.getPostId());
        if (post == null) {
            throw new ResourceNotFoundException("帖子", "id", comment.getPostId());
        }
        
        if (!comment.getUserId().equals(userId) && !post.getUserId().equals(userId)) {
            throw new BusinessException("没有权限删除此评论");
        }
        
        int deletedCount = 1;
        List<PostComment> childComments = postCommentMapper.selectByParentCommentId(commentId);
        for (PostComment child : childComments) {
            List<PostComment> grandChildComments = postCommentMapper.selectByParentCommentId(child.getId());
            deletedCount += 1 + grandChildComments.size();
            grandChildComments.forEach(grandChild -> postCommentMapper.deleteById(grandChild.getId()));
            postCommentMapper.deleteById(child.getId());
        }
        
        postCommentMapper.deleteById(comment.getId());
        
        if (comment.getParentCommentId() != null) {
            PostComment parentComment = postCommentMapper.selectById(comment.getParentCommentId());
            if (parentComment != null) {
                parentComment.setReplyCount(parentComment.getReplyCount() - 1);
                postCommentMapper.updateById(parentComment);
            }
        }
        
        return deletedCount;
    }
    
    @Override
    public boolean canDeleteComment(Long commentId, Long userId) {
        try {
            PostComment comment = postCommentMapper.selectById(commentId);
            if (comment == null) return false;
            
            Post post = postMapper.selectById(comment.getPostId());
            if (post == null) return false;
            
            return comment.getUserId().equals(userId) || post.getUserId().equals(userId);
        } catch (Exception e) {
            return false;
        }
    }
    
    @Override
    public User getUserById(Long userId) {
        return userMapper.selectById(userId);
    }
    
    @Override
    public Map<Long, User> getUsersByIds(Set<Long> userIds) {
        List<User> users = userMapper.selectBatchIds(userIds);
        return users.stream()
                .collect(Collectors.toMap(User::getId, u -> u));
    }
    
    @Override
    public List<Post> getPostsByIds(Set<Long> postIds) {
        return postMapper.selectBatchIds(new java.util.ArrayList<>(postIds));
    }
    
    @Override
    public boolean hasLiked(Long postId, Long userId) {
        return postInteractionMapper.existsByPostIdAndUserIdAndInteractionType(postId, userId, "like");
    }
    
    @Override
    public Map<Long, Boolean> getLikedPostsByUser(Long userId, List<Long> postIds) {
        List<PostInteraction> interactions = postInteractionMapper.findByUserIdAndPostIdInAndInteractionType(
            userId, postIds, "LIKE"
        );
        
        Map<Long, Boolean> likedMap = postIds.stream()
            .collect(Collectors.toMap(id -> id, id -> false));
        
        interactions.forEach(interaction -> likedMap.put(interaction.getPostId(), true));
        
        return likedMap;
    }
    
    @Override
    public IPage<Post> getPostsByHashtag(String hashtag, int page, int size) {
        Page<Post> pageParam = new Page<>(page, size);
        return postMapper.selectPostsByHashtag(hashtag, pageParam);
    }

    @Override
    public List<Post> getPostsByUserId(Long userId) {
        return postMapper.selectList(
            new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<Post>()
                .eq("user_id", userId)
                .orderByDesc("created_at")
        );
    }

    @Override
    public List<Post> getPostsByUserId(Long userId, String sort) {
        if ("hot".equalsIgnoreCase(sort)) {
            return postMapper.selectByUserIdOrderByHotDesc(userId);
        }
        return postMapper.selectList(
            new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<Post>()
                .eq("user_id", userId)
                .orderByDesc("created_at")
        );
    }

    @Override
    public void likeComment(Long commentId, Long userId) {
        if (commentInteractionMapper.existsByCommentIdAndUserId(commentId, userId)) {
            throw new BusinessException("已点赞");
        }

        CommentInteraction interaction = CommentInteraction.builder()
                .commentId(commentId)
                .userId(userId)
                .build();

        commentInteractionMapper.insert(interaction);

        PostComment comment = postCommentMapper.selectById(commentId);
        if (comment != null) {
            comment.setLikeCount(comment.getLikeCount() != null ? comment.getLikeCount() + 1 : 1);
            postCommentMapper.updateById(comment);
            
            if (!comment.getUserId().equals(userId)) {
                notificationService.createCommentLikeNotification(comment.getUserId(), userId, commentId, comment.getPostId());
            }
        }
    }

    @Override
    public void unlikeComment(Long commentId, Long userId) {
        Optional<CommentInteraction> optInteraction = commentInteractionMapper
                .findByCommentIdAndUserId(commentId, userId);
        CommentInteraction interaction = optInteraction.orElse(null);
        if (interaction == null) {
            throw new ResourceNotFoundException("点赞记录", "commentId", commentId);
        }

        commentInteractionMapper.deleteById(interaction.getId());

        PostComment comment = postCommentMapper.selectById(commentId);
        if (comment != null) {
            comment.setLikeCount(comment.getLikeCount() != null && comment.getLikeCount() > 0 ? comment.getLikeCount() - 1 : 0);
            postCommentMapper.updateById(comment);
        }
    }

    @Override
    public boolean hasLikedComment(Long commentId, Long userId) {
        return commentInteractionMapper.existsByCommentIdAndUserId(commentId, userId);
    }

    @Override
    public int getCommentLikeCount(Long commentId) {
        return (int) commentInteractionMapper.countByCommentId(commentId);
    }

    @Override
    public Map<Long, Boolean> getLikedCommentsByUser(Long userId, List<Long> commentIds) {
        List<CommentInteraction> interactions = commentInteractionMapper.findByUserIdAndCommentIdIn(userId, commentIds);

        Map<Long, Boolean> likedMap = commentIds.stream()
            .collect(Collectors.toMap(id -> id, id -> false));

        interactions.forEach(interaction -> likedMap.put(interaction.getCommentId(), true));

        return likedMap;
    }

    @Override
    public PostComment getCommentById(Long commentId) {
        PostComment comment = postCommentMapper.selectById(commentId);
        if (comment == null) {
            throw new ResourceNotFoundException("评论", "id", commentId);
        }
        return comment;
    }

    @Override
    public int getReplyCount(Long commentId) {
        return (int) postCommentMapper.countByParentCommentId(commentId);
    }

    @Override
    public List<String> getTopTrendingHashtags() {
        List<Post> posts = postMapper.selectAllWithHashtags();
        Map<String, Integer> hashtagCount = new HashMap<>();
        
        for (Post post : posts) {
            try {
                @SuppressWarnings("unchecked")
                List<String> hashtags = objectMapper.readValue(post.getHashtags(), List.class);
                for (String hashtag : hashtags) {
                    if (hashtag != null && !hashtag.trim().isEmpty()) {
                        hashtagCount.merge(hashtag.trim(), 1, Integer::sum);
                    }
                }
            } catch (Exception e) {
                log.error("Failed to parse hashtags for post: {}", post.getId(), e);
            }
        }
        
        return hashtagCount.entrySet().stream()
                .sorted((e1, e2) -> e2.getValue().compareTo(e1.getValue()))
                .limit(5)
                .map(Map.Entry::getKey)
                .collect(Collectors.toList());
    }

    @Override
    @Transactional
    public void delete(Long postId, Long userId) {
        Post post = getById(postId);
        
        if (!post.getUserId().equals(userId)) {
            throw new BusinessException("只能删除自己发布的帖子");
        }
        
        postInteractionMapper.deleteByPostId(postId);
        
        postCommentMapper.deleteByPostId(postId);
        
        postMapper.deleteById(postId);
    }
    
    @Override
    public PostDetailResponse.PlanInfoResponse buildPlanInfoResponse(Plan plan) {
        if (plan == null) return null;
        
        User owner = userMapper.selectUserById(plan.getUserId());
        
        PostDetailResponse.UserResponse ownerResponse = owner != null ?
            PostDetailResponse.UserResponse.builder()
                .id(owner.getId())
                .username(owner.getUsername())
                .displayName(owner.getDisplayName())
                .avatarUrl(owner.getAvatarUrl())
                .build() : null;
        
        return PostDetailResponse.PlanInfoResponse.builder()
                .id(plan.getId())
                .title(plan.getTitle())
                .description(plan.getDescription())
                .category(plan.getCategory() != null ? plan.getCategory().name() : null)
                .status(plan.getStatus() != null ? plan.getStatus().name() : null)
                .progressPercentage(plan.getProgressPercentage())
                .coverImageUrl(plan.getCoverImageUrl())
                .createdAt(plan.getCreatedAt())
                .owner(ownerResponse)
                .build();
    }
}
