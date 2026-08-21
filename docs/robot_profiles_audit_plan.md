# 로봇 프로파일 — 공유상수 타깃 감사 계획 (실행용 핸드오프)
> (닉네임 전환 기능은 §4에서 보듯 불채택됨)

> 작성: 2026-08-12 세션. 이 문서 하나로 **새 세션에서 즉시 이어서 실행**할 수 있도록 썼다.
> 결정 근거·분류표·마이그레이션 목록·검증 방법·백로그가 모두 들어 있다.

---

## 0. 한 줄 요약

"팔마다 값이 공유돼서 복잡하다"는 통증의 **진짜 원인은 '공유 그 자체'가 아니라, 물리적으로
그리퍼/팔에 의존하는 소수 상수가 `config.py` 에 하드코딩돼 있던 것**이다. 전수 감사 결과 그
위험 집합은 **4~6개로 열거 가능**하다. 이것만 프로파일로 이관하면(대상물/작업셀/알고리즘
기본값은 단일 출처로 공유 유지) "깜짝 공유상수" 버그 부류가 사라진다.

> ⚠ 초안의 "닉네임(별칭) 전환" 기능은 **사용자 결정으로 불채택(2026-08-12)**. 전환은 정식 모델
> `name` 으로만 한다. 아래 §4 및 닉네임 언급은 모두 무시할 것(기록 보존용으로만 남김).

## 1. 배경 & 결정 (왜 '전부 비공유'가 아니라 '타깃 감사'인가)

- 현재 구조는 **이미 팔별 독립**이다. 각 팔 = 자기 YAML(`robot_profiles/data/<모델>.yaml`),
  전환 시 `apply_profile()` 이 `PickPlaceConfig` 클래스 속성에 주입. `binpick_model use <name>` 로 전환.
- 우리를 문 버그(2026-08-12): `GRASP_MAX_ABOVE`(적응형 하강 z_cap) 가 FR3 손끝(9.5mm) 기준으로
  하드코딩돼, 손끝이 긴 Robotiq(28.5mm)에서 적응형 하강 루프가 통째로 스킵됐다. → 이미 커밋
  `378d1bb` 에서 `grasp_floor_raise` 프로파일 값으로 우회. 하지만 `GRASP_MAX_ABOVE` 자체는 여전히
  FR3-튜닝 공유 상수로 남아 있다.
- **'전부 비공유 + 등록 시 사용자 전량 입력'은 채택하지 않는다**(객관적 판단):
  - 대상물 값(M8 볼트 반경·길이)·작업셀 값(통 치수·드롭 슬롯·바닥)은 팔이 바뀌어도 같다.
    팔마다 입력시키면 같은 값을 N번 입력 → "한 팔만 고치고 딴 팔 깜빡"하는 **새 불일치 버그**.
  - 순수 알고리즘 허용오차·스텝 수십 개까지 등록 시 입력시키면 등록 부담 폭증·입력 실수.
    복잡도가 사라지는 게 아니라 사용자에게 전가된다.
- **채택안**: 타깃 감사 → 팔/그리퍼 의존 상수만 프로파일로 이관(합리적 기본값 유지로 등록은
  가볍게). 대상물/작업셀/알고리즘 기본값은 단일 출처 공유 유지.

## 2. 감사 결과 — config.py 상수 분류

분류 부호: **①팔/그리퍼 의존** · **②대상물(M8 볼트)** · **③작업셀(통/바닥)** · **④순수 알고리즘/인프라**

### 2a. 이미 프로파일 주입됨(= 이미 팔별 독립, 건드릴 것 없음)
`apply_profile()` 이 arm/gripper/workspace 에서 꽂는 값:
- 팔: `PLANNING_GROUP, REFERENCE_FRAME, END_EFFECTOR_LINK, ARM_JOINTS, ARM_CONTROLLER,
  HOME_STATE, JOINT_LIMITS, LIMIT_MARGIN`
