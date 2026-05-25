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
├── Dockerfile
├── docker-compose.yml.default
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
│       ├── certs/cloudflare/       # Cloudflare 憑證放置目錄（預設空，http 模式不需要）
│       ├── templates/
│       │   ├── http/
│       │   │   └── default.conf.template               # HTTP 模式 template
│       │   └── cloudflare/
│       │       └── default.conf.template               # Cloudflare SSL 模式 template
│       └── conf.d/                 # 舊版靜態設定檔（參考用，已由 templates 取代）
│           ├── default.conf.default
│           ├── default.conf.https-letsencrypt.default
│           └── default.conf.cloudflare.default
│
└── db/
    └── finance_schema.sql          # 理財系統資料表建立 SQL
```

---

## 快速開始

### 1. 複製設定檔

```bash
cp conf/config.ini.default conf/config.ini
cp conf/flask.json.default conf/flask.json
```

### 2. 建立資料庫表格

```bash
mysql -u root -p your_database < db/finance_schema.sql
```

### 3. 設定資料庫連線

編輯 `conf/config.ini`：

```ini
[MYSQL]
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DB=your_database
```

### 4. 安裝套件並啟動

```bash
pip install -r requirements.txt
python run.py
```

首次啟動自動建立 `admin / admin` 帳號，**請立即修改密碼**。

| 服務 | 網址 |
|---|---|
| 📊 理財追蹤系統 | http://127.0.0.1:5000/finance/ |
| 🛠 系統後台管理 | http://127.0.0.1:5000/admin/ |
| 📄 Swagger API 文件 | http://127.0.0.1:5000/apidocs |

---

## Docker 部署

架構：`nginx（對外）→ app（Flask）→ MySQL / MongoDB / Redis`

### 步驟一：準備設定檔

```bash
cp docker-compose.yml.default docker-compose.yml
cp .env.default .env
cp conf/config.ini.default conf/config.ini
cp conf/flask.json.default conf/flask.json
```

### 步驟二：調整 config.ini（主機名稱改為服務名稱）

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
REDIS_PASSWORD=redis_password
```

> 本機直接跑 `python run.py` 時改回 `localhost`；Docker 容器內用服務名稱（`mysql` / `mongo` / `redis`）。

### 步驟三：首次啟動（建置 image）

```bash
docker compose up -d --build
```

> 首次啟動需要 `--build` 以建置 Flask image。之後若只修改 Python / HTML 程式碼，**不需重新 build**，直接重啟即可：
>
> ```bash
> docker compose restart app
> ```
>
> 只有異動 `requirements.txt` 或 `Dockerfile` 時，才需要再加 `--build`。

### 服務一覽

| 服務 | 映像 | 說明 |
|---|---|---|
| `nginx` | nginx:alpine | 反向代理，對外唯一入口（port 80） |
| `app` | 本地建置 | Flask 應用，僅內部 5000（不對外） |
| `mongo` | mongo:7 | MongoDB（操作紀錄） |
| `mysql` | mysql:8.0 | MySQL（理財資料） |
| `redis` | redis:7-alpine | Redis（快取） |

### 開啟系統（Docker）

| 服務 | 網址 |
|---|---|
| 📊 理財追蹤系統 | http://127.0.0.1/finance/ |
| 🛠 系統後台管理 | http://127.0.0.1/admin/ |
| 📄 Swagger API 文件 | http://127.0.0.1/apidocs |

### 部署自訂域名（含 HTTPS）

nginx 模式透過 `.env` 的 `NGINX_MODE` 控制，**不需要手動換設定檔**，只要改 `.env` 再重啟即可。

| `NGINX_MODE` | 說明 | 適用情境 |
|---|---|---|
| `http` | 純 HTTP（預設） | 本機、無域名、內網 |
| `cloudflare` | Cloudflare Origin CA SSL | 域名走 Cloudflare 代理 |

---

#### 模式一：HTTP（預設，無需額外設定）

`.env` 保持預設即可：

```env
NGINX_MODE=http
DOMAIN=_
```

---

#### 模式二：Cloudflare SSL

##### 1. DNS 設定

Cloudflare Dashboard → 你的域名 → DNS → 新增 A Record：

```
類型   名稱   值              Proxy
A      @      伺服器 IP       ☁ Proxied
```

##### 2. 伺服器開放 Port

```bash
ufw allow 80 && ufw allow 443
```

##### 3. 建立 Cloudflare Origin CA 憑證

Cloudflare Dashboard → **SSL/TLS → Origin Server → Create Certificate**

- 選 RSA，有效期 15 年
- 複製 **Origin Certificate** 和 **Private Key**

```bash
mkdir -p /etc/ssl/cloudflare
nano /etc/ssl/cloudflare/origin.pem   # 貼上 Origin Certificate
nano /etc/ssl/cloudflare/origin.key   # 貼上 Private Key
chmod 600 /etc/ssl/cloudflare/origin.key
```

##### 4. 更新 `.env`

```env
NGINX_MODE=cloudflare
DOMAIN=your.domain.com
CF_CERT_DIR=/etc/ssl/cloudflare
```

##### 5. 啟動

```bash
docker compose up -d
```

> Cloudflare SSL/TLS 模式記得設為 **Full (Strict)**，確保 Cloudflare ↔ 伺服器端對端加密。

### 常用指令

```bash
docker compose ps                    # 查看運行狀態
docker compose logs -f app           # 即時查看 Flask 日誌
docker compose logs -f nginx         # 即時查看 nginx 日誌
docker compose restart app           # 重啟應用（程式碼異動後）
docker compose restart nginx         # 重載 nginx 設定
docker compose down                  # 停止所有服務
docker compose down -v               # 停止並清除資料（不可逆）
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
| `conf/flask.json` | 含 SECRET_KEY，**勿提交版控** |
| `docker-compose.yml` | 由 `.default` 複製而來，**勿提交版控** |
| nginx 設定 | `conf/nginx/conf.d/default.conf` 不納入版控；從 `*.default` 範本複製後修改 |
| 預設帳號 | `admin / admin`，首次登入後請立即修改 |
| 理財系統分類 | 首次啟動自動插入 16 個預設分類（10 支出 + 6 收入） |
| CSV 編碼 | UTF-8 BOM，可直接以 Excel 開啟並顯示中文 |
| 股票持倉計算 | 買入股數 - 賣出股數 = 持有股數；平均成本 = 買入總成本 ÷ 買入總股數 |
| 預算警示 | 使用率 ≥ 80% 顯示黃色，> 100% 顯示紅色 |
