package com.planhub.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.planhub.entity.Plan;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;
import java.util.Optional;

@Mapper
public interface PlanMapper extends BaseMapper<Plan> {

    @Select("SELECT * FROM plans p WHERE p.deleted_at IS NULL AND p.user_id = #{userId}")
    IPage<Plan> selectByUserId(@Param("userId") Long userId, Page<Plan> page);

    @Select("SELECT * FROM plans p WHERE p.deleted_at IS NULL AND p.user_id = #{userId} AND LOWER(p.status) = LOWER(#{status})")
    IPage<Plan> selectByUserIdAndStatus(@Param("userId") Long userId, 
                                      @Param("status") String status, 
                                      Page<Plan> page);

    @Select("SELECT * FROM plans p WHERE p.deleted_at IS NULL AND p.user_id = #{userId} AND LOWER(p.category) = LOWER(#{category})")
    IPage<Plan> selectByUserIdAndCategory(@Param("userId") Long userId, 
                                        @Param("category") String category, 
                                        Page<Plan> page);

    @Select("SELECT * FROM plans p WHERE p.deleted_at IS NULL AND p.user_id = #{userId} AND LOWER(p.priority) = LOWER(#{priority})")
    IPage<Plan> selectByUserIdAndPriority(@Param("userId") Long userId, 
                                       @Param("priority") String priority, 
                                       Page<Plan> page);

    @Select("SELECT * FROM plans p WHERE p.deleted_at IS NULL AND p.id = #{id} AND p.user_id = #{userId}")
    Plan selectByIdAndUserId(@Param("id") Long id, @Param("userId") Long userId);

    @Select("SELECT * FROM plans p WHERE p.deleted_at IS NULL AND p.user_id = #{userId} AND LOWER(p.status) = LOWER(#{status})")
    List<Plan> selectByUserIdAndStatusList(@Param("userId") Long userId, 
                                      @Param("status") String status);

    @Select("SELECT * FROM plans p WHERE p.deleted_at IS NULL AND LOWER(p.visibility) = LOWER(#{visibility}) ORDER BY p.created_at DESC")
    IPage<Plan> selectByVisibilityOrderByCreatedAtDesc(@Param("visibility") String visibility, 
                                                     Page<Plan> page);

    IPage<Plan> selectByTitleContainingOrDescriptionContainingAndVisibility(
            @Param("title") String title, 
            @Param("description") String description, 
            @Param("visibility") String visibility, 
            Page<Plan> page);

    IPage<Plan> selectByTitleContainingOrDescriptionContaining(
            @Param("title") String title, 
            @Param("description") String description, 
            Page<Plan> page);

    IPage<Plan> selectByUserIdAndTitleContainingOrUserIdAndDescriptionContaining(
            @Param("userId1") Long userId1, 
            @Param("title") String title, 
            @Param("userId2") Long userId2, 
            @Param("description") String description, 
            Page<Plan> page);

    IPage<Plan> selectByVisibilityAndTitleContainingOrVisibilityAndDescriptionContaining(
            @Param("visibility1") String visibility1, 
            @Param("title") String title, 
            @Param("visibility2") String visibility2, 
            @Param("description") String description, 
            Page<Plan> page);

    IPage<Plan> selectByUserIdAndVisibilityAndTitleContainingOrUserIdAndVisibilityAndDescriptionContaining(
            @Param("userId1") Long userId1, 
            @Param("visibility1") String visibility1, 
            @Param("title") String title, 
            @Param("userId2") Long userId2, 
            @Param("visibility2") String visibility2, 
            @Param("description") String description, 
            Page<Plan> page);

    @Select("SELECT * FROM plans p WHERE p.deleted_at IS NULL AND LOWER(p.visibility) = LOWER(#{visibility}) AND p.user_id != #{userId} ORDER BY p.created_at DESC")
    IPage<Plan> selectByVisibilityAndUserIdNotOrderByCreatedAtDesc(@Param("visibility") String visibility, 
                                                                 @Param("userId") Long userId, 
                                                                 Page<Plan> page);

    IPage<Plan> selectByVisibilityAndUserIdNotAndTitleContainingOrVisibilityAndUserIdNotAndDescriptionContaining(
            @Param("visibility1") String visibility1, 
            @Param("userId1") Long userId1, 
            @Param("title") String title, 
            @Param("visibility2") String visibility2, 
            @Param("userId2") Long userId2, 
            @Param("description") String description, 
            Page<Plan> page);

    @Select("SELECT * FROM plans p WHERE p.deleted_at IS NULL AND p.user_id = #{userId} AND LOWER(p.visibility) = LOWER(#{visibility})")
    List<Plan> selectByUserIdAndVisibilityList(@Param("userId") Long userId, 
                                            @Param("visibility") String visibility);

    @Select("SELECT * FROM plans p WHERE p.deleted_at IS NULL AND p.user_id = #{userId} AND LOWER(p.visibility) = LOWER(#{visibility})")
    IPage<Plan> selectByUserIdAndVisibility(@Param("userId") Long userId, 
                                          @Param("visibility") String visibility, 
                                          Page<Plan> page);
    
    @Select("SELECT * FROM plans p WHERE p.deleted_at IS NULL AND p.id = #{id}")
    Plan selectPlanById(@Param("id") Long id);
}