- 그리퍼: `GRIPPER_JOINT, GRIPPER_STATE_JOINTS, GRIPPER_ACTION(_TYPE), GRIPPER_CONTROLLER,
  GRIPPER_TOUCH_LINKS, GRIPPER_OPEN, GRIPPER_CLOSED, *_HALFWIDTH, TCP_TO_FINGERTIP,
  FINGER_HALF_W, FINGER_TIP_HALF_X, GRASP_MIN_OPEN, GRASP_PREGRASP_OPEN, APERTURE_STEP`
- 워크스페이스: `REACH_Y_MAX, REACH_X_FAR, APPROACH_HEIGHT, TILT_MIN_CENTER_Z,
  TILT_CANDIDATES_DEG, PLANNER_FALLBACK, DROP_Z, GRASP_FLOOR_RAISE`
- 신원/유도: `ROBOT_MODEL, ROBOT_PROFILE, GRASP_DETECT_MIN, GRASP_FLOOR_Z`

### 2b. ★ 위험 집합 — 팔/그리퍼 의존인데 아직 하드코딩(= 이관 대상)

| 상수 | 현재값 | 분류 | 왜 팔/그리퍼 의존인가 | 우선순위 |
|---|---|---|---|---|
| `GRASP_MAX_ABOVE` | 0.006 | ① | 적응형 하강 z_cap=bolt중심+이값. **손끝 길이**에 따라 유효성이 갈린다(FR3 floor 0.015 가 겨우 들어오게 튜닝된 값). Robotiq에서 루프 무효화 → `378d1bb`가 `grasp_floor_raise`로 우회했지만 이 상수 자체는 미이관. | **높음** |
| `GRASP_Z_TOL` | 0.003 | ①/④ | 실행후 FK z 허용오차. **컨트롤러 추종 정확도**(팔+구동계)에 민감. UR5e IK폴백 하강이 이 3mm 게이트에 아슬아슬(실측 +0.2~2.8mm). | 중 |
| `IK_SEED_JITTER` / `IK_SEED_SPREAD` | 1 / 1.2 | ① | 7축 여유자유도(팔꿈치 분기) 해소용. **UR5e는 6축**이라 여유자유도가 없어 의미가 다르다(seed jitter 무용). DOF에 따라 달라야 함. | 중 |
| `PICK_CLEAR_R` | 0.075 | ①/② | "손가락 반경(0.050)+이웃 볼트 반길이(0.025)". 앞 항이 **그리퍼 풋프린트** 성격 → 큰 그리퍼면 커져야. | 낮음-중 |
| `GRASP_FLOOR_CLEAR` | 0.0005 | ③/④ | 손끝이 바닥 위 남길 여유. 바닥(작업셀) 성격이나 그리퍼 정밀도와도 관련. 대체로 안전여유. | 낮음 |
| `GRASP_RAISE_STEP` | 0.002 | ④(경계) | 적응형 하강 재계획 간격. 대체로 일반값이나 그리퍼 기하와 상호작용. | 낮음 |

> 결론: **실질 위험은 `GRASP_MAX_ABOVE` 1개(높음) + `GRASP_Z_TOL`, `IK_SEED_*`(중) 정도**.
> 나머지는 경계/저위험. 전면 재작성이 아니라 이 목록만 다루면 된다.

### 2c. 공유 유지가 옳은 값(이관 금지 — 단일 출처)
- ② 대상물: `BOLT_SHAFT_RADIUS(0.004), GRASP_DETECT_MAX(0.009), SLOT_CLEAR_R`
- ③ 작업셀(`bolt_scene.py` 의 `BIN_XYZ/BIN_OUTER/BIN_THICK/DROP_BIN_XYZ` 에서 유도):
  `BIN_FLOOR_TOP, BIN_WALL_TOP, BOLT_REST_CENTER_Z, BIN_INNER_HALF, DROP_SLOT_DX/DY,
  APERTURE_SCAN_R, USE_PICK_BIN, PICK_BIN_FLOOR`
