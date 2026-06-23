package com.planhub.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.planhub.entity.CommentInteraction;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;
import java.util.Optional;

@Mapper
public interface CommentInteractionMapper extends BaseMapper<CommentInteraction> {

    @Select("SELECT * FROM comment_interactions WHERE comment_id = #{commentId} AND user_id = #{userId} LIMIT 1")
    Optional<CommentInteraction> findByCommentIdAndUserId(@Param("commentId") Long commentId, @Param("userId") Long userId);

    @Select("SELECT * FROM comment_interactions WHERE comment_id = #{commentId}")
    List<CommentInteraction> findByCommentId(@Param("commentId") Long commentId);

    @Select("SELECT * FROM comment_interactions WHERE user_id = #{userId}")
    List<CommentInteraction> findByUserId(@Param("userId") Long userId);

    @Select("SELECT COUNT(*) FROM comment_interactions WHERE comment_id = #{commentId}")
    long countByCommentId(@Param("commentId") Long commentId);

    @Select("SELECT COUNT(*) > 0 FROM comment_interactions WHERE comment_id = #{commentId} AND user_id = #{userId}")
    boolean existsByCommentIdAndUserId(@Param("commentId") Long commentId, @Param("userId") Long userId);

    List<CommentInteraction> findByUserIdAndCommentIdIn(@Param("userId") Long userId, @Param("commentIds") List<Long> commentIds);

    @Delete("DELETE FROM comment_interactions WHERE comment_id = #{commentId} AND user_id = #{userId}")
    void deleteByCommentIdAndUserId(@Param("commentId") Long commentId, @Param("userId") Long userId);
}
