import axios from 'axios';
import type { AxiosInstance } from 'axios';
import type { User, Plan, PlanTask, Post, Comment, LoginResponse, ApiResponse, LoginRequest, RegisterRequest, CreatePlanRequest, PlanCheckin, SearchResponse, UserProfileResponse, ChangePasswordRequest, Activity, Notification, ChatConversation, ChatMessage, LikedItemResponse } from '../types';

const API_BASE_URL = 'http://localhost:8080/api';
const UPLOAD_BASE_URL = 'http://localhost:8080';

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getImageUrl = (url: string): string => {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }
  if (url.startsWith('/')) {
    return `${UPLOAD_BASE_URL}${url}`;
  }
  return `${UPLOAD_BASE_URL}/${url}`;
};

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const response = await api.post<ApiResponse<LoginResponse>>('/auth/login', data);
    return response.data.data;
  },

  register: async (data: RegisterRequest): Promise<LoginResponse> => {
    const response = await api.post<ApiResponse<LoginResponse>>('/auth/register', data);
    return response.data.data;
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await api.get<ApiResponse<User>>('/auth/me');
    return response.data.data;
  },
};

export const userApi = {
  updateUser: async (userId: number, data: Partial<User>): Promise<User> => {
    const response = await api.put<ApiResponse<User>>(`/users/${userId}`, data);
    return response.data.data;
  },

  updateAvatar: async (userId: number, avatarUrl: string): Promise<User> => {
    const response = await api.post<ApiResponse<User>>(`/users/${userId}/avatar`, { avatarUrl });
    return response.data.data;
  },

  getUserProfile: async (userId: number, currentUserId?: number): Promise<UserProfileResponse> => {
    const params = currentUserId ? `?currentUserId=${currentUserId}` : '';
    const response = await api.get<ApiResponse<UserProfileResponse>>(`/users/${userId}/profile${params}`);
    return response.data.data;
  },

  changePassword: async (data: ChangePasswordRequest): Promise<void> => {
    await api.post('/users/change-password', data);
  },

  updatePrivacySettings: async (userId: number, settings: { showActivities: boolean; showFollowers?: boolean; showFollowing?: boolean; showLikedContent?: boolean }): Promise<User> => {
    const response = await api.put<ApiResponse<User>>(`/users/${userId}/privacy-settings`, settings);
    return response.data.data;
  },

  followUser: async (followerId: number, followingId: number): Promise<void> => {
    await api.post(`/users/${followerId}/follow/${followingId}`);
  },

  unfollowUser: async (followerId: number, followingId: number): Promise<void> => {
    await api.delete(`/users/${followerId}/follow/${followingId}`);
  },

  isFollowing: async (followerId: number, followingId: number): Promise<boolean> => {
    const response = await api.get<ApiResponse<boolean>>(`/users/${followerId}/is-following/${followingId}`);
    return response.data.data;
  },

  getFollowers: async (userId: number): Promise<User[]> => {
    const response = await api.get<ApiResponse<User[]>>(`/users/${userId}/followers`);
    return response.data.data;
  },

  getFollowing: async (userId: number): Promise<User[]> => {
    const response = await api.get<ApiResponse<User[]>>(`/users/${userId}/following`);
    return response.data.data;
  },

  getLikedContent: async (userId: number, currentUserId?: number): Promise<LikedItemResponse[]> => {
    const params = currentUserId ? `?currentUserId=${currentUserId}` : '';
    const response = await api.get<ApiResponse<LikedItemResponse[]>>(`/users/${userId}/liked${params}`);
    return response.data.data;
  },
};

