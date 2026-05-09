-- AIMS PostgreSQL Database Initialization
-- Run: psql -h 127.0.0.1 -U GodyChang -d aims -f init.pg.sql

-- ============================================================
-- 1. Core Business Tables
-- ============================================================

CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    channel VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    agent_name VARCHAR(255) DEFAULT 'main',
    message TEXT,
    reply TEXT,
    intent TEXT,
    confidence DOUBLE PRECISION DEFAULT 0.0,
    skill_used TEXT,
    duration_ms INT DEFAULT 0,
    tokens_used INT DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_channel ON sessions(channel);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_agent_name ON sessions(agent_name);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,
    channel VARCHAR(255) NOT NULL,
    external_id VARCHAR(255),
    name TEXT,
    avatar TEXT,
    role VARCHAR(255) DEFAULT 'user',
    preferences TEXT DEFAULT '{}',
    interaction_count INT DEFAULT 0,
    last_active_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_users_channel ON users(channel);
CREATE INDEX IF NOT EXISTS idx_users_external_id ON users(external_id);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(255) UNIQUE NOT NULL,
    platform VARCHAR(255) NOT NULL,
    sku_id VARCHAR(255),
    title TEXT NOT NULL,
    price DOUBLE PRECISION DEFAULT 0.0,
    currency VARCHAR(255) DEFAULT 'CNY',
    category VARCHAR(255),
    subcategory TEXT,
    selling_points TEXT,
    description TEXT,
    images TEXT DEFAULT '[]',
    status VARCHAR(255) DEFAULT 'active',
    bsr_rank INT DEFAULT 0,
    review_count INT DEFAULT 0,
    rating DOUBLE PRECISION DEFAULT 0.0,
    monthly_sales INT DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_products_product_id ON products(product_id);
CREATE INDEX IF NOT EXISTS idx_products_platform ON products(platform);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(255) UNIQUE NOT NULL,
    platform VARCHAR(255) NOT NULL,
    order_no TEXT NOT NULL,
    product_id VARCHAR(255),
    product_title TEXT,
    quantity INT DEFAULT 1,
    amount DOUBLE PRECISION DEFAULT 0.0,
    currency VARCHAR(255) DEFAULT 'CNY',
    status VARCHAR(255) DEFAULT 'pending',
    buyer_id VARCHAR(255),
    buyer_name TEXT,
    shipping_address TEXT,
    tracking_number TEXT,
    logistics_status TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_orders_order_id ON orders(order_id);
CREATE INDEX IF NOT EXISTS idx_orders_platform ON orders(platform);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_buyer_id ON orders(buyer_id);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);

CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
    review_id VARCHAR(255) UNIQUE NOT NULL,
    platform VARCHAR(255) NOT NULL,
    product_id VARCHAR(255) NOT NULL,
    order_id VARCHAR(255),
    content TEXT NOT NULL,
    rating INT DEFAULT 5,
    sentiment VARCHAR(255) DEFAULT 'neutral',
    sentiment_score DOUBLE PRECISION DEFAULT 0.5,
    replied INT DEFAULT 0,
    reply_content TEXT,
    reviewer_name TEXT,
    review_date TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_reviews_review_id ON reviews(review_id);
CREATE INDEX IF NOT EXISTS idx_reviews_platform ON reviews(platform);
CREATE INDEX IF NOT EXISTS idx_reviews_product_id ON reviews(product_id);
CREATE INDEX IF NOT EXISTS idx_reviews_sentiment ON reviews(sentiment);
CREATE INDEX IF NOT EXISTS idx_reviews_replied ON reviews(replied);

