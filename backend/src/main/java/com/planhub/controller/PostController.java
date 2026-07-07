package com.planhub.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.planhub.dto.request.CreateCommentRequest;
import com.planhub.dto.request.CreatePostRequest;
import com.planhub.dto.request.SharePostRequest;
import com.planhub.dto.response.ApiResponse;
import com.planhub.dto.response.PostDetailResponse;
import com.planhub.entity.Plan;
import com.planhub.entity.Post;
import com.planhub.entity.PostComment;
import com.planhub.entity.User;
import com.planhub.mapper.PlanMapper;
import com.planhub.service.PostService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/posts")
public class PostController {
    private final PostService postService;
    private final PlanMapper planMapper;

    public PostController(PostService postService, PlanMapper planMapper) {
        this.postService = postService;
        this.planMapper = planMapper;
    }

    @GetMapping
    public ResponseEntity<ApiResponse<List<PostDetailResponse>>> getPosts(
            @RequestParam(required = false) String type,
            @RequestParam(defaultValue = "newest") String sort,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            Authentication authentication) {
        IPage<Post> posts = postService.getAll(type, sort, page, size);
        
        Set<Long> userIds = posts.getRecords().stream()
                .map(Post::getUserId)
                .collect(Collectors.toSet());
        Map<Long, User> userMap = postService.getUsersByIds(userIds);
        
        List<Long> postIds = posts.getRecords().stream()
                .map(Post::getId)
                .collect(Collectors.toList());
        
        final Map<Long, Boolean> likedMapFinal;
        if (authentication != null && authentication.getPrincipal() != null) {
            Long userId = (Long) authentication.getPrincipal();
            likedMapFinal = postService.getLikedPostsByUser(userId, postIds);
        } else {
            likedMapFinal = null;
        }
        
        List<PostDetailResponse> responses = buildPostResponses(posts.getRecords(), userMap, likedMapFinal);
        return ResponseEntity.ok(ApiResponse.success(responses));
    }

    @GetMapping("/latest")
    public ResponseEntity<ApiResponse<List<PostDetailResponse>>> getLatestPosts(
            @RequestParam(defaultValue = "10") int limit,
            Authentication authentication) {
        List<Post> posts = postService.getLatestPosts(limit);
        
        Set<Long> userIds = posts.stream()
                .map(Post::getUserId)
                .collect(Collectors.toSet());
        Map<Long, User> userMap = postService.getUsersByIds(userIds);
        
        List<Long> postIds = posts.stream()
                .map(Post::getId)
                .collect(Collectors.toList());
        
        final Map<Long, Boolean> likedMapFinal;
        if (authentication != null && authentication.getPrincipal() != null) {
            Long userId = (Long) authentication.getPrincipal();
            likedMapFinal = postService.getLikedPostsByUser(userId, postIds);
        } else {
            likedMapFinal = null;
        }
        
        List<PostDetailResponse> responses = buildPostResponses(posts, userMap, likedMapFinal);
        return ResponseEntity.ok(ApiResponse.success(responses));
    }

    @GetMapping("/popular")
    public ResponseEntity<ApiResponse<List<PostDetailResponse>>> getPopularPosts(
            @RequestParam(defaultValue = "10") int limit,
            Authentication authentication) {
        List<Post> posts = postService.getPopularPosts(limit);
        
        Set<Long> userIds = posts.stream()
                .map(Post::getUserId)
                .collect(Collectors.toSet());
        Map<Long, User> userMap = postService.getUsersByIds(userIds);
        
        List<Long> postIds = posts.stream()
                .map(Post::getId)
                .collect(Collectors.toList());
        
        final Map<Long, Boolean> likedMapFinal;
        if (authentication != null && authentication.getPrincipal() != null) {
            Long userId = (Long) authentication.getPrincipal();
            likedMapFinal = postService.getLikedPostsByUser(userId, postIds);
        } else {
            likedMapFinal = null;
        }
        
        List<PostDetailResponse> responses = buildPostResponses(posts, userMap, likedMapFinal);
        return ResponseEntity.ok(ApiResponse.success(responses));
    }
    
