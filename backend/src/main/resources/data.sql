-- 为 post_comments 表添加 parent_comment_id 列（如果不存在）
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE table_name = 'post_comments'
    AND table_schema = DATABASE()
    AND column_name = 'parent_comment_id'
  ) > 0,
  'SELECT 1',
  'ALTER TABLE post_comments ADD COLUMN parent_comment_id BIGINT NULL AFTER user_id'
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- 初始化热门话题数据（如果表为空）
INSERT INTO trending_topics (tag_name, display_name, topic_type, post_count, engagement_score, trend_direction, last_updated, is_featured)
SELECT * FROM (
    SELECT '年度计划' AS tag_name, '年度计划' AS display_name, 'HASHTAG' AS topic_type, 150 AS post_count, 1250.50 AS engagement_score, 'RISING' AS trend_direction, NOW() AS last_updated, TRUE AS is_featured UNION ALL
    SELECT '学习计划', '学习计划', 'HASHTAG', 120, 980.25, 'RISING', NOW(), TRUE UNION ALL
    SELECT '健身计划', '健身计划', 'HASHTAG', 95, 765.80, 'STABLE', NOW(), TRUE UNION ALL
    SELECT '旅行计划', '旅行计划', 'HASHTAG', 88, 620.45, 'FALLING', NOW(), FALSE UNION ALL
    SELECT '工作计划', '工作计划', 'HASHTAG', 200, 1580.00, 'RISING', NOW(), TRUE UNION ALL
    SELECT '阅读计划', '阅读计划', 'HASHTAG', 65, 445.20, 'STABLE', NOW(), FALSE UNION ALL
    SELECT '减肥计划', '减肥计划', 'HASHTAG', 78, 520.75, 'RISING', NOW(), FALSE UNION ALL
    SELECT '早起计划', '早起计划', 'HASHTAG', 45, 310.00, 'STABLE', NOW(), FALSE UNION ALL
    SELECT '考研计划', '考研计划', 'HASHTAG', 55, 420.60, 'RISING', NOW(), FALSE UNION ALL
    SELECT '备考计划', '备考计划', 'HASHTAG', 40, 285.30, 'STABLE', NOW(), FALSE
) AS tmp
WHERE NOT EXISTS (SELECT 1 FROM trending_topics);
