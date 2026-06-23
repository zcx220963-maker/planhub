package com.planhub.dto.request;

import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class CreatePlanRequest {
    @NotBlank(message = "计划标题不能为空")
    private String title;
    
    private String description;
    
    private String category = "personal";
    
    private String priority = "medium";
    
    private LocalDate targetDate;
    
    private LocalDate startDate;
    
    private Integer estimatedDurationHours;
    
    private List<String> tags;
    
    private ReminderSettings reminderSettings;
    
    private String visibility = "private";

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ReminderSettings {
        private Boolean enabled;
        private String frequency;
        private String time;
    }
}