CREATE TABLE IF NOT EXISTS contents (
    id SERIAL PRIMARY KEY,
    content_id VARCHAR(255) UNIQUE NOT NULL,
    type VARCHAR(255) NOT NULL,
    platform VARCHAR(255) NOT NULL,
    title TEXT,
    content TEXT,
    tags TEXT DEFAULT '[]',
    status VARCHAR(255) DEFAULT 'draft',
    published_at TEXT,
    views INT DEFAULT 0,
    likes INT DEFAULT 0,
    comments INT DEFAULT 0,
    shares INT DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_contents_content_id ON contents(content_id);
CREATE INDEX IF NOT EXISTS idx_contents_type ON contents(type);
CREATE INDEX IF NOT EXISTS idx_contents_platform ON contents(platform);
CREATE INDEX IF NOT EXISTS idx_contents_status ON contents(status);

-- ============================================================
-- 2. Cron Jobs
-- ============================================================

CREATE TABLE IF NOT EXISTS cron_jobs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    cron_expr VARCHAR(128) NOT NULL,
    description TEXT,
    agent VARCHAR(128) DEFAULT 'main',
    skill VARCHAR(128),
    action VARCHAR(128),
    params TEXT DEFAULT '{}',
    channel VARCHAR(128) DEFAULT 'feishu',
    target TEXT,
    enabled INT DEFAULT 1,
    last_run TEXT,
    next_run TEXT,
    run_count INT DEFAULT 0,
    fail_count INT DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_cron_jobs_name ON cron_jobs(name);
CREATE INDEX IF NOT EXISTS idx_cron_jobs_enabled ON cron_jobs(enabled);

CREATE TABLE IF NOT EXISTS cron_executions (
    id SERIAL PRIMARY KEY,
    job_name VARCHAR(255) NOT NULL,
    execution_id VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(64) DEFAULT 'pending',
    started_at TEXT,
    completed_at TEXT,
    duration_ms INT DEFAULT 0,
    retry_count INT DEFAULT 0,
    result TEXT,
    error_message TEXT,
    trigger_type VARCHAR(64) DEFAULT 'cron'
);
CREATE INDEX IF NOT EXISTS idx_cron_executions_job_name ON cron_executions(job_name);
CREATE INDEX IF NOT EXISTS idx_cron_executions_status ON cron_executions(status);
CREATE INDEX IF NOT EXISTS idx_cron_executions_started_at ON cron_executions(started_at);

CREATE TABLE IF NOT EXISTS cron_locks (
    job_name VARCHAR(255) PRIMARY KEY,
    locked_by TEXT,
    locked_at TEXT,
    expires_at TEXT
);

-- ============================================================
-- 3. Knowledge Base
-- ============================================================

CREATE TABLE IF NOT EXISTS knowledge_docs (
    id SERIAL PRIMARY KEY,
    doc_id VARCHAR(255) UNIQUE NOT NULL,
    category VARCHAR(255) NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT DEFAULT '[]',
    source VARCHAR(255) DEFAULT 'manual',
    vector_id VARCHAR(255),
    char_count INT DEFAULT 0,
    chunk_count INT DEFAULT 0,
    access_count INT DEFAULT 0,
    relevance_score DOUBLE PRECISION DEFAULT 0.0,
    status VARCHAR(255) DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_doc_id ON knowledge_docs(doc_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_category ON knowledge_docs(category);
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_source ON knowledge_docs(source);
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_status ON knowledge_docs(status);

-- ============================================================
-- 4. After-Sale
-- ============================================================

CREATE TABLE IF NOT EXISTS aftersale_orders (
    id SERIAL PRIMARY KEY,
    aftersale_id VARCHAR(255) UNIQUE NOT NULL,
    order_id VARCHAR(255) NOT NULL,
    type VARCHAR(255) NOT NULL,
    reason_category VARCHAR(255) NOT NULL,
    reason_detail TEXT,
    status VARCHAR(255) DEFAULT 'submitted',
    refund_amount DOUBLE PRECISION DEFAULT 0,
    evidence TEXT DEFAULT '[]',
    buyer_id VARCHAR(255),
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_aftersale_orders_aftersale_id ON aftersale_orders(aftersale_id);
CREATE INDEX IF NOT EXISTS idx_aftersale_orders_order_id ON aftersale_orders(order_id);
CREATE INDEX IF NOT EXISTS idx_aftersale_orders_status ON aftersale_orders(status);
CREATE INDEX IF NOT EXISTS idx_aftersale_orders_created_at ON aftersale_orders(created_at);

CREATE TABLE IF NOT EXISTS aftersale_timeline (
    id SERIAL PRIMARY KEY,
    aftersale_id VARCHAR(255) NOT NULL,
    status VARCHAR(255) NOT NULL,
    description TEXT,
    operator VARCHAR(255) DEFAULT 'system',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_aftersale_timeline_aftersale_id ON aftersale_timeline(aftersale_id);
CREATE INDEX IF NOT EXISTS idx_aftersale_timeline_created_at ON aftersale_timeline(created_at);

-- ============================================================
-- 5. Skill Gate
-- ============================================================

CREATE TABLE IF NOT EXISTS gate_rules (
    id SERIAL PRIMARY KEY,
    agent VARCHAR(255) NOT NULL,
    operation VARCHAR(255) NOT NULL,
    default_level VARCHAR(64) NOT NULL DEFAULT 'medium',
    conditions TEXT DEFAULT '[]',
    description TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gate_records (
    id SERIAL PRIMARY KEY,
    gate_id VARCHAR(255) NOT NULL UNIQUE,
    agent VARCHAR(255) NOT NULL,
    operation VARCHAR(255) NOT NULL,
    level VARCHAR(64) NOT NULL,
    confidence DOUBLE PRECISION DEFAULT 0.0,
    params TEXT DEFAULT '{}',
    status VARCHAR(64) NOT NULL DEFAULT 'pending',
    result TEXT DEFAULT '',
    approved_by VARCHAR(255) DEFAULT '',
    approved_at TEXT DEFAULT '',
    rejected_by VARCHAR(255) DEFAULT '',
    rejected_at TEXT DEFAULT '',
    comment TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    resolved_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS gate_notifications (
    id SERIAL PRIMARY KEY,
    gate_id VARCHAR(255) NOT NULL,
    agent VARCHAR(255) NOT NULL,
    operation VARCHAR(255) NOT NULL,
    level VARCHAR(64) NOT NULL,
    channel VARCHAR(64) DEFAULT 'feishu',
    sent_at TEXT NOT NULL,
    status VARCHAR(64) DEFAULT 'sent'
);

-- ============================================================
-- 6. Security
-- ============================================================

CREATE TABLE IF NOT EXISTS security_audit_logs (
    id SERIAL PRIMARY KEY,
    check_type VARCHAR(255) NOT NULL,
    input_text TEXT,
    result TEXT,
    risk_level VARCHAR(64) DEFAULT 'low',
    details TEXT,
    checked_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS credential_store (
    id SERIAL PRIMARY KEY,
    credential_key VARCHAR(255) UNIQUE NOT NULL,
    credential_hash TEXT NOT NULL,
    credential_type VARCHAR(64) DEFAULT 'api_key',
    description TEXT,
    rotation_days INT DEFAULT 90,
    last_rotated TEXT,
    expires_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS access_control (
    id SERIAL PRIMARY KEY,
    role VARCHAR(255) NOT NULL,
    resource VARCHAR(255) NOT NULL,
    action VARCHAR(255) NOT NULL,
    allowed INT DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rate_limits (
    id SERIAL PRIMARY KEY,
    identifier VARCHAR(255) NOT NULL,
    endpoint VARCHAR(255),
    request_count INT DEFAULT 0,
    window_start TEXT,
    window_seconds INT DEFAULT 60,
    max_requests INT DEFAULT 100,
    UNIQUE (identifier, endpoint)
);

-- ============================================================
-- 7. Knowledge Pipeline
-- ============================================================

CREATE TABLE IF NOT EXISTS kp_documents (
    id SERIAL PRIMARY KEY,
    doc_id VARCHAR(255) UNIQUE,
    title TEXT,
    category TEXT,
    content TEXT,
    tags TEXT,
    source VARCHAR(128) DEFAULT 'builtin',
    char_count INT DEFAULT 0,
    chunk_count INT DEFAULT 0,
    status VARCHAR(64) DEFAULT 'active',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS kp_chunks (
    id SERIAL PRIMARY KEY,
    chunk_id VARCHAR(255) UNIQUE,
    doc_id VARCHAR(255),
    chunk_index INT,
    content TEXT,
    char_count INT DEFAULT 0,
    vector BYTEA,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS kp_hallucination_checks (
    id SERIAL PRIMARY KEY,
    query TEXT,
    response TEXT,
    sources TEXT,
    confidence_score DOUBLE PRECISION DEFAULT 0.0,
    hallucination_risk VARCHAR(64) DEFAULT 'low',
    check_details TEXT,
    checked_at TEXT
);

CREATE TABLE IF NOT EXISTS kp_import_logs (
    id SERIAL PRIMARY KEY,
    import_id VARCHAR(255),
    source_type VARCHAR(128),
    source_path TEXT,
    total_docs INT DEFAULT 0,
    imported_docs INT DEFAULT 0,
    failed_docs INT DEFAULT 0,
    total_chunks INT DEFAULT 0,
    status VARCHAR(64) DEFAULT 'running',
    started_at TEXT,
    completed_at TEXT,
    error_message TEXT
);

-- ============================================================
-- 8. MCP Framework
-- ============================================================

CREATE TABLE IF NOT EXISTS mcp_call_logs (
    id SERIAL PRIMARY KEY,
    server_name VARCHAR(255),
    tool_name VARCHAR(255),
    params TEXT,
    result_summary TEXT,
    status VARCHAR(64) DEFAULT 'success',
    duration_ms INT DEFAULT 0,
    error_message TEXT,
    called_at TEXT
);

CREATE TABLE IF NOT EXISTS mcp_cache (
    cache_key VARCHAR(255) PRIMARY KEY,
    server_name VARCHAR(255),
    tool_name VARCHAR(255),
    params_hash VARCHAR(255),
    result TEXT,
    expires_at TEXT,
    created_at TEXT
);

-- ============================================================
-- 9. ETL & Data Quality
-- ============================================================

CREATE TABLE IF NOT EXISTS etl_pipeline_logs (
    id SERIAL PRIMARY KEY,
    pipeline_name TEXT NOT NULL,
    execution_id TEXT NOT NULL,
    status TEXT DEFAULT 'running',
    records_processed INT DEFAULT 0,
    records_inserted INT DEFAULT 0,
    records_updated INT DEFAULT 0,
    records_failed INT DEFAULT 0,
    started_at TEXT,
    completed_at TEXT,
    duration_ms INT DEFAULT 0,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS data_quality_checks (
    id SERIAL PRIMARY KEY,
    table_name TEXT NOT NULL,
    check_type TEXT NOT NULL,
    check_result TEXT,
    issues_found INT DEFAULT 0,
    checked_at TEXT
);

-- ============================================================
-- 10. Gate Initialization Data
-- ============================================================

INSERT INTO gate_rules (agent, operation, default_level, conditions, description, created_at, updated_at)
SELECT * FROM (VALUES
    ('ecommerce', 'listing_gen', 'low', '[]', 'Listing生成', NOW(), NOW()),
    ('ecommerce', 'listing_optimize', 'low', '[]', 'Listing优化', NOW(), NOW()),
    ('ecommerce', 'data_query', 'low', '[]', '数据查询', NOW(), NOW()),
    ('ecommerce', 'report_gen', 'low', '[]', '报表生成', NOW(), NOW()),
    ('ecommerce', 'ad_monitor', 'low', '[]', '广告监控', NOW(), NOW()),
    ('ecommerce', 'ad_adjust_price', 'medium', '[]', '广告调价', NOW(), NOW()),
    ('ecommerce', 'review_reply', 'medium', '[]', '差评回复', NOW(), NOW()),
    ('ecommerce', 'material_publish', 'medium', '[]', '素材发布', NOW(), NOW()),
    ('ecommerce', 'product_delete', 'high', '[]', '删除商品', NOW(), NOW()),
    ('ecommerce', 'refund', 'high', '[]', '退款操作', NOW(), NOW()),
    ('social-media', 'content_gen', 'low', '[]', '内容生成', NOW(), NOW()),
    ('social-media', 'compliance_check', 'low', '[]', '合规检测', NOW(), NOW()),
    ('social-media', 'content_publish', 'medium', '[]', '内容发布', NOW(), NOW()),
    ('social-media', 'negative_opinion', 'high', '[]', '负面舆情处理', NOW(), NOW()),
    ('cs', 'faq_reply', 'low', '[]', 'FAQ回复', NOW(), NOW()),
    ('cs', 'order_query', 'low', '[]', '订单查询', NOW(), NOW()),
    ('cs', 'refund_process', 'high', '[]', '退款处理', NOW(), NOW()),
    ('cs', 'negative_sentiment', 'high', '[]', '负面情感转人工', NOW(), NOW()),
    ('office', 'report_gen', 'low', '[]', '报表生成', NOW(), NOW()),
    ('office', 'email_draft', 'medium', '[]', '邮件草拟', NOW(), NOW()),
    ('office', 'email_send', 'high', '[]', '邮件发送', NOW(), NOW())
) AS v WHERE NOT EXISTS (SELECT 1 FROM gate_rules);

-- ============================================================
-- 11. Seed Data
-- ============================================================

-- Product seeds
INSERT INTO products (product_id, platform, title, price, category, status, created_at, updated_at)
SELECT * FROM (VALUES
    ('prod-demo-001', 'taobao', '智能降噪蓝牙耳机', 199.9, '电子产品', 'active', NOW(), NOW()),
    ('prod-demo-002', 'taobao', '无线充电器快充版', 89.9, '电子产品', 'active', NOW(), NOW()),
    ('prod-demo-003', 'jd', '便携式蓝牙音箱', 159.0, '电子产品', 'active', NOW(), NOW())
) AS v WHERE NOT EXISTS (SELECT 1 FROM products WHERE product_id = 'prod-demo-001');

-- Cron job definitions
INSERT INTO cron_jobs (name, display_name, cron_expr, description, agent, skill, action, params, channel, target, enabled, created_at, updated_at)
SELECT * FROM (VALUES
    ('daily-ai-report', 'AI行业日报', '0 9 * * *', '每天9:00推送AI行业日报', 'office', 'report-gen', 'generate_daily_report', '{"report_type": "ai_industry"}', 'feishu', 'office_group', 1, NOW(), NOW()),
    ('xhs-daily-publish', '小红书每日发布', '0 10 * * *', '每天10:00自动发布小红书', 'social-media', 'xhs-seed', 'auto_publish', '{"publish_mode": "scheduled"}', 'feishu', 'social_group', 1, NOW(), NOW()),
    ('opinion-monitor', '舆情监控', '*/10 * * * *', '每10分钟监控社媒舆情', 'social-media', 'opinion-watch', 'scan_opinions', '{"scan_type": "incremental"}', 'feishu', 'social_group', 1, NOW(), NOW()),
    ('weekly-report', '运营周报', '0 18 * * 5', '每周五18:00生成运营周报', 'office', 'report-gen', 'generate_weekly_report', '{"report_type": "weekly_operations"}', 'feishu', 'office_group', 1, NOW(), NOW())
) AS v WHERE NOT EXISTS (SELECT 1 FROM cron_jobs WHERE name = 'daily-ai-report');

-- Knowledge base seeds
INSERT INTO knowledge_docs (doc_id, category, title, content, status, created_at, updated_at)
SELECT * FROM (VALUES
    ('kb-ecom-001', 'platform_rules', '亚马逊Listing规范', 'Amazon Listing标题应包含品牌+核心关键词+产品特性+尺寸/颜色，不超过200字符。五点描述突出卖点，每点不超过500字符。', 'active', NOW(), NOW()),
    ('kb-ecom-002', 'platform_rules', '淘宝标题优化规则', '淘宝标题60字符内，核心关键词前置，避免堆砌。主图5张以上，白底图优先。', 'active', NOW(), NOW()),
    ('kb-social-001', 'platform_rules', '小红书内容规范', '禁止导流外链，禁用极限词，医疗类需资质。内容原创，图文并茂效果更佳。', 'active', NOW(), NOW())
) AS v WHERE NOT EXISTS (SELECT 1 FROM knowledge_docs WHERE doc_id = 'kb-ecom-001');
