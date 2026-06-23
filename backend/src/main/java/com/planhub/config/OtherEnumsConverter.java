package com.planhub.config;

import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

// 注释掉枚举转换器，因为 TrendingTopic 使用字符串类型而不是枚举类型
// @Converter(autoApply = true)
// class TopicTypeConverter implements AttributeConverter<TopicType, String> {
//     @Override
//     public String convertToDatabaseColumn(TopicType attribute) {
//         return attribute != null ? attribute.name() : null;
//     }
// 
//     @Override
//     public TopicType convertToEntityAttribute(String dbData) {
//         if (dbData == null || dbData.trim().isEmpty()) {
//             return TopicType.HASHTAG;
//         }
//         try {
//             return TopicType.valueOf(dbData.toUpperCase().trim());
//         } catch (IllegalArgumentException e) {
//             return TopicType.HASHTAG;
//         }
//     }
// }

// @Converter(autoApply = true)
// class TrendDirectionConverter implements AttributeConverter<TrendDirection, String> {
//     @Override
//     public String convertToDatabaseColumn(TrendDirection attribute) {
//         return attribute != null ? attribute.name() : null;
//     }
// 
//     @Override
//     public TrendDirection convertToEntityAttribute(String dbData) {
//         if (dbData == null || dbData.trim().isEmpty()) {
//             return TrendDirection.STABLE;
//         }
//         try {
//             return TrendDirection.valueOf(dbData.toUpperCase().trim());
//         } catch (IllegalArgumentException e) {
//             return TrendDirection.STABLE;
//         }
//     }
// }
