package com.planhub.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "plans")
@TableName("plans")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Plan {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(nullable = false, length = 200)
    private String title;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(length = 20)
    @Builder.Default
    private Category category = Category.PERSONAL;

    @Column(length = 20)
    @Builder.Default
    private Priority priority = Priority.MEDIUM;

    @Column(length = 20)
    @Builder.Default
    private Status status = Status.DRAFT;

    @Column(name = "target_date")
    private LocalDate targetDate;

    @Column(name = "start_date")
    private LocalDate startDate;

    @Column(name = "estimated_duration_hours")
    @Builder.Default
    private Integer estimatedDurationHours = 0;

    @Column(name = "actual_duration_hours")
    @Builder.Default
    private Integer actualDurationHours = 0;

    @Column(name = "progress_percentage", precision = 5, scale = 2)
    @Builder.Default
    private BigDecimal progressPercentage = BigDecimal.ZERO;

    @Column(columnDefinition = "JSON")
    private String tags;

    @Column(name = "cover_image_url", length = 255)
    private String coverImageUrl;

    @Column(name = "reminder_settings", columnDefinition = "JSON")
    private String reminderSettings;

    @Column(name = "sharing_settings", columnDefinition = "JSON")
    private String sharingSettings;

    @Column(length = 20)
    @Builder.Default
    private Visibility visibility = Visibility.PRIVATE;

    @Column(name = "completion_criteria", columnDefinition = "JSON")
    private String completionCriteria;

    @Column(name = "created_at")
    @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(name = "updated_at")
    @Builder.Default
    private LocalDateTime updatedAt = LocalDateTime.now();

    @Column(name = "completed_at")
    private LocalDateTime completedAt;

    @Column(name = "deleted_at")
    private LocalDateTime deletedAt;

    public enum Category {
        LEARNING, FITNESS, HABIT, CAREER, PERSONAL, HEALTH, CREATIVE, OTHER
    }

    public enum Priority {
        LOW, MEDIUM, HIGH, URGENT
    }

    public enum Status {
        DRAFT, PENDING, ACTIVE, COMPLETED, PAUSED, CANCELLED
    }

    public enum Visibility {
        PRIVATE, PUBLIC, FRIENDS
    }
}
