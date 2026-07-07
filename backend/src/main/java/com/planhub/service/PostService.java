package com.planhub.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.planhub.dto.request.CreateCommentRequest;
import com.planhub.dto.request.CreatePostRequest;
import com.planhub.dto.response.PostDetailResponse;
import com.planhub.entity.Activity;
import com.planhub.entity.CommentInteraction;
import com.planhub.entity.Plan;
import com.planhub.entity.Post;
import com.planhub.entity.PostComment;
import com.planhub.entity.PostInteraction;
import com.planhub.entity.User;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;
import java.util.Set;

public interface PostService {
    Post create(Long userId, CreatePostRequest request);

    Post share(Long userId, Long originalPostId, Long originalAuthorId, String content);

    Post getById(Long postId);

    IPage<Post> getAll(String type, String sort, int page, int size);

    List<Post> getLatestPosts(int limit);

    List<Post> getPopularPosts(int limit);

    int getLikeCount(Long postId);

    int getCommentCount(Long postId);

    List<PostComment> getAllComments(Long postId);

    void like(Long postId, Long userId);

    void unlike(Long postId, Long userId);

    void bookmark(Long postId, Long userId);

    void unbookmark(Long postId, Long userId);

    PostComment createComment(Long postId, Long userId, CreateCommentRequest request);

    IPage<PostComment> getComments(Long postId, int page, int size);

    int deleteComment(Long commentId, Long userId);

    boolean canDeleteComment(Long commentId, Long userId);

    User getUserById(Long userId);

    Map<Long, User> getUsersByIds(Set<Long> userIds);

    List<Post> getPostsByIds(Set<Long> postIds);

    boolean hasLiked(Long postId, Long userId);

    Map<Long, Boolean> getLikedPostsByUser(Long userId, List<Long> postIds);

    IPage<Post> getPostsByHashtag(String hashtag, int page, int size);

    List<Post> getPostsByUserId(Long userId);

    List<Post> getPostsByUserId(Long userId, String sort);

    void likeComment(Long commentId, Long userId);

    void unlikeComment(Long commentId, Long userId);

    boolean hasLikedComment(Long commentId, Long userId);

    int getCommentLikeCount(Long commentId);

    Map<Long, Boolean> getLikedCommentsByUser(Long userId, List<Long> commentIds);

    PostComment getCommentById(Long commentId);

    int getReplyCount(Long commentId);

    List<String> getTopTrendingHashtags();

    @Transactional
    void delete(Long postId, Long userId);

    PostDetailResponse.PlanInfoResponse buildPlanInfoResponse(Plan plan);
}
