package com.planhub.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.planhub.dto.request.ChangePasswordRequest;
import com.planhub.dto.request.UpdatePrivacySettingsRequest;
import com.planhub.dto.response.ApiResponse;
import com.planhub.dto.response.LikedItemResponse;
import com.planhub.dto.response.UserProfileResponse;
import com.planhub.entity.User;
import com.planhub.service.UserService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/users")
public class UserController {
    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    @GetMapping("/username/{username}")
    public ResponseEntity<ApiResponse<User>> getUserByUsername(@PathVariable String username) {
        User user = userService.findByUsername(username);
        return ResponseEntity.ok(ApiResponse.success(user));
    }

    @GetMapping("/email/{email}")
    public ResponseEntity<ApiResponse<User>> getUserByEmail(@PathVariable String email) {
        User user = userService.findByEmail(email);
        return ResponseEntity.ok(ApiResponse.success(user));
    }

    @GetMapping("/page")
    public ResponseEntity<ApiResponse<IPage<User>>> getUsers(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String keyword) {
        IPage<User> users = userService.findAll(page, size, keyword);
        return ResponseEntity.ok(ApiResponse.success(users));
    }

    @GetMapping("/{userId}")
    public ResponseEntity<ApiResponse<User>> getUserById(@PathVariable Long userId) {
        User user = userService.findById(userId);
        return ResponseEntity.ok(ApiResponse.success(user));
    }

    @PutMapping("/{userId}")
    public ResponseEntity<ApiResponse<Void>> updateUser(@PathVariable Long userId, @RequestBody User user) {
        userService.update(userId, user);
        return ResponseEntity.ok(ApiResponse.success(null, "用户信息更新成功"));
    }

    @DeleteMapping("/{userId}")
    public ResponseEntity<ApiResponse<Void>> deleteUser(@PathVariable Long userId) {
        userService.delete(userId);
        return ResponseEntity.ok(ApiResponse.success(null, "用户删除成功"));
    }

    @PostMapping("/{userId}/change-password")
    public ResponseEntity<ApiResponse<Void>> changePassword(
            @PathVariable Long userId,
            @Valid @RequestBody ChangePasswordRequest request) {
        userService.changePassword(userId, request.getOldPassword(), request.getNewPassword());
        return ResponseEntity.ok(ApiResponse.success(null, "密码修改成功"));
    }

    @PostMapping("/{userId}/avatar")
    public ResponseEntity<ApiResponse<User>> updateAvatar(
            @PathVariable Long userId,
            @RequestBody Map<String, String> request) {
        String avatarUrl = request.get("avatarUrl");
        User user = userService.updateAvatar(userId, avatarUrl);
        return ResponseEntity.ok(ApiResponse.success(user, "头像更新成功"));
    }

    @PutMapping("/{userId}/privacy-settings")
    public ResponseEntity<ApiResponse<User>> updatePrivacySettings(
            @PathVariable Long userId,
            @Valid @RequestBody UpdatePrivacySettingsRequest request) {
        User user = userService.updatePrivacySettings(userId, request);
        return ResponseEntity.ok(ApiResponse.success(user, "隐私设置更新成功"));
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
    public ResponseEntity<ApiResponse<List<User>>> getFollowers(@PathVariable Long userId) {
        List<User> followers = userService.getFollowers(userId);
        return ResponseEntity.ok(ApiResponse.success(followers));
    }

    @GetMapping("/{userId}/following")
    public ResponseEntity<ApiResponse<List<User>>> getFollowing(@PathVariable Long userId) {
        List<User> following = userService.getFollowing(userId);
        return ResponseEntity.ok(ApiResponse.success(following));
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
