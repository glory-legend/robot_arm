# 프로젝트 진행 로그 & 로드맵

FR3 M8 볼트 빈피킹 — **컴퓨터비전 → 데스크톱앱 → 로봇암** 파이프라인.
지금은 Gazebo 시뮬로 리허설, 최종 목표는 **실물 FR3 로봇암 적용**.

> 범례: ✅ 완료 · 🔶 진행/부분 · ⬜ 예정
> 갱신: 2026-09-09

---

## 🎯 최종 목표

데스크톱앱이 카메라 포인트클라우드로 **가장 집기 좋은 볼트를 랭킹→1순위 선택**해 로봇에 좌표를 주고,
로봇은 그 좌표로 **집어 옮기며**, 데스크톱은 로봇 움직임을 **실시간 디지털 섀도우**로 감시·개입한다.
시뮬로 완성한 뒤 **데이터 소스만 스왑해 실물로 전환**한다.

## 📍 현재 단계 (한눈에)

```
[시뮬 파지 ✅] → [볼트 인식 = 데스크톱앱 몫(별도 팀) ⬜] → [데스크톱 데이터계약 ✅기획]
    → [통신방식 ✅구현] → [로봇측 연동 IF 🔶] → [데스크톱앱 구현 ⬜(별도 팀)] → [실물 전환 ⬜]
```

> **2026-08-27 아키텍처 정리:** 로봇쪽 테스트용 비전(`bolt_vision`·`vision_verify`·
> 카메라 URDF/월드/브릿지)을 **제거**했다. 볼트 인식은 데스크톱앱(별도 팀)이 담당하는
> 별개 파이프라인이고, 로봇은 데스크톱이 보낸 좌표(`PICK_BOLT`→`/next_bolt_pose`)를
> 받아 집기만 한다 — 로봇쪽 카메라는 데스크톱앱 없이 E2E를 돌려보려던 비계였다.
> `/next_bolt_pose` 입력 통로와 Gazebo pose 폴백은 정식 인터페이스로 유지.

**요약:** FR3/UR5e 시뮬 파지 기반과 양 모델의 비전 E2E 검증, 로봇 프로파일 등록·전환,
데스크톱↔로봇 REST+WebSocket 통신 및 Python SDK까지 구현됐다. 다만 현재 성공률의
기준 장면은 실제 무더기가 아니라 겹치지 않는 5개 단일 레이어이며, 데스크톱 명령 중
일부만 커맨드 버스로 로봇 동작에 연결돼 있다. 다음 핵심은 통신 계약 결함/소프트 정지
semantics 수정, seeded clutter 벤치마크, 다중 pose/grasp 후보, 실물 센싱·안전 계층이다.
상세 실행 백로그는 `docs/bin_picking_analysis_and_upgrade_plan.md`. 전체 목표 대비
대략 **60~65% 지점**.

---

## ✅ 완료한 태스크

### 3단 밀집·혼합 회전 적재 (2026-09-09)
- 사용자 요청: 같은 방향으로 펼쳐 놓지 않고 3단에 더 촘촘하게 적재.
- ✅ `dense` 전략: 모서리 양방향 정렬·0/90° 회전·128개 배치 후보 비교,
  박스 간 3 mm 여유, 다중 하부 상면 지지·누적 하중·최대 3단 제한.
- ✅ 기본 36개 전량 기하 배치, 회전 박스 12개, 적재 외곽 높이 300 mm,
  해당 높이 기준 부피 활용률 70.93%. 박스 치수·질량은 기존과 동일하다.
- 같은 36개 입력의 이전 compact는 4단·400 mm·53.20%였고, 새 배치는 높이를 25% 줄였다.
- ✅ 실행 전 수직 하강 검증·손목 대안 자세 탐색, 지지물별 접촉 허용,
  기존 적재 높이에 따른 운반 높이 및 배치 후 방향 확인.
- 🔶 Gazebo 전체 실행 검증 진행 중. 기하 배치 성공을 로봇 운반 성공으로 세지 않는다.
- 기존 6개 모션은 `strategy:=compact box_count:=6`으로 실행.

