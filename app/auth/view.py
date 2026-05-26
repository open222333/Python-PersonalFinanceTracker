"""
認證 Blueprint
url_prefix: /auth

端點：
  POST /auth/login           — 帳號密碼登入，回傳 JWT
  GET  /auth/me              — 取得當前登入使用者資訊
  POST /auth/change-password — 使用者自行修改密碼
  PUT  /auth/profile         — 使用者更新自己的顯示名稱/信箱
"""
import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    jwt_required, get_jwt_identity,
    create_access_token,
)
from src.models.user import User
from src.permissions import get_current_user_id

logger = logging.getLogger(__name__)
app_auth = Blueprint('auth', __name__)


@app_auth.route('/login', methods=['POST'])
def login():
    """帳號密碼登入，回傳 JWT token"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '缺少請求參數'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')
    if not username or not password:
        return jsonify({'success': False, 'message': 'username 或 password 不得為空'}), 400

    user = User.find_by_username(username)
    if not user or not user.get('is_active', 1):
        return jsonify({'success': False, 'message': '帳號不存在或已停用'}), 401
    if not User.check_password(password, user['password']):
        return jsonify({'success': False, 'message': '帳號或密碼錯誤'}), 401

    additional_claims = {
        'role':         user['role'],
        'username':     user['username'],
        'display_name': user.get('display_name') or '',
    }
    token = create_access_token(
        identity=str(user['id']),
        additional_claims=additional_claims,
    )
    User.update_last_login(user['id'])
    logger.info(f'[auth] 使用者登入：{username} (id={user["id"]}, role={user["role"]})')

    return jsonify({
        'success':      True,
        'token':        token,
        'user_id':      user['id'],
        'username':     user['username'],
        'display_name': user.get('display_name') or '',
        'role':         user['role'],
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
