import json
d = json.load(open(r'.\data\app_data.json', 'r', encoding='utf-8'))
o = [r for r in d if r['transaction_type'] == '鍏朵粬']
print(f'鍏朵粬鍓╀綑: {len(o)}/1028\n')
for r in o:
    s = r['transaction_status']
    ie = r['income_expense_type']
    a = r['amount']
    c = r['counterparty']
    src = r['source_system']
    print(f'{s:4s} {ie:6s} {a:>8.2f} | {c[:25]:25s} | {src}')
