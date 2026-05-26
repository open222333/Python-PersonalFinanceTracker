"""
使用者帳號模型（MySQL）
資料表：users
角色：admin（後台管理者）、user（一般使用者）
"""
import bcrypt
from src.mysql import query, execute

ROLES = ['admin', 'user']


class User:

    @classmethod
    def find_all(cls) -> list:
        """查詢所有使用者（不含密碼）"""
        return query(
            'SELECT id, username, display_name, email, role, is_active, last_login_at, created_at '
            'FROM users ORDER BY id'
        )

    @classmethod
    def find_by_id(cls, user_id: int) -> dict:
        """依 ID 查詢（含密碼，用於認證）"""
        rows = query('SELECT * FROM users WHERE id=%s', (user_id,))
        return rows[0] if rows else None

    @classmethod
    def find_by_username(cls, username: str) -> dict:
        """依帳號查詢（含密碼，用於認證）"""
        rows = query('SELECT * FROM users WHERE username=%s', (username,))
        return rows[0] if rows else None

    @classmethod
    def create(cls, username: str, password: str, role: str = 'user',
               display_name: str = '', email: str = '') -> int:
        """新增使用者，回傳新增 id"""
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        execute(
            'INSERT INTO users (username, password, display_name, email, role) '
            'VALUES (%s, %s, %s, %s, %s)',
            (username, hashed, display_name, email, role)
        )
        rows = query('SELECT LAST_INSERT_ID() AS id')
        return rows[0]['id'] if rows else None

    @classmethod
    def update(cls, user_id: int, password: str = None, role: str = None,
               display_name: str = None, email: str = None,
               is_active: int = None) -> bool:
        """更新使用者欄位（只更新傳入的欄位）"""
        fields, params = [], []
        if password is not None:
            fields.append('password=%s')
            params.append(bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode())
        if role is not None:
            fields.append('role=%s'); params.append(role)
        if display_name is not None:
            fields.append('display_name=%s'); params.append(display_name)
        if email is not None:
            fields.append('email=%s'); params.append(email)
        if is_active is not None:
            fields.append('is_active=%s'); params.append(is_active)
        if not fields:
            return False
        params.append(user_id)
        return execute(f'UPDATE users SET {", ".join(fields)} WHERE id=%s', params) > 0

    @classmethod
    def delete(cls, user_id: int) -> bool:
        """刪除使用者"""
        return execute('DELETE FROM users WHERE id=%s', (user_id,)) > 0

    @classmethod
    def update_last_login(cls, user_id: int) -> None:
        """更新最後登入時間"""
        execute('UPDATE users SET last_login_at=NOW() WHERE id=%s', (user_id,))

    @staticmethod
    def check_password(plain: str, hashed: str) -> bool:
        """驗證密碼"""
        return bcrypt.checkpw(plain.encode(), hashed.encode())
