# Python-PersonalFinanceTracker

個人理財追蹤系統 — 以 Flask 後端 + Bootstrap 5 SPA 前端實作，支援收支記錄、股票管理、預算追蹤與視覺化報表。

測試環境：Python 3.11.2

---

## 功能列表

| 功能 | 說明 |
|---|---|
| **收支記錄** | 新增 / 編輯 / 刪除收入與支出，支援日期、分類、關鍵字篩選與分頁 |
| **股票管理** | 記錄買入 / 賣出 / 股利，自動計算持倉、平均成本、已實現損益 |
| **自訂分類** | 支援收入 / 支出分類，含自訂顏色與 Bootstrap Icons 圖示 |
| **預算管理** | 設定各分類每月預算，即時顯示使用率與超支警示 |
| **報表分析** | 年度收支趨勢長條圖、月份支出分類圓餅圖 |
| **資料匯出** | 一鍵匯出 CSV（UTF-8 BOM）或 Excel（.xlsx）|
| **JWT 認證** | 所有 API 需帶 Bearer Token，前端 SPA 自動管理登入狀態 |

---

## 系統架構

```
Python-PersonalFinanceTracker/
│
├── run.py                          # 啟動入口（自動建立 admin 帳號、初始化財務分類）
├── requirements.txt
├── docker-compose.yml.default      # Docker Compose 範本（複製為 docker-compose.yml 後使用）
├── .env.default                    # 環境變數範本（複製為 .env 後使用）
│
├── app/                            # Flask 應用程式
│   ├── __init__.py                 # Blueprint 註冊
│   ├── auth/view.py                # POST /auth/login
│   ├── user/view.py                # 使用者 CRUD
│   ├── admin/view.py               # 系統後台 UI
│   ├── finance/
│   │   ├── view.py                 # /finance/category/*  分類 CRUD
│   │   ├── transaction/view.py     # /finance/transaction/* 收支 CRUD
│   │   ├── stock/view.py           # /finance/stock/* 股票 CRUD + 持倉/損益
│   │   ├── budget/view.py          # /finance/budget/* 預算 CRUD + 執行率
│   │   ├── report/view.py          # /finance/report/* 報表 + 匯出
│   │   └── dashboard/view.py       # GET /finance/ → 前端 SPA 頁面
│   └── templates/
│       ├── admin/index.html        # 系統管理後台
│       └── finance/dashboard.html  # 理財追蹤 SPA（主要介面）
│
├── src/
│   ├── mysql.py                    # MySQL 連線池
│   ├── models/
│   │   ├── user.py                 # 使用者模型
│   │   ├── log.py                  # 操作紀錄模型
│   │   └── finance.py              # 理財模型（Category / Transaction / Stock / Budget / Report）
│   └── permissions.py              # @require_role 裝飾器
│
├── conf/
│   ├── config.ini.default          # DB 連線設定範本
│   ├── flask.json.default          # SECRET_KEY 範本
│   └── nginx/
│       ├── nginx.conf              # nginx 主設定（worker、gzip、log 格式）
│       ├── certs/cloudflare/       # Cloudflare 憑證放置目錄（http 模式不需要）
│       └── conf.d/
│           ├── default.conf.http.template              # HTTP 模式範本
│           ├── default.conf.cloudflare.template        # Cloudflare SSL 模式範本
│           └── default.conf.https-letsencrypt.template # Let's Encrypt 模式範本
│
├── docker/
│   ├── Dockerfile                  # Flask 映像建置檔
│   ├── database/
│   │   ├── mongo/                  # MongoDB 持久化資料（volume）
│   │   ├── mysql/                  # MySQL 持久化資料（volume）
│   │   └── redis/                  # Redis 持久化資料（volume）
│   └── init/
│       └── mysql/
│           └── finance_schema.sql  # MySQL 首次啟動自動建立的資料表（4 張表）
│
├── db/
│   └── finance_schema.sql          # 手動建表用（與 docker/init/mysql/ 同內容）
│
└── logs/                           # Flask 日誌輸出目錄（Docker volume 掛載點）
```

---

## 快速開始（本機直接執行）

> 適合本機開發測試，需自行安裝並啟動 MySQL（和選用的 MongoDB、Redis）。

### 1. 複製設定檔

```bash
cp conf/config.ini.default conf/config.ini
cp conf/flask.json.default conf/flask.json
```

### 2. 調整 `conf/config.ini` — 改為本機連線

