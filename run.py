import json
import secrets
from os.path import join

# 本機開發：自動載入 .env（Docker 不影響，docker-compose 已透過 env_file 注入）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

_FLASK_JSON_PATH = join('conf', 'flask.json')
with open(_FLASK_JSON_PATH, 'r') as _f:
    _flask_conf = json.load(_f)

if not _flask_conf.get('SECRET_KEY'):
    _flask_conf['SECRET_KEY'] = secrets.token_hex(32)
    with open(_FLASK_JSON_PATH, 'w') as _f:
        json.dump(_flask_conf, _f, indent=2)
    print('[init] 已自動產生 SECRET_KEY 並寫入 conf/flask.json')

from app import create_app
from conf.config import TestingConfig
from src.models.user import User
from src import FLASK_PORT


app = create_app(TestingConfig)

# ── 初始化預設管理員帳號（MySQL）───────────────────────────
try:
    admin = User.find_by_username('admin')
    if not admin:
        admin_id = User.create('admin', 'admin', role='admin', display_name='系統管理員')
        print(f'[init] 已建立預設帳號 admin / admin（id={admin_id}），請登入後立即修改密碼')
        # 初始化管理員的預設財務分類
        try:
            from src.models.finance import Category
            Category.init_defaults_for_user(admin_id)
        except Exception as _ce:
            print(f'[init] 管理員分類初始化略過：{_ce}')
    else:
        # 修正舊資料：確保 role 是新格式
        if admin.get('role') not in ('admin', 'user'):
            User.update(admin['id'], role='admin')
            print('[init] 已修正 admin 帳號 role')
except Exception as _e:
    print(f'[init] 使用者初始化略過（DB 可能尚未建立）：{_e}')

if __name__ == "__main__":
    app.run(
        host='0.0.0.0',
        port=FLASK_PORT,
        debug=True,
        use_reloader=True,
        reloader_type='stat',   # polling reloader：相容 Docker on macOS（inotify 跨 VM 不可靠）
    )
