CREATE DATABASE IF NOT EXISTS aims DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE aims;

CREATE TABLE IF NOT EXISTS sessions (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  channel VARCHAR(32) NOT NULL,
  user_id VARCHAR(128) NOT NULL,
  message TEXT NOT NULL,
  reply TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_sessions_channel_user_created (channel, user_id, created_at)
);

CREATE TABLE IF NOT EXISTS users (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  channel VARCHAR(32) NOT NULL,
  external_id VARCHAR(128) NOT NULL,
  name VARCHAR(128) NOT NULL,
  avatar VARCHAR(512),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_users_channel_external (channel, external_id)
);

CREATE TABLE IF NOT EXISTS products (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  platform VARCHAR(32) NOT NULL,
  sku_id VARCHAR(128) NOT NULL,
  title VARCHAR(255) NOT NULL,
  price DECIMAL(10,2) NOT NULL DEFAULT 0,
  category VARCHAR(128) NOT NULL,
  selling_points JSON,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_products_platform_sku (platform, sku_id)
);

CREATE TABLE IF NOT EXISTS orders (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  platform VARCHAR(32) NOT NULL,
  order_no VARCHAR(128) NOT NULL,
  product_id BIGINT,
  amount DECIMAL(10,2) NOT NULL DEFAULT 0,
  status VARCHAR(64) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_orders_platform_order_no (platform, order_no),
  CONSTRAINT fk_orders_product FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS reviews (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  platform VARCHAR(32) NOT NULL,
  product_id BIGINT NOT NULL,
  content TEXT NOT NULL,
  sentiment VARCHAR(32) DEFAULT 'neutral',
  replied TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_reviews_platform_product_created (platform, product_id, created_at),
  CONSTRAINT fk_reviews_product FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS contents (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  type VARCHAR(64) NOT NULL,
  platform VARCHAR(32) NOT NULL,
  title VARCHAR(255) NOT NULL,
  content LONGTEXT NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'draft',
  published_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_contents_type_platform_status (type, platform, status)
);

CREATE TABLE IF NOT EXISTS cron_jobs (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(128) NOT NULL,
  cron_expr VARCHAR(64) NOT NULL,
  message TEXT NOT NULL,
  channel VARCHAR(32),
  last_run DATETIME NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_cron_jobs_name (name)
);

CREATE TABLE IF NOT EXISTS knowledge_docs (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  category VARCHAR(64) NOT NULL,
  title VARCHAR(255) NOT NULL,
  content LONGTEXT NOT NULL,
  vector_id VARCHAR(128),
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_knowledge_docs_category_updated (category, updated_at)
);

INSERT INTO cron_jobs (name, cron_expr, message, channel, status)
VALUES
  ('daily-ai-report', '0 9 * * *', '生成今日 AI 营销行业日报，包含电商数据和社媒热点', 'feishu', 'pending'),
  ('xhs-daily-publish', '0 10 * * *', '从待发布队列获取小红书种草内容并发布', 'feishu', 'pending'),
  ('douyin-daily-publish', '0 11 * * *', '从待发布队列获取抖音短视频脚本并发布', 'feishu', 'pending'),
  ('video-channel-publish', '0 14 * * *', '从待发布队列获取视频号内容并发布', 'feishu', 'pending'),
  ('weekly-report', '0 18 * * 5', '汇总本周电商与社媒运营数据，使用 excel-viz Skill 生成可视化周报', 'feishu', 'pending'),
  ('opinion-monitor', '*/10 * * * *', '扫描各社媒平台评论，识别负面舆情并告警', NULL, 'pending'),
  ('token-refresh', '0 */1 * * *', '刷新各电商平台 API 的 access token', NULL, 'pending'),
  ('team-daily-report', '0 8 * * *', '汇总团队昨日工作进展，生成日报并发送到飞书群', 'feishu', 'pending')
ON DUPLICATE KEY UPDATE
  cron_expr = VALUES(cron_expr),
  message = VALUES(message),
  channel = VALUES(channel),
  status = VALUES(status);
