package com.planhub.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.planhub.entity.Activity;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface ActivityMapper extends BaseMapper<Activity> {

    @Select("SELECT * FROM activities WHERE user_id = #{userId} ORDER BY created_at DESC")
    IPage<Activity> selectByUserIdOrderByCreatedAtDesc(@Param("userId") Long userId, Page<Activity> page);

    @Select("SELECT * FROM activities WHERE user_id = #{userId} ORDER BY created_at DESC")
    List<Activity> selectListByUserIdOrderByCreatedAtDesc(@Param("userId") Long userId);

    @Select("<script>" +
            "SELECT * FROM activities WHERE user_id = #{userId} AND id IN " +
            "<foreach collection='ids' item='id' open='(' separator=',' close=')'>" +
            "#{id}" +
            "</foreach>" +
            "</script>")
    List<Activity> selectListByUserIdAndIdIn(@Param("userId") Long userId, @Param("ids") List<Long> ids);
}