export const planApi = {
  getAllPlans: async (): Promise<Plan[]> => {
    const response = await api.get<ApiResponse<Plan[]>>('/plans');
    return response.data.data;
  },

  getPlanById: async (planId: number): Promise<Plan> => {
    const response = await api.get<ApiResponse<Plan>>(`/plans/${planId}`);
    return response.data.data;
  },

  createPlan: async (data: CreatePlanRequest): Promise<Plan> => {
    const response = await api.post<ApiResponse<Plan>>('/plans', data);
    return response.data.data;
  },

  updatePlan: async (planId: number, data: Partial<Plan>): Promise<Plan> => {
    const response = await api.put<ApiResponse<Plan>>(`/plans/${planId}`, data);
    return response.data.data;
  },

  deletePlan: async (planId: number): Promise<void> => {
    await api.delete(`/plans/${planId}`);
  },

  getPlanTasks: async (planId: number): Promise<PlanTask[]> => {
    const response = await api.get<ApiResponse<PlanTask[]>>(`/plans/${planId}/tasks`);
    return response.data.data;
  },

  createTask: async (planId: number, data: Partial<PlanTask>): Promise<PlanTask> => {
    const response = await api.post<ApiResponse<PlanTask>>(`/plans/${planId}/tasks`, data);
    return response.data.data;
  },

  updateTask: async (planId: number, taskId: number, data: Partial<PlanTask>): Promise<PlanTask> => {
    const response = await api.put<ApiResponse<PlanTask>>(`/plans/${planId}/tasks/${taskId}`, data);
    return response.data.data;
  },

  deleteTask: async (planId: number, taskId: number): Promise<void> => {
    await api.delete(`/plans/${planId}/tasks/${taskId}`);
  },

  checkin: async (planId: number, data: Partial<PlanCheckin>): Promise<PlanCheckin> => {
    const response = await api.post<ApiResponse<PlanCheckin>>(`/plans/${planId}/checkins`, data);
    return response.data.data;
  },

  getCheckins: async (planId: number): Promise<PlanCheckin[]> => {
    const response = await api.get<ApiResponse<PlanCheckin[]>>(`/plans/${planId}/checkins`);
    return response.data.data;
  },

  getUserPlans: async (userId: number, search?: string): Promise<PlanInfoResponse[]> => {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    const response = await api.get<ApiResponse<{ records: PlanInfoResponse[] }>>(`/plans/user/${userId}?${params.toString()}`);
    const data = response.data.data;
    if (data && typeof data === 'object' && 'records' in data) {
      return (data as { records: PlanInfoResponse[] }).records;
    }
    return [];
  },
  getPublicPlans: async (search?: string): Promise<PlanInfoResponse[]> => {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    const response = await api.get<ApiResponse<{ records: PlanInfoResponse[] }>>(`/plans/public?${params.toString()}`);
    const data = response.data.data;
    if (data && typeof data === 'object' && 'records' in data) {
      return (data as { records: PlanInfoResponse[] }).records;
    }
    return [];
  },

  likePlan: async (planId: number): Promise<{ liked: boolean; likeCount: number }> => {
    const response = await api.post<ApiResponse<{ liked: boolean; likeCount: number }>>(`/plans/${planId}/like`);
    return response.data.data;
  },

  unlikePlan: async (planId: number): Promise<{ liked: boolean; likeCount: number }> => {
    const response = await api.delete<ApiResponse<{ liked: boolean; likeCount: number }>>(`/plans/${planId}/like`);
    return response.data.data;
  },

  sharePlanToCommunity: async (planId: number, content?: string): Promise<{ success: boolean; message: string }> => {
    const response = await api.post<ApiResponse<{ success: boolean; message: string }>>(`/plans/${planId}/share`, { content });
    return response.data.data;
  },

  getPlanInteractionStatus: async (planId: number): Promise<{ liked: boolean; likeCount: number; shareCount: number }> => {
    const response = await api.get<ApiResponse<{ liked: boolean; likeCount: number; shareCount: number }>>(`/plans/${planId}/status`);
    return response.data.data;
  },
};

