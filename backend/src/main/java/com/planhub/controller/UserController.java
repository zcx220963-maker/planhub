package com.planhub.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.planhub.dto.request.ChangePasswordRequest;
import com.planhub.dto.request.UpdatePrivacySettingsRequest;
import com.planhub.dto.response.ApiResponse;
import com.planhub.dto.response.LikedItemResponse;
import com.planhub.dto.response.UserProfileResponse;
import com.planhub.dto.response.UserPublicDTO;
import com.planhub.entity.User;
import com.planhub.service.UserService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/users")
public class UserController {
    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    /**
     * 根据用户名查询用户公开信息
     * 仅返回安全字段，不暴露 email/phone/passwordHash
     */
    @GetMapping("/username/{username}")
    public ResponseEntity<ApiResponse<UserPublicDTO>> getUserByUsername(@PathVariable String username) {
        User user = userService.findByUsername(username);
        return ResponseEntity.ok(ApiResponse.success(UserPublicDTO.fromEntity(user)));
    }

    /**
     * 根据邮箱查询用户 —— 仅限已认证用户自己查询
     * 移除公开枚举风险，改为需要认证且只能查自己
     */
    @GetMapping("/email/{email}")
    public ResponseEntity<ApiResponse<UserPublicDTO>> getUserByEmail(
            @PathVariable String email,
            Authentication authentication) {
        if (authentication == null || authentication.getPrincipal() == null) {
            return ResponseEntity.status(401).body(ApiResponse.error("未认证"));
        }
        // 只能查询自己的邮箱信息
        User current = userService.findById((Long) authentication.getPrincipal());
        if (current == null || !current.getEmail().equalsIgnoreCase(email)) {
            return ResponseEntity.status(403).body(ApiResponse.error("无权访问"));
        }
        return ResponseEntity.ok(ApiResponse.success(UserPublicDTO.fromEntity(current)));
    }

    /**
     * 用户列表 —— 仅返回公开字段
     */
    @GetMapping("/page")
    public ResponseEntity<ApiResponse<IPage<UserPublicDTO>>> getUsers(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String keyword) {
        IPage<User> users = userService.findAll(page, size, keyword);
        IPage<UserPublicDTO> result = users.convert(UserPublicDTO::fromEntity);
        return ResponseEntity.ok(ApiResponse.success(result));
    }

    /**
     * 根据 ID 查询用户公开信息
     */
    @GetMapping("/{userId}")
    public ResponseEntity<ApiResponse<UserPublicDTO>> getUserById(@PathVariable Long userId) {
        User user = userService.findById(userId);
        return ResponseEntity.ok(ApiResponse.success(UserPublicDTO.fromEntity(user)));
    }

    @PutMapping("/{userId}")
    public ResponseEntity<ApiResponse<Void>> updateUser(
            @PathVariable Long userId,
            @RequestBody User user,
            Authentication authentication) {
        // 只能修改自己的信息
        validateSelfAccess(userId, authentication);
        userService.update(userId, user);
        return ResponseEntity.ok(ApiResponse.success(null, "用户信息更新成功"));
    }

    @DeleteMapping("/{userId}")
    public ResponseEntity<ApiResponse<Void>> deleteUser(
            @PathVariable Long userId,
            Authentication authentication) {
        validateSelfAccess(userId, authentication);
        userService.delete(userId);
        return ResponseEntity.ok(ApiResponse.success(null, "用户删除成功"));
    }

    @PostMapping("/{userId}/change-password")
    public ResponseEntity<ApiResponse<Void>> changePassword(
            @PathVariable Long userId,
            @Valid @RequestBody ChangePasswordRequest request,
            Authentication authentication) {
        validateSelfAccess(userId, authentication);
        userService.changePassword(userId, request.getOldPassword(), request.getNewPassword());
        return ResponseEntity.ok(ApiResponse.success(null, "密码修改成功"));
    }

