package com.planhub.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.planhub.entity.PostInteraction;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;
import java.util.Optional;

@Mapper
public interface PostInteractionMapper extends BaseMapper<PostInteraction> {

    @Select("SELECT * FROM post_interactions WHERE post_id = #{postId} AND user_id = #{userId} AND interaction_type = #{interactionType} LIMIT 1")
    Optional<PostInteraction> findByPostIdAndUserIdAndInteractionType(Long postId, Long userId, String interactionType);

    @Select("SELECT COUNT(*) FROM post_interactions WHERE post_id = #{postId} AND interaction_type = #{interactionType}")
    long countByPostIdAndInteractionType(Long postId, String interactionType);

    @Select("SELECT EXISTS(SELECT 1 FROM post_interactions WHERE post_id = #{postId} AND user_id = #{userId} AND interaction_type = #{interactionType})")
    boolean existsByPostIdAndUserIdAndInteractionType(Long postId, Long userId, String interactionType);

    List<PostInteraction> findByUserIdAndPostIdInAndInteractionType(Long userId, List<Long> postIds, String interactionType);

    @Delete("DELETE FROM post_interactions WHERE post_id = #{postId}")
    void deleteByPostId(Long postId);
}
