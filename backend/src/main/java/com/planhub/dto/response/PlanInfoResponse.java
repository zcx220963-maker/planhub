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
public class PlanInfoResponse {
    private Long id;
    private String title;
    private String description;
    private String category;
    private String status;
    private Integer progressPercentage;
    private String coverImageUrl;
    private LocalDateTime createdAt;
    private PostDetailResponse.UserResponse owner;
}