### 팔레타이징 실제 운반·흡착 툴·작업셀 (2026-09-09)
- 사용자 후속 요청에 따라 실제 모션과 그리퍼 교체를 우선 구현했다.
- ✅ FR3 평행 그리퍼 제거, 4컵 진공 툴·`vacuum_tcp`·SRDF/MoveIt 체인 구성.
  Franka 벤더 파일과 기본 빈피킹 프로파일은 보존.
- ✅ MoveIt 궤적 실행 + Gazebo DetachableJoint 물리 부착/해제.
  상면 접촉 조건 → 상승 확인 → 운반 → 해제 → 최종 위치 확인이 모두 지나야 완료 처리.
- ✅ 실행용 박스 간 12 mm 여유, 롤러 컨베이어·목재 팔레트·테이프/바코드 표시,
  전용 Gazebo/RViz 설정, `/palletizing/status` 및 소프트 중단 요청.
- ✅ Headless **3/3**, GUI **6/6** 운반 완료. Python **240 passed**, 전체 **5패키지 빌드**.
- ✅ 최종 검사: Gazebo 박스 pose 6개·MoveIt 객체 8개 대조, 잔여 부착 없음, 오류 없음.
- 기본 실행: `ros2 launch bin_picking palletizing_demo.launch.py`.
  정적 장면은 `mode:=preview box_count:=12`로 분리했다.
- 압력/누설 모델·실제 컨베이어 이송·바코드 판독·온라인 버퍼 정책은 아직 미구현이다.
  세부 범위: `docs/palletizing_implementation.md`.

### 바코드 기반 혼합 박스 팔레타이징 — PDF 1단계 (2026-09-09)
- **기준 정정:** 사용자 지정 PDF 「실시간 바코드 기반 온라인 혼합 박스 팔레타이징
  시스템」 §12를 따른다. 특허용 가상 회수 T0/T3 및 별도 M1~M4 계획과 구분한다.
- ✅ 박스 3종·600×400 mm 출고 팔레트 1개·오프라인 배치 구현.
  0/90° 회전, 경계·겹침·단일 하부 박스의 전체 지지·누적 상부하중을 검사한다.
- ✅ `palletizing_plan` CLI, `/packing/plan` JSON, 공통 장면 데이터에서 생성한
  SDF, 순차 스폰 런치, Gazebo 실측 자세의 MoveIt 충돌체 동기화 구현.
- ✅ 기준선 `greedy`와 개선 `compact` 비교. 여러 배치 우선순위의 결과를 비교하여
  누락·적재 높이·질량의 높이 모멘트를 줄인다. 기본값은 `compact`.
  90개 사례에서 12박스 평균 높이 136→100 mm, 24박스 283.3→213.3 mm,
  36박스 평균 미배치 0.77→0개. 계산 시간 증가를 함께 기록했다.
- ✅ `python3 -m pytest test/ -q`: **235 passed**. 팔레타이징 신규 30개 포함.
  `colcon build --symlink-install`: **5 packages finished**.
- 기본 seed 20260909: 12/12 배치, 거부 0, 사용 높이 100 mm(Greedy 160 mm).
- ✅ Headless Gazebo/MoveIt에서 기본 compact 장면 검증 완료:
  박스 pose 12개·충돌체 13개, 계획 위치 오차 최대 0.001 mm 미만,
  동기화 오차 0 mm. GUI 화면·로봇 모션 검증은 포함하지 않는다.
  `ros_gz_sim create`의 기본 pose가 SDF 내부 pose를 덮어쓰는 문제도 확인해
  스폰 `-x/-y/-z`를 공통 데이터로 명시하도록 수정했다.
- 기하 미리보기 실행: `ros2 launch bin_picking palletizing_demo.launch.py mode:=preview box_count:=12`.
  자세한 사용법·검증 범위: **`docs/palletizing_implementation.md`**.
- 이 단계의 장면은 계산된 최종 배치를 스폰하는 기하 미리보기다.
  로봇 모션은 위의 후속 작업에서 구현했으며, PDF 2단계 바코드·목적지·출고 순서와
  온라인 도착·버퍼·회수는 후속 구현 대상이다.

