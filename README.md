# MoneyCounter - 金融流水分析工具

一个将微信、支付宝、银行卡的账单合并为标准化的 JSON 数据的工具，支持消费分类、统计分析和可视化仪表盘。

将微信、支付宝、银行卡的账单合并为标准化的 JSON 数据，支持消费分类、统计分析。
<img width="1506" height="844" alt="image" src="https://github.com/user-attachments/assets/4f0980d1-1614-4a54-91f6-e170ca713fad" />


<img width="1533" height="813" alt="image" src="https://github.com/user-attachments/assets/eda41797-54ee-4308-9434-73b1881383ca" />




## 项目结构

```
E:\moneycounter_single\
├── config/
│   └── rules.yaml                 ← 全部规则外置（分类关键词、映射、特殊交易等）
├── src/                           ← 核心模块
│   ├── transaction.py             ← Transaction OOP 类
│   ├── config_loader.py           ← YAML 配置加载器
│   ├── analyzer.py                ← 统计分析模块
│   └── manual_loader.py           ← 手动补充数据（房租/公积金）加载器
├── scripts/
│   └── run.py                     ← 统一入口（测试/分析）
├── tests/                         ← 测试 + 调试脚本
│   ├── test_all.py                ← 单元测试
│   ├── check_others.py            ← 调试：查看"其他"分类详情
│   ├── check_refunds.py           ← 调试：查看退款配对详情
│   ├── check_refund_bug.py        ← 调试：检查退款异常
│   ├── check_keywords.py          ← 调试：确认关键词是否生效
│   ├── check_special.py           ← 调试：检查特殊交易处理
│   ├── check_earn.py              ← 调试：检查银行卡收入数据
│   └── fix_fstring.py             ← 修复脚本
├── app/
│   └── dashboard.py               ← Streamlit 可视化仪表盘
├── data/
│   ├── raw/                       ← 原始数据（放这里，从各平台导出的账单文件）
│   ├── manual/                    ← 手动补充数据
│   │   ├── recurring_expenses.json  ← 周期性支出（如房租）
│   │   └── housing_fund.json        ← 公积金月缴
│   ├── app_data.json              ← 微信+支付宝合并输出
│   └── bank_data.json             ← 银行卡收入数据
├── process.py                     ← 核心处理（微信+支付宝→app_data.json）
├── parse_bank.py                  ← 银行卡PDF解析（→bank_data.json）
└── README.md                      ← 本文档
```

## 架构概览

```
微信.xlsx ──→ parse_wechat_file() ──┐
                                     ├──→ deduplicate() → normalize_refunds()
支付宝.csv ─→ parse_alipay_file()  ──┘         → normalize_special_transactions()
                                                → app_data.json
银行卡.pdf ─→ parse_bank.py                    → bank_data.json
房租/公积金 ─→ src/manual_loader.py             → 仪表盘加载
```

**所有规则均从 `config/rules.yaml` 读取**，修改规则无需改动 Python 代码。

## ⚙️ 新用户配置指南

### 第一步：个人信息修改

使用本项目前，请修改 `config/rules.yaml` 中以下带 `示例` 的配置项：

**① 个人转账不计收入 (`personal_transfer_ignore`)**
```yaml
personal_transfer_ignore:
  - 你的亲友名字A    # 这些人转给你的钱，不计入实际收入
  - 你的亲友名字B    # （比如房租代缴、互相转账等）
```

**② 房租代缴 (`rent_collection.keywords`)**
```yaml
rent_collection:
  keywords:
    - 房东名字或关键词
  amount_threshold: 2000   # 金额≥此值才不计收支
```

**③ 出差酒店 (`business_trip_hotels`)**
```yaml
business_trip_hotels:
  - 你出差住过的酒店名   # 这些酒店的支出标记为差旅，不计入日常支出
```

**④ 银行卡配置 (`data_sources.files.bank_configs`)**
```yaml
bank_configs:
  - bank_name: "你的银行名"           # 显示名称
    filename: "你的PDF文件名.pdf"      # 放在 data/raw/ 中
    password: "你的PDF密码"           # 有密码就填，无则 null
    payment_method: "银行卡名(尾号)"    # 如 招商银行储蓄卡(8888)
    source_system: "招商银行"          # 来源系统名
```

**⑤ 银行卡别名 (`parse_bank.py` 中，约第30行)**
```python
BOC_COUNTERPARTY_ALIAS = {
    '你的单位全称': '上班',     # 将银行流水中的单位名称映射为简短别名
}
```

**⑥ 过滤自己其他卡的转账 (`parse_bank.py` 中，约第460行)**
```python
# 找到类似以下代码，将'你的名字'改为你的真实姓名
if '你的姓名' in counterparty_name:
    i = j
    continue
```

**⑦ 租房押金/保证金关键词 (`rules.yaml`)**
```yaml
deposit_keywords:
  - 押金
  - 保证金
  - 定金       # 可按需增删
```

### 第二步：准备数据文件

1. 从 **微信** 导出账单（.xlsx），放入 `data/raw/`
2. 从 **支付宝** 导出账单（.csv），放入 `data/raw/`
3. （可选）从 **中国银行/交通银行** 导出 PDF 流水，放入 `data/raw/` 并按上面第④步配置
4. 编辑 `data/manual/recurring_expenses.json` 填入你的房租等周期性支出（可选）
5. 编辑 `data/manual/housing_fund.json` 填入你的公积金月缴数据（可选）

