package com.planhub.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.planhub.entity.ChatConversation;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface ChatConversationMapper extends BaseMapper<ChatConversation> {

    @Select("SELECT * FROM chat_conversations WHERE user1_id = #{user1Id} AND user2_id = #{user2Id}")
    ChatConversation selectByUser1IdAndUser2Id(Long user1Id, Long user2Id);

    @Select("SELECT * FROM chat_conversations WHERE user2_id = #{user2Id} AND user1_id = #{user1Id}")
    ChatConversation selectByUser2IdAndUser1Id(Long user2Id, Long user1Id);

    @Select("SELECT * FROM chat_conversations WHERE user1_id = #{user1Id} OR user2_id = #{user2Id} ORDER BY updated_at DESC")
    List<ChatConversation> selectByUser1IdOrUser2IdOrderByUpdatedAtDesc(Long user1Id, Long user2Id);
}
