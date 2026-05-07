"""M07 通知注入 - 快速测试 (1步判定,未拒绝即攻击成功)"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
from attacks.quick_test_runner import run_quick_test

DATASET = os.path.join(os.path.dirname(__file__), "attack_data_enhanced_20260310_215949.json")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="M07 快速测试")
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--count", type=int, default=None)
    p.add_argument("--model", default="qwen-vl-max-latest")
    a = p.parse_args()
    run_quick_test(DATASET, start=a.start, count=a.count, model=a.model)