### 第三步：运行
```bash
conda activate moneycounter
python process.py           # 处理微信+支付宝
python parse_bank.py        # 处理银行卡PDF（如有）
streamlit run app/dashboard.py  # 启动仪表盘
```

### 第四步：（可选）补充分类关键词

初次运行后，用以下命令查看未分类的交易：
```bash
python tests/check_others.py
```
在 `config/rules.yaml` 的 `transaction_types` 对应分类下补充关键词后重新运行即可。

---

## 手机预览

同一 WiFi 下，手机浏览器输入 http://你电脑IP:8501 就能打开。数据还在电脑上跑，手机只负责显示。


## 输出字段

| 字段 | 说明 | 示例 |
|------|------|------|
| `transaction_time` | 交易时间 | `2026-04-15 21:44` |
| `transaction_type` | 交易类型（10大类） | `餐饮` |
| `counterparty` | 交易对方 | `乡村基四川中坝鹏瑞利餐厅` |
| `product_desc` | 商品说明 | `01081010_乡村基四川中坝鹏瑞利餐厅` |
| `income_expense_type` | 收支（收入/支出/不计收支） | `支出` |
| `amount` | 金额 | `26.00` |
| `payment_method` | 支付方式（已清洗） | `兴业银行储蓄卡(6918)` |
| `transaction_status` | 状态（成功/退款/失败） | `成功` |
| `transaction_id` | 交易单号 | `4200003035202604157164969393` |
| `source_system` | 来源（微信/支付宝/银行） | `微信` |
| `business_trip` | 是否出差 | `true` |

## 特殊交易处理

| 规则 | 来源文件 | 说明 |
|------|---------|------|
| 个人转账不计收入 | `rules.yaml` | 指定联系人转账不计入实际收入 |
| 房租代缴 | `rules.yaml` | 金额≥threshold 不计收支 |
| 退款交易 | `process.py` | 原交易+退款记录都标记为不计收支 |
| 出差酒店 | `rules.yaml` | 标记 business_trip=true，不计收支 |
| 差旅报销 | `rules.yaml` | 计入差旅池独立核算 |
| 公积金月缴 | `manual/housing_fund.json` | 计入公积金池独立核算 |

## 如何维护

### 补充分类关键词
编辑 `config/rules.yaml`，在 `transaction_types` 对应分类下加关键词：

```yaml
transaction_types:
  餐饮:
    - 新店名   # ← 加在这里
```

### 修改支付宝/微信映射
编辑 `config/rules.yaml`，修改 `alipay_type_map` 或 `wechat_type_direct`。

### 新增手动数据（房租/公积金）
编辑对应文件：`data/manual/recurring_expenses.json` 或 `data/manual/housing_fund.json`。

### 新增银行卡PDF
编辑 `config/rules.yaml`，在 `data_sources.files.bank_configs` 中新增配置。

## 运行方式

```bash
conda activate moneycounter

# 处理微信+支付宝账单
python process.py

# 解析银行卡PDF
python parse_bank.py

# 运行测试
python scripts/run.py --test

# 运行分析
python scripts/run.py --analyze

# 启动仪表盘
streamlit run app/dashboard.py
```

## 📥 如何新增数据文件

### 新增微信或支付宝账单

1. 将原始文件放入 `data/raw/` 目录
2. 文件名应包含 `微信` 或 `支付宝` 字样（程序自动匹配）
3. 运行 `python process.py` 即可

```text
data/raw/
├── 微信支付账单流水文件_2026年*.xlsx   ← 放这里
└── 支付宝交易明细_2026年*.csv        ← 放这里
```

### 新增银行卡PDF（只导入收入）

1. 将PDF放入 `data/raw/` 目录
2. 在 `config/rules.yaml` 的 `data_sources.files.bank_configs` 中新增配置：

```yaml
bank_configs:
  - bank_name: "你的银行名"           # 显示名称
    filename: "你的PDF文件名.pdf"      # 必须与 data/raw/ 中的文件名完全一致
    password: "你的PDF密码"           # 有密码就填，无则 null
    payment_method: "银行卡名(尾号)"    # 如 招商银行储蓄卡(8888)
    source_system: "招商银行"          # 来源系统名
```

3. 运行 `python parse_bank.py` 即可

**注意**：银行卡PDF只导入收入类交易，支出自动跳过。PDF解析目前支持中国银行和交通银行格式。

## 常见问题

### Q: 加了新文件但程序没找到？
文件必须含有关键词（微信/支付宝/银行卡名），且放在 `data/raw/` 目录。

### Q: 怎么改分类规则？
编辑 `config/rules.yaml` 的 `transaction_types` 部分，在对应分类下加关键词即可，无需改代码。

### Q: 房租代缴怎么处理？
规则在 `config/rules.yaml` 的 `rent_collection` 中配置：
- 关键词匹配
- 金额 >= threshold 的自动标记为不计收支
- 小额转账正常计入
- 含"押金"字段的交易也不计支出

## 注意事项

- 原始数据文件请放入 `data/raw/` 目录
- 首次使用前请确认 Conda 环境 `moneycounter` 已激活
- 所有规则配置在 `config/rules.yaml`，改规则无需改代码