    private List<PostDetailResponse> buildPostResponses(List<Post> posts, Map<Long, User> userMap, Map<Long, Boolean> likedMapFinal) {
        Set<Long> originalPostIds = posts.stream()
                .filter(p -> p.getOriginalPostId() != null)
                .map(Post::getOriginalPostId)
                .collect(Collectors.toSet());
        
        Map<Long, Post> originalPostMap = originalPostIds.isEmpty() ? new java.util.HashMap<>() : 
            postService.getPostsByIds(originalPostIds).stream()
                .collect(Collectors.toMap(Post::getId, p -> p));
        
        Set<Long> originalAuthorIds = originalPostMap.values().stream()
                .map(Post::getUserId)
                .collect(Collectors.toSet());
        
        Map<Long, User> originalAuthorMap = originalAuthorIds.isEmpty() ? new java.util.HashMap<>() :
            postService.getUsersByIds(originalAuthorIds);
        
        // 获取关联计划信息
        Set<Long> linkedPlanIds = posts.stream()
                .filter(p -> p.getLinkedPlanId() != null)
                .map(Post::getLinkedPlanId)
                .collect(Collectors.toSet());
        
        Map<Long, Plan> linkedPlanMap = linkedPlanIds.isEmpty() ? new java.util.HashMap<>() :
            planMapper.selectBatchIds(new java.util.ArrayList<>(linkedPlanIds)).stream()
                .collect(Collectors.toMap(Plan::getId, p -> p));
        
        return posts.stream()
                .map(post -> {
                    Post originalPost = post.getOriginalPostId() != null ? 
                        originalPostMap.get(post.getOriginalPostId()) : null;
                    User originalAuthor = originalPost != null ? 
                        originalAuthorMap.get(originalPost.getUserId()) : null;
                    
                    int originalPostLikes = originalPost != null ? 
                        postService.getLikeCount(originalPost.getId()) : 0;
                    int originalPostCommentsCount = originalPost != null ? 
                        postService.getCommentCount(originalPost.getId()) : 0;
                    
                    Plan linkedPlan = post.getLinkedPlanId() != null ? 
                        linkedPlanMap.get(post.getLinkedPlanId()) : null;
                    
                    PostDetailResponse.PostDetailResponseBuilder builder = PostDetailResponse.fromEntity(
                            post,
                            postService.getLikeCount(post.getId()),
                            postService.getCommentCount(post.getId()),
                            null,
                            userMap.get(post.getUserId()),
                            null,
                            likedMapFinal != null ? likedMapFinal.get(post.getId()) : null,
                            originalPost,
                            originalAuthor,
                            originalPostLikes,
                            originalPostCommentsCount
                    ).toBuilder();
                    
                    if (post.getLinkedPlanId() != null) {
                        builder.linkedPlanId(post.getLinkedPlanId());
                    }
                    
                    if (linkedPlan != null) {
                        PostDetailResponse.PlanInfoResponse planInfo = postService.buildPlanInfoResponse(linkedPlan);
                        builder.linkedPlan(planInfo);
                    }
                    
                    return builder.build();
                })
                .collect(Collectors.toList());
    }

