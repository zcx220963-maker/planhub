package com.planhub.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;

@Entity
@Table(name = "posts")
@TableName("posts")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Post {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(columnDefinition = "TEXT", nullable = false)
    private String content;

    @Column(name = "original_post_id")
    private Long originalPostId;

    @Column(name = "original_author_id")
    private Long originalAuthorId;

    @Column(name = "linked_plan_id")
    private Long linkedPlanId;

    @Column(name = "post_type", length = 20)
    @Builder.Default
    private String postType = "TEXT";

    @Column(name = "media_urls", columnDefinition = "JSON")
    private String mediaUrls;

    @Column(columnDefinition = "JSON")
    private String hashtags;

    @Column(columnDefinition = "JSON")
    private String mentions;

    @Column(length = 100)
    private String location;

    @Column(length = 20)
    @Builder.Default
    private String privacy = "PUBLIC";

    @Column(name = "view_count")
    @Builder.Default
    private Integer viewCount = 0;

    @Column(name = "created_at")
    @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(name = "updated_at")
    @Builder.Default
    private LocalDateTime updatedAt = LocalDateTime.now();

    @Column(name = "deleted_at")
    private LocalDateTime deletedAt;

    public enum PostType {
        TEXT, IMAGE, VIDEO, LINK, POLL
    }

    public enum Privacy {
        PUBLIC, FRIENDS, PRIVATE
    }
}
