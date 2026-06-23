package com.planhub.service.impl;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.planhub.dto.request.CheckinRequest;
import com.planhub.dto.request.CreatePlanRequest;
import com.planhub.dto.request.UpdatePlanRequest;
import com.planhub.entity.Activity;
import com.planhub.entity.Plan;
import com.planhub.entity.PlanCheckin;
import com.planhub.exception.BusinessException;
import com.planhub.exception.ResourceNotFoundException;
import com.planhub.mapper.PlanCheckinMapper;
import com.planhub.mapper.PlanMapper;
import com.planhub.service.ActivityService;
import com.planhub.service.PlanService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;

@Service
@Transactional
@RequiredArgsConstructor
@Slf4j
public class PlanServiceImpl implements PlanService {
    private final PlanMapper planMapper;
    private final PlanCheckinMapper planCheckinMapper;
    private final ObjectMapper objectMapper;
    private final ActivityService activityService;

    @Override
    public Plan create(Long userId, CreatePlanRequest request) {
        Plan plan = Plan.builder()
                .userId(userId)
                .title(request.getTitle())
                .description(request.getDescription())
                .category(Plan.Category.valueOf(request.getCategory().toUpperCase()))
                .priority(Plan.Priority.valueOf(request.getPriority().toUpperCase()))
                .status(Plan.Status.PENDING)
                .targetDate(request.getTargetDate())
                .startDate(request.getStartDate())
                .estimatedDurationHours(request.getEstimatedDurationHours())
                .visibility(Plan.Visibility.valueOf(request.getVisibility().toUpperCase()))
                .build();

        if (request.getTags() != null) {
            try {
                plan.setTags(objectMapper.writeValueAsString(request.getTags()));
            } catch (JsonProcessingException e) {
                throw new RuntimeException("Failed to serialize tags");
            }
        }

        if (request.getReminderSettings() != null) {
            try {
                plan.setReminderSettings(objectMapper.writeValueAsString(request.getReminderSettings()));
            } catch (JsonProcessingException e) {
                throw new RuntimeException("Failed to serialize reminder settings");
            }
        }

        planMapper.insert(plan);

        activityService.createActivity(userId, "PLAN_CREATED", plan.getId(), "PLAN", plan.getTitle());

        return plan;
    }

    @Override
    public Plan getById(Long planId) {
        Plan plan = planMapper.selectById(planId);
        if (plan == null) {
            throw new ResourceNotFoundException("计划", "id", planId);
        }
        return plan;
    }

    @Override
    public Plan getByIdAndUserId(Long planId, Long userId) {
        Plan plan = planMapper.selectByIdAndUserId(planId, userId);
        if (plan == null) {
            throw new ResourceNotFoundException("计划", "id", planId);
        }
        return plan;
    }

    @Override
    public IPage<Plan> getByUserId(Long userId, String status, String category, String priority, int page, int size) {
        Page<Plan> pageParam = new Page<>(page - 1, size);

        if (status != null && !status.isEmpty()) {
            return planMapper.selectByUserIdAndStatus(userId, status.toUpperCase(), pageParam);
        }
        if (category != null && !category.isEmpty()) {
            return planMapper.selectByUserIdAndCategory(userId, category.toUpperCase(), pageParam);
        }
        if (priority != null && !priority.isEmpty()) {
            return planMapper.selectByUserIdAndPriority(userId, priority.toUpperCase(), pageParam);
        }

        return planMapper.selectByUserId(userId, pageParam);
    }

    @Override
    public IPage<Plan> getPublicPlans(Long excludeUserId, String search, int page, int size) {
        Page<Plan> pageParam = new Page<>(page - 1, size);
        if (search != null && !search.trim().isEmpty()) {
            return planMapper.selectByVisibilityAndUserIdNotAndTitleContainingOrVisibilityAndUserIdNotAndDescriptionContaining(
                    "PUBLIC", excludeUserId, search, "PUBLIC", excludeUserId, search, pageParam);
        }
        return planMapper.selectByVisibilityAndUserIdNotOrderByCreatedAtDesc("PUBLIC", excludeUserId, pageParam);
    }

