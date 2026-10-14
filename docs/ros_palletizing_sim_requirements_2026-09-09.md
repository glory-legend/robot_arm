# ROS 팔레타이징 회수 시뮬레이션 — 요구사항·목표 (구현 핸드오프)

> **2026-09-09 사용자 정정:** 실제 구현 기준은 사용자 지정 PDF
> 「실시간 바코드 기반 온라인 혼합 박스 팔레타이징 시스템」이다.
> 개발 순서와 현재 구현 상태는 [`palletizing_implementation.md`](palletizing_implementation.md)를
> 따른다. 아래 M1~M4는 가상 회수 특허 실험의 별도 설계로 보존한다.

> 작성일: 2026-09-09
> 대상 독자: **이 저장소에서 구현을 수행할 코딩 에이전트(Codex 등)**
> 성격: 요구사항·목표·설계 제약의 명세. **이 문서는 구현물이 아니다** — 구현은 독자가 한다.
> 선행 산출물(반드시 먼저 읽을 것):
> - 특허 명세서: `docs/virtual_retrieval_patent_spec_draft_2026-09-09.md` (청구항 1의 G1·G2·G3)
> - 추상 시뮬레이터(로직 원본): `experiments/virtual_retrieval_sim/sim.py`, `README.md`
> - 선행조사: `docs/virtual_retrieval_verification_claim_chart_2026-09-09.md`
> - 프로젝트 지침: 루트 `AGENTS.md`, `README.md`, `PROGRESS.md`, `src/AGENTS.md`

---

## 1. 목표 (한 문장)

기존 로봇암 프로젝트(FR3 + MoveIt2 + Gazebo, ROS2 Jazzy)와 **동일한 방식**으로,
컨베이어로 도착하는 혼합 박스를 **상면 흡착 그리퍼**로 집어 **임시 적층부(버퍼)에
회수 실행가능성(G1·G2·G3)을 검증하며 배치**하고, **외부에서 부여된 회수 순서대로 꺼내
출고 팔레트에 적재**하는 과정을 **Gazebo/RViz에서 눈으로 볼 수 있게** 실행한다.

## 2. 배경 (왜 이걸 만드는가)

- 특허(가상 회수 검증 기반 버퍼 적재)의 진보성 근거로, 순수 기하 시뮬레이션
  (`experiments/virtual_retrieval_sim/`)에서 **T3(발명) 배치가 종래(T0) 대비 회수 재배치를
  24%(여유 조건)~50%(저점유) 감소**시킴을 이미 정량 입증했다(재현 가능).
- 그 추상 결과를 **로봇이 실제로 움직이는 ROS 시뮬**로 실체화해, (a) 시각적 데모와
  (b) 특허 실물 검증(대표 시나리오)의 토대를 만든다.
- **핵심 알고리즘은 새로 짜지 말 것.** `experiments/virtual_retrieval_sim/sim.py`의
  전략(T0/T3)·게이트(G1/G2/G3)·회수 로직을 그대로 재사용/이식한다.

## 3. 환경 (검증 완료 — 2026-09-09)

- ROS2 **Jazzy**, Gazebo(gz sim, Harmonic 계열, `gz_tools_vendor`), MoveIt2, colcon.
- WSL2 + **WSLg GUI** (`DISPLAY=:0`) — GUI 렌더 가능.
- **기존 로봇 시뮬이 이 환경에서 정상 기동함을 확인**:
  `ros2 launch bin_picking franka_gazebo_moveit.launch.py` 실행 시
  `gz sim server`/`gz sim gui`/`move_group`(MoveIt)/컨트롤러(`fr3_arm_controller`,
  `fr3_gripper_controller`, `joint_state_broadcaster`)가 모두 활성화됨.
  world = `install/bin_picking/share/bin_picking/worlds/robot_view.sdf`.
- **소싱 주의(AGENTS.md):** 기본 셸이 zsh라 `.bash` 직접 소싱이 깨진다. 반드시
  `bash -c 'source /opt/ros/jazzy/setup.bash && source install/setup.bash && ...'`
  또는 `.zsh` 형제 파일을 쓴다.
- 빌드: `colcon build --symlink-install` 후 `source install/setup.bash`.

## 4. 재사용할 기존 자산 (그대로 참고/확장)

