# 국내 제조공정 + 로봇암 특허 랜드스케이프 및 프로젝트 중복도

> 조사 기준일: 2026-08-26  
> 실시 국가: 대한민국  
> 제품 기준: 실물 `비전 → 데스크톱 판단·감시 → 로봇암 실행` 제조 셀  
> 성격: 공개자료 기반 선행기술·FTO 예비조사이며 법률의견이나 비침해 보증이 아니다.

## 1. 결론

### 1.1 “제조공정 + 로봇암”은 하나의 특허군이 아니다

국내 문헌은 다음 세 층으로 나뉜다.

1. **수평 플랫폼권리:** 센서/비전, 사용자 단말·서버, 로봇 제어, AI 검사,
   안전거리, 작업 recipe처럼 여러 제조업에 공통 적용되는 권리
2. **공정권리:** 공급, 조립, 체결, 용접, 도포, 사출, 가공, 검사, 분류, 포장,
   팔레타이징 등 특정 공정 순서와 설비 조합을 청구하는 권리
3. **로봇 하드웨어권리:** 관절, 감속기, 암, 그리퍼, 툴체인저, 이동베이스처럼
   제조공정과 무관하게 로봇 자체를 청구하는 권리

현재 프로젝트의 가장 큰 위험은 특정 로봇 모델이 아니라 **수평 플랫폼권리와 선택한
공정권리가 만나는 지점**이다. 단순히 로봇 제조사를 바꾸거나 연산을 데스크톱으로
옮기는 것만으로는 기능적으로 작성된 시스템 청구항을 회피하지 못한다.

### 1.2 조사 범위 내 우선 감시 7건