    @Override
    public IPage<Plan> getUserPlansWithSearch(Long userId, String search, int page, int size) {
        Page<Plan> pageParam = new Page<>(page - 1, size);
        if (search != null && !search.trim().isEmpty()) {
            return planMapper.selectByUserIdAndVisibilityAndTitleContainingOrUserIdAndVisibilityAndDescriptionContaining(
                    userId, "PUBLIC", search, userId, "PUBLIC", search, pageParam);
        }
        return planMapper.selectByUserIdAndVisibility(userId, "PUBLIC", pageParam);
    }

    @Override
    public Plan update(Long planId, Long userId, Plan updatePlan) {
        Plan plan = getByIdAndUserId(planId, userId);

        if (updatePlan.getTitle() != null) {
            plan.setTitle(updatePlan.getTitle());
        }
        if (updatePlan.getDescription() != null) {
            plan.setDescription(updatePlan.getDescription());
        }
        if (updatePlan.getStatus() != null) {
            plan.setStatus(updatePlan.getStatus());
        }
        if (updatePlan.getPriority() != null) {
            plan.setPriority(updatePlan.getPriority());
        }
        if (updatePlan.getCategory() != null) {
            plan.setCategory(updatePlan.getCategory());
        }
        if (updatePlan.getTargetDate() != null) {
            plan.setTargetDate(updatePlan.getTargetDate());
        }
        if (updatePlan.getStartDate() != null) {
            plan.setStartDate(updatePlan.getStartDate());
        }
        if (updatePlan.getEstimatedDurationHours() != null) {
            plan.setEstimatedDurationHours(updatePlan.getEstimatedDurationHours());
        }
        if (updatePlan.getVisibility() != null) {
            plan.setVisibility(updatePlan.getVisibility());
        }
        if (updatePlan.getTags() != null && !updatePlan.getTags().trim().isEmpty()) {
            plan.setTags(updatePlan.getTags());
        }

        planMapper.updateById(plan);
        return plan;
    }

    @Override
    public Plan update(Long planId, Long userId, UpdatePlanRequest request) {
        Plan plan = getByIdAndUserId(planId, userId);

        if (request.getTitle() != null) {
            plan.setTitle(request.getTitle());
        }
        if (request.getDescription() != null) {
            plan.setDescription(request.getDescription());
        }
        if (request.getStatus() != null) {
            plan.setStatus(Plan.Status.valueOf(request.getStatus().toUpperCase().trim()));
        }
        if (request.getPriority() != null) {
            plan.setPriority(Plan.Priority.valueOf(request.getPriority().toUpperCase().trim()));
        }
        if (request.getCategory() != null) {
            plan.setCategory(Plan.Category.valueOf(request.getCategory().toUpperCase().trim()));
        }
        if (request.getTargetDate() != null) {
            plan.setTargetDate(request.getTargetDate());
        }
        if (request.getStartDate() != null) {
            plan.setStartDate(request.getStartDate());
        }
        if (request.getEstimatedDurationHours() != null) {
            plan.setEstimatedDurationHours(request.getEstimatedDurationHours());
        }
        if (request.getVisibility() != null) {
            plan.setVisibility(Plan.Visibility.valueOf(request.getVisibility().toUpperCase().trim()));
        }
        if (request.getTags() != null && !request.getTags().trim().isEmpty()) {
            plan.setTags(request.getTags());
        }
        if (request.getActualDurationHours() != null) {
            plan.setActualDurationHours(request.getActualDurationHours());
        }
        if (request.getProgressPercentage() != null) {
            plan.setProgressPercentage(java.math.BigDecimal.valueOf(request.getProgressPercentage()));
        }
        if (request.getCoverImageUrl() != null) {
            plan.setCoverImageUrl(request.getCoverImageUrl());
        }
        if (request.getCompletionCriteria() != null) {
            plan.setCompletionCriteria(request.getCompletionCriteria());
        }
        if (request.getReminderSettings() != null) {
            plan.setReminderSettings(request.getReminderSettings());
        }
        if (request.getSharingSettings() != null) {
            plan.setSharingSettings(request.getSharingSettings());
        }
        if (request.getCompletedAt() != null) {
            plan.setCompletedAt(request.getCompletedAt());
        }

        planMapper.updateById(plan);
        return plan;
    }

