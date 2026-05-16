import json
d = json.load(open(r'.\data\app_data.json', 'r', encoding='utf-8'))
cnt = 0
for r in d:
    if r['transaction_status'] == '閫€娆? and r['income_expense_type'] == '鏀嚭':
        cnt += 1
        print(f'{r["transaction_time"]} | {r["amount"]:>8.2f} | {r["counterparty"]:30s} | {r["product_desc"]}')
print(f'\n鎬绘暟: {cnt}')
