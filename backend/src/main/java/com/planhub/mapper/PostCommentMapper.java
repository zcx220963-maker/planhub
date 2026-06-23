package com.planhub.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.planhub.entity.PostComment;
import org.apache.ibatis.annotations.*;

import java.util.List;

@Mapper
public interface PostCommentMapper extends BaseMapper<PostComment> {

    IPage<PostComment> selectByPostId(Page<PostComment> page, @Param("postId") Long postId);

    IPage<PostComment> selectByPostIdAndParentCommentId(Page<PostComment> page,
                                                         @Param("postId") Long postId,
                                                         @Param("parentCommentId") Long parentCommentId);

    @Select("SELECT * FROM post_comments WHERE parent_comment_id = #{parentCommentId} ORDER BY created_at DESC")
    List<PostComment> selectByParentCommentId(@Param("parentCommentId") Long parentCommentId);

    @Select("SELECT * FROM post_comments WHERE post_id = #{postId} ORDER BY created_at DESC")
    List<PostComment> selectByPostId(@Param("postId") Long postId);

    @Select("SELECT COUNT(*) FROM post_comments WHERE post_id = #{postId}")
    long countByPostId(@Param("postId") Long postId);

    @Select("SELECT COUNT(*) FROM post_comments WHERE parent_comment_id = #{parentCommentId}")
    long countByParentCommentId(@Param("parentCommentId") Long parentCommentId);

    @Delete("DELETE FROM post_comments WHERE post_id = #{postId}")
    int deleteByPostId(@Param("postId") Long postId);
}
