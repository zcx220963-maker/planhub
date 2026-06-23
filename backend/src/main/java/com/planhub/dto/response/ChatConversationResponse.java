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
public class ChatConversationResponse {
    private Long id;
    private Long otherUserId;
    private PostDetailResponse.UserResponse otherUser;
    private String lastMessage;
    private LocalDateTime lastMessageTime;
    private Integer unreadCount;
    private Boolean isMutualFollow;
    private Boolean canSend;
    private String messageLimit;
    private LocalDateTime createdAt;
}
