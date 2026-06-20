export interface User {
  id: number;
  username: string;
  email?: string;
  displayName?: string;
  avatarUrl?: string;
  bio?: string;
  location?: string;
  websiteUrl?: string;
  phoneNumber?: string;
  dateOfBirth?: string;
  gender?: string;
  timezone?: string;
  language?: string;
  themePreference?: string;
  colorScheme?: string;
  accountStatus?: string;
  emailVerified?: boolean;
  phoneVerified?: boolean;
  lastLoginAt?: string;
  loginCount?: number;
  privacySettings?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface Plan {
  id: number;
  userId: number;
  title: string;
  description?: string;
  category: 'LEARNING' | 'FITNESS' | 'HABIT' | 'CAREER' | 'PERSONAL' | 'HEALTH' | 'CREATIVE' | 'OTHER';
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';
  status: 'DRAFT' | 'PENDING' | 'ACTIVE' | 'COMPLETED' | 'PAUSED' | 'CANCELLED';
  targetDate?: string;
  startDate?: string;
  estimatedDurationDays?: number;
  actualDurationDays?: number;
  progressPercentage: number;
  tags?: string;
  coverImageUrl?: string;
  reminderSettings?: string;
  sharingSettings?: string;
  visibility: 'PRIVATE' | 'PUBLIC' | 'FRIENDS';
  completionCriteria?: string;
  createdAt: string;
  updatedAt: string;
  completedAt?: string;
}

export interface PlanCheckin {
  id: number;
  planId: number;
  userId: number;
  checkinDate: string;
  notes?: string;
  moodRating?: number;
  energyRating?: number;
  progressNotes?: string;
  photos?: string;
  tags?: string;
  createdAt: string;
}

export interface PlanTask {
  id: number;
  planId: number;
  title: string;
  description?: string;
  completed: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface PlanSummaryResponse {
  id: number;
  title: string;
  description?: string;
  category?: string;
  status?: string;
  progressPercentage?: number;
  coverImageUrl?: string;
  createdAt?: string;
  owner?: {
    id: number;
    username: string;
    displayName?: string;
    avatarUrl?: string;
  };
}

export interface PlanInfoResponse {
  id: number;
  title: string;
  description?: string;
  category?: string;
  status?: string;
  progressPercentage?: number;
  coverImageUrl?: string;
  createdAt?: string;
  owner?: {
    id: number;
    username: string;
    displayName?: string;
    avatarUrl?: string;
  };
}

export interface PostSummaryResponse {
  id: number;
  content: string;
  hashtags?: string;
  likes: number;
  commentsCount: number;
  createdAt?: string;
  user?: {
    id: number;
    username: string;
    displayName?: string;
    avatarUrl?: string;
  };
}

export interface Post {
  id: number;
  userId: number;
  content: string;
  postType?: string;
  mediaUrls?: string;
  hashtags?: string;
  mentions?: string;
  location?: string;
  privacy?: string;
  viewCount: number;
  likes: number;
  commentsCount: number;
  createdAt: string;
  updatedAt: string;
  originalPostId?: number;
  originalAuthorId?: number;
  originalPost?: Post;
  originalAuthor?: {
    id: number;
    username: string;
    displayName?: string;
    avatarUrl?: string;
  };
  user?: {
    id: number;
    username: string;
    displayName?: string;
    avatarUrl?: string;
  };
  comments?: Comment[];
  liked?: boolean;
  linkedPlanId?: number;
  linkedPlan?: PlanInfoResponse;
}

export interface Comment {
  id: number;
  postId: number;
  userId: number;
  parentCommentId?: number;
  content: string;
  mentions?: string;
  mediaUrls?: string;
  createdAt: string;
  updatedAt: string;
  likeCount?: number;
  replyCount?: number;
  liked?: boolean;
  user?: {
    id: number;
    username: string;
    displayName?: string;
    avatarUrl?: string;
  };
}

export interface LoginResponse {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
  user: {
    id: number;
    username: string;
    displayName?: string;
    avatarUrl?: string;
  };
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  displayName: string;
  email: string;
  password: string;
}

export interface ChangePasswordRequest {
  oldPassword: string;
  newPassword: string;
}

export interface CreatePlanRequest {
  title: string;
  description?: string;
  category: string;
  priority: string;
  targetDate?: string;
  startDate?: string;
  estimatedDurationHours?: number;
  visibility?: string;
  tags?: string[];
}

export interface CreatePostRequest {
  content: string;
  imageUrl?: string;
  mediaUrls?: string[];
  postType?: string;
  hashtags?: string[];
  privacy?: string;
  location?: string;
  linkedPlanId?: number;
}

export interface CreateCommentRequest {
  content: string;
  mediaUrls?: string[];
}

export interface SearchResponse {
  users?: SearchUserResult[];
  posts?: SearchPostResult[];
  plans?: SearchPlanResult[];
  topics?: string[];
  totalResults: number;
}

export interface SearchUserResult {
  id: number;
  username: string;
  displayName?: string;
  avatarUrl?: string;
  description?: string;
  matchScore: number;
}

export interface SearchPostResult {
  id: number;
  userId?: number;
  user?: string;
  avatarUrl?: string;
  content: string;
  time: string;
  tags?: string[];
  matchScore: number;
}

export interface SearchPlanResult {
  id: number;
  title: string;
  description?: string;
  deadline?: string;
  userId?: number;
  user?: {
    name: string;
  };
  matchScore: number;
}

export interface UserProfileResponse {
    id: number;
    username: string;
    email: string;
    displayName?: string;
    avatarUrl?: string;
    bio?: string;
    publicPlans: PlanSummary[];
    publicPosts: PostSummary[];
    activities?: Activity[];
    showActivities?: boolean;
    showFollowers?: boolean;
    showFollowing?: boolean;
    showLikedContent?: boolean;
    followerCount: number;
    followingCount: number;
    isFollowing?: boolean;
}

export interface LikedItemResponse {
    id: number;
    type: 'post' | 'plan';
    title?: string;
    content?: string;
    coverImageUrl?: string;
    status?: string;
    createdAt: string;
    likedAt: string;
}

export interface PlanSummary {
    id: number;
    title: string;
    description?: string;
    status: string;
    progressPercentage: number;
    targetDate?: string;
}

export interface PostSummary {
    id: number;
    content: string;
    hashtags?: string;
    likes: number;
    commentsCount: number;
    createdAt?: string;
}

export interface Activity {
    id: number;
    userId: number;
    type: string;
    targetId?: number;
    targetType?: string;
    content?: string;
    displayText?: string;
    createdAt: string;
}

export type NotificationType = 'POST_LIKE' | 'POST_COMMENT' | 'COMMENT_LIKE' | 'COMMENT_REPLY' | 'POST_SHARE';

export interface Notification {
  id: number;
  userId: number;
  targetUserId?: number;
  postId?: number;
  commentId?: number;
  type: NotificationType;
  content: string;
  isRead: boolean;
  createdAt: string;
}

export interface ChatUser {
  id: number;
  username: string;
  displayName?: string;
  avatarUrl?: string;
}

export interface ChatMessage {
  id: number;
  senderId: number;
  receiverId: number;
  content: string;
  messageType: string;
  isRead: boolean;
  isSystemMessage: boolean;
  createdAt: string;
  sender?: ChatUser;
  receiver?: ChatUser;
  sharedPlanId?: number;
  sharedPlan?: PlanInfo;
  sharedPostId?: number;
  sharedPost?: PostSummary;
}

export interface PlanInfo {
  id: number;
  title: string;
  description?: string;
  category?: string;
  status?: string;
  progressPercentage?: number;
  coverImageUrl?: string;
  createdAt?: string;
  owner?: ChatUser;
}

export interface PostSummary {
  id: number;
  content: string;
  hashtags?: string;
  likes: number;
  commentsCount: number;
  createdAt?: string;
  user?: ChatUser;
}

export interface ChatConversation {
  id: number;
  otherUserId: number;
  otherUser: ChatUser;
  lastMessage?: string;
  lastMessageTime?: string;
  unreadCount: number;
  isMutualFollow: boolean;
  canSend: boolean;
  messageLimit?: string;
  createdAt: string;
}
