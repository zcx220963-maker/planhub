package com.planhub.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.planhub.dto.request.RegisterRequest;
import com.planhub.dto.request.UpdatePrivacySettingsRequest;
import com.planhub.dto.response.ActivityResponse;
import com.planhub.dto.response.LikedItemResponse;
import com.planhub.dto.response.UserProfileResponse;
import com.planhub.entity.Plan;
import com.planhub.entity.PlanInteraction;
import com.planhub.entity.Post;
import com.planhub.entity.PostInteraction;
import com.planhub.entity.User;
import com.planhub.entity.UserRelationship;
import com.planhub.exception.BusinessException;
import com.planhub.exception.ResourceNotFoundException;
import com.planhub.mapper.PlanInteractionMapper;
import com.planhub.mapper.PlanMapper;
import com.planhub.mapper.PostInteractionMapper;
import com.planhub.mapper.PostMapper;
import com.planhub.mapper.UserMapper;
import com.planhub.mapper.UserRelationshipMapper;
import com.planhub.service.ActivityService;
import com.planhub.service.ChatService;
import com.planhub.service.UserService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.PageRequest;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class UserServiceImpl implements UserService {
    private final UserMapper userMapper;
    private final PasswordEncoder passwordEncoder;
    private final PlanMapper planMapper;
    private final PostMapper postMapper;
    private final UserRelationshipMapper userRelationshipMapper;
    private final ActivityService activityService;
    private final ChatService chatService;
    private final ObjectMapper objectMapper;
    private final PostInteractionMapper postInteractionMapper;
    private final PlanInteractionMapper planInteractionMapper;

    @Override
    public User register(RegisterRequest request) {
        log.info("=== 开始注册用户 ===");
        log.info("请求数据: username={}, email={}, displayName={}", 
                request.getUsername(), request.getEmail(), request.getDisplayName());
        
        if (userMapper.existByUsername(request.getUsername())) {
            log.warn("用户名已存在: {}", request.getUsername());
            throw new BusinessException("用户名已存在");
        }
        log.info("用户名检查通过");
        
        if (userMapper.existByEmail(request.getEmail())) {
            log.warn("邮箱已被注册: {}", request.getEmail());
            throw new BusinessException("邮箱已被注册");
        }
        log.info("邮箱检查通过");

        User user = User.builder()
                .username(request.getUsername())
                .email(request.getEmail())
                .passwordHash(passwordEncoder.encode(request.getPassword()))
                .displayName(request.getDisplayName())
                .build();
        
        log.info("用户对象创建完成，准备保存");
        userMapper.insert(user);
        log.info("=== 用户注册成功 === id={}, username={}", user.getId(), user.getUsername());
        
        return user;
    }

    @Override
    public User findByUsername(String username) {
        User user = userMapper.selectByUsername(username);
        if (user == null) {
            throw new ResourceNotFoundException("用户", "username", username);
        }
        return user;
    }

    @Override
    public User findByEmail(String email) {
        User user = userMapper.selectByEmail(email);
        if (user == null) {
            throw new ResourceNotFoundException("用户", "email", email);
        }
        return user;
    }

    @Override
    public User findById(Long id) {
        User user = userMapper.selectById(id);
        if (user == null) {
            throw new ResourceNotFoundException("用户", "id", id);
        }
        return user;
    }

    @Override
    public User update(Long id, User updateUser) {
        User user = findById(id);
        if (updateUser.getUsername() != null) {
            user.setUsername(updateUser.getUsername());
        }
        if (updateUser.getEmail() != null) {
            user.setEmail(updateUser.getEmail());
        }
        if (updateUser.getAvatarUrl() != null) {
            user.setAvatarUrl(updateUser.getAvatarUrl());
        }
        if (updateUser.getDisplayName() != null) {
            user.setDisplayName(updateUser.getDisplayName());
        }
        if (updateUser.getBio() != null) {
            user.setBio(updateUser.getBio());
        }
        userMapper.updateById(user);
        return user;
    }

    @Override
    public IPage<User> findAll(int page, int size, String keyword) {
        Page<User> pageParam = new Page<>(page, size);
        if (keyword != null && !keyword.isEmpty()) {
            return userMapper.selectByUsernameContainingOrEmailContaining(pageParam, keyword);
        }
        return userMapper.selectPage(pageParam, new QueryWrapper<>());
    }

    @Override
    public void delete(Long id) {
        User user = findById(id);
        userMapper.deleteById(user.getId());
    }

    @Override
    public UserProfileResponse getUserProfile(Long userId, Long currentUserId) {
        log.info("=== 开始获取用户资料 === userId={}, currentUserId={}", userId, currentUserId);
        try {
            User user = findById(userId);
            log.info("=== 已找到用户 === username={}", user.getUsername());
            
            Page<Plan> planPage = new Page<>(1, 10);
            Page<Post> postPage = new Page<>(1, 10);
            List<Plan> publicPlans = planMapper.selectByUserIdAndVisibility(userId, "PUBLIC", planPage).getRecords();
            log.info("=== 获取到公开计划数量 === count={}", publicPlans.size());
            
            List<Post> publicPosts = postMapper.selectByUserIdAndPrivacy(userId, "PUBLIC", postPage).getRecords();
            log.info("=== 获取到公开帖子数量 === count={}", publicPosts.size());

            List<UserProfileResponse.PlanSummary> planSummaries = publicPlans.stream()
                    .map(plan -> UserProfileResponse.PlanSummary.builder()
                            .id(plan.getId())
                            .title(plan.getTitle())
                            .description(plan.getDescription())
                            .status(plan.getStatus().name())
                            .progressPercentage(plan.getProgressPercentage() != null ? plan.getProgressPercentage().intValue() : 0)
                            .targetDate(plan.getTargetDate() != null ? plan.getTargetDate().toString() : null)
                            .build())
                    .collect(Collectors.toList());

            List<UserProfileResponse.PostSummary> postSummaries = publicPosts.stream()
                    .map(post -> UserProfileResponse.PostSummary.builder()
                            .id(post.getId())
                            .content(post.getContent())
                            .hashtags(post.getHashtags())
                            .likes(0)
                            .commentsCount(0)
                            .createdAt(post.getCreatedAt() != null ? post.getCreatedAt().toString() : null)
                            .build())
                    .collect(Collectors.toList());


            Map<String, Boolean> privacySettings = getPrivacySettingsFromUser(user);
            Boolean showActivities = privacySettings.get("showActivities");
            Boolean showFollowers = privacySettings.get("showFollowers");
            Boolean showFollowing = privacySettings.get("showFollowing");
            Boolean showLikedContent = privacySettings.get("showLikedContent");
            log.info("=== 隐私设置 === showActivities={}, showFollowers={}, showFollowing={}, showLikedContent={}", 
                    showActivities, showFollowers, showFollowing, showLikedContent);

            log.info("=== 展示活动记录 === showActivities={}", showActivities);
            List<ActivityResponse> activities = null;
            if (showActivities) {
                try {
                    activities = activityService.getActivitiesByUserId(userId).stream()
                            .limit(10)
                            .collect(Collectors.toList());
                    log.info("=== 获取到活动记录数量 === count={}", activities.size());
                } catch (Exception e) {
                    log.warn("=== 获取活动记录失败，忽略此部分 ===", e);
                    activities = new ArrayList<>();
                }
            }

            Long followerCount = getFollowerCount(userId);
            Long followingCount = getFollowingCount(userId);
            Boolean isFollowing = currentUserId != null ? isFollowing(currentUserId, userId) : false;
            log.info("=== 粉丝/关注数量 === followerCount={}, followingCount={}, isFollowing={}", 
                    followerCount, followingCount, isFollowing);

            UserProfileResponse response = UserProfileResponse.builder()
                    .id(user.getId())
                    .username(user.getUsername())
                    .email(user.getEmail())
                    .displayName(user.getDisplayName())
                    .avatarUrl(user.getAvatarUrl())
                    .bio(user.getBio())
                    .publicPlans(planSummaries)
                    .publicPosts(postSummaries)
                    .activities(activities)
                    .showActivities(showActivities)
                    .showFollowers(showFollowers)
                    .showFollowing(showFollowing)
                    .showLikedContent(showLikedContent)
                    .followerCount(followerCount)
                    .followingCount(followingCount)
                    .isFollowing(isFollowing)
                    .build();
            
            log.info("=== 用户资料构建完成 === id={}", response.getId());
            return response;
        } catch (Exception e) {
            log.error("=== 获取用户资料失败 ===", e);
            e.printStackTrace();
            throw e;
        }
    }

    private Map<String, Boolean> getPrivacySettingsFromUser(User user) {
        Map<String, Boolean> result = new HashMap<>();
        result.put("showActivities", true);
        result.put("showFollowers", true);
        result.put("showFollowing", true);
        result.put("showLikedContent", true);
        
        if (user.getPrivacySettings() == null || user.getPrivacySettings().isEmpty()) {
            return result;
        }
        try {
            Map<String, Object> privacySettings = objectMapper.readValue(
                    user.getPrivacySettings(), 
                    new TypeReference<HashMap<String, Object>>() {}
            );
            
            if (privacySettings.get("showActivities") != null) {
                result.put("showActivities", (Boolean) privacySettings.get("showActivities"));
            }
            if (privacySettings.get("showFollowers") != null) {
                result.put("showFollowers", (Boolean) privacySettings.get("showFollowers"));
            }
            if (privacySettings.get("showFollowing") != null) {
                result.put("showFollowing", (Boolean) privacySettings.get("showFollowing"));
            }
            if (privacySettings.get("showLikedContent") != null) {
                result.put("showLikedContent", (Boolean) privacySettings.get("showLikedContent"));
            }
        } catch (Exception e) {
            log.error("Failed to parse privacy settings for user {}", user.getId(), e);
        }
        
        return result;
    }

    @Override
    public User updatePrivacySettings(Long userId, UpdatePrivacySettingsRequest request) {
        User user = findById(userId);
        
        Map<String, Object> privacySettings;
        if (user.getPrivacySettings() != null && !user.getPrivacySettings().isEmpty()) {
            try {
                privacySettings = objectMapper.readValue(
                        user.getPrivacySettings(), 
                        new TypeReference<HashMap<String, Object>>() {}
                );
            } catch (Exception e) {
                privacySettings = new HashMap<>();
            }
        } else {
            privacySettings = new HashMap<>();
        }

        if (request.getShowActivities() != null) {
            privacySettings.put("showActivities", request.getShowActivities());
        }
        if (request.getShowFollowers() != null) {
            privacySettings.put("showFollowers", request.getShowFollowers());
        }
        if (request.getShowFollowing() != null) {
            privacySettings.put("showFollowing", request.getShowFollowing());
        }
        if (request.getShowLikedContent() != null) {
            privacySettings.put("showLikedContent", request.getShowLikedContent());
        }

        try {
            user.setPrivacySettings(objectMapper.writeValueAsString(privacySettings));
        } catch (Exception e) {
            throw new BusinessException("Failed to save privacy settings");
        }

        userMapper.updateById(user);
        return user;
    }

    @Override
    public void changePassword(Long userId, String oldPassword, String newPassword) {
        log.info("=== 修改用户密码 === userId={}", userId);
        User user = findById(userId);
        
        if (!passwordEncoder.matches(oldPassword, user.getPasswordHash())) {
            log.warn("原密码错误");
            throw new BusinessException("原密码错误");
        }
        
        if (passwordEncoder.matches(newPassword, user.getPasswordHash())) {
            log.warn("新密码不能与原密码相同");
            throw new BusinessException("新密码不能与原密码相同");
        }
        
        user.setPasswordHash(passwordEncoder.encode(newPassword));
        userMapper.updateById(user);
        
        log.info("=== 密码修改成功 ===");
    }

    @Override
    public User updateAvatar(Long userId, String avatarUrl) {
        log.info("=== 更新用户头像 === userId={}, avatarUrl={}", userId, avatarUrl);
        User user = findById(userId);
        user.setAvatarUrl(avatarUrl);
        userMapper.updateById(user);
        log.info("=== 头像更新成功 ===");
        return user;
    }

    @Override
    public void followUser(Long followerId, Long followingId) {
        log.info("=== 用户关注 === followerId={}, followingId={}", followerId, followingId);
        
        if (followerId.equals(followingId)) {
            throw new BusinessException("不能关注自己");
        }
        
        if (userRelationshipMapper.existByFollowerIdAndFollowingIdAndRelationshipType(
                followerId, followingId, "follow")) {
            throw new BusinessException("已经关注该用户");
        }
        
        boolean wasFollowedBefore = userRelationshipMapper.existByFollowerIdAndFollowingIdAndRelationshipType(
                followingId, followerId, "follow");
        
        findById(followingId);
        
        UserRelationship relationship = UserRelationship.builder()
                .followerId(followerId)
                .followingId(followingId)
                .relationshipType("follow")
                .build();
        
        userRelationshipMapper.insert(relationship);
        log.info("=== 关注成功 ===");
        
        if (wasFollowedBefore) {
            log.info("=== 检测到互关，创建对话并发送系统消息 ===");
            try {
                chatService.sendSystemMessageOnMutualFollow(
                        followerId, 
                        followingId, 
                        "我们已经互关了，可以正常聊天了！"
                );
                log.info("=== 互关系统消息发送成功 ===");
            } catch (Exception e) {
                log.error("=== 发送互关系统消息失败 ===", e);
            }
        }
    }

    @Override
    public void unfollowUser(Long followerId, Long followingId) {
        log.info("=== 用户取消关注 === followerId={}, followingId={}", followerId, followingId);
        
        UserRelationship relationship = userRelationshipMapper
                .selectByFollowerIdAndFollowingIdAndRelationshipType(
                        followerId, followingId, "follow");
        if (relationship == null) {
            throw new BusinessException("未关注该用户");
        }
        
        userRelationshipMapper.deleteById(relationship.getId());
        log.info("=== 取消关注成功 ===");
    }

    @Override
    public boolean isFollowing(Long followerId, Long followingId) {
        return userRelationshipMapper.existByFollowerIdAndFollowingIdAndRelationshipType(
                followerId, followingId, "follow");
    }

    @Override
    public long getFollowerCount(Long userId) {
        return userRelationshipMapper.countByFollowingIdAndRelationshipType(
                userId, "follow");
    }

    @Override
    public long getFollowingCount(Long userId) {
        return userRelationshipMapper.countByFollowerIdAndRelationshipType(
                userId, "follow");
    }

    @Override
    public List<User> getFollowers(Long userId) {
        List<UserRelationship> relationships = userRelationshipMapper
                .selectByFollowingIdAndRelationshipType(userId, "follow");
        
        return relationships.stream()
                .map(rel -> findById(rel.getFollowerId()))
                .collect(Collectors.toList());
    }

    @Override
    public List<User> getFollowing(Long userId) {
        List<UserRelationship> relationships = userRelationshipMapper
                .selectByFollowerIdAndRelationshipType(userId, "follow");
        
        return relationships.stream()
                .map(rel -> findById(rel.getFollowingId()))
                .collect(Collectors.toList());
    }

    @Override
    public List<LikedItemResponse> getLikedContent(Long userId, Long currentUserId) {
        User user = findById(userId);
        Map<String, Boolean> privacySettings = getPrivacySettingsFromUser(user);
        Boolean showLikedContent = privacySettings.get("showLikedContent");
        
        // 检查是否有权查看：自己或者公开
        if (!showLikedContent && (currentUserId == null || !currentUserId.equals(userId))) {
            return new ArrayList<>();
        }
        
        List<LikedItemResponse> result = new ArrayList<>();
        
        // 获取点赞的帖子
        LambdaQueryWrapper<PostInteraction> postLikeQuery = new LambdaQueryWrapper<>();
        postLikeQuery.eq(PostInteraction::getUserId, userId)
                .eq(PostInteraction::getInteractionType, "like")  // 数据库中存储的是小写
                .orderByDesc(PostInteraction::getCreatedAt);
        
        List<PostInteraction> postInteractions = postInteractionMapper.selectList(postLikeQuery);
        
        for (PostInteraction interaction : postInteractions) {
            Post post = postMapper.selectById(interaction.getPostId());
            if (post != null && post.getDeletedAt() == null && "PUBLIC".equals(post.getPrivacy())) {
                LikedItemResponse item = LikedItemResponse.builder()
                        .id(post.getId())
                        .type("post")
                        .title(null)
                        .content(post.getContent())
                        .coverImageUrl(null)
                        .status(null)
                        .createdAt(post.getCreatedAt())
                        .likedAt(interaction.getCreatedAt())
                        .build();
                result.add(item);
            }
        }
        
        // 获取点赞的计划
        List<PlanInteraction> planInteractions = planInteractionMapper.findLikedPlansByUserId(userId);
        
        for (PlanInteraction interaction : planInteractions) {
            Plan plan = planMapper.selectById(interaction.getPlanId());
            if (plan != null && plan.getDeletedAt() == null && Plan.Visibility.PUBLIC.equals(plan.getVisibility())) {
                LikedItemResponse item = LikedItemResponse.builder()
                        .id(plan.getId())
                        .type("plan")
                        .title(plan.getTitle())
                        .content(plan.getDescription())
                        .coverImageUrl(plan.getCoverImageUrl())
                        .status(plan.getStatus().name())
                        .createdAt(plan.getCreatedAt())
                        .likedAt(interaction.getCreatedAt())
                        .build();
                result.add(item);
            }
        }
        
        // 按点赞时间倒序排序
        result.sort(Comparator.comparing(LikedItemResponse::getLikedAt).reversed());
        
        // 限制最多返回
        return result.stream().limit(20).collect(Collectors.toList());
    }
}
