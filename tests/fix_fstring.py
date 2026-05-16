with open(r'E:\moneycounter\parse_bank.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the f-string by just replacing the cfg part
# The file has: cfg[\"filename\"]  which is invalid in f-string
content = content.replace('cfg[\\"filename\\"]', "cfg['filename']")

with open(r'E:\moneycounter\parse_bank.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
