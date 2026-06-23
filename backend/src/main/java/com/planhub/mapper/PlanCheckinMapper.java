package com.planhub.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.planhub.entity.PlanCheckin;
import org.apache.ibatis.annotations.*;

import java.time.LocalDate;
import java.util.List;

@Mapper
public interface PlanCheckinMapper extends BaseMapper<PlanCheckin> {
    
    @Select("SELECT * FROM plan_checkins WHERE user_id = #{userId} ORDER BY checkin_date DESC, created_at DESC")
    IPage<PlanCheckin> selectByUserId(IPage<PlanCheckin> page, @Param("userId") Long userId);
    
    @Select("SELECT * FROM plan_checkins WHERE plan_id = #{planId} ORDER BY checkin_date DESC, created_at DESC")
    IPage<PlanCheckin> selectByPlanId(IPage<PlanCheckin> page, @Param("planId") Long planId);
    
    @Select("SELECT * FROM plan_checkins WHERE plan_id = #{planId} AND checkin_date = #{checkinDate}")
    PlanCheckin selectByPlanIdAndCheckinDate(@Param("planId") Long planId, @Param("checkinDate") LocalDate checkinDate);
    
    @Select("SELECT COUNT(*) > 0 FROM plan_checkins WHERE plan_id = #{planId} AND user_id = #{userId} AND checkin_date = #{checkinDate}")
    boolean existByPlanIdAndUserIdAndCheckinDate(@Param("planId") Long planId, @Param("userId") Long userId, @Param("checkinDate") LocalDate checkinDate);
    
    @Select("SELECT * FROM plan_checkins WHERE plan_id = #{planId} ORDER BY checkin_date DESC, created_at DESC")
    List<PlanCheckin> selectListByPlanId(@Param("planId") Long planId);
    
    @Select("SELECT COUNT(*) FROM plan_checkins WHERE plan_id = #{planId}")
    long countByPlanId(@Param("planId") Long planId);

    @Select("SELECT COUNT(*) FROM plan_checkins WHERE plan_id = #{planId} AND user_id = #{userId}")
    long countByPlanIdAndUserId(@Param("planId") Long planId, @Param("userId") Long userId);
    
    @Delete("DELETE FROM plan_checkins WHERE plan_id = #{planId}")
    int deleteByPlanId(@Param("planId") Long planId);
}
