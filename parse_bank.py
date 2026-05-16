#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_bank.py - 解析银行卡PDF流水，生成 bank_data.json

支持中国银行和交通银行的PDF格式。
规则配置从 config/rules.yaml 读取。
"""

import json
import os
import re
import sys
from collections import OrderedDict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from src.config_loader import get_config

CONFIG = get_config()
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')
RAW_DIR = os.path.join(SCRIPT_DIR, 'data', 'raw')
OUTPUT_FILE = os.path.join(DATA_DIR, 'bank_data.json')

# 从YAML读取银行配置
bank_configs_raw = CONFIG.get('data_sources', {}).get('files', {}).get('bank_configs', [])
BANK_CONFIGS = {}
for cfg in bank_configs_raw:
    name = cfg['bank_name']
    BANK_CONFIGS[name] = cfg

# 从YAML读取规则
bank_rules = CONFIG.get('bank_rules', {})

# 公积金提取关键词（匹配到的记录设为不计收支，走公积金池独立核算）
HOUSING_FUND_KEYWORDS = ['住房公积金', '公积金']

# 对方名显示别名映射（仅对中国银行生效）
# 请按需修改
BOC_COUNTERPARTY_ALIAS = {}
IGNORE_NAMES = bank_rules.get('ignore_names', [])
SKIP_TYPES = bank_rules.get('skip_types', [])
SKIP_MEMO = bank_rules.get('skip_memo', [])
HEADER_KEYWORDS = bank_rules.get('header_keywords', [])


def is_header(line):
    return any(k in line for k in HEADER_KEYWORDS)


def clean_name(text):
    """清洗对方户名：去除账号数字和多余空格"""
    text = re.sub(r'\d{6,}(\*+\d+)?', '', text)
    text = re.sub(r'\s+', '', text)
    return text.strip()


def extract_counterparty_from_memo(memo):
    """
    从中国银行的附言/摘要字段中提取有意义的对方名。
    
    原始内容如：
      "某公司名2012******0043中国工商银行..."
      "奖金某公司名4780******8132中国银行..."
      "908270010无锡市住房公积金管理中心4767******4903中国银行无锡..."
      "豆包新春现金红包豆包6171******0068"
      "6301571天津持辉网络科技有限公司8110******0847中信银行"
    """
    if not memo:
        return ''
    
    text = memo
    
    # 去掉前缀的交易类型名（已在 transaction_type 中）
    known_prefixes = ['工资', '奖金', '报销']
    for prefix in known_prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    
    # 清理开头的纯数字前缀（如 "908270010"）
    text = re.sub(r'^\d+', '', text)
    
    # 找到第一个 数字(6位+) 或 数字(4位+)****数字(4位+) 的位置截断
    m = re.search(r'\d{4,}\*{2,}\d{4,}|\d{6,}', text)
    if m:
        text = text[:m.start()]
    
    return text.strip()


def clean_product_desc(raw_desc):
    """
    清洗商品说明，去除银行账号、银行名称、页码等无效信息。
    """
    if not raw_desc:
        return ''
    
    text = raw_desc
    
    # 1. 去掉前缀的交易类型名（已在 transaction_type 中）
    known_prefixes = ['工资', '奖金', '报销']
    for prefix in known_prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    
    # 2. 去掉页码信息
    text = re.sub(r'第\d+ 页/共\d+ 页.*$', '', text)
    text = re.sub(r'行数:\d+.*$', '', text)
    
    # 3. 去掉银行账号模式：数字+****+数字 或 纯数字(6位以上)
    text = re.sub(r'\d{4,}\*{2,}\d{4,}', '', text)
    text = re.sub(r'\d{6,}', '', text)
    
    # 4. 去掉常见银行名称关键词
    bank_keywords = [
        '中国工商银行', '中国建设银行', '中国银行', '中国农业银行',
        '交通银行', '招商银行', '中信银行', '兴业银行', '浦发银行',
        '中国邮政储蓄银行', '中国光大银行', '华夏银行', '广发银行',
        '平安银行', '民生银行', '上海银行', '北京银行',
        '支行', '分行', '营业部', '分理处', '储蓄所',
        '股份有限公司', '有限责任公司',
    ]
    for kw in bank_keywords:
        text = text.replace(kw, '')
    
    # 5. 去掉常见银行城市名后缀（匹配末尾的城市+银行字样）
    city_bank_pattern = r'(?:北京|上海|广州|深圳|无锡|苏州|南京|杭州|成都|武汉|天津|重庆|西安|长沙|郑州|东莞|青岛|沈阳|宁波|昆明|大连|厦门|合肥|佛山|福州|哈尔滨|济南|温州|长春|石家庄|常州|泉州|南宁|贵阳|南昌|太原|烟台|嘉兴|南通|金华|珠海|惠州|徐州|海口|乌鲁木齐|绍兴|中山|台州|兰州|保定|潍坊|呼和浩特|镇江|扬州|桂林|唐山|三亚|湖州|廊坊|洛阳|盐城|临沂|江阴|宜兴|张家港|常熟|太仓|昆山|吴江|启东|如皋|海门|扬中|丹阳|句容|靖江|泰兴|兴化|东台|大丰|阜宁|建湖|射阳)(?:市)?(?:支行|分行|营业部|分理处|储蓄所|新区|开发区|高新区|园区|国家文化与金融合|文化与金融)?'
    text = re.sub(city_bank_pattern, '', text)
    
    # 6. 去掉多余的****
    text = re.sub(r'\*+\s*\*+', '', text)
    
    # 7. 清理多余空格
    text = re.sub(r'\s+', '', text)
    
    return text.strip()


def clean_bocomm_product_desc(raw_desc):
    """
    清洗交通银行product_desc中的 * * * * 分隔符和无效信息。
    """
    if not raw_desc:
        return ''
    
    text = raw_desc
    
    # 去掉 * * * * * 分隔线（单独的星号序列）
    text = re.sub(r'(\*\s*){3,}', '', text)
    
    # 去掉 "打印完毕" 后的统计信息
    text = re.sub(r'打印完毕.*$', '', text)
    text = re.sub(r'借方发生额汇总.*$', '', text)
    text = re.sub(r'贷方发生额汇总.*$', '', text)
    text = re.sub(r'[\d,]+\.\d{2}', '', text)
    
    # 清理
    text = re.sub(r'\s+', '', text)
    
    return text.strip()


def parse_boc_pdf(filepath, password, payment_method, source_system):
    """解析中国银行PDF流水"""
    import fitz

    doc = fitz.open(filepath)
    if doc.needs_pass and password:
        doc.authenticate(password)

    lines = []
    for page in doc:
        for line in page.get_text().split('\n'):
            line = line.strip()
            if line and not is_header(line):
                lines.append(line)
    doc.close()

    records = []
    i = 0
    while i < len(lines):
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', lines[i]):
            i += 1
            continue

        date_str = lines[i]
        i += 1
        if i >= len(lines) or not re.match(r'^\d{2}:\d{2}:\d{2}$', lines[i]):
            continue
        time_str = lines[i][:5]
        i += 1
        if i >= len(lines) or lines[i] != '人民币':
            continue
        i += 1
        if i >= len(lines):
            break
        try:
            amount = round(float(lines[i].replace(',', '')), 2)
        except ValueError:
            continue
        i += 1  # 余额

        # 交易名称
        i += 1
        name_parts = []
        while i < len(lines):
            l = lines[i]
            if re.match(r'^\d{4}-\d{2}-\d{2}$', l):
                break
            if l in ('柜台', '网上银行', '手机银行', '银企对接',
                     '卡组织线上/无', '卡交易', '其他'):
                if l == '卡组织线上/无' and i + 1 < len(lines) and lines[i + 1] == '卡交易':
                    i += 1
                i += 1
                break
            if '----' in l or '---' in l:
                i += 1
                break
            name_parts.append(l)
            i += 1
        trans_name = ''.join(name_parts).replace('--', '').strip()

        # 跳过网点
        while i < len(lines):
            l = lines[i]
            if re.match(r'^\d{4}-\d{2}-\d{2}$', l):
                break
            if '----' in l or '---' in l:
                i += 1
                break
            i += 1

        # 附言/摘要
        memo_parts = []
        while i < len(lines):
            l = lines[i]
            if re.match(r'^\d{4}-\d{2}-\d{2}$', l):
                break
            if '----' in l or '---' in l:
                i += 1
                break
            memo_parts.append(l)
            i += 1
        memo_raw = ''.join(memo_parts).replace('--', '').strip()

        # 对方账户名
        cp_parts = []
        while i < len(lines):
            l = lines[i]
            if re.match(r'^\d{4}-\d{2}-\d{2}$', l):
                break
            if '----' in l or '---' in l:
                i += 1
                break
            cp_parts.append(l)
            i += 1
        counterparty_raw = ''.join(cp_parts).replace('--', '').strip()
        counterparty_clean = clean_name(counterparty_raw)

        # 跳过剩余到下一日期
        while i < len(lines):
            if re.match(r'^\d{4}-\d{2}-\d{2}$', lines[i]):
                break
            i += 1

        # ---- 字段提取与清洗 ----

        # 如果 counterparty 为空，从 memo 中提取
        if not counterparty_clean and memo_raw:
            counterparty_clean = extract_counterparty_from_memo(memo_raw)

        # 清洗 product_desc
        desc_clean = clean_product_desc(memo_raw)
        # 如果清洗后为空但原始有内容，提取简短的摘要
        if not desc_clean and memo_raw:
            desc_clean = extract_counterparty_from_memo(memo_raw)

        # 过滤
        skip = False
        check_text = counterparty_raw + ' ' + memo_raw
        for name in IGNORE_NAMES:
            if name in check_text:
                skip = True
                break
        if skip:
            continue
        for kw in SKIP_TYPES:
            if kw in trans_name:
                skip = True
                break
        if skip:
            continue
        if '银联入账' in trans_name:
            for kw in SKIP_MEMO:
                if kw in memo_raw or kw in counterparty_raw:
                    skip = True
                    break
        if skip:
            continue

        # 公积金提取 → 保留为收入（提取的钱实打实到银行卡）
        check_text = f'{counterparty_clean} {memo_raw}'
        is_housing_fund = any(kw in check_text for kw in HOUSING_FUND_KEYWORDS)
        ie_type = '收入'

        # 对方名别名映射（仅中国银行生效）
        if source_system == '中国银行':
            cp_display = BOC_COUNTERPARTY_ALIAS.get(counterparty_clean, counterparty_clean)
        else:
            cp_display = counterparty_clean

        records.append(OrderedDict([
            ('transaction_time', f'{date_str} {time_str}'),
            ('transaction_type', trans_name if trans_name else '未知'),
            ('counterparty', cp_display),
            ('product_desc', desc_clean),
            ('income_expense_type', ie_type),
            ('amount', amount),
            ('payment_method', payment_method),
            ('transaction_status', '成功'),
            ('transaction_id', None),
            ('source_system', source_system),
            ('business_trip', False),
        ]))

    return records


def parse_bocomm_pdf(filepath, password, payment_method, source_system):
    """解析交通银行PDF流水"""
    import fitz

    doc = fitz.open(filepath)
    if doc.needs_pass and password:
        doc.authenticate(password)

    raw_lines = []
    for page in doc:
        for line in page.get_text().split('\n'):
            line = line.strip()
            if line:
                raw_lines.append(line)
    doc.close()

    # 过滤页眉页脚和星号分隔线
    lines = []
    for l in raw_lines:
        if is_header(l):
            continue
        if '****' in l:
            continue
        if '第' in l and '页' in l:
            continue
        if '/' in l and ('页' in l or '行数' in l):
            continue
        # 过滤纯星号行
        if re.match(r'^[\s\*]+$', l):
            continue
        lines.append(l)

    records = []
    i = 0
    while i < len(lines):
        if not re.match(r'^\d{1,3}$', lines[i]):
            i += 1
            continue
        serial = lines[i]

        if i + 6 >= len(lines):
            break

        balance_str = lines[i + 1].replace(',', '')
        if not re.match(r'^\d+(\.\d+)?$', balance_str):
            i += 1
            continue

        trans_type = lines[i + 2]
        dc_flag = lines[i + 3]
        if '贷' not in dc_flag and '借' not in dc_flag:
            i += 1
            continue

        time_str = lines[i + 4]
        if not re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', time_str):
            i += 1
            continue

        amt_str = lines[i + 5].replace(',', '')
        try:
            amount = round(float(amt_str), 2)
        except ValueError:
            i += 1
            continue

        # 渠道（剩余行直到下一序号）
        remaining = []
        j = i + 6
        while j < len(lines):
            if re.match(r'^\d{1,3}$', lines[j]) and j + 6 < len(lines):
                next_check = lines[j + 1].replace(',', '')
                if re.match(r'^\d+(\.\d+)?$', next_check):
                    break
            remaining.append(lines[j])
            j += 1

        # 分配剩余字段
        channel = ''
        counterparty_account = ''
        counterparty_name = ''
        abstract = ''

        if remaining:
            channel = remaining[0]
            acc_parts = []
            name_parts = []
            abs_parts = []
            mode = 'account'
            for k in range(1, len(remaining)):
                part = remaining[k]
                if mode == 'account':
                    acc_parts.append(part)
                    mode = 'name'
                elif mode == 'name':
                    name_parts.append(part)
                    mode = 'abstract'
                elif mode == 'abstract':
                    abs_parts.append(part)

            if acc_parts:
                counterparty_account = ''.join(acc_parts)
            if name_parts:
                counterparty_name = ''.join(name_parts)
            if abs_parts:
                abstract = ''.join(abs_parts)

        # 过滤退款/退货
        is_refund = any(kw in trans_type for kw in ['退款', '退货'])
        if is_refund:
            i = j
            continue

        # 过滤跨行汇款到自己其他卡（按需配置）
        # 示例： if '本人姓名' in counterparty_name:
        #     i = j
        #     continue

        # 过滤页面汇总记录（非真实交易）
        if '打印完毕' in abstract or '借方发生额汇总' in abstract or '贷方发生额汇总' in abstract:
            i = j
            continue

        # 清洗 product_desc
        abstract_clean = clean_bocomm_product_desc(abstract)

        # business_trip: 标记差旅相关交易
        is_biz_trip = False
        if '4307' in payment_method:
            if '报销' in trans_type or '代发报销' in (abstract_clean or ''):
                is_biz_trip = True

        # 对方名：出差记录写差补，其他保持原名
        cp_display = '差补' if is_biz_trip else counterparty_name

        # 出差报销不计入日常收入（走差旅池独立核算）
        ie_type = '收入'
        if is_biz_trip:
            ie_type = '不计收支'

        dt = time_str[:16]
        records.append(OrderedDict([
            ('transaction_time', dt),
            ('transaction_type', trans_type),
            ('counterparty', cp_display),
            ('product_desc', abstract_clean),
            ('income_expense_type', ie_type),
            ('amount', amount),
            ('payment_method', payment_method),
            ('transaction_status', '成功'),
            ('transaction_id', None),
            ('source_system', source_system),
            ('business_trip', is_biz_trip),
        ]))

        i = j

    return records


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    all_records = []

    for bank_name, cfg in BANK_CONFIGS.items():
        fn = cfg['filename']
        # 优先在 data/raw/ 下找，其次在根目录
        path = os.path.join(RAW_DIR, fn)
        if not os.path.exists(path):
            path = os.path.join(SCRIPT_DIR, fn)
        if not os.path.exists(path):
            msg = f'[跳过] {bank_name} 文件未找到: {fn}'
            print(msg)
            continue
        try:
            if '中国银行' in bank_name:
                recs = parse_boc_pdf(path, cfg.get('password'),
                                     cfg['payment_method'], cfg['source_system'])
            else:
                recs = parse_bocomm_pdf(path, cfg.get('password'),
                                        cfg['payment_method'], cfg['source_system'])
            msg = f'{bank_name}: {len(recs)} 条收入记录'
            print(msg)
            all_records.extend(recs)
        except Exception as e:
            msg = f'{bank_name} 解析失败: {e}'
            print(msg)

    # 租房补贴 → 人才补贴（统一对方名）
    for r in all_records:
        if '租房补贴' in r.get('product_desc', ''):
            r['counterparty'] = '人才补贴'

    if all_records:
        total = sum(r['amount'] for r in all_records)
        print(f'\n总收入: {round(total, 2)} 元（共 {len(all_records)} 笔）')

        from collections import Counter
        tc = Counter()
        for r in all_records:
            tc[r['transaction_type']] += 1
        print('收入类型:')
        for k, v in sorted(tc.items(), key=lambda x: -x[1]):
            amt = sum(r['amount'] for r in all_records if r['transaction_type'] == k)
            print(f'  {k}: {v} 笔, {round(amt, 2)} 元')

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_records, f, ensure_ascii=False, indent=2)

        size = os.path.getsize(OUTPUT_FILE) / 1024
        print(f'\n已保存: {OUTPUT_FILE} ({round(size, 1)} KB)')
    else:
        print('无记录')


if __name__ == '__main__':
    main()