### 통신 계약 P0 정리 — 검증가능 슬라이스 (2026-08-27)
- **범위:** `docs/bin_picking_analysis_and_upgrade_plan.md` 의 P0 중, Gazebo 없이
  단위테스트로 완전 검증되는 것만 처리(사용자 결정).
- ✅ **BP-C01** alert 대소문자 통일(`ALERT`→`alert`) — 브릿지 4곳 + SDK wire 테스트.
  이전엔 SDK `on('alert')` 가 stale/TF/모델변경 경고를 전혀 못 받았다.
- ✅ **BP-C02** 리프트 실패 reason 오기록 수정(`descend_fail`→`lift_fail`) +
  AST 회귀 테스트(방출 reason ↔ `FAIL_REASON_MAP` 양방향 일치, 죽은 키 금지).
- ✅ **BP-C04a(부분)** RESET `confirm=true` 시행 — `protocol.validate_command`
  순수 함수 + 브릿지 게이트 + 문서 각주. confirm 없으면 estop 안 풀림.
- 🟢 **BP-C03** 주 결함 해소 — 비전 제거로 `/next_bolt_pose` 발행자가 브릿지
  하나뿐이라 오상관 구조적 불가. 동시 PICK_BOLT 거부·corr 왕복은 기구현.
- **검증:** `pytest test/` → **193 passed**(기존 182 + 신규 11).
- **미착수(Gazebo 런타임 필요):** BP-C04a ACK 분리, BP-C04b active goal cancel/
  soft-stop, BP-C05 grasp/cycle 결과 분리. → 시뮬 세션에서 이어서.

### 두 번째 팔 등록 완료 — UR5e + Robotiq 2F-85 (2026-08-10)
- **목표:** 등록 계층이 실제로 벤더 중립인지, **다른 제조사 팔을 올릴 수 있는지** 증명.
- **결과 — 등록·전환·로드 전 과정 동작:**
  - `binpick_model verify ur5e_robotiq85` → **7개 검사층 전부 통과**(static/files/
    urdf/srdf/planners/joint_states/controllers), 오류 0.
  - `binpick_model use ur5e_robotiq85` → 활성 모델 저장.
  - **`robot_model` 인자 없이** 런치 → UR5e 가 뜸(`status=verified` 표시),
    `ur_arm_controller`/`robotiq_gripper_controller`/`joint_state_broadcaster` 활성.
    컨트롤러 이름이 FR3 와 완전히 다른데 런치에는 어느 쪽도 하드코딩돼 있지 않다.
- **UR5e 를 붙이며 드러난 프랑카 가정(전부 수정):** 그리퍼 개폐 방향(2F-85 는
  0 rad=만개, 0.79=폐쇄로 **반대**), 관절값/물리개구 단위 혼용, 툴 프레임 축 규약,
  벤더 커스텀 YAML 태그(`!degrees`), `planner_configs` 부재, `move_gripper` 로그의
  rad×1000→"mm" 오표기.
- **`status` 의미 정정:** `verified` 를 '파지 성공'이 아니라 **'verify 통과(값이 실제
  모델/런타임과 대조됨)'** 로 재정의하고, 작업 성능은 `task_validated` 로 분리했다.
  둘을 한 축에 묶으면 "안전하게 로드는 되지만 이 작업엔 안 맞는 팔"을 표현할 수
  없다 — UR5e+2F-85 가 정확히 그 상태다. 전환 게이트는 `status` 만 본다.
- **`verify --promote` 추가:** 0 오류 통과 시에만 `status` 를 올린다(유일한 승격
  경로). 주석 보존을 위해 `status:` 한 줄만 치환하고, 빌드 산출물이면 거부한다.
- **워크스페이스 실측 도구(`measure_workspace`) 추가.** FR3 값을 베껴 뒀던 것이
  **부당한 제약**이었음이 드러났다 — `reach_y_max` 0.063(실측 **0.095**),
  `reach_x_far` 0.45(실측 **0.515**). 통의 상당 부분을 이유 없이 배제하고 있었다.