- ④ 알고리즘/인프라: `GRASP_MIN_FRACTION, MIN_FRACTION, ROLLOUT_*, DESCENT_STEP, CART_MAX_STEP,
  GRASP_SAFETY, SWEEP_SAFETY, APERTURE_SELF_TOL, POSE_REFRESH_TOL, TRIED_POS_TOL,
  MAX_PICK_RETRY, MAX_NO_PROGRESS, USE_LEARNED_SELECTOR, SELECTOR_REFIT_EVERY,
  WARM_START_EPOCHS, TILT_PRIOR_PENALTY, GRASP_SETTLE_SEC, EXT_POSE_WAIT, STEP_BY_STEP,
  REQUIRE_SENSING, 각종 TOPIC/TIMEOUT/COLOR/FRAME_DIAG/BOLT_ID_RE/APPROACH_DOWN`
- ~~죽은 코드: `GRASP_DEPTH_OFFSET(0.004, 레거시 미사용)`~~ → ✅ 제거 완료(2026-08-21).
  `config.py` 클래스 상수 + `test_config_profile_regression.py` 회귀 항목 삭제.

## 3. 마이그레이션 계획 (위험 집합 → 프로파일)

> **진행:** ✅ **전체 완료(2026-08-21).** `grasp:` 섹션 신설 + 위험집합 8개 필드 전부
> 이관됨. `schema.py`(`GraspSpec`) + `config.py`(`apply_profile()` 주입) +
> `fr3.yaml`/`ur5e_robotiq85.yaml`(값+유도주석) + `test_config_profile_regression.py`
> (FR3 리터럴 대조) 4층 모두 정합. 182 tests pass(FR3 불변 증명). 죽은 코드
> `GRASP_DEPTH_OFFSET` 제거 완료. UR5e 의 `z_tol`/`ik_seed_jitter`/`pick_clear_r`
> 는 FR3 기본값을 그대로 이관했고, 향후 라이브 A/B 로 UR5e 최적값을 확정할 것
> (YAML 에 `# 검토:` 주석으로 후보값 기재해 둠).

원칙: **FR3 완전 불변**. 새 프로파일 필드는 기본값을 FR3 현재값과 동일하게 두고, `apply_profile()`
가 주입. `grasp_floor_raise` 를 넣은 것과 동일한 패턴(`378d1bb` 참고).

권장 신설 섹션: 프로파일에 `grasp:` 섹션을 새로 두어 파지 알고리즘의 팔/그리퍼 의존 값을 모은다
(schema `GraspSpec`). 필드/기본값(FR3)/제안 UR5e값:

| 프로파일 필드(grasp.) | 기본값(FR3) | UR5e 제안 | 대응 상수 |
|---|---|---|---|
| `max_above` | 0.006 | 0.006 | `GRASP_MAX_ABOVE` |
| `z_tol` | 0.003 | 0.004(검토) | `GRASP_Z_TOL` |
| `raise_step` | 0.002 | 0.002 | `GRASP_RAISE_STEP` |
| `floor_clear` | 0.0005 | 0.0005 | `GRASP_FLOOR_CLEAR` |
| `ik_seed_jitter` | 1 | 0(6축, 검토) | `IK_SEED_JITTER` |
| `ik_seed_spread` | 1.2 | 1.2 | `IK_SEED_SPREAD` |
| `pick_clear_r` | 0.075 | 0.075 | `PICK_CLEAR_R` |

> `grasp_floor_raise` 는 현재 `workspace` 에 있는데, 이 `grasp:` 섹션으로 옮기는 것이 개념상 더
> 맞다(선택). 옮기면 schema/yaml/config 3곳 동기 수정 + 회귀 테스트 갱신 필요.

