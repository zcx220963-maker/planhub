package com.planhub.dto.request;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UpdatePrivacySettingsRequest {
    private Boolean showActivities;
    private Boolean showFollowers;
    private Boolean showFollowing;
    private Boolean showLikedContent;
}