- **남은 것 ⬜ — 파지는 실패(0/5).** 원인은 등록 계층이나 도달성이 아니라 **그리퍼
  적합성**이다: 2F-85 손끝 두께 31.2mm(프랑카 핸드 4.4mm의 **7.1배**)라 통 안에서
  개구 확보가 안 된다. 통 기하로 계산하면 집을 수 있는 영역이 바닥 면적의 32%
  (FR3 는 70%). 이 작업에는 소형 정밀 그리퍼(예: Robotiq Hand-E)가 맞다 —
  `robotiq_description` 이 2F-85 만 제공하므로 에셋 확보가 선행돼야 한다.

### ⚠ WSLg + ogre2 렌더러 → 컨트롤러 스포너 연쇄 실패 (2026-08-10)
- **증상:** Gazebo GUI 로 데모를 띄우면 `joint_state_broadcaster`/`fr3_arm_controller`/
  `fr3_gripper_controller` 스포너가 **전부** 죽는다. 로그에는
  `Could not successfully call service /controller_manager/switch_controller after 3 attempts`,
  `Failed to acquire lock in 20 seconds` 가 반복되고, 이어서 `integrated_pick_place` 가
  `moveit_io.wait_for_ready()` 에서 예외로 종료된다.
- **함정:** 이게 코드 버그처럼 보인다. 하지만 **`/clock` 은 553Hz 로 정상 발행**되고
  있어서 "시뮬은 멀쩡한데 왜 서비스만 안 되지"로 한참 헤맨다.
- **근본 원인:** WSLg 는 GPU 가속 없이 소프트웨어 렌더링을 한다. 기본 렌더러(**ogre2**)
  로 GUI 를 띄우면 `gz sim gui` 가 **CPU 277%**(약 3코어)를 먹고, gz 서버 플러그인
  안에서 도는 `controller_manager` 의 서비스 콜백이 굶어 10초 타임아웃을 넘긴다.
  스포너 3개가 락을 두고 경합하면서 연쇄 실패한다.
- **해결:** 가벼운 렌더러로 바꾼다 — `gz_args` 에 `--render-engine ogre` 추가.
  ```bash
  ros2 launch bin_picking desktop_integration_demo.launch.py \
    gz_args:='-r --render-engine ogre <워크스페이스>/install/bin_picking/share/bin_picking/worlds/robot_view.sdf' \
    bolts_delay:=30.0 apps_delay:=45.0
  ```
  바꾼 뒤 컨트롤러 3개가 모두 정상 활성화됐다. 헤드리스(`-s`)로 돌 때는 애초에
  안 나는 문제라, GUI 를 켤 때만 해당한다.
- **구분:** 2026-08-06 의 "Gazebo 서버 중복 기동" 과는 **별개 원인**이다. 그쪽은 서버가
  둘 떠서 났고, 이번 건은 서버 하나에 GUI 가 자원을 뺏는 것이다.

### 리팩터링 후 실동작 검증 (2026-08-10)
- 모델 등록/전환 계층을 넣은 뒤 **실제 Gazebo 데모로 회귀 확인**. 볼트 5개 중 3개
  파지·운반 성공, 2개는 서로 인접해 개구 확보 실패로 보류(블랙리스트 0).
- 전 구간 달성률 100%(접근/하강/리프트/이동/놓기). 특히 **하강 실측 TCP z=0.0150 /
  목표 0.0150, 초과 +0.0mm** — 이 값은 `apply_profile()` 이 프로파일의
  `TCP_TO_FINGERTIP` 에서 재계산해 꽂은 `GRASP_FLOOR_Z` 다. 유도 상수 재계산을
  빼먹었다면 여기서 어긋났을 것이므로, "이름만 새 로봇이고 물리는 옛 로봇" 버그가
  없다는 실동작 증거가 된다.
- 학습 선택기 표본 550 → 553 재적합·저장 확인.

### 로봇팔 모델 등록/전환 계층 (2026-08-10)
- **목표:** 다른 제조사 로봇팔로 갈아끼울 수 있게 하되, **전환 후에도 기능은 완전히
  동일**해야 한다. 사용자 정정으로 무게중심을 "전환"이 아니라 **"등록"** 으로 옮겼다 —
  그리퍼를 비롯해 업체마다 다른 값은 자동 추론이 불가능하고 사람이 실측해 넣어야
  하므로, 핵심 기능은 그 수기 입력을 빠짐없이 받고 **틀리면 시끄럽게 알리는** 것이다.
