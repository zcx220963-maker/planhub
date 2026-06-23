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
public class CreatePostRequest {
    private String content;
    
    private String postType = "text";
    
    private List<String> hashtags;
    
    private List<Long> mentions;
    
    private String location;
    
    private String privacy = "public";
    
    private List<String> mediaUrls;
    
    private Long linkedPlanId;
}
