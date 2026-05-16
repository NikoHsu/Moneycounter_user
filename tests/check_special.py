import json
d = json.load(open(r'.\data\app_data.json', 'r', encoding='utf-8'))

# 妫€鏌ュぉ瀹?print('=== 澶╁畤鐩稿叧 ===')
for r in d:
    if '澶╁畤' in r['counterparty'] or '澶╁畤' in r['product_desc']:
        print(f'  {r["income_expense_type"]:6s} | {r["amount"]:>8.2f} | {r["counterparty"]:30s} | {r["product_desc"]}')

# 妫€鏌ュ嚭宸厭搴?print('\n=== 鍑哄樊閰掑簵 ===')
for r in d:
    if r.get('business_trip'):
        print(f'  {r["income_expense_type"]:6s} | {r["amount"]:>8.2f} | {r["counterparty"]:30s} | {r["product_desc"][:40]}')

# 妫€鏌ヨ鍗撴椈/绉︽宸?璁稿織寮?print('\n=== 璁?绉︾浉鍏?===')
for name in ['璁稿崜鏃?, '绉︽宸?, '璁稿織寮?]:
    for r in d:
        if name in r['counterparty']:
            print(f'  [{name}] {r["income_expense_type"]:6s} | {r["amount"]:>8.2f} | {r["counterparty"]}')
