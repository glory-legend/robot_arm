"""같은 3종 박스·도착 순서에서 greedy/compact 오프라인 기준선 비교(ROS 무의존)."""
import argparse
import json
import statistics
import time

from bin_picking.palletizing_planner import demo_boxes, plan_boxes, plan_quality


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=int, default=30)
    parser.add_argument('--seed', type=int, default=20260909)
    parser.add_argument('--counts', type=int, nargs='+', default=[12, 24, 36])
    args = parser.parse_args()
    if args.cases < 1:
        parser.error('--cases must be positive')
    report = {'seed': args.seed, 'cases_per_count': args.cases, 'results': []}
    for count in args.counts:
        metrics = {s: [] for s in ('greedy', 'compact')}
        strictly_better = 0
        for i in range(args.cases):
            boxes = demo_boxes(args.seed + i, count)
            plans = {}
            for strategy in metrics:
                start = time.perf_counter()
                plans[strategy] = plan_boxes(boxes, strategy=strategy)
                elapsed = time.perf_counter() - start
                row = plans[strategy].to_dict()['metrics']
                row['planning_ms'] = elapsed * 1000
                metrics[strategy].append(row)
            assert plan_quality(plans['compact']) <= plan_quality(plans['greedy'])
            strictly_better += plan_quality(plans['compact']) < plan_quality(plans['greedy'])
        report['results'].append({
            'box_count': count, 'compact_strictly_better_cases': strictly_better,
            'means': {strategy: {key: statistics.mean(row[key] for row in rows)
                                 for key in rows[0]} for strategy, rows in metrics.items()},
        })
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
