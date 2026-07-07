package com.planhub.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.planhub.dto.response.ActivityResponse;
import com.planhub.dto.response.ApiResponse;
import com.planhub.service.ActivityService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/activities")
@RequiredArgsConstructor
public class ActivityController {

    private final ActivityService activityService;

    @GetMapping
    public ApiResponse<IPage<ActivityResponse>> getActivities(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            Authentication authentication) {
        Long userId = Long.parseLong(authentication.getName());
        IPage<ActivityResponse> activities = activityService.getActivitiesByUserId(userId, page, size);
        return ApiResponse.success(activities);
    }

    @DeleteMapping("/{activityId}")
    public ApiResponse<Void> deleteActivity(
            @PathVariable Long activityId,
            Authentication authentication) {
        Long userId = Long.parseLong(authentication.getName());
        activityService.deleteActivity(activityId, userId);
        return ApiResponse.success(null, "删除成功");
    }

    @DeleteMapping("/batch")
    public ApiResponse<Void> deleteActivities(
            @RequestBody List<Long> activityIds,
            Authentication authentication) {
        Long userId = Long.parseLong(authentication.getName());
        activityService.deleteActivities(activityIds, userId);
        return ApiResponse.success(null, "删除成功");
    }
}