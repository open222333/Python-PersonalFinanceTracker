"""
定期收入與保險設定管理 Blueprint
url_prefix: /finance/recurring
"""

import logging
from datetime import date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from src.permissions import require_role, get_current_user_id
from src.models.finance_recurring import RecurringIncome, InsuranceSetting

logger = logging.getLogger(__name__)

app_finance_recurring = Blueprint('app_finance_recurring', __name__)


def _serialize_rows(rows: list) -> list:
    """將查詢結果中的 date / datetime 轉為字串"""
    result = []
    for row in rows:
        r = dict(row)
        for k, v in r.items():
            if hasattr(v, 'isoformat'):
                r[k] = v.isoformat()
            elif not isinstance(v, (int, float, str, bool, type(None))):
                r[k] = str(v)
        result.append(r)
    return result


# ---------------------------------------------------------------------------
# 定期收入 CRUD
# ---------------------------------------------------------------------------

@app_finance_recurring.route('/', methods=['GET'])
@jwt_required()
@require_role('admin', 'user')
def list_recurring():
    """
    查詢所有定期收入規則
    回傳全部規則清單（包含停用中的規則）
    """
    user_id = get_current_user_id()
    try:
        rows = RecurringIncome.list_all(user_id=user_id)
        return jsonify({'success': True, 'data': _serialize_rows(rows)})
    except Exception as e:
        logger.exception('list_recurring 失敗')
        return jsonify({'success': False, 'message': str(e)}), 500


@app_finance_recurring.route('/', methods=['POST'])
@jwt_required()
@require_role('admin', 'user')
def create_recurring():
    """
    新增定期收入規則
    必填欄位：name, amount, frequency
    選填欄位：day_of_month, month_of_year, day_of_week, hour_of_day,
              category_id, auto_insurance, note
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '缺少請求參數'}), 400

    name      = data.get('name', '').strip()
    amount    = data.get('amount')
    frequency = data.get('frequency', '').strip()

    if not name:
        return jsonify({'success': False, 'message': 'name 不得為空'}), 400
    if amount is None:
        return jsonify({'success': False, 'message': 'amount 不得為空'}), 400
    if not frequency:
        return jsonify({'success': False, 'message': 'frequency 不得為空'}), 400

    user_id = get_current_user_id()
    try:
        new_id = RecurringIncome.create(
            name=name,
            amount=float(amount),
            frequency=frequency,
            day_of_month=data.get('day_of_month'),
            month_of_year=data.get('month_of_year'),
            day_of_week=data.get('day_of_week'),
            hour_of_day=data.get('hour_of_day'),
            category_id=data.get('category_id'),
            auto_insurance=data.get('auto_insurance'),
            note=data.get('note', ''),
            user_id=user_id,
        )
        return jsonify({'success': True, 'id': new_id}), 201
    except Exception as e:
        logger.exception('create_recurring 失敗')
        return jsonify({'success': False, 'message': str(e)}), 500


@app_finance_recurring.route('/<int:id>', methods=['GET'])
@jwt_required()
@require_role('admin', 'user')
def get_recurring(id):
    """
    查詢單筆定期收入規則
    路由參數：id（規則 ID）
    """
    user_id = get_current_user_id()
    try:
        row = RecurringIncome.find_by_id(id, user_id=user_id)
        if not row:
            return jsonify({'success': False, 'message': '記錄不存在'}), 404
        return jsonify({'success': True, 'data': _serialize_rows([row])[0]})
    except Exception as e:
        logger.exception('get_recurring 失敗')
        return jsonify({'success': False, 'message': str(e)}), 500


@app_finance_recurring.route('/<int:id>', methods=['PUT'])
@jwt_required()
@require_role('admin', 'user')
def update_recurring(id):
    """
    更新定期收入規則
    路由參數：id（規則 ID）
    可更新欄位：name, amount, frequency, day_of_month, month_of_year,
                day_of_week, hour_of_day, category_id, auto_insurance, note
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '缺少請求參數'}), 400

    allowed = {
        'name', 'amount', 'frequency', 'day_of_month', 'month_of_year',
        'day_of_week', 'hour_of_day', 'category_id', 'auto_insurance', 'note',
    }
    kwargs = {k: v for k, v in data.items() if k in allowed}
    if 'amount' in kwargs:
        kwargs['amount'] = float(kwargs['amount'])

    user_id = get_current_user_id()
    try:
        if not RecurringIncome.update(id, user_id, **kwargs):
            return jsonify({'success': False, 'message': '記錄不存在或無變更'}), 404
        return jsonify({'success': True})
    except Exception as e:
        logger.exception('update_recurring 失敗')
        return jsonify({'success': False, 'message': str(e)}), 500


