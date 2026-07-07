-- PlanHub 数据库结构文件（清理版）
-- 包含完整的表结构，但不含用户数据和敏感信息
-- 导入后会自动创建所有表

-- ----------------------------
-- MySQL dump 10.13  Distrib 8.0.34, for Win64 (x86_64)
-- ----------------------------

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for rag_documents
-- ----------------------------
DROP TABLE IF EXISTS `rag_documents`;
CREATE TABLE `rag_documents` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '文档ID',
  `user_id` bigint NOT NULL COMMENT '所属用户ID',
  `filename` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '原始文件名',
  `file_size` bigint DEFAULT '0' COMMENT '文件大小(字节)',
  `chunk_count` int DEFAULT '0' COMMENT '切分片段数',
  `file_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '磁盘文件路径',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT 'active' COMMENT '状态: active/deleted',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted_at` timestamp NULL DEFAULT NULL COMMENT '删除时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='RAG 知识库文档元数据';

-- ----------------------------
-- Table structure for rag_bm25_index
-- ----------------------------
DROP TABLE IF EXISTS `rag_bm25_index`;
CREATE TABLE `rag_bm25_index` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `doc_id` bigint NOT NULL COMMENT '文档ID',
  `chunk_index` int NOT NULL COMMENT '片段序号',
  `term` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '分词后的词',
  `tf` int NOT NULL DEFAULT '0' COMMENT '词频',
  `chunk_length` int NOT NULL DEFAULT '0' COMMENT '片段长度（冗余存储，避免JOIN）',
  `content` text COLLATE utf8mb4_unicode_ci COMMENT '片段原文（用于回显）',
  `doc_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '文档名（冗余，避免JOIN）',
  PRIMARY KEY (`id`),
  KEY `idx_doc_id` (`doc_id`),
  KEY `idx_term` (`term`),
  KEY `idx_doc_chunk` (`doc_id`,`chunk_index`),
  KEY `idx_term_doc` (`term`,`doc_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='RAG BM25 倒排索引';

-- ----------------------------
-- Table structure for achievements
-- ----------------------------
DROP TABLE IF EXISTS `achievements`;
CREATE TABLE `achievements` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '成就名称',
  `description` text COLLATE utf8mb4_unicode_ci COMMENT '成就描述',
  `icon_class` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '图标CSS类',
  `badge_color` varchar(7) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '徽章颜色 (HEX)',
  `achievement_type` enum('planning','completion','social','streak','special') COLLATE utf8mb4_unicode_ci DEFAULT 'planning' COMMENT '成就类型',
  `requirements` json DEFAULT NULL COMMENT '成就要求配置',
  `is_active` tinyint(1) DEFAULT '1' COMMENT '是否激活',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_type` (`achievement_type`),
  KEY `idx_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for activities
-- ----------------------------
DROP TABLE IF EXISTS `activities`;
CREATE TABLE `activities` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `content` text,
  `created_at` datetime(6) NOT NULL,
  `target_id` bigint DEFAULT NULL,
  `target_type` varchar(50) DEFAULT NULL,
  `type` varchar(50) NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for chat_conversations
-- ----------------------------
DROP TABLE IF EXISTS `chat_conversations`;
CREATE TABLE `chat_conversations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) DEFAULT NULL,
  `last_message` varchar(255) DEFAULT NULL,
  `last_message_time` datetime(6) DEFAULT NULL,
  `updated_at` datetime(6) DEFAULT NULL,
  `user1_id` bigint NOT NULL,
  `user1_unread` int DEFAULT NULL,
  `user2_id` bigint NOT NULL,
  `user2_unread` int DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for chat_messages
-- ----------------------------
DROP TABLE IF EXISTS `chat_messages`;
CREATE TABLE `chat_messages` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `content` text,
  `conversation_id` bigint NOT NULL,
  `created_at` datetime(6) DEFAULT NULL,
  `is_read` bit(1) DEFAULT NULL,
  `is_system_message` bit(1) DEFAULT NULL,
  `message_type` int DEFAULT NULL,
  `receiver_id` bigint NOT NULL,
  `sender_id` bigint NOT NULL,
  `shared_plan_id` bigint DEFAULT NULL,
  `shared_post_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for comment_interactions
