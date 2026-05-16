import json
d = json.load(open(r'.\data\bank_data.json', 'r', encoding='utf-8'))

from collections import defaultdict
by_bank = defaultdict(list)
for r in d:
    by_bank[r['source_system'] + '(' + r['payment_method'].split('(')[-1].replace(')', '') + ')'].append(r)

for bank, recs in sorted(by_bank.items()):
    total = sum(r['amount'] for r in recs)
    print(f'\n=== {bank} === ({len(recs)}绗? {total:.2f}鍏?')
    for r in recs:
        print(f'  {r["transaction_time"]} | {r["transaction_type"]:12s} | {r["amount"]:>8.2f} | {r["counterparty"][:25]:25s} | {r["product_desc"][:25]}')