- **왜 FR3 가 박혀 있었나(근본원인):** 7개 층에 서로 다른 성격으로 흩어져 있었다 —
  ① 이름 규약 ② `config.py` 클래스 상수(임포트 시점 고정 + `desktop_bridge` 가
  모듈 최상단에서 복사) ③ 런치 리터럴 ④ 실측 유도 물리상수(TCP↔손끝 9.5mm 등)
  ⑤ 제어 인터페이스 규약(FollowJointTrajectory + 선형 관절 전제) ⑥ 툴 프레임 규약
  ⑦ 벤더 자산(메시가 fr3 뿐). 상위 `franka_description` 은 이미 `robot_type` 으로
  파라미터화돼 있었는데, **우리 코드가 그 결과 문자열을 최종형태로 복사해 넣어**
  파라미터화를 무너뜨린 것이 근본원인이었다.
- **결과:**
  - `robot_profiles/` 신설 — 스키마(무엇을 채워야 하는가) + 레지스트리(어디에 적힌
    것을 등록으로 인정하는가) + **검증기**(채운 값이 실제 로봇과 맞는가).
  - FR3 를 기준 프로파일로 등록. **값 100% 보존**을 회귀 테스트로 기계 증명
    (리터럴 대조 — 프로파일에서 유도하면 동어반복이라 의미 없으므로 손으로 옮겨 적음).
  - `config.py` 는 클래스 속성 주입 방식(`apply_profile`)으로 전환. 인스턴스 속성이
    아니라 **클래스** 속성인 이유는 `_grasp_z_for`/`_finger_width_is_grasp` 같은
    `@classmethod` 순수 계산이 `cls.X` 를 읽기 때문 — 인스턴스에만 넣으면 그것들이
    옛 값을 조용히 쓴다.
  - 그리퍼 어댑터(`gripper_adapters.py`)로 `GripperCommand` 경로 확보. 파지 판정을
    **물리 개구(m) 단위**로 정규화(프랑카 핸드는 항등 변환이라 수치 완전 동일).
  - `robot_model:=` 인자 하나로 URDF/SRDF/MoveIt/컨트롤러/엔티티/노드가 모두 전환.
  - 원클릭 조작면 2종: `binpick_model` 명령 + `desktop_bridge` REST 엔드포인트.
    **미검증(draft) 모델로의 전환은 양쪽 모두 거부**한다.
  - 문서 `docs/robot_profiles.md` (등록 절차 + 검증기가 잡는 오류 표).
- **남은 것 ⬜:** 자산이 벤더링된 모델은 여전히 FR3 뿐 — 다른 팔을 실제로 띄우려면
  그 팔의 description/MoveIt 패키지(+그리퍼 결합 xacro)를 먼저 확보해야 한다.
  UR 계열은 `ros-jazzy-ur-description`/`ur-moveit-config`/`ur-simulation-gz` +
  `robotiq-description` 로 apt 설치 가능함을 확인했다(미설치). `GripperCommand`
  어댑터와 툴 프레임 축 규약 보정은 실기 검증 전이다.

### 볼트 파지 근본원인 수정 — TCP↔손끝 오프셋 (2026-07-21~22)
- **목표:** 시뮬에서 볼트를 안정적으로 파지.
- **결과:** `fr3_hand_tcp`가 손끝보다 **9.5mm 위**임을 발견 → 목표 z를 바닥 아래로 잡던 버그 수정
  (`GRASP_FLOOR_Z=0.015` 재유도). **파지 성공률 ~100%(5/5)** 달성. 목표 대비 **완료**.

### 도달성·싱귤레이션·기울임·속도 튜닝 (2026-07-22~23)
- **목표:** 구석 볼트 실패 제거 + 사이클타임 단축.
- **결과:** 2D 도달성 필터(‖y−통중심‖≤63mm), 싱귤레이션 배치, 기울임 게이트(바닥 볼트는 수직),
  속도 상향, **plan-only 롤아웃**(안 움직이고 후보 시뮬 후 최적만 실행), **학습형 선택기(SGD)**. **완료**.

