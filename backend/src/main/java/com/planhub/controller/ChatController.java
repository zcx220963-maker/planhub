package com.planhub.controller;

import com.planhub.dto.request.SendMessageRequest;
import com.planhub.dto.response.ChatConversationResponse;
import com.planhub.dto.response.ChatMessageResponse;
import com.planhub.dto.response.ApiResponse;
import com.planhub.entity.ChatMessage;
import com.planhub.service.ChatService;
import jakarta.validation.Valid;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/chat")
@RequiredArgsConstructor
public class ChatController {
    private final ChatService chatService;

    @GetMapping("/conversations")
    public ResponseEntity<ApiResponse<List<ChatConversationResponse>>> getConversations(
            Authentication authentication) {
        Long userId = (Long) authentication.getPrincipal();
        List<ChatConversationResponse> conversations = chatService.getConversations(userId);
        return ResponseEntity.ok(ApiResponse.success(conversations));
    }

    @GetMapping("/conversations/{conversationId}/messages")
    public ResponseEntity<ApiResponse<List<ChatMessageResponse>>> getMessages(
            Authentication authentication,
            @PathVariable Long conversationId) {
        Long userId = (Long) authentication.getPrincipal();
        List<ChatMessageResponse> messages = chatService.getMessages(conversationId, userId);
        return ResponseEntity.ok(ApiResponse.success(messages));
    }

    @PostMapping("/messages")
    public ResponseEntity<ApiResponse<ChatMessageResponse>> sendMessage(
            Authentication authentication,
            @Valid @RequestBody SendMessageRequest request) {
        Long senderId = (Long) authentication.getPrincipal();
        ChatMessage message = chatService.sendMessage(senderId, request.getReceiverId(), request.getContent());
        // 直接返回消息，为了简单起见这里可以简化或重新查询
        List<ChatMessageResponse> messages = chatService.getMessages(message.getConversationId(), senderId);
        ChatMessageResponse response = messages.get(messages.size() - 1);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @PostMapping("/messages/share-plan")
    public ResponseEntity<ApiResponse<ChatMessageResponse>> sharePlan(
            Authentication authentication,
            @Valid @RequestBody SharePlanToChatRequest request) {
        Long senderId = (Long) authentication.getPrincipal();
        ChatMessage message = chatService.sendSharedPlan(senderId, request.getReceiverId(), request.getPlanId(), request.getContent());
        List<ChatMessageResponse> messages = chatService.getMessages(message.getConversationId(), senderId);
        ChatMessageResponse response = messages.get(messages.size() - 1);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @PostMapping("/messages/share-post")
    public ResponseEntity<ApiResponse<ChatMessageResponse>> sharePost(
            Authentication authentication,
            @Valid @RequestBody SharePostToChatRequest request) {
        Long senderId = (Long) authentication.getPrincipal();
        ChatMessage message = chatService.sendSharedPost(senderId, request.getReceiverId(), request.getPostId(), request.getContent());
        List<ChatMessageResponse> messages = chatService.getMessages(message.getConversationId(), senderId);
        ChatMessageResponse response = messages.get(messages.size() - 1);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @Data
    public static class SharePlanToChatRequest {
        @jakarta.validation.constraints.NotNull
        private Long receiverId;
        @jakarta.validation.constraints.NotNull
        private Long planId;
        private String content;
    }

    @Data
    public static class SharePostToChatRequest {
        @jakarta.validation.constraints.NotNull
        private Long receiverId;
        @jakarta.validation.constraints.NotNull
        private Long postId;
        private String content;
    }
}
