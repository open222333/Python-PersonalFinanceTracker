"""
理財系統前台頁面 Blueprint
url_prefix: /finance
"""

from flask import Blueprint, render_template

app_finance_dashboard = Blueprint('app_finance_dashboard', __name__)


@app_finance_dashboard.route('/')
def finance_index():
    """回傳理財系統主頁（SPA，不需 JWT，由前端處理登入邏輯）"""
    return render_template('finance/dashboard.html', admin_title='個人理財追蹤系統')