@app_finance_recurring.route('/<int:id>', methods=['DELETE'])
@jwt_required()
@require_role('admin', 'user')
def delete_recurring(id):
    """
    刪除定期收入規則
    路由參數：id（規則 ID）
    """
    user_id = get_current_user_id()
    try:
        if not RecurringIncome.delete(id, user_id):
            return jsonify({'success': False, 'message': '記錄不存在'}), 404
        return jsonify({'success': True})
    except Exception as e:
        logger.exception('delete_recurring 失敗')
        return jsonify({'success': False, 'message': str(e)}), 500


@app_finance_recurring.route('/<int:id>/toggle', methods=['POST'])
@jwt_required()
@require_role('admin', 'user')
def toggle_recurring(id):
    """
    切換定期收入規則的啟用／停用狀態
    路由參數：id（規則 ID）
    回傳切換後的 is_active 值
    """
    user_id = get_current_user_id()
    try:
        new_state = RecurringIncome.toggle_active(id, user_id=user_id)
        if new_state is None:
            return jsonify({'success': False, 'message': '記錄不存在'}), 404
        return jsonify({'success': True, 'is_active': new_state})
    except Exception as e:
        logger.exception('toggle_recurring 失敗')
        return jsonify({'success': False, 'message': str(e)}), 500


# ---------------------------------------------------------------------------
# 到期 / 觸發
# ---------------------------------------------------------------------------

@app_finance_recurring.route('/due', methods=['GET'])
@jwt_required()
@require_role('admin', 'user')
def list_due():
    """
    查詢已到期的定期收入規則
    條件：next_run_date <= 今日 且 is_active = 1
    """
    user_id = get_current_user_id()
    try:
        rows = RecurringIncome.get_due(user_id=user_id)
        return jsonify({'success': True, 'data': _serialize_rows(rows)})
    except Exception as e:
        logger.exception('list_due 失敗')
        return jsonify({'success': False, 'message': str(e)}), 500


@app_finance_recurring.route('/<int:id>/trigger', methods=['POST'])
@jwt_required()
@require_role('admin', 'user')
def trigger_one(id):
    """
    手動觸發單筆定期收入規則
    路由參數：id（規則 ID）
    回傳觸發結果摘要 dict
    """
    user_id = get_current_user_id()
    try:
        result = RecurringIncome.trigger(id, user_id=user_id)
        if result is None:
            return jsonify({'success': False, 'message': '記錄不存在或觸發失敗'}), 404
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        logger.exception('trigger_one 失敗')
        return jsonify({'success': False, 'message': str(e)}), 500


@app_finance_recurring.route('/trigger-all', methods=['POST'])
@jwt_required()
@require_role('admin', 'user')
def trigger_all():
    """
    批次觸發所有到期的定期收入規則
    依序呼叫 RecurringIncome.get_due() 取得到期清單後逐一觸發，
    回傳成功觸發筆數與各筆結果清單
    """
    user_id = get_current_user_id()
    try:
        due_rows = RecurringIncome.get_due(user_id=user_id)
        results = []
        triggered = 0
        for row in due_rows:
            row_id = dict(row).get('id')
            try:
                result = RecurringIncome.trigger(row_id)
                results.append({'id': row_id, 'success': True, 'result': result})
                triggered += 1
            except Exception as inner_e:
                logger.warning('trigger_all：觸發 id=%s 失敗：%s', row_id, inner_e)
                results.append({'id': row_id, 'success': False, 'message': str(inner_e)})
        return jsonify({'success': True, 'triggered': triggered, 'results': results})
    except Exception as e:
        logger.exception('trigger_all 失敗')
        return jsonify({'success': False, 'message': str(e)}), 500