```ini
[MONGO]
MONGO_URI=mongodb://localhost:27017

[MYSQL]
MYSQL_HOST=localhost
MYSQL_USER=root           # 或你的 MySQL 使用者
MYSQL_PASSWORD=           # 填入你的 MySQL 密碼
MYSQL_DB=finance          # 資料庫名稱（自行決定）

[REDIS]
REDIS_HOST=localhost
; REDIS_PASSWORD=         # 本機 Redis 無密碼則留空（保持註解）
```

> ⚠️ **注意**：`config.ini` 預設內容是 Docker 服務名稱（`mysql` / `mongo` / `redis`）。
> 本機執行前務必改為 `localhost`，否則連線會失敗。

### 3. 建立資料庫與資料表

```bash
# 建立資料庫（若尚未存在）
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS finance CHARACTER SET utf8mb4;"

# 建立 4 張資料表
mysql -u root -p finance < db/finance_schema.sql
```

### 4. 安裝套件並啟動

```bash
pip install -r requirements.txt
python run.py
```

首次啟動自動建立 `admin / admin` 帳號，並插入 16 個預設財務分類，**請立即修改密碼**。

| 服務 | 網址 |
|---|---|
| 📊 理財追蹤系統 | http://127.0.0.1:5000/finance/ |
| 🛠 系統後台管理 | http://127.0.0.1:5000/admin/ |
| 📄 Swagger API 文件 | http://127.0.0.1:5000/apidocs |

---

## Docker 部署

架構：`nginx（port 80/443）→ app（Flask:5000）→ MySQL / MongoDB / Redis`

### 步驟一：複製設定檔

```bash
cp docker-compose.yml.default docker-compose.yml
cp .env.default .env
cp conf/config.ini.default conf/config.ini
cp conf/flask.json.default conf/flask.json
```

### 步驟二：調整 `conf/config.ini`（使用 Docker 服務名稱）

```ini
[MONGO]
MONGO_URI=mongodb://mongo:27017

[MYSQL]
MYSQL_HOST=mysql
MYSQL_USER=flask_user
MYSQL_PASSWORD=flask_password
MYSQL_DB=flask_app

[REDIS]
REDIS_HOST=redis
REDIS_PASSWORD=redis_password   # ← 取消此行的 ; 註解
```

> **本機 vs Docker 設定差異：**
>
> | 項目 | 本機直接執行 | Docker 部署 |
> |---|---|---|
> | MYSQL_HOST | `localhost` | `mysql` |
> | MONGO_URI | `mongodb://localhost:27017` | `mongodb://mongo:27017` |
> | REDIS_HOST | `localhost` | `redis` |
> | REDIS_PASSWORD | 空（視本機設定） | `redis_password` |

### 步驟三：建立 logs 目錄

```bash
mkdir -p logs
```

> Docker 會將容器內的 Flask 日誌掛載到此目錄，若目錄不存在會導致 volume 掛載失敗。

### 步驟四：首次啟動（建置 image）

```bash
docker compose up -d --build
```

**首次啟動會自動：**
- 建置 Flask image（安裝 requirements.txt 所有套件）
- MySQL 初始化資料庫並執行 `docker/init/mysql/finance_schema.sql`，自動建立 4 張資料表
- Flask 啟動後插入 16 個預設財務分類

> **注意：** MySQL 容器加入了 `healthcheck`，Flask 會等 MySQL 完全就緒（約 30–60 秒）後才啟動，不會出現連線失敗。

---

後續修改程式碼（`.py` / `.html`）時：
```bash
docker compose restart app    # ← 不需重新 build，直接重啟
```

異動 `requirements.txt` 或 `docker/Dockerfile` 時：
```bash
docker compose build app && docker compose up -d app   # ← 需重新 build
```

### 服務一覽

| 服務 | 映像 | 說明 |
|---|---|---|
| `nginx` | nginx:alpine | 反向代理，對外唯一入口（port 80 / 443） |
| `app` | 本地建置 | Flask 應用，僅內部 5000（不對外） |
| `mongo` | mongo:7 | MongoDB（使用者帳號、操作紀錄） |
| `mysql` | mysql:8.0 | MySQL（所有理財資料） |
| `redis` | redis:7-alpine | Redis（快取，密碼：redis_password） |

### 開啟系統

| 服務 | 網址 |
|---|---|
| 📊 個人理財追蹤系統 | http://localhost/finance/ |
| 🛠 系統後台管理 | http://localhost/admin/ |
| 📄 Swagger API 文件 | http://localhost/apidocs |

---

## 部署自訂域名（HTTPS）

nginx 模式透過 `.env` 的 `NGINX_MODE` 控制，無需手動修改設定檔。

