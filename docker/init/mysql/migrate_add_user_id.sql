-- ============================================================
-- Migration: 為各 finance 表加入 user_id 欄位
--
-- 適用情境：容器已啟動過（DB 已存在），但建立時的 schema 缺少 user_id
-- 執行方式（容器正常運行時，在專案根目錄執行）：
--
--   docker exec -i python-personalfinancetracker-mysql-1 \
--     mysql -u flask_user -pflask_password flask_app \
--     < docker/init/mysql/migrate_add_user_id.sql
--
-- 注意：已存在的欄位會跳過（透過 PREPARE/EXECUTE 條件判斷）
-- ============================================================

-- 使用 information_schema 動態判斷欄位是否存在，避免重複執行報錯

-- ── finance_categories ──────────────────────────────────────
SET @col = (SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='finance_categories' AND COLUMN_NAME='user_id');
SET @sql = IF(@col=0,
    'ALTER TABLE finance_categories ADD COLUMN user_id INT DEFAULT NULL COMMENT "所屬使用者" AFTER id',
    'SELECT "skip: finance_categories.user_id already exists"');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- ── finance_transactions ────────────────────────────────────
SET @col = (SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='finance_transactions' AND COLUMN_NAME='user_id');
SET @sql = IF(@col=0,
    'ALTER TABLE finance_transactions ADD COLUMN user_id INT DEFAULT NULL COMMENT "所屬使用者" AFTER id',
    'SELECT "skip: finance_transactions.user_id already exists"');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- ── finance_stocks ──────────────────────────────────────────
SET @col = (SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='finance_stocks' AND COLUMN_NAME='user_id');
SET @sql = IF(@col=0,
    'ALTER TABLE finance_stocks ADD COLUMN user_id INT DEFAULT NULL COMMENT "所屬使用者" AFTER id',
    'SELECT "skip: finance_stocks.user_id already exists"');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- ── finance_budgets ─────────────────────────────────────────
SET @col = (SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='finance_budgets' AND COLUMN_NAME='user_id');
SET @sql = IF(@col=0,
    'ALTER TABLE finance_budgets ADD COLUMN user_id INT DEFAULT NULL COMMENT "所屬使用者" AFTER id',
    'SELECT "skip: finance_budgets.user_id already exists"');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- finance_budgets UNIQUE KEY 原本只含 (category_id, year, month)，需改為含 user_id
-- 先刪舊 key（若存在），再建新 key
SET @idx = (SELECT COUNT(*) FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='finance_budgets'
              AND INDEX_NAME='uq_budget');
SET @sql = IF(@idx>0, 'ALTER TABLE finance_budgets DROP INDEX uq_budget', 'SELECT "skip: uq_budget not found"');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

SET @idx2 = (SELECT COUNT(*) FROM information_schema.STATISTICS
             WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='finance_budgets'
               AND INDEX_NAME='uq_budget' AND COLUMN_NAME='user_id');
SET @sql = IF(@idx2=0,
    'ALTER TABLE finance_budgets ADD UNIQUE KEY uq_budget (user_id, category_id, year, month)',
    'SELECT "skip: uq_budget(user_id,...) already exists"');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- ── finance_recurring_income ────────────────────────────────
SET @col = (SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='finance_recurring_income' AND COLUMN_NAME='user_id');
SET @sql = IF(@col=0,
    'ALTER TABLE finance_recurring_income ADD COLUMN user_id INT DEFAULT NULL COMMENT "所屬使用者" AFTER id',
    'SELECT "skip: finance_recurring_income.user_id already exists"');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- ── finance_insurance_settings ──────────────────────────────
SET @col = (SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='finance_insurance_settings' AND COLUMN_NAME='user_id');
SET @sql = IF(@col=0,
    'ALTER TABLE finance_insurance_settings ADD COLUMN user_id INT DEFAULT NULL COMMENT "所屬使用者" AFTER id',
    'SELECT "skip: finance_insurance_settings.user_id already exists"');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- ── 完成 ────────────────────────────────────────────────────
SELECT 'migrate_add_user_id.sql 執行完畢' AS status;
