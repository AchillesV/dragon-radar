CREATE DATABASE IF NOT EXISTS dragonradar;

CREATE TABLE IF NOT EXISTS dragonradar.stock_daily (
    date        Date,
    code        String,
    open        Float32,
    high        Float32,
    low         Float32,
    close       Float32,
    volume      UInt64,
    amount      Float64,
    change_pct  Float32,
    turnover    Float32,
    pe          Float32,
    pb          Float32
) ENGINE = MergeTree()
ORDER BY (code, date);

CREATE TABLE IF NOT EXISTS dragonradar.stock_minute (
    datetime    DateTime,
    code        String,
    open        Float32,
    high        Float32,
    low         Float32,
    close       Float32,
    volume      UInt64,
    amount      Float64
) ENGINE = MergeTree()
ORDER BY (code, datetime)
TTL datetime + INTERVAL 90 DAY;

CREATE TABLE IF NOT EXISTS dragonradar.fund_flow (
    date         Date,
    code         String,
    main_inflow  Float64,
    big_inflow   Float64,
    mid_inflow   Float64,
    small_inflow Float64
) ENGINE = MergeTree()
ORDER BY (code, date);
