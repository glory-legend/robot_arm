# 빈피킹 프로젝트 정밀 분석 · 개선 계획 (Claude 실행용 핸드오프)

> 작성: 2026-08-25  
> 분석 기준 커밋: `cc82c97`  
> 범위: `robotarm_main` 전체 — ROS2 Jazzy, Gazebo Harmonic, MoveIt2, 비전,
> 로봇 프로파일, 데스크톱 브리지/SDK, 실물 FR3 전환 준비  
> 이 문서는 **현황 설명서가 아니라 실행 백로그**다. Claude 또는 다른 작업자는
> 아래 작업 ID와 수용 기준을 그대로 구현 단위로 사용한다.
> 통신 계층 상세는 `docs/desktop_protocol_upgrade_plan.md`, PLC 없는 셀의 ROS 작업
> 오케스트레이션 상세는 `docs/ros_supervisor_design.md`를 함께 따른다.

---

## 1. 결론

현재 프로젝트는 다음 두 수준을 구분해서 평가해야 한다.

1. **분리 배치된 M8 볼트의 시뮬레이션 픽앤플레이스 데모**
   - FR3: 충분히 검증됨.
   - UR5e + Robotiq 2F-85: 등록/실행/비전은 검증됐고 파지는 부분 검증됨.
   - 로봇 프로파일, 파지 하강 검증, 실패 복구, PlanningScene 동기화가 강점이다.
2. **무더기(clutter) 빈피킹 → 데스크톱 랭킹 → 실물 FR3 운용 시스템**
   - 아직 중간 단계다.
   - 실제 장면은 겹치지 않는 5개 단일 레이어이고, 데스크톱 앱은 외부 팀 범위이며,
     E-STOP은 하드웨어 안전 기능이 아닌 소프트 플래그다.

전체 최종 목표 대비 현실적인 완성도는 **약 60~65%**다. `PROGRESS.md` 상단의
55% 평가는 비전 E2E, UR5e 개선, 커맨드 버스, SDK 추가 전 상태라 현행화가 필요하다.

---

## 2. 분석 시 직접 확인한 근거

### 2.1 실행 결과

| 검사 | 결과 |
|---|---|
| `cd src/bin_picking && python3 -m pytest test/ -q` | **182 passed**, 경고 2건 |
| `binpick_model validate fr3` | 오류 0, 경고 0 |
| `binpick_model validate ur5e_robotiq85` | 오류 0, 경고 0 |
| `colcon list` / 설치 패키지 조회 | 4개 패키지 정상 인식, 활성 모델 `fr3` |
| `python3 -m flake8 bin_picking test tools/desktop_sdk` | **1264건**, 실패 |
| Git 작업 트리 | clean |

경고 2건은 `tools/desktop_sdk/client.py`가 `websockets` legacy/deprecated API를
사용해서 발생했다. flake8 1264건 중 618건은 Mixin 분해 때 복제된 미사용 import라
즉시 동작 결함은 아니지만, 현재 lint를 CI 품질 게이트로 사용할 수 없는 상태다.

### 2.2 이번 분석에서 하지 않은 것

- Gazebo+MoveIt 전체 스택을 새로 띄운 라이브 파지는 수행하지 않았다.
- 성공률과 비전 오차는 `PROGRESS.md`에 기록된 기존 라이브 실측을 근거로 했다.
- 소스 동작은 변경하지 않았다.

---

## 3. 현재 시스템의 실제 데이터 흐름

```text
Gazebo RGB-D
  -> /bin_camera/points
  -> bolt_vision (crop -> voxel -> DBSCAN -> PCA)
  -> /next_bolt_pose
  -> IntegratedPickPlace
       -> 외부 pose 또는 자체 후보 선택
       -> 개구/벽/도달성 필터
       -> plan-only rollout + MoveIt 계획
       -> 접근 -> 하강 -> FK 도달 검증 -> 그리퍼 폐쇄
       -> PlanningScene attach -> 리프트 -> 볼트 상승량 검증
       -> 드롭 위치 계획 -> detach

Desktop SDK
  -> REST
  -> desktop_bridge
  -> /bin_picking/command 또는 /next_bolt_pose
  -> IntegratedPickPlace
  -> /bin_picking/cycle_result
  -> desktop_bridge
  -> WebSocket telemetry
```

중요한 단일 입구/출구:

- 볼트 pose: `sensing.py::_all_bolt_poses()`
- 파지 결과: `selection.py::_log_attempt()`
- 실패 코드 변환: `protocol.py::FAIL_REASON_MAP`
- 기체별 상수: `robot_profiles/data/*.yaml` -> `config.py::apply_profile()`

