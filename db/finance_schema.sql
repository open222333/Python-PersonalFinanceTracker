-- 個人理財追蹤系統 資料庫 Schema
-- 執行方式: mysql -u root -p your_db < db/finance_schema.sql

-- 分類表
CREATE TABLE IF NOT EXISTS finance_categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    type ENUM('income', 'expense') NOT NULL COMMENT '收入/支出',
    color VARCHAR(20) DEFAULT '#808080',
    icon VARCHAR(50) DEFAULT 'bi-tag',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='財務分類';

-- 收支記錄表
CREATE TABLE IF NOT EXISTS finance_transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL,
    type ENUM('income', 'expense') NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    category_id INT DEFAULT NULL,
    description VARCHAR(200) DEFAULT '',
    note TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES finance_categories(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='收支記錄';

-- 股票交易表
CREATE TABLE IF NOT EXISTS finance_stocks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL,
    ticker VARCHAR(20) NOT NULL COMMENT '股票代號',
    company_name VARCHAR(100) DEFAULT '',
    market VARCHAR(10) DEFAULT 'TW' COMMENT '市場: TW/US/HK',
    action ENUM('buy', 'sell', 'dividend') NOT NULL,
    shares DECIMAL(15,4) DEFAULT 0 COMMENT '股數',
    price DECIMAL(15,4) DEFAULT 0 COMMENT '單價',
    amount DECIMAL(15,2) NOT NULL COMMENT '交易金額',
    fee DECIMAL(10,2) DEFAULT 0 COMMENT '手續費',
    tax DECIMAL(10,2) DEFAULT 0 COMMENT '交易稅',
    note TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票交易記錄';

-- 預算表
CREATE TABLE IF NOT EXISTS finance_budgets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category_id INT NOT NULL,
    year INT NOT NULL,
    month INT NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_budget (category_id, year, month),
    FOREIGN KEY (category_id) REFERENCES finance_categories(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='每月預算';
