package com.planhub.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.planhub.entity.PlanMilestone;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface PlanMilestoneMapper extends BaseMapper<PlanMilestone> {

    @Select("SELECT * FROM plan_milestones WHERE plan_id = #{planId} ORDER BY order_index")
    List<PlanMilestone> findByPlanIdOrderByOrderIndex(Long planId);

    @Select("SELECT * FROM plan_milestones WHERE plan_id = #{planId} AND is_completed = #{isCompleted}")
    List<PlanMilestone> findByPlanIdAndIsCompleted(Long planId, Boolean isCompleted);

    @Select("SELECT COUNT(*) FROM plan_milestones WHERE plan_id = #{planId}")
    long countByPlanId(Long planId);
}
