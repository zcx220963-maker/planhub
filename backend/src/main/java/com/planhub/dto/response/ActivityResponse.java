package com.planhub.dto.response;

import com.planhub.entity.Activity;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ActivityResponse {
    private Long id;
    private Long userId;
    private String type;
    private Long targetId;
    private String targetType;
    private String content;
    private String displayText;
    private String createdAt;

    public static ActivityResponse fromEntity(Activity activity) {
        String displayText = generateDisplayText(activity);
        return ActivityResponse.builder()
                .id(activity.getId())
                .userId(activity.getUserId())
                .type(activity.getType())
                .targetId(activity.getTargetId())
                .targetType(activity.getTargetType())
                .content(activity.getContent())
                .displayText(displayText)
                .createdAt(formatDateTime(activity.getCreatedAt()))
                .build();
    }

    private static String generateDisplayText(Activity activity) {
        String content = activity.getContent() != null ? activity.getContent() : "";
        String type = activity.getType();
        if (type == null) return content;
        switch (type.toUpperCase()) {
            case "PLAN_CREATED":
                return "创建了新计划「" + content + "」";
            case "PLAN_COMPLETED":
                return "完成了计划「" + content + "」";
            case "PLAN_CHECKIN":
                return "在计划「" + content + "」中打卡";
            case "POST_LIKED":
                return "点赞了一篇社区帖子";
            case "POST_COMMENTED":
                return "评论了一篇帖子";
            case "COMMENT_LIKED":
                return "点赞了一条评论";
            case "COMMENT_REPLIED":
                return "回复了一条评论";
            default:
                return content;
        }
    }

    private static String formatDateTime(LocalDateTime dateTime) {
        if (dateTime == null) return "";
        LocalDateTime now = LocalDateTime.now();
        java.time.Duration duration = java.time.Duration.between(dateTime, now);
        
        long days = duration.toDays();
        long hours = duration.toHours();
        long minutes = duration.toMinutes();
        
        if (minutes < 1) return "刚刚";
        if (minutes < 60) return minutes + "分钟前";
        if (hours < 24) return hours + "小时前";
        if (days < 7) return days + "天前";
        
        return dateTime.format(DateTimeFormatter.ofPattern("yyyy-MM-dd"));
    }
}