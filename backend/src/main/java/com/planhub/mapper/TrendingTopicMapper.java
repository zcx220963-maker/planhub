package com.planhub.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.planhub.entity.TrendingTopic;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;
import java.util.Optional;

@Mapper
public interface TrendingTopicMapper extends BaseMapper<TrendingTopic> {

    @Select("SELECT * FROM trending_topics WHERE tag_name = #{tagName}")
    Optional<TrendingTopic> selectByTagName(String tagName);

    @Select("SELECT * FROM trending_topics WHERE is_featured = true ORDER BY engagement_score DESC")
    List<TrendingTopic> selectByIsFeaturedTrueOrderByEngagementScoreDesc();

    @Select("SELECT * FROM trending_topics WHERE topic_type = #{topicType}")
    List<TrendingTopic> selectByTopicType(String topicType);

    @Select("SELECT * FROM trending_topics ORDER BY engagement_score DESC LIMIT 10")
    List<TrendingTopic> selectTop10ByOrderByEngagementScoreDesc();

    @Select("SELECT * FROM trending_topics")
    List<TrendingTopic> selectAll();
}
