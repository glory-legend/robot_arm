# -*- coding: utf-8 -*-
"""어느 볼트를 어떻게 집을지 선택(휴리스틱·학습·plan-only 롤아웃).

SelectionMixin 은 IntegratedPickPlace 에 섞이는 책임 단위다(상태는 노드가 소유).
"""
import json
import math
import os
import random
import re
import sys
import threading
import time
import xml.etree.ElementTree as ET

import numpy as np
import rclpy
import tf_transformations
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.parameter_client import AsyncParameterClient
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

from builtin_interfaces.msg import Duration
from control_msgs.action import FollowJointTrajectory
from geometry_msgs.msg import Point, Pose, PoseStamped, Quaternion, Vector3
from moveit_msgs.action import ExecuteTrajectory, MoveGroup
from moveit_msgs.msg import (
    AttachedCollisionObject,
    BoundingVolume,
    CollisionObject,
    Constraints,
    JointConstraint,
    MotionPlanRequest,
    MoveItErrorCodes,
    OrientationConstraint,
    PlanningOptions,
    PlanningScene,
    PositionConstraint,
    RobotState,
)
from moveit_msgs.srv import (
    ApplyPlanningScene,
    GetCartesianPath,
    GetPositionFK,
    GetPositionIK,
)
from sensor_msgs.msg import JointState
from shape_msgs.msg import SolidPrimitive
from std_msgs.msg import ColorRGBA, Empty, String
from tf2_msgs.msg import TFMessage
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from visualization_msgs.msg import Marker, MarkerArray

# 볼트 통/볼트 자산 (SDF 스폰과 동일한 배치를 planning-scene에 재사용)
from bin_picking.bolt_scene import (
    BIN_OUTER,
    BIN_THICK,
    BIN_XYZ,
    BOLT_LAYOUT,
    BOLT_LEN,
    BOLT_RADIUS,
    BOLT_REST_Z,
    DROP_BIN_XYZ,
    LAYOUT_SOURCE,
    bin_collision_object,
    bolt_collision_objects,
    drop_bin_collision_object,
    object_ids as bolt_object_ids,
)

# 학습형 파지 선택기(ROS 무의존). 임포트 자체가 실패해도(파일 없음 등) 데모는
# 기존 휴리스틱으로 굴러가야 하므로 감싸 둔다 → GraspSelector=None 이면 R3 경로 비활성.
try:
    from bin_picking.grasp_selector import GraspSelector
    _SELECTOR_IMPORT_ERR = ''
except Exception as _exc:                       # noqa: BLE001
    GraspSelector = None
    _SELECTOR_IMPORT_ERR = repr(_exc)




