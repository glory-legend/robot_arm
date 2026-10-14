# 빈피킹 특허 랜드스케이프 및 현재 프로젝트 중복도 예비분석

> **범위 정정:** 이 문서는 현재 소스와 해외 패밀리까지 훑은 1차 랜드스케이프다.
> 국내에서 실물 비전-데스크톱-로봇암 최종 시스템을 운용한다는 기준의 결론은
> [`bin_picking_korean_patent_fto_final_system_2026-08-26.md`](bin_picking_korean_patent_fto_final_system_2026-08-26.md)를 우선한다.

> 조사 기준일: 2026-08-26  
> 분석 대상: `robotarm_main` 현재 소스와 문서  
> 성격: 공개문헌 기반 선행기술·FTO(실시자유) **예비조사**  
> 주의: 이 문서는 변리사/변호사의 법률의견이나 비침해 보증이 아니다.

## 1. 결론부터

1. **기술 아이디어 수준의 겹침은 크다.** RGB-D/3D 비전으로 빈 속 물체 자세를
   얻고, 여러 파지 후보를 만들고, 벽·이웃·도달성·충돌을 검사하고, 가장 성공할
   후보를 골라 픽앤플레이스하는 큰 흐름은 이미 많은 특허 문헌에 나타난다.
2. **현재 한국 실시 기준으로, 이번에 독립청구항까지 대조한 활성 한국 특허 중
   현재 코드가 모든 필수요소를 그대로 충족한다고 확인된 건은 없었다.** 가장 비슷한
   한국 등록특허들도 아래와 같은 필수요소가 현재 코드에 없다.
   - 회전각·거리별 2D 물체모델 DB와 검출 영역의 대조
   - 카메라가 관심영역 주위를 회전하며 얻은 복수 점군의 병합/ICP 모델링
   - RGB-D·LiDAR·스테레오 중 2종 이상, 칼만 정합, 강화학습 인식, superpixel,
     affinity propagation, PoseCNN/DeepIM, zero/few-shot의 결합
   - Charuco/Aruco와 depth를 이용한 특정 캘리브레이션 절차
3. **수출·해외 설치까지 보면 주의도가 올라간다.** 미국에서는 Intrinsic의
   `US20230256601A1`(심사 중), Universal Robots/Teradyne의 `US11511415B2`(등록),
   Siemens의 `US20250387902A1`(심사 중)이 현재 후보생성·점수화·plan-only 검증·
   벽 충돌판정과 가장 가깝다. 다만 이 세 패밀리 모두 이번 공개 패밀리 목록에는
   한국 출원이 없었다.
4. 현재 프로젝트의 독특한 조합인 **M8 볼트 PCA 축 추정 + 축 정렬 평행그리퍼 +
   손가락 스윕/벽 개구의 해석기하 + SGD 성공확률 + MoveIt plan-only rollout +
   리프트 후 실제 상승 검증** 전체가 하나의 확인된 독립청구항에 그대로 들어간
   문헌은 찾지 못했다. 그러나 각 조각은 별개의 선행 특허에 넓게 분산돼 있다.
5. 따라서 현재 판단은 다음과 같다.
   - 한국 내 연구·시뮬레이션: **낮음**
   - 한국 내 상용 장비 판매/실물 운용: **낮음~중간**(권리상태 원장 재확인 필요)
   - 미국/일본/중국/유럽 판매·설치: **중간**, 특히 후보 점수화와 경로 검증 부분
   - 향후 멀티센서+강화학습+딥러닝 인식으로 업그레이드: **재조사 필수**

여기서 위험도는 법적 결론이 아니라 조사 우선순위다. 특허는 제목이나 초록이 아니라
해당 국가에서 살아 있는 **청구항의 모든 필수요소**를 실시하는지가 핵심이다.

## 2. 조사 범위와 한계

### 2.1 이번에 한 일