### 파지 성공 판정 개선 — pose 기반 (2026-07-23)
- **목표:** "정확히 잡았는데 빈손으로 오탐" 제거.
- **결과:** 손끝 폭 대신 **리프트 후 볼트 상승량**(지상진실)으로 성공 확정. **완료**.

### 비전 파이프라인 — 카메라→포인트클라우드→볼트 자세 (2026-07-23~24)
- **목표:** 통 위 RGB-D 카메라로 볼트 6D 자세 인식 → `/next_bolt_pose` 발행.
- **결과:** gz `rgbd_camera` 추가, **월드에 `Sensors` 시스템 플러그인 누락**을 찾아 수정(카메라가 조용히
  발행 안 하던 근본원인), `bolt_vision`의 포인트클라우드 NaN/inf 필터 수정.
- **남은 것 🔶:** RViz Best-Effort QoS로 점군 확인 + **비전이 실제로 `/next_bolt_pose`를 발행해 로봇이
  그걸로 파지하는 엔드투엔드 검증**. → 아래 "앞으로 할 일" 최상단.

### 코드 리팩토링 + 자체완결 워크스페이스 + GitHub (2026-07-24)
- **목표:** 3350줄 갓클래스를 "처음 보는 사람도 이해"하게 모듈화, 별도 폴더로 관리·GitHub 푸시.
- **결과:** 책임별 **14개 Mixin 모듈**로 분해(동작 보존 — 메서드 107·상수 82 값 완전 일치 검증),
  실행 의존(FR3 모델·MoveIt·Gazebo) 통째 포함한 **자체완결 워크스페이스**, README/아키텍처 문서,
  `slfkalstks/robot_arm`에 푸시(`4937dba`). **완료**.

### WSL 이전 + 실행 편의 (2026-07-24)
- **목표:** 윈도우 데스크톱 → 우분투(WSL) 실환경으로 이전.
- **결과:** `~/robotarm_main`으로 통째 이전, 전체 colcon 빌드 확인, `binpick_activate` 명령 추가,
  데스크톱 원본 정리. **완료**.

### 데스크톱↔로봇 데이터 계약 설계 (2026-07-24)
- **목표:** 데스크톱앱 연동 전에 **"무엇을 주고받을지"(데이터 계약)** 먼저 확정.
- **결과:** `docs/desktop_protocol.md` + 노션 기획서. 주 명령 **`PICK_BOLT`**(1순위 좌표),
  섀도우 연료 **`arm_state`** 스트림, `fail_reason` 거부 루프, enum/필드 정밀 스펙까지. **기획 완료**
  (통신 방식·구현은 다음 단계).

### 통신 방식 확정 + `desktop_bridge` 구현 (2026-08-03)
- **목표:** 데이터 계약 다음 단계인 **통신 방식(전송 프로토콜)** 을 정하고, 데스크톱앱이
  아직 없어도 **로봇쪽 통신 기능 자체를 검증**할 수 있게 만든다(데스크톱앱은 별도 팀 구현 예정).
- **결과:** rosbridge 대신 **자체 WebSocket+JSON 브릿지**로 결정(이유: 데스크톱 쪽이
  ROS/roslib 없이 아무 언어의 평범한 websocket 라이브러리만으로 §2 봉투 스키마 그대로
  주고받을 수 있음 — docs/desktop_protocol.md §4). `desktop_bridge` 노드를
  `integrated_pick_place`(1000줄+ 갓클래스)와 **별도 프로세스**로 구현해 Gazebo/MoveIt 없이도
  단독 기동·검증 가능. `PICK_BOLT`→기존 `/next_bolt_pose` 재발행, 결과→`selection.py`
  `_log_attempt()`(모든 `_pick()` 종결점의 단일 입구)에 발행 훅 1줄 추가로 실제 `RESULT` 왕복까지
  확인(파지 로직 코드는 미변경). `tools/mock_desktop_client.py`(ROS 무의존)로 PING/GET_STATUS/
  PICK_BOLT/heartbeat/arm_state 전체 왕복 실측 검증. **완료** — 단, PICK_BOLT 를 뺀 나머지
  명령은 ACK 골격만(로봇 동작 미반영, 의도된 범위 제한).

