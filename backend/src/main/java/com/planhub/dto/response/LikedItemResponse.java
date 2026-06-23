
package com.planhub.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class LikedItemResponse {
    private Long id;
    private String type; // "post" or "plan"
    private String title;
    private String content;
    private String coverImageUrl;
    private String status;
    private LocalDateTime createdAt;
    private LocalDateTime likedAt;
}
