
package com.planhub.service;

public interface PlanInteractionService {
    void likePlan(Long userId, Long planId);
    void unlikePlan(Long userId, Long planId);
    void sharePlanToCommunity(Long userId, Long planId, String content);
    boolean hasLiked(Long userId, Long planId);
    Integer getLikeCount(Long planId);
    Integer getShareCount(Long planId);
}
