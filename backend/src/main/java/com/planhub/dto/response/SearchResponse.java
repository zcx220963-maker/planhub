package com.planhub.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class SearchResponse {
    private List<UserResult> users;
    private List<PlanResult> plans;
    private List<PostResult> posts;
    private List<String> topics;
    private Integer totalResults;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class UserResult {
        private Long id;
        private String username;
        private String displayName;
        private String avatarUrl;
        private String description;
        private Integer planCount;
        private Double matchScore;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PlanResult {
        private Long id;
        private String title;
        private String description;
        private String deadline;
        private UserInfo user;
        private Double matchScore;

        @Data
        @Builder
        @NoArgsConstructor
        @AllArgsConstructor
        public static class UserInfo {
            private String name;
        }
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PostResult {
        private Long id;
        private Long userId;
        private String user;
        private String avatarUrl;
        private String content;
        private String time;
        private List<String> tags;
        private Double matchScore;
    }
}
