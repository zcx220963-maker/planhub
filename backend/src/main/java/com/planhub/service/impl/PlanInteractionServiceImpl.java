
package com.planhub.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.planhub.entity.Activity;
import com.planhub.entity.Plan;
import com.planhub.entity.PlanInteraction;
import com.planhub.entity.Post;
import com.planhub.exception.BusinessException;
import com.planhub.exception.ResourceNotFoundException;
import com.planhub.mapper.PlanInteractionMapper;
import com.planhub.mapper.PlanMapper;
import com.planhub.mapper.PostMapper;
import com.planhub.service.ActivityService;
import com.planhub.service.PlanInteractionService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Slf4j
public class PlanInteractionServiceImpl implements PlanInteractionService {
    private final PlanInteractionMapper planInteractionMapper;
    private final PlanMapper planMapper;
    private final PostMapper postMapper;
    private final ActivityService activityService;

    @Override
    @Transactional
    public void likePlan(Long userId, Long planId) {
        Plan plan = planMapper.selectById(planId);
        if (plan == null || plan.getDeletedAt() != null) {
            throw new ResourceNotFoundException("计划", "id", planId);
        }

        if (!Plan.Visibility.PUBLIC.equals(plan.getVisibility()) && !plan.getUserId().equals(userId)) {
            throw new BusinessException("只能点赞公开计划或自己的计划");
        }

        LambdaQueryWrapper<PlanInteraction> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(PlanInteraction::getPlanId, planId)
                .eq(PlanInteraction::getUserId, userId)
                .eq(PlanInteraction::getInteractionType, PlanInteraction.InteractionType.LIKE.name().toLowerCase());
        
        PlanInteraction existing = planInteractionMapper.selectOne(wrapper);
        if (existing == null) {
            PlanInteraction interaction = PlanInteraction.builder()
                    .planId(planId)
                    .userId(userId)
                    .interactionType(PlanInteraction.InteractionType.LIKE.name().toLowerCase())
                    .build();
            planInteractionMapper.insert(interaction);
            if (!userId.equals(plan.getUserId())) {
                activityService.createActivity(userId, "POST_LIKED", planId, "PLAN", null);
            }
        }
    }

    @Override
    @Transactional
    public void unlikePlan(Long userId, Long planId) {
        LambdaQueryWrapper<PlanInteraction> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(PlanInteraction::getPlanId, planId)
                .eq(PlanInteraction::getUserId, userId)
                .eq(PlanInteraction::getInteractionType, PlanInteraction.InteractionType.LIKE.name().toLowerCase());
        planInteractionMapper.delete(wrapper);
    }

    @Override
    @Transactional
    public void sharePlanToCommunity(Long userId, Long planId, String content) {
        Plan plan = planMapper.selectById(planId);
        if (plan == null || plan.getDeletedAt() != null) {
            throw new ResourceNotFoundException("计划", "id", planId);
        }

        if (!Plan.Visibility.PUBLIC.equals(plan.getVisibility()) && !plan.getUserId().equals(userId)) {
            throw new BusinessException("只能分享公开计划或自己的计划");
        }

        Post post = Post.builder()
                .userId(userId)
                .content(content != null ? content : "分享了一个计划：" + plan.getTitle())
                .linkedPlanId(planId)
                .postType("text")
                .privacy("public")
                .build();
        postMapper.insert(post);

        LambdaQueryWrapper<PlanInteraction> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(PlanInteraction::getPlanId, planId)
                .eq(PlanInteraction::getUserId, userId)
                .eq(PlanInteraction::getInteractionType, PlanInteraction.InteractionType.SHARE.name().toLowerCase());
        
        PlanInteraction existing = planInteractionMapper.selectOne(wrapper);
        if (existing == null) {
            PlanInteraction interaction = PlanInteraction.builder()
                    .planId(planId)
                    .userId(userId)
                    .interactionType(PlanInteraction.InteractionType.SHARE.name().toLowerCase())
                    .build();
            planInteractionMapper.insert(interaction);
        }
    }

    @Override
    public boolean hasLiked(Long userId, Long planId) {
        LambdaQueryWrapper<PlanInteraction> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(PlanInteraction::getPlanId, planId)
                .eq(PlanInteraction::getUserId, userId)
                .eq(PlanInteraction::getInteractionType, PlanInteraction.InteractionType.LIKE.name().toLowerCase());
        return planInteractionMapper.selectCount(wrapper) > 0;
    }

    @Override
    public Integer getLikeCount(Long planId) {
        return planInteractionMapper.countLikesByPlanId(planId);
    }

    @Override
    public Integer getShareCount(Long planId) {
        return planInteractionMapper.countSharesByPlanId(planId);
    }
}
