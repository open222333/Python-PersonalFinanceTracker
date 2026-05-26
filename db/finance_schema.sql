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
    note TEXT,
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
    note TEXT,
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

-- 週期固定收入設定
CREATE TABLE IF NOT EXISTS finance_recurring_income (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT '項目名稱',
    amount DECIMAL(12,2) NOT NULL DEFAULT 0 COMMENT '金額',
    frequency ENUM('yearly','monthly','weekly','daily','hourly') NOT NULL DEFAULT 'monthly' COMMENT '週期',
    hour_of_day TINYINT NOT NULL DEFAULT 0 COMMENT '每天幾點（0-23）',
    day_of_week TINYINT DEFAULT NULL COMMENT '每週幾（0=週一…6=週日，Python weekday 對應）',
    day_of_month TINYINT NOT NULL DEFAULT 1 COMMENT '每月幾號（1-31）',
    month_of_year TINYINT NOT NULL DEFAULT 1 COMMENT '幾月（1-12）',
    category_id INT DEFAULT NULL COMMENT '收入分類',
    auto_insurance TINYINT(1) NOT NULL DEFAULT 0 COMMENT '觸發時是否同步產生勞健保費用',
    is_active TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否啟用',
    next_run_date DATE DEFAULT NULL COMMENT '下次預計執行日',
    last_run_date DATE DEFAULT NULL COMMENT '上次實際執行日',
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES finance_categories(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='週期固定收入設定';

-- 勞健保設定
CREATE TABLE IF NOT EXISTS finance_insurance_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    monthly_salary DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '月薪',
    labor_insured_salary DECIMAL(10,2) DEFAULT NULL COMMENT '勞保投保薪資（NULL=自動對應級距）',
    labor_rate DECIMAL(6,4) NOT NULL DEFAULT 2.4000 COMMENT '勞保員工負擔率 %（費率×員工比例）',
    health_insured_salary DECIMAL(10,2) DEFAULT NULL COMMENT '健保投保金額（NULL=自動對應）',
    health_rate DECIMAL(6,4) NOT NULL DEFAULT 5.1700 COMMENT '健保費率 %（2024）',
    health_employee_ratio DECIMAL(4,2) NOT NULL DEFAULT 0.30 COMMENT '健保員工負擔比例',
    dependents TINYINT NOT NULL DEFAULT 0 COMMENT '眷屬人數',
    labor_pension_rate DECIMAL(4,2) NOT NULL DEFAULT 0.00 COMMENT '勞退自提率 %（0–6）',
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='勞健保設定';

-- ── 使用者帳號表 ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    username     VARCHAR(50)  NOT NULL UNIQUE,
    password     VARCHAR(100) NOT NULL COMMENT 'bcrypt 雜湊',
    display_name VARCHAR(100) DEFAULT '',
    email        VARCHAR(100) DEFAULT '',
    role         ENUM('admin','user') NOT NULL DEFAULT 'user',
    is_active    TINYINT(1)   NOT NULL DEFAULT 1,
    last_login_at DATETIME    DEFAULT NULL,
    created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='使用者帳號';

-- ── 各 finance 表加入 user_id（新安裝時執行，升級用 ALTER TABLE）──
-- （新容器初始化時，由 docker-entrypoint-initdb.d 建立，欄位定義已含 user_id）
