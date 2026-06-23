package com.planhub.config;

import com.planhub.entity.User.Gender;
import com.planhub.entity.User.ThemePreference;
import com.planhub.entity.User.ColorScheme;
import com.planhub.entity.User.AccountStatus;
import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

@Converter(autoApply = true)
public class GenderConverter implements AttributeConverter<Gender, String> {
    @Override
    public String convertToDatabaseColumn(Gender attribute) {
        return attribute != null ? attribute.name() : null;
    }

    @Override
    public Gender convertToEntityAttribute(String dbData) {
        if (dbData == null || dbData.trim().isEmpty()) {
            return Gender.PREFER_NOT_TO_SAY;
        }
        try {
            return Gender.valueOf(dbData.toUpperCase().trim());
        } catch (IllegalArgumentException e) {
            return Gender.PREFER_NOT_TO_SAY;
        }
    }
}

@Converter(autoApply = true)
class ThemePreferenceConverter implements AttributeConverter<ThemePreference, String> {
    @Override
    public String convertToDatabaseColumn(ThemePreference attribute) {
        return attribute != null ? attribute.name() : null;
    }

    @Override
    public ThemePreference convertToEntityAttribute(String dbData) {
        if (dbData == null || dbData.trim().isEmpty()) {
            return ThemePreference.LIGHT;
        }
        try {
            return ThemePreference.valueOf(dbData.toUpperCase().trim());
        } catch (IllegalArgumentException e) {
            return ThemePreference.LIGHT;
        }
    }
}

@Converter(autoApply = true)
class ColorSchemeConverter implements AttributeConverter<ColorScheme, String> {
    @Override
    public String convertToDatabaseColumn(ColorScheme attribute) {
        return attribute != null ? attribute.name() : null;
    }

    @Override
    public ColorScheme convertToEntityAttribute(String dbData) {
        if (dbData == null || dbData.trim().isEmpty()) {
            return ColorScheme.BLUE;
        }
        try {
            return ColorScheme.valueOf(dbData.toUpperCase().trim());
        } catch (IllegalArgumentException e) {
            return ColorScheme.BLUE;
        }
    }
}
