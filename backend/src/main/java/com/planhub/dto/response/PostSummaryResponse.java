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
public class PostSummaryResponse {
    private Long id;
    private String content;
    private String hashtags;
    private Integer likes;
    private Integer commentsCount;
    private LocalDateTime createdAt;
    private PostDetailResponse.UserResponse user;
}
