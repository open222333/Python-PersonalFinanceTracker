"""
finance_recurring.py - 週期固定收入與勞健保設定模型

管理定期固定收入規則（RecurringIncome）以及勞健保設定（InsuranceSetting）。
"""

import calendar
from datetime import date, timedelta

from src.mysql import query, execute
from src.models.finance import Transaction

# 2024 台灣勞保投保薪資分級表
LABOR_BRACKETS = [
    27600, 28800, 30300, 31800, 33300, 34800, 36300,
    38200, 40100, 42000, 43900, 45800, 48200, 50600,
    53000, 55400, 57800, 60800, 63800, 66800, 69800,
    72800, 76500, 80200, 83900, 87600,
]


class RecurringIncome:
    """
    週期固定收入模型

    管理 finance_recurring_income 資料表，支援新增、更新、刪除、查詢、
    觸發收入入帳（含自動保費扣除）等功能。

    頻率（frequency）可為：
        - yearly：每年
        - monthly：每月
        - weekly：每週
        - daily：每日
        - hourly：每小時（當日重複觸發）
    """

    TABLE = 'finance_recurring_income'

    @classmethod
    def compute_next_run_date(cls, frequency, day_of_month=None, month_of_year=None,
                              day_of_week=None, from_date=None):
        """
        依據頻率與相關欄位計算下一次執行日期。

        :param frequency: 頻率字串（yearly/monthly/weekly/daily/hourly）
        :param day_of_month: 每月幾號（monthly/yearly 使用）
        :param month_of_year: 幾月（yearly 使用）
        :param day_of_week: 星期幾（weekly 使用，0=Mon...6=Sun，對應 Python weekday()）
        :param from_date: 起始日期（date 物件），預設為今日
        :return: 下一次執行日期（date 物件）
        """
        today = from_date if from_date is not None else date.today()

        if frequency == 'hourly':
            # 當日即可再次觸發
            return today

        if frequency == 'daily':
            return today + timedelta(days=1)

        if frequency == 'weekly':
            # 0=Mon...6=Sun，使用 Python weekday()
            target_dow = int(day_of_week) if day_of_week is not None else 0
            current_dow = today.weekday()
            days_ahead = (target_dow - current_dow) % 7
            if days_ahead == 0:
                days_ahead = 7
            return today + timedelta(days=days_ahead)

        if frequency == 'monthly':
            dom = int(day_of_month) if day_of_month else 1
            if today.day < dom:
                # 本月尚未到指定日，在本月執行
                year = today.year
                month = today.month
            else:
                # 已過指定日，排到下個月
                if today.month == 12:
                    year = today.year + 1
                    month = 1
                else:
                    year = today.year
                    month = today.month + 1
            # 夾緊至該月最後一天
            last_day = calendar.monthrange(year, month)[1]
            day = min(dom, last_day)
            return date(year, month, day)

        if frequency == 'yearly':
            moy = int(month_of_year) if month_of_year else 1
            dom = int(day_of_month) if day_of_month else 1
            year = today.year
            last_day = calendar.monthrange(year, moy)[1]
            day = min(dom, last_day)
            target = date(year, moy, day)
            if target <= today:
                year += 1
                last_day = calendar.monthrange(year, moy)[1]
                day = min(dom, last_day)
                target = date(year, moy, day)
            return target

        # 預設回傳明日
        return today + timedelta(days=1)

    @classmethod
    def create(cls, user_id: int, **kwargs):
        """
        新增一筆週期固定收入規則，並自動計算 next_run_date。

        :param user_id: 使用者 ID
        :param kwargs: 欄位名稱與值（name, amount, frequency, ...）
        :return: 新記錄的 id
        """
        frequency = kwargs.get('frequency', 'monthly')
        day_of_month = kwargs.get('day_of_month')
        month_of_year = kwargs.get('month_of_year')
        day_of_week = kwargs.get('day_of_week')

        next_run = cls.compute_next_run_date(
            frequency, day_of_month, month_of_year, day_of_week
        )
        kwargs['next_run_date'] = next_run.strftime('%Y-%m-%d')
        kwargs['user_id'] = user_id

        columns = ', '.join(kwargs.keys())
        placeholders = ', '.join(['%s'] * len(kwargs))
        sql = f'INSERT INTO {cls.TABLE} ({columns}) VALUES ({placeholders})'
        result = execute(sql, list(kwargs.values()))
        return result

    @classmethod
    def update(cls, id, user_id: int, **kwargs):
        """
        更新指定 id 的週期固定收入規則，同時驗證 user_id 擁有權。
        若有更動頻率或日期相關欄位，自動重新計算 next_run_date。

        :param id: 記錄 id
        :param user_id: 使用者 ID
        :param kwargs: 欲更新的欄位與值
        :return: 影響筆數
        """
        recompute_fields = {'frequency', 'day_of_month', 'month_of_year', 'day_of_week'}
        if recompute_fields & set(kwargs.keys()):
            # 取得最新記錄以補全缺少的欄位
            current = cls.get(id, user_id=user_id)
            if current:
                frequency = kwargs.get('frequency', current.get('frequency', 'monthly'))
                day_of_month = kwargs.get('day_of_month', current.get('day_of_month'))
                month_of_year = kwargs.get('month_of_year', current.get('month_of_year'))
                day_of_week = kwargs.get('day_of_week', current.get('day_of_week'))
                next_run = cls.compute_next_run_date(
                    frequency, day_of_month, month_of_year, day_of_week
                )
                kwargs['next_run_date'] = next_run.strftime('%Y-%m-%d')

        set_clause = ', '.join([f'{k} = %s' for k in kwargs.keys()])
        values = list(kwargs.values()) + [id, user_id]
        sql = f'UPDATE {cls.TABLE} SET {set_clause} WHERE id = %s AND user_id = %s'
        return execute(sql, values)

    @classmethod
    def delete(cls, id, user_id: int):
        """
        刪除指定 id 的週期固定收入規則，同時驗證 user_id 擁有權。

        :param id: 記錄 id
        :param user_id: 使用者 ID
        :return: 影響筆數
        """
        sql = f'DELETE FROM {cls.TABLE} WHERE id = %s AND user_id = %s'
        return execute(sql, [id, user_id])

    @classmethod
    def get(cls, id, user_id: int = None):
        """
        取得單筆週期固定收入規則。

        :param id: 記錄 id
        :param user_id: 使用者 ID（若提供則同時驗證擁有權）
        :return: 記錄 dict，若不存在則回傳 None
        """
        if user_id is not None:
            sql = f'SELECT * FROM {cls.TABLE} WHERE id = %s AND user_id = %s LIMIT 1'
            rows = query(sql, [id, user_id])
        else:
            sql = f'SELECT * FROM {cls.TABLE} WHERE id = %s LIMIT 1'
            rows = query(sql, [id])
        return rows[0] if rows else None

    @classmethod
    def list_all(cls, user_id: int):
        """
        取得指定使用者的所有週期固定收入規則，並 JOIN finance_categories 取得 category_name。

        :param user_id: 使用者 ID
        :return: 記錄 list（每筆含 category_name）
        """
        sql = f"""
            SELECT r.*, c.name AS category_name
            FROM {cls.TABLE} r
            LEFT JOIN finance_categories c ON r.category_id = c.id
            WHERE r.user_id = %s
            ORDER BY r.id
        """
        return query(sql, [user_id])

    @classmethod
    def get_due(cls, user_id: int):
        """
        取得指定使用者目前到期（next_run_date <= 今日）且啟用中的週期固定收入規則。

        :param user_id: 使用者 ID
        :return: 到期記錄 list
        """
        today_str = date.today().strftime('%Y-%m-%d')
        sql = f"""
            SELECT * FROM {cls.TABLE}
            WHERE is_active = 1
              AND next_run_date <= %s
              AND user_id = %s
        """
        return query(sql, [today_str, user_id])

    @classmethod
    def toggle_active(cls, id, user_id: int):
        """
        切換指定 id 的 is_active 狀態（0 → 1，1 → 0），同時驗證 user_id 擁有權。

        :param id: 記錄 id
        :param user_id: 使用者 ID
        :return: 影響筆數
        """
        sql = f'UPDATE {cls.TABLE} SET is_active = NOT is_active WHERE id = %s AND user_id = %s'
        return execute(sql, [id, user_id])

    @classmethod
    def trigger(cls, id, user_id: int):
        """
        手動或排程觸發指定週期固定收入規則：
        1. 建立一筆 type='income' 的 Transaction 記錄。
        2. 更新 last_run_date 為今日，並重新計算 next_run_date。
        3. 若 auto_insurance=1 且存在啟用中的 InsuranceSetting，
           額外建立勞保費、健保費、勞退自提三筆支出 Transaction（金額為 0 時略過）。

        :param id: 記錄 id
        :param user_id: 使用者 ID
        :return: 觸發結果摘要 dict
        """
        record = cls.get(id, user_id=user_id)
        if not record:
            return {'success': False, 'error': f'找不到 id={id} 的記錄'}

        today = date.today()
        today_str = today.strftime('%Y-%m-%d')

        # 建立收入交易
        income_desc = f'[固定收入] {record["name"]}'
        income_tx_id = Transaction.create(
            date=today_str,
            type_='income',
            amount=record['amount'],
            category_id=record.get('category_id'),
            description=income_desc,
            note=record.get('note', ''),
            user_id=user_id,
        )

        # 更新 last_run_date 與 next_run_date
        next_run = cls.compute_next_run_date(
            record['frequency'],
            record.get('day_of_month'),
            record.get('month_of_year'),
            record.get('day_of_week'),
            from_date=today,
        )
        execute(
            f'UPDATE {cls.TABLE} SET last_run_date = %s, next_run_date = %s WHERE id = %s AND user_id = %s',
            [today_str, next_run.strftime('%Y-%m-%d'), id, user_id],
        )

        summary = {
            'success': True,
            'income_transaction_id': income_tx_id,
            'amount': record['amount'],
            'next_run_date': next_run.strftime('%Y-%m-%d'),
            'insurance_transactions': [],
        }

        # 自動保費扣除
        if record.get('auto_insurance'):
            insurance = InsuranceSetting.get_active(user_id)
            if insurance:
                calc = InsuranceSetting.calculate(
                    monthly_salary=record['amount'],
                    settings=insurance,
                )

                # 查詢是否有 '保險' 分類（限定該使用者）
                ins_category_rows = query(
                    "SELECT id FROM finance_categories WHERE name = '保險' AND user_id = %s LIMIT 1",
                    [user_id]
                )
                ins_category_id = ins_category_rows[0]['id'] if ins_category_rows else None

                insurance_items = [
                    ('勞保費', calc.get('labor_amount', 0)),
                    ('健保費', calc.get('health_amount', 0)),
                    ('勞退自提', calc.get('pension_amount', 0)),
                ]

                for desc, amount in insurance_items:
                    if amount and float(amount) > 0:
                        tx_id = Transaction.create(
                            date=today_str,
                            type_='expense',
                            amount=amount,
                            category_id=ins_category_id,
                            description=desc,
                            note=f'[固定收入自動扣除] {record["name"]}',
                            user_id=user_id,
                        )
                        summary['insurance_transactions'].append({
                            'description': desc,
                            'amount': amount,
                            'transaction_id': tx_id,
                        })

        return summary


