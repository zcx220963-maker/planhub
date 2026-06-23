package com.planhub.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.planhub.dto.request.CheckinRequest;
import com.planhub.dto.request.CreatePlanRequest;
import com.planhub.dto.request.UpdatePlanRequest;
import com.planhub.dto.response.ApiResponse;
import com.planhub.dto.response.PostDetailResponse;
import com.planhub.entity.Plan;
import com.planhub.entity.PlanCheckin;
import com.planhub.entity.User;
import com.planhub.mapper.UserMapper;
import com.planhub.service.PlanService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/plans")
@RequiredArgsConstructor
public class PlanController {
    private final PlanService planService;
    private final UserMapper userMapper;

    @GetMapping
    public ResponseEntity<ApiResponse<List<Plan>>> getPlans(
            Authentication authentication,
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String category,
            @RequestParam(required = false) String priority,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "100") int size) {
        // 检查是否已认证，未认证则返回空列表
        if (authentication == null || authentication.getPrincipal() == null) {
            return ResponseEntity.ok(ApiResponse.success(java.util.Collections.emptyList()));
        }
        Long userId = (Long) authentication.getPrincipal();
        IPage<Plan> plans = planService.getByUserId(userId, status, category, priority, page, size);
        return ResponseEntity.ok(ApiResponse.success(plans.getRecords()));
    }

    @GetMapping("/user/{userId}")
    public ResponseEntity<ApiResponse<IPage<PostDetailResponse.PlanInfoResponse>>> getUserPlans(
            @PathVariable Long userId,
            @RequestParam(required = false) String search,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "100") int size) {
        IPage<Plan> plans = planService.getUserPlansWithSearch(userId, search, page, size);
        
        // 获取所有计划的创建者信息
        Set<Long> userIds = plans.getRecords().stream()
                .map(Plan::getUserId)
                .collect(Collectors.toSet());
        Map<Long, User> userMap = userIds.isEmpty() ? Map.of() : 
            userMapper.selectBatchIds(new java.util.ArrayList<>(userIds)).stream()
                .collect(Collectors.toMap(User::getId, u -> u));
        
        // 构建响应
        List<PostDetailResponse.PlanInfoResponse> responses = plans.getRecords().stream()
                .map(plan -> buildPlanInfoResponse(plan, userMap.get(plan.getUserId())))
                .collect(Collectors.toList());
        
        IPage<PostDetailResponse.PlanInfoResponse> responsePage = new com.baomidou.mybatisplus.extension.plugins.pagination.Page<>(
                plans.getCurrent(), plans.getSize(), plans.getTotal());
        responsePage.setRecords(responses);
        
        return ResponseEntity.ok(ApiResponse.success(responsePage));
    }

    @GetMapping("/user/me")
    public ResponseEntity<ApiResponse<IPage<PostDetailResponse.PlanInfoResponse>>> getMyPlans(
            Authentication authentication,
            @RequestParam(required = false) String search,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "100") int size) {
        Long userId = (Long) authentication.getPrincipal();
        IPage<Plan> plans = planService.getUserPlansWithSearch(userId, search, page, size);
        
        // 获取所有计划的创建者信息
        Set<Long> userIds = plans.getRecords().stream()
                .map(Plan::getUserId)
                .collect(Collectors.toSet());
        Map<Long, User> userMap = userIds.isEmpty() ? Map.of() : 
            userMapper.selectBatchIds(new java.util.ArrayList<>(userIds)).stream()
                .collect(Collectors.toMap(User::getId, u -> u));
        
        // 构建响应
        List<PostDetailResponse.PlanInfoResponse> responses = plans.getRecords().stream()
                .map(plan -> buildPlanInfoResponse(plan, userMap.get(plan.getUserId())))
                .collect(Collectors.toList());
        
        IPage<PostDetailResponse.PlanInfoResponse> responsePage = new com.baomidou.mybatisplus.extension.plugins.pagination.Page<>(
                plans.getCurrent(), plans.getSize(), plans.getTotal());
        responsePage.setRecords(responses);
        
        return ResponseEntity.ok(ApiResponse.success(responsePage));
    }

    @GetMapping("/public")
    public ResponseEntity<ApiResponse<IPage<PostDetailResponse.PlanInfoResponse>>> getPublicPlans(
            Authentication authentication,
            @RequestParam(required = false) String search,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "100") int size) {
        Long userId = (Long) authentication.getPrincipal();
        IPage<Plan> plans = planService.getPublicPlans(userId, search, page, size);
        
        // 获取所有计划的创建者信息
        Set<Long> userIds = plans.getRecords().stream()
                .map(Plan::getUserId)
                .collect(Collectors.toSet());
        Map<Long, User> userMap = userIds.isEmpty() ? Map.of() : 
            userMapper.selectBatchIds(new java.util.ArrayList<>(userIds)).stream()
                .collect(Collectors.toMap(User::getId, u -> u));
        
        // 构建响应
        List<PostDetailResponse.PlanInfoResponse> responses = plans.getRecords().stream()
                .map(plan -> buildPlanInfoResponse(plan, userMap.get(plan.getUserId())))
                .collect(Collectors.toList());
        
        IPage<PostDetailResponse.PlanInfoResponse> responsePage = new com.baomidou.mybatisplus.extension.plugins.pagination.Page<>(
                plans.getCurrent(), plans.getSize(), plans.getTotal());
        responsePage.setRecords(responses);
        
        return ResponseEntity.ok(ApiResponse.success(responsePage));
    }
    
    private PostDetailResponse.PlanInfoResponse buildPlanInfoResponse(Plan plan, User owner) {
        PostDetailResponse.UserResponse ownerResponse = owner != null ?
            PostDetailResponse.UserResponse.builder()
                .id(owner.getId())
                .username(owner.getUsername())
                .displayName(owner.getDisplayName())
                .avatarUrl(owner.getAvatarUrl())
                .build() : null;
        
        return PostDetailResponse.PlanInfoResponse.builder()
                .id(plan.getId())
                .title(plan.getTitle())
                .description(plan.getDescription())
                .category(plan.getCategory() != null ? plan.getCategory().name() : null)
                .status(plan.getStatus() != null ? plan.getStatus().name() : null)
                .progressPercentage(plan.getProgressPercentage())
                .coverImageUrl(plan.getCoverImageUrl())
                .createdAt(plan.getCreatedAt())
                .owner(ownerResponse)
                .build();
    }

    @GetMapping("/{planId}")
    public ResponseEntity<ApiResponse<Plan>> getPlanById(@PathVariable Long planId) {
        Plan plan = planService.getById(planId);
        return ResponseEntity.ok(ApiResponse.success(plan));
    }

    @PostMapping
    public ResponseEntity<ApiResponse<Plan>> createPlan(
            Authentication authentication,
            @Valid @RequestBody CreatePlanRequest request) {
        // 支持可选认证，未登录用户返回错误
        if (authentication == null || authentication.getPrincipal() == null) {
            return ResponseEntity.status(401).body(ApiResponse.error("请先登录才能创建计划"));
        }
        Long userId = (Long) authentication.getPrincipal();
        Plan plan = planService.create(userId, request);
        return ResponseEntity.ok(ApiResponse.success(plan, "计划创建成功"));
    }

    @PutMapping("/{planId}")
    public ResponseEntity<ApiResponse<Plan>> updatePlan(
            Authentication authentication,
            @PathVariable Long planId,
            @RequestBody UpdatePlanRequest request) {
        Long userId = (Long) authentication.getPrincipal();
        Plan plan = planService.update(planId, userId, request);
        return ResponseEntity.ok(ApiResponse.success(plan, "计划更新成功"));
    }

    @DeleteMapping("/{planId}")
    public ResponseEntity<ApiResponse<Void>> deletePlan(
            Authentication authentication,
            @PathVariable Long planId) {
        Long userId = (Long) authentication.getPrincipal();
        planService.delete(planId, userId);
        return ResponseEntity.ok(ApiResponse.success(null, "计划删除成功"));
    }

    @PostMapping("/{planId}/checkins")
    public ResponseEntity<ApiResponse<PlanCheckin>> checkin(
            Authentication authentication,
            @PathVariable Long planId,
            @RequestBody CheckinRequest request) {
        // 支持可选认证，未登录用户返回错误
        if (authentication == null || authentication.getPrincipal() == null) {
            return ResponseEntity.status(401).body(ApiResponse.error("请先登录才能打卡"));
        }
        Long userId = (Long) authentication.getPrincipal();
        PlanCheckin checkin = planService.checkin(planId, userId, request);
        return ResponseEntity.ok(ApiResponse.success(checkin, "打卡成功"));
    }

    @GetMapping("/{planId}/checkins")
    public ResponseEntity<ApiResponse<List<PlanCheckin>>> getCheckins(
            @PathVariable Long planId,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size) {
        IPage<PlanCheckin> checkins = planService.getCheckinsByPlan(planId, page, size);
        return ResponseEntity.ok(ApiResponse.success(checkins.getRecords()));
    }

    @GetMapping("/{planId}/checkins/exists")
    public ResponseEntity<ApiResponse<Boolean>> checkCheckinExists(
            Authentication authentication,
            @PathVariable Long planId,
            @RequestParam(required = false) LocalDate date) {
        Long userId = (Long) authentication.getPrincipal();
        LocalDate checkDate = date != null ? date : LocalDate.now();
        boolean exists = planService.existsCheckin(planId, userId, checkDate);
        return ResponseEntity.ok(ApiResponse.success(exists));
    }

    @GetMapping("/{planId}/checkins/count")
    public ResponseEntity<ApiResponse<Long>> getCheckinCount(
            Authentication authentication,
            @PathVariable Long planId) {
        Long userId = (Long) authentication.getPrincipal();
        long count = planService.countCheckinsByPlanAndUser(planId, userId);
        return ResponseEntity.ok(ApiResponse.success(count));
    }
}
