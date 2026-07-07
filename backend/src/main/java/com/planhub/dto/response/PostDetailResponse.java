package com.planhub.dto.response;

import com.planhub.entity.Post;
import com.planhub.entity.PostComment;
import com.planhub.entity.User;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Data
@Builder(toBuilder = true)
@NoArgsConstructor
@AllArgsConstructor
public class PostDetailResponse {
    private Long id;
    private Long userId;
    private String content;
    private String postType;
    private String mediaUrls;
    private String hashtags;
    private String mentions;
    private String location;
    private String privacy;
    private Integer viewCount;
    private Integer likes;
    private Integer commentsCount;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private List<CommentResponse> comments;
    private UserResponse user;
    private Boolean liked;
    private Long originalPostId;
    private Long originalAuthorId;
    private PostDetailResponse originalPost;
    private UserResponse originalAuthor;
    private Long linkedPlanId;
    private PlanInfoResponse linkedPlan;
    
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PlanInfoResponse {
        private Long id;
        private String title;
        private String description;
        private String category;
        private String status;
        private java.math.BigDecimal progressPercentage;
        private String coverImageUrl;
        private LocalDateTime createdAt;
        private UserResponse owner;
    }
    
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class UserResponse {
        private Long id;
        private String username;
        private String displayName;
        private String avatarUrl;
    }
    
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CommentResponse {
        private Long id;
        private Long postId;
        private Long userId;
        private Long parentCommentId;
        private String content;
        private String mediaUrls;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;
        private Integer likeCount;
        private Integer replyCount;
        private Boolean liked;
        private UserResponse user;
    }
    
    public static PostDetailResponse fromEntity(Post post, int likes, int commentsCount, List<PostComment> comments, User postUser, List<User> commentUsers, Boolean liked) {
        return fromEntity(post, likes, commentsCount, comments, postUser, commentUsers, liked, null, null, 0, 0);
    }
    
    public static PostDetailResponse fromEntity(Post post, int likes, int commentsCount, List<PostComment> comments, User postUser, List<User> commentUsers, Boolean liked, Post originalPost, User originalAuthor, int originalPostLikes, int originalPostCommentsCount) {
        return fromEntity(post, likes, commentsCount, comments, postUser, commentUsers, liked, originalPost, originalAuthor, originalPostLikes, originalPostCommentsCount, null);
    }
    
    public static PostDetailResponse fromEntity(Post post, int likes, int commentsCount, List<PostComment> comments, User postUser, List<User> commentUsers, Boolean liked, Post originalPost, User originalAuthor, int originalPostLikes, int originalPostCommentsCount, PlanInfoResponse linkedPlanInfo) {
        List<CommentResponse> commentResponses = comments != null ? 
            comments.stream()
                .map(c -> {
                    User commentUser = commentUsers != null ? 
                        commentUsers.stream().filter(u -> u.getId().equals(c.getUserId())).findFirst().orElse(null) : null;
                    return CommentResponse.builder()
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
                        .liked(false)
                        .user(commentUser != null ? UserResponse.builder()
                            .id(commentUser.getId())
                            .username(commentUser.getUsername())
                            .displayName(commentUser.getDisplayName())
                            .avatarUrl(commentUser.getAvatarUrl())
                            .build() : null)
                        .build();
                })
                .collect(Collectors.toList()) : null;
        
        UserResponse userResponse = postUser != null ? 
            UserResponse.builder()
                .id(postUser.getId())
                .username(postUser.getUsername())
                .displayName(postUser.getDisplayName())
                .avatarUrl(postUser.getAvatarUrl())
                .build() : null;
        
        PostDetailResponse.PostDetailResponseBuilder builder = PostDetailResponse.builder()
                .id(post.getId())
                .userId(post.getUserId())
                .content(post.getContent())
                .postType(post.getPostType() != null ? post.getPostType() : "TEXT")
                .mediaUrls(post.getMediaUrls())
                .hashtags(post.getHashtags())
                .mentions(post.getMentions())
                .location(post.getLocation())
                .privacy(post.getPrivacy() != null ? post.getPrivacy() : "PUBLIC")
                .viewCount(post.getViewCount())
                .likes(likes)
                .commentsCount(commentsCount)
                .createdAt(post.getCreatedAt())
                .updatedAt(post.getUpdatedAt())
                .comments(commentResponses)
                .user(userResponse)
                .liked(liked != null ? liked : false)
                .linkedPlanId(post.getLinkedPlanId())
                .linkedPlan(linkedPlanInfo);
        
        if (post.getOriginalPostId() != null && originalPost != null) {
            builder.originalPostId(post.getOriginalPostId());
            builder.originalAuthorId(post.getOriginalAuthorId());
            
            UserResponse originalAuthorResponse = originalAuthor != null ? 
                UserResponse.builder()
                    .id(originalAuthor.getId())
                    .username(originalAuthor.getUsername())
                    .displayName(originalAuthor.getDisplayName())
                    .avatarUrl(originalAuthor.getAvatarUrl())
                    .build() : null;
            
            PostDetailResponse originalPostResponse = PostDetailResponse.builder()
                    .id(originalPost.getId())
                    .userId(originalPost.getUserId())
                    .content(originalPost.getContent())
                    .postType(originalPost.getPostType() != null ? originalPost.getPostType() : "TEXT")
                    .mediaUrls(originalPost.getMediaUrls())
                    .hashtags(originalPost.getHashtags())
                    .privacy(originalPost.getPrivacy() != null ? originalPost.getPrivacy() : "PUBLIC")
                    .viewCount(originalPost.getViewCount())
                    .likes(originalPostLikes)
                    .commentsCount(originalPostCommentsCount)
                    .createdAt(originalPost.getCreatedAt())
                    .updatedAt(originalPost.getUpdatedAt())
                    .user(originalAuthorResponse)
                    .liked(false)
                    .build();
            
            builder.originalPost(originalPostResponse);
            builder.originalAuthor(originalAuthorResponse);
        }
        
        return builder.build();
    }
}