- 한국어/영어 키워드: `빈피킹`, `bin picking`, `random bin picking`, `robotic
  grasp`, `point cloud`, `grasp candidate`, `ranking`, `reachability`, `bin wall`,
  `collision`, `online learning`, `self learning`, `bolt`, `screw`, `fastener`
- 분류 확장: `B25J9/1697`, `B25J9/1664`, `B25J9/1666`, `B25J9/1669`,
  `G05B2219/40053`, `G05B2219/39484` 주변
- 출원인 확장: ABB, FANUC, Siemens, Universal Robots/Teradyne, Intrinsic,
  TCS, OMRON/Adept, Fetch/Zebra, MUJIN, ETRI, 한화, 한국공학대학교 등
- 주요 문헌의 인용·피인용 및 INPADOC 계열 국가 목록 확인
- 현재 코드의 실제 구현과 공개된 독립청구항을 요소별 대조

### 2.2 “전부”의 의미와 한계

전 세계 특허를 문자 그대로 100% 완전하게 보증하는 검색은 불가능하다. 비공개 상태인
출원(통상 출원 후 18개월), 번역·표기 차이, 아직 색인되지 않은 문헌, 계속/분할출원,
청구항 보정, 법적 상태 지연이 있기 때문이다. 이번 문서는 공개 웹 검색에서 발견한
핵심·인접 문헌 **30개 대표 패밀리/문헌**을 남겼고, 서로 아주 조금만 다른 하드웨어,
캘리브레이션, 빈 모델링, 파지 후 검사 문헌도 제외하지 않았다.

법적 상태는 Google Patents가 표시한 상태와 이벤트를 1차로 사용했다. 실제 의사결정
전에는 KIPRIS 특허원부, USPTO Patent Center, EPO Register, CNIPA/J-PlatPat에서
연차료, 포기, 무효, 청구항 보정, 존속기간을 다시 확인해야 한다.

## 3. 현재 프로젝트의 비교 기준

| ID | 현재 구현 요소 | 코드 근거 |
|---|---|---|
| P1 | 고정 RGB-D 포인트클라우드를 base 프레임으로 변환하고 통 ROI crop | `bolt_vision.py:105-163` |
| P2 | voxel 다운샘플, DBSCAN 분할, PCA/SVD로 볼트 중심·주축·6D 자세 추정 | `bolt_vision.py:160-213` |
| P3 | 가장 높고 점이 많은 볼트를 비전 출력; 내부 폴백은 높이+주변 여유 | `bolt_vision.py:186-197`, `selection.py:149-186` |
| P4 | 볼트×접근각 후보, 벽/이웃/도달성/개구 특징을 SGD 성공확률로 점수화 | `selection.py:191-300`, `grasp_selector.py:55-226` |
| P5 | 벽까지 ray-rectangle 거리와 손가락 sweep-볼트 segment 거리로 개구 계산 | `grasp_planning.py:87-221` |
| P6 | 수직/기울임 접근 후보를 만들고 바닥·벽 조건으로 제한 | `grasp_planning.py:223-305` |
| P7 | 상위 후보를 IK·Cartesian fraction·관절여유로 plan-only rollout 후 선택 | `selection.py:302-418` |
| P8 | MoveIt 충돌계획, 접근·하강·파지·attach·리프트·place 실행 | `pick_place_node.py:711-928`, `930-1024` |
| P9 | 파지 성공/실패로 SGD를 온라인 갱신하고 epsilon 탐험 | `grasp_selector.py:158-226`, `selection.py:275-300` |
| P10 | 리프트 후 볼트 실제 z 상승 또는 손가락 폭으로 파지 성공 검증 | `pick_place_node.py:854-927` |

현재 비전은 겹친 실제 무더기보다 비접촉 단일 레이어에 맞춰져 있고, 딥러닝·강화학습·
멀티센서 융합·모델 DB 매칭·회전 카메라 스캔은 구현돼 있지 않다.

## 4. 가장 가까운 문헌의 청구항 대조

