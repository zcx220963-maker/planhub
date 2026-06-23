
package com.planhub.controller;

import com.planhub.dto.request.SharePlanRequest;
import com.planhub.dto.response.ApiResponse;
import com.planhub.service.PlanInteractionService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/plans/{planId}")
@RequiredArgsConstructor
public class PlanInteractionController {
    private final PlanInteractionService planInteractionService;

    @PostMapping("/like")
    public ResponseEntity<ApiResponse<Map<String, Object>>> likePlan(
            Authentication authentication,
            @PathVariable Long planId) {
        Long userId = (Long) authentication.getPrincipal();
        planInteractionService.likePlan(userId, planId);
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("liked", true);
        result.put("likeCount", planInteractionService.getLikeCount(planId));
        return ResponseEntity.ok(ApiResponse.success(result));
    }

    @DeleteMapping("/like")
    public ResponseEntity<ApiResponse<Map<String, Object>>> unlikePlan(
            Authentication authentication,
            @PathVariable Long planId) {
        Long userId = (Long) authentication.getPrincipal();
        planInteractionService.unlikePlan(userId, planId);
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("liked", false);
        result.put("likeCount", planInteractionService.getLikeCount(planId));
        return ResponseEntity.ok(ApiResponse.success(result));
    }

    @PostMapping("/share")
    public ResponseEntity<ApiResponse<Map<String, Object>>> sharePlanToCommunity(
            Authentication authentication,
            @PathVariable Long planId,
            @Valid @RequestBody(required = false) SharePlanRequest request) {
        Long userId = (Long) authentication.getPrincipal();
        String content = request != null ? request.getContent() : null;
        planInteractionService.sharePlanToCommunity(userId, planId, content);
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("message", "分享成功");
        return ResponseEntity.ok(ApiResponse.success(result));
    }

    @GetMapping("/status")
    public ResponseEntity<ApiResponse<Map<String, Object>>> getInteractionStatus(
            Authentication authentication,
            @PathVariable Long planId) {
        Long userId = (Long) authentication.getPrincipal();
        Map<String, Object> result = new HashMap<>();
        result.put("liked", planInteractionService.hasLiked(userId, planId));
        result.put("likeCount", planInteractionService.getLikeCount(planId));
        result.put("shareCount", planInteractionService.getShareCount(planId));
        return ResponseEntity.ok(ApiResponse.success(result));
    }
}
