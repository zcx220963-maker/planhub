package com.planhub.controller;

import com.planhub.dto.response.ApiResponse;
import com.planhub.entity.TrendingTopic;
import com.planhub.mapper.TrendingTopicMapper;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/trending")
public class TrendingController {
    private final TrendingTopicMapper trendingTopicMapper;

    public TrendingController(TrendingTopicMapper trendingTopicMapper) {
        this.trendingTopicMapper = trendingTopicMapper;
    }

    @GetMapping("/topics")
    public ResponseEntity<ApiResponse<List<TrendingTopic>>> getTrendingTopics() {
        List<TrendingTopic> topics = trendingTopicMapper.selectTop10ByOrderByEngagementScoreDesc();
        return ResponseEntity.ok(ApiResponse.success(topics));
    }

    @GetMapping("/topics/featured")
    public ResponseEntity<ApiResponse<List<TrendingTopic>>> getFeaturedTopics() {
        List<TrendingTopic> topics = trendingTopicMapper.selectByIsFeaturedTrueOrderByEngagementScoreDesc();
        return ResponseEntity.ok(ApiResponse.success(topics));
    }
}