# ---------------------------------------------------------------------------
# 保險設定
# ---------------------------------------------------------------------------

@app_finance_recurring.route('/insurance', methods=['GET'])
@jwt_required()
@require_role('admin', 'user')
def get_insurance():
    """
    查詢目前生效的保險設定
    若尚未設定則回傳空 dict
    """
    user_id = get_current_user_id()
    try:
        setting = InsuranceSetting.get_active(user_id=user_id)
        if not setting:
            return jsonify({'success': True, 'data': {}})
        return jsonify({'success': True, 'data': _serialize_rows([setting])[0]})
    except Exception as e:
        logger.exception('get_insurance 失敗')
        return jsonify({'success': False, 'message': str(e)}), 500


@app_finance_recurring.route('/insurance', methods=['POST'])
@jwt_required()
@require_role('admin', 'user')
def upsert_insurance():
    """
    新增或更新保險設定（UPSERT）
    欄位：monthly_salary, labor_insured_salary, labor_rate,
          health_insured_salary, health_rate, health_employee_ratio,
          dependents, labor_pension_rate, note
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '缺少請求參數'}), 400

    allowed = {
        'monthly_salary', 'labor_insured_salary', 'labor_rate',
        'health_insured_salary', 'health_rate', 'health_employee_ratio',
        'dependents', 'labor_pension_rate', 'note',
    }
    kwargs = {k: v for k, v in data.items() if k in allowed}

    user_id = get_current_user_id()
    try:
        record_id = InsuranceSetting.upsert(user_id=user_id, **kwargs)
        return jsonify({'success': True, 'id': record_id}), 201
    except Exception as e:
        logger.exception('upsert_insurance 失敗')
        return jsonify({'success': False, 'message': str(e)}), 500


@app_finance_recurring.route('/insurance/calculate', methods=['GET'])
@jwt_required()
@require_role('admin', 'user')
def calculate_insurance():
    """
    試算薪資保險扣款
    QueryString：
      salary              (float, 必填；若未傳入則嘗試使用已儲存設定的 monthly_salary)
      labor_rate          (float, 選填，覆蓋設定值)
      health_rate         (float, 選填，覆蓋設定值)
      health_employee_ratio (float, 選填，覆蓋設定值)
      dependents          (int,   選填，覆蓋設定值)
      labor_pension_rate  (float, 選填，覆蓋設定值)
    回傳各項扣款金額的計算結果 dict
    """
    user_id = get_current_user_id()
    try:
        # 取出 salary：優先使用 query param，否則讀取已儲存的設定
        salary_param = request.args.get('salary')
        if salary_param is not None:
            salary = float(salary_param)
        else:
            setting = InsuranceSetting.get_active(user_id=user_id)
            if not setting:
                return jsonify({'success': False, 'message': '未提供 salary 且無已儲存的設定'}), 400
            salary = float(dict(setting).get('monthly_salary', 0) or 0)
            if salary <= 0:
                return jsonify({'success': False, 'message': '未提供 salary 且儲存的 monthly_salary 無效'}), 400

        # 選填覆蓋參數
        overrides = {}
        for key in ('labor_rate', 'health_rate', 'health_employee_ratio',
                    'labor_pension_rate'):
            val = request.args.get(key)
            if val is not None:
                overrides[key] = float(val)
        dependents_param = request.args.get('dependents')
        if dependents_param is not None:
            overrides['dependents'] = int(dependents_param)

        result = InsuranceSetting.calculate(salary=salary, user_id=user_id, **overrides)
        return jsonify({'success': True, 'result': result})
    except ValueError as e:
        return jsonify({'success': False, 'message': f'參數格式錯誤：{e}'}), 400
    except Exception as e:
        logger.exception('calculate_insurance 失敗')
        return jsonify({'success': False, 'message': str(e)}), 500
