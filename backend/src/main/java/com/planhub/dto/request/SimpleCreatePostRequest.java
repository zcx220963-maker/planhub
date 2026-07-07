package com.planhub.dto.request;

import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SimpleCreatePostRequest {
    @NotBlank(message = "内容不能为空")
    private String content;
    
    private String imageUrl;
}