### ⚠ `reason` 문자열 개명 — `attempts.jsonl` 분석 시 주의 (2026-08-07)
- **무슨 일:** 커밋 `bf7aff0` 에서 `_pick()` 이 발행하는 내부 `reason` 문자열 3개가 바뀌었다.
  - `abort` → **`axis_unreachable`** (볼트 축이 거의 수직 — 옆에서 못 감싸 영구 포기)
  - `no_aperture` → **`no_aperture_exhausted`** (시도할 새 접근 자세 소진 → 블랙리스트)
  - `abort` → **`orientation_fail`** (파지 자세 생성 실패)
  - `abort`/`no_aperture` 자체는 **다른 의미로 계속 쓰인다**(각각 하강 직전 볼트 이동으로 시도
    취소 / 이번 무더기에서만 보류) — 사라진 게 아니라 의미가 좁아졌다.
- **왜 중요한가:** 이 문자열은 `selection.py._log_attempt()` 가 `attempts.jsonl` 에 그대로 기록한다.
  즉 **커밋 전후 레코드가 같은 물리적 사건에 서로 다른 `reason` 을 쓴다.** `train_selector` 등
  `reason` 으로 그룹핑해 분석하면 한 사건이 두 그룹으로 쪼개지거나, `abort` 그룹에 의미가 다른
  구·신 레코드가 섞인다.
- **어떻게 할 것:** 개명 이전 로그를 함께 볼 때는 위 매핑으로 정규화한 뒤 집계할 것. 매핑표
  자체는 `protocol.py` 의 `FAIL_REASON_MAP` (부록D 코드 변환) 참고.

---

## 🔜 앞으로 할 일 / 해야 할 것

### 정밀 분석 · 업그레이드 핸드오프 (2026-08-25)
- 프로젝트 전체 문서·소스·런치·프로파일·테스트를 대조하고, 최신 빈피킹 연구 및
  MoveIt/ROS 공식 기능을 현재 구조에 맞춰 적용하는 실행 계획을 작성했다.
- 확인된 우선 결함: `ALERT` type 대소문자 드리프트, 리프트 실패 reason 오기록,
  `/next_bolt_pose`의 비전/데스크톱 출처·correlation 소실, soft ESTOP/RESET 의미,
  파지 성공과 place 완료 결과의 미분리.
- 현재 장면은 실제 무더기가 아니라 5개 단일 레이어 singulation 기준선이므로,
  L0~L3 seeded clutter benchmark와 clear-rate 지표를 먼저 추가하는 방향을 확정했다.
- Claude/후속 작업자는 작업 ID·파일·수용 기준·검증 명령이 정리된
  **`docs/bin_picking_analysis_and_upgrade_plan.md`**를 실행 백로그로 사용할 것.
- 통신 프로토콜은 별도 정밀 감사를 완료했다. 확인된 P0는 `deadline(t_sim)`과 Unix
  벽시계 혼용, HTTP 접수와 robot ACK 미분리, RESULT/ALERT의 telemetry queue 드롭,
  재접속 복구 부재다. v3 hotfix와 v4 command resource/action/idempotency/replay/
  scope·lease 구현 순서는 **`docs/desktop_protocol_upgrade_plan.md`**를 기준으로 한다.
- PLC 없는 구성을 위한 ROS Supervisor 설계를 별도로 확정했다. 셀/명령/cycle 상태기계,
  READY admission, custom Action, phase별 cancel·recovery, restart reconciliation과 현재
  `run()`/`_pick()`/`_drop()`의 이관 순서는 **`docs/ros_supervisor_design.md`**의
  `SUP-01`~`SUP-08`을 기준으로 한다. Supervisor는 기능 안전이나 FCI 실시간 제어를
  대체하지 않는다.

