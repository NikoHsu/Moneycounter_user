import json
d = json.load(open(r'E:\moneycounter\data\bank_data.json', 'r', encoding='utf-8'))
for r in d:
    cp = r['counterparty'] or '(绌?'
    desc = r['product_desc'] or '(绌?'
    print(f'{r["transaction_type"]:10s} | cp=[{cp:25s}] | desc=[{desc[:60]}] | {r["amount"]:>8.2f} | {r["source_system"]}')