| 자산 | 경로 | 팔레타이징에서의 역할 |
|---|---|---|
| 로봇+MoveIt+gz 기동 | `src/bin_picking/launch/franka_gazebo_moveit.launch.py` | **그대로 재사용**(로봇/월드/MoveIt) |
| 씬 스폰 패턴 | `src/bin_picking/launch/spawn_bolts.launch.py` | → `spawn_palletizing.launch.py`의 본보기 |
| SDF 모델 | `src/bin_picking/models/bolt_bin/`, `m8_bolt/` | → 팔레트·박스 SDF의 본보기 |
| MoveIt planning-scene | `src/bin_picking/bin_picking/bolt_scene.py` | → 팔레타이징 planning-scene의 본보기 |
| 데모 실행자 | `src/bin_picking/bin_picking/pick_place_node.py` (`integrated_pick_place`) | → 팔레타이징 데모 노드의 본보기 |
| MoveIt 래퍼 | `src/bin_picking/bin_picking/moveit_io.py` | 계획/실행/Cartesian/IK/FK — **그대로 호출** |
| 기하 엔진 | `src/bin_picking/bin_picking/geometry.py` (`_seg_seg_dist`, `_ray_rect_travel`) | G2 판정 — 추상 시뮬이 이미 재사용 중 |
| 그리퍼 | `src/bin_picking/bin_picking/gripper.py` | 흡착 대체(§6) |
| gz↔ROS 브리지 | `ros_gz_sim create`, `ros_gz_bridge parameter_bridge` | 모델 스폰·pose 브리지(spawn_bolts 참고) |
| 배치/회수 알고리즘 | `experiments/virtual_retrieval_sim/sim.py` | **T0/T3·G1/G2/G3·회수 로직 이식 원본** |

## 5. 기능 요구사항

### FR-1 씬 구성
- **출고 팔레트** 1개 이상(목적지별), **임시 적층부(버퍼)** 1개 — 둘 다 SDF 모델로 스폰.
- **혼합 박스** N개: 서로 다른 폭(footprint)·높이·중량. 각 박스에 **외부 부여 회수 순서**를
  부여(주문 시스템 모사). 컨베이어 도착 위치(또는 픽업 지점)에 순차 스폰.
- 배치·회수는 FR3의 **도달 범위 안**에 있어야 한다(기존 `config.py`의 REACH_* 참고,
  spawn_bolts가 도달권에 맞춰 좌표를 조인 사례 참고).
- MoveIt **planning-scene**에 팔레트·버퍼·박스를 충돌체로 등록(bolt_scene.py 패턴).

### FR-2 배치 결정(핵심 = 발명)
- 신규 박스마다: 출고 팔레트 즉시 적재 가능하면 적재, 아니면 **버퍼 배치 후보를 생성**하고
  **T3 전략**(`sim.choose_stack('T3', ...)`)으로 위치 결정.
- T3는 각 후보에 가상 배치 후 **부여 회수 순서로 가상 회수**하며 매 단계 **G1∧G2∧G3**를
  검사, 통과 후보 중 회수 비용 최소 위치를 택한다(`sim.retrieval_cost`).
- **비교 데모용으로 T0(종래)도 선택 가능**해야 한다(launch 인자 `strategy:=T0|T3`).

### FR-3 회수
- 부여 회수 순서대로 버퍼에서 박스를 꺼내 출고 팔레트로 적재.
- 대상이 맨 위가 아니거나 경로가 막히면 **재배치**(다른 스택으로 임시 이동) — 횟수 집계.
- `sim.evaluate_retrieval`의 정책과 **동일**하게 동작해야 T0/T3 비교가 공정하다.

### FR-4 가시화·계측
- Gazebo(gz gui)에서 로봇 모션과 박스 이동이 보이고, RViz(`rviz:=true`)에서 planning-scene·
  계획 경로가 보인다.
- 실행 로그/화면에 **누적 재배치 횟수, 회수 순서 진행, 현재 G1/G2/G3 판정 결과**를 출력.
- 한 회 실행 종료 시 T0/T3 요약(재배치 횟수 등)을 남긴다 — 추상 시뮬 결과와 대조 가능하게.

## 6. 상면 흡착 그리퍼 (가정)

- 특허·시뮬은 **상면 진공 흡착**을 전제한다. 기존 하드웨어는 FR3 평행 그리퍼(집게)다.
- **구현 선택지(우선순위 순, 독자가 택일):**
  1. **부착/해제(attach-detach) 방식**: gz 흡착/조인트 부착 플러그인 또는 `AttachLink`
     서비스로 흡착 순간 박스를 엔드이펙터에 고정, 놓을 때 해제. 상면 수직 접근.
  2. gz 진공 그리퍼 플러그인이 가용하면 사용.
  3. 최소안: 평행 그리퍼로 상면 근처를 집되, **접근 방향을 상면 수직으로 고정**하고 G1을
     "상면 노출"로만 판정(물리 흡착은 근사).
- 어느 방식이든 **G1의 의미(상면이 덮이면 파지 불가, 측면 대안 없음)**는 유지해야 한다.

## 7. 물리 게이트 G1·G2·G3 의 ROS 대응 (sim.py → ROS)

| 게이트 | 추상 시뮬(sim.py) | ROS 구현 지침 |
|---|---|---|
| **G1 파지** | 대상이 스택 맨 위(상면 노출) | 대상 박스 상면이 다른 박스에 덮이지 않고 흡착 패드 footprint 확보. planning-scene 기하로 판정 |
| **G2 경로** | `_seg_seg_dist`(파지물+그리퍼 스윕 vs 이웃) + IK 해 | **MoveIt으로 실제 반출 경로 계획 성공 여부**로 대체 가능(가장 정확). 사전 필터는 geometry의 선분거리 유지 |
| **G3 안정성** | 지지 다각형 내 무게중심 + 하중 | 제거 후 잔여 박스의 무게중심 투영이 하위 지지면 안인지 기하 판정(sim.g3 이식) |

