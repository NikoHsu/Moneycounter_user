"""
分析器 - 对交易数据进行多维度统计分析
"""

from collections import defaultdict
from datetime import datetime
from src.config_loader import get_config


class Analyzer:
    def __init__(self, transactions: list):
        self.transactions = transactions

    # ---- 过滤 ----

    @property
    def incomes(self) -> list:
        return [tx for tx in self.transactions
                if tx.is_income() and not tx.is_personal_transfer()]

    @property
    def expenses(self) -> list:
        return [tx for tx in self.transactions
                if tx.is_expense() and not tx.is_refund()
                and not tx.is_business_trip()]

    def filter_by_year(self, year: int, txs: list = None) -> list:
        source = txs if txs is not None else self.transactions
        return [tx for tx in source if tx.year == year]

    def filter_by_date(self, start: str, end: str, txs: list = None) -> list:
        """按日期范围筛选 (YYYY-MM-DD)"""
        source = txs if txs is not None else self.transactions
        s = datetime.strptime(start, '%Y-%m-%d')
        e = datetime.strptime(end, '%Y-%m-%d')
        result = []
        for tx in source:
            t = tx._parsed_time
            if t and s <= t <= e:
                result.append(tx)
        return result

    # ---- 收入/支出统计 ----

    def total_income(self, txs: list = None) -> float:
        source = txs if txs is not None else self.transactions
        filtered = [tx for tx in source
                    if tx.is_income() and not tx.is_personal_transfer()
                    and tx.status not in ('退款', '失败')]
        return sum(tx.amount for tx in filtered)

    def total_expense(self, txs: list = None) -> float:
        source = txs if txs is not None else self.transactions
        filtered = [tx for tx in source
                    if tx.is_expense() and not tx.is_refund()
                    and tx.status not in ('退款', '失败')]
        return sum(tx.amount for tx in filtered)

    def net_income(self, txs: list = None) -> float:
        return self.total_income(txs) - self.total_expense(txs)

    # ---- 收入结构分析 ----

    def income_source_summary(self, txs: list = None):
        """收入来源汇总（只统计真实收入）"""
        import pandas as pd
        raw = txs if txs is not None else self.transactions
        source = [tx for tx in raw
                  if tx.is_income() and not tx.is_personal_transfer()
                  and tx.status not in ('退款', '失败')]
        source_totals = defaultdict(float)
        total = 0.0
        for tx in source:
            s = tx.counterparty or '未知'
            source_totals[s] += tx.amount
            total += tx.amount
        rows = []
        for s in sorted(source_totals, key=lambda x: source_totals[x], reverse=True):
            rows.append({
                'source': s,
                'amount': round(source_totals[s], 2),
                'percentage': round(source_totals[s] / total * 100, 1) if total > 0 else 0,
            })
        return pd.DataFrame(rows)

    def income_type_summary(self, txs: list = None):
        """收入类型汇总（只统计真实收入）"""
        import pandas as pd
        raw = txs if txs is not None else self.transactions
        source = [tx for tx in raw
                  if tx.is_income() and not tx.is_personal_transfer()
                  and tx.status not in ('退款', '失败')]
        type_totals = defaultdict(float)
        total = 0.0
        for tx in source:
            t = tx.transaction_type or '未知'
            type_totals[t] += tx.amount
            total += tx.amount
        rows = []
        for t in sorted(type_totals, key=lambda x: type_totals[x], reverse=True):
            rows.append({
                'type': t,
                'amount': round(type_totals[t], 2),
                'percentage': round(type_totals[t] / total * 100, 1) if total > 0 else 0,
            })
        return pd.DataFrame(rows)

    # ---- 支出结构分析 ----

    def expense_category_summary(self, txs: list = None):
        """按分类汇总支出（只统计真实支出，排除退款/失败/不计收支）"""
        import pandas as pd
        source = txs if txs is not None else self.transactions
        source = [tx for tx in source
                  if tx.is_expense() and not tx.is_refund()
                  and not tx.is_business_trip()
                  and tx.status not in ('退款', '失败')]
        cat_totals = defaultdict(float)
        total = 0.0
        for tx in source:
            cat = tx.classify_by_keywords()
            cat_totals[cat] += tx.amount
            total += tx.amount
        rows = []
        for cat in sorted(cat_totals, key=lambda c: cat_totals[c], reverse=True):
            rows.append({
                'category': cat,
                'amount': round(cat_totals[cat], 2),
                'percentage': round(cat_totals[cat] / total * 100, 1) if total > 0 else 0,
            })
        return pd.DataFrame(rows)

    # ---- 时间序列（3线并行） ----

    def time_series_monthly(self, txs: list = None):
        """月度时间序列：收入、支出、净利润三条线"""
        import pandas as pd
        source = txs if txs is not None else self.transactions
        monthly = defaultdict(lambda: {'income': 0.0, 'expense': 0.0})
        for tx in source:
            key = tx.year_month
            if tx.status in ('退款', '失败'):
                continue
            if tx.is_income() and not tx.is_personal_transfer():
                monthly[key]['income'] += tx.amount
            elif tx.is_expense() and not tx.is_refund():
                monthly[key]['expense'] += tx.amount
        rows = []
        for ym in sorted(monthly.keys()):
            inc = round(monthly[ym]['income'], 2)
            exp = round(monthly[ym]['expense'], 2)
            rows.append({
                'month': ym,
                '收入': inc,
                '支出': exp,
                '净利润': round(inc - exp, 2),
            })
        return pd.DataFrame(rows)

    def time_series_yearly(self, txs: list = None):
        """年度时间序列"""
        import pandas as pd
        source = txs if txs is not None else self.transactions
        yearly = defaultdict(lambda: {'income': 0.0, 'expense': 0.0})
        for tx in source:
            key = str(tx.year)
            if tx.status in ('退款', '失败'):
                continue
            if tx.is_income() and not tx.is_personal_transfer():
                yearly[key]['income'] += tx.amount
            elif tx.is_expense() and not tx.is_refund():
                yearly[key]['expense'] += tx.amount
        rows = []
        for y in sorted(yearly.keys()):
            inc = round(yearly[y]['income'], 2)
            exp = round(yearly[y]['expense'], 2)
            rows.append({
                'year': y,
                '收入': inc,
                '支出': exp,
                '净利润': round(inc - exp, 2),
            })
        return pd.DataFrame(rows)

    # ---- 差旅池分析 ----

    def travel_fund_summary(self, txs: list = None):
        """
        差旅池汇总
        - 差旅收入 = business_trip=true 且来源于银行（报销/补贴入账）
        - 差旅支出 = business_trip=true 且来源于微信/支付宝（酒店消费）
        - 差额 = 差旅收入 - 差旅支出
        """
        source = txs if txs is not None else self.transactions
        biz_txs = [tx for tx in source if tx.business_trip]

        # 排除公积金记录
        def _is_fund(tx):
            cp = (tx.counterparty or '') + (tx.product_desc or '')
            return '公积金' in cp or '住房公积金' in cp

        biz_income = sum(tx.amount for tx in biz_txs
                         if tx.source in ('交通银行', '中国银行') and not _is_fund(tx)
                         and tx.status != '退款')
        biz_expense = sum(tx.amount for tx in biz_txs
                          if tx.source in ('微信', '支付宝')
                          and tx.status not in ('退款', '失败'))
        balance = round(biz_income - biz_expense, 2)

        return {
            'biz_income': round(biz_income, 2),
            'biz_expense': round(biz_expense, 2),
            'balance': balance,
        }

    def travel_fund_monthly(self, txs: list = None):
        """差旅池月度时间序列"""
        import pandas as pd
        from collections import defaultdict
        source = txs if txs is not None else self.transactions
        biz_txs = [tx for tx in source if tx.business_trip]

        def _is_fund(tx):
            cp = (tx.counterparty or '') + (tx.product_desc or '')
            return '公积金' in cp or '住房公积金' in cp

        monthly = defaultdict(lambda: {'income': 0.0, 'expense': 0.0})
        for tx in biz_txs:
            key = tx.year_month
            if tx.source in ('交通银行', '中国银行') and not _is_fund(tx) and tx.status != '退款':
                monthly[key]['income'] += tx.amount
            elif tx.source in ('微信', '支付宝') and tx.status not in ('退款', '失败'):
                monthly[key]['expense'] += tx.amount

        rows = []
        cum_balance = 0.0
        for ym in sorted(monthly.keys()):
            inc = round(monthly[ym]['income'], 2)
            exp = round(monthly[ym]['expense'], 2)
            net = round(inc - exp, 2)
            cum_balance += net
            rows.append({
                'month': ym,
                '报销收入': inc,
                '酒店支出': exp,
                '月净额': net,
                '累计余额': round(cum_balance, 2),
            })
        return pd.DataFrame(rows)

    # ---- 公积金池分析 ----

    def housing_fund_summary(self, txs: list = None):
        """公积金池汇总（月缴+提取自动抓取）"""
        source = txs if txs is not None else self.transactions
        # 月缴记录（手动补充，source=公积金）
        fund_txs = [tx for tx in source if tx.source == '公积金']
        fund_income = sum(tx.amount for tx in fund_txs)

        # 提取记录（银行数据，对方含住房公积金）
        xtract_txs = [tx for tx in source
                      if '住房公积金' in (tx.counterparty or '')
                      and tx.source != '公积金']
        xtract_total = sum(tx.amount for tx in xtract_txs)
        xtract_count = len(xtract_txs)

        balance = round(fund_income - xtract_total, 2)
        return {
            'fund_income': round(fund_income, 2),
            'xtract_total': round(xtract_total, 2),
            'xtract_count': xtract_count,
            'balance': balance,
        }

    def housing_fund_monthly(self, txs: list = None):
        """公积金池月度时间序列（只显示月缴）"""
        import pandas as pd
        from collections import defaultdict
        source = txs if txs is not None else self.transactions
        fund_txs = [tx for tx in source if tx.source == '公积金']

        monthly = defaultdict(float)
        for tx in fund_txs:
            key = tx.year_month
            monthly[key] += tx.amount

        rows = []
        cum = 0.0
        for ym in sorted(monthly.keys()):
            cum += monthly[ym]
            rows.append({
                'month': ym,
                '月缴': round(monthly[ym], 2),
                '累计': round(cum, 2),
            })
        return pd.DataFrame(rows)

    # ---- 净利润分析 ----

    def profit_analysis(self, txs: list = None):
        """净利润分析：总收入、总支出、净利润、利润率"""
        source = txs if txs is not None else self.transactions
        inc = self.total_income(source)
        exp = self.total_expense(source)
        net = inc - exp
        margin = round(net / inc * 100, 1) if inc > 0 else 0
        return {
            'total_income': round(inc, 2),
            'total_expense': round(exp, 2),
            'net_profit': round(net, 2),
            'profit_margin': margin,
        }

    # ---- 财务自由度 ----

    @staticmethod
    def financial_freedom(net_assets: float, target: float = 3000000):
        """计算财务自由度"""
        ratio = net_assets / target * 100
        return {
            'net_assets': round(net_assets, 2),
            'target': target,
            'ratio': round(ratio, 2),
            'milestone_25': ratio >= 25,
            'milestone_50': ratio >= 50,
            'milestone_100': ratio >= 100,
        }

    # ---- 兼容旧接口 ----

    def category_summary(self, year: int = None):
        """兼容旧接口：按年汇总支出"""
        txs = self.expenses
        if year:
            txs = self.filter_by_year(year, txs)
        return self.expense_category_summary(txs)

    def monthly_summary(self, year: int = None):
        """兼容旧接口：按月汇总"""
        txs = self.transactions
        if year:
            txs = self.filter_by_year(year)
        return self.time_series_monthly(txs)

    def summary_report(self, year: int = None) -> str:
        lines = []
        lines.append("=" * 50)
        lines.append(f"交易分析报告{' (' + str(year) + '年)' if year else ''}")
        lines.append("=" * 50)
        txs = self.transactions
        if year:
            txs = self.filter_by_year(year)
        p = self.profit_analysis(txs)
        lines.append(f"\n总收入:     {p['total_income']:,.2f} 元")
        lines.append(f"总支出:     {p['total_expense']:,.2f} 元")
        lines.append(f"净利润:     {p['net_profit']:,.2f} 元")
        lines.append(f"利润率:     {p['profit_margin']}%")

        lines.append(f"\n分类支出 TOP5:")
        cat_df = self.expense_category_summary(txs)
        for _, row in cat_df.head(5).iterrows():
            lines.append(f"  {row['category']}: {row['amount']:,.2f} 元 ({row['percentage']}%)")

        lines.append("\n" + "=" * 50)
        return "\n".join(lines)
