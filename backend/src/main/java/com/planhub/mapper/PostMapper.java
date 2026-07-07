package com.planhub.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.planhub.entity.Post;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface PostMapper extends BaseMapper<Post> {

    @Select("SELECT p.* FROM posts p WHERE p.deleted_at IS NULL ORDER BY (SELECT COUNT(*) FROM post_interactions i WHERE i.post_id = p.id AND LOWER(i.interaction_type) = 'like') DESC")
    List<Post> selectPopularPosts(Page<Post> page);

    @Select("SELECT p.* FROM posts p WHERE p.deleted_at IS NULL AND p.user_id = #{userId} ORDER BY (SELECT COUNT(*) FROM post_interactions i WHERE i.post_id = p.id AND LOWER(i.interaction_type) = 'like') DESC, (SELECT COUNT(*) FROM post_comments c WHERE c.post_id = p.id) DESC")
    List<Post> selectByUserIdOrderByHotDesc(@Param("userId") Long userId);

    @Select("SELECT p.* FROM posts p WHERE p.deleted_at IS NULL AND p.hashtags LIKE CONCAT('%', #{hashtag}, '%')")
    IPage<Post> selectPostsByHashtag(@Param("hashtag") String hashtag, Page<Post> page);

    @Select("SELECT p.* FROM posts p WHERE p.deleted_at IS NULL AND (p.content LIKE CONCAT('%', #{content}, '%') OR p.hashtags LIKE CONCAT('%', #{hashtags}, '%'))")
    IPage<Post> selectByContentContainingOrHashtagsContaining(
            @Param("content") String content,
            @Param("hashtags") String hashtags,
            Page<Post> page);

    @Select("SELECT p.* FROM posts p WHERE p.deleted_at IS NULL AND ((LOWER(p.privacy) = LOWER(#{privacy1}) AND p.content LIKE CONCAT('%', #{content}, '%')) OR (LOWER(p.privacy) = LOWER(#{privacy2}) AND p.hashtags LIKE CONCAT('%', #{hashtags}, '%')))")
    IPage<Post> selectByPrivacyAndContentContainingOrPrivacyAndHashtagsContaining(
            @Param("privacy1") String privacy1,
            @Param("content") String content,
            @Param("privacy2") String privacy2,
            @Param("hashtags") String hashtags,
            Page<Post> page);

    @Select("SELECT p.* FROM posts p WHERE p.deleted_at IS NULL AND p.hashtags IS NOT NULL AND p.hashtags != '[]'")
    List<Post> selectAllWithHashtags();
    
    @Select("SELECT p.* FROM posts p WHERE p.deleted_at IS NULL AND p.user_id = #{userId} AND LOWER(p.privacy) = LOWER(#{privacy})")
    IPage<Post> selectByUserIdAndPrivacy(@Param("userId") Long userId, 
                                        @Param("privacy") String privacy, 
                                        Page<Post> page);
    
    @Select("SELECT p.* FROM posts p WHERE p.deleted_at IS NULL ORDER BY p.created_at DESC")
    IPage<Post> selectAllPostsPage(Page<Post> page);
    
    @Select("SELECT p.* FROM posts p WHERE p.deleted_at IS NULL AND p.id = #{id}")
    Post selectPostById(@Param("id") Long id);
}
