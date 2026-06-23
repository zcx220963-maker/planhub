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
@Table(name = "plan_checkins")
@TableName("plan_checkins")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PlanCheckin {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "plan_id", nullable = false)
    private Long planId;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "checkin_date", nullable = false)
    private LocalDate checkinDate;

    @Column(columnDefinition = "TEXT")
    private String notes;

    @Column(name = "mood_rating")
    private Integer moodRating;

    @Column(name = "energy_rating")
    private Integer energyRating;

    @Column(name = "progress_notes", columnDefinition = "TEXT")
    private String progressNotes;

    @Column(columnDefinition = "JSON")
    private String photos;

    @Column(columnDefinition = "JSON")
    private String tags;

    @Column(name = "created_at")
    @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();
}