### 즉시 (지금 막힌 지점 해소)
- ✅ **비전 엔드투엔드 검증 (FR3 라이브 완료):**
  - ✅ `bolt_vision` 벤더 중립화: 하드코딩 `fr3_link0` 제거, BIN crop 을 `bolt_scene` 단일 출처로 유도.
  - ✅ `vision_verify` 노드 신설: 비전 추정 vs Gazebo 정답 대조 → 위치(mm)/축(°) 오차 통계.
  - ✅ Gazebo Harmonic `optical_frame_id` 프레임 불일치 버그 발견·수정(양쪽 URDF).
  - ✅ XY crop 마진이 빈 테두리를 포함해 잘못된 클러스터 선택하던 문제 발견·수정.
  - ✅ **FR3 라이브 결과**: 위치 **7.8mm**(Z 편향 4mm 포함) / 축 **1.2°** — 파지 허용 범위 내.
  - ✅ **UR5e 라이브 결과**: 위치 **6.1mm** / 축 **1.8°** — FR3 와 동등. BASE_FRAME `base_link` 자동 전환 확인.

### 다음 단계 — 데스크톱 연동
- ⬜ **로봇측 연동 인터페이스 마무리:** `desktop_bridge` 는 준비됐다 — 남은 건
  ① `fail_reason` 을 부록D 고정 어휘로 정확히 매핑(현재는 내부 사유 문자열 그대로 전달)
  ② `ESTOP`/`START`/`SET_SPEED`/`BLACKLIST_ADD` 등 ACK-only 명령을 실제 로봇 동작에 연결
  ③ heartbeat.state 를 부록B 전체 상태enum(HOMING/PLANNING/...)으로 세분화.
- ⬜ **데스크톱앱 구현(별도 팀):** 포인트클라우드 수신 → 볼트 랭킹 → `PICK_BOLT` 송신(WebSocket+JSON,
  `docs/desktop_protocol.md` 그대로) → **디지털 섀도우**(URDF + `arm_state` 렌더; Foxglove 3D 우선 검토).

### 안전 (자리 미리 확보)
- ⬜ deadman 워치독 + RESET 게이팅을 프로토콜/노드에 반영(실물에서 하드웨어 안전회로에 물릴 자리).

### 실물 전환 대비 (중장기)
- ⬜ hand-eye 캘리브레이션(실물 카메라 외참).
- ⬜ 하드웨어 E-STOP + 로봇 안전 컨트롤러(STO) 연동.
- ⬜ 데이터 소스 스왑: Gazebo `/joint_states` → `franka_ros2` 하드웨어(계약이 동일해 앱 변경 최소).

---

### 로봇 모델 등록 — 공유상수 타깃 감사 (계획 확정, 2026-08-12)
- ✅ UR5e 파지 튜닝(0/5→4/5) 및 바닥 볼트 적응형 하강 부활(`grasp_floor_raise`, FR3 불변).
- ⬜ **타깃 감사**: 팔/그리퍼 의존 하드코딩 상수(`GRASP_MAX_ABOVE` 등)만 프로파일 이관.
  대상물/작업셀/알고리즘 기본값은 단일 출처 공유 유지(전면 비공유는 불채택 — 근거는 계획서).
- ❌ 닉네임(별칭) 전환: 검토했으나 **불채택**(2026-08-12 사용자 결정). 전환은 정식 `name` 으로만.
- ⬜ **백로그**: bolt_3 far 자세 운반 모션 장벽(step 1b), `tilt_min_center_z` 실측화(step 2).
- → 실행용 상세 계획: **`docs/robot_profiles_audit_plan.md`** (분류표·마이그레이션·라이브 재현법).

## 참고 문서
- `README.md` — 빌드·실행·모듈 지도
- `docs/architecture.md` — 모듈 의존 그래프·회귀 주의점
- `docs/desktop_protocol.md` — 데스크톱↔로봇 데이터 계약(주고받는 데이터)
- `docs/desktop_protocol_upgrade_plan.md` — 통신 결함·보안·신뢰성 감사와 v4 실행 백로그
- `docs/ros_supervisor_design.md` — PLC 없는 셀의 ROS 상태기계·Action·복구 설계
- `docs/robot_profiles.md` — 로봇 프로파일 등록 시스템
- `docs/robot_profiles_audit_plan.md` — 공유상수 타깃 감사 실행 계획(핸드오프)