구현 순서(각 상수당): ①`schema.py` 에 필드+기본값+from_dict/to_dict → ②`config.py` 에서 클래스
기본값 제거 후 `apply_profile()` 주입으로 대체 → ③`fr3.yaml`/`ur5e_robotiq85.yaml` 에 값+유도주석
→ ④`test/test_config_profile_regression.py` 회귀 갱신 → ⑤`pytest`(161) + 라이브 A/B.

⚠ `binpick_model verify` 가 새 필드도 검증하도록 `validator.py` 확인.

## 4. 닉네임(별칭) 전환 기능 — ❌ 불채택 (2026-08-12 사용자 결정)

**이 절은 실행하지 않는다.** 사용자가 닉네임 전환을 원치 않기로 결정했다. 전환은 정식 모델
`name` 으로만 한다(`binpick_model use <name>`). 아래는 당초 설계였으나 참고용으로만 남긴다. ~~취소~~

목적: `binpick_model use ur5e_robotiq85` 대신 사용자가 정한 짧은 별칭으로 전환.
- schema: 프로파일 최상위에 `aliases: [..]`(또는 `nickname:`) 선택 필드. `display_name` 은 이미 있음.
- `robot_profiles/registry.py`(또는 `__init__`): `get(name)` / 활성화 시 **별칭→정식 name 해석**.
  충돌 검사(두 프로파일이 같은 별칭 금지)는 `validator` 또는 로드시.
- `model_cli.py`(`binpick_model`): `use <name|alias>` 별칭 허용, `list` 에 별칭 표시,
  `new` 에서 별칭 입력 프롬프트(선택).
- 활성 모델 저장은 항상 **정식 name** 으로(별칭은 입력 편의일 뿐). `~/.config/bin_picking/active_model`.
- 테스트: 별칭 해석 + 충돌 거부 유닛 테스트 추가.

리스크 낮음(순수 추가, 기존 name 경로 불변). 이관 작업과 독립이라 먼저 해도 됨.

## 5. 백로그 (이번 세션에서 발견/보류)

### 5a. ★ bolt_3 운반 모션 장벽 (step 1b, 하강과 별개) — ✅ 해결
- 증상: 전방으로 먼 바닥 볼트(예 (0.442,-0.045))는 `378d1bb` 로 **하강·파지는 성공**하나,
  그 far 자세(팔 전방-우측 최대 신전, J1≈-0.4)에서 **드롭 통(0.000,0.395)까지 운반 모션이
  5개 플래너 전부 실패**(`ToDropBin 자세 계획 실패`) → 잡고도 못 옮겨 detach.
- 성격: 하강이 아니라 **도달성/모션계획**. 리프트 후 곧장 큰 스윙을 RRT가 못 푼다.
- ✅ **해결(커밋 `2f71e13`)**: 후보 해법 (1) 채택 — 드롭 통 이동을 ready 경유로 분할.

### 5b. step 2 — `tilt_min_center_z` 실측화 — ✅ 수치유도 완료
- ~~현재 UR5e 값 0.042 는 "FR3의 3배" heuristic(0.009 + 11mm×3). 미실측.~~
- ✅ `tools/derive_tilt_min_center_z.py` 로 수치유도 완료 → UR5e 0.035 적용(yaml 반영 완료).
- 정밀 유도 방법(이 세션에서 설계): 코드의 실제 tool 프레임(`geometry._grasp_frame`:
  `z_tool=approach, y_tool=z_tool×axis, x_tool=y_tool×z_tool`) + `_rotate_about`(로드리게스)로,
  기울임 θ에서 **최저 손끝 z**를 수치 계산 → floor(0) 위에 남는 최소 볼트중심 c 를 구한다.
  - tiltable 볼트는 `c ≥ tilt_min > GRASP_FLOOR_Z` 라 TCP 가 볼트중심 높이 c 에 놓임.
  - 손끝 최저점 = c + Σ(오프셋·world_z). 주항: 손끝이 approach축 따라 `tcp_to_fingertip` 아래 +
    **가로 반개구(≈pregrasp_open)** 가 기울일 때 아래로 스윙(y_tool.z 성분).
  - 볼트 방위 φ·기울임 부호 스윕해 **최악값** 채택. FR3 파라미터로 같은 모델 돌려 **0.020 재현
    여부로 검증**한 뒤 UR5e(tcp_to_fingertip=0.0285) 적용.
