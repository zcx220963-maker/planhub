
package com.planhub.dto.request;

import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SharePlanRequest {
    @Size(max = 1000, message = "分享内容不能超过1000字")
    private String content;
}
