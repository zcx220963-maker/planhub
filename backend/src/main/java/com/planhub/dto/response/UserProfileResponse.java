package com.planhub.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserProfileResponse {
    private Long id;
    private String username;
    private String email;
    private String displayName;
    private String avatarUrl;
    private String bio;
    private List<PlanSummary> publicPlans;
    private List<PostSummary> publicPosts;
    private List<ActivityResponse> activities;
    private Boolean showActivities;
    private Boolean showFollowers;
    private Boolean showFollowing;
    private Boolean showLikedContent;
    private Long followerCount;
    private Long followingCount;
    private Boolean isFollowing;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PlanSummary {
        private Long id;
        private String title;
        private String description;
        private String status;
        private Integer progressPercentage;
        private String targetDate;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PostSummary {
        private Long id;
        private String content;
        private String hashtags;
        private Integer likes;
        private Integer commentsCount;
        private String createdAt;
    }
}