| `NGINX_MODE` | 說明 | 適用情境 |
|---|---|---|
| `http` | 純 HTTP（預設） | 本機、IP 直連、內網 |
| `cloudflare` | Cloudflare Origin CA SSL | 域名走 Cloudflare 代理（推薦） |
| `https-letsencrypt` | Let's Encrypt 自動憑證 | 有公開域名的 VPS |

### 模式一：HTTP（預設，無需額外設定）

`.env` 維持預設：
```env
NGINX_MODE=http
DOMAIN=_
```

啟動後直接以 `http://IP` 存取。

---

### 模式二：Cloudflare SSL（推薦）

#### 1. DNS 設定

Cloudflare Dashboard → 你的域名 → DNS → 新增：

```
類型   名稱   值（伺服器 IP）   Proxy
A      @      1.2.3.4          ☁ Proxied
```

#### 2. 伺服器開放 Port

```bash
ufw allow 80 && ufw allow 443
```

#### 3. 建立 Origin CA 憑證

Cloudflare Dashboard → **SSL/TLS → Origin Server → Create Certificate**

選 RSA 2048、有效期 15 年，複製 Certificate 和 Private Key：

```bash
mkdir -p /etc/ssl/cloudflare
nano /etc/ssl/cloudflare/origin.pem    # 貼上 Origin Certificate
nano /etc/ssl/cloudflare/origin.key    # 貼上 Private Key
chmod 600 /etc/ssl/cloudflare/origin.key
```

#### 4. 更新 `.env`

```env
NGINX_MODE=cloudflare
DOMAIN=your.domain.com
CF_CERT_DIR=/etc/ssl/cloudflare
```

#### 5. 啟動

```bash
docker compose up -d
```

> Cloudflare SSL/TLS 模式需設為 **Full (Strict)**，確保端對端加密。

---

## 常用維運指令

```bash
# 查看狀態
docker compose ps

# 即時日誌
docker compose logs -f app           # Flask 日誌
docker compose logs -f nginx         # nginx 日誌
docker compose logs -f mysql         # MySQL 日誌

# 重啟
docker compose restart app           # 程式碼修改後重啟 Flask
docker compose restart nginx         # nginx 設定修改後重啟

# 停止
docker compose down                  # 停止（保留資料）
docker compose down -v               # 停止並清除所有資料 ⚠️ 不可逆

# 強制重建（requirements.txt / Dockerfile 有修改時）
docker compose build app --no-cache && docker compose up -d app

# 進入容器除錯
docker compose exec app bash         # 進入 Flask 容器
docker compose exec mysql bash       # 進入 MySQL 容器
docker compose exec mysql mysql -u flask_user -pflask_password flask_app  # 直接開 MySQL CLI
```

---

## API 端點

### 認證

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/auth/login` | 登入取得 JWT token |

### 分類管理 `/finance/category`

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/` | 查詢分類（?type=income/expense） |
| POST | `/` | 新增分類 |
| PUT | `/<id>` | 更新分類 |
| DELETE | `/<id>` | 刪除分類 |

### 收支記錄 `/finance/transaction`

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/` | 查詢記錄（?date_from=&date_to=&type=&category_id=&keyword=&limit=&offset=） |
| GET | `/<id>` | 查詢單筆 |
| POST | `/` | 新增記錄 |
| PUT | `/<id>` | 更新記錄 |
| DELETE | `/<id>` | 刪除記錄 |
| GET | `/summary` | 月份收支概況（?year=&month=） |

### 股票管理 `/finance/stock`

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/` | 查詢交易記錄（?date_from=&date_to=&ticker=&action=&limit=&offset=） |
| GET | `/<id>` | 查詢單筆 |
| POST | `/` | 新增交易（action: buy/sell/dividend） |
| PUT | `/<id>` | 更新記錄 |
| DELETE | `/<id>` | 刪除記錄 |
| GET | `/portfolio` | 持倉彙總（持有股數、平均成本） |
| GET | `/pnl` | 已實現損益彙總 |
| GET | `/dividend` | 股利彙總 |

### 預算管理 `/finance/budget`

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/` | 查詢預算（?year=&month=） |
| POST | `/` | 設定預算（UPSERT） |
| PUT | `/<id>` | 更新金額 |
| DELETE | `/<id>` | 刪除 |
| GET | `/status` | 預算執行率（各分類已用/剩餘/使用率） |

### 報表與匯出 `/finance/report`

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/dashboard` | 儀表板摘要（本月收支、預算執行率、持倉數、最近交易） |
| GET | `/monthly` | 月報（?year=&month=） |
| GET | `/yearly` | 年度趨勢（?year=） |
| GET | `/category` | 分類統計（?date_from=&date_to=&type=expense） |
| GET | `/export` | 匯出檔案（?type=transactions/stocks&format=csv/excel&date_from=&date_to=） |