- **원칙:** 배치 결정(빠른 사전 판정)은 sim.py 기하로, **실제 실행 직전 검증**은 MoveIt 계획
  성공/실패로 확인(계획상 위치 vs 실제 위치 오차 반영 = 특허 청구항 7·S9).

## 8. 구현 범위 (단계별 마일스톤 — 각 단계가 독립적으로 "볼 수 있는" 산출물)

- **M1 씬만**: 로봇 launch + `spawn_palletizing.launch.py`로 팔레트 2개 + 박스 N개 스폰,
  planning-scene 등록. → gz/RViz에 로봇·팔레트·박스가 보인다. **가장 먼저, 반드시 이것부터.**
- **M2 배치**: 데모 노드가 박스를 하나씩 흡착해 T3로 버퍼에 배치(회수는 아직). → 적재 모션 관찰.
- **M3 회수**: 부여 순서대로 회수 + 재배치 + 출고 팔레트 적재. → 전체 사이클 관찰.
- **M4 비교**: `strategy:=T0|T3` 인자로 두 전략 실행, 재배치 횟수 로그 대조 →
  추상 시뮬(§2)의 우위가 실물 모션에서도 재현됨을 확인.

## 9. 만들/수정할 파일 (제안, 전부 `src/bin_picking/` 안)

| 파일 | 내용 |
|---|---|
| `models/pallet/model.sdf` | 출고/버퍼 공용 팔레트 SDF (bolt_bin 참고, 평평한 팔레트) |
| `models/mixed_box_*/model.sdf` | 폭·높이 다른 박스 SDF 몇 종 (m8_bolt 참고, PosePublisher 포함) |
| `launch/spawn_palletizing.launch.py` | 팔레트+박스 스폰 + pose 브리지 (spawn_bolts 이식) |
| `bin_picking/palletizing_scene.py` | MoveIt planning-scene 등록 (bolt_scene 이식) |
| `bin_picking/palletizing_demo_node.py` | 데모 실행자: sim 전략으로 결정 + moveit_io로 실행 |
| `bin_picking/virtual_retrieval.py` | sim.py의 T0/T3·G1/G2/G3·회수 로직을 ROS 패키지로 이식(또는 sim.py를 import) |
| `setup.py` | `console_scripts`에 `palletizing_demo` 엔트리 추가 |
| `launch/palletizing_demo.launch.py` | (선택) 로봇+씬+데모 원클릭 (desktop_integration_demo 패턴) |
| `PROGRESS.md` | 진행 상황 갱신 |

## 10. 제약·규칙 (반드시 준수)

- `franka_description` / `franka_fr3_moveit_config` / `franka_gazebo_bringup`는
  **read-only 벤더 자산**. 수정 금지(태스크가 명시적으로 요구하지 않는 한).
- `build/`, `install/`, `log/`는 **직접 편집 금지** — `colcon build`로 재생성.
- 신규 코드는 `src/bin_picking/`에만. 데이터 계약을 건드리면 `docs/desktop_protocol.md`와
  `protocol.py` 동기 유지(FAIL_REASON_MAP이 단일 진실).
- 문서(README/PROGRESS/docs)는 한국어 관례 유지.
- 배치/회수 정책은 추상 시뮬과 **동작 일치**를 유지해야 비교가 유효하다(회귀 시 sim.py가 기준).
- 런타임 산출물(`~/pick_place_logs/` 등)은 gitignore 대상 — 커밋 금지.

## 11. 검증 기준 (완료 조건)

- **M1**: `franka_gazebo_moveit.launch.py` + `spawn_palletizing.launch.py` 동시 실행 시,
  gz에 로봇·출고 팔레트·버퍼·박스 N개가 스폰되고 RViz planning-scene에 충돌체로 보인다.
- **M2/M3**: 데모 노드가 오류 없이 배치→회수 전 사이클을 실행하고, 로봇이 실제로 박스를
  옮긴다(gz에서 관찰). 회수 순서가 부여 순서와 일치.
- **M4**: 동일 시나리오(같은 seed)에서 `strategy:=T0`와 `T3`의 재배치 횟수가 로그로 출력되고,
  **T3 ≤ T0**(추상 시뮬과 같은 방향). 대표 시나리오에서 T3가 유의하게 적음.
- 각 단계 실행 커맨드와 기대 출력을 `PROGRESS.md`에 기록.

## 12. 열린 결정 사항 (독자가 판단·선택)

- 흡착 구현 방식(§6의 1~3 중) — gz 플러그인 가용성에 따라.
- 박스 종류 수·크기 분포, 버퍼 스택 수/높이(추상 시뮬 기본: 5스택×5, 폭 1~3단위 참고).
- 출고 팔레트 개수(단일 목적지로 시작 권장, 다목적지는 확장).
- 컨베이어를 실제 모델로 둘지, 픽업 지점만 둘지(데모는 픽업 지점만으로 충분).
- G2를 MoveIt 계획 성공으로 볼지, 기하 사전판정만으로 볼지(정확도 vs 속도).
