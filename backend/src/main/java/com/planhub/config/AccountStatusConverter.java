package com.planhub.config;

import com.planhub.entity.User.AccountStatus;
import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

@Converter(autoApply = true)
public class AccountStatusConverter implements AttributeConverter<AccountStatus, String> {

    @Override
    public String convertToDatabaseColumn(AccountStatus attribute) {
        return attribute != null ? attribute.name() : null;
    }

    @Override
    public AccountStatus convertToEntityAttribute(String dbData) {
        if (dbData == null || dbData.trim().isEmpty()) {
            return AccountStatus.ACTIVE;
        }
        try {
            return AccountStatus.valueOf(dbData.toUpperCase().trim());
        } catch (IllegalArgumentException e) {
            return AccountStatus.ACTIVE;
        }
    }
}
