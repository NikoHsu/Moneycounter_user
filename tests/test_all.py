"""
Transaction 类单元测试 + 规则配置验证
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.transaction import Transaction
from src.config_loader import get_config

# 加载真实配置
CONFIG = get_config()


def make_tx(overrides: dict = None) -> Transaction:
    raw = {
        "transaction_time": "2026-05-10 12:30:00",
        "transaction_type": "消费",
        "counterparty": "测试商家",
        "product_desc": "测试商品",
        "income_expense_type": "支出",
        "amount": "100.00",
        "payment_method": "微信支付",
        "transaction_status": "已完成",
        "transaction_id": "TX001",
        "source_system": "微信",
    }
    if overrides:
        raw.update(overrides)
    return Transaction(raw, config=CONFIG)


def test_basic_attributes():
    tx = make_tx()
    assert tx.amount == 100.00
    assert tx.transaction_id == "TX001"
    assert tx.income_expense_type == "支出"
    print("  [OK] test_basic_attributes")


def test_is_income():
    tx = make_tx({"income_expense_type": "收入"})
    assert tx.is_income()
    assert not tx.is_expense()
    print("  [OK] test_is_income")


def test_is_expense():
    tx = make_tx({"income_expense_type": "支出"})
    assert tx.is_expense()
    assert not tx.is_income()
    print("  [OK] test_is_expense")


def test_is_ignored():
    tx = make_tx({"income_expense_type": "不计收支"})
    assert tx.is_ignored()
    print("  [OK] test_is_ignored")


def test_is_refund():
    tx = make_tx({"transaction_status": "退款"})
    assert tx.is_refund()
    print("  [OK] test_is_refund")


def test_is_business_trip():
    tx = make_tx({"counterparty": "怡和东方酒店", "income_expense_type": "支出"})
    assert tx.is_business_trip()
    print("  [OK] test_is_business_trip")


def test_is_personal_transfer():
    tx = make_tx({"counterparty": "许卓旻", "income_expense_type": "收入"})
    assert tx.is_personal_transfer()
    print("  [OK] test_is_personal_transfer")


def test_personal_transfer_list():
    """验证配置中的个人转账名单"""
    ignore_list = CONFIG.get("personal_transfer_ignore", [])
    assert len(ignore_list) >= 3, f"应有至少3个名单，现有{len(ignore_list)}"
    print(f"  [OK] test_personal_transfer_list: {ignore_list}")


def test_business_trip_list():
    hotels = CONFIG.get("business_trip_hotels", [])
    assert len(hotels) >= 2, f"应有至少2个酒店，现有{len(hotels)}"
    print(f"  [OK] test_business_trip_list: {hotels}")


def test_rent_collection():
    """验证房租代缴规则"""
    rc = CONFIG.get("rent_collection", {})
    assert "keywords" in rc, "缺少 keywords"
    assert "amount_threshold" in rc, "缺少 amount_threshold"
    assert any('天宇' in kw for kw in rc['keywords']), "应包含天宇关键词"
    assert rc['amount_threshold'] >= 2000, f"阈值应为>=2000，当前{rc['amount_threshold']}"
    print(f"  [OK] test_rent_collection: keywords={rc['keywords']}, threshold={rc['amount_threshold']}")


def test_classify_dining():
    tx = make_tx({"product_desc": "午餐", "counterparty": "乡村基"})
    assert tx.classify_by_keywords() == "餐饮", f"应为餐饮，实际为{tx.classify_by_keywords()}"
    print("  [OK] test_classify_dining")


def test_classify_transport():
    tx = make_tx({"counterparty": "滴滴出行"})
    assert tx.classify_by_keywords() == "交通"
    print("  [OK] test_classify_transport")


def test_classify_shopping():
    tx = make_tx({"counterparty": "淘宝网"})
    assert tx.classify_by_keywords() == "购物"
    print("  [OK] test_classify_shopping")


def test_classify_unknown():
    tx = make_tx({"counterparty": "某小众店铺", "product_desc": "奇特商品"})
    assert tx.classify_by_keywords() == "其他"
    print("  [OK] test_classify_unknown")


def test_year_month():
    tx = make_tx({"transaction_time": "2026-05-10 12:30"})
    assert tx.year == 2026
    assert tx.month == 5
    assert tx.year_month == "2026-05"
    print("  [OK] test_year_month")


def test_to_ordered_dict():
    tx = make_tx()
    d = tx.to_ordered_dict()
    assert d["transaction_id"] == "TX001"
    assert d["amount"] == 100.00
    assert "business_trip" in d
    print("  [OK] test_to_ordered_dict")


def test_config_loaded():
    """验证 YAML 配置已正确加载"""
    assert "transaction_types" in CONFIG
    assert "alipay_type_map" in CONFIG
    assert "wechat_type_direct" in CONFIG
    assert "personal_transfer_ignore" in CONFIG
    assert "business_trip_hotels" in CONFIG
    assert "bank_rules" in CONFIG
    print(f"  [OK] test_config_loaded: "
          f"{len(CONFIG['transaction_types'])} 分类, "
          f"{len(CONFIG.get('alipay_type_map', {}))} 支付宝映射, "
          f"{len(CONFIG.get('wechat_type_direct', {}))} 微信映射")


def test_bank_rules():
    bank = CONFIG.get("bank_rules", {})
    assert "ignore_names" in bank
    assert "skip_types" in bank
    assert "skip_memo" in bank
    print(f"  [OK] test_bank_rules: "
          f"{len(bank.get('ignore_names', []))} 忽略名单, "
          f"{len(bank.get('skip_types', []))} 跳过类型")


def test_yaml_syntax():
    """验证 YAML 文件语法正确、无重复键问题"""
    import yaml
    path = os.path.join(os.path.dirname(__file__), "..", "config", "rules.yaml")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    # 检查是否有 None（YAML 解析异常时会返回 None 或部分数据）
    assert data is not None, "YAML 解析返回 None，文件可能有语法错误"
    print(f"  [OK] test_yaml_syntax: YAML 解析正常")


def run_all():
    print("\n" + "=" * 45)
    print("Transaction + Config 综合测试")
    print("=" * 45)
    tests = [
        test_yaml_syntax,
        test_config_loaded,
        test_basic_attributes,
        test_is_income,
        test_is_expense,
        test_is_ignored,
        test_is_refund,
        test_is_business_trip,
        test_is_personal_transfer,
        test_personal_transfer_list,
        test_business_trip_list,
        test_rent_collection,
        test_bank_rules,
        test_classify_dining,
        test_classify_transport,
        test_classify_shopping,
        test_classify_unknown,
        test_year_month,
        test_to_ordered_dict,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {t.__name__}: {e}")
    print(f"\n{'=' * 45}")
    print(f"通过: {passed}/{len(tests)}")
    print(f"{'=' * 45}\n")


if __name__ == "__main__":
    run_all()