export const postApi = {
  getAllPosts: async (): Promise<Post[]> => {
    const response = await api.get<ApiResponse<Post[]>>('/posts');
    console.log('API Response:', response);
    console.log('Response data:', response.data);
    console.log('Posts data:', response.data.data);
    return response.data.data;
  },

  getLatestPosts: async (limit: number = 10): Promise<Post[]> => {
    const response = await api.get<ApiResponse<Post[]>>(`/posts/latest?limit=${limit}`);
    return response.data.data;
  },

  getPopularPosts: async (limit: number = 10): Promise<Post[]> => {
    const response = await api.get<ApiResponse<Post[]>>(`/posts/popular?limit=${limit}`);
    return response.data.data;
  },

  getPostById: async (postId: number): Promise<Post> => {
    const response = await api.get<ApiResponse<Post>>(`/posts/${postId}`);
    return response.data.data;
  },

  createPost: async (data: { content: string; hashtags?: string[]; mediaUrls?: string[]; postType?: string; privacy?: string; linkedPlanId?: number }): Promise<Post> => {
    const response = await api.post<ApiResponse<Post>>('/posts', data);
    return response.data.data;
  },

  deletePost: async (postId: number): Promise<void> => {
    await api.delete(`/posts/${postId}`);
  },

  likePost: async (postId: number): Promise<{ likes: number }> => {
    const response = await api.post<ApiResponse<{ likes: number }>>(`/posts/${postId}/like`);
    return response.data.data;
  },

  unlikePost: async (postId: number): Promise<{ likes: number }> => {
    const response = await api.delete<ApiResponse<{ likes: number }>>(`/posts/${postId}/like`);
    return response.data.data;
  },

  sharePost: async (originalPostId: number, originalAuthorId: number, content?: string): Promise<Post> => {
    const response = await api.post<ApiResponse<Post>>(`/posts/${originalPostId}/share`, {
      originalPostId,
      originalAuthorId,
      content
    });
    return response.data.data;
  },

  uploadImage: async (file: File): Promise<string> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post<ApiResponse<{ url: string }>>('/upload/image', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data.data.url;
  },

  getTrendingHashtags: async (): Promise<string[]> => {
    const response = await api.get<ApiResponse<string[]>>('/posts/trending/hashtags');
    return response.data.data;
  },

  getPostsByHashtag: async (hashtag: string): Promise<Post[]> => {
    const response = await api.get<ApiResponse<Post[]>>(`/posts/hashtag/${hashtag}`);
    return response.data.data;
  },

  getUserPosts: async (userId: number, sort?: string): Promise<Post[]> => {
    const params = sort ? `?sort=${sort}` : '';
    const response = await api.get<ApiResponse<Post[]>>(`/posts/user/${userId}${params}`);
    return response.data.data;
  },
};

export const commentApi = {
  getCommentsByPostId: async (postId: number): Promise<Comment[]> => {
    const response = await api.get<ApiResponse<Comment[]>>(`/posts/${postId}/comments`);
    return response.data.data;
  },

  getPostIdByCommentId: async (commentId: number): Promise<number> => {
    const response = await api.get<ApiResponse<number>>(`/posts/comments/${commentId}/post`);
    return response.data.data;
  },

  createComment: async (postId: number, data: { content: string; mediaUrls?: string[]; parentCommentId?: number }): Promise<Comment> => {
    const response = await api.post<ApiResponse<Comment>>(`/posts/${postId}/comments`, data);
    return response.data.data;
  },

  likeComment: async (commentId: number): Promise<{ likes: number }> => {
    const response = await api.post<ApiResponse<{ likes: number }>>(`/posts/comments/${commentId}/like`);
    return response.data.data;
  },

  deleteComment: async (commentId: number): Promise<{ deletedCount: number }> => {
    const response = await api.delete<ApiResponse<{ deletedCount: number }>>(`/posts/comments/${commentId}`);
    return response.data.data;
  },

  unlikeComment: async (commentId: number): Promise<{ likes: number }> => {
    const response = await api.delete<ApiResponse<{ likes: number }>>(`/posts/comments/${commentId}/like`);
    return response.data.data;
  },
};

export const searchApi = {
  search: async (query: string, type?: string): Promise<SearchResponse> => {
    const params = new URLSearchParams({ q: query });
    if (type) params.append('type', type);
    const response = await api.get<ApiResponse<SearchResponse>>(`/search?${params.toString()}`);
    return response.data.data;
  },
};

export const activityApi = {
  getActivities: async (page: number = 1, size: number = 20): Promise<Activity[]> => {
    const response = await api.get<ApiResponse<{ records: Activity[] }>>(`/activities?page=${page}&size=${size}`);
    const data = response.data.data;
    if (data && typeof data === 'object' && 'records' in data) {
      return (data as { records: Activity[] }).records;
    }
    return [];
  },

  deleteActivity: async (activityId: number): Promise<void> => {
    await api.delete(`/activities/${activityId}`);
  },

  deleteActivities: async (activityIds: number[]): Promise<void> => {
    await api.delete('/activities/batch', { data: activityIds });
  },
};

export const notificationApi = {
  getUnreadCount: async (): Promise<number> => {
    const response = await api.get<ApiResponse<number>>('/notifications/unread-count');
    return response.data.data;
  },

  getNotifications: async (page: number = 1, size: number = 20): Promise<Notification[]> => {
    const params = new URLSearchParams({ page: String(page), size: String(size) });
    const response = await api.get<ApiResponse<{ records: Notification[] }>>(`/notifications?${params.toString()}`);
    const data = response.data.data;
    if (data && typeof data === 'object' && 'records' in data) {
      return (data as { records: Notification[] }).records;
    }
    return [];
  },

  markAsRead: async (notificationId: number): Promise<void> => {
    await api.put(`/notifications/${notificationId}/read`);
  },

  markAllAsRead: async (): Promise<void> => {
    await api.put('/notifications/read-all');
  },

  markMultipleAsRead: async (notificationIds: number[]): Promise<void> => {
    await api.put('/notifications/read-multiple', notificationIds);
  },

  deleteMultipleNotifications: async (notificationIds: number[]): Promise<void> => {
    await api.delete('/notifications/batch', { data: notificationIds });
  },
};

