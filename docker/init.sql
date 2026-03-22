CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    security_level INT DEFAULT 3,
    risk_threshold FLOAT DEFAULT 0.65,
    use_detail_ai_model BOOLEAN DEFAULT FALSE,
    basic_threshold FLOAT DEFAULT 0.9,
    enabled_modules VARCHAR(255) DEFAULT 'ALL',
    youtube_channel_id VARCHAR(100) UNIQUE,
    youtube_channel_name VARCHAR(100),
    youtube_channel_url VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_dictionaries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    word VARCHAR(100) NOT NULL,
    list_type VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uq_user_word (user_id, word),
    INDEX idx_user_id (user_id),
    INDEX idx_word (word)
);

CREATE TABLE IF NOT EXISTS system_dictionaries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    word VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50) DEFAULT 'SYSTEM_KEYWORD',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_word (word)
);

-- 테스트용 기본 유저 생성 (userId=1)
INSERT INTO users (username, security_level, risk_threshold, use_detail_ai_model, basic_threshold, enabled_modules)
VALUES ('test_user', 3, 0.65, FALSE, 0.9, 'ALL')
ON DUPLICATE KEY UPDATE username=username;