    @GetMapping("/{postId}")
    public ResponseEntity<ApiResponse<PostDetailResponse>> getPostById(
            @PathVariable Long postId,
            Authentication authentication) {
        Post post = postService.getById(postId);
        if (post == null) {
            return ResponseEntity.notFound().build();
        }
        List<PostComment> comments = postService.getAllComments(postId);
        
        Set<Long> userIds = new java.util.HashSet<>();
        userIds.add(post.getUserId());
        userIds.addAll(comments.stream().map(PostComment::getUserId).toList());
        Map<Long, User> userMap = postService.getUsersByIds(userIds);
        
        Boolean liked = null;
        if (authentication != null && authentication.getPrincipal() != null) {
            Long userId = (Long) authentication.getPrincipal();
            liked = postService.hasLiked(postId, userId);
        }
        
        // 填充关联计划信息
        PostDetailResponse.PlanInfoResponse planInfo = null;
        if (post.getLinkedPlanId() != null) {
            Plan linkedPlan = planMapper.selectPlanById(post.getLinkedPlanId());
            if (linkedPlan != null) {
                planInfo = postService.buildPlanInfoResponse(linkedPlan);
            }
        }
        
        PostDetailResponse response = PostDetailResponse.fromEntity(
                post,
                postService.getLikeCount(postId),
                postService.getCommentCount(postId),
                comments,
                userMap.get(post.getUserId()),
                new ArrayList<>(userMap.values()),
                liked,
                null,
                null,
                0,
                0,
                planInfo
        );
        
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @PostMapping
    public ResponseEntity<ApiResponse<PostDetailResponse>> createPost(
            Authentication authentication,
            @Valid @RequestBody CreatePostRequest request) {
        Long userId = (Long) authentication.getPrincipal();
        Post post = postService.create(userId, request);
        User postUser = postService.getUserById(userId);
        
        // 填充关联计划信息
        PostDetailResponse.PlanInfoResponse planInfo = null;
        if (post.getLinkedPlanId() != null) {
            Plan linkedPlan = planMapper.selectPlanById(post.getLinkedPlanId());
            if (linkedPlan != null) {
                planInfo = postService.buildPlanInfoResponse(linkedPlan);
            }
        }
        
        PostDetailResponse response = PostDetailResponse.fromEntity(
                post, 0, 0, null, postUser, null, false,
                null, null, 0, 0, planInfo
        );
        
        return ResponseEntity.ok(ApiResponse.success(response, "帖子发布成功"));
    }

    @PostMapping("/{postId}/share")
    public ResponseEntity<ApiResponse<PostDetailResponse>> sharePost(
            Authentication authentication,
            @PathVariable Long postId,
            @RequestBody SharePostRequest request) {
        Long userId = (Long) authentication.getPrincipal();
        Post sharedPost = postService.share(userId, postId, request.getOriginalAuthorId(), request.getContent());
        User postUser = postService.getUserById(userId);
        
        Post originalPost = postService.getById(postId);
        User originalAuthor = originalPost != null ? postService.getUserById(request.getOriginalAuthorId()) : null;
        
        PostDetailResponse response = PostDetailResponse.fromEntity(
                sharedPost, 0, 0, null, postUser, null, false,
                originalPost, originalAuthor, 0, 0, null
        );
        
        return ResponseEntity.ok(ApiResponse.success(response, "分享成功"));
    }

    @PostMapping("/{postId}/like")
    public ResponseEntity<ApiResponse<LikeResponse>> likePost(
            Authentication authentication,
            @PathVariable Long postId) {
        Long userId = (Long) authentication.getPrincipal();
        postService.like(postId, userId);
        int likes = postService.getLikeCount(postId);
        return ResponseEntity.ok(ApiResponse.success(new LikeResponse(likes), "点赞成功"));
    }

    @DeleteMapping("/{postId}/like")
    public ResponseEntity<ApiResponse<LikeResponse>> unlikePost(
            Authentication authentication,
            @PathVariable Long postId) {
        Long userId = (Long) authentication.getPrincipal();
        postService.unlike(postId, userId);
        int likes = postService.getLikeCount(postId);
        return ResponseEntity.ok(ApiResponse.success(new LikeResponse(likes), "取消点赞成功"));
    }

    @PostMapping("/{postId}/comments")
    public ResponseEntity<ApiResponse<PostDetailResponse.CommentResponse>> createComment(
            Authentication authentication,
            @PathVariable Long postId,
            @Valid @RequestBody CreateCommentRequest request) {
        Long userId = (Long) authentication.getPrincipal();
        PostComment comment = postService.createComment(postId, userId, request);
        User commentUser = postService.getUserById(userId);
        
        PostDetailResponse.CommentResponse response = PostDetailResponse.CommentResponse.builder()
                .id(comment.getId())
                .postId(comment.getPostId())
                .userId(comment.getUserId())
                .parentCommentId(comment.getParentCommentId())
                .content(comment.getContent())
                .mediaUrls(comment.getMediaUrls())
                .createdAt(comment.getCreatedAt())
                .updatedAt(comment.getUpdatedAt())
                .likeCount(comment.getLikeCount() != null ? comment.getLikeCount() : 0)
                .replyCount(comment.getReplyCount() != null ? comment.getReplyCount() : 0)
                .liked(false)
                .user(commentUser != null ? PostDetailResponse.UserResponse.builder()
                        .id(commentUser.getId())
                        .username(commentUser.getUsername())
                        .displayName(commentUser.getDisplayName())
                        .avatarUrl(commentUser.getAvatarUrl())
                        .build() : null)
                .build();
        return ResponseEntity.ok(ApiResponse.success(response, "评论成功"));
    }

    @GetMapping("/{postId}/comments")
    public ResponseEntity<ApiResponse<List<PostDetailResponse.CommentResponse>>> getComments(
            @PathVariable Long postId,
            Authentication authentication) {
        try {
            List<PostComment> comments = postService.getAllComments(postId);
            
            if (comments == null || comments.isEmpty()) {
                return ResponseEntity.ok(ApiResponse.success(new java.util.ArrayList<>()));
            }
            
            Set<Long> userIds = comments.stream()
                    .map(PostComment::getUserId)
                    .collect(Collectors.toSet());
            Map<Long, User> userMap = userIds.isEmpty() ? new java.util.HashMap<>() : postService.getUsersByIds(userIds);
            
            final Map<Long, Boolean> likedMap = new java.util.HashMap<>();
            if (authentication != null && authentication.getPrincipal() != null) {
                try {
                    Long userId = (Long) authentication.getPrincipal();
                    List<Long> commentIds = comments.stream()
                            .map(PostComment::getId)
                            .collect(Collectors.toList());
                    for (Long commentId : commentIds) {
                        try {
                            likedMap.put(commentId, postService.hasLikedComment(commentId, userId));
                        } catch (Exception e) {
                            likedMap.put(commentId, false);
                        }
                    }
                } catch (Exception e) {
                    // 忽略点赞状态查询错误
                }
            } else {
                comments.forEach(c -> likedMap.put(c.getId(), false));
            }
            
            List<PostDetailResponse.CommentResponse> responses = comments.stream()
                    .map(c -> {
                        User commentUser = userMap.get(c.getUserId());
                        return PostDetailResponse.CommentResponse.builder()
                                .id(c.getId())
                                .postId(c.getPostId())
                                .userId(c.getUserId())
                                .parentCommentId(c.getParentCommentId())
                                .content(c.getContent())
                                .mediaUrls(c.getMediaUrls())
                                .createdAt(c.getCreatedAt())
                                .updatedAt(c.getUpdatedAt())
                                .likeCount(c.getLikeCount() != null ? c.getLikeCount() : 0)
                                .replyCount(c.getReplyCount() != null ? c.getReplyCount() : 0)
                                .liked(likedMap.getOrDefault(c.getId(), false))
                                .user(commentUser != null ? PostDetailResponse.UserResponse.builder()
                                        .id(commentUser.getId())
                                        .username(commentUser.getUsername())
                                        .displayName(commentUser.getDisplayName())
                                        .avatarUrl(commentUser.getAvatarUrl())
                                        .build() : null)
                                .build();
                    })
                    .collect(Collectors.toList());
            return ResponseEntity.ok(ApiResponse.success(responses));
        } catch (Exception e) {
            e.printStackTrace();
            return ResponseEntity.ok(ApiResponse.success(new java.util.ArrayList<>()));
        }
    }

    @DeleteMapping("/{postId}")
    public ResponseEntity<ApiResponse<Void>> deletePost(
            Authentication authentication,
            @PathVariable Long postId) {
        Long userId = (Long) authentication.getPrincipal();
        postService.delete(postId, userId);
        return ResponseEntity.ok(ApiResponse.success(null, "删除成功"));
    }

    @GetMapping("/comments/{commentId}/post")
    public ResponseEntity<ApiResponse<Long>> getPostIdByCommentId(
            @PathVariable Long commentId) {
        PostComment comment = postService.getCommentById(commentId);
        return ResponseEntity.ok(ApiResponse.success(comment.getPostId()));
    }

    @PostMapping("/comments/{commentId}/like")
    public ResponseEntity<ApiResponse<LikeResponse>> likeComment(
            Authentication authentication,
            @PathVariable Long commentId) {
        Long userId = (Long) authentication.getPrincipal();
        postService.likeComment(commentId, userId);
        int likes = postService.getCommentLikeCount(commentId);
        return ResponseEntity.ok(ApiResponse.success(new LikeResponse(likes), "评论点赞成功"));
    }

    @DeleteMapping("/comments/{commentId}/like")
    public ResponseEntity<ApiResponse<LikeResponse>> unlikeComment(
            Authentication authentication,
            @PathVariable Long commentId) {
        Long userId = (Long) authentication.getPrincipal();
        postService.unlikeComment(commentId, userId);
        int likes = postService.getCommentLikeCount(commentId);
        return ResponseEntity.ok(ApiResponse.success(new LikeResponse(likes), "取消评论点赞成功"));
    }

    @DeleteMapping("/comments/{commentId}")
    public ResponseEntity<ApiResponse<DeleteCommentResponse>> deleteComment(
            Authentication authentication,
            @PathVariable Long commentId) {
        Long userId = (Long) authentication.getPrincipal();
        int deletedCount = postService.deleteComment(commentId, userId);
        return ResponseEntity.ok(ApiResponse.success(new DeleteCommentResponse(deletedCount), "删除评论成功"));
    }
    
    public static class DeleteCommentResponse {
        private int deletedCount;
        
        public DeleteCommentResponse(int deletedCount) {
            this.deletedCount = deletedCount;
        }
        
        public int getDeletedCount() {
            return deletedCount;
        }
    }

    @GetMapping("/hashtag/{hashtag}")
    public ResponseEntity<ApiResponse<List<PostDetailResponse>>> getPostsByHashtag(
            @PathVariable String hashtag,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            Authentication authentication) {
        IPage<Post> posts = postService.getPostsByHashtag(hashtag, page, size);
        
        Set<Long> userIds = posts.getRecords().stream()
                .map(Post::getUserId)
                .collect(Collectors.toSet());
        Map<Long, User> userMap = postService.getUsersByIds(userIds);
        
        List<Long> postIds = posts.getRecords().stream()
                .map(Post::getId)
                .collect(Collectors.toList());
        
        final Map<Long, Boolean> likedMapFinal;
        if (authentication != null && authentication.getPrincipal() != null) {
            Long userId = (Long) authentication.getPrincipal();
            likedMapFinal = postService.getLikedPostsByUser(userId, postIds);
        } else {
            likedMapFinal = null;
        }
        
        // 获取关联计划信息
        Set<Long> linkedPlanIds = posts.getRecords().stream()
                .filter(p -> p.getLinkedPlanId() != null)
                .map(Post::getLinkedPlanId)
                .collect(Collectors.toSet());
        
        Map<Long, Plan> linkedPlanMap = linkedPlanIds.isEmpty() ? new java.util.HashMap<>() :
            planMapper.selectBatchIds(new java.util.ArrayList<>(linkedPlanIds)).stream()
                .collect(Collectors.toMap(Plan::getId, p -> p));
        
        List<PostDetailResponse> responses = posts.getRecords().stream()
                .map(post -> {
                    PostDetailResponse.PostDetailResponseBuilder builder = PostDetailResponse.fromEntity(
                            post,
                            postService.getLikeCount(post.getId()),
                            postService.getCommentCount(post.getId()),
                            null,
                            userMap.get(post.getUserId()),
                            null,
                            likedMapFinal != null ? likedMapFinal.get(post.getId()) : null
                    ).toBuilder();
                    
                    if (post.getLinkedPlanId() != null) {
                        builder.linkedPlanId(post.getLinkedPlanId());
                        Plan linkedPlan = linkedPlanMap.get(post.getLinkedPlanId());
                        if (linkedPlan != null) {
                            PostDetailResponse.PlanInfoResponse planInfo = postService.buildPlanInfoResponse(linkedPlan);
                            builder.linkedPlan(planInfo);
                        }
                    }
                    
                    return builder.build();
                })
                .collect(Collectors.toList());
        return ResponseEntity.ok(ApiResponse.success(responses));
    }

    @GetMapping("/trending/hashtags")
    public ResponseEntity<ApiResponse<List<String>>> getTrendingHashtags() {
        List<String> hashtags = postService.getTopTrendingHashtags();
        return ResponseEntity.ok(ApiResponse.success(hashtags));
    }

    @GetMapping("/user/{userId}")
    public ResponseEntity<ApiResponse<List<PostDetailResponse>>> getPostsByUserId(
            @PathVariable Long userId,
            @RequestParam(defaultValue = "time") String sort,
            Authentication authentication) {
        List<Post> posts = postService.getPostsByUserId(userId, sort);

        Set<Long> userIds = posts.stream()
                .map(Post::getUserId)
                .collect(Collectors.toSet());
        Map<Long, User> userMap = postService.getUsersByIds(userIds);

        List<Long> postIds = posts.stream()
                .map(Post::getId)
                .collect(Collectors.toList());

        final Map<Long, Boolean> likedMapFinal;
        if (authentication != null && authentication.getPrincipal() != null) {
            Long currentUserId = (Long) authentication.getPrincipal();
            likedMapFinal = postService.getLikedPostsByUser(currentUserId, postIds);
        } else {
            likedMapFinal = null;
        }

        List<PostDetailResponse> responses = buildPostResponses(posts, userMap, likedMapFinal);
        return ResponseEntity.ok(ApiResponse.success(responses));
    }

    public static class LikeResponse {
        private int likes;

        public LikeResponse(int likes) {
            this.likes = likes;
        }

        public int getLikes() {
            return likes;
        }

        public void setLikes(int likes) {
            this.likes = likes;
        }
    }
}
