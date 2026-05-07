"""
M07 通知注入攻击 - 标准运行脚本
基于 _attack_runner.py / batch_runner.py 通用架构

用法:
  python run_attack.py                          # 运行全部
  python run_attack.py --start 0 --count 5      # 运行前5条
  python run_attack.py --model qwen-vl-max-latest
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
from attacks.batch_runner import run_batch

DATASET = os.path.join(os.path.dirname(__file__),
                       "attack_data_enhanced_20260310_215949.json")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="M07 通知注入攻击测试")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--count", type=int, default=None)
    parser.add_argument("--model", default="qwen-vl-max-latest")
    parser.add_argument("--max-steps", type=int, default=15)
    args = parser.parse_args()

    run_batch(
        dataset_path=DATASET,
        start=args.start, count=args.count,
        model=args.model, max_steps=args.max_steps,
    )