    @PostMapping("/{userId}/avatar")
    public ResponseEntity<ApiResponse<UserPublicDTO>> updateAvatar(
            @PathVariable Long userId,
            @RequestBody Map<String, String> request,
            Authentication authentication) {
        validateSelfAccess(userId, authentication);
        String avatarUrl = request.get("avatarUrl");
        User user = userService.updateAvatar(userId, avatarUrl);
        return ResponseEntity.ok(ApiResponse.success(UserPublicDTO.fromEntity(user), "头像更新成功"));
    }

    @PutMapping("/{userId}/privacy-settings")
    public ResponseEntity<ApiResponse<UserPublicDTO>> updatePrivacySettings(
            @PathVariable Long userId,
            @Valid @RequestBody UpdatePrivacySettingsRequest request,
            Authentication authentication) {
        validateSelfAccess(userId, authentication);
        User user = userService.updatePrivacySettings(userId, request);
        return ResponseEntity.ok(ApiResponse.success(UserPublicDTO.fromEntity(user), "隐私设置更新成功"));
    }

    /**
     * 验证当前用户只能操作自己的资源
     */
    private void validateSelfAccess(Long userId, Authentication authentication) {
        if (authentication == null || authentication.getPrincipal() == null) {
            throw new org.springframework.security.access.AccessDeniedException("未认证");
        }
        Long currentUserId = (Long) authentication.getPrincipal();
        if (!currentUserId.equals(userId)) {
            throw new org.springframework.security.access.AccessDeniedException("无权操作其他用户资源");
        }
    }

    // ========== 关注/粉丝相关接口 ==========

    @PostMapping("/{followerId}/follow/{followingId}")
    public ResponseEntity<ApiResponse<Void>> followUser(
            @PathVariable Long followerId,
            @PathVariable Long followingId) {
        userService.followUser(followerId, followingId);
        return ResponseEntity.ok(ApiResponse.success(null, "关注成功"));
    }

    @DeleteMapping("/{followerId}/follow/{followingId}")
    public ResponseEntity<ApiResponse<Void>> unfollowUser(
            @PathVariable Long followerId,
            @PathVariable Long followingId) {
        userService.unfollowUser(followerId, followingId);
        return ResponseEntity.ok(ApiResponse.success(null, "取消关注成功"));
    }

    @GetMapping("/{userId}/followers")
    public ResponseEntity<ApiResponse<List<UserPublicDTO>>> getFollowers(@PathVariable Long userId) {
        List<User> followers = userService.getFollowers(userId);
        List<UserPublicDTO> result = followers.stream()
                .map(UserPublicDTO::fromEntity)
                .collect(Collectors.toList());
        return ResponseEntity.ok(ApiResponse.success(result));
    }

    @GetMapping("/{userId}/following")
    public ResponseEntity<ApiResponse<List<UserPublicDTO>>> getFollowing(@PathVariable Long userId) {
        List<User> following = userService.getFollowing(userId);
        List<UserPublicDTO> result = following.stream()
                .map(UserPublicDTO::fromEntity)
                .collect(Collectors.toList());
        return ResponseEntity.ok(ApiResponse.success(result));
    }

    @GetMapping("/{followerId}/is-following/{followingId}")
    public ResponseEntity<ApiResponse<Boolean>> isFollowing(
            @PathVariable Long followerId,
            @PathVariable Long followingId) {
        boolean isFollowing = userService.isFollowing(followerId, followingId);
        return ResponseEntity.ok(ApiResponse.success(isFollowing));
    }

    @GetMapping("/{userId}/profile")
    public ResponseEntity<ApiResponse<UserProfileResponse>> getUserProfile(
            @PathVariable Long userId,
            @RequestParam(required = false) Long currentUserId) {
        UserProfileResponse profile = userService.getUserProfile(userId, currentUserId);
        return ResponseEntity.ok(ApiResponse.success(profile));
    }

    @GetMapping("/{userId}/liked")
    public ResponseEntity<ApiResponse<List<LikedItemResponse>>> getLikedContent(
            @PathVariable Long userId,
            @RequestParam(required = false) Long currentUserId) {
        List<LikedItemResponse> liked = userService.getLikedContent(userId, currentUserId);
        return ResponseEntity.ok(ApiResponse.success(liked));
    }
}
