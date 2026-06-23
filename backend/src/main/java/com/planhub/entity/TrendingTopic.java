package com.planhub.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "trending_topics")
@TableName("trending_topics")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TrendingTopic {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "tag_name", nullable = false, length = 50)
    private String tagName;

    @Column(name = "display_name", length = 100)
    private String displayName;

    @Column(name = "topic_type", length = 20)
    @Builder.Default
    private String topicType = "hashtag";

    @Column(name = "post_count")
    @Builder.Default
    private Integer postCount = 0;

    @Column(name = "engagement_score", precision = 10, scale = 2)
    @Builder.Default
    private BigDecimal engagementScore = BigDecimal.ZERO;

    @Column(name = "trend_direction", length = 20)
    @Builder.Default
    private String trendDirection = "stable";

    @Column(name = "last_updated")
    @Builder.Default
    private LocalDateTime lastUpdated = LocalDateTime.now();

    @Column(name = "is_featured")
    @Builder.Default
    private Boolean isFeatured = false;
}
