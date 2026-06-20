package com.planhub.config;

import com.planhub.entity.Plan.Category;
import com.planhub.entity.Plan.Priority;
import com.planhub.entity.Plan.Status;
import com.planhub.entity.Plan.Visibility;
import com.planhub.entity.Post.PostType;
import com.planhub.entity.Post.Privacy;
import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

@Converter(autoApply = true)
public class PlanStatusConverter implements AttributeConverter<Status, String> {
    @Override
    public String convertToDatabaseColumn(Status attribute) {
        return attribute != null ? attribute.name() : null;
    }

    @Override
    public Status convertToEntityAttribute(String dbData) {
        if (dbData == null || dbData.trim().isEmpty()) {
            return Status.PENDING;
        }
        try {
            return Status.valueOf(dbData.toUpperCase().trim());
        } catch (IllegalArgumentException e) {
            return Status.PENDING;
        }
    }
}

@Converter(autoApply = true)
class PlanCategoryConverter implements AttributeConverter<Category, String> {
    @Override
    public String convertToDatabaseColumn(Category attribute) {
        return attribute != null ? attribute.name() : null;
    }

    @Override
    public Category convertToEntityAttribute(String dbData) {
        if (dbData == null || dbData.trim().isEmpty()) {
            return Category.PERSONAL;
        }
        try {
            return Category.valueOf(dbData.toUpperCase().trim());
        } catch (IllegalArgumentException e) {
            return Category.PERSONAL;
        }
    }
}

@Converter(autoApply = true)
class PlanPriorityConverter implements AttributeConverter<Priority, String> {
    @Override
    public String convertToDatabaseColumn(Priority attribute) {
        return attribute != null ? attribute.name() : null;
    }

    @Override
    public Priority convertToEntityAttribute(String dbData) {
        if (dbData == null || dbData.trim().isEmpty()) {
            return Priority.MEDIUM;
        }
        try {
            return Priority.valueOf(dbData.toUpperCase().trim());
        } catch (IllegalArgumentException e) {
            return Priority.MEDIUM;
        }
    }
}

@Converter(autoApply = true)
class PlanVisibilityConverter implements AttributeConverter<Visibility, String> {
    @Override
    public String convertToDatabaseColumn(Visibility attribute) {
        return attribute != null ? attribute.name() : null;
    }

    @Override
    public Visibility convertToEntityAttribute(String dbData) {
        if (dbData == null || dbData.trim().isEmpty()) {
            return Visibility.PRIVATE;
        }
        try {
            return Visibility.valueOf(dbData.toUpperCase().trim());
        } catch (IllegalArgumentException e) {
            return Visibility.PRIVATE;
        }
    }
}

@Converter(autoApply = true)
class PostTypeConverter implements AttributeConverter<PostType, String> {
    @Override
    public String convertToDatabaseColumn(PostType attribute) {
        return attribute != null ? attribute.name() : null;
    }

    @Override
    public PostType convertToEntityAttribute(String dbData) {
        if (dbData == null || dbData.trim().isEmpty()) {
            return PostType.TEXT;
        }
        try {
            return PostType.valueOf(dbData.toUpperCase().trim());
        } catch (IllegalArgumentException e) {
            return PostType.TEXT;
        }
    }
}

@Converter(autoApply = true)
class PostPrivacyConverter implements AttributeConverter<Privacy, String> {
    @Override
    public String convertToDatabaseColumn(Privacy attribute) {
        return attribute != null ? attribute.name() : null;
    }

    @Override
    public Privacy convertToEntityAttribute(String dbData) {
        if (dbData == null || dbData.trim().isEmpty()) {
            return Privacy.PUBLIC;
        }
        try {
            return Privacy.valueOf(dbData.toUpperCase().trim());
        } catch (IllegalArgumentException e) {
            return Privacy.PUBLIC;
        }
    }
}
