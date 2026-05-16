"""
手动补充数据加载器
- data/manual/recurring_expenses.json → 周期性支出（如房租），展开为逐月支出
- data/manual/housing_fund.json → 公积金月缴，展开为逐月不计收支记录
"""

import json
import os
from collections import OrderedDict

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'manual')


def _expand_monthly(item, prefix, ie_type, source):
    """将周期性条目按逐月展开"""
    records = []
    start_ym = item['start']
    end_ym = item['end']
    amount = item['amount_per_month']

    start_year, start_month = int(start_ym[:4]), int(start_ym[5:7])
    end_year, end_month = int(end_ym[:4]), int(end_ym[5:7])

    y, m = start_year, start_month
    while (y < end_year) or (y == end_year and m <= end_month):
        tx_time = f'{y:04d}-{m:02d}-01 00:00'
        records.append(OrderedDict([
            ('transaction_time', tx_time),
            ('transaction_type', item.get('transaction_type', '房屋居住')),
            ('counterparty', item.get('counterparty', '')),
            ('product_desc', item.get('product_desc', '')),
            ('income_expense_type', ie_type),
            ('amount', amount),
            ('payment_method', item.get('payment_method', '银行转账')),
            ('transaction_status', '成功'),
            ('transaction_id', f'{prefix}_{y}{m:02d}'),
            ('source_system', source),
            ('business_trip', False),
        ]))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return records


def load_recurring_expenses(filepath=None):
    """加载周期性支出（房租等），返回逐月支出记录 list[OrderedDict]"""
    if filepath is None:
        filepath = os.path.join(DATA_DIR, 'recurring_expenses.json')
    if not os.path.exists(filepath):
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    records = []
    for item in data.get('expenses', []):
        records.extend(_expand_monthly(item, 'rent', '支出', '手动补充'))
    return records


def load_housing_fund(filepath=None):
    """
    加载公积金月缴数据，返回逐月记录 list[OrderedDict]
    月缴标记为不计收支（独立跟踪，不算日常收入/支出）
    """
    if filepath is None:
        filepath = os.path.join(DATA_DIR, 'housing_fund.json')
    if not os.path.exists(filepath):
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    records = []
    for item in data.get('monthly_contributions', []):
        records.extend(_expand_monthly(item, 'fund', '不计收支', '公积金'))
    return records
