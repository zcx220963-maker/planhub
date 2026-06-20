package com.planhub.dto.request;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class CheckinRequest {
    private LocalDate checkinDate;
    private String notes;
    private Integer moodRating;
    private Integer energyRating;
    private String progressNotes;
    private List<String> photos;
    private List<String> tags;
}
