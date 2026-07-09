package com.planhub.dto.response;

import com.planhub.entity.User;
import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 用户公开信息 DTO
 * 仅暴露可公开访问的字段，排除 passwordHash、email、phoneNumber 等敏感信息
 */
@Data
@Builder
public class UserPublicDTO {
    private Long id;
    private String username;
    private String displayName;
    private String avatarUrl;
    private String bio;
    private String location;
    private String websiteUrl;
    private User.Gender gender;
    private LocalDateTime createdAt;

    /**
     * 从 User 实体转换为公开 DTO，只复制安全字段
     */
    public static UserPublicDTO fromEntity(User user) {
        if (user == null) return null;
        return UserPublicDTO.builder()
                .id(user.getId())
                .username(user.getUsername())
                .displayName(user.getDisplayName())
                .avatarUrl(user.getAvatarUrl())
                .bio(user.getBio())
                .location(user.getLocation())
                .websiteUrl(user.getWebsiteUrl())
                .gender(user.getGender())
                .createdAt(user.getCreatedAt())
                .build();
    }
}
