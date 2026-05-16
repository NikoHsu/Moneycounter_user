import json
d = json.load(open(r'.\data\app_data.json', 'r', encoding='utf-8'))

refunds = [r for r in d if r['transaction_status'] == '閫€娆?]
print(f'閫€娆捐褰曞叡 {len(refunds)} 绗擻n')

# 鎸夋潵婧愬垎缁?from collections import Counter
src = Counter()
for r in refunds:
    src[r['source_system']] += 1
for k, v in src.most_common():
    print(f'  {k}: {v} 绗擻n')

# 鎸夋敹鏀垎缁?ie = Counter()
for r in refunds:
    ie[r['income_expense_type']] += 1
for k, v in ie.most_common():
    print(f'  {k}: {v}')

print()
print('=== 閫€娆鹃€愮瑪鏄庣粏 ===')
for r in refunds:
    s = r['source_system']
    ie = r['income_expense_type']
    a = r['amount']
    st = r['transaction_status']
    cp = r['counterparty'][:25]
    ti = r['transaction_time']
    print(f'  [{s}] {ti} | {ie:6s} | {a:>8.2f} | {cp:25s}')