class InsuranceSetting:
    """
    勞健保設定模型

    管理 finance_insurance_settings 資料表，支援查詢、新增/更新設定，
    以及依薪資計算勞保費、健保費與勞退自提金額。
    """

    TABLE = 'finance_insurance_settings'

    @classmethod
    def get_active(cls, user_id: int):
        """
        取得指定使用者最新一筆啟用中的勞健保設定。

        :param user_id: 使用者 ID
        :return: 設定 dict，若無則回傳 None
        """
        sql = f"""
            SELECT * FROM {cls.TABLE}
            WHERE is_active = 1 AND user_id = %s
            ORDER BY id DESC
            LIMIT 1
        """
        rows = query(sql, [user_id])
        return rows[0] if rows else None

    @classmethod
    def upsert(cls, user_id: int, **kwargs):
        """
        若提供 id 且記錄存在（且 user_id 符合）則更新，否則新增一筆設定記錄。

        :param user_id: 使用者 ID
        :param kwargs: 欄位名稱與值（可含 id）
        :return: 影響筆數或新記錄 id
        """
        record_id = kwargs.pop('id', None)

        if record_id:
            existing = query(
                f'SELECT id FROM {cls.TABLE} WHERE id = %s AND user_id = %s LIMIT 1',
                [record_id, user_id],
            )
            if existing:
                set_clause = ', '.join([f'{k} = %s' for k in kwargs.keys()])
                values = list(kwargs.values()) + [record_id, user_id]
                sql = f'UPDATE {cls.TABLE} SET {set_clause} WHERE id = %s AND user_id = %s'
                return execute(sql, values)

        kwargs['user_id'] = user_id
        columns = ', '.join(kwargs.keys())
        placeholders = ', '.join(['%s'] * len(kwargs))
        sql = f'INSERT INTO {cls.TABLE} ({columns}) VALUES ({placeholders})'
        return execute(sql, list(kwargs.values()))

    @staticmethod
    def get_bracket(salary, brackets):
        """
        依薪資找出最低且 >= salary 的投保薪資級距。
        若薪資超過所有級距，回傳最高級距。

        :param salary: 薪資金額
        :param brackets: 投保薪資分級列表（已排序）
        :return: 對應的投保薪資
        """
        for bracket in brackets:
            if salary <= bracket:
                return bracket
        return brackets[-1]

    @classmethod
    def calculate(cls, monthly_salary=None, settings=None, user_id: int = None):
        """
        依薪資與設定計算勞保費、健保費及勞退自提金額。

        計算邏輯：
        - labor_insured：若 labor_insured_salary 有設定則直接使用，否則依投保薪資分級表取得
        - health_insured：若 health_insured_salary 有設定則直接使用，否則依投保薪資分級表取得
        - labor_amount = labor_insured × labor_rate / 100
        - health_amount = health_insured × health_rate / 100 × health_employee_ratio × (1 + dependents)
        - pension_amount = monthly_salary × labor_pension_rate / 100
        - total_deduction = labor_amount + health_amount + pension_amount
        - net_income = monthly_salary - total_deduction

        :param monthly_salary: 月薪（若為 None，從 settings 取得）
        :param settings: 勞健保設定 dict；若為 None 則自動查詢啟用中設定（需提供 user_id）
        :param user_id: 使用者 ID（當 settings 為 None 時用於查詢設定）
        :return: 計算結果 dict（所有金額四捨五入至小數點第 2 位）
        """
        if settings is None:
            settings = cls.get_active(user_id)

        if settings is None:
            return {'error': '找不到啟用中的勞健保設定'}

        if monthly_salary is None:
            monthly_salary = float(settings.get('monthly_salary', 0))
        else:
            monthly_salary = float(monthly_salary)

        labor_rate = float(settings.get('labor_rate', 0))
        health_rate = float(settings.get('health_rate', 0))
        health_employee_ratio = float(settings.get('health_employee_ratio', 1))
        dependents = int(settings.get('dependents', 0))
        labor_pension_rate = float(settings.get('labor_pension_rate', 0))

        # 勞保投保薪資
        labor_insured_salary = settings.get('labor_insured_salary')
        if labor_insured_salary:
            labor_insured = float(labor_insured_salary)
        else:
            labor_insured = float(cls.get_bracket(monthly_salary, LABOR_BRACKETS))

        # 健保投保薪資
        health_insured_salary = settings.get('health_insured_salary')
        if health_insured_salary:
            health_insured = float(health_insured_salary)
        else:
            health_insured = float(cls.get_bracket(monthly_salary, LABOR_BRACKETS))

        labor_amount = labor_insured * labor_rate / 100
        health_amount = health_insured * health_rate / 100 * health_employee_ratio * (1 + dependents)
        pension_amount = monthly_salary * labor_pension_rate / 100

        total_deduction = labor_amount + health_amount + pension_amount
        net_income = monthly_salary - total_deduction

        return {
            'monthly_salary': round(monthly_salary, 2),
            'labor_insured': round(labor_insured, 2),
            'health_insured': round(health_insured, 2),
            'labor_rate': round(labor_rate, 2),
            'health_rate': round(health_rate, 2),
            'health_employee_ratio': round(health_employee_ratio, 2),
            'dependents': dependents,
            'labor_pension_rate': round(labor_pension_rate, 2),
            'labor_amount': round(labor_amount, 2),
            'health_amount': round(health_amount, 2),
            'pension_amount': round(pension_amount, 2),
            'total_deduction': round(total_deduction, 2),
            'net_income': round(net_income, 2),
        }
