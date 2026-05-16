with open(r'E:\moneycounter\process.py', 'r', encoding='utf-8') as f:
    t = f.read()
for kw in ['来福士', '智能寄存', '智能服务', '元宝', '拼多多', '盒马', '鲜丰']:
    print(f'{kw}: {"found" if kw in t else "not found"}')