- 산출물: 유도된 값으로 ur5e yaml 갱신 + 유도주석. (계산 스크립트는 순수 numpy로 작성 가능.)

### 5c. step 3 — 비전 엔드투엔드 검증 (✅ 완료)
- 현 4/5 는 대체로 Gazebo ground-truth pose(`/model/bolt_i/pose` 브리지) 기반. **카메라→검출→
  좌표변환** 앞단이 UR5e 조립에서 끝까지 도는지 미검증.
- UR5e 는 base_frame/카메라 장착이 달라 **TF 체인(camera_frame→base_link)**이 FR3와 다르다.
- ✅ **코드 수정 완료 (2026-08-18):**
  - `bolt_vision.py`: 하드코딩 `fr3_link0` → `self.BASE_FRAME`(프로파일 동적 참조)으로 수정.
  - `bolt_vision.py`: BIN crop 상수 4개를 `bolt_scene.py` 에서 유도(단일 출처 보장).
  - `vision_verify.py` 신설: 비전 추정 vs Gazebo 정답 대조 노드. 위치(mm)/축(°) 오차를
    실시간 로그 + 종료 시 요약 통계(평균/중앙/최대/표준편차) 출력. `ros2 run bin_picking
    vision_verify [--duration 30]` 으로 실행.
  - **카메라 URDF 확인**: UR5e xacro 에 이미 FR3 와 동일 배치(eye-to-hand, base 고정,
    (0.40,0,0.60), optical_frame 규약)의 rgbd_camera 포함. 토픽 이름도 동일(`/bin_camera/*`).
  - **TF 체인 확인**: `bolt_vision` 은 `tf2.lookup_transform(BASE_FRAME, cloud_frame)` 으로
    동적 변환. BASE_FRAME 은 프로파일에서 읽으므로 UR5e(`base_link`)/FR3(`fr3_link0`) 모두
    코드 변경 없이 동작.
  - 165 tests pass (회귀 없음).
- ✅ **라이브 검증 완료 (2026-08-18, FR3):**
  - **발견 및 수정**: Gazebo Harmonic 의 `optical_frame_id` 가 PointCloud2 좌표를 실제로
    회전시키지 않고 헤더 frame_id 만 바꾸는 버그 발견. camera_link 프레임으로 데이터가
    나오는데 camera_optical_link 로 표기돼 TF 불일치 발생. 양쪽 URDF(FR3·UR5e)에서
    `optical_frame_id` 제거해 해결.
  - **발견 및 수정**: XY crop 마진(+20mm)이 빈 테두리 상면 포인트를 포함해 DBSCAN 이
    빈 림을 '가장 큰 클러스터'로 선택하는 문제 발견. 내벽 안쪽으로 10mm 인셋하는
    `_CROP_XY_INSET` 으로 교체해 해결.
  - **결과** (FR3, 30초, 204 샘플):
    - 위치 오차: 평균 **7.8mm** / 중앙 7.9 / 최대 7.9 / 표준편차 0.4
    - 축 오차: 평균 **1.2°** / 중앙 1.2 / 최대 1.2 / 표준편차 0.1
    - 5개 볼트 전부 검출, 2개(bolt_2·bolt_4) 선택 매칭 확인
    - 위치 오차의 주 원인은 Z 방향 4mm 편향(카메라가 상면만 보므로 중심 대비 상향).
      XY 정밀도는 파지 허용 범위 내.
  - 165 tests pass (회귀 없음).
  - ✅ **UR5e 라이브 결과** (30초, 195 샘플):
    - bolt_3: 194건 — 위치 **6.1mm** / 축 **1.8°** (안정)
    - bolt_1: 1건 — 56.7mm (초기 GT 구독 타이밍 이상치)
    - BASE_FRAME 이 `base_link` 로 자동 전환 확인, TF 체인 정상.
    - FR3 결과(7.8mm/1.2°)와 동등 — 양쪽 모델 모두 파지 허용 범위 내.