-- ----------------------------
DROP TABLE IF EXISTS `comment_interactions`;
CREATE TABLE `comment_interactions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `comment_id` bigint NOT NULL,
  `created_at` datetime(6) DEFAULT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for notifications
-- ----------------------------
DROP TABLE IF EXISTS `notifications`;
CREATE TABLE `notifications` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `comment_id` bigint DEFAULT NULL,
  `content` text,
  `created_at` datetime(6) DEFAULT NULL,
  `is_read` bit(1) DEFAULT NULL,
  `post_id` bigint DEFAULT NULL,
  `target_user_id` bigint DEFAULT NULL,
  `type` varchar(255) NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for plan_checkins
-- ----------------------------
DROP TABLE IF EXISTS `plan_checkins`;
CREATE TABLE `plan_checkins` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `plan_id` bigint NOT NULL COMMENT '计划ID',
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `checkin_date` date NOT NULL COMMENT '打卡日期',
  `notes` text COLLATE utf8mb4_unicode_ci COMMENT '备注',
  `mood_rating` int DEFAULT NULL,
  `energy_rating` int DEFAULT NULL,
  `progress_notes` text COLLATE utf8mb4_unicode_ci COMMENT '进度备注',
  `photos` json DEFAULT NULL COMMENT '图片URL数组',
  `tags` json DEFAULT NULL COMMENT '标签数组',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_plan_date` (`plan_id`,`checkin_date`),
  KEY `idx_plan` (`plan_id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_date` (`checkin_date`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for plan_interactions
-- ----------------------------
DROP TABLE IF EXISTS `plan_interactions`;
CREATE TABLE `plan_interactions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `plan_id` bigint NOT NULL COMMENT '计划ID',
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `interaction_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `metadata` json DEFAULT NULL COMMENT '额外信息',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_interaction` (`plan_id`,`user_id`,`interaction_type`),
  KEY `idx_plan` (`plan_id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_type` (`interaction_type`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for plan_milestones
-- ----------------------------
DROP TABLE IF EXISTS `plan_milestones`;
CREATE TABLE `plan_milestones` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `plan_id` bigint NOT NULL COMMENT '计划ID',
  `title` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '里程碑标题',
  `description` text COLLATE utf8mb4_unicode_ci COMMENT '里程碑描述',
  `due_date` date DEFAULT NULL COMMENT '截止日期',
  `is_completed` tinyint(1) DEFAULT '0' COMMENT '是否完成',
  `completed_at` timestamp NULL DEFAULT NULL COMMENT '完成时间',
  `order_index` int DEFAULT '0' COMMENT '排序索引',
  PRIMARY KEY (`id`),
  KEY `idx_plan` (`plan_id`),
  KEY `idx_due_date` (`due_date`),
  KEY `idx_order` (`order_index`),
  KEY `idx_completed` (`is_completed`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for plans
-- ----------------------------
DROP TABLE IF EXISTS `plans`;
CREATE TABLE `plans` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `title` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '计划标题',
  `description` text COLLATE utf8mb4_unicode_ci COMMENT '计划描述',
  `category` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `priority` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `target_date` date DEFAULT NULL COMMENT '目标日期',
  `start_date` date DEFAULT NULL COMMENT '开始日期',
  `estimated_duration_hours` int DEFAULT '0' COMMENT '预估耗时(小时)',
  `actual_duration_hours` int DEFAULT '0' COMMENT '实际耗时(小时)',
  `progress_percentage` decimal(5,2) DEFAULT '0.00' COMMENT '进度百分比',
  `tags` json DEFAULT NULL COMMENT '标签数组',
  `cover_image_url` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '封面图片URL',
  `reminder_settings` json DEFAULT NULL COMMENT '提醒设置',
  `sharing_settings` json DEFAULT NULL COMMENT '分享设置',
  `visibility` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `completion_criteria` json DEFAULT NULL COMMENT '完成标准',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `completed_at` timestamp NULL DEFAULT NULL COMMENT '完成时间',
  `deleted_at` timestamp NULL DEFAULT NULL COMMENT '删除时间',
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_category` (`category`),
  KEY `idx_target_date` (`target_date`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for post_comments
-- ----------------------------
DROP TABLE IF EXISTS `post_comments`;
CREATE TABLE `post_comments` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `post_id` bigint NOT NULL COMMENT '帖子ID',
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `parent_comment_id` bigint DEFAULT NULL COMMENT '父评论ID',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '评论内容',
  `mentions` json DEFAULT NULL COMMENT '@提及的用户ID数组',
  `media_urls` json DEFAULT NULL COMMENT '媒体文件URL数组',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `like_count` int DEFAULT NULL,
  `reply_count` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_post` (`post_id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_parent` (`parent_comment_id`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for post_interactions
-- ----------------------------
DROP TABLE IF EXISTS `post_interactions`;
CREATE TABLE `post_interactions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `post_id` bigint NOT NULL COMMENT '帖子ID',
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `interaction_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `metadata` json DEFAULT NULL COMMENT '额外信息',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_interaction` (`post_id`,`user_id`,`interaction_type`),
  KEY `idx_post` (`post_id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_type` (`interaction_type`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for posts
-- ----------------------------
DROP TABLE IF EXISTS `posts`;
CREATE TABLE `posts` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '内容',
  `original_post_id` bigint DEFAULT NULL COMMENT '原帖ID(转发/引用)',
  `original_author_id` bigint DEFAULT NULL COMMENT '原作者ID',
  `post_type` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `media_urls` json DEFAULT NULL COMMENT '媒体文件URL数组',
  `hashtags` json DEFAULT NULL COMMENT '话题标签数组',
  `mentions` json DEFAULT NULL COMMENT '@提及的用户ID数组',
  `location` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '位置',
  `privacy` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `view_count` int DEFAULT '0' COMMENT '浏览次数',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted_at` timestamp NULL DEFAULT NULL COMMENT '删除时间',
  `linked_plan_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `original_post_id` (`original_post_id`),
  KEY `original_author_id` (`original_author_id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_type` (`post_type`),
  KEY `idx_privacy` (`privacy`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for trending_topics
-- ----------------------------
DROP TABLE IF EXISTS `trending_topics`;
CREATE TABLE `trending_topics` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tag_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '标签名称',
  `display_name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '显示名称',
  `topic_type` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `post_count` int DEFAULT '0' COMMENT '帖子数量',
  `engagement_score` decimal(10,2) DEFAULT '0.00' COMMENT '参与度分数',
  `trend_direction` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_updated` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
  `is_featured` tinyint(1) DEFAULT '0' COMMENT '是否推荐',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_tag` (`tag_name`),
  KEY `idx_type` (`topic_type`),
  KEY `idx_score` (`engagement_score`),
  KEY `idx_featured` (`is_featured`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for user_achievements
-- ----------------------------
DROP TABLE IF EXISTS `user_achievements`;
CREATE TABLE `user_achievements` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `achievement_id` bigint NOT NULL COMMENT '成就ID',
  `unlocked_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '解锁时间',
  `progress_data` json DEFAULT NULL COMMENT '进度数据',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_user_achievement` (`user_id`,`achievement_id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_achievement` (`achievement_id`),
  KEY `idx_unlocked_at` (`unlocked_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for user_relationships
-- ----------------------------
DROP TABLE IF EXISTS `user_relationships`;
CREATE TABLE `user_relationships` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `follower_id` bigint NOT NULL COMMENT '关注者ID',
  `following_id` bigint NOT NULL COMMENT '被关注者ID',
  `relationship_type` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_relationship` (`follower_id`,`following_id`,`relationship_type`),
  KEY `idx_follower` (`follower_id`),
  KEY `idx_following` (`following_id`),
  KEY `idx_relationship_type` (`relationship_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for users
-- ----------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `username` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户名',
  `email` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '邮箱',
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '密码哈希',
  `display_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '显示名称',
  `avatar_url` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '头像URL',
  `bio` text COLLATE utf8mb4_unicode_ci COMMENT '个人简介',
  `location` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '位置',
  `website_url` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '网站URL',
  `phone_number` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '电话号码',
  `date_of_birth` date DEFAULT NULL COMMENT '出生日期',
  `gender` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `timezone` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT 'Asia/Shanghai' COMMENT '时区',
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'zh-CN' COMMENT '语言',
  `theme_preference` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `color_scheme` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `notification_settings` json DEFAULT NULL COMMENT '通知设置',
  `privacy_settings` json DEFAULT NULL COMMENT '隐私设置',
  `account_status` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `email_verified` tinyint(1) DEFAULT '0' COMMENT '邮箱已验证',
  `phone_verified` tinyint(1) DEFAULT '0' COMMENT '电话已验证',
  `last_login_at` datetime DEFAULT NULL COMMENT '最后登录时间',
  `login_count` int DEFAULT '0' COMMENT '登录次数',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted_at` timestamp NULL DEFAULT NULL COMMENT '删除时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`),
  KEY `idx_username` (`username`),
  KEY `idx_email` (`email`),
  KEY `idx_display_name` (`display_name`),
  KEY `idx_account_status` (`account_status`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

-- ----------------------------
-- 初始化基础数据
-- ----------------------------

-- 成就表初始数据
INSERT INTO `achievements` VALUES 
(1,'连续打卡王','连续打卡30天','fa-fire','#FFD700','streak','{\"streak_days\": 30}',1,NULL),
(2,'学习达人','完成5个学习计划','fa-book','#4CAF50','completion','{\"category\": \"learning\", \"plan_count\": 5}',1,NULL),
(3,'社区之星','获得100个赞','fa-star','#2196F3','social','{\"likes_received\": 100}',1,NULL),
(4,'完美主义者','所有计划100%完成','fa-check-circle','#9C27B0','completion','{\"completion_rate\": 100}',1,NULL),
(5,'早起鸟','连续早于7点开始计划','fa-sun','#FF9800','streak','{\"early_start_days\": 7, \"start_time_before\": \"07:00\"}',1,NULL),
(6,'分享专家','发布50篇高质量帖子','fa-share-alt','#E91E63','social','{\"posts_count\": 50, \"quality_score\": 4.5}',1,NULL);

-- 热门话题初始数据
INSERT INTO `trending_topics` VALUES 
(1,'React学习','#React学习','hashtag',128,850.50,'stable',NULL,1),
(2,'健身打卡','#健身打卡','hashtag',89,620.25,'stable',NULL,1),
(3,'读书分享','#读书分享','hashtag',67,480.75,'stable',NULL,1),
(4,'技术分享','#技术分享','hashtag',45,320.00,'stable',NULL,1),
(5,'目标达成','#目标达成','hashtag',32,240.50,'stable',NULL,0);

-- ----------------------------
-- 注意事项
-- ----------------------------
-- 1. 导入前请先创建数据库：CREATE DATABASE planhub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- 2. 用户数据需要在应用启动后通过注册功能创建
-- 3. 其他业务数据（计划、帖子、打卡等）需要用户创建后才会产生
-- 4. 所有外键约束会在数据导入后自动生效
-- ----------------------------
