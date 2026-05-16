#!/usr/bin/env python3
"""
MoneyCounter - 个人账单合并与标准化工具
读取微信和支付宝账单，合并为统一格式的 use_data.json

规则配置从 config/rules.yaml 读取，修改规则无需改动代码。
"""

import csv
import json
import os
import sys
from datetime import datetime
from collections import OrderedDict

# 将项目根目录加入 path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from src.config_loader import get_config

# ============ 加载配置 ============
CONFIG = get_config()
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')
OUTPUT_FILE = os.path.join(DATA_DIR, 'app_data.json')

# 从 YAML 中提取各配置项
ALIPAY_TYPE_MAP = CONFIG.get('alipay_type_map', {})
WECHAT_TYPE_DIRECT = CONFIG.get('wechat_type_direct', {})
WECHAT_STATUS_MAP = CONFIG.get('wechat_status_map', {})
ALIPAY_STATUS_MAP = CONFIG.get('alipay_status_map', {})
WECHAT_IE_MAP = CONFIG.get('income_expense_maps', {}).get('wechat', {})
ALIPAY_IE_MAP = CONFIG.get('income_expense_maps', {}).get('alipay', {})
DISCOUNT_KEYWORDS = CONFIG.get('payment_discount_keywords', [])
CATEGORY_KEYWORDS = CONFIG.get('transaction_types', {})
PERSONAL_TRANSFER_IGNORE = CONFIG.get('personal_transfer_ignore', [])
BUSINESS_TRIP_HOTELS = CONFIG.get('business_trip_hotels', [])
RENT_COLLECTION = CONFIG.get('rent_collection', {})
DEPOSIT_KEYWORDS = CONFIG.get('deposit_keywords', [])


def clean_payment_method(raw):
    """清洗支付方式，剔除&红包、&优惠、&立减金等干扰词"""
    if not raw or raw.strip() == '':
        return '未知'
    parts = raw.split('&')
    clean_parts = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        is_discount = any(kw in part for kw in DISCOUNT_KEYWORDS)
        if not is_discount:
            clean_parts.append(part)
    if not clean_parts:
        return '未知'
    return '&'.join(clean_parts)


def classify_by_keywords(counterparty, product_desc):
    """根据交易对方和商品说明的关键词分类到10大类"""
    text = f"{counterparty} {product_desc}"

    # 分类匹配顺序（优先匹配前面的分类）
    category_order = ['餐饮', '交通', '购物', '生活缴费', '娱乐',
                      '医疗健康', '房屋居住', '金融理财', '转账/红包']

    for category in category_order:
        keywords = CATEGORY_KEYWORDS.get(category, [])
        for kw in keywords:
            if kw and isinstance(kw, str) and kw.lower() in text.lower():
                return category

    return '其他'


def normalize_time(time_val):
    """统一时间格式为 YYYY-MM-DD HH:MM"""
    if isinstance(time_val, datetime):
        return time_val.strftime('%Y-%m-%d %H:%M')
    if isinstance(time_val, str):
        time_val = time_val.strip()
        for fmt in ['%Y/%m/%d %H:%M', '%Y-%m-%d %H:%M',
                     '%Y/%m/%d %H:%M:%S', '%Y-%m-%d %H:%M:%S']:
            try:
                return datetime.strptime(time_val, fmt).strftime('%Y-%m-%d %H:%M')
            except ValueError:
                continue
    return str(time_val)


def parse_wechat_file(filepath):
    """解析微信Excel文件"""
    import openpyxl
    wb = openpyxl.load_workbook(filepath)
    ws = wb.active

    records = []
    in_data = False

    for row in ws.iter_rows(values_only=True):
        if row[0] == '交易时间':
            in_data = True
            continue
        if not in_data or row[0] is None:
            continue

        trans_time = row[0]
        trans_type_raw = str(row[1] or '')
        counterparty = str(row[2] or '')
        product_desc = str(row[3] or '')
        ie_raw = str(row[4] or '/')
        amount_raw = row[5]
        pay_method_raw = str(row[6] or '')
        status_raw = str(row[7] or '')
        trans_id = str(row[8] or '').strip()

        transaction_time = normalize_time(trans_time)
        income_expense_type = WECHAT_IE_MAP.get(ie_raw, '不计收支')
        try:
            amount = round(float(amount_raw), 2)
        except (ValueError, TypeError):
            amount = 0.0
        payment_method = clean_payment_method(pay_method_raw)
        transaction_status = WECHAT_STATUS_MAP.get(status_raw, '失败')

        # 是否退款
        is_refund_type = '退款' in trans_type_raw
        is_full_refund = status_raw == '已全额退款'

        # 交易类型映射
        if trans_type_raw in WECHAT_TYPE_DIRECT:
            transaction_type = WECHAT_TYPE_DIRECT[trans_type_raw]
            if transaction_type == '其他' and not is_refund_type:
                tt = classify_by_keywords(counterparty, product_desc)
                if tt != '其他':
                    transaction_type = tt
        elif is_refund_type:
            transaction_type = classify_by_keywords(counterparty, product_desc)
        else:
            transaction_type = classify_by_keywords(counterparty, product_desc)

        # 退款记录特殊处理
        if is_refund_type:
            income_expense_type = '不计收支'
        elif is_full_refund:
            income_expense_type = '不计收支'
            transaction_status = '退款'

        records.append(OrderedDict([
            ('transaction_time', transaction_time),
            ('transaction_type', transaction_type),
            ('counterparty', counterparty),
            ('product_desc', product_desc),
            ('income_expense_type', income_expense_type),
            ('amount', amount),
            ('payment_method', payment_method),
            ('transaction_status', transaction_status),
            ('transaction_id', trans_id),
            ('source_system', '微信'),
        ]))

    return records