---

## 4. 즉시 수정해야 할 확인 결함

> **상태(2026-08-27): BP-C01·BP-C02·BP-C04a(RESET confirm)·BP-C03 처리됨.**
> C01/C02/C04a 는 코드 수정+단위테스트로 완결(pytest 193 passed). C04a 의
> "HTTP ACK vs robot ACK 분리"와 C04b(active goal cancel), C05(grasp/cycle 결과
> 분리)는 Gazebo 런타임 검증이 필요해 미착수. C03 은 아래 항목 참고(비전 제거로
> 주 실패모드 소멸).

### BP-C01 — `ALERT` 이벤트 대소문자 불일치 ✅ 완료(2026-08-27)

**근거**

- `desktop_bridge.py`는 `_envelope('ALERT', ...)`로 대문자를 발행한다.
- `desktop_sdk/client.py::_dispatch()`는 `mtype == 'alert'` 소문자만 처리한다.
- `docs/desktop_protocol.md` 카탈로그도 `alert` 소문자로 정의한다.

**영향**

SDK 사용자는 stale command, joint-state/TF stall, 모델 변경 경고를 `Alert` 객체로
받지 못하고 `'*'` raw listener에서만 우연히 볼 수 있다.

**권장 변경**

1. 와이어 표준을 문서대로 소문자 `alert`로 통일한다.
2. 브릿지의 모든 `'ALERT'` 발행을 `'alert'`로 변경한다.
3. SDK는 한 릴리스 동안 `'ALERT'`도 읽는 호환 분기를 둘지 결정한다. 아직 외부 앱
   본체가 없으므로 클린 브레이크를 택해도 된다.
4. `test_desktop_sdk.py`에 실제 브릿지와 같은 envelope를 `_dispatch()`하는 테스트를
   추가한다.

**수용 기준**

- `client.on('alert', cb)`가 브릿지에서 보낸 stale/TF 경고를 수신한다.
- 문서, 브릿지, SDK, mock client가 동일한 type 문자열을 사용한다.
- pytest 통과.

### BP-C02 — 리프트 실패가 `descend_fail`로 잘못 기록됨 ✅ 완료(2026-08-27)

**근거**

`pick_place_node.py`의 리프트 실행 실패 분기가 다음처럼 되어 있다.

```python
if not self.cartesian_viz_execute(lift, ...):
    return fail('리프트 실패', 'descend_fail')
```

그러나 `protocol.FAIL_REASON_MAP`, 문서 부록 D, 테스트는 `lift_fail`이 실제 발생한다고
가정한다. 현재 `lift_fail`은 매핑표에만 있고 실코드에서 방출되지 않는다.

**권장 변경**

- 해당 reason을 `lift_fail`로 수정한다.
- 단순 매핑표 테스트 외에 `_pick()`의 `fail(..., '<literal>')` reason 집합과
  `FAIL_REASON_MAP` 키를 비교하는 AST 기반 회귀 테스트를 추가한다.

**수용 기준**

- 리프트 계획/실행 실패 레코드의 내부 reason이 `lift_fail`이다.
- 실제 방출 reason이 매핑되지 않으면 테스트가 실패한다.

### BP-C03 — `/next_bolt_pose` 출처와 correlation이 소실됨 🟢 주 결함 해소(2026-08-27)

> **상태:** 로봇쪽 비전(`bolt_vision`) 제거로 `/next_bolt_pose` 발행자가
> `desktop_bridge` 하나뿐이 됐다 — "비전 pose 결과가 데스크톱 명령 RESULT 로
> 오상관"되는 주 실패모드가 **구조적으로 불가능**해졌다. 동시 PICK_BOLT 거부는
> 이미 구현돼 있고(`_pick_bolt_core`: `pick already in progress`), corr 은
> `_pending_pick` 단일 슬롯으로 왕복한다(cmd_id→RESULT.corr). 남은 옵션 A(전용
> typed corr 메시지)는 pick_place_node 변경 + Gazebo 검증이 필요한 견고화이며
> 가치가 낮아져 후순위. 아래 원문은 비전이 있던 시점의 분석으로 보존한다.

**근거**

- `bolt_vision`과 `desktop_bridge`가 모두 `/next_bolt_pose`에 `PoseStamped`를 발행한다.
- `PoseStamped`에는 명령 ID, `bolt_id`, origin이 없다.
- `pick_place_node`는 이 토픽에서 받은 모든 fresh pose를 `origin='DESKTOP'`으로 기록한다.
- 브릿지는 대기 중인 PICK_BOLT 하나와 다음 `origin='DESKTOP'` 결과를 연결한다.

