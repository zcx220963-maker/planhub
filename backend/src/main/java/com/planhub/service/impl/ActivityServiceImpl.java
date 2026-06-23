package com.planhub.service.impl;

import com.planhub.dto.response.ActivityResponse;
import com.planhub.entity.Activity;
import com.planhub.mapper.ActivityMapper;
import com.planhub.service.ActivityService;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class ActivityServiceImpl implements ActivityService {

    private final ActivityMapper activityMapper;

    @Override
    public Activity createActivity(Long userId, String type, Long targetId, String targetType, String content) {
        Activity activity = Activity.builder()
                .userId(userId)
                .type(type)
                .targetId(targetId)
                .targetType(targetType)
                .content(content)
                .build();
        activityMapper.insert(activity);
        return activity;
    }

    @Override
    public List<ActivityResponse> getActivitiesByUserId(Long userId) {
        log.info("=== 开始获取活动记录 === userId={}", userId);
        try {
            List<Activity> activities = activityMapper.selectListByUserIdOrderByCreatedAtDesc(userId);
            log.info("=== 从数据库获取到活动记录数量 === count={}", activities.size());
            List<ActivityResponse> responses = activities.stream()
                    .map(ActivityResponse::fromEntity)
                    .collect(Collectors.toList());
            log.info("=== 成功转换活动记录 === count={}", responses.size());
            return responses;
        } catch (Exception e) {
            log.error("=== 获取活动记录失败 ===", e);
            throw e;
        }
    }

    @Override
    public IPage<ActivityResponse> getActivitiesByUserId(Long userId, int page, int size) {
        Page<Activity> pageParam = new Page<>(page - 1, size);
        return activityMapper.selectByUserIdOrderByCreatedAtDesc(userId, pageParam)
                .convert(ActivityResponse::fromEntity);
    }

    @Override
    public void deleteActivity(Long activityId, Long userId) {
        Activity activity = activityMapper.selectById(activityId);
        if (activity == null) {
            throw new com.planhub.exception.ResourceNotFoundException("活动记录", "id", activityId);
        }
        if (!activity.getUserId().equals(userId)) {
            throw new com.planhub.exception.BusinessException("只能删除自己的活动记录");
        }
        activityMapper.deleteById(activityId);
    }

    @Override
    public void deleteActivities(List<Long> activityIds, Long userId) {
        List<Activity> activities = activityMapper.selectListByUserIdAndIdIn(userId, activityIds);
        if (activities.size() != activityIds.size()) {
            throw new com.planhub.exception.BusinessException("只能删除自己的活动记录");
        }
        activityMapper.deleteBatchIds(activityIds);
    }
}