def parse_alipay_file(filepath):
    """解析支付宝CSV文件"""
    records = []

    with open(filepath, 'r', encoding='gbk') as f:
        reader = csv.reader(f)
        in_data = False

        for row in reader:
            if len(row) >= 10 and row[0] == '交易时间':
                in_data = True
                continue
            if not in_data or len(row) < 10:
                continue

            trans_time = row[0].strip()
            trans_type_raw = row[1].strip()
            counterparty = row[2].strip()
            product_desc = row[4].strip()
            ie_raw = row[5].strip()
            amount_raw = row[6].strip()
            pay_method_raw = row[7].strip()
            status_raw = row[8].strip()
            trans_id = row[9].strip()

            transaction_time = normalize_time(trans_time)
            income_expense_type = ALIPAY_IE_MAP.get(ie_raw, '不计收支')
            try:
                amount = round(float(amount_raw), 2)
            except (ValueError, TypeError):
                amount = 0.0
            payment_method = clean_payment_method(pay_method_raw)
            transaction_status = ALIPAY_STATUS_MAP.get(status_raw, '失败')

            is_refund = (trans_type_raw == '退款')

            # 交易类型映射
            if trans_type_raw in ALIPAY_TYPE_MAP:
                transaction_type = ALIPAY_TYPE_MAP[trans_type_raw]
            else:
                transaction_type = classify_by_keywords(counterparty, product_desc)

            # 如果映射结果为'其他'，尝试关键词匹配兜底
            if transaction_type == '其他':
                tt = classify_by_keywords(counterparty, product_desc)
                if tt != '其他':
                    transaction_type = tt

            if is_refund:
                income_expense_type = '不计收支'
                transaction_status = '退款'

            records.append(OrderedDict([
                ('transaction_time', transaction_time),
                ('transaction_type', transaction_type),
                ('counterparty', counterparty),
                ('product_desc', product_desc),
                ('income_expense_type', income_expense_type),
                ('amount', amount),
                ('payment_method', payment_method),
                ('transaction_status', transaction_status),
                ('transaction_id', trans_id),
                ('source_system', '支付宝'),
            ]))

    return records


def normalize_refunds(records):
    """退款归一化：将退款相关的双方记录都标记为不计收支"""
    # 第1步：所有状态为退款的记录 → 不计收支
    for r in records:
        if r['transaction_status'] == '退款':
            r['income_expense_type'] = '不计收支'

    # 第2步：支付宝通过交易单号匹配被退款的原始交易
    id_index = {}
    for i, r in enumerate(records):
        tid = r['transaction_id']
        if tid:
            id_index[tid] = i

    refund_matched = set()
    for i, r in enumerate(records):
        if r['source_system'] != '支付宝':
            continue
        if r['transaction_status'] != '退款':
            continue

        tid = r['transaction_id']
        if not tid:
            continue

        original_id = None
        for sep in ['*', '_']:
            if sep in tid:
                candidate = tid.split(sep)[0]
                if candidate in id_index:
                    original_id = candidate
                    break

        if original_id:
            orig_idx = id_index[original_id]
            if orig_idx not in refund_matched:
                orig = records[orig_idx]
                if orig['income_expense_type'] == '支出':
                    orig['income_expense_type'] = '不计收支'
                refund_matched.add(orig_idx)

        # 金额+交易对方匹配兜底
        if original_id is None and r['amount'] > 0:
            amount = r['amount']
            cp = r['counterparty']
            for j, orig in enumerate(records):
                if j in refund_matched or j == i:
                    continue
                if orig['source_system'] != '支付宝':
                    continue
                if orig['transaction_status'] == '退款':
                    continue
                if orig['income_expense_type'] != '支出':
                    continue
                if abs(orig['amount'] - amount) < 0.01:
                    if cp and orig['counterparty'] and (
                        cp[:3] in orig['counterparty'] or orig['counterparty'][:3] in cp
                    ):
                        orig['income_expense_type'] = '不计收支'
                        refund_matched.add(j)
                        break

    return records