**영향**

비전 노드와 데스크톱 명령을 동시에 켜면 비전 pose의 결과가 데스크톱 명령의 RESULT로
잘못 상관될 수 있다. 현재 desktop demo launch가 비전을 제외해서 숨겨진 문제다.

**권장 설계**

다음 중 A를 권장한다.

- **A. 전용 명령 메시지/토픽:** `/bin_picking/pick_request`에 JSON 또는 custom msg로
  `corr`, `bolt_id`, `origin`, `pose`, `stamp`, `deadline`을 함께 전달한다.
- B. 비전과 데스크톱 pose 토픽을 분리하고 콜백별로 origin을 고정한다.

브릿지에서 생성한 correlation ID가 결과까지 손실 없이 이동해야 한다. 최근 pose
한 칸을 덮어쓰는 방식 대신 bounded command queue 또는 명시적 busy rejection을 쓴다.

**수용 기준**

- vision publisher와 desktop publisher가 동시에 동작하는 통합 테스트에서 오상관 0건.
- RESULT의 `corr`가 로봇 노드까지 전달된 원본 ID와 같다.
- 두 번째 동시 PICK_BOLT는 명시적으로 거부되며 첫 명령 결과를 덮어쓰지 않는다.

### BP-C04 — ESTOP/RESET/PAUSE가 실제 의미보다 강하게 표현됨 🔶 부분(2026-08-27)

