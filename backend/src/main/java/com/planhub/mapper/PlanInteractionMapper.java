
package com.planhub.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.planhub.entity.PlanInteraction;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface PlanInteractionMapper extends BaseMapper<PlanInteraction> {
    
    @Select("SELECT COUNT(*) FROM plan_interactions WHERE plan_id = #{planId} AND interaction_type = 'like'")
    Integer countLikesByPlanId(@Param("planId") Long planId);
    
    @Select("SELECT COUNT(*) FROM plan_interactions WHERE plan_id = #{planId} AND interaction_type = 'share'")
    Integer countSharesByPlanId(@Param("planId") Long planId);
    
    @Select("SELECT pi.* FROM plan_interactions pi " +
            "WHERE pi.user_id = #{userId} AND pi.interaction_type = 'like' " +
            "ORDER BY pi.created_at DESC")
    List<PlanInteraction> findLikedPlansByUserId(@Param("userId") Long userId);
}
