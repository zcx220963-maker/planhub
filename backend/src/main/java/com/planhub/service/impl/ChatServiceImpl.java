package com.planhub.service.impl;

import com.planhub.dto.response.ChatConversationResponse;
import com.planhub.dto.response.ChatMessageResponse;
import com.planhub.dto.response.PlanInfoResponse;
import com.planhub.dto.response.PostDetailResponse;
import com.planhub.dto.response.PostSummaryResponse;
import com.planhub.entity.ChatConversation;
import com.planhub.entity.ChatMessage;
import com.planhub.entity.Plan;
import com.planhub.entity.Post;
import com.planhub.entity.User;
import com.planhub.entity.UserRelationship;
import com.planhub.mapper.ChatConversationMapper;
import com.planhub.mapper.ChatMessageMapper;
import com.planhub.mapper.PlanMapper;
import com.planhub.mapper.PostMapper;
import com.planhub.mapper.UserRelationshipMapper;
import com.planhub.mapper.UserMapper;
import com.planhub.service.ChatService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class ChatServiceImpl implements ChatService {
    private final ChatConversationMapper conversationMapper;
    private final ChatMessageMapper messageMapper;
    private final UserRelationshipMapper relationshipMapper;
    private final UserMapper userMapper;
    private final PlanMapper planMapper;
    private final PostMapper postMapper;

    @Override
    public boolean isMutualFollow(Long userId1, Long userId2) {
        UserRelationship follow1 = relationshipMapper
                .selectByFollowerIdAndFollowingIdAndRelationshipType(userId1, userId2, "follow");
        UserRelationship follow2 = relationshipMapper
                .selectByFollowerIdAndFollowingIdAndRelationshipType(userId2, userId1, "follow");
        return follow1 != null && follow2 != null;
    }

    @Override
    public boolean canSendMessage(Long senderId, Long receiverId) {
        if (isMutualFollow(senderId, receiverId)) {
            return true;
        }
        ChatConversation conversation = getOrCreateConversation(senderId, receiverId);
        if (conversation != null) {
            List<ChatMessage> messages = messageMapper.selectByConversationIdOrderByCreatedAtAsc(conversation.getId());
            long senderMessages = messages.stream()
                    .filter(m -> m.getSenderId().equals(senderId) && !m.getIsSystemMessage())
                    .count();
            return senderMessages < 1;
        }
        return true;
    }

    @Override
    public String getMessageLimitInfo(Long senderId, Long receiverId) {
        if (isMutualFollow(senderId, receiverId)) {
            return null;
        }
        ChatConversation conversation = getOrCreateConversation(senderId, receiverId);
        if (conversation != null) {
            List<ChatMessage> messages = messageMapper.selectByConversationIdOrderByCreatedAtAsc(conversation.getId());
            long senderMessages = messages.stream()
                    .filter(m -> m.getSenderId().equals(senderId) && !m.getIsSystemMessage())
                    .count();
            if (senderMessages == 0) {
                return "未互关，仅可发送一条消息";
            } else {
                return "已发送一条消息，请等待对方回复";
            }
        }
        return "未互关，仅可发送一条消息";
    }

    @Override
    public ChatConversation getOrCreateConversation(Long user1Id, Long user2Id) {
        ChatConversation existing = conversationMapper.selectByUser1IdAndUser2Id(user1Id, user2Id);
        if (existing != null) {
            return existing;
        }
        existing = conversationMapper.selectByUser2IdAndUser1Id(user1Id, user2Id);
        if (existing != null) {
            return existing;
        }
        return null;
    }

    @Override
    public ChatConversation createConversation(Long user1Id, Long user2Id) {
        Long u1 = Math.min(user1Id, user2Id);
        Long u2 = Math.max(user1Id, user2Id);
        ChatConversation conversation = ChatConversation.builder()
                .user1Id(u1)
                .user2Id(u2)
                .build();
        conversationMapper.insert(conversation);
        return conversation;
    }

    @Override
    @Transactional
    public ChatMessage sendMessage(Long senderId, Long receiverId, String content) {
        if (!canSendMessage(senderId, receiverId)) {
            throw new RuntimeException("无法发送消息，请等待对方回复或互相关注后继续");
        }

        ChatConversation conversation = getOrCreateConversation(senderId, receiverId);
        if (conversation == null) {
            conversation = createConversation(senderId, receiverId);
        }

        boolean isFirstMessage = messageMapper.selectByConversationIdOrderByCreatedAtAsc(conversation.getId()).isEmpty();
        if (isFirstMessage && !isMutualFollow(senderId, receiverId)) {
            ChatMessage systemMsg = ChatMessage.builder()
                    .conversationId(conversation.getId())
                    .senderId(senderId)
                    .receiverId(receiverId)
                    .content("未互关，仅可发送一条消息")
                    .messageType(2)
                    .isSystemMessage(true)
                    .build();
            messageMapper.insert(systemMsg);
        }

        ChatMessage message = ChatMessage.builder()
                .conversationId(conversation.getId())
                .senderId(senderId)
                .receiverId(receiverId)
                .content(content)
                .messageType(0)
                .build();

        messageMapper.insert(message);

        conversation.setLastMessage(content);
        conversation.setLastMessageTime(LocalDateTime.now());
        if (conversation.getUser1Id().equals(receiverId)) {
            conversation.setUser1Unread(conversation.getUser1Unread() + 1);
        } else {
            conversation.setUser2Unread(conversation.getUser2Unread() + 1);
        }
        conversation.setUpdatedAt(LocalDateTime.now());
        conversationMapper.updateById(conversation);

        return message;
    }

    @Override
    @Transactional
    public ChatMessage sendSharedPlan(Long senderId, Long receiverId, Long planId, String content) {
        if (!canSendMessage(senderId, receiverId)) {
            throw new RuntimeException("无法发送消息，请等待对方回复或互相关注后继续");
        }

        Plan plan = planMapper.selectById(planId);
        if (plan == null) {
            throw new RuntimeException("计划不存在");
        }

        ChatConversation conversation = getOrCreateConversation(senderId, receiverId);
        if (conversation == null) {
            conversation = createConversation(senderId, receiverId);
        }

        boolean isFirstMessage = messageMapper.selectByConversationIdOrderByCreatedAtAsc(conversation.getId()).isEmpty();
        if (isFirstMessage && !isMutualFollow(senderId, receiverId)) {
            ChatMessage systemMsg = ChatMessage.builder()
                    .conversationId(conversation.getId())
                    .senderId(senderId)
                    .receiverId(receiverId)
                    .content("未互关，仅可发送一条消息")
                    .messageType(2)
                    .isSystemMessage(true)
                    .build();
            messageMapper.insert(systemMsg);
        }

        ChatMessage message = ChatMessage.builder()
                .conversationId(conversation.getId())
                .senderId(senderId)
                .receiverId(receiverId)
                .content(content != null && !content.isEmpty() ? content : "[分享了一个计划]")
                .messageType(0) // 使用普通消息类型，靠 shared_plan_id 字段来区分
                .sharedPlanId(planId)
                .isRead(false)
                .isSystemMessage(false)
                .createdAt(LocalDateTime.now())
                .build();

        messageMapper.insert(message);

        String lastMessage = content != null && !content.isEmpty() ? content : "[分享了一个计划]";
        conversation.setLastMessage(lastMessage);
        conversation.setLastMessageTime(LocalDateTime.now());
        if (conversation.getUser1Id().equals(receiverId)) {
            conversation.setUser1Unread(conversation.getUser1Unread() + 1);
        } else {
            conversation.setUser2Unread(conversation.getUser2Unread() + 1);
        }
        conversation.setUpdatedAt(LocalDateTime.now());
        conversationMapper.updateById(conversation);

        return message;
    }

    @Override
    @Transactional
    public ChatMessage sendSharedPost(Long senderId, Long receiverId, Long postId, String content) {
        if (!canSendMessage(senderId, receiverId)) {
            throw new RuntimeException("无法发送消息，请等待对方回复或互相关注后继续");
        }

        Post post = postMapper.selectById(postId);
        if (post == null) {
            throw new RuntimeException("帖子不存在");
        }

        ChatConversation conversation = getOrCreateConversation(senderId, receiverId);
        if (conversation == null) {
            conversation = createConversation(senderId, receiverId);
        }

        boolean isFirstMessage = messageMapper.selectByConversationIdOrderByCreatedAtAsc(conversation.getId()).isEmpty();
        if (isFirstMessage && !isMutualFollow(senderId, receiverId)) {
            ChatMessage systemMsg = ChatMessage.builder()
                    .conversationId(conversation.getId())
                    .senderId(senderId)
                    .receiverId(receiverId)
                    .content("未互关，仅可发送一条消息")
                    .messageType(2)
                    .isSystemMessage(true)
                    .build();
            messageMapper.insert(systemMsg);
        }

        ChatMessage message = ChatMessage.builder()
                .conversationId(conversation.getId())
                .senderId(senderId)
                .receiverId(receiverId)
                .content(content != null && !content.isEmpty() ? content : "[分享了一个帖子]")
                .messageType(0) // 使用普通消息类型，靠 shared_post_id 字段来区分
                .sharedPostId(postId)
                .isRead(false)
                .isSystemMessage(false)
                .createdAt(LocalDateTime.now())
                .build();

        messageMapper.insert(message);

        String lastMessage = content != null && !content.isEmpty() ? content : "[分享了一个帖子]";
        conversation.setLastMessage(lastMessage);
        conversation.setLastMessageTime(LocalDateTime.now());
        if (conversation.getUser1Id().equals(receiverId)) {
            conversation.setUser1Unread(conversation.getUser1Unread() + 1);
        } else {
            conversation.setUser2Unread(conversation.getUser2Unread() + 1);
        }
        conversation.setUpdatedAt(LocalDateTime.now());
        conversationMapper.updateById(conversation);

        return message;
    }

    @Override
    public List<ChatConversationResponse> getConversations(Long currentUserId) {
        List<ChatConversation> conversations = conversationMapper
                .selectByUser1IdOrUser2IdOrderByUpdatedAtDesc(currentUserId, currentUserId);

        Set<Long> userIds = new HashSet<>();
        for (ChatConversation conversation : conversations) {
            userIds.add(conversation.getUser1Id());
            userIds.add(conversation.getUser2Id());
        }

        final Map<Long, User> userMap;
        if (!userIds.isEmpty()) {
            userMap = userMapper.selectBatchIds(userIds).stream()
                    .collect(Collectors.toMap(User::getId, u -> u));
        } else {
            userMap = new HashMap<>();
        }

        return conversations.stream()
                .map(conv -> buildConversationResponse(conv, currentUserId, userMap))
                .collect(Collectors.toList());
    }

    @Override
    public List<ChatMessageResponse> getMessages(Long conversationId, Long currentUserId) {
        ChatConversation conversation = conversationMapper.selectById(conversationId);
        if (conversation == null) {
            throw new RuntimeException("会话不存在");
        }

        if (conversation.getUser1Id().equals(currentUserId)) {
            conversation.setUser1Unread(0);
        } else {
            conversation.setUser2Unread(0);
        }
        conversationMapper.updateById(conversation);

        List<ChatMessage> messages = messageMapper.selectByConversationIdOrderByCreatedAtAsc(conversationId);

        Set<Long> userIds = new HashSet<>();
        for (ChatMessage msg : messages) {
            userIds.add(msg.getSenderId());
            userIds.add(msg.getReceiverId());
        }
        
        final Map<Long, User> userMap;
        if (!userIds.isEmpty()) {
            userMap = userMapper.selectBatchIds(userIds).stream()
                    .collect(Collectors.toMap(User::getId, u -> u));
        } else {
            userMap = new HashMap<>();
        }

        return messages.stream()
                .map(msg -> buildMessageResponse(msg, userMap))
                .collect(Collectors.toList());
    }

    @Override
    public void sendSystemMessageOnMutualFollow(Long user1Id, Long user2Id, String content) {
        ChatConversation conversation = getOrCreateConversation(user1Id, user2Id);
        if (conversation == null) {
            conversation = createConversation(user1Id, user2Id);
        }

        ChatMessage systemMsg = ChatMessage.builder()
                .conversationId(conversation.getId())
                .senderId(user1Id)
                .receiverId(user2Id)
                .content(content)
                .messageType(2)
                .isSystemMessage(true)
                .build();
        messageMapper.insert(systemMsg);

        conversation.setLastMessage(content);
        conversation.setLastMessageTime(LocalDateTime.now());
        if (conversation.getUser1Id().equals(user2Id)) {
            conversation.setUser1Unread(conversation.getUser1Unread() + 1);
        } else {
            conversation.setUser2Unread(conversation.getUser2Unread() + 1);
        }
        conversation.setUpdatedAt(LocalDateTime.now());
        conversationMapper.updateById(conversation);
    }

    private ChatConversationResponse buildConversationResponse(ChatConversation conv, Long currentUserId, Map<Long, User> userMap) {
        Long otherUserId = conv.getUser1Id().equals(currentUserId) ? conv.getUser2Id() : conv.getUser1Id();
        User otherUser = userMap.get(otherUserId);
        Integer unreadCount = conv.getUser1Id().equals(currentUserId) ? conv.getUser1Unread() : conv.getUser2Unread();
        boolean isMutual = isMutualFollow(currentUserId, otherUserId);
        boolean canSend = canSendMessage(currentUserId, otherUserId);
        String limitInfo = getMessageLimitInfo(currentUserId, otherUserId);

        return ChatConversationResponse.builder()
                .id(conv.getId())
                .otherUserId(otherUserId)
                .otherUser(buildUserResponse(otherUser))
                .lastMessage(conv.getLastMessage())
                .lastMessageTime(conv.getLastMessageTime())
                .unreadCount(unreadCount)
                .isMutualFollow(isMutual)
                .canSend(canSend)
                .messageLimit(limitInfo)
                .createdAt(conv.getCreatedAt())
                .build();
    }

    private ChatMessageResponse buildMessageResponse(ChatMessage msg, Map<Long, User> userMap) {
        User sender = userMap.get(msg.getSenderId());
        User receiver = userMap.get(msg.getReceiverId());

        String msgType = null;
        if (msg.getMessageType() != null) {
            switch (msg.getMessageType()) {
                case 0: 
                    // 根据字段来区分
                    if (msg.getSharedPlanId() != null) {
                        msgType = "SHARED_PLAN";
                    } else if (msg.getSharedPostId() != null) {
                        msgType = "SHARED_POST";
                    } else {
                        msgType = "TEXT";
                    }
                    break;
                case 1: msgType = "IMAGE"; break;
                case 2: msgType = "SYSTEM"; break;
                default: msgType = "TEXT"; break;
            }
        }
        
        ChatMessageResponse.ChatMessageResponseBuilder builder = ChatMessageResponse.builder()
                .id(msg.getId())
                .senderId(msg.getSenderId())
                .receiverId(msg.getReceiverId())
                .content(msg.getContent())
                .messageType(msgType)
                .isRead(msg.getIsRead())
                .isSystemMessage(msg.getIsSystemMessage())
                .createdAt(msg.getCreatedAt())
                .sender(buildUserResponse(sender))
                .receiver(buildUserResponse(receiver))
                .sharedPlanId(msg.getSharedPlanId())
                .sharedPostId(msg.getSharedPostId());
        
        // 加载分享的计划信息
        if (msg.getSharedPlanId() != null) {
            Plan plan = planMapper.selectById(msg.getSharedPlanId());
            if (plan != null) {
                User planOwner = userMapper.selectById(plan.getUserId());
                PlanInfoResponse planInfo = PlanInfoResponse.builder()
                        .id(plan.getId())
                        .title(plan.getTitle())
                        .description(plan.getDescription())
                        .category(plan.getCategory() != null ? plan.getCategory().name() : null)
                        .status(plan.getStatus() != null ? plan.getStatus().name() : null)
                        .progressPercentage(plan.getProgressPercentage() != null ? plan.getProgressPercentage().intValue() : 0)
                        .coverImageUrl(plan.getCoverImageUrl())
                        .createdAt(plan.getCreatedAt())
                        .owner(buildUserResponse(planOwner))
                        .build();
                builder.sharedPlan(planInfo);
            }
        }
        
        // 加载分享的帖子信息
        if (msg.getSharedPostId() != null) {
            Post post = postMapper.selectById(msg.getSharedPostId());
            if (post != null) {
                User postOwner = userMapper.selectById(post.getUserId());
                PostSummaryResponse postSummary = PostSummaryResponse.builder()
                        .id(post.getId())
                        .content(post.getContent())
                        .hashtags(post.getHashtags())
                        .likes(0) // 这里需要实际的点赞数
                        .commentsCount(0) // 这里需要实际的评论数
                        .createdAt(post.getCreatedAt())
                        .user(buildUserResponse(postOwner))
                        .build();
                builder.sharedPost(postSummary);
            }
        }
        
        return builder.build();
    }

    private PostDetailResponse.UserResponse buildUserResponse(User user) {
        if (user == null) return null;
        return PostDetailResponse.UserResponse.builder()
                .id(user.getId())
                .username(user.getUsername())
                .displayName(user.getDisplayName())
                .avatarUrl(user.getAvatarUrl())
                .build();
    }
}
