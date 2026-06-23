package com.planhub.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.planhub.dto.response.ActivityResponse;
import com.planhub.entity.Activity;

import java.util.List;

public interface ActivityService {

    Activity createActivity(Long userId, String type, Long targetId, String targetType, String content);

    List<ActivityResponse> getActivitiesByUserId(Long userId);

    IPage<ActivityResponse> getActivitiesByUserId(Long userId, int page, int size);

    void deleteActivity(Long activityId, Long userId);

    void deleteActivities(List<Long> activityIds, Long userId);
}
