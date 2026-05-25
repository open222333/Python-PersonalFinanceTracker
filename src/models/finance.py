"""
個人理財追蹤系統 — 資料模型
包含 Category、Transaction、Stock、Budget、Report 五個模型類別
"""

from datetime import datetime
from src.mysql import query, execute


# ─────────────────────────────────────────────
# 分類模型
# ─────────────────────────────────────────────
class Category:
    """財務分類（收入 / 支出）"""

    # 預設支出分類
    _DEFAULT_EXPENSE = [
        ('飲食',   'expense', '#FF6B6B', 'bi-cup-straw'),
        ('交通',   'expense', '#4ECDC4', 'bi-bus-front'),
        ('娛樂',   'expense', '#45B7D1', 'bi-controller'),
        ('購物',   'expense', '#96CEB4', 'bi-bag'),
        ('醫療',   'expense', '#FFEAA7', 'bi-heart-pulse'),
        ('住宿',   'expense', '#DDA0DD', 'bi-house'),
        ('教育',   'expense', '#98D8C8', 'bi-book'),
        ('水電費', 'expense', '#F7DC6F', 'bi-lightning'),
        ('保險',   'expense', '#F0A500', 'bi-shield-check'),
        ('其他支出', 'expense', '#B0B0B0', 'bi-three-dots'),
    ]

    # 預設收入分類
    _DEFAULT_INCOME = [
        ('薪資',     'income', '#2ECC71', 'bi-briefcase'),
        ('獎金',     'income', '#3498DB', 'bi-gift'),
        ('投資收益', 'income', '#9B59B6', 'bi-graph-up-arrow'),
        ('股利',     'income', '#1ABC9C', 'bi-cash-coin'),
        ('兼職收入', 'income', '#E67E22', 'bi-laptop'),
        ('其他收入', 'income', '#F39C12', 'bi-plus-circle'),
    ]

    @classmethod
    def init_defaults(cls):
        """初始化預設分類；若資料表已有資料則略過"""
        try:
            rows = query('SELECT COUNT(*) AS cnt FROM finance_categories')
            if rows and rows[0]['cnt'] > 0:
                return
            for row in cls._DEFAULT_EXPENSE + cls._DEFAULT_INCOME:
                execute(
                    'INSERT INTO finance_categories (name, type, color, icon) VALUES (%s, %s, %s, %s)',
                    row
                )
            print('[init] 已插入預設財務分類')
        except Exception as e:
            print(f'[init] 插入預設分類失敗：{e}')

    @staticmethod
    def find_all(type_filter: str = None) -> list:
        """查詢所有分類，可按 type 篩選"""
        if type_filter in ('income', 'expense'):
            return query(
                'SELECT * FROM finance_categories WHERE type=%s ORDER BY id',
                (type_filter,)
            )
        return query('SELECT * FROM finance_categories ORDER BY type, id')

    @staticmethod
    def find_by_id(cat_id: int) -> dict:
        """依 ID 查詢單筆分類"""
        rows = query('SELECT * FROM finance_categories WHERE id=%s', (cat_id,))
        return rows[0] if rows else None

    @staticmethod
    def create(name: str, type_: str, color: str = '#808080', icon: str = 'bi-tag') -> int:
        """新增分類，回傳新增 ID"""
        conn_rows = query(
            'SELECT LAST_INSERT_ID() AS id FROM finance_categories WHERE 1=0'
        )  # 取最後插入 ID 需另想辦法
        execute(
            'INSERT INTO finance_categories (name, type, color, icon) VALUES (%s, %s, %s, %s)',
            (name, type_, color, icon)
        )
        rows = query('SELECT LAST_INSERT_ID() AS id')
        return rows[0]['id'] if rows else None

    @staticmethod
    def update(cat_id: int, name: str = None, color: str = None, icon: str = None) -> bool:
        """更新分類（僅更新有傳入的欄位）"""
        fields, params = [], []
        if name  is not None:
            fields.append('name=%s');  params.append(name)
        if color is not None:
            fields.append('color=%s'); params.append(color)
        if icon  is not None:
            fields.append('icon=%s');  params.append(icon)
        if not fields:
            return False
        params.append(cat_id)
        return execute(f'UPDATE finance_categories SET {", ".join(fields)} WHERE id=%s', params) > 0

    @staticmethod
    def delete(cat_id: int) -> bool:
        """刪除分類"""
        return execute('DELETE FROM finance_categories WHERE id=%s', (cat_id,)) > 0


