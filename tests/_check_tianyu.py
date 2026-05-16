import json, re
d = json.load(open(r'E:\moneycounter\data\app_data.json', 'r', encoding='utf-8'))

# Check 澶╁畤/琚佸ぉ瀹?records
print('=== 澶╁畤/琚佸ぉ瀹?鐩稿叧 ===')
for r in d:
    cp = r.get('counterparty', '') or ''
    pd = r.get('product_desc', '') or ''
    # remove emoji for print
    cp_clean = re.sub(r'[^\u0000-\uFFFF]', '', cp)
    pd_clean = re.sub(r'[^\u0000-\uFFFF]', '', pd)
    if '澶╁畤' in cp_clean or '澶╁畤' in pd_clean or '琚佸ぉ瀹? in cp_clean:
        print(f'  cp=[{cp_clean}] desc=[{pd_clean[:60]}] amt={r["amount"]} ie={r["income_expense_type"]}')

# Check 鎶奸噾 records
print()
print('=== 鎶奸噾鐩稿叧 ===')
for r in d:
    pd = r.get('product_desc', '') or ''
    pd_clean = re.sub(r'[^\u0000-\uFFFF]', '', pd)
    if '鎶奸噾' in pd_clean:
        print(f'  desc=[{pd_clean[:60]}] amt={r["amount"]} ie={r["income_expense_type"]} cp=[{r.get("counterparty","")}]')
