
package com.planhub.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "plan_interactions")
@TableName("plan_interactions")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PlanInteraction {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "plan_id", nullable = false)
    private Long planId;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "interaction_type", nullable = false, length = 20)
    private String interactionType;

    @Column(columnDefinition = "JSON")
    private String metadata;

    @Column(name = "created_at")
    @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();

    public enum InteractionType {
        LIKE, BOOKMARK, SHARE, REPORT
    }
}