---

## 資料模型

### finance_categories（財務分類）
| 欄位 | 型別 | 說明 |
|---|---|---|
| id | INT PK | 自動遞增 |
| name | VARCHAR(50) | 分類名稱 |
| type | ENUM | income / expense |
| color | VARCHAR(20) | 顯示顏色（#RRGGBB） |
| icon | VARCHAR(50) | Bootstrap Icons class |

### finance_transactions（收支記錄）
| 欄位 | 型別 | 說明 |
|---|---|---|
| id | INT PK | |
| date | DATE | 交易日期 |
| type | ENUM | income / expense |
| amount | DECIMAL(15,2) | 金額 |
| category_id | INT FK | 關聯分類（可空） |
| description | VARCHAR(200) | 簡短說明 |
| note | TEXT | 詳細備注 |

### finance_stocks（股票交易）
| 欄位 | 型別 | 說明 |
|---|---|---|
| id | INT PK | |
| date | DATE | 交易日期 |
| ticker | VARCHAR(20) | 股票代號 |
| company_name | VARCHAR(100) | 公司名稱 |
| market | VARCHAR(10) | TW / US / HK |
| action | ENUM | buy / sell / dividend |
| shares | DECIMAL(15,4) | 股數 |
| price | DECIMAL(15,4) | 單價 |
| amount | DECIMAL(15,2) | 交易金額 |
| fee | DECIMAL(10,2) | 手續費 |
| tax | DECIMAL(10,2) | 交易稅 |

### finance_budgets（月度預算）
| 欄位 | 型別 | 說明 |
|---|---|---|
| id | INT PK | |
| category_id | INT FK | 關聯支出分類 |
| year | INT | 年份 |
| month | INT | 月份 |
| amount | DECIMAL(15,2) | 預算金額 |
| UNIQUE | (category_id, year, month) | 防止重複設定 |

---

## 技術棧

| 類別 | 技術 |
|---|---|
| 後端框架 | Flask 2.2 + Flask-JWT-Extended |
| 資料庫 | MySQL（PyMySQL 連線池） |
| API 文件 | Swagger（flasgger） |
| 前端框架 | Bootstrap 5.3 + Bootstrap Icons |
| 圖表 | Chart.js 4.4（折線 / 長條 / 圓餅圖） |
| 資料處理 | pandas |
| 匯出 | pandas（CSV）+ openpyxl（Excel） |
| 部署 | Docker + nginx 反向代理 |

---

## 注意事項

| 項目 | 說明 |
|---|---|
| `conf/flask.json` | 含 SECRET_KEY，**勿提交版控**（已加入 .gitignore） |
| `docker-compose.yml` / `.env` | 由 `.default` 複製而來，**勿提交版控** |
| `conf/config.ini` | 含 DB 密碼，**勿提交版控**（已加入 .gitignore） |
| 本機 vs Docker 設定 | `config.ini` 的 host 需手動切換：本機用 `localhost`，Docker 用服務名稱 |
| MySQL TEXT 欄位 | MySQL 8.0 嚴格模式不允許 `TEXT DEFAULT ''`，schema 已修正為 `TEXT`（無 DEFAULT）|
| MySQL 連線池 | PyMySQL 1.0+ 已移除 `pymysql.pool`，改用 `DBUtils.PooledDB`（requirements.txt 已含）|
| `logs/` 目錄 | Docker volume 掛載點，**需手動建立**（`mkdir -p logs`）否則啟動失敗 |
| MySQL init SQL | 只在 Docker volume 為空時自動執行；若需重新初始化，刪除 `docker/database/mysql/` 內容後重啟 |
| 預設帳號 | `admin / admin`，首次登入後請立即修改 |
| 理財系統分類 | 首次啟動自動插入 16 個預設分類（10 支出 + 6 收入） |
| CSV 編碼 | UTF-8 BOM，可直接以 Excel 開啟並顯示中文 |
| 股票持倉計算 | 買入股數 − 賣出股數 = 持有股數；平均成本 = 買入總成本 ÷ 買入總股數 |
| 預算警示 | 使用率 ≥ 80% 顯示黃色，> 100% 顯示紅色 |
| 正式部署 | 修改 `docker-compose.yml` 內的預設密碼（`root_password` / `flask_password` / `redis_password`） |