class SelectionMixin:

    # ---------- 볼트 재시도 / 블랙리스트 상태기계 (Issue C) ----------
    def _note_progress(self):
        """파지 성공 = 무더기가 실제로 바뀜. 진전 epoch 를 올리고 보류를 푼다.

        epoch 가 오르면 모든 볼트의 실패 스트릭이 자동으로 무효화된다
        (_note_attempt_failed 가 epoch 불일치를 리셋으로 해석) → 이웃이 빠져
        정말로 집을 수 있게 된 볼트는 절대 블랙리스트로 가지 않는다.
        """
        self._pick_epoch += 1
        self._deferred.clear()

    def _note_attempt_failed(self, key, reason=''):
        """볼트(또는 외부 pose 키) 한 번의 '진전 없는' 실패를 기록.

        같은 epoch 안에서만 누적하고, MAX_NO_PROGRESS 에 도달하면 영구
        블랙리스트로 보낸다. 반환값은 블랙리스트에 넣었는지 여부.
        """
        if not key:
            return False
        epoch, n = self._attempts.get(key, (self._pick_epoch, 0))
        if epoch != self._pick_epoch:
            epoch, n = self._pick_epoch, 0      # 그 사이 진전이 있었다 → 리셋
        n += 1
        self._attempts[key] = (epoch, n)
        if n >= self.MAX_NO_PROGRESS:
            self._blacklist.add(key)
            self.get_logger().warn(
                f'[{key}] 진전 없이 {n}회 실패{f" ({reason})" if reason else ""} '
                f'— 영구 블랙리스트. 다음 볼트로 넘어갑니다')
            return True
        self.get_logger().info(
            f'[{key}] 실패 {n}/{self.MAX_NO_PROGRESS}'
            f'{f" ({reason})" if reason else ""} — 재시도 여지 있음')
        return False

    def _tried_approaches(self, key, pos):
        """이 볼트가 '지금과 같은 상황'에서 이미 실패한 기울기(deg) 집합."""
        rec = self._tried_grasp.get(key)
        if rec is None:
            return set()
        epoch, rpos, degs = rec
        if (epoch != self._pick_epoch
                or math.dist(rpos, tuple(pos)) > self.TRIED_POS_TOL):
            self._tried_grasp.pop(key, None)   # 상황이 바뀌었다 → 리셋
            return set()
        return degs

    def _record_tried(self, key, pos, deg):
        """실패한 (위치, 기울기) 조합을 기억."""
        sig = round(deg)
        rec = self._tried_grasp.get(key)
        if (rec is not None and rec[0] == self._pick_epoch
                and math.dist(rec[1], tuple(pos)) <= self.TRIED_POS_TOL):
            rec[2].add(sig)
        else:
            self._tried_grasp[key] = (self._pick_epoch, tuple(pos), {sig})

    def _selectable(self, bid):
        """지금 이 볼트를 선택 후보로 볼 수 있는가."""
        return not (bid in self._picked or bid in self._blacklist
                    or bid in self._deferred)

    def _select_topmost_bolt(self):
        """폴백 선택기: 집는 통 안에서 '가장 위 + 주변이 덜 붐비는' 볼트.
        (실제 비전이 붙으면 이 함수는 안 쓰인다)"""
        if not self._bolt_sensed:
            # 이 상태로 계속 돌면 '스폰 직후 공중 좌표'를 향해 내려가 허공만
            # 쥔다(빈손 연속). 20260721 로그의 전 사이클 실패가 정확히 이 케이스.
            self.get_logger().warn(
                '⚠ 볼트 pose 센싱 0건 — 스폰 레이아웃(낙하 전 좌표)으로 동작 중. '
                '실제 볼트는 떨어져 다른 위치라 빈손 파지가 납니다. '
                'spawn_bolts.launch.py 가 이 세션에 켜져 있는지, '
                '`ros2 topic hz /model/bolt_0/pose` 가 나오는지 확인하세요')
        cands = []
        for i in range(len(BOLT_LAYOUT)):
            bid = f'bolt_{i}'
            if not self._selectable(bid):
                continue
            pos, quat = self._bolt_pose(i)
            if not self._in_bin(pos) or not self._reach_ok(pos):
                continue
            clear = min(
                (math.dist(pos[:2], self._bolt_pose(j)[0][:2])
                 for j in range(len(BOLT_LAYOUT))
                 if j != i and f'bolt_{j}' not in self._picked),
                default=1.0)
            cands.append((pos[2], clear, i, pos, quat))
        if not cands:
            # 왜 끝나는지 남긴다 — '조용히 종료'는 디버깅이 불가능하다
            self.get_logger().info(
                f'선택 가능한 볼트 없음 — 옮김 {len(self._picked)}개 / '
                f'블랙리스트 {sorted(self._blacklist) or "없음"} / '
                f'보류 {sorted(self._deferred) or "없음"}')
            return None
        cands.sort(key=lambda c: (round(c[0], 3), c[1]), reverse=True)
        z, clear, i, pos, quat = cands[0]
        self.get_logger().info(
            f'자체 선택: bolt_{i} (높이 {z:.3f}m, 주변 여유 {clear * 1000:.0f}mm) '
            f'— 통에 {len(cands)}개 남음')
        return (f'bolt_{i}', pos, quat)

    # =========================================================
    # 학습형 파지 선택 (R3) — 특징 생성 / 후보 랭킹 / 선택
    # =========================================================
    def _grasp_features(self, pos, axis, tilt_deg, aperture, wall_cap,
                        approach, all_poses=None):
        """[R3] 파지 후보 하나(볼트×접근각) → GraspSelector 특징 dict.

        selector.FEATURES 순서와 이름이 일치해야 한다(벡터화는 selector 담당).
        기하 계산은 여기(메인 노드)서만 하고 selector 로는 dict 만 넘긴다.
        """
        if all_poses is None:
            all_poses = self._all_bolt_poses()
        p = np.asarray(pos, dtype=float)
        # 이웃 거리/개수 — 대상 자신(APERTURE_SELF_TOL 이내)은 제외.
        dists = []
        for _bid, (npos, _q) in all_poses.items():
            d = math.dist(pos[:2], npos[:2])
            if d <= self.APERTURE_SELF_TOL:
                continue
            dists.append(d)
        clear = min(dists) if dists else 0.2
        n_neigh = sum(1 for d in dists if d <= self.APERTURE_SCAN_R)
        # 손가락 닫힘축 방향 벽까지의 경로거리(양쪽 최소). inf 는 selector 가 클립.
        frame = self._grasp_frame(axis, approach)
        if frame is None:
            wall_reach = float('inf')
        else:
            y_tool = frame[1]
            wall_reach = min(self._wall_reach_along(p, y_tool),
                             self._wall_reach_along(p, -y_tool))
        ap_at_min = 1.0 if aperture <= self.GRASP_MIN_OPEN + 1e-9 else 0.0
        ax = self._unit(axis)
        axis_vert = abs(float(ax[2])) if ax is not None else 0.0
        tx, ty = float(pos[0]), float(pos[1])
        return {
            'z': float(pos[2]), 'clear': float(clear), 'n_neigh': int(n_neigh),
            'aperture': float(aperture), 'wall_cap': float(wall_cap),
            'ap_at_min': ap_at_min, 'tilt': float(tilt_deg),
            'wall_reach': float(wall_reach), 'axis_vert': axis_vert,
            'reach': float(math.hypot(tx, ty)), 'tx': tx, 'ty': ty,
        }

    def _rank_candidates(self):
        """[R3] 선택 가능한 모든 (볼트 × 접근각) 중 개구가 확보되는 후보 전부를
        selector 성공확률로 랭킹.

        반환: [(score, bolt_id, pos, quat, tilt_deg, approach_vec,
                aperture, wall_cap, feat_dict), ...]  내림차순.
        이미 실패한 (볼트, 각도)는 _tried_approaches 로 제외한다.
        """
        ranked = []
        all_poses = self._all_bolt_poses()
        for i in range(len(BOLT_LAYOUT)):
            bid = f'bolt_{i}'
            if not self._selectable(bid):
                continue
            pos, quat = self._bolt_pose(i)
            if not self._in_bin(pos) or not self._reach_ok(pos):
                continue                      # 통 밖 또는 좌우 도달권 밖(구석)
            axis = self.bolt_axis_from_quat(quat)
            if self.grasp_quat_for_axis(axis) is None:
                continue                      # 거의 수직 → 옆에서 감쌀 수 없음
            tried = self._tried_approaches(bid, tuple(pos))
            for deg, approach in self._approach_candidates(pos, axis):
                if round(deg) in tried:
                    continue
                ap = self._grasp_aperture(pos, axis, bid, approach=approach)
                if ap is None:
                    continue
                aperture, wall_cap = ap
                feat = self._grasp_features(pos, axis, deg, aperture,
                                            wall_cap, approach, all_poses)
                # 학습기가 없거나(콜드 스타트/비활성) 준비 전이면 점수 0 — 롤아웃이
                # 실제 계획-시뮬로 최종 선별하므로 학습 전에도 정상 동작한다.
                score = None
                if self.selector is not None:
                    score = self.selector.predict_proba(feat)
                if score is None:
                    score = 0.0
                # 수직 선호 프라이어: 각도에 비례한 소액 페널티를 얹어 정렬.
                # 수직으로 충분한 상황에서 굳이 손목을 꺾고 들어가는 것을 방지.
                score -= abs(deg) * self.TILT_PRIOR_PENALTY
                ranked.append((score, bid, pos, quat, deg, approach,
                               aperture, wall_cap, feat))
        ranked.sort(key=lambda c: c[0], reverse=True)
        return ranked

    def _select_learned(self):
        """[R3] 랭킹 최고점(또는 ε-탐험 시 2~3위 무작위) 후보를 채택.

        반환: ((bolt_id, pos, quat), plan) / 통과 후보 없으면 None.
        plan 은 _pick 에 넘겨 (tilt/approach/aperture) 재계산을 생략시킨다.
        """
        ranked = self._rank_candidates()
        if not ranked:
            return None
        eps = self.selector.epsilon()
        # ε 확률로 최고점 대신 2~3위 중 하나를 골라 탐색(선택 편향 완화).
        if len(ranked) > 1 and random.random() < eps:
            k = min(3, len(ranked))
            idx = random.randint(1, k - 1)    # 0(최고점) 제외한 2~k위
            mode = f'탐험 ε={eps:.2f}({idx + 1}위/{len(ranked)})'
        else:
            idx = 0
            mode = f'최고점(후보 {len(ranked)})'
        (score, bid, pos, quat, deg, approach,
         aperture, wall_cap, feat) = ranked[idx]
        self.get_logger().info(
            f'[학습 선택:{mode}] {bid} 성공확률 {score:.3f} / 기울기 {deg:+.0f}° / '
            f'개구 {aperture * 1000:.1f}mm — 선택 이유: {self.selector.explain(feat)}')
        plan = {'tilt_deg': deg, 'approach': approach, 'aperture': aperture,
                'wall_cap': wall_cap, 'feat': feat}
        return ((bid, pos, quat), plan)

    def _diverse_seeds(self):
        """접근 IK 탐색용 시드 목록: ready + 관절을 흔든 변형들.
        무작위지만 판/사이클마다 달라도 무방하다(어차피 시뮬로 걸러진다)."""
        seeds = [dict(self._ready_target)]
        base = self._ready_target
        for _ in range(self.IK_SEED_JITTER):
            s = {}
            for j, v in base.items():
                lo, hi = self.JOINT_LIMITS.get(j, (v - 1, v + 1))
                nv = v + random.uniform(-self.IK_SEED_SPREAD, self.IK_SEED_SPREAD)
                s[j] = min(hi - 0.05, max(lo + 0.05, nv))
            seeds.append(s)
        return seeds

    def _simulate_candidate(self, cand):
        """[plan-only 롤아웃] 후보 하나를 '팔을 움직이지 않고' 계획만 해서
        실제 실행 시 어떻게 될지 시뮬레이션한다.

        cand = (score, bid, pos, quat, deg, approach, aperture, wall_cap, feat)
        절차(전부 실행 없음): 접근 pose IK → 그 자세에서 하강 Cartesian 달성률
        → 낮으면 파지 pose IK 존재 여부 → 관절 여유. 이 값들로 '실행 점수'를 낸다.

        반환: (feasible: bool, sim_score: float, info: dict)
        """
        (lscore, bid, pos, quat, deg, approach, aperture, wall_cap, feat) = cand
        axis = self.bolt_axis_from_quat(quat)
        ori = self.grasp_quat_for_axis(axis, approach)
        if ori is None:
            return False, -9.9, {}
        tx, ty = pos[0], pos[1]
        grasp_z = self._grasp_z_for(pos[2])
        app_pose = Pose()
        app_pose.position = Point(x=tx, y=ty, z=self.APPROACH_HEIGHT)
        app_pose.orientation = ori
        grasp_pose = Pose()
        grasp_pose.position = Point(x=tx, y=ty, z=grasp_z)
        grasp_pose.orientation = ori

        # 여러 IK 분기(팔꿈치 방향)를 시드로 접근 자세를 풀고, 각 자세에서
        # '하강하면 실제로 파지 깊이에 닿는가'를 시뮬한다. 닿는 자세가 하나라도
        # 있으면 그 자세로 실행한다 → '그 분기로는 못 내려가는' 문제를 우회.
        best_local = None
        for seed in self._diverse_seeds():
            app_joints = self._ik_joint_goal(app_pose, seed=seed)
            if app_joints is None:
                continue
            # 이 접근 자세에서 하강 직선 달성률
            descent = self.make_vertical_waypoints(
                tx, ty, self.APPROACH_HEIGHT, grasp_z, ori)
            _, frac = self.compute_cartesian(
                descent, vel=self._vel_fine, start_joints=app_joints)
            line_ok = frac >= self.ROLLOUT_MIN_FRACTION
            # [비용 절감] 직선이 이미 완주면 파지 pose IK 를 부르지 않는다(콜 3→2).
            # 직선이 부족할 때만 '관절이동 폴백이 되는가'를 IK 로 확인한다.
            grasp_joints = None
            if not line_ok:
                grasp_joints = self._ik_joint_goal(grasp_pose, seed=app_joints)
            reachable = line_ok or (grasp_joints is not None)
            if not reachable:
                continue
            margin = self._joint_margin(grasp_joints or app_joints)
            sscore = (1.0 * frac + (0.5 if line_ok else 0.0)
                      + 0.4 * lscore + 0.5 * margin
                      - abs(deg) * self.TILT_PRIOR_PENALTY)
            if best_local is None or sscore > best_local[0]:
                best_local = (sscore, frac, line_ok, margin, app_joints,
                              grasp_joints is not None)
            if line_ok:
                break     # 직선 완주 자세를 찾았으면 더 볼 것 없다(최상)

        if best_local is None:
            return False, -1.0, {'why': 'no_ik_branch_reaches'}
        sscore, frac, line_ok, margin, app_joints, gik_ok = best_local
        return True, sscore, {'frac': frac, 'line_ok': line_ok,
                              'margin': round(margin, 3), 'grasp_ik': gik_ok,
                              'approach_joints': app_joints}

    def _select_by_rollout(self):
        """[plan-only 롤아웃 선택] 후보를 학습/기하 점수로 추린 뒤(TOPK), 각각을
        실제로 계획-시뮬레이션해 '실행 점수'가 가장 높은 후보를 채택한다.
        실패가 예정된 후보는 실행하지 않으므로 화면엔 최종 최적 동작만 보인다.

        반환: ((bolt_id, pos, quat), plan) / 실현 후보 없으면 None.
        """
        ranked = self._rank_candidates()
        if not ranked:
            return None
        topk = ranked[:self.ROLLOUT_TOPK]
        self.get_logger().info(
            f'[롤아웃] 후보 {len(ranked)}개 중 상위 {len(topk)}개를 '
            f'백그라운드 계획-시뮬레이션합니다(팔 안 움직임)...')
        best = None
        n_feas = 0
        for cand in topk:
            feasible, sscore, info = self._simulate_candidate(cand)
            if feasible:
                n_feas += 1
                if best is None or sscore > best[0]:
                    best = (sscore, cand, info)
        if best is None:
            self.get_logger().warn(
                f'[롤아웃] 상위 {len(topk)}개 모두 시뮬에서 실현 불가 '
                f'— 이번 사이클 실행할 후보 없음')
            return None
        sscore, cand, info = best
        (lscore, bid, pos, quat, deg, approach, aperture, wall_cap, feat) = cand
        self.get_logger().info(
            f'[롤아웃] 실현 {n_feas}/{len(topk)} → 채택 {bid} '
            f'(시뮬점수 {sscore:.3f}, 하강달성률 {info.get("frac", 0) * 100:.0f}%, '
            f'관절여유 {info.get("margin", 0):.2f}rad, 기울기 {deg:+.0f}°) '
            f'— 이 최적 동작만 실행합니다')
        plan = {'tilt_deg': deg, 'approach': approach, 'aperture': aperture,
                'wall_cap': wall_cap, 'feat': feat,
                # 시뮬에서 '하강이 닿은' 바로 그 접근 팔자세 — 실행도 이 자세로
                # 접근해야 시뮬과 동일한 IK 분기에서 하강이 성립한다.
                'approach_joints': info.get('approach_joints')}
        return ((bid, pos, quat), plan)

    def _select_fallback(self):
        """[R3] 외부 비전 자세가 없을 때의 선택 진입점.

        학습 선택기가 준비됐으면 랭킹 기반으로, 아니면 기존 휴리스틱
        (_select_topmost_bolt)으로 고른다. 학습 경로는 결정된 plan 을
        self._pending_plan 에 실어 _pick 이 재계산 없이 쓰게 한다.
        """
        self._pending_plan = None
        # 1순위: plan-only 롤아웃(내부 시뮬 후 최적 하나만 실행). 학습 전에도
        # 실제 계획으로 실현성을 판별하므로 콜드 스타트부터 바로 유효하다.
        if self.ROLLOUT_ENABLE:
            chosen = self._select_by_rollout()
            if chosen is not None:
                target, plan = chosen
                self._pending_plan = plan
                return target
            self.get_logger().info('[롤아웃] 실현 후보 없음 — 휴리스틱 폴백')
        # 2순위: 롤아웃 꺼졌고 학습기 준비됐으면 학습 랭킹만으로 선택
        elif (self.USE_LEARNED_SELECTOR and self.selector is not None
                and self.selector.ready()):
            chosen = self._select_learned()
            if chosen is not None:
                target, plan = chosen
                self._pending_plan = plan
                return target
            self.get_logger().info('[학습선택기] 통과 후보 없음 — 휴리스틱 폴백')
        return self._select_topmost_bolt()

    def _log_attempt(self, bolt, feat, ok, reason, fraction=None, dur=None,
                     metrics=None, retries=0):
        """[R4] 파지 시도 1건을 attempts.jsonl 에 append + 온라인 학습.

        모든 _pick 종결 지점에서 호출된다. 기록/학습 실패는 데모를 막지 않게
        전부 흡수한다. 특징(feat)이 있는 시도만 온라인 학습에 반영하고, 일정
        횟수마다 전체 재적합 + 저장으로 "돌 때마다 똑똑해지는" 지속 학습을 이룬다.

        USE_LEARNED_SELECTOR=False 면 데이터 기록·학습을 통째로 건너뛴다 —
        선택기를 끄면 파일 생성/학습을 포함해 '완전히 기존 동작'으로 돌아간다.

        [데스크톱 통신] 모든 _pick 종결 지점을 지나가는 이 단일 입구에, 결과를
        desktop_bridge 노드로 흘려보내는 발행 훅 하나를 얹는다(부작용만 추가,
        반환값·제어흐름 불변). 실패해도 데모를 막지 않도록 통째로 흡수한다.

        `metrics`(dict|None): 성공/`empty_after_lift` 종결점에서만 채워지는
        지상진실 측정값(`bolt_rise_m`, `gripper_width_m`) — grasp_result 로 나간다.
        `retries`(int): 호출자(pick_place_node.py `_pick()`)가 이미 계산해 넘기는
        가공된 값 — 여기서는 그대로 실어 보낼 뿐 재계산하지 않는다(호출자가
        _note_attempt_failed 의 증가/pop 순서를 알고 있어야만 정확히 계산되므로).
        """
        try:
            if not hasattr(self, '_cycle_result_pub'):
                from bin_picking.desktop_bridge import CYCLE_RESULT_TOPIC
                self._cycle_result_pub = self.create_publisher(String, CYCLE_RESULT_TOPIC, 10)
            # cycle_id 발급 — 시스템 전체에서 이 카운터 하나만 cycle_id 를 발급한다
            # (desktop_bridge 는 절대 스스로 cycle_id 를 지어내지 않고 echo 만 한다).
            self._cycle_seq += 1
            rec = String()
            rec.data = json.dumps({
                'bolt_id': bolt, 'success': bool(ok), 'reason': reason, 'dur': dur,
                'cycle_id': self._cycle_seq, 'origin': self._pick_origin,
                'retries': retries, 'metrics': metrics,
            })
            self._cycle_result_pub.publish(rec)
        except Exception:                       # noqa: BLE001
            pass
        if not self.USE_LEARNED_SELECTOR:
            return
        try:
            rec = {'t': round(time.time(), 3), 'bolt': bolt,
                   'epoch': self._pick_epoch, 'feat': feat,
                   'ok': int(bool(ok)), 'reason': reason,
                   'out': {'fraction': fraction, 'dur': dur, 'metrics': metrics}}
            os.makedirs(os.path.dirname(self.ATTEMPTS_PATH), exist_ok=True)
            with open(self.ATTEMPTS_PATH, 'a', encoding='utf-8') as f:
                f.write(json.dumps(rec) + '\n')
        except Exception:                     # noqa: BLE001
            pass
        if feat is None or self.selector is None or not self.selector.available:
            return
        try:
            self.selector.update(feat, bool(ok))
            self._attempt_count += 1
            if self._attempt_count % self.SELECTOR_REFIT_EVERY == 0:
                n, ready = self.selector.warm_start(
                    self.ATTEMPTS_PATH, epochs=self.WARM_START_EPOCHS)
                self.selector.save(self.MODEL_PATH)
                self.get_logger().info(
                    f'[학습선택기] 주기 재적합: 표본 {n}개, ready={ready}, 저장 완료')
        except Exception:                     # noqa: BLE001
            pass

    def _neighbors_within(self, pos, radius, target_id=None):
        """pos 반경 안의 (아직 안 집은) 볼트 id 목록. 대상 자신도 포함해 반환."""
        ids = []
        if target_id:
            ids.append(target_id)
        # ⚠ _bolt_sensed 를 직접 돌면 pose 브리지가 없는 폴백 모드에서 항상
        #   [target_id] 만 나와 '임시 제거'가 무력화된다 → _all_bolt_poses 경유.
        for bid, (p, _q) in self._all_bolt_poses().items():
            # 이미 옮긴/포기한 볼트도 '실물'은 존재하므로 이웃 판정에 포함한다
            if bid in ids:
                continue
            if math.dist(pos[:2], p[:2]) <= radius:
                ids.append(bid)
        return ids

    def _drop_slots(self):
        """놓는 통 안쪽 격자 슬롯(월드 xy). 벽에서 3cm 안쪽으로만 만든다."""
        cx, cy, _ = DROP_BIN_XYZ
        # 인셋 0.040: 벽까지 볼트 반길이(0.025) 빼고도 15mm 남아 림 걸침 방지
        rx = BIN_OUTER[0] / 2.0 - BIN_THICK - 0.040
        ry = BIN_OUTER[1] / 2.0 - BIN_THICK - 0.040
        nx = max(1, int(round(2 * rx / self.DROP_SLOT_DX)) + 1)
        ny = max(1, int(round(2 * ry / self.DROP_SLOT_DY)) + 1)
        slots = []
        for iy in range(ny):
            for ix in range(nx):
                x = cx - rx + ix * (2 * rx / max(1, nx - 1)) if nx > 1 else cx
                y = cy - ry + iy * (2 * ry / max(1, ny - 1)) if ny > 1 else cy
                slots.append((x, y))
        return slots

    def _free_drop_slot(self):
        """놓는 통에서 비어 있는 슬롯을 고른다.

        점유 판정: 슬롯 중심에서 SLOT_CLEAR_R 안에 (들고 있는 것 제외) 볼트가
        하나라도 있으면 '자리 참'. 빈 슬롯이 없으면 가장 여유로운 자리를 쓴다.
        """
        held = {self._attached_id, self._attached_src_id}
        occupied = [p[0][:2] for bid, p in self._all_bolt_poses().items()
                    if bid not in held]   # 폴백 모드에서도 같은 경로를 쓴다
        best, best_clear = None, -1.0
        for (sx, sy) in self._drop_slots():
            clear = min((math.dist((sx, sy), o) for o in occupied), default=9.9)
            if clear >= self.SLOT_CLEAR_R:
                return (sx, sy), clear, True
            if clear > best_clear:
                best, best_clear = (sx, sy), clear
        return best, best_clear, False

    def _finalize_selector(self):
        """[R4] 에피소드 종료 시 학습 선택기를 전체 재적합하고 저장한다.

        온라인 partial_fit 은 표본 순서에 민감하므로, 끝에서 누적 로그 전체로 한
        번 더 수렴시켜(warm_start) 저장하면 다음 실행이 더 나은 모델로 시작한다.
        실패해도 종료 흐름을 막지 않는다.
        """
        if self.selector is None or not self.selector.available:
            return
        try:
            n, ready = self.selector.warm_start(
                self.ATTEMPTS_PATH, epochs=self.WARM_START_EPOCHS)
            saved = self.selector.save(self.MODEL_PATH)
            self.get_logger().info(
                f'[학습선택기] 에피소드 종료 재적합: 표본 {n}개, ready={ready}, '
                f'저장 {"성공" if saved else "실패"} → {self.MODEL_PATH}')
        except Exception as exc:              # noqa: BLE001
            self.get_logger().warn(f'[학습선택기] 종료 재적합 실패: {exc!r}')
