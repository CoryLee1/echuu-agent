"""GagLedger：登记去重、未回收查询、标记回收。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from echuu.core.gag_ledger import GagLedger


def test_register_and_query():
    ledger = GagLedger()
    ledger.register(["猫罐头汇率", "左耳尖结晶"], unit_index=0)
    ledger.register(["猫罐头汇率", "  "])  # 重复与空白忽略
    assert len(ledger) == 2
    assert ledger.unrecalled() == ["猫罐头汇率", "左耳尖结晶"]


def test_mark_recalled():
    ledger = GagLedger()
    ledger.register(["猫罐头汇率"])
    ledger.mark_recalled("猫罐头汇率")
    assert ledger.unrecalled() == []