# ─────────────────────────────────────────────
# 收支記錄模型
# ─────────────────────────────────────────────
class Transaction:
    """收支記錄"""

    @staticmethod
    def find(date_from=None, date_to=None, type_=None, category_id=None,
             keyword=None, limit=20, offset=0) -> tuple:
        """
        多條件查詢收支記錄
        回傳 (list[dict], total_count)
        """
        conditions, params = [], []

        if date_from:
            conditions.append('t.date >= %s'); params.append(date_from)
        if date_to:
            conditions.append('t.date <= %s'); params.append(date_to)
        if type_ in ('income', 'expense'):
            conditions.append('t.type = %s'); params.append(type_)
        if category_id:
            conditions.append('t.category_id = %s'); params.append(category_id)
        if keyword:
            conditions.append('(t.description LIKE %s OR t.note LIKE %s)')
            params += [f'%{keyword}%', f'%{keyword}%']

        where = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''

        # 取總筆數
        count_sql = f'SELECT COUNT(*) AS cnt FROM finance_transactions t {where}'
        count_rows = query(count_sql, params)
        total = count_rows[0]['cnt'] if count_rows else 0

        # 取分頁資料
        data_sql = f'''
            SELECT t.*, c.name AS category_name, c.color AS category_color, c.icon AS category_icon
            FROM finance_transactions t
            LEFT JOIN finance_categories c ON t.category_id = c.id
            {where}
            ORDER BY t.date DESC, t.id DESC
            LIMIT %s OFFSET %s
        '''
        rows = query(data_sql, params + [limit, offset])
        return rows, total

    @staticmethod
    def find_by_id(tx_id: int) -> dict:
        rows = query('SELECT * FROM finance_transactions WHERE id=%s', (tx_id,))
        return rows[0] if rows else None

    @staticmethod
    def create(date: str, type_: str, amount: float, category_id=None,
               description: str = '', note: str = '') -> int:
        """新增收支記錄，回傳新增 ID"""
        execute(
            '''INSERT INTO finance_transactions (date, type, amount, category_id, description, note)
               VALUES (%s, %s, %s, %s, %s, %s)''',
            (date, type_, amount, category_id or None, description, note)
        )
        rows = query('SELECT LAST_INSERT_ID() AS id')
        return rows[0]['id'] if rows else None

    @staticmethod
    def update(tx_id: int, **kwargs) -> bool:
        """更新收支記錄"""
        allowed = {'date', 'type', 'amount', 'category_id', 'description', 'note'}
        fields, params = [], []
        for k, v in kwargs.items():
            if k in allowed:
                fields.append(f'{k}=%s')
                params.append(v)
        if not fields:
            return False
        params.append(tx_id)
        return execute(f'UPDATE finance_transactions SET {", ".join(fields)} WHERE id=%s', params) > 0

    @staticmethod
    def delete(tx_id: int) -> bool:
        return execute('DELETE FROM finance_transactions WHERE id=%s', (tx_id,)) > 0

    @staticmethod
    def monthly_summary(year: int, month: int) -> dict:
        """計算指定年月的收入、支出、淨額"""
        sql = '''
            SELECT
                COALESCE(SUM(CASE WHEN type='income'  THEN amount ELSE 0 END), 0) AS income,
                COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END), 0) AS expense
            FROM finance_transactions
            WHERE YEAR(date)=%s AND MONTH(date)=%s
        '''
        rows = query(sql, (year, month))
        if rows:
            income  = float(rows[0]['income'])
            expense = float(rows[0]['expense'])
            return {'income': income, 'expense': expense, 'net': income - expense}
        return {'income': 0, 'expense': 0, 'net': 0}