## 6. 완료 상태 요약 (2026-08-21 기준)

| 항목 | 상태 |
|---|---|
| §3 위험집합 8개 상수 이관 | ✅ 전체 완료 |
| §2c 죽은 코드 GRASP_DEPTH_OFFSET | ✅ 제거 완료 |
| §5a 운반 모션 장벽 | ✅ ready 경유로 해결 |
| §5b tilt_min_center_z 수치유도 | ✅ 0.035 적용 (라이브 미실측) |
| §5c 비전 E2E 검증 | ✅ 양쪽 모델 완료 |
| UR5e 라이브 A/B 튜닝 (`z_tol`/`ik_seed_jitter`/`pick_clear_r`) | 🔲 YAML `# 검토:` 에 후보 기재, 향후 진행 |

테스트: 182 passed (FR3 불변 증명).

## 7. 라이브 재현 방법 (이 세션에서 확립 — 헤드리스)

```bash
# 0) 활성 모델
env -i HOME=$HOME bash -lc 'source /opt/ros/jazzy/setup.bash; source install/setup.bash; \
  ros2 run bin_picking binpick_model use ur5e_robotiq85'
# 1) 스택(헤드리스: gz server-only + RViz off)  — 심링크 install 이라 재빌드 불필요
env -i HOME=$HOME bash -lc 'source /opt/ros/jazzy/setup.bash; source install/setup.bash; \
  ros2 launch bin_picking franka_gazebo_moveit.launch.py rviz:=false \
  gz_args:="-s -r $(pwd)/install/bin_picking/share/bin_picking/worlds/robot_view.sdf"'
# 컨트롤러 3기 active + /move_group 뜰 때까지 대기 (ros2 control list_controllers)
# 2) 볼트 스폰 (매번 새 랜덤; 동일배치 A/B가 필요하면 spawn_bolts 를 임시로 재사용패치)
env -i HOME=$HOME bash -lc 'source ...; ros2 launch bin_picking spawn_bolts.launch.py'
# 3) 자동 픽플레이스 (로그는 ~/pick_place_logs/latest.log 로 tee)
env -i HOME=$HOME bash -lc 'source ...; ros2 run bin_picking integrated_pick_place --auto'
```
- **동일배치 A/B**: `spawn_bolts.launch.py` 는 매 실행 `/tmp/bolt_layout.json` 을 새로 쓴다.
  같은 배치로 수정 전/후를 비교하려면, 그 파일을 백업해 두고 spawn 이 재생성 대신 재사용하도록
  임시 패치(env 게이트)한 뒤 검증하고 **되돌린다**(이번 세션에 그렇게 검증함).
- 정리: `gz sim`/`move_group`/`parameter_bridge`/`robot_state_publisher`/`integrated_pick_place`
  PID 를 `kill -9`. `pgrep -f "gz sim"` 자기 명령줄 오탐 주의(ps 로 실확인).
- **끝나면 활성 모델을 fr3 로 복원**해야 `pytest` 가 161 통과(bolt_scene.REFERENCE_FRAME 는
  import 시 활성모델로 스냅샷되어, ur5e 활성 상태면 `test_bolt_scene_reference_frame_matches` 실패).

## 8. 이번 세션 커밋 요약(참고)
- `378d1bb` fix: UR5e 바닥 볼트 적응형 하강 부활(`grasp_floor_raise`, FR3 불변, 161 pass).
- `fabfcb9` fix: UR5e 파지 튜닝(개구 단위버그·ready·플래너폴백·드롭 클리어런스, 0/5→4/5).
