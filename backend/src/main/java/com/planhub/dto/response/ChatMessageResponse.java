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
public class ChatMessageResponse {
    private Long id;
    private Long senderId;
    private Long receiverId;
    private String content;
    private String messageType;
    private Boolean isRead;
    private Boolean isSystemMessage;
    private LocalDateTime createdAt;
    private PostDetailResponse.UserResponse sender;
    private PostDetailResponse.UserResponse receiver;
    private Long sharedPlanId;
    private PlanInfoResponse sharedPlan;
    private Long sharedPostId;
    private PostSummaryResponse sharedPost;
}
