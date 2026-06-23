package com.planhub.dto.request;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class UpdatePlanRequest {
    private String title;
    
    private String description;
    
    private String category;
    
    private String priority;
    
    private String status;
    
    private LocalDate targetDate;
    
    private LocalDate startDate;
    
    private Integer estimatedDurationHours;
    
    private Integer actualDurationHours;
    
    private Integer progressPercentage;
    
    private String visibility;
    
    private String tags;
    
    private String coverImageUrl;
    
    private String completionCriteria;
    
    private String reminderSettings;
    
    private String sharingSettings;
    
    private LocalDateTime completedAt;
}