export const checkinApi = {
  checkCheckinExists: async (planId: number): Promise<boolean> => {
    const response = await api.get<ApiResponse<boolean>>(`/plans/${planId}/checkins/exists`);
    return response.data.data;
  },

  getCheckinsByPlanId: async (planId: number): Promise<PlanCheckin[]> => {
    const response = await api.get<ApiResponse<PlanCheckin[]>>(`/plans/${planId}/checkins`);
    return response.data.data;
  },

  checkin: async (planId: number, data: { content?: string; mood?: string; productivityScore?: number }): Promise<PlanCheckin> => {
    const response = await api.post<ApiResponse<PlanCheckin>>(`/plans/${planId}/checkins`, data);
    return response.data.data;
  },

  getCheckinCount: async (planId: number): Promise<number> => {
    const response = await api.get<ApiResponse<number>>(`/plans/${planId}/checkins/count`);
    return response.data.data;
  },
};

// AI 服务通过 Java 后端安全网关转发
// 前端不再直接调用 Python AI 服务，所有请求先经过 Java 验证 JWT
// Java 后端会通过内部密钥 (X-Internal-Api-Secret) 转发请求到 Python
const AI_API_BASE_URL = '/api/ai';

const aiApi = axios.create({
  baseURL: API_BASE_URL,  // 使用 Java 后端的基础 URL（http://localhost:8080/api）
  headers: {
    'Content-Type': 'application/json',
  },
});

// 为 aiApi 添加请求拦截器（与 api 保持一致）
aiApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

aiApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const planAssistantApi = {
  chat: async (message: string, sessionId?: string): Promise<{ response: string; session_id: string }> => {
    // 请求 Java 网关: POST http://localhost:8080/api/ai/chat
    const response = await api.post('/ai/chat', { message, session_id: sessionId });
    return response.data;
  },

  assistant: async (query: string): Promise<{ response: string }> => {
    const response = await api.post('/ai/assistant', { query });
    return response.data;
  },

  queryRAG: async (query: string, sessionId?: string, userId?: string, docIds?: number[]): Promise<{ response: string; sources: any[] }> => {
    const response = await api.post('/ai/rag/query', { 
      query, 
      session_id: sessionId || undefined, 
      user_id: userId || "default",
      top_k: 3,
      doc_ids: docIds && docIds.length > 0 ? docIds : undefined
    });
    return response.data;
  },

  uploadDocument: async (file: File, userId?: string): Promise<{ message: string; document_id: string }> => {
    const formData = new FormData();
    formData.append('file', file);
    if (userId) {
      formData.append('user_id', userId);
    }
    const response = await api.post('/ai/rag/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getDocuments: async (userId?: string): Promise<{ documents: any[] }> => {
    const params = userId ? `?user_id=${userId}` : '';
    const response = await api.get(`/ai/rag/documents${params}`);
    return response.data;
  },
};

export const chatApi = {
  getConversations: async (): Promise<ChatConversation[]> => {
    const response = await api.get<ApiResponse<ChatConversation[]>>('/chat/conversations');
    return response.data.data;
  },

  getMessages: async (conversationId: number): Promise<ChatMessage[]> => {
    const response = await api.get<ApiResponse<ChatMessage[]>>(`/chat/conversations/${conversationId}/messages`);
    return response.data.data;
  },

  sendMessage: async (receiverId: number, content: string): Promise<ChatMessage> => {
    const response = await api.post<ApiResponse<ChatMessage>>('/chat/messages', { receiverId, content });
    return response.data.data;
  },

  sharePlanToChat: async (receiverId: number, planId: number, content?: string): Promise<ChatMessage> => {
    const response = await api.post<ApiResponse<ChatMessage>>('/chat/messages/share-plan', { receiverId, planId, content });
    return response.data.data;
  },

  sharePostToChat: async (receiverId: number, postId: number, content?: string): Promise<ChatMessage> => {
    const response = await api.post<ApiResponse<ChatMessage>>('/chat/messages/share-post', { receiverId, postId, content });
    return response.data.data;
  },
};

export default api;