# ─────────────────────────────────────────────
# 股票交易模型
# ─────────────────────────────────────────────
class Stock:
    """股票交易記錄"""

    @staticmethod
    def find(date_from=None, date_to=None, ticker=None, action=None,
             limit=20, offset=0) -> tuple:
        """多條件查詢股票交易，回傳 (list[dict], total)"""
        conditions, params = [], []

        if date_from:
            conditions.append('date >= %s'); params.append(date_from)
        if date_to:
            conditions.append('date <= %s'); params.append(date_to)
        if ticker:
            conditions.append('ticker = %s'); params.append(ticker.upper())
        if action in ('buy', 'sell', 'dividend'):
            conditions.append('action = %s'); params.append(action)

        where = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''

        total = query(f'SELECT COUNT(*) AS cnt FROM finance_stocks {where}', params)[0]['cnt']
        rows  = query(
            f'SELECT * FROM finance_stocks {where} ORDER BY date DESC, id DESC LIMIT %s OFFSET %s',
            params + [limit, offset]
        )
        return rows, total

    @staticmethod
    def find_by_id(stock_id: int) -> dict:
        rows = query('SELECT * FROM finance_stocks WHERE id=%s', (stock_id,))
        return rows[0] if rows else None

    @staticmethod
    def create(date, ticker, company_name='', market='TW', action='buy',
               shares=0, price=0, amount=0, fee=0, tax=0, note='') -> int:
        """新增股票交易記錄"""
        execute(
            '''INSERT INTO finance_stocks
               (date, ticker, company_name, market, action, shares, price, amount, fee, tax, note)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
            (date, ticker.upper(), company_name, market, action,
             shares, price, amount, fee, tax, note)
        )
        rows = query('SELECT LAST_INSERT_ID() AS id')
        return rows[0]['id'] if rows else None

    @staticmethod
    def update(stock_id: int, **kwargs) -> bool:
        """更新股票交易記錄"""
        allowed = {'date', 'ticker', 'company_name', 'market', 'action',
                   'shares', 'price', 'amount', 'fee', 'tax', 'note'}
        fields, params = [], []
        for k, v in kwargs.items():
            if k in allowed:
                fields.append(f'{k}=%s')
                params.append(v)
        if not fields:
            return False
        params.append(stock_id)
        return execute(f'UPDATE finance_stocks SET {", ".join(fields)} WHERE id=%s', params) > 0

    @staticmethod
    def delete(stock_id: int) -> bool:
        return execute('DELETE FROM finance_stocks WHERE id=%s', (stock_id,)) > 0

    @staticmethod
    def portfolio() -> list:
        """
        計算各 ticker 持倉（買入股數 - 賣出股數 = 持有股數）
        及平均成本（買入總成本 / 總買入股數）
        """
        sql = '''
            SELECT
                ticker,
                MAX(company_name) AS company_name,
                MAX(market) AS market,
                SUM(CASE WHEN action='buy'  THEN shares ELSE 0 END) -
                SUM(CASE WHEN action='sell' THEN shares ELSE 0 END)  AS hold_shares,
                SUM(CASE WHEN action='buy'  THEN shares ELSE 0 END)  AS total_buy_shares,
                SUM(CASE WHEN action='buy'  THEN amount + fee ELSE 0 END) AS total_buy_cost
            FROM finance_stocks
            WHERE action IN ('buy', 'sell')
            GROUP BY ticker
            ORDER BY ticker
        '''
        rows = query(sql)
        result = []
        for r in rows:
            hold    = float(r['hold_shares']       or 0)
            buy_qty = float(r['total_buy_shares']  or 0)
            cost    = float(r['total_buy_cost']    or 0)
            avg_cost = round(cost / buy_qty, 4) if buy_qty > 0 else 0
            result.append({
                'ticker':       r['ticker'],
                'company_name': r['company_name'],
                'market':       r['market'],
                'hold_shares':  hold,
                'avg_cost':     avg_cost,
                'total_cost':   round(hold * avg_cost, 2),
            })
        return result

    @staticmethod
    def pnl() -> list:
        """
        計算各 ticker 已實現損益
        已實現損益 = 賣出總金額 - (賣出股數 × 平均買入成本)
        """
        # 先取各 ticker 平均買入成本
        cost_sql = '''
            SELECT ticker,
                   SUM(CASE WHEN action='buy' THEN amount + fee ELSE 0 END) AS total_cost,
                   SUM(CASE WHEN action='buy' THEN shares ELSE 0 END) AS total_buy_shares
            FROM finance_stocks
            WHERE action IN ('buy', 'sell')
            GROUP BY ticker
        '''
        cost_rows = {r['ticker']: r for r in query(cost_sql)}

        # 取賣出記錄
        sell_sql = '''
            SELECT ticker, SUM(amount) AS sell_amount, SUM(shares) AS sell_shares
            FROM finance_stocks
            WHERE action='sell'
            GROUP BY ticker
        '''
        result = []
        for r in query(sell_sql):
            ticker     = r['ticker']
            sell_amt   = float(r['sell_amount']  or 0)
            sell_qty   = float(r['sell_shares']  or 0)
            cost_info  = cost_rows.get(ticker)
            if cost_info:
                total_cost  = float(cost_info['total_cost']      or 0)
                total_buy   = float(cost_info['total_buy_shares'] or 0)
                avg_cost    = total_cost / total_buy if total_buy > 0 else 0
                cost_basis  = avg_cost * sell_qty
                realized    = sell_amt - cost_basis
                pnl_rate    = (realized / cost_basis * 100) if cost_basis > 0 else 0
            else:
                realized = sell_amt
                pnl_rate = 0
            result.append({
                'ticker':        ticker,
                'sell_amount':   sell_amt,
                'realized_pnl':  round(realized, 2),
                'pnl_rate':      round(pnl_rate, 2),
            })
        return result

    @staticmethod
    def dividend_summary() -> list:
        """各 ticker 累計股利彙總"""
        sql = '''
            SELECT ticker,
                   MAX(company_name) AS company_name,
                   SUM(amount) AS total_dividend,
                   COUNT(*) AS dividend_count
            FROM finance_stocks
            WHERE action='dividend'
            GROUP BY ticker
            ORDER BY total_dividend DESC
        '''
        return query(sql)


# ─────────────────────────────────────────────
# 預算模型
# ─────────────────────────────────────────────
class Budget:
    """每月預算管理"""

    @staticmethod
    def find(year: int, month: int) -> list:
        """查詢指定年月的所有預算"""
        sql = '''
            SELECT b.*, c.name AS category_name, c.color AS category_color, c.icon AS category_icon
            FROM finance_budgets b
            JOIN finance_categories c ON b.category_id = c.id
            WHERE b.year=%s AND b.month=%s
            ORDER BY c.name
        '''
        return query(sql, (year, month))

    @staticmethod
    def find_by_id(budget_id: int) -> dict:
        rows = query('SELECT * FROM finance_budgets WHERE id=%s', (budget_id,))
        return rows[0] if rows else None

    @staticmethod
    def upsert(category_id: int, year: int, month: int, amount: float) -> None:
        """INSERT ... ON DUPLICATE KEY UPDATE（設定或更新預算）"""
        execute(
            '''INSERT INTO finance_budgets (category_id, year, month, amount)
               VALUES (%s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE amount=%s''',
            (category_id, year, month, amount, amount)
        )

    @staticmethod
    def update(budget_id: int, amount: float) -> bool:
        return execute(
            'UPDATE finance_budgets SET amount=%s WHERE id=%s', (amount, budget_id)
        ) > 0

    @staticmethod
    def delete(budget_id: int) -> bool:
        return execute('DELETE FROM finance_budgets WHERE id=%s', (budget_id,)) > 0

    @staticmethod
    def status(year: int, month: int) -> list:
        """
        查詢各分類預算執行狀況
        回傳: category_name, budget_amount, actual_expense, remaining, usage_rate
        """
        sql = '''
            SELECT
                b.id,
                c.name  AS category_name,
                c.color AS category_color,
                c.icon  AS category_icon,
                b.amount AS budget_amount,
                COALESCE(
                    (SELECT SUM(t.amount)
                     FROM finance_transactions t
                     WHERE t.category_id = b.category_id
                       AND t.type = 'expense'
                       AND YEAR(t.date) = b.year
                       AND MONTH(t.date) = b.month),
                    0
                ) AS actual_expense
            FROM finance_budgets b
            JOIN finance_categories c ON b.category_id = c.id
            WHERE b.year=%s AND b.month=%s
            ORDER BY c.name
        '''
        rows = query(sql, (year, month))
        result = []
        for r in rows:
            budget_amt  = float(r['budget_amount']  or 0)
            actual_exp  = float(r['actual_expense'] or 0)
            remaining   = budget_amt - actual_exp
            usage_rate  = round(actual_exp / budget_amt * 100, 1) if budget_amt > 0 else 0
            result.append({
                'id':             r['id'],
                'category_name':  r['category_name'],
                'category_color': r['category_color'],
                'category_icon':  r['category_icon'],
                'budget_amount':  budget_amt,
                'actual_expense': actual_exp,
                'remaining':      remaining,
                'usage_rate':     usage_rate,
            })
        return result


# ─────────────────────────────────────────────
# 報表模型
# ─────────────────────────────────────────────
class Report:
    """報表查詢（月報、年報、分類統計）"""

    @staticmethod
    def monthly(year: int, month: int) -> dict:
        """月報：當月總收入、支出、淨額及各分類明細"""
        summary = Transaction.monthly_summary(year, month)

        # 各分類支出明細
        cat_sql = '''
            SELECT c.name AS category_name, c.color, c.icon,
                   t.type,
                   COALESCE(SUM(t.amount), 0) AS total
            FROM finance_transactions t
            LEFT JOIN finance_categories c ON t.category_id = c.id
            WHERE YEAR(t.date)=%s AND MONTH(t.date)=%s
            GROUP BY t.category_id, t.type
            ORDER BY total DESC
        '''
        details = query(cat_sql, (year, month))

        return {
            'year':    year,
            'month':   month,
            'summary': summary,
            'details': details,
        }

    @staticmethod
    def yearly(year: int) -> list:
        """年報：12個月收支趨勢"""
        sql = '''
            SELECT
                MONTH(date) AS month,
                COALESCE(SUM(CASE WHEN type='income'  THEN amount ELSE 0 END), 0) AS income,
                COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END), 0) AS expense
            FROM finance_transactions
            WHERE YEAR(date)=%s
            GROUP BY MONTH(date)
            ORDER BY MONTH(date)
        '''
        rows = query(sql, (year,))
        # 補齊 1~12 月
        data = {r['month']: r for r in rows}
        result = []
        for m in range(1, 13):
            row = data.get(m, {'month': m, 'income': 0, 'expense': 0})
            result.append({
                'month':   m,
                'income':  float(row['income']),
                'expense': float(row['expense']),
                'net':     float(row['income']) - float(row['expense']),
            })
        return result

    @staticmethod
    def category_stats(date_from: str, date_to: str, type_: str = 'expense') -> list:
        """
        分類統計：指定期間各分類金額及佔比
        type_: 'income' 或 'expense'
        """
        sql = '''
            SELECT c.name AS category_name, c.color, c.icon,
                   COALESCE(SUM(t.amount), 0) AS total
            FROM finance_transactions t
            LEFT JOIN finance_categories c ON t.category_id = c.id
            WHERE t.type=%s AND t.date BETWEEN %s AND %s
            GROUP BY t.category_id
            ORDER BY total DESC
        '''
        rows = query(sql, (type_, date_from, date_to))
        grand_total = sum(float(r['total']) for r in rows)
        result = []
        for r in rows:
            total = float(r['total'])
            result.append({
                'category_name': r['category_name'] or '未分類',
                'color':  r['color'] or '#808080',
                'icon':   r['icon']  or 'bi-tag',
                'total':  total,
                'ratio':  round(total / grand_total * 100, 1) if grand_total > 0 else 0,
            })
        return result

    @staticmethod
    def dashboard(year: int, month: int) -> dict:
        """
        儀表板摘要：
        - 本月收支概況
        - 本月預算整體執行率
        - 股票持倉數量
        - 最近5筆交易
        """
        # 本月收支
        summary = Transaction.monthly_summary(year, month)

        # 本月預算整體執行率
        budget_status = Budget.status(year, month)
        total_budget = sum(b['budget_amount']  for b in budget_status)
        total_actual = sum(b['actual_expense'] for b in budget_status)
        budget_rate  = round(total_actual / total_budget * 100, 1) if total_budget > 0 else 0

        # 持股數量（持有股數 > 0 的 ticker 數）
        portfolio = Stock.portfolio()
        holding_count = sum(1 for p in portfolio if p['hold_shares'] > 0)

        # 最近5筆交易
        recent_rows, _ = Transaction.find(limit=5, offset=0)

        return {
            'summary':       summary,
            'budget_rate':   budget_rate,
            'holding_count': holding_count,
            'recent_transactions': recent_rows,
        }