등급은 `기술 유사도 / 현재 청구항 충족 가능성`이며 각각 0~5다. 후자는 공개된
독립청구항을 현재 코드에 문자적으로 대조한 예비값이다.

### 4.1 한국 권리

| 문헌 | 상태·만료예상 | 유사도 | 청구항 대조와 결론 |
|---|---|---:|---|
| [KR102953519B1](https://patents.google.com/patent/KR102953519B1/ko), 아이티유, 우선일 2025-08-12 | 활성, 2045 예상 | 4.5 / 1.0 | 초록은 3D 비전·파지후보·학습·로봇연동으로 매우 가깝다. 그러나 청구항 1은 2종 이상 센서+칼만 정합, RL 적응 인식, superpixel+affinity propagation, IoU/precision/recall/F1 피드백, PoseCNN/DeepIM+RANSAC 정합, zero/few-shot 등을 한꺼번에 요구한다. 현재 프로젝트에는 대부분 없다. |
| [KR102081139B1](https://patents.google.com/patent/KR102081139B1/ko), ETRI, 우선일 2014-03-12 | 활성, 2034 예상 | 3.0 / 0.5 | 2D 영상 국소특징으로 영역을 만들고, 회전각·거리별 저장 물체모델 영역과 대조하며, 절대 회전각/카메라 거리로 후보를 선택한다. 현재는 3D 점군 DBSCAN/PCA이며 모델 영상 DB가 없다. |
| [KR102030040B1](https://patents.google.com/patent/KR102030040B1/ko), 한화, 우선일 2018-05-09 | 활성 | 2.5 / 0.5 | 관심영역을 회전하며 촬영한 복수 점군을 병합하고, dominant plane 위 점을 추출하고, 정합·정제해 빈 ROI 모델을 만든다. 현재는 고정 카메라, 사전 치수 crop이며 멀티뷰 병합/ICP 빈 모델링이 없다. |
| [KR102831296B1](https://patents.google.com/patent/KR102831296B1/ko), 한국공학대, 우선일 2023-05-16 | 활성, 2043 예상 | 1.5 / 0.0 | Charuco/Aruco, pinhole 내부·외부 파라미터, depth를 외부행렬 Z에 적용하고 두 로봇 자세의 동차행렬을 연립하는 캘리브레이션 청구항이다. 현재 런타임 TF 소비와 다르다. |
| [KR102953070B1](https://patents.google.com/patent/KR102953070B1/ko), 에이딘로보틱스, 우선일 2023-06-14 | 활성, 2043 예상 | 1.0 / 0.0 | 석션 컵+한 쌍 핑거와 3개 구동부를 갖고 빈/선반 모드마다 핑거 위치를 바꾸는 하이브리드 그리퍼다. Franka/Robotiq 평행 그리퍼와 구조가 다르다. |
| [KR20110015765A](https://patents.google.com/patent/KR20110015765A/ko), 삼성전자, 우선일 2009-08-10 | 소멸 | 4.5 / 권리없음 | 복수 접근경로 후보의 충돌검사→점수 정렬→실제 파지 성공 시 경로 확정이 매우 가깝다. 한국 권리는 소멸 표시다. 현재 기술의 강한 선행기술로는 중요하다. |
| [KR101712116B1](https://patents.google.com/patent/KR101712116B1/ko), KAIST, 우선일 2015-08-13 | 연차료 만료 | 2.5 / 권리없음 | 객체 접근도, 단위행동 DB, 지속 경로 재생성 및 장애물 시 복귀가 핵심이다. 현재 구조와 필수요소가 다르고 권리도 만료 표시다. |

### 4.2 해외 권리·출원

| 문헌 | 주요 국가/상태 | 유사도 | 청구항 대조와 결론 |
|---|---|---:|---|
| [US20230256601A1](https://patents.google.com/patent/US20230256601A1/en), Intrinsic, 우선일 2022-02-17 | US 심사 중; WO 종료; KR 없음 | 4.5 / 3.0 | virtual workspace, 서로 다른 위치의 grasp proposal+grasping window, 각 후보의 pre-grasp/grasp waypoint, window 안 scene feature 점수, 선택 후보 trajectory 실행을 요구한다. 현재 P4/P7/P8은 매우 가깝지만 ‘grasping window와 그 안 scene feature’ 대신 객체 6D pose와 해석기하 특징을 쓴다. 미국 실시 전 정밀 claim chart가 최우선이다. |
| [US11511415B2](https://patents.google.com/patent/US11511415B2/en), Universal Robots/Teradyne, 우선일 2018-06-26 | US·JP·CN 등록/EP 공개; KR 없음 | 4.0 / 2.5 | 후보 물체, 로봇 환경·관절제약 기반 경로, place 가능성, grasp feasibility, 놓은 뒤 release-retreat까지 collision-free path, 실패 시 다른 grasp/path/object를 요구한다. 현재는 후보/경로/대체 후보는 있지만 선택 전에 전체 place+release retreat를 검증하지 않는다. |
| [US20250387902A1](https://patents.google.com/patent/US20250387902A1/en), Siemens, 우선일 2022-07-18 | US·EP·CN 심사 중; KR 없음 | 4.0 / 2.5 | 빈 치수→벽 plane, end-effector 속성, grasp point+nominal line으로 실행 전 벽 충돌을 판정한다. 현재 ray-rectangle 벽 여유와 MoveIt 충돌계획이 기능상 가깝지만 명시적인 wall plane/nominal-line 거리 비교와는 다르다. |
| [US12493978B2](https://patents.google.com/patent/US12493978B2/en), TCS, 우선일 2022-08-17 | US·JP·AU 등록, EP 심사 중; KR 없음 | 4.0 / 1.5 | RGB-D에서 사각 grasp pose를 무작위 샘플하고 중심픽셀 depth 차로 binary map, contact/free/collision subregion, center/width refinement, FRL+CRS GQS 최대를 요구한다. 현재 DBSCAN/PCA·segment sweep·SGD/rollout은 계산 방식이 다르다. |
| [US11701777B2](https://patents.google.com/patent/US11701777B2/en), FANUC, 우선일 2020-04-03 | US·JP·CN 등록, DE; KR 없음 | 3.5 / 0.5 | 3D 물체모델에서 robust grasp와 stable intermediate pose를 만들고, 직접 goal pose가 불가하면 중간에 놓고 재파지하는 그래프 탐색이 핵심이다. 현재는 중간 재파지와 goal orientation 강제가 없다. |
| [US11787059B2](https://patents.google.com/patent/US11787059B2/en), Zebra/Fetch, 우선일 2017-11-14 | US만 등록 | 3.5 / 0.5 | 사용자 grasp preference, object point cloud와 color 기반 heuristic, 두 후보의 pairwise ranking이 필수다. 현재는 실제 성공/실패 라벨의 pointwise SGD 확률이며 사용자 선호·색·pairwise 비교가 없다. |
| [US20240198530A1](https://patents.google.com/patent/US20240198530A1/en), Siemens, 우선일 2021-06-25 | US·EP·CN 심사 중; KR 없음 | 3.5 / 1.0 | 별도 object detection 출력과 grasp detection 출력을 HLSF로 결합하고 MCDM으로 랭킹한다. 현재는 단일 고전비전 결과와 로봇측 후보생성으로, 두 detector 출력의 sensor fusion이 없다. |
| [WO2023083848A1](https://patents.google.com/patent/WO2023083848A1/en), trinamiX, 우선일 2021-11-09 | PCT 종료 표시 | 4.0 / 권리없음(PCT 자체) | 학습 성공확률·최고점 선택·센서 피드백 재학습·충돌 시뮬레이션이 P9와 가깝다. 그러나 독립항은 다중 촬영위치, projector 패턴, reflection beam profile로 재질특성을 얻어 모델 입력으로 쓰는 조합이다. |
| [US11007648B2](https://patents.google.com/patent/US11007648B2/en), ABB, 우선일 2017-09-05 | US 등록; KR 없음 | 3.0 / 0.0 | 설명에는 성공확률 점수·도달성·crash recovery가 있지만 등록 독립항은 ramped surface에서 물체를 위로 옮겨 풀어 다른 물체를 재배열하는 절차를 요구한다. 현재 통에는 ramp/stir 동작이 없다. |
| [US7313464B1](https://patents.google.com/patent/US7313464B1/en), OMRON/Adept, 우선일 2004-10-15 | US 상태 재확인 필요; KR 없음 | 3.5 / 0.5 | visibility/prehension feature와 도달성을 보고, pickable 물체가 없으면 빈을 변위·기울임·흔든 뒤 반복하는 것이 독립항의 핵심이다. 현재는 빈을 움직이지 않는다. 오래된 권리라 USPTO 원장으로 존속을 재확인해야 한다. |
| [US20240408766A1](https://patents.google.com/patent/US20240408766A1/en), Fizyr, 우선일 2021-10-19 | US 심사 중 | 2.5 / 0.0 | DNN이 segmentation map과 복수 property map을 만들고 별도 알고리즘이 grasp proposal을 결정한다. 현재 비전은 DNN/property map이 없다. |

## 5. 아주 조금이라도 다른 인접 문헌 목록

아래는 현재 직접 중복도는 낮지만 업그레이드 시 범위에 들어올 수 있어 남긴 문헌이다.

| 문헌 | 차이점 / 재검토 트리거 |
|---|---|
| [US11648674B2](https://patents.google.com/patent/US11648674B2/en) | 집은 첫 workpiece를 별도 scanner에 제시해 pose를 저장하고 유사한 다음 workpiece의 pick/place에 재사용. 파지 후 정밀 재스캔을 넣을 때 재검토. |
| [US9008841B2](https://patents.google.com/patent/US9008841B2/en) | 파지 후 카메라로 1개/복수개 파지를 판정하고 자세가 기준 밖이면 반환·조정. 현재는 z 상승/핑거폭 검증. post-pick 카메라 추가 시 재검토. |
| [US9079308B2](https://patents.google.com/patent/US9079308B2/en) | 인출 중 힘을 감시하고 한도 초과 시 다른 인출방향 탐색/해제. 현재 force/torque 기반 인출은 없음. |
| [US12304066B2](https://patents.google.com/patent/US12304066B2/en) | 수백 개 랜덤 빈 시뮬레이션과 leftover 수로 fingertip 형상을 반복 최적화. 그리퍼 프로파일/성능평가와는 다르나 자동 손끝 설계 시 재검토. |
| [JP2023120149A](https://patents.google.com/patent/JP2023120149A/en) | CAD와 GUI에서 사람이 target grasp region을 정의해 grasp DB 생성. 현재는 볼트 축에서 자동 생성. |
| [CN119188728B](https://patents.google.com/patent/CN119188728B/en) | semantic point cloud, 각 sampling point의 PCA normal/principal axis, grid search, confidence ranking. PCA 기반 후보를 dense sampling으로 확장할 때 재검토. |
| [JP2015182184A](https://patents.google.com/patent/JP2015182184A/en) | 금속광택 볼트의 영상 기반 bin picking/자세 조정 문헌. 현재 Gazebo 점군과 실제 반사 금속 대응은 다름. |
| [US20250242498A1](https://patents.google.com/patent/US20250242498A1/en) | 임의 크기/장방형 end-effector의 yaw-oriented pick pose. 대형 흡착툴로 바꿀 때 재검토. |
| [US20250262772A1](https://patents.google.com/patent/US20250262772A1/en) | place 영역 정보를 pick 선택에 역으로 반영. 현재 drop slot은 pick 이후 선택. place-conditioned pick을 넣을 때 재검토. |
| [US20230081119A1](https://patents.google.com/patent/US20230081119A1/en) | 여러 end-effector별 성공모델과 자동 tool selection/swap. 현재 robot profile 전환은 기동 전이며 자동 tool swap이 아님. |
| [US20200017317A1](https://patents.google.com/patent/US20200017317A1/en) | 랜덤·신규 물체의 pick/sort/place와 graspability 확률. M8 단일종·PCA 규칙과 다름. |
| [US11559885B2](https://patents.google.com/patent/US11559885B2/en) | graspability map의 고확률 pixel/영역을 점수화·선택. 현재는 3D 물체×접근각 후보. |
| [US20240070900A1](https://patents.google.com/patent/US20240070900A1/en) | 위 TCS 등록특허의 공개번호. depth binary subregion 방식의 상세 구현 비교용. |
| [KR20240175941A](https://patents.google.com/patent/KR20240175941A/ko) | 위 KR102953070B1의 공개번호. 석션+핑거 하이브리드 하드웨어. |
| [KR20240096989A](https://patents.google.com/patent/KR20240096989A/ko) | 로봇 부착 RGB-D, 기준마커와 IK로 평면 평행화 후 물체 자세 추정; 절차 포기/소멸 표시. |
| [KR102803072B1](https://patents.google.com/patent/KR102803072B1/ko) | grid-based warehouse의 레일 이동 피킹장치/컨테이너 승강 구조. 빈이라는 단어 외 핵심이 다름. |

## 6. 기능별 겹침 정도

| 프로젝트 기능 | 선행문헌 밀도 | 현재 차별점 | 판단 |
|---|---:|---|---|
| RGB-D/점군으로 빈 속 물체 검출 | 매우 높음 | 고정 ROI+DBSCAN+PCA로 알려진 M8 축만 추정 | 아이디어 자체는 새롭지 않음 |
| 높은/여유 있는 물체 우선 | 높음 | z, 최근접 이웃, 벽, 개구를 한 특징벡터에 결합 | 구성요소별 선행 다수 |
| 접근각 후보와 충돌검사 | 매우 높음 | 볼트축 둘레 기울임과 바닥 높이 게이트 | 일부 차별, 단독 신규성 보장 안 됨 |
| 벽/이웃에 따른 동적 개구 | 중간 | 사각 팁을 6개 sweep segment로 근사하고 선분간 거리로 개구 하향탐색 | 이번 조사에서 가장 구체적인 차별점 중 하나 |
| 성공/실패 온라인 SGD 랭킹 | 높음 | 딥RL/사용자 pairwise가 아닌 12개 해석 특징의 pointwise partial-fit | 방식 차이는 명확하나 학습 랭킹 개념은 선행 다수 |
| MoveIt plan-only rollout | 높음 | IK branch seed, Cartesian fraction, joint margin을 결합하고 같은 접근 관절해를 실행에 전달 | 구체 조합은 차별 가능, Intrinsic/UR 계열 주의 |
| attach 후 lift 성공 검증 | 중간~높음 | Gazebo 실제 bolt z 상승, 불가 시 finger width 폴백 | 카메라/힘센서 검증 특허와 센서 방식 차이 |
| robot profile로 FR3/UR5e 교체 | 낮음~중간 | 검증된 YAML 프로파일과 물리개구 단위 변환 | 빈피킹 특허 핵심보다는 플랫폼 구성 |
| REST/WS 데스크톱 모니터링 | 낮음 | 로봇 제어 GUI 특허는 많지만 현재 핵심 청구항 대조에서는 부수요소 | 별도 산업제어/디지털트윈 검색 필요 |

## 7. 실제 제품화 전 조치

### 7.1 지금 바로 유지할 설계 증거

- `bolt_vision.py`가 2D 모델 DB나 DNN이 아닌 DBSCAN/PCA라는 점
- 후보가 이미지상의 grasping window가 아니라 `bolt_id × axis-relative tilt`라는 점
- 점수가 object color/user preference/pairwise가 아니라 실제 성공·실패의 pointwise
  SGD라는 점
- 벽/이웃 필터가 sensor-fusion이나 learned map이 아니라 명시적 기하 계산이라는 점
- 현재 pick 전에 전체 place+release-retreat를 공동 최적화하지 않는다는 점

이 차이는 코드 주석뿐 아니라 버전 태그, 설계문서, 시험로그로 남겨야 한다. 나중에 기능이
바뀌면 과거 버전을 기준으로 한 이 분석은 더 이상 유효하지 않다.

### 7.2 기능 추가 전 특허 재검토 게이트

다음 변경은 구현 PR 전에 새 검색과 claim chart를 요구하는 것이 안전하다.

1. RGB-D 외 LiDAR/스테레오 추가 및 칼만 기반 센서 정합
2. PoseCNN/DeepIM, zero/few-shot, reinforcement learning, superpixel segmentation
3. 이미지/height-map의 grasp window·property map·affordance map 점수화
4. pick 후보 선택 전에 place와 release-retreat 전체를 함께 feasibility 검증
5. 빈 벽을 plane으로 만들고 grasp nominal line과의 거리로 전용 충돌판정
6. post-pick 카메라로 단일/복수 파지 및 자세를 검사
7. 여러 그리퍼 성공모델을 비교해 자동 tool swap
8. 빈을 흔들거나 물체를 밀어 재배열하는 stir/disperse 동작

### 7.3 국가별 출시 게이트

- **한국:** 위 5개 활성 한국 등록권의 KIPRIS 원장과 최종 등록청구항을 변리사가
  재확인하고, 특히 `KR102953519B1`과 `KR102081139B1`에 대해 1페이지 claim chart 작성.
- **미국:** `US20230256601A1`의 심사·보정 결과를 추적하고 `US11511415B2`의
  claim 1/20/21, `US12493978B2` claim 1, `US11787059B2` claim 1을 정밀 대조.
- **일본/중국/유럽:** Universal Robots, FANUC, TCS, Siemens 패밀리의 해당 국가
  청구항은 미국 청구항과 달라질 수 있으므로 별도 대조.
- 오픈소스 MoveIt/ROS/Gazebo를 쓴다는 사실은 제3자 특허 실시허락을 의미하지 않는다.

## 8. 최종 위험 순위

1. **해외 최우선 감시:** Intrinsic `US20230256601A1` — 현재 후보/waypoint/점수/
   trajectory 구조와 가장 가까운 심사 중 청구항.
2. **해외 등록권 최우선:** Universal Robots `US11511415B2`와 국가 패밀리 — 현재는
   사전 place/retreat 공동검증이 빠져 있지만 개선계획이 그 방향으로 갈 수 있다.
3. **벽 계산 변경 시:** Siemens `US20250387902A1` — 현재도 기능상 가깝고 향후
   wall-plane 전용 판정을 넣으면 더 가까워진다.
4. **한국 업그레이드 감시:** `KR102953519B1` — 현재는 필수요소가 대거 빠져 있으나
   계획된 멀티센서·학습형 비전 업그레이드가 같은 조합으로 접근할 가능성이 있다.
5. **현재 한국 직접 위험:** 이번 공개자료·독립청구항 대조 범위에서는 낮다. 다만
   비침해 확정이 아니며 비공개 출원과 검색 누락 가능성이 남는다.

## 9. 참고 링크

- [KIPRIS 특허정보검색](https://www.kipris.or.kr/)
- [WIPO PATENTSCOPE](https://patentscope.wipo.int/)
- [USPTO Patent Center](https://patentcenter.uspto.gov/)
- [EPO Espacenet](https://worldwide.espacenet.com/)
- [Google Patents](https://patents.google.com/)
