package com.planhub.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PostResponse {
    private Long id;
    private Long userId;
    private String content;
    private String imageUrl;
    private Integer likes;
    private Integer commentsCount;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private UserResponse user;
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
        private String content;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;
        private UserResponse user;
    }
}