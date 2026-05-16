"""
Transaction 类 - 单条交易的核心数据模型

所有判断逻辑内聚为方法，避免散落的 if/else 判断。
"""

from datetime import datetime
from collections import OrderedDict


class Transaction:
    """单条交易记录"""

    def __init__(self, raw: dict, config: dict = None):
        self.transaction_time = raw.get("transaction_time", "")
        self.transaction_type = raw.get("transaction_type", "")
        self.counterparty = raw.get("counterparty", "")
        self.product_desc = raw.get("product_desc", "")
        self.income_expense_type = raw.get("income_expense_type", "")
        self.amount = float(raw.get("amount", 0))
        self.payment_method = raw.get("payment_method", "")
        self.status = raw.get("transaction_status", "")
        self.transaction_id = raw.get("transaction_id", "")
        self.source = raw.get("source_system", "")
        self.business_trip = raw.get("business_trip", False)

        # 可选字段
        self.remark = raw.get("remark", "")
        self.balance = raw.get("balance")
        self._parsed_time = self._parse_time(raw.get("transaction_time"))
        self._config = config or {}

    # ---- 字段别名 ----
    @property
    def time(self): return self.transaction_time
    @property
    def type(self): return self.transaction_type
    @property
    def desc(self): return self.product_desc

    # ---- 状态判断 ----

    def is_income(self) -> bool:
        return self.income_expense_type == "收入"

    def is_expense(self) -> bool:
        return self.income_expense_type == "支出"

    def is_ignored(self) -> bool:
        """是否不计收支"""
        return self.income_expense_type == "不计收支"

    def is_refund(self) -> bool:
        """是否为退款交易"""
        if self.status == "退款":
            return True
        refund_keywords = self._config.get("refund_keywords", ["退款"])
        return any(kw in self.product_desc for kw in refund_keywords)

    def is_business_trip(self) -> bool:
        """是否为差旅支出"""
        hotels = self._config.get("business_trip_hotels", [])
        return any(hotel in self.counterparty for hotel in hotels)

    def is_personal_transfer(self) -> bool:
        """是否为个人转账（房租代缴、朋友转账等）"""
        ignore_list = self._config.get("personal_transfer_ignore", [])
        return any(name in self.counterparty or name in self.product_desc
                   for name in ignore_list)

    # ---- 分类 ----

    def classify_by_keywords(self) -> str:
        """
        根据配置规则自动分类交易
        从 transaction_types 中遍历匹配关键词
        """
        if self.is_refund():
            return "退款"

        text = f"{self.counterparty} {self.product_desc}"
        type_rules = self._config.get("transaction_types", {})

        for category, keywords in type_rules.items():
            if not keywords:
                continue
            for kw in keywords:
                if kw and isinstance(kw, str) and kw.lower() in text.lower():
                    return category
        return "其他"

    # ---- 格式化 ----

    @property
    def year(self) -> int:
        return self._parsed_time.year if self._parsed_time else 0

    @property
    def month(self) -> int:
        return self._parsed_time.month if self._parsed_time else 0

    @property
    def year_month(self) -> str:
        if self._parsed_time:
            return self._parsed_time.strftime("%Y-%m")
        return "未知"

    def to_ordered_dict(self) -> OrderedDict:
        """导出为 OrderedDict（保持字段顺序，兼容现有 JSON 输出）"""
        from collections import OrderedDict
        d = OrderedDict()
        for field in ["transaction_time", "transaction_type", "counterparty",
                       "product_desc", "income_expense_type", "amount",
                       "payment_method", "transaction_status", "transaction_id",
                       "source_system"]:
            val = getattr(self, {
                "transaction_status": "status",
                "source_system": "source",
            }.get(field, field), "")
            d[field] = val
        d["business_trip"] = self.business_trip
        return d

    def __repr__(self) -> str:
        return (f"Transaction({self.transaction_id}, "
                f"{self.amount}元, {self.income_expense_type}, "
                f"{self.counterparty})")

    # ---- 内部方法 ----

    @staticmethod
    def _parse_time(time_str):
        if not time_str:
            return None
        formats = [
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%Y/%m/%d %H:%M",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d",
            "%Y年%m月%d日",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(str(time_str).strip(), fmt)
            except (ValueError, TypeError):
                continue
        return None
