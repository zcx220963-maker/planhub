package com.planhub.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.planhub.entity.UserRelationship;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface UserRelationshipMapper extends BaseMapper<UserRelationship> {

    @Select("SELECT * FROM user_relationships WHERE follower_id = #{followerId} AND following_id = #{followingId} AND relationship_type = #{relationshipType}")
    UserRelationship selectByFollowerIdAndFollowingIdAndRelationshipType(
            @Param("followerId") Long followerId,
            @Param("followingId") Long followingId,
            @Param("relationshipType") String relationshipType);

    @Select("SELECT * FROM user_relationships WHERE follower_id = #{followerId} AND relationship_type = #{relationshipType}")
    List<UserRelationship> selectByFollowerIdAndRelationshipType(
            @Param("followerId") Long followerId,
            @Param("relationshipType") String relationshipType);

    @Select("SELECT * FROM user_relationships WHERE following_id = #{followingId} AND relationship_type = #{relationshipType}")
    List<UserRelationship> selectByFollowingIdAndRelationshipType(
            @Param("followingId") Long followingId,
            @Param("relationshipType") String relationshipType);

    @Select("SELECT COUNT(*) FROM user_relationships WHERE follower_id = #{followerId} AND relationship_type = #{relationshipType}")
    long countByFollowerIdAndRelationshipType(
            @Param("followerId") Long followerId,
            @Param("relationshipType") String relationshipType);

    @Select("SELECT COUNT(*) FROM user_relationships WHERE following_id = #{followingId} AND relationship_type = #{relationshipType}")
    long countByFollowingIdAndRelationshipType(
            @Param("followingId") Long followingId,
            @Param("relationshipType") String relationshipType);

    @Select("SELECT COUNT(*) > 0 FROM user_relationships WHERE follower_id = #{followerId} AND following_id = #{followingId} AND relationship_type = #{relationshipType}")
    boolean existByFollowerIdAndFollowingIdAndRelationshipType(
            @Param("followerId") Long followerId,
            @Param("followingId") Long followingId,
            @Param("relationshipType") String relationshipType);
}
