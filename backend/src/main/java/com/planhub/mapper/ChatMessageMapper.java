package com.planhub.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.planhub.entity.ChatMessage;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface ChatMessageMapper extends BaseMapper<ChatMessage> {
    
    @Select("SELECT * FROM chat_messages WHERE conversation_id = #{conversationId} ORDER BY created_at ASC")
    List<ChatMessage> selectByConversationIdOrderByCreatedAtAsc(Long conversationId);
    
    @Select("SELECT * FROM chat_messages WHERE sender_id = #{senderId} AND receiver_id = #{receiverId} ORDER BY created_at ASC")
    List<ChatMessage> selectBySenderIdAndReceiverIdOrderByCreatedAtAsc(Long senderId, Long receiverId);
    
    @Select("SELECT COUNT(*) FROM chat_messages WHERE conversation_id = #{conversationId} AND is_read = false AND receiver_id = #{receiverId}")
    Long countByConversationIdAndIsReadFalseAndReceiverId(Long conversationId, Long receiverId);
    
    @Select("SELECT COUNT(*) FROM chat_messages WHERE receiver_id = #{receiverId} AND is_read = false")
    Long countByReceiverIdAndIsReadFalse(Long receiverId);
}
