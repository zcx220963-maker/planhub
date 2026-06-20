package com.planhub.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.planhub.dto.response.SearchResponse;
import com.planhub.entity.Plan;
import com.planhub.entity.Post;
import com.planhub.entity.TrendingTopic;
import com.planhub.entity.User;
import com.planhub.mapper.PlanMapper;
import com.planhub.mapper.PostMapper;
import com.planhub.mapper.TrendingTopicMapper;
import com.planhub.mapper.UserMapper;
import com.planhub.service.SearchService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class SearchServiceImpl implements SearchService {
    private final UserMapper userMapper;
    private final PostMapper postMapper;
    private final TrendingTopicMapper trendingTopicMapper;
    private final PlanMapper planMapper;
    private final ObjectMapper objectMapper;

    @Override
    public SearchResponse search(String query, String type, int page, int size) {
        SearchResponse response = new SearchResponse();
        int totalResults = 0;
        Page<User> userPageParam = new Page<>(page - 1, size);
        Page<Post> postPageParam = new Page<>(page - 1, size);
        Page<Plan> planPageParam = new Page<>(page - 1, size);
        
        log.info("Searching for query: {}, type: {}", query, type);

        if ("all".equals(type) || "users".equals(type)) {
            QueryWrapper<User> userQueryWrapper = new QueryWrapper<>();
            userQueryWrapper.like("username", query)
                    .or()
                    .like("display_name", query)
                    .or()
                    .like("email", query);
            
            IPage<User> userPage = userMapper.selectPage(userPageParam, userQueryWrapper);
            List<User> users = userPage.getRecords();

            List<SearchResponse.UserResult> userResults = users.stream()
                    .map(u -> SearchResponse.UserResult.builder()
                            .id(u.getId())
                            .username(u.getUsername())
                            .displayName(u.getDisplayName())
                            .avatarUrl(u.getAvatarUrl())
                            .description(u.getBio())
                            .matchScore(0.95)
                            .build())
                    .collect(Collectors.toList());

            response.setUsers(userResults);
            totalResults += userResults.size();
        }

        if ("all".equals(type) || "posts".equals(type)) {
            IPage<Post> postPage = postMapper.selectByContentContainingOrHashtagsContaining(
                    query, query, postPageParam);
            List<Post> posts = postPage.getRecords();

            List<SearchResponse.PostResult> postResults = posts.stream()
                    .map(p -> {
                        List<String> tags = parseHashtags(p.getHashtags());
                        User postUser = getUserById(p.getUserId());

                        return SearchResponse.PostResult.builder()
                                .id(p.getId())
                                .userId(p.getUserId())
                                .user(postUser != null ? postUser.getDisplayName() : "用户" + p.getUserId())
                                .avatarUrl(postUser != null ? postUser.getAvatarUrl() : null)
                                .content(p.getContent())
                                .time(p.getCreatedAt().toString())
                                .tags(tags)
                                .matchScore(0.9)
                                .build();
                    })
                    .collect(Collectors.toList());

            response.setPosts(postResults);
            totalResults += postResults.size();
        }

        if ("all".equals(type) || "plans".equals(type)) {
            try {
                log.info("Searching plans...");
                IPage<Plan> planPage = planMapper.selectByTitleContainingOrDescriptionContainingAndVisibility(
                        query, query, Plan.Visibility.PUBLIC.name(), planPageParam);
                List<Plan> plans = planPage.getRecords();
                log.info("Found {} plans", plans.size());

                List<SearchResponse.PlanResult> planResults = plans.stream()
                        .map(p -> {
                            User planUser = getUserById(p.getUserId());
                            return SearchResponse.PlanResult.builder()
                                    .id(p.getId())
                                    .title(p.getTitle())
                                    .description(p.getDescription())
                                    .deadline(p.getTargetDate() != null ? p.getTargetDate().toString() : null)
                                    .user(SearchResponse.PlanResult.UserInfo.builder()
                                            .name(planUser != null ? planUser.getDisplayName() : "用户" + p.getUserId())
                                            .build())
                                    .matchScore(0.85)
                                    .build();
                        })
                        .collect(Collectors.toList());

                response.setPlans(planResults);
                totalResults += planResults.size();
            } catch (Exception e) {
                log.error("Error searching plans", e);
            }
        }

        if ("all".equals(type) || "topics".equals(type)) {
            try {
                log.info("Searching topics...");
                List<TrendingTopic> topics = trendingTopicMapper.selectAll();
                log.info("selectAll found {} topics", topics != null ? topics.size() : 0);
                
                if (topics == null || topics.isEmpty()) {
                    topics = trendingTopicMapper.selectList(null);
                    log.info("selectList found {} topics", topics != null ? topics.size() : 0);
                }
                
                if (topics == null || topics.isEmpty()) {
                    log.info("No topics found, initializing default topics...");
                    initializeDefaultTopics();
                    topics = trendingTopicMapper.selectList(null);
                    log.info("After initialization, found {} topics", topics != null ? topics.size() : 0);
                } else {
                    initializeDefaultTopics();
                    topics = trendingTopicMapper.selectList(null);
                }
                
                if (topics != null) {
                    List<String> topicResults = topics.stream()
                            .filter(t -> t.getTagName().toLowerCase().contains(query.toLowerCase()))
                            .map(TrendingTopic::getTagName)
                            .collect(Collectors.toList());

                    log.info("Found {} topics matching query '{}'", topicResults.size(), query);
                    response.setTopics(topicResults);
                    totalResults += topicResults.size();
                }
            } catch (Exception e) {
                log.error("Error searching topics", e);
            }
        }

        response.setTotalResults(totalResults);
        return response;
    }

    @Override
    public List<String> getSuggestions(String query) {
        List<String> suggestions = new ArrayList<>();

        QueryWrapper<User> userQueryWrapper = new QueryWrapper<>();
        userQueryWrapper.like("username", query)
                .or()
                .like("email", query);
        
        Page<User> suggestionPageParam = new Page<>(0, 5);
        IPage<User> userPage = userMapper.selectPage(suggestionPageParam, userQueryWrapper);
        List<User> users = userPage.getRecords();
        suggestions.addAll(users.stream().map(User::getUsername).collect(Collectors.toList()));

        List<TrendingTopic> topics = trendingTopicMapper.selectList(null);
        suggestions.addAll(topics.stream()
                .filter(t -> t.getTagName().toLowerCase().contains(query.toLowerCase()))
                .map(TrendingTopic::getTagName)
                .collect(Collectors.toList()));

        return suggestions;
    }

    private User getUserById(Long userId) {
        if (userId == null) return null;
        try {
            return userMapper.selectById(userId);
        } catch (Exception e) {
            return null;
        }
    }

    private void initializeDefaultTopics() {
        log.info("Initializing default trending topics");
        String[] defaultTopics = {"年度计划", "学习计划", "健身计划", "旅行计划", "工作计划", "阅读计划", "减肥计划", "早起计划", "考研计划", "备考计划",
                "健康", "健身", "运动", "运动打卡", "减肥法", "React学习", "前端开发", "技术分享"};
        
        for (String topicName : defaultTopics) {
            TrendingTopic existing = trendingTopicMapper.selectByTagName(topicName).orElse(null);
            if (existing == null) {
                TrendingTopic topic = TrendingTopic.builder()
                        .tagName(topicName)
                        .displayName(topicName)
                        .topicType("hashtag")
                        .postCount(0)
                        .engagementScore(java.math.BigDecimal.ZERO)
                        .trendDirection("stable")
                        .lastUpdated(java.time.LocalDateTime.now())
                        .isFeatured(false)
                        .build();
                trendingTopicMapper.insert(topic);
                log.info("Created default topic: {}", topicName);
            }
        }
    }

    private List<String> parseHashtags(String hashtagsJson) {
        List<String> tags = new ArrayList<>();
        if (hashtagsJson == null || hashtagsJson.trim().isEmpty()) {
            return tags;
        }

        try {
            tags = objectMapper.readValue(hashtagsJson, new TypeReference<List<String>>() {});
        } catch (Exception e) {
            try {
                String hashtagsStr = hashtagsJson.trim();
                if (hashtagsStr.startsWith("[") && hashtagsStr.endsWith("]")) {
                    String[] parts = hashtagsStr.substring(1, hashtagsStr.length() - 1).split(",");
                    for (String part : parts) {
                        String tag = part.trim().replace("\"", "").replace("'", "");
                        if (!tag.isEmpty()) tags.add(tag);
                    }
                } else {
                    tags.add(hashtagsStr);
                }
            } catch (Exception e2) {
            }
        }
        return tags;
    }

    @Override
    public void syncAllPostHashtagsToTopics() {
        log.info("Starting to sync all post hashtags to topics...");
        List<Post> allPosts = postMapper.selectList(null);
        int createdTopics = 0;
        
        for (Post post : allPosts) {
            List<String> hashtags = parseHashtags(post.getHashtags());
            for (String hashtag : hashtags) {
                String tagName = hashtag.startsWith("#") ? hashtag.substring(1) : hashtag;
                tagName = tagName.trim();
                
                if (tagName.isEmpty()) {
                    continue;
                }
                
                Optional<TrendingTopic> existingTopic = trendingTopicMapper.selectByTagName(tagName);
                if (existingTopic.isEmpty()) {
                    TrendingTopic newTopic = TrendingTopic.builder()
                            .tagName(tagName)
                            .displayName(tagName)
                            .topicType("hashtag")
                            .postCount(0)
                            .engagementScore(java.math.BigDecimal.ZERO)
                            .trendDirection("stable")
                            .lastUpdated(java.time.LocalDateTime.now())
                            .isFeatured(false)
                            .build();
                    trendingTopicMapper.insert(newTopic);
                    createdTopics++;
                    log.info("Created topic from post hashtag: {}", tagName);
                }
            }
        }
        
        log.info("Sync completed. Created {} new topics from post hashtags.", createdTopics);
    }
}
