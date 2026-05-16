"""
入口脚本 - 合并后的数据加载与分析入口

用法：
    conda activate moneycounter
    python scripts/run.py [--test] [--analyze]
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    import argparse
    parser = argparse.ArgumentParser(description="MoneyCounter 金融流水分析")
    parser.add_argument("--test", action="store_true", help="运行单元测试")
    parser.add_argument("--analyze", action="store_true", help="运行分析")
    parser.add_argument("--year", type=int, help="分析指定年份")
    args = parser.parse_args()

    if args.test:
        from tests.test_all import run_all
        run_all()
        return

    if args.analyze:
        from src.config_loader import get_config
        from src.analyzer import Analyzer
        import json

        config = get_config()
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        output_file = os.path.join(data_dir, "app_data.json")
        earn_file = os.path.join(data_dir, "bank_data.json")

        all_txs = []

        # 加载 app_data.json
        if os.path.exists(output_file):
            with open(output_file, "r", encoding="utf-8") as f:
                records = json.load(f)
            from src.transaction import Transaction
            txs = [Transaction(r, config=config) for r in records]
            all_txs.extend(txs)
            print(f"[OK] 已加载 use_data.json: {len(txs)} 条")

        # 加载 earn_data.json
        if os.path.exists(earn_file):
            with open(earn_file, "r", encoding="utf-8") as f:
                records = json.load(f)
            from src.transaction import Transaction
            txs = [Transaction(r, config=config) for r in records]
            all_txs.extend(txs)
            print(f"[OK] 已加载 earn_data.json: {len(txs)} 条")

        if not all_txs:
            print("[Warn] 无数据。请先运行 process.py 和 parse_bank.py 生成数据")
            return

        analyzer = Analyzer(all_txs)
        print(analyzer.summary_report(args.year))

        monthly = analyzer.monthly_summary(args.year)
        if not monthly.empty:
            print("\n月度统计:")
            print(monthly.to_string(index=False))
        return

    # 默认：显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()
