"""동일 물량의 기존 실행 배치(12 mm)와 3단 dense(3 mm)를 비교한다.

패키지 루트에서 python3 -m tools.benchmark_palletizing_dense.
ROS 실행 성공률이 아니라 순수 기하 비교이며 전역 최적성을 주장하지 않는다.
"""
import argparse
import json
import time

from bin_picking.palletizing_cell import motion_plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=20260909)
    parser.add_argument('--box-count', type=int, default=36)
    args = parser.parse_args()
    results = []
    for strategy in ('compact', 'dense'):
        start = time.monotonic()
        plan, _ = motion_plan(args.seed, args.box_count, strategy)
        results.append({'strategy': strategy, 'elapsed_s': time.monotonic()-start,
                        'metrics': plan.to_dict()['metrics'], 'rejected': plan.rejected})
    print(json.dumps({'seed': args.seed, 'box_count': args.box_count,
                      'scope': 'offline_geometry_only', 'results': results}, indent=2))


if __name__ == '__main__':
    main()
