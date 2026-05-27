"""
認證 Blueprint
url_prefix: /auth

端點：
  GET  /auth/register-status — 查詢是否開放自助註冊
  POST /auth/register        — 自助註冊（須 REGISTER_ENABLED=true）
  POST /auth/login           — 帳號密碼登入，回傳 JWT
  GET  /auth/me              — 取得當前登入使用者資訊
  POST /auth/change-password — 使用者自行修改密碼
  PUT  /auth/profile         — 使用者更新自己的顯示名稱/信箱
"""
import os
import re
import logging
from datetime import timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    jwt_required, get_jwt_identity,
    create_access_token,
)
from src.models.user import User
from src.permissions import get_current_user_id

REMEMBER_ME_DAYS = 30

logger = logging.getLogger(__name__)
app_auth = Blueprint('auth', __name__)

# 帳號格式：3–32 字元，只允許英數字、底線、連字號
_USERNAME_RE = re.compile(r'^[A-Za-z0-9_-]{3,32}$')


def _is_register_enabled() -> bool:
    """讀取 REGISTER_ENABLED 環境變數，預設為 false"""
    return os.environ.get('REGISTER_ENABLED', 'false').lower() in ('1', 'true', 'yes')


def _make_token(user: dict, remember: bool = False) -> str:
    expires = timedelta(days=REMEMBER_ME_DAYS) if remember else None  # None → 使用 config 預設
    return create_access_token(
        identity=str(user['id']),
        additional_claims={
            'role':         user['role'],
            'username':     user['username'],
            'display_name': user.get('display_name') or '',
            'remember':     remember,
        },
        expires_delta=expires,
    )


@app_auth.route('/register-status', methods=['GET'])
def register_status():
    """查詢是否開放自助註冊"""
    return jsonify({'success': True, 'enabled': _is_register_enabled()})


@app_auth.route('/register', methods=['POST'])
def register():
    """自助註冊（須 REGISTER_ENABLED=true）"""
    if not _is_register_enabled():
        return jsonify({'success': False, 'message': '目前未開放自助註冊，請聯絡管理員'}), 403

    data = request.get_json() or {}
    username     = data.get('username', '').strip()
    password     = data.get('password', '')
    confirm_pw   = data.get('confirm_password', '')
    display_name = data.get('display_name', '').strip()

    # 驗證
    if not username or not password:
        return jsonify({'success': False, 'message': 'username 與 password 為必填'}), 400
    if not _USERNAME_RE.match(username):
        return jsonify({'success': False, 'message': '帳號格式錯誤（3–32 字元，英數字／底線／連字號）'}), 400
    if len(password) < 6:
        return jsonify({'success': False, 'message': '密碼長度至少 6 個字元'}), 400
    if confirm_pw and confirm_pw != password:
        return jsonify({'success': False, 'message': '兩次密碼輸入不一致'}), 400
    if User.find_by_username(username):
        return jsonify({'success': False, 'message': '此帳號已被使用，請換一個'}), 409

    # 建立帳號（固定 role=user）
    user_id = User.create(username, password, role='user', display_name=display_name)

    # 初始化預設財務分類
    try:
        from src.models.finance import Category
        Category.init_defaults_for_user(user_id)
    except Exception as e:
        logger.warning(f'[auth] 初始化分類失敗（user_id={user_id}）：{e}')

    # 回傳 JWT，直接登入
    user = User.find_by_id(user_id)
    User.update_last_login(user_id)
    token = _make_token(user)
    logger.info(f'[auth] 新使用者自助註冊：{username} (id={user_id})')

    return jsonify({
        'success':      True,
        'token':        token,
        'user_id':      user_id,
        'username':     username,
        'display_name': display_name or username,
        'role':         'user',
    }), 201


@app_auth.route('/login', methods=['POST'])
def login():
    """帳號密碼登入，回傳 JWT token"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '缺少請求參數'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')
    remember = bool(data.get('remember', False))
    if not username or not password:
        return jsonify({'success': False, 'message': 'username 或 password 不得為空'}), 400

    user = User.find_by_username(username)
    if not user or not user.get('is_active', 1):
        return jsonify({'success': False, 'message': '帳號不存在或已停用'}), 401
    if not User.check_password(password, user['password']):
        return jsonify({'success': False, 'message': '帳號或密碼錯誤'}), 401

    token = _make_token(user, remember=remember)
    User.update_last_login(user['id'])
    logger.info(f'[auth] 使用者登入：{username} (id={user["id"]}, role={user["role"]}, remember={remember})')

    import os
    from src import JWT_ACCESS_TOKEN_EXPIRES_HOURS
    expires_seconds = REMEMBER_ME_DAYS * 86400 if remember else JWT_ACCESS_TOKEN_EXPIRES_HOURS * 3600

    return jsonify({
        'success':         True,
        'token':           token,
        'user_id':         user['id'],
        'username':        user['username'],
        'display_name':    user.get('display_name') or '',
        'role':            user['role'],
        'expires_seconds': expires_seconds,   # 前端用來設 localStorage 過期時間
    })


@app_auth.route('/me', methods=['GET'])
@jwt_required()
def me():
    """取得當前登入使用者資訊"""
    from flask_jwt_extended import get_jwt
    claims = get_jwt()
    return jsonify({
        'success':      True,
        'user_id':      int(get_jwt_identity()),
        'username':     claims.get('username', ''),
        'display_name': claims.get('display_name', ''),
        'role':         claims.get('role', 'user'),
    })


@app_auth.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """使用者自行修改密碼"""
    data = request.get_json() or {}
    old_pw = data.get('old_password', '')
    new_pw = data.get('new_password', '')
    if not old_pw or not new_pw:
        return jsonify({'success': False, 'message': '請提供 old_password 與 new_password'}), 400
    if len(new_pw) < 6:
        return jsonify({'success': False, 'message': '新密碼長度至少 6 個字元'}), 400

    user_id = get_current_user_id()
    user = User.find_by_id(user_id)
    if not user or not User.check_password(old_pw, user['password']):
        return jsonify({'success': False, 'message': '舊密碼不正確'}), 401

    User.update(user_id, password=new_pw)
    return jsonify({'success': True, 'message': '密碼已更新，請重新登入'})


@app_auth.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """使用者更新自己的顯示名稱和信箱"""
    data = request.get_json() or {}
    display_name = data.get('display_name', '')
    email        = data.get('email', '')
    user_id = get_current_user_id()
    User.update(user_id, display_name=display_name, email=email)
    return jsonify({'success': True})