    @Override
    public void delete(Long planId, Long userId) {
        Plan plan = getByIdAndUserId(planId, userId);
        planCheckinMapper.deleteByPlanId(planId);
        planMapper.deleteById(planId);
    }

    @Override
    public PlanCheckin checkin(Long planId, Long userId, CheckinRequest request) {
        LocalDate checkinDate = request.getCheckinDate() != null ? request.getCheckinDate() : LocalDate.now();

        if (planCheckinMapper.existByPlanIdAndUserIdAndCheckinDate(planId, userId, checkinDate)) {
            throw new BusinessException("该用户在此计划中今天已打卡");
        }

        PlanCheckin checkin = PlanCheckin.builder()
                .planId(planId)
                .userId(userId)
                .checkinDate(checkinDate)
                .notes(request.getNotes())
                .moodRating(request.getMoodRating())
                .energyRating(request.getEnergyRating())
                .progressNotes(request.getProgressNotes())
                .build();

        if (request.getPhotos() != null) {
            try {
                checkin.setPhotos(objectMapper.writeValueAsString(request.getPhotos()));
            } catch (JsonProcessingException e) {
                throw new RuntimeException("Failed to serialize photos");
            }
        }

        if (request.getTags() != null) {
            try {
                checkin.setTags(objectMapper.writeValueAsString(request.getTags()));
            } catch (JsonProcessingException e) {
                throw new RuntimeException("Failed to serialize tags");
            }
        }

        planCheckinMapper.insert(checkin);
        updatePlanProgress(planId);

        Plan plan = getById(planId);
        activityService.createActivity(userId, "PLAN_CHECKIN", planId, "PLAN", plan.getTitle());

        return checkin;
    }

    private void updatePlanProgress(Long planId) {
        Plan plan = planMapper.selectById(planId);
        if (plan == null) {
            return;
        }

        boolean wasNotCompleted = plan.getStatus() != Plan.Status.COMPLETED;

        long checkinCount = planCheckinMapper.countByPlanId(planId);

        int planDays = calculatePlanDays(plan);

        if (planDays > 0) {
            long progress = (checkinCount * 100) / planDays;
            plan.setProgressPercentage(java.math.BigDecimal.valueOf(Math.min(progress, 100)));
        } else if (plan.getEstimatedDurationHours() != null && plan.getEstimatedDurationHours() > 0) {
            long progress = (checkinCount * 100) / plan.getEstimatedDurationHours();
            plan.setProgressPercentage(java.math.BigDecimal.valueOf(Math.min(progress, 100)));
        } else {
            plan.setProgressPercentage(java.math.BigDecimal.valueOf(Math.min(checkinCount * 10, 100)));
        }

        if (plan.getProgressPercentage().doubleValue() >= 100) {
            plan.setStatus(Plan.Status.COMPLETED);
            plan.setCompletedAt(java.time.LocalDateTime.now());

            if (wasNotCompleted) {
                activityService.createActivity(plan.getUserId(), "PLAN_COMPLETED", planId, "PLAN", plan.getTitle());
            }
        }

        planMapper.updateById(plan);
    }

    private int calculatePlanDays(Plan plan) {
        if (plan.getStartDate() != null && plan.getTargetDate() != null) {
            return (int) java.time.temporal.ChronoUnit.DAYS.between(plan.getStartDate(), plan.getTargetDate()) + 1;
        }
        return 0;
    }

    @Override
    public IPage<PlanCheckin> getCheckinsByPlan(Long planId, int page, int size) {
        Page<PlanCheckin> pageParam = new Page<>(page - 1, size);
        return planCheckinMapper.selectByPlanId(pageParam, planId);
    }

    @Override
    public boolean existsCheckin(Long planId, Long userId, LocalDate date) {
        return planCheckinMapper.existByPlanIdAndUserIdAndCheckinDate(planId, userId, date);
    }

    @Override
    public long countCheckinsByPlanAndUser(Long planId, Long userId) {
        return planCheckinMapper.countByPlanIdAndUserId(planId, userId);
    }
}
