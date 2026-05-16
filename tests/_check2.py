import json
d = json.load(open(r'E:\moneycounter\data\bank_data.json', 'r', encoding='utf-8'))
for r in d:
    if '鑸┖' in r.get('product_desc', '') or '鑸┖' in r.get('counterparty', ''):
        cp = r['counterparty'] or '(绌?'
        desc = r['product_desc'] or '(绌?'
        print(f'cp=[{cp}] desc=[{desc}]')
print('---')
# Also check 澶╁畤 records
for r in d:
    cp = r.get('counterparty', '') or ''
    pd = r.get('product_desc', '') or ''
    if '澶╁畤' in cp or '澶╁畤' in pd or '琚佸ぉ瀹? in cp:
        print(f'[澶╁畤] cp=[{cp}] desc=[{pd[:60]}] amt={r["amount"]}')
