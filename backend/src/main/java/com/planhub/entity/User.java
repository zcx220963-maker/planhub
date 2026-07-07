package com.planhub.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "users")
@TableName("users")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class User {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(unique = true, nullable = false, length = 50)
    private String username;

    @Column(unique = true, nullable = false, length = 100)
    private String email;

    @Column(name = "password_hash", nullable = false, length = 255)
    private String passwordHash;

    @Column(name = "display_name", nullable = false, length = 100)
    private String displayName;

    @Column(name = "avatar_url", length = 255)
    private String avatarUrl;

    @Column(columnDefinition = "TEXT")
    private String bio;

    @Column(length = 100)
    private String location;

    @Column(name = "website_url", length = 255)
    private String websiteUrl;

    @Column(name = "phone_number", length = 20)
    private String phoneNumber;

    @Column(name = "date_of_birth")
    private LocalDate dateOfBirth;

    @Column(length = 20)
    @Builder.Default
    private Gender gender = Gender.PREFER_NOT_TO_SAY;

    @Column(length = 50)
    @Builder.Default
    private String timezone = "Asia/Shanghai";

    @Column(length = 10)
    @Builder.Default
    private String language = "zh-CN";

    @Column(name = "theme_preference", length = 10)
    @Builder.Default
    private ThemePreference themePreference = ThemePreference.LIGHT;

    @Column(name = "color_scheme", length = 10)
    @Builder.Default
    private ColorScheme colorScheme = ColorScheme.BLUE;

    @Column(name = "notification_settings", columnDefinition = "JSON")
    private String notificationSettings;

    @Column(name = "privacy_settings", columnDefinition = "JSON")
    private String privacySettings;

    @Column(name = "account_status", length = 20)
    @Builder.Default
    private AccountStatus accountStatus = AccountStatus.ACTIVE;

    @Column(name = "email_verified")
    @Builder.Default
    private Boolean emailVerified = false;

    @Column(name = "phone_verified")
    @Builder.Default
    private Boolean phoneVerified = false;

    @Column(name = "last_login_at")
    private LocalDateTime lastLoginAt;

    @Column(name = "login_count")
    @Builder.Default
    private Integer loginCount = 0;

    @Column(name = "created_at")
    @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(name = "updated_at")
    @Builder.Default
    private LocalDateTime updatedAt = LocalDateTime.now();

    @Column(name = "deleted_at")
    private LocalDateTime deletedAt;

    public enum Gender {
        MALE, FEMALE, OTHER, PREFER_NOT_TO_SAY
    }

    public enum ThemePreference {
        LIGHT, DARK, AUTO
    }

    public enum ColorScheme {
        BLUE, GREEN, PURPLE, ORANGE
    }

    public enum AccountStatus {
        ACTIVE, SUSPENDED, DELETED
    }
}