> **상태:** RESET `confirm=true` 시행(단기 권장 #3)만 완료(BP-C04a,
> `protocol.validate_command`, 단위테스트). 명령 ACK/robot ACK 분리(#2),
> active goal cancel(#4~#6), SOFT_STOP 상태기계는 Gazebo+MoveIt 런타임 검증이
> 필요해 미착수. ROS Supervisor 설계(`docs/ros_supervisor_design.md`)와 함께 진행.

**현재 동작**

- ESTOP: 브릿지 플래그 설정 + ROS 토픽 1회 발행 + 새 사이클 진입 차단.
- 실행 중인 MoveIt/컨트롤러 goal을 취소하지 않는다.
- 로봇 수신 ACK 없이 HTTP `accepted:true`를 반환한다.
- RESET은 `confirm=true`를 검증하지 않는다.
- PAUSE는 `_spin_sleep()`/`_spin_until()`에서만 정지하며 실행 중 trajectory는 계속 간다.
- START/STOP 등 일부 명령은 여전히 ACK만 반환하고 로봇에서 처리하지 않는다.

**단기 권장 변경**

1. UI/문서에서 현재 기능을 `SOFT_STOP` 또는 “다음 안전 지점 정지”로 명확히 표시한다.
2. command에 ID를 붙이고 robot ACK/REJECT 토픽을 추가한다.
3. RESET은 `confirm is True`일 때만 허용한다.
4. `ExecuteTrajectory`와 그리퍼 goal handle을 보관하고 ESTOP 시
   `cancel_goal_async()`를 호출한다.
5. cancel 완료 또는 제한시간 초과를 별도 상태로 보고한다.
6. 컨트롤러가 지원하면 cancel 시 감속 정지를 구성한다.

ROS 2 action은 장시간 작업의 취소/선점을 본래 기능으로 제공한다. Jazzy의
`joint_trajectory_controller`도 action goal 취소와 선택적 감속 정지를 지원한다.
참고: [ROS 2 Actions](https://docs.ros.org/en/rolling/Concepts/Basic/About-Actions.html),
[rclpy action API](https://docs.ros.org/en/ros2_packages/jazzy/api/rclpy/rclpy.action.html),
[Jazzy joint_trajectory_controller](https://control.ros.org/jazzy/doc/ros2_controllers/joint_trajectory_controller/doc/userdoc.html).

**실물 전환 게이트**

소프트웨어 ESTOP은 하드웨어 E-STOP/STO를 대체하지 않는다. 실물에서는 로봇 안전
컨트롤러와 독립된 안전회로가 최종 정지를 담당해야 한다.

**수용 기준**

- 실행 중 trajectory에서 stop 요청 후 goal cancel 결과가 관측된다.
- HTTP ACK와 robot ACK가 구분된다.
- 로봇 노드 미기동/토픽 유실 상태를 `accepted:true`로 최종 성공 처리하지 않는다.
- RESET 확인값 누락/false는 거부된다.
- 실물 모드에서는 하드웨어 안전 입력 미연결 시 자동운전을 시작하지 않는다.

### BP-C05 — PICK_BOLT 성공과 전체 운반 성공이 구분되지 않음

`_log_attempt()`와 RESULT는 리프트 성공 직후 발생한다. 이후 `_drop()`이 실패해도
데스크톱은 이미 `success:true`를 받는다. 이는 “파지 성공”으로는 맞지만 “볼트를 다른
통으로 옮겨라”라는 작업 완료 의미로는 부족하다.

**권장 변경**

- `grasp_result`: 리프트 기준 파지 결과 유지.
- `cycle_result`: place/detach까지 포함한 전체 작업 결과로 분리.
- PICK_BOLT 최종 RESULT가 어느 의미인지 계약에서 명시한다.
- 권장: 즉시 `ACK`, 중간 `grasp_result`, 최종 `RESULT{stage:'PLACE_COMPLETE'}`.

**수용 기준**

- 파지 성공 후 drop 실패를 데스크톱이 실패로 관측할 수 있다.
- 학습 선택기의 grasp label은 place 실패와 섞이지 않는다.

### BP-C06 — SDK 연결 준비와 재연결 신뢰성 부족

- `BinPickingClient.connect()`는 WS 연결 완료를 기다리지 않고 task만 생성한다.
- 연결 직후 즉시 PICK_BOLT를 보내면 RESULT listener 준비 전에 이벤트가 나갈 수 있다.
- WS가 끊긴 동안 발생한 이벤트는 서버에 replay/persistence가 없어 복구되지 않는다.
- 현재 `websockets` legacy API 경고가 발생한다.

**권장 변경**

- 최초 STATUS 수신까지 기다리는 `wait_ready(timeout)` 또는 connect barrier 추가.
- SDK가 준비되지 않은 상태의 `pick_bolt()`는 대기 또는 명시적 오류.
- 서버에 최근 중요 이벤트 ring buffer와 `last_seq` 기반 replay를 추가하거나,
  최소한 pending command status 조회 API를 둔다.
- 지원할 `websockets` 버전 범위를 requirements에 고정하고 최신 asyncio API로 전환.

통신 계층 전체의 clock/ACK/idempotency/replay/auth/lease 설계와 세부 구현 순서는
`docs/desktop_protocol_upgrade_plan.md`의 CP 작업 ID를 따른다. 이 절은 전체 프로젝트
관점의 요약이고, 프로토콜 계획서가 해당 영역의 상세 백로그다.

---

## 5. “진짜 빈피킹” 관점의 핵심 갭

### 5.1 현재 장면은 singulation 벤치마크다

`spawn_bolts.launch.py`는 볼트 5개를 3×3 슬롯에서 골라 겹치지 않는 단일 레이어로
배치한다. 현재 성공률은 이 장면의 성공률이지, 겹치고 가려진 무더기의 성공률이 아니다.

`bolt_vision.py`도 DBSCAN이 겹친 볼트를 하나로 합칠 수 있으며 현재 낱개 배치에
충분하다고 명시한다.

**개선 원칙:** 지금 장면을 없애지 말고 난이도 0 기준선으로 보존한다. 그 위에 별도
난이도를 추가해야 회귀와 연구 성능을 동시에 볼 수 있다.

### 5.2 벤치마크 시나리오 제안

| 레벨 | 장면 | 목적 |
|---|---|---|
| L0 | 현재 5개 단일 레이어, 비접촉 | 기본 동작 회귀 |
| L1 | 7~10개, 일부 접촉/교차, 낮은 적층 | 이웃/개구/축 분리 검증 |
| L2 | 15개 이상 랜덤 낙하, 다층 적층 | 실제 clutter clear-rate 검증 |
| L3 | 센서 노이즈·외참 오차·마찰/질량 랜덤화 | sim-to-real 강건성 |

각 레벨은 seed를 launch 인자로 받고 같은 seed를 재현할 수 있어야 한다. 모델별·레벨별
최소 100 episode를 자동 실행해 다음을 기록한다.

- grasp success rate
- place-complete success rate
- bin-clear rate와 남은 볼트 수
- picks per hour 또는 cycle time p50/p95
- 계획 시간 p50/p95, planner fallback 횟수
- perception recall/precision, pose error, confidence calibration
- collision abort, joint-limit, timeout, blacklist/deferred 분포
- recovery 후 성공률

---

## 6. 비전/자세 추정 업그레이드

### 6.1 1단계 — 기존 고전 비전의 다중 후보화

딥러닝보다 먼저 현재 코드를 다음처럼 확장한다.

1. 한 프레임에서 최상위 1개만 발행하지 말고 모든 cluster 후보를 구조화해 발행.
2. 후보마다 `pose`, `axis`, `extent`, `n_points`, PCA 고유값 비율, 경계/가림 점수,
   timestamp, covariance/confidence를 포함.
3. 동일 형상 볼트의 축 부호와 축 회전 대칭을 명시적으로 정규화.
4. 프레임 간 nearest-neighbor가 아니라 추적 ID와 confidence decay를 사용.
5. 낮은 confidence에서는 움직이지 말고 재관측 또는 다음 후보 선택.

M8 볼트는 축 방향/회전 대칭성이 있으므로 단순 quaternion 차이보다 형상 대칭을 고려한
오차가 적절하다. BOP benchmark는 이런 pose ambiguity를 고려하는 평가 방법을 제공한다.
참고: [BOP ECCV 2018 논문](https://openaccess.thecvf.com/content_ECCV_2018/html/Tomas_Hodan_PESTO_6D_Object_ECCV_2018_paper.html),
[BOP 공식 사이트](https://bop.felk.cvut.cz/home/).

### 6.2 2단계 — CAD 기반 pose estimator 비교

볼트 CAD/메시가 이미 있고 대상 종류가 알려져 있으므로, 범용 foundation model보다
먼저 CAD 기반 registration/pose estimator를 baseline과 비교하는 것이 비용 대비 좋다.

비교 인터페이스:

```text
PointCloud/RGB-D -> PoseCandidate[]
PoseCandidate = pose + covariance + score + symmetry_id + visible_fraction
```

후보 방법 중 하나로 FoundationPose를 별도 노드에서 실험할 수 있다. FoundationPose는
CAD가 있는 model-based 설정과 reference image 기반 설정을 모두 지원하지만 GPU·배포
복잡도가 크므로 기존 DBSCAN/PCA를 즉시 제거하지 않는다.
참고: [FoundationPose, CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/html/Wen_FoundationPose_Unified_6D_Pose_Estimation_and_Tracking_of_Novel_Objects_CVPR_2024_paper.html).

### 6.3 3단계 — 다중 시점/능동 재관측

가림이 심하거나 confidence가 낮으면 즉시 파지하지 않고 다음 중 하나를 수행한다.

- 고정 카메라를 하나 더 추가해 점군 융합.
- 손목 카메라를 안전 관측 pose로 이동.
- 후보별 예상 가시성, 이동비용, 충돌 가능성을 점수화해 next-best-view 선택.

단, 관측 이동은 새로운 충돌/시간 비용을 만들므로 L2 벤치마크에서 “바로 집기” 대비
clear-rate와 cycle time을 함께 비교해야 한다.

---

## 7. 파지 후보 생성과 선택 업그레이드

### 7.1 현재 중심점 1개에서 shaft 구간 후보들로 확장

현재는 볼트 중심과 축에서 사실상 하나의 대표 grasp를 만든다. 실제 볼트는 머리,
샤프트, 나사산, 가림 영역이 다르므로 다음 후보 축이 필요하다.

- 축 방향 파지 위치 여러 개
- 접근 tilt와 부호
- tool roll
- pre-grasp width
- finger contact가 shaft에 남는지
- 머리/벽/이웃 sweep clearance

후보 점수 예:

```text
score =
    w1 * perception_confidence
  + w2 * predicted_grasp_success
  + w3 * joint_margin
  + w4 * wall_and_neighbor_clearance
  - w5 * path_length
  - w6 * pose_uncertainty_sensitivity
  - w7 * prior_fail_count
```

각 hard gate를 통과한 후보만 학습 점수로 정렬한다. 학습기가 안전/충돌 gate를 우회하면
안 된다.

### 7.2 학습형 6D grasp는 비교 플러그인으로 도입

Contact-GraspNet은 depth point cloud에서 clutter 장면의 6-DoF parallel-jaw grasp
분포를 직접 생성하며 논문에서 structured clutter 실로봇 실험을 보고한다. 이 프로젝트의
그리퍼도 parallel-jaw이므로 연구 비교 대상으로 적합하다.
참고: [Contact-GraspNet 논문](https://arxiv.org/abs/2103.14127).

Dex-Net 2.0은 합성 depth/analytic grasp metric을 이용해 robust grasp success를
학습하는 대표 기준선이다. 현재 `attempts.jsonl`의 작은 온라인 SGD보다 uncertainty와
grasp geometry를 체계적으로 다루는 비교 기준이 된다.
참고: [Dex-Net 2.0 논문](https://goldberg.berkeley.edu/pubs/dex-net-2.0-Camera-Ready-RSS-2017.pdf).

**도입 원칙**

- `GraspCandidateProvider` 인터페이스 아래 `heuristic`, `contact_graspnet` 등을 둔다.
- 모델 출력은 반드시 현재 bin-wall/IK/PlanningScene gate를 다시 통과한다.
- 동일 seed 장면에서 success/clear-rate/latency/GPU 사용량을 비교한다.
- 학습 모델 부재나 추론 실패 시 기존 휴리스틱으로 폴백한다.

### 7.3 그리퍼 자체의 작업 적합성도 벤치마크 대상

UR5e 등록 과정에서 팔의 도달성보다 그리퍼 손끝/통 기하가 병목이었다. 알고리즘만
개선해도 기구적으로 들어가지 못하는 영역은 해결되지 않는다.

- FR3 hand, 2F-85, 소형 정밀 그리퍼를 동일 장면에서 비교.
- 볼트 재질이 허용하면 magnetic 또는 suction end-effector도 별도 실험 가능.
- 단, 도구 변경은 프로파일의 geometry/command/success sensing까지 함께 등록해야 한다.

---

## 8. 모션 계획/실행 업그레이드

### 8.1 MoveIt Task Constructor 파일럿

현재 `_pick()`/`_drop()`은 수동 상태기계 안에서 stage를 직접 연결한다. MoveIt Task
Constructor(MTC)는 pick/place를 `MoveTo`, `Connect`, `MoveRelative`, scene attach/
detach 같은 stage로 구성하고 여러 해를 비교하도록 설계돼 있다.
참고: [MoveIt2 공식 MTC pick/place tutorial](https://github.com/moveit/moveit2_tutorials/blob/main/doc/tutorials/pick_and_place_with_moveit_task_constructor/pick_and_place_with_moveit_task_constructor.rst),
[MTC 공식 문서](https://moveit.github.io/moveit_task_constructor/).

**권장:** 기존 노드를 즉시 재작성하지 않는다. `mtc_pick_place_experiment` 별도 실행
경로를 만들고 L0/L1에서 다음을 비교한다.

- 전체 계획 성공률
- 후보 간 solution cost
- 계획 시간
- recovery 표현력
- attach/detach 일관성

MTC가 명확히 우세할 때만 단계적으로 production 경로로 승격한다.

### 8.2 반복 구간 trajectory cache

Ready, drop-bin 접근, home 같은 구간은 반복성이 높다. MoveIt trajectory cache는
시작/목표/constraint가 충분히 가까운 요청의 기존 trajectory를 재사용해 계획을 생략할
수 있다. 동적 clutter 내부의 접근/하강에는 사용하지 말고 자유공간 반복 구간부터
측정한다.
참고: [MoveIt trajectory cache](https://github.com/moveit/moveit2/blob/main/moveit_ros/trajectory_cache/README.md).

### 8.3 동적 장면에는 Hybrid Planning을 후순위 실험

MoveIt Hybrid Planning은 느린 global planner와 빠른 local planner를 결합해 환경이나
목표 변화에 반응하고 필요 시 재계획한다. 볼트가 접근 중 움직이는 현 상태에서는 장기적
가치가 있지만, 먼저 pose uncertainty와 command cancellation을 해결해야 한다.
참고: [MoveIt Hybrid Planning 공식 문서](https://moveit.picknik.ai/main/doc/concepts/hybrid_planning/hybrid_planning.html).

---

## 9. 실물 FR3 전환 업그레이드

현재 “Gazebo `/joint_states`를 실물 데이터로 바꾸면 된다”는 설명은 목표 아키텍처로는
맞지만 실제 전환 작업량을 과소표현한다.

### 9.1 제거하거나 대체해야 할 Gazebo ground truth

현재 Gazebo pose가 담당하는 기능:

- 볼트 위치와 PlanningScene 갱신
- 접근 중 볼트 이동 감지
- nearest sensed bolt ID 매칭
- 리프트 후 볼트 상승량 기반 파지 성공 판정

실물 대체안:

- 다중 객체 vision tracker + covariance
- gripper width/current 또는 외력 기반 접촉 판정
- 리프트 전후 RGB-D 재관측
- 위 신호를 결합한 grasp verification state estimator

### 9.2 캘리브레이션과 불확실성 gate

- camera intrinsics/extrinsics와 hand-eye calibration 버전 관리
- TCP 및 손끝 collision geometry 실측
- bin frame registration과 재기동 후 drift 검사
- 오차 budget: vision, hand-eye, TCP, controller tracking을 분리 기록
- 합성 오차가 finger/bolt clearance를 넘으면 파지를 거부

### 9.3 sim-to-real randomization

L3 장면에서 최소 다음을 randomize한다.

- 볼트 질량/마찰/반발
- 카메라 depth noise, dropout, quantization
- 카메라 외참 오차
- 그리퍼 닫힘 지연과 controller tracking error
- bin pose/치수 공차
- 조명과 재질(금속 반사 포함)

평균 성공률만 보지 말고 worst seed와 p95 오차를 남긴다.

---

## 10. 코드 구조와 테스트 업그레이드

### 10.1 Mixin의 “파일 분리”를 실제 의존성 분리로 진행

`geometry.py`는 ROS 무의존이라고 문서화돼 있지만 실제로 `rclpy`, MoveIt 메시지,
PlanningScene 타입을 대량 import한다. `config.py`, `grasp_planning.py`, 다른 Mixin도
원본 공통 import 블록을 대부분 복제했다.

권장 순서:

1. `geometry.py`의 실제 사용 import만 남긴다.
2. quaternion 연산의 최소 의존을 명시한다.
3. ROS 메시지 입력을 tuple/dataclass 입력으로 바꾸고 adapter를 ROS 경계에 둔다.
4. `grasp_planning.py`도 같은 방식으로 순수화한다.
5. 그 뒤에만 Mixin을 collaborator 객체로 점진 전환할지 판단한다.

한 번에 전체 Mixin 구조를 갈아엎지 않는다. 파지 성공 경로 회귀 위험이 크다.

### 10.2 필요한 자동 테스트

| 테스트 | 목적 |
|---|---|
| geometry property tests | 회전행렬 직교성, 단위축, 선분거리 대칭성 |
| aperture/bin-wall fixtures | 벽/이웃/tilt 경계 회귀 |
| emitted reason AST test | `_pick()` reason과 `FAIL_REASON_MAP` 드리프트 방지 |
| bridge wire test | REST ACK -> ROS -> RESULT -> WS correlation |
| SDK dispatch test | 실제 type 대소문자와 payload 모델 검증 |
| launch_testing smoke | controller/readiness와 노드 종료 감지 |
| seeded Gazebo benchmark | L0~L3 성공률 회귀 |
| fault injection | TF 유실, joint-state stall, action timeout/cancel |

### 10.3 readiness 기반 launch

`desktop_integration_demo.launch.py`는 18초/23초 고정 TimerAction에 의존한다. 느린 머신,
WSLg, controller contention에서 불안정하다.

최종적으로는 다음 준비 상태를 확인한 뒤 다음 단계를 시작한다.

- Gazebo world/create service
- controller active 상태
- MoveGroup action/service
- `/joint_states` 수신
- bolt spawn/pose topics

TimerAction 인자는 비상 폴백으로만 유지한다.

### 10.4 의존성과 배포

현재 `setup.py install_requires`는 `setuptools`뿐이고 `package.xml`도 실제 import 전부를
표현하지 않는다. `numpy`, `scikit-learn`, `PyYAML`, `aiohttp`, `sensor_msgs_py`,
`ament_index_python`, `launch`, `launch_ros`, `xacro` 등을 실행 경로별로 감사한다.

`tools/desktop_sdk`는 소스 폴더일 뿐 독립 pip package metadata가 없다. 외부 데스크톱
팀에 전달하려면 별도 `pyproject.toml`, 버전, 지원 Python/websockets 범위, contract
test를 갖춘 패키지로 분리하는 것이 좋다.

---

## 11. 학습 데이터/평가 개선

현재 온라인 SGD는 작은 feature 집합에서 성공/실패를 학습하고 지속 저장한다. 좋은
실험 기반이지만 다음 보강이 필요하다.

- attempts schema에 명시적 `schema_version`, robot model, scene level, seed 추가.
- 과거 reason 개명 migration을 로더에서 공식 지원.
- grasp 성공과 place 성공 label 분리.
- scene/episode 단위 train/validation split으로 같은 장면 누출 방지.
- predicted probability의 calibration curve/Brier score 기록.
- 모델 승격 조건을 표본 수뿐 아니라 고정 validation seed 성능으로 결정.
- model artifact에 feature schema hash와 profile version 저장.
- 새 모델이 기준선보다 나쁘면 자동 rollback.

---

## 12. Claude용 실행 순서

### 작업 원칙

1. 각 작업 시작 전 루트 `AGENTS.md`와 대상 디렉터리의 `AGENTS.md`를 읽는다.
2. 아래 작업 ID 하나를 한 변경 단위로 처리한다.
3. correctness fix와 대형 리팩터링을 같은 변경에 섞지 않는다.
4. 데이터 계약 변경 시 `protocol.py`, `desktop_bridge.py`, SDK, mock client,
   `docs/desktop_protocol.md`를 함께 갱신한다.
   셀 상태기계/Action/cancel 변경은 `docs/ros_supervisor_design.md`도 함께 갱신한다.
5. 기체별 값은 `config.py`에 하드코딩하지 말고 robot profile에 둔다.
6. 파지 결과는 반드시 `_log_attempt()`, pose는 `_all_bolt_poses()` 경계를 지킨다.
7. 완료 주장에는 실행한 명령과 결과를 남긴다.

### 권장 작업 묶음

| 순서 | 작업 ID | 내용 | 선행 |
|---:|---|---|---|
| 1 | BP-C01 | alert type 통일 + SDK wire test | 없음 |
| 2 | BP-C02 | lift reason 수정 + emitted-reason test | 없음 |
| 3 | BP-C04a | RESET 검증, 명령 ACK/robot ACK 분리 | 없음 |
| 4 | BP-C04b | active action cancel + soft-stop 상태기계 | C04a |
| 5 | BP-C05 | grasp 결과와 place-complete 결과 분리 | C02 |
| 6 | BP-C03 | pick request correlation 전용 경로 | C05 |
| 7 | BP-C06 | SDK ready barrier/reconnect 정책 | C03 |
| 8 | BP-B01 | L0~L2 seeded scene/benchmark runner | C01~C03 |
| 9 | BP-V01 | PoseCandidate[] + confidence/추적 | B01 |
| 10 | BP-G01 | shaft 다중 grasp 후보/score | V01 |
| 11 | BP-M01 | MTC 별도 파일럿 비교 | B01 |
| 12 | BP-R01 | 실물 sensor/safety abstraction | C04b, V01 |

### 각 작업 공통 완료 조건

```bash
cd src/bin_picking
python3 -m pytest test/

cd ../..
source /opt/ros/jazzy/setup.zsh
colcon build --symlink-install
source install/setup.zsh
```

- 관련 프로파일 `binpick_model validate` 통과.
- 새 동작에 대한 단위 또는 통합 테스트 존재.
- 문서와 코드의 enum/필드/type이 일치.
- 기존 FR3 L0 기준선에 회귀 없음.
- 로봇/시뮬을 실행하지 못했다면 “미검증”을 명시하고 완료로 간주하지 않는다.

---

## 13. 우선순위 요약

### P0 — 다음 기능 개발 전에

- BP-C01 alert 대소문자
- BP-C02 lift reason
- BP-C04 RESET/stop 의미와 로봇 ACK
- BP-C03 pose 출처/correlation
- BP-C05 place 완료 결과

### P1 — 진짜 빈피킹 성능을 말하기 전에

- L0/L1/L2 seeded benchmark
- 다중 pose 후보와 confidence
- shaft 다중 grasp 후보
- clutter에서 perception/clear-rate 측정
- fault injection과 bridge wire test

### P2 — 실물 FR3 전에

- action cancel + 하드웨어 안전 연동
- hand-eye/TCP/bin calibration
- Gazebo ground-truth 제거
- grasp verification sensor fusion
- hardware bringup launch와 sim/real interface 분리
- L3 sim-to-real randomization

### P3 — 성능 최적화/연구 비교

- Contact-GraspNet 또는 CAD pose estimator 플러그인
- MTC 파일럿
- trajectory cache
- Hybrid Planning
- active perception/next-best-view

---

## 14. 최종 판단

이 프로젝트의 가장 강한 부분은 **시뮬레이션 파지 엔지니어링, 실패 복구,
로봇 프로파일 검증**이다. 가장 약한 부분은 **진짜 clutter 인식, 통합 프로토콜의
end-to-end 계약 검증, 정지 안전성, 실물에서 Gazebo ground truth를 대체할 관측 계층**이다.

따라서 다음 업그레이드의 성공 기준은 “새 AI 모델을 붙였다”가 아니라 다음이어야 한다.

> 동일한 seeded clutter 장면에서, 명령 상관관계와 안전 정지가 보장되고,
> perception uncertainty를 반영한 후보 중 실행 가능한 grasp를 선택해,
> place 완료까지의 성공률과 clear-rate를 재현 가능하게 높였는가?
