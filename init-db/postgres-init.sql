CREATE TABLE stocks (
    code        VARCHAR(10) PRIMARY KEY,
    name        VARCHAR(50) NOT NULL,
    market      VARCHAR(5),
    list_date   DATE,
    industry    VARCHAR(50),
    is_st       BOOLEAN DEFAULT FALSE,
    updated_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE stock_features (
    id          BIGSERIAL PRIMARY KEY,
    date        DATE NOT NULL,
    code        VARCHAR(10) NOT NULL,
    feature_id  VARCHAR(50) NOT NULL,
    score       FLOAT,
    meta        JSONB,
    UNIQUE(date, code, feature_id)
);

CREATE INDEX idx_sf_date_feature ON stock_features(date, feature_id);

CREATE TABLE user_features (
    id          BIGSERIAL PRIMARY KEY,
    user_id     VARCHAR(50) DEFAULT 'default',
    name        VARCHAR(100) NOT NULL,
    conditions  JSONB NOT NULL,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE analysis_reports (
    id           BIGSERIAL PRIMARY KEY,
    report_type  VARCHAR(20) NOT NULL,
    target_id    VARCHAR(50) NOT NULL,
    date         DATE NOT NULL,
    content      TEXT,
    generated_at TIMESTAMP DEFAULT NOW(),
    model        VARCHAR(50)
);

CREATE INDEX idx_reports_target ON analysis_reports(target_id, date);

CREATE TABLE lianban_history (
    id           BIGSERIAL PRIMARY KEY,
    date         DATE NOT NULL,
    code         VARCHAR(10) NOT NULL,
    count        INTEGER,
    limit_reason TEXT,
    UNIQUE(date, code)
);

-- 插入一些测试股票数据
INSERT INTO stocks (code, name, market, industry) VALUES
('601991', '大唐发电', 'SH', '电力设备'),
('600396', '华电辽能', 'SH', '电力设备'),
('002081', '金螳螂', 'SZ', '建筑装饰'),
('002918', '蒙娜丽莎', 'SZ', '建筑材料'),
('603618', '杭电股份', 'SH', '电气设备');
