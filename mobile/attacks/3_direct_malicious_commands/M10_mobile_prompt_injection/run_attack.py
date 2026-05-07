"""
M10 移动端提示注入攻击 - 标准运行脚本
基于 _attack_runner.py / batch_runner.py 通用架构

用法:
  python run_attack.py                          # 运行全部(v1数据集)
  python run_attack.py --dataset M10-diverse-attack-v2.json  # v2数据集
  python run_attack.py --start 0 --count 5      # 运行前5条
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
from attacks.batch_runner import run_batch

DATASET_V1 = os.path.join(os.path.dirname(__file__), "M10-diverse-attack.json")
DATASET_V2 = os.path.join(os.path.dirname(__file__), "M10-diverse-attack-v2.json")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="M10 移动端提示注入攻击测试")
    parser.add_argument("--dataset", type=str, default=None,
                        help="数据集文件名 (默认 M10-diverse-attack.json)")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--count", type=int, default=None)
    parser.add_argument("--model", default="qwen-vl-max-latest")
    parser.add_argument("--max-steps", type=int, default=15)
    args = parser.parse_args()

    dataset = args.dataset
    if dataset is None:
        dataset = DATASET_V1
    elif not os.path.isabs(dataset):
        dataset = os.path.join(os.path.dirname(__file__), dataset)

    run_batch(
        dataset_path=dataset,
        start=args.start, count=args.count,
        model=args.model, max_steps=args.max_steps,
    )
