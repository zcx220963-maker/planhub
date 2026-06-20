package com.planhub.service;

import com.planhub.dto.response.ChatConversationResponse;
import com.planhub.dto.response.ChatMessageResponse;
import com.planhub.entity.ChatConversation;
import com.planhub.entity.ChatMessage;

import java.util.List;

public interface ChatService {
    boolean isMutualFollow(Long userId1, Long userId2);

    boolean canSendMessage(Long senderId, Long receiverId);

    String getMessageLimitInfo(Long senderId, Long receiverId);

    ChatConversation getOrCreateConversation(Long user1Id, Long user2Id);

    ChatConversation createConversation(Long user1Id, Long user2Id);

    ChatMessage sendMessage(Long senderId, Long receiverId, String content);

    ChatMessage sendSharedPlan(Long senderId, Long receiverId, Long planId, String content);

    ChatMessage sendSharedPost(Long senderId, Long receiverId, Long postId, String content);

    List<ChatConversationResponse> getConversations(Long currentUserId);

    List<ChatMessageResponse> getMessages(Long conversationId, Long currentUserId);

    void sendSystemMessageOnMutualFollow(Long user1Id, Long user2Id, String content);
}