| 순위 | 문헌 | 상태 표시 | 현재 구조와의 관계 |
|---:|---|---|---|
| 1 | [KR20260010291A](https://patents.google.com/patent/KR20260010291A/ko) | 심사 중 | 센서로 서로 다른 객체를 인식하고 조건을 결정해 다중 파지방식으로 파지·조립·이송·검사하는 매우 넓은 독립항 |
| 2 | [KR20250149622A](https://patents.google.com/patent/KR20250149622A/ko) | 심사 중 | 다관절 검사로봇, 로봇 장착 검사유닛, 수집정보 기반 로봇제어와 이상판정을 넓게 묶음 |
| 3 | [KR102797428B1](https://patents.google.com/patent/KR102797428B1/ko) | 활성 등록 | 사용자 단말 + 검사서버 + 정상영상 전용 STPM/teacher-student + 3D 스캔 + RPA/no-code 조합 |
| 4 | [KR102594983B1](https://patents.google.com/patent/KR102594983B1/ko) | 활성 등록 | 카메라로 협동로봇 궤적 촬영, 2D→3D, AI 예측, 서버가 안전·위험구역을 단말에 안내 |
| 5 | [KR102541166B1](https://patents.google.com/patent/KR102541166B1/ko) | 활성 등록 | 로봇 탑재 카메라, 실시간 동영상 복수 캡처, AI 양불판정, 모니터링·알람, 가변조명 |
| 6 | [KR20260010302A](https://patents.google.com/patent/KR20260010302A/ko) | 심사 중 | 복수 협동로봇을 이용한 공급·사출조립·통전검사·배출·트레이 적재의 통합 제조라인 |
| 7 | [KR102443284B1](https://patents.google.com/patent/KR102443284B1/ko) | 등록 | 설계데이터로 검사 대상을 고르고 로봇암이 검사장치를 이동해 치수를 측정·판정 |

`KR20260010291A`와 `KR20250149622A`는 공개출원이라 심사에서 대폭 좁아지거나
거절될 수 있다. 반대로 현재 공개청구항 그대로 등록되면 프로젝트의 범용
검사·분류 플랫폼과 매우 가까우므로 심사경과를 분기별로 추적해야 한다.

### 1.3 현재 제품 방향의 예비 중복도

| 제품안 | 기능·아이디어 중복도 | 독립항 위험 | 판단 |
|---|---:|---|---|
| 범용 AI 비전검사 + 다품종 자동 recipe + 가변그리퍼 + 로봇 처리 | **75~90%** | 높음 | 위 1~5번과 동시에 가까워짐 |
| 고정 카메라 + 구조화 단일 대상 + 명시적 치수규칙 + 고정그리퍼 + 로봇 분류 | **45~60%** | 낮음~중간 | 현재 권고 기본안 |
| 로봇 장착 카메라로 다면 AI 검사·동적 궤적보정 | **70~85%** | 높음 | `KR20250149622A`, `KR102541166B1` 우선 대조 |
| 무작위 적층물 3D 빈피킹 후 검사·분류 | **80~90%** | 높음 | 빈피킹권리까지 누적되므로 권고하지 않음 |

숫자는 조사 문헌과 겹치는 기능요소 밀도이며 침해확률이 아니다.

## 2. 고정 제품 경계와 비교 기준

### 2.1 변하지 않는 구조

- 비전 계층은 원영상, 측정값, 판정근거와 confidence를 생성한다.
- 데스크톱 계층은 recipe, 작업대상·목적지, 승인, 이력, 재시도와 정지를 관리한다.
- 로봇암 계층은 승인된 이송·회전·분류·키팅 작업을 실행하고 결과를 반환한다.
- 하드웨어 안전회로는 일반 데스크톱·비전 소프트웨어와 분리한다.

### 2.2 아직 바꿀 수 있는 것

- 로봇 제조사·모델·축수와 말단장치
- 카메라의 고정/손목 배치, 2D/3D 여부와 조명
- 볼트 또는 다른 대상물, 공급방법과 검사 항목
- 조립·체결·가공·검사·분류·키팅·포장 중 실제 판매 공정

## 3. 수평 플랫폼 특허

### 3.1 범용 객체 대응과 검사로봇

#### KR20260010291A — 특수 객체 대응 로봇

공개 독립항 1은 서로 다른 형상·크기·재질·무게·표면의 복수 객체, 센서부,
센서정보에 따른 작업조건 결정 제어부, 상이한 파지방식이 가능한 파지유닛, 그리고
파지·조작·조립·이송·검사 중 하나를 요구한다. 종속항은 비전/거리/힘 센서, 자동
경로보정, 작업 시나리오 DB, 다중로봇, 모듈형 툴, 성공률 학습까지 확장한다.

- **금지선:** 다품종 자동인식 + 자동 recipe 선택 + 가변/다중 파지방식을 하나의
  제품 사양으로 동시에 확정하지 않는다.
- **설계 차이:** 초기 제품은 한 recipe에 고정된 대상·고정그리퍼·승인된 작업조건을
  사용하고, recipe 변경은 사용자가 명시적으로 검증·승인한다.

#### KR20250149622A — 고정밀 검사 로봇

독립항은 다관절 검사로봇, 로봇에 장착된 조작/감지/촬영 검사유닛, 수집정보 기반
로봇동작 제어와 이상판정을 넓게 요구한다.

- **금지선:** 손목카메라/센서가 검사와 폐루프 궤적보정을 동시에 담당하는 구성
- **설계 차이:** 고정 외부카메라가 검사하고 로봇은 이미 결정된 분류 이송만 수행

### 3.2 비전검사 + 사용자 단말/서버

#### KR102797428B1 — 다품종 통합 AI 비전검사 서비스

활성 독립항은 정상영상만 이용한 판정 단말, 검사서버, 정상영상 데이터, STPM 기반
teacher-student 이상탐지, 검사결과 빅데이터/재학습, 연속불량 알람·시각화, 3D 스캔,
RPA와 drag-and-drop no-code flow를 하나로 결합한다.

- 단순 사용자 단말이나 AI 검사만으로 독립항 전부가 충족되는 것은 아니다.
- **금지선:** 정상영상 전용 STPM + 3D scanner + RPA/no-code recipe builder를 그대로
  결합하지 않는다.

#### KR102541166B1 — 로봇을 활용한 AI 비전검사

독립항은 카메라 탑재 로봇, 제품 전면 실시간 동영상에서 복수 캡처, AI 양불판정,
불량위치, 모니터링·알람, 색상별 조명변경, 레일 이동 LED, 제품 고정·높이조절 구조를
함께 요구한다.

- **설계 차이:** 고정카메라·고정조명·정지화상·규칙기반 치수검사로 출발한다.

#### KR101487169B1 — 로봇 작업 품질 모니터링

카메라 영상에서 관리단말 사용자가 ROI와 이벤트를 설정하고 픽셀수/움직임 강도로
모션을 검출해 알람하는 독립항이다. 연차료 소멸 표시이므로 직접 장애물보다는
데스크톱 모니터링의 선행기술이다.

### 3.3 협동로봇 안전과 공정 모니터링

- [KR102594983B1](https://patents.google.com/patent/KR102594983B1/ko): 카메라 궤적,
  2D→3D, AI 시계열 예측, 사용자 단말 안전구역/알람, 지연·속도조절
- [KR20240047507A](https://patents.google.com/patent/KR20240047507A/ko): 이동로봇의
  검사위치 반복오차를 transformation 분포와 image augmentation에 반영
- [KR20240065341A](https://patents.google.com/patent/KR20240065341A/ko): 관재 가공·용접,
  상태정보, 서비스서버·사용자단말, ML 불량판단과 공정 피드백
- [KR102668950B1](https://patents.google.com/patent/KR102668950B1/ko): 제조 station의
  허용오차와 제어입력을 딥러닝으로 조정하는 예측 공정제어

하드웨어 안전은 이들 영상/AI 서비스와 별개로 인증된 안전 PLC, STO, 스캐너,
보호정지로 구현한다. AI 궤적예측은 안전기능의 단일 수단으로 사용하지 않는다.

## 4. 공정별 국내 문헌 지도

아래는 검색식과 인용망으로 확인한 제조공정 관련 한국 공개·등록 문헌이다. 상태는
검색 서비스 표시이므로 상업 실시 전 KIPRIS 원부로 다시 확인한다.

### 4.1 부품공급·조립·체결

| 문헌 | 핵심 공정·설비 | 프로젝트 재검토 조건 |
|---|---|---|
| [KR20230147955A](https://patents.google.com/patent/KR20230147955A/ko) | 정렬된 복수 체결부품 동시피킹 후 하나씩 가체결 | 복수 볼트 동시피킹·가체결 도입 |
| [KR20230040064A](https://patents.google.com/patent/KR20230040064A/ko) | 체결로봇 너트런너 소켓 자동교환 | 로봇 체결과 자동 소켓교환 도입 |
| [KR20260043922A](https://patents.google.com/patent/KR20260043922A/ko) | 작업자 자세·거리 인식, 협동로봇이 체결물품 운반·순서관리 | 작업자 자세 기반 동적 위치·순서제어 |
| [KR102672927B1](https://patents.google.com/patent/KR102672927B1/ko) | 두 로봇암, 접착제 도포, 심지·상하판 순차 조립 | 같은 골판지 보빈 공정 |
| [KR20230065891A](https://patents.google.com/patent/KR20230065891A/ko) | 탄소섬유 테이프 절단·교차배치·접착제 도포·툴교환 | 탄소섬유 그리드 제조 |
| [KR102213011B1](https://patents.google.com/patent/KR102213011B1/ko) | 적외선 램프 로봇암으로 자동차 방진패드 열융착 | 열융착 궤적과 동일 지그 |
| [KR101655623B1](https://patents.google.com/patent/KR101655623B1/ko) | 부품패널 피킹·가압과 projection 다점용접 통합 | 로봇 EOAT에 피킹·가압·전극 통합 |
| [KR20260010302A](https://patents.google.com/patent/KR20260010302A/ko) | 공급·윤활·버스바 사출조립·검사·트레이 적재 통합 | 다로봇 통합라인 또는 윤활 도포 |

### 4.2 용접·접합·도포·도장·표면처리

| 문헌 | 핵심 공정·설비 | 프로젝트 재검토 조건 |
|---|---|---|
| [KR101381955B1](https://patents.google.com/patent/KR101381955B1/ko) | 지그로 밀착된 두 소재를 로봇 레이저 헤드가 용접선 따라 이동 | 레이저 용접 셀 전환 |
| [KR100913793B1](https://patents.google.com/patent/KR100913793B1/ko) | 로봇 부품 로딩과 분할 레이저빔 내경용접 | 동일 광학·회전물림판 |
| [KR101231002B1](https://patents.google.com/patent/KR101231002B1/ko) | 로봇 도킹건에 실러 충진·잔압제거 | 실러 도포 툴 채택 |
| [KR20240146862A](https://patents.google.com/patent/KR20240146862A/ko) | 이동 플랫폼·센싱 로봇암·브러시 도장 | 모바일 도장로봇 |
| [KR101659758B1](https://patents.google.com/patent/KR101659758B1/ko) | spindle conveyor 흔들림 방지와 로봇 분사건 도장 | 회전 워크 컨베이어 도장 |
| [KR20090074971A](https://patents.google.com/patent/KR20090074971A/ko) | 로봇 노즐 shot peening과 쇼트볼 회수·순환 | 로봇 표면처리 셀 |

### 4.3 사출·취출·절삭·디버링

| 문헌 | 핵심 공정·설비 | 프로젝트 재검토 조건 |
|---|---|---|
| [KR101532706B1](https://patents.google.com/patent/KR101532706B1/ko) | 사출물 취출·gate 커팅·도포 일체형 multi-chuck | 복합 EOAT 도입 |
| [KR101623455B1](https://patents.google.com/patent/KR101623455B1/ko) | 취출로봇 흡착구의 load-cell·온도센서로 즉시 불량판정 | 그리퍼 내 중량·온도 검사 |
| [KR100965781B1](https://patents.google.com/patent/KR100965781B1/ko) | 복수 로봇과 회전테이블의 사출 프레임 구역별 디버링 | 로봇 디버링 공정 |
| [KR101810554B1](https://patents.google.com/patent/KR101810554B1/ko) | 프레스 패널 air centering·load-cell·초음파 중복검사 | 프레스 tandem 검사 |

### 4.4 검사·계측·불량분류

| 문헌 | 핵심 공정·설비 | 프로젝트 재검토 조건 |
|---|---|---|
| [KR102443284B1](https://patents.google.com/patent/KR102443284B1/ko) | CAD 기반 자동차 노즐 선택, 로봇 검사장치 이동, 직경판정 | CAD가 검사점을 자동 선택하는 치수검사 |
| [KR102810575B1](https://patents.google.com/patent/KR102810575B1/ko) | 로봇이 wafer carrier를 정반에 이송, 다지점 두께검사 | 같은 carrier·정반·상하 측정기 |
| [KR102920792B1](https://patents.google.com/patent/KR102920792B1/ko) | guide bolt pipe 호퍼·회전피더·2개 컨베이어·비전·불량리턴 | 같은 볼트파이프 라인 |
| [KR101366188B1](https://patents.google.com/patent/KR101366188B1/ko) | 나사 측면·머리면을 cone mirror로 한 카메라 촬영 | 소멸 표시, 광학 선행기술 |
| [KR101358111B1](https://patents.google.com/patent/KR101358111B1/ko) | 투광 이송부·반사경·복수면 합성이미지 비교 | 소멸 표시, 검사 선행기술 |
| [KR102831296B1](https://patents.google.com/patent/KR102831296B1/ko) | Charuco/Aruco와 depth를 이용한 로봇 calibration | 동일 수식·마커 절차 |
| [KR20250149623A](https://patents.google.com/patent/KR20250149623A/ko) | 인서트 hole 비전, 로봇/비전 offset 보정, 사출 loading/unloading | insert molding cell |

### 4.5 반도체·디스플레이 이송

| 문헌 | 핵심 공정·설비 | 프로젝트 재검토 조건 |
|---|---|---|
| [KR101709586B1](https://patents.google.com/patent/KR101709586B1/ko) | 진공 transfer chamber 로봇과 공정 chamber | 반도체 진공이송 진입 |
| [KR20070021802A](https://patents.google.com/patent/KR20070021802A/ko) | wafer 안착·진동 감지 로봇암 | wafer end-effector |
| [KR20090047117A](https://patents.google.com/patent/KR20090047117A/ko) | 비전으로 wafer 이송로봇 자동 teaching | 반도체 vision auto-teaching |
| [KR20070003411A](https://patents.google.com/patent/KR20070003411A/ko) | 공정 chamber 사이 wafer 로봇암 보호판 | chamber robot 구조 |
| [KR20060134533A](https://patents.google.com/patent/KR20060134533A/ko) | wafer 미끄럼 방지 robot blade | wafer handling EOAT |

### 4.6 포장·팔레타이징·출하

| 문헌 | 핵심 공정·설비 | 프로젝트 재검토 조건 |
|---|---|---|
| [KR20220042647A](https://patents.google.com/patent/KR20220042647A/ko) | frame 내부 3축 palletizing robot, 범위·속도 확장 | palletizing 하드웨어 |
| [KR100424067B1](https://patents.google.com/patent/KR100424067B1/ko) | 서로 다른 두 pallet 동시 공급과 다품종 적재패턴 | 혼류 pallet line |
| [KR20250114027A](https://patents.google.com/patent/KR20250114027A/ko) | 자동 주문피킹용 tray/package unloading과 mixed-case 적재 | 물류·포장으로 전환 |
| [KR101455228B1](https://patents.google.com/patent/KR101455228B1/ko) | 포대 사방 평탄화 후 로봇 pallet 적재 | 유연 포대 적재 |

## 5. 피킹·파지·이송이 제조공정에 결합될 때의 추가 권리

공급·검사·분류 공정이라도 로봇이 비정형 대상이나 무더기를 다루면 다음 빈피킹·그리퍼
권리가 누적된다.

| 문헌 | 추가 위험요소 |
|---|---|
| [KR20250080798A](https://patents.google.com/patent/KR20250080798A/ko) | 반사/투과 객체의 검출모델 + depth/point 복원모델 + pick pose |
| [KR101913321B1](https://patents.google.com/patent/KR101913321B1/ko) | 주변값 또는 다시점 정합으로 missing depth 보정 |
| [KR102432370B1](https://patents.google.com/patent/KR102432370B1/ko) | 손목카메라 + 두 DNN + learned next-best-view |
| [KR102953519B1](https://patents.google.com/patent/KR102953519B1/ko) | 멀티센서·Kalman·RL·superpixel·PoseCNN/DeepIM·zero/few-shot 결합 |
| [KR102030040B1](https://patents.google.com/patent/KR102030040B1/ko) | 다시점 점군·dominant plane·ICP로 bin model 생성 |
| [KR102735562B1](https://patents.google.com/patent/KR102735562B1/ko) | suction·공압확인·진동 triangular groove 정렬 |
| [KR102953070B1](https://patents.google.com/patent/KR102953070B1/ko) | suction cup + finger hybrid gripper |
| [KR20220165750A](https://patents.google.com/patent/KR20220165750A/ko) | 복수 arm·suction cup 가변 사각배열 |

따라서 구조화된 tray/escapement에서 한 개씩 제공받는 것이 제조공정권리와
빈피킹권리의 동시 중첩을 피하는 가장 단순한 제품 경계다.

## 6. 권고 제품의 설계금지선

### 6.1 우선 피할 결합

- 다품종 자동인식, 자동 recipe 선택, 자동 툴교환/다중 파지방식의 일괄 결합
- 손목카메라/센서로 검사하면서 결과에 따라 로봇 검사궤적을 동적으로 변경
- 정상영상-only STPM teacher-student, 3D scanner, RPA/no-code flow의 결합
- 카메라로 로봇 궤적을 2D→3D 변환하고 AI로 위험구역을 예측해 안전제어
- 로봇 장착 카메라의 실시간 동영상, 색상별 가변조명, AI 양불, LoT 알람의 결합
- 무더기 3D 인식, missing-depth 복원, learned next-best-view와 제조검사를 결합
- 피킹·검사·조립·체결·포장까지 한 셀에서 연속 자동화하는 초기 제품

### 6.2 1차 실물 제품 권고 사양

1. 교환식 tray 또는 단순 escapement가 한 개 대상의 위치·방향을 제한한다.
2. 고정 외부카메라와 고정 조명으로 정지화상을 얻는다.
3. 첫 recipe는 명시적 치수·윤곽·색상·존재검사로 판정한다.
4. 데스크톱은 작업자가 검증한 recipe와 목적지만 선택하며 자동 recipe 생성은 하지 않는다.
5. 고정그리퍼를 단 로봇암은 양품·불량·재검사 tray로 이송한다.
6. 검사와 로봇 실행은 cycle ID로 연결하지만, 비전이 로봇의 안전기능을 대체하지 않는다.
7. 두 번째 대상은 같은 메시지 계약을 재사용하되 별도 검증된 recipe로 추가한다.

이 사양은 `비전 → 데스크톱 → 로봇암`을 유지하면서 현재 넓은 공개청구항의 핵심인
다품종 자동적응, 로봇장착 검사유닛, 다중 파지방식을 동시에 사용하지 않는다.

## 7. 실제 구현 전 claim chart 순서

1. `KR20260010291A` 청구항 1~10 대 실제 대상 다양성·파지유닛·recipe 선택
2. `KR20250149622A` 청구항 1과 카메라/센서 배치·검사/로봇 피드백 경계
3. `KR102797428B1` 청구항 1과 학습모델·3D scan·RPA/no-code 사용 여부
4. `KR102541166B1` 청구항 1과 카메라·조명·동영상·알람 구조
5. `KR102594983B1` 청구항 1·10과 협동로봇 안전감시 구현
6. 선택한 실제 공정의 4장 해당 문헌
7. 무작위 공급 또는 3D 피킹을 채택할 때만 5장 문헌

## 8. 검색 범위와 완전성 한계

### 8.1 사용한 공정군

- 공급/취출/로딩/언로딩/이송/정렬
- 조립/삽입/압입/체결/나사/너트런너
- 용접/레이저/spot/projection/접착/실러/도포/도장/열융착
- 사출/프레스/절삭/연마/디버링/표면처리/적층제조
- 비전검사/계측/양불/분류/재검사/공정피드백
- 반도체/wafer/chamber/robot blade
- 포장/적재/팔레타이징/출하
- 협동로봇/작업자/안전거리/모니터링/사용자 단말/서비스 서버

### 8.2 분류 축

- B25J 9/00, 9/16, 9/1664, 9/1666, 13/08, 15/00, 19/00, 19/02, 19/04
- B23K 용접, B05B/B05C 도포, B23Q/B24B 가공, B29C 사출
- G01B/G01N 검사, G06T 영상, G06Q50 제조관리, B65G 포장·적재

### 8.3 “전부”의 법적 한계

이 문서는 공개 검색으로 식별 가능한 관련 한국 문헌을 공정군별로 최대한 확장한
랜드스케이프다. 그러나 다음 때문에 “대한민국의 관련 특허를 법적으로 100% 전부
확인했다”고 보증할 수 없다.

- 출원 후 18개월이 지나지 않아 아직 공개되지 않은 문헌
- 검색어에 로봇암 대신 manipulator, transfer unit 등 다른 표현을 쓴 문헌
- 명세서에만 로봇이 있고 독립항은 다른 설비를 청구하는 문헌
- 분할출원, 정정, 무효심판, 권리이전, 연차료와 최근 보정의 색인 지연
- Google Patents 상태표시와 실제 KIPRIS 특허원부의 차이

상업화 대상 공정과 하드웨어 BOM이 확정되면 KIPRIS에서 원부·최종 등록청구항·심사
이력까지 확인하고 변리사가 요소별 claim chart를 작성해야 FTO 결론을 낼 수 있다.

## 9. 공식 확인처

- [KIPRIS 특허정보검색](https://www.kipris.or.kr/)
- [특허로](https://www.patent.go.kr/)
- [Google Patents](https://patents.google.com/)
- [WIPO PATENTSCOPE](https://patentscope.wipo.int/)

