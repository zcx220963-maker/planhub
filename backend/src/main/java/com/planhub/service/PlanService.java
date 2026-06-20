package com.planhub.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.planhub.dto.request.CheckinRequest;
import com.planhub.dto.request.CreatePlanRequest;
import com.planhub.dto.request.UpdatePlanRequest;
import com.planhub.entity.Plan;
import com.planhub.entity.PlanCheckin;

import java.time.LocalDate;

public interface PlanService {
    Plan create(Long userId, CreatePlanRequest request);

    Plan getById(Long planId);

    Plan getByIdAndUserId(Long planId, Long userId);

    IPage<Plan> getByUserId(Long userId, String status, String category, String priority, int page, int size);

    IPage<Plan> getPublicPlans(Long excludeUserId, String search, int page, int size);

    IPage<Plan> getUserPlansWithSearch(Long userId, String search, int page, int size);

    Plan update(Long planId, Long userId, Plan updatePlan);

    Plan update(Long planId, Long userId, UpdatePlanRequest request);

    void delete(Long planId, Long userId);

    PlanCheckin checkin(Long planId, Long userId, CheckinRequest request);

    IPage<PlanCheckin> getCheckinsByPlan(Long planId, int page, int size);

    boolean existsCheckin(Long planId, Long userId, LocalDate date);

    long countCheckinsByPlanAndUser(Long planId, Long userId);
}
