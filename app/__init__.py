from flask import Flask, redirect
from flasgger import Swagger
from flask_jwt_extended import JWTManager
from app.sample.view import app_sample
from app.auth.view import app_auth
from app.user.view import app_user
from app.admin.view import app_admin
from app.log.view import app_log
# 理財追蹤系統 Blueprints
from app.finance.dashboard.view import app_finance_dashboard
from app.finance.view import app_finance_category
from app.finance.transaction.view import app_finance_transaction
from app.finance.stock.view import app_finance_stock
from app.finance.budget.view import app_finance_budget
from app.finance.report.view import app_finance_report
from app.finance.yuanta.view import app_finance_yuanta
from app.finance.recurring.view import app_finance_recurring
from app.finance.quick.view import app_finance_quick
from app.docs.view import app_docs
from src import FLASK_JSON_PATH
import json

app = Flask(__name__)
template = {
    "swagger": "2.0",
    # "openapi": "3.0.0",
    "info": {
        "title": "My API",
        "description": "練習用 API文檔",
        "contact": {
            "responsibleOrganization": "ME",
            "responsibleDeveloper": "Me",
            "email": "open222333@gmail.com",
            "url": "www.test.com",
        },
        "termsOfService": "http://test.com/terms",
        "version": "0.0.1"
    },
    "host": "127.0.0.1",  # overrides localhost:500
    "basePath": "/",  # base bash for blueprint registration
    "schemes": [
        "http",
        # "https"
    ],
    "operationId": "getmyData",
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT token，格式: Bearer <token>"
        }
    }
}

swagger = Swagger(app, template=template)
jwt = JWTManager(app)


@app.route("/")
def index():
    """主域名自動跳轉至個人理財追蹤系統（含登入頁）"""
    return redirect('/finance/')


def create_app(confgi_object=None):
    app.register_blueprint(blueprint=app_sample, url_prefix='/sample')
    app.register_blueprint(blueprint=app_auth, url_prefix='/auth')
    app.register_blueprint(blueprint=app_user, url_prefix='/user')
    app.register_blueprint(blueprint=app_admin, url_prefix='/admin')
    app.register_blueprint(blueprint=app_log, url_prefix='/log')
    # 理財追蹤系統
    app.register_blueprint(blueprint=app_finance_dashboard,   url_prefix='/finance')
    app.register_blueprint(blueprint=app_finance_category,   url_prefix='/finance/category')
    app.register_blueprint(blueprint=app_finance_transaction, url_prefix='/finance/transaction')
    app.register_blueprint(blueprint=app_finance_stock,      url_prefix='/finance/stock')
    app.register_blueprint(blueprint=app_finance_budget,     url_prefix='/finance/budget')
    app.register_blueprint(blueprint=app_finance_report,     url_prefix='/finance/report')
    app.register_blueprint(blueprint=app_finance_yuanta,    url_prefix='/finance/yuanta')
    app.register_blueprint(blueprint=app_finance_recurring, url_prefix='/finance/recurring')
    app.register_blueprint(blueprint=app_finance_quick,     url_prefix='/finance/quick')
    app.register_blueprint(blueprint=app_docs,             url_prefix='/docs')
    if confgi_object:
        app.config.from_object(confgi_object)
    return app
