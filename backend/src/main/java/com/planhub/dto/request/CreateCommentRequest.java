package com.planhub.dto.request;

import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class CreateCommentRequest {
    private String content;
    
    private List<Long> mentions;
    
    private Long parentCommentId;
    
    private List<String> mediaUrls;
}