def normalize_special_transactions(records):
    """对特殊交易进行归一化（规则来自 config/rules.yaml）"""
    for r in records:
        cp = r['counterparty'] or ''
        pd = r['product_desc'] or ''
        amt = abs(r['amount'])

        # 个人转账不计收入（规则来自 config/rules.yaml personal_transfer_ignore）
        for name in PERSONAL_TRANSFER_IGNORE:
            if name in cp or name in pd:
                if r['income_expense_type'] in ('收入', '支出'):
                    r['income_expense_type'] = '不计收支'
                break

        # 房租代缴：仅金额 >= threshold 才不计收支
        rent_kws = RENT_COLLECTION.get('keywords', [])
        rent_threshold = RENT_COLLECTION.get('amount_threshold', 2000)
        is_rent = any(kw in cp or kw in pd for kw in rent_kws)
        if is_rent and amt >= rent_threshold:
            if r['income_expense_type'] in ('收入', '支出'):
                r['income_expense_type'] = '不计收支'

        # 押金/保证金不计支出（后续可退）
        if r['income_expense_type'] == '支出':
            for kw in DEPOSIT_KEYWORDS:
                if kw in pd:
                    r['income_expense_type'] = '不计收支'
                    break

        # 出差酒店标记 + 酒店支出不计收支
        is_biz = False
        for hotel in BUSINESS_TRIP_HOTELS:
            if hotel in cp or hotel in pd:
                is_biz = True
                break
        if is_biz and r['income_expense_type'] == '支出':
            r['income_expense_type'] = '不计收支'
        r['business_trip'] = is_biz

    return records


def deduplicate(records):
    """根据transaction_id去重"""
    seen = set()
    unique = []
    for r in records:
        tid = r['transaction_id']
        if tid and tid not in seen:
            seen.add(tid)
            unique.append(r)
        elif not tid:
            unique.append(r)
    return unique


def find_data_file(directory, keyword, extensions):
    """在指定目录下按关键词和扩展名查找文件"""
    if not os.path.exists(directory):
        return None
    for f in os.listdir(directory):
        if keyword in f and any(f.endswith(ext) for ext in extensions):
            return os.path.join(directory, f)
    return None


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    # 优先在 data/raw/ 下查找，其次在项目根目录
    raw_dir = os.path.join(SCRIPT_DIR, 'data', 'raw')

    wechat_file = find_data_file(raw_dir, '微信', ['.xlsx', '.xls'])
    if not wechat_file:
        wechat_file = find_data_file(SCRIPT_DIR, '微信', ['.xlsx', '.xls'])

    alipay_file = find_data_file(raw_dir, '支付宝', ['.csv'])
    if not alipay_file:
        alipay_file = find_data_file(SCRIPT_DIR, '支付宝', ['.csv'])

    if not wechat_file:
        print('[ERROR] 未找到微信账单（请放入 data/raw/ 目录）')
        return
    if not alipay_file:
        print('[ERROR] 未找到支付宝账单（请放入 data/raw/ 目录）')
        return

    wx = parse_wechat_file(wechat_file)
    ali = parse_alipay_file(alipay_file)
    all_ = deduplicate(wx + ali)

    all_ = normalize_refunds(all_)
    all_ = normalize_special_transactions(all_)

    # 转账/红包类型的所有对方名统一为市场
    for r in all_:
        if r['transaction_type'] == '转账/红包':
            r['counterparty'] = '市场'

    def stat(lst, key):
        d = {}
        for r in lst:
            v = r[key]
            d[v] = d.get(v, 0) + 1
        return d

    print(f'微信: {len(wx)}  支付宝: {len(ali)}  合并去重: {len(all_)}')
    print()
    print('── 交易类型分布 ──')
    for k, v in sorted(stat(all_, 'transaction_type').items(), key=lambda x: -x[1]):
        print(f'  {k:10s}  {v:>4d}')
    print()
    print('── 收支分布 ──')
    for k, v in sorted(stat(all_, 'income_expense_type').items(), key=lambda x: -x[1]):
        print(f'  {k:8s}  {v:>4d}')
    print()
    print('── 状态分布 ──')
    for k, v in sorted(stat(all_, 'transaction_status').items(), key=lambda x: -x[1]):
        print(f'  {k:8s}  {v:>4d}')
    print()
    print('── 来源分布 ──')
    for k, v in sorted(stat(all_, 'source_system').items(), key=lambda x: -x[1]):
        print(f'  {k:8s}  {v:>4d}')

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_, f, ensure_ascii=False, indent=2)

    print(f'\nOK! 输出: {OUTPUT_FILE}')
    print(f'大小: {os.path.getsize(OUTPUT_FILE) / 1024:.1f} KB')


if __name__ == '__main__':
    main()
