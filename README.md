# Python-FlaskAPI

Flask API 框架範本，整合以下功能，可直接作為新專案的起始模板：

- **Swagger UI**（flasgger）— 自動產生 API 文件
- **JWT 認證** + **角色權限**（admin / operator / viewer）
- **後台管理 UI**（Bootstrap 5，支援行動裝置）
- **資料庫整合**：MongoDB、MySQL、Redis
- **Docker 部署**：nginx + Flask + MongoDB + MySQL + Redis，一鍵啟動

測試環境：Python 3.11.2

---

## 目錄

- [專案結構](#專案結構)
- [快速開始](#快速開始)
- [Docker 部署](#docker-部署)
- [API 說明](#api-說明)
- [設定檔說明](#設定檔說明)
- [擴充模組教學](#擴充模組教學)
- [注意事項](#注意事項)

---

## 專案結構

```
Python-FlaskAPI/
├── run.py                          # 啟動入口（自動產生 SECRET_KEY、建立預設 admin 帳號）
├── Dockerfile
├── docker-compose.yml.default      # Docker Compose 範本（nginx / app / mongo / mysql / redis）
├── .env.default                    # 環境變數範本
│
├── app/                            # Flask 應用程式
│   ├── __init__.py                 # 初始化、Swagger / JWT 設定、藍圖註冊
│   ├── auth/view.py                # POST /auth/login → 回傳 JWT token
│   ├── user/view.py                # 使用者 CRUD（admin 限定）
│   ├── admin/view.py               # GET /admin/ → 後台 UI
│   ├── log/view.py                 # GET /log/ → 操作紀錄
│   ├── sample/
│   │   ├── view.py                 # 範例路由
│   │   └── doc/sample.yaml        # Swagger 文件
│   └── templates/admin/index.html # 後台管理 UI
│
├── conf/
│   ├── nginx/
│   │   ├── nginx.conf              # nginx 主設定（worker / gzip / log 格式）
│   │   └── conf.d/
│   │       └── default.conf        # 反向代理設定（upstream → app:5000）
│   ├── config.py                   # TestingConfig / ProductionConfig 等
│   ├── config.ini.default          # 設定範本（LOG / MONGO / MYSQL / REDIS）
│   └── flask.json.default          # SECRET_KEY 範本
│
└── src/
    ├── __init__.py                 # 讀取全部設定參數
    ├── mongo.py                    # MongoDB singleton
    ├── mysql.py                    # MySQL 連線 pool（query / execute）
    ├── redis_client.py             # Redis singleton
    ├── permissions.py              # @require_role 裝飾器
    └── models/
        ├── user.py                 # User model（bcrypt 加密）
        └── log.py                  # Log model
```

---

## 快速開始

### 1. 複製設定檔

```bash
cp conf/config.ini.default conf/config.ini
cp conf/flask.json.default conf/flask.json
```

> `conf/flask.json` 的 `SECRET_KEY` 留空即可，`run.py` 啟動時會自動產生並寫入。

### 2. 設定資料庫連線

編輯 `conf/config.ini`，填入需要的連線資訊（不需要的資料庫保持預設值即可）：

```ini
[MONGO]
MONGO_URI=mongodb://localhost:27017
MONGO_DB=flask_app

[MYSQL]
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DB=flask_app

[REDIS]
REDIS_HOST=localhost
REDIS_PASSWORD=
```

### 3. 安裝套件並啟動

```bash
pip install -r requirements.txt
python run.py
```

首次啟動會自動建立預設帳號 `admin / admin`，**請登入後台後立即修改密碼**。

| 服務 | 網址 |
|---|---|
| 後台管理 | http://127.0.0.1:5000/admin/ |
| Swagger UI | http://127.0.0.1:5000/apidocs |

### 環境變數

| 變數 | 說明 | 預設值 |
|---|---|---|
| `FLASK_PORT` | Flask 內部埠號 | `5000` |
| `JWT_ACCESS_TOKEN_EXPIRES_HOURS` | Token 有效時數 | `8` |

---

## Docker 部署

### 1. 準備設定檔

```bash
cp docker-compose.yml.default docker-compose.yml
cp .env.default .env
cp conf/config.ini.default conf/config.ini
cp conf/flask.json.default conf/flask.json
```

> `conf/flask.json` 的 `SECRET_KEY` 留空即可，容器啟動時會自動產生並寫入。

### 2. 調整 config.ini（主機名稱改為服務名稱）

```ini
[MONGO]
MONGO_URI=mongodb://mongo:27017
MONGO_DB=flask_app

[MYSQL]
MYSQL_HOST=mysql
MYSQL_USER=flask_user
MYSQL_PASSWORD=flask_password
MYSQL_DB=flask_app

[REDIS]
REDIS_HOST=redis
REDIS_PASSWORD=redis_password
```

### 3. 啟動

```bash
docker compose up -d --build
```

### 服務一覽

| 服務 | 映像 | 對外埠號 | 說明 |
|---|---|---|---|
| `nginx` | nginx:alpine | **80** | 反向代理，統一對外入口 |
| `app` | 本地建置 | — | Flask API（僅 Docker 內部） |
| `mongo` | mongo:7 | — | MongoDB |
| `mysql` | mysql:8.0 | — | MySQL |
| `redis` | redis:7-alpine | — | Redis |

啟動後透過 nginx 存取：

| 服務 | 網址 |
|---|---|
| 後台管理 | http://localhost/admin/ |
| Swagger UI | http://localhost/apidocs |
| nginx 健康檢查 | http://localhost/nginx-health |

> Flask 不直接對外暴露，所有請求統一經由 nginx（port 80）轉發至 `app:5000`。

### nginx 設定

| 檔案 | 說明 |
|---|---|
| `conf/nginx/nginx.conf` | 主設定（worker、gzip、log 格式） |
| `conf/nginx/conf.d/default.conf` | 反向代理、upstream、client_max_body_size |

如需修改上游位址或新增 HTTPS，編輯 `conf/nginx/conf.d/default.conf` 後重啟 nginx：

```bash
docker compose restart nginx
```

### 常用指令

```bash
docker compose ps                    # 查看狀態
docker compose logs -f app           # 查看 Flask 日誌
docker compose logs -f nginx         # 查看 nginx 日誌
docker compose exec app bash         # 進入 Flask 容器
docker compose down                  # 停止
docker compose down -v               # 停止並清除資料（不可逆）
docker compose build --no-cache      # 重新建置映像
```

---

## API 說明

### 公開端點

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/` | 健康檢查 |
| POST | `/auth/login` | 登入，回傳 JWT token |
| GET | `/admin/` | 後台管理 UI |
| GET | `/apidocs` | Swagger UI |
| GET | `/sample/check/<domain>` | 域名格式驗證範例 |

### 受保護端點（需 `Authorization: Bearer <token>`）

| 方法 | 路徑 | 所需角色 | 說明 |
|---|---|---|---|
| GET | `/user/` | admin | 列出使用者 |
| POST | `/user/` | admin | 新增使用者 |
| PUT | `/user/<id>` | admin | 更新密碼或角色 |
| DELETE | `/user/<id>` | admin | 刪除使用者 |
| GET | `/log/` | 已登入 | 查詢操作紀錄 |

### 登入取得 Token

**本機開發（port 5000）**

```bash
curl -X POST http://127.0.0.1:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'
# {"success": true, "token": "<jwt>", "role": "admin"}

curl http://127.0.0.1:5000/user/ \
  -H "Authorization: Bearer <jwt>"
```

**Docker 部署（port 80，經 nginx）**

```bash
curl -X POST http://localhost/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'

curl http://localhost/user/ \
  -H "Authorization: Bearer <jwt>"
```

---

## 設定檔說明

### conf/config.ini

| 區塊 | 參數 | 說明 | 預設值 |
|---|---|---|---|
| `[LOG]` | `LOG_DISABLE` | 關閉 log（1=關閉） | `False` |
| | `LOG_PATH` | log 目錄 | `logs` |
| | `LOG_LEVEL` | 等級（DEBUG/INFO/WARNING/ERROR/CRITICAL） | `WARNING` |
| | `LOG_FILE_DISABLE` | 關閉寫入檔案（1=關閉） | `False` |
| `[SETTING]` | `FLASK_JSON_PATH` | flask.json 路徑 | `conf/flask.json` |
| | `ADMIN_TITLE` | 後台管理頁面名稱 | `後台管理` |
| `[MONGO]` | `MONGO_URI` | MongoDB 連線 URI | `mongodb://localhost:27017` |
| | `MONGO_DB` | 資料庫名稱 | `flask_app` |
| `[MYSQL]` | `MYSQL_HOST` | 主機 | `localhost` |
| | `MYSQL_PORT` | 埠號 | `3306` |
| | `MYSQL_USER` | 使用者 | `root` |
| | `MYSQL_PASSWORD` | 密碼 | _(空)_ |
| | `MYSQL_DB` | 資料庫名稱 | `flask_app` |
| `[REDIS]` | `REDIS_HOST` | 主機 | `localhost` |
| | `REDIS_PORT` | 埠號 | `6379` |
| | `REDIS_PASSWORD` | 密碼 | _(空)_ |
| | `REDIS_DB` | DB 編號 | `0` |

### conf/flask.json

```json
{ "SECRET_KEY": "" }
```

`SECRET_KEY` 留空時，`run.py` 啟動會自動產生並寫入。

---

## 擴充模組教學

以新增「商品管理」模組為例，說明完整擴充流程。

### 步驟一：建立 Blueprint

```
app/product/
├── __init__.py    （空白）
└── view.py
```

```python
# app/product/view.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from src.permissions import require_role

app_product = Blueprint('app_product', __name__)

@app_product.route('/', methods=['GET'])
@jwt_required()
def list_products():
    return jsonify({'success': True, 'data': []})

@app_product.route('/', methods=['POST'])
@jwt_required()
@require_role('admin', 'operator')
def create_product():
    data = request.get_json()
    return jsonify({'success': True}), 201
```

### 步驟二：選擇資料存取方式

**MongoDB**

```python
# src/models/product.py
from datetime import datetime
from src.mongo import get_db

class Product:
    COLLECTION = 'products'

    @classmethod
    def find_all(cls) -> list:
        return list(get_db()[cls.COLLECTION].find({}, {'_id': 0}))

    @classmethod
    def create(cls, name: str, price: float) -> str:
        result = get_db()[cls.COLLECTION].insert_one({
            'name': name, 'price': price, 'created_at': datetime.utcnow()
        })
        return str(result.inserted_id)
```

**MySQL**

```python
from src.mysql import query, execute

rows = query('SELECT id, name, price FROM products ORDER BY id DESC')
execute('INSERT INTO products (name, price) VALUES (%s, %s)', (name, price))
```

**Redis 快取**

```python
import json
from src.redis_client import get_redis

CACHE_KEY = 'products:all'
CACHE_TTL = 60  # 秒

def list_products():
    r = get_redis()
    cached = r.get(CACHE_KEY)
    if cached:
        return jsonify({'success': True, 'data': json.loads(cached)})
    rows = query('SELECT * FROM products')
    r.setex(CACHE_KEY, CACHE_TTL, json.dumps(rows))
    return jsonify({'success': True, 'data': rows})

def create_product():
    # 寫入後清除快取
    execute('INSERT INTO products (name, price) VALUES (%s, %s)', (name, price))
    get_redis().delete(CACHE_KEY)
```

### 步驟三：註冊藍圖

```python
# app/__init__.py
from app.product.view import app_product

def create_app(confgi_object=None):
    ...
    app.register_blueprint(blueprint=app_product, url_prefix='/product')
```

### 步驟四：（選用）Swagger 文件

```yaml
# app/product/doc/list_products.yaml
summary: 商品列表
tags:
  - Product
security:
  - Bearer: []
responses:
  200:
    description: 成功
```

```python
from flasgger import swag_from
import os

@app_product.route('/', methods=['GET'])
@jwt_required()
@swag_from(os.path.join('doc', 'list_products.yaml'))
def list_products():
    ...
```

### 步驟五：（選用）擴充後台 UI

編輯 [app/templates/admin/index.html](app/templates/admin/index.html)：

```html
<!-- 1. 側邊欄加入連結 -->
<a class="nav-link" id="nav-products" onclick="switchTab('products')" href="#">
  <i class="bi bi-box-seam"></i>商品管理
</a>

<!-- 2. 加入頁籤區塊 -->
<div id="tab-products" class="d-none">
  <h5 class="fw-bold"><i class="bi bi-box-seam me-2 text-primary"></i>商品管理</h5>
</div>
```

```javascript
// 3. switchTab() 加入新頁籤
function switchTab(tab) {
  ['users', 'logs', 'products'].forEach(t => {
    document.getElementById(`tab-${t}`).classList.toggle('d-none', tab !== t);
    document.getElementById(`nav-${t}`).classList.toggle('active', tab === t);
  });
  closeSidebar();
  if (tab === 'users') loadUsers();
  else if (tab === 'logs') loadLogs();
  else if (tab === 'products') loadProducts();
}

// 4. 加入 fetch 函式
async function loadProducts() {
  const res = await apiFetch('/product/');
  if (!res) return;
  const { data } = await res.json();
  // 渲染 data...
}
```

---

### 角色說明

| 角色 | 可存取範圍 |
|---|---|
| `admin` | 完整權限（含使用者管理） |
| `operator` | 一般操作（不可管理使用者） |
| `viewer` | 唯讀 |

```python
@require_role('admin')              # 僅 admin
@require_role('admin', 'operator')  # admin 或 operator
```

### 寫入操作紀錄

```python
from src.models.log import Log
from flask_jwt_extended import get_jwt_identity

Log.create(
    username=get_jwt_identity(),
    action='create_product',
    detail=f'name={name}',
    success=True
)
```

---

## 注意事項

| 項目 | 說明 |
|---|---|
| `conf/flask.json` | 含 `SECRET_KEY`，**勿提交至版控** |
| `docker-compose.yml` | 由 `docker-compose.yml.default` 複製而來，**勿提交至版控**（已加入 .gitignore） |
| Docker 資料庫密碼 | `docker-compose.yml` 中的密碼為範本預設值，**正式環境務必修改** |
| debug 模式 | 預設開啟，正式部署請改用 `ProductionConfig` 並關閉 |
| 預設帳號 | `admin / admin`，**首次啟動後立即修改** |
| nginx 設定 | `conf/nginx/conf.d/default.conf` 可自訂 upstream、HTTPS、限流等規則 |
| MySQL / Redis | 選用功能，不設定 `config.ini` 對應區塊即不啟用 |
