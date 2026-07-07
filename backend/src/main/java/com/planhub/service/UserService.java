package com.planhub.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.planhub.dto.request.RegisterRequest;
import com.planhub.dto.request.UpdatePrivacySettingsRequest;
import com.planhub.dto.response.ActivityResponse;
import com.planhub.dto.response.LikedItemResponse;
import com.planhub.dto.response.UserProfileResponse;
import com.planhub.entity.User;

import java.util.List;

public interface UserService {
    User register(RegisterRequest request);
    
    User findByUsername(String username);
    
    User findByEmail(String email);
    
    User findById(Long id);
    
    User update(Long id, User updateUser);
    
    IPage<User> findAll(int page, int size, String keyword);
    
    void delete(Long id);
    
    UserProfileResponse getUserProfile(Long userId, Long currentUserId);
    
    User updatePrivacySettings(Long userId, UpdatePrivacySettingsRequest request);
    
    void changePassword(Long userId, String oldPassword, String newPassword);
    
    User updateAvatar(Long userId, String avatarUrl);
    
    void followUser(Long followerId, Long followingId);
    
    void unfollowUser(Long followerId, Long followingId);
    
    boolean isFollowing(Long followerId, Long followingId);
    
    long getFollowerCount(Long userId);
    
    long getFollowingCount(Long userId);
    
    List<User> getFollowers(Long userId);
    
    List<User> getFollowing(Long userId);
    
    List<LikedItemResponse> getLikedContent(Long userId, Long currentUserId);
}
