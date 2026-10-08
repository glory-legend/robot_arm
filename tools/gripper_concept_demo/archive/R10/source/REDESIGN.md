# R05 · 현실성을 우선한 통합 그리퍼 재설계

M6~M10 모두 최종 체결하는 것을 설계 조건으로 정했다. 규격별 소켓 교환 없이 헤드에 자동으로 맞물리는 범용 구조를 사용한다. 전체 도구의 경량화, 작은 보조 엄지, 실제 헤드 유지·체결·정렬 구조를 조사하여 모델 전체를 재설계한다. 기존 R04는 구동부가 생략된 가상 3조 척이므로 완성 도구의 무게나 길이 비교 기준으로 쓰지 않는다.

## 설계 결정

- 기본 파지: Zimmer GEP2006IL-03-B급 전동 평행 모듈. 6mm/측 스트로크, 180g. 본체 설치 공간은 44×22×69mm(턱 포함 높이 85.5mm)이며 제조사 CAD 복제가 아니다. 중앙 체결축과 간섭하지 않도록 뒤쪽에 장착한다.
- 주집게: 관절 손가락을 폐기하고 일자형 테이퍼 팁 2개로 변경했다. 동일한 강체 팁을 M6~M10에 사용하며 뿌리 8×8mm, 끝 3×4mm, 길이 58mm. 끝의 작은 수동 회전 패드가 볼트의 90° 회전을 따른다. 실제 회전 패드 강도·마찰은 미검증이다. 파지 모듈 전체가 대각 레일을 따라 뒤 35mm·위 35mm 후퇴하여 체결면을 비운다. 레일 스트로크는 49.5mm이며 2축 모터를 의미하지 않는다.
- 보조 엄지: 25+25=50mm 두 링크, 기존 55+50=105mm 대비 52% 감소. 기준점을 손끝 가까이 옮겨 필요한 도달 거리를 줄인다. 두 구동기는 본체 쪽에 두고 텐던으로 전달하며 링크 자체에 모터를 숨기지 않는다.
- 헤드 유지·체결: 여러 턱이 오므라드는 방식을 선택했다. 6개의 방사형 강체 턱이 육각 대변 10/13/17mm에 맞춰 닫히는 자체 설계안이다. 18mm 착좌 스트로크, 쐐기 캠·추력 베어링·잠금 구조를 개념 형상으로 표현한다. Gator-Grip 핀 배열이나 규격 교환 소켓은 채택하지 않는다. 현재 형상 대응 범위는 육각 외부 헤드이며 임의 형상 대응을 주장하지 않는다. 캠 구동력·기계 잠금·접촉압력·토크 용량을 실물 정격으로 보증하지 않는다.
- 체결: Kolver KDS-PL50CA급 5~50Nm, 지름 57×길이 322mm, 1.8kg 실제 외형 공간을 확보한다. 제조사 CAD가 아닌 설치 공간 모델이다. 최종 체결 값은 나사 강도·윤활·체결부 설계가 미지정이므로 확정하지 않는다. 시연은 예시 8/20/40Nm로 구분하며 추천 토크라고 표시하지 않는다.
- 긴 70mm 척 연장을 삭제했다. 소켓이 짧게 전진하여 헤드에 들어가고 파지 모듈을 대각 레일로 후퇴시켜 작업면과의 간섭을 피한다. 모델은 육각 위상이 맞은 상태에서 착좌·척 닫힘·집게 해제 순서를 보여준다. 실제 자동화를 위해서는 ±30° 이내 저토크 위상 탐색과 착좌·잠금 감지가 필요하며 현재 재생은 센서 시뮬레이션이 아니다.
- FR3 손목 관절 정격을 넘는 반력을 로봇으로 버티지 않는다. 고정 체결 지그의 수직 키 홈이 스핀들 하우징 탭을 받아 토크를 작업대로 전달한다. 볼트 삽입 중 축방향 이동은 키 홈을 따라 허용한다. 애니메이션은 지그 키가 들어간 다음 구동한다. 실기 제어는 도킹 센서와 별도의 인터록이 필요하다.
- 스핀들에는 고정 하우징/회전축/베어링/축방향 컴플라이언스를 구분한다. 전체 모터가 회전하거나 샤프트가 고무처럼 늘어나는 표현을 제거한다.

## 조사 범위와 근거

| 기능             | 비교한 자료                                                                  | 판단                                                                                                         |
| ---------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| 범용 관절 파지   | Robotiq2F85, OnRobotRG2                                                      | 85/110mm 개구와 범용 파지는 작은 볼트에 비해 큰 구조. 기준 비교만 보존.                                      |
| 소형 전동 파지   | SCHUNK EGP25, Zimmer GEP2006                                                 | EGP25-N-S-B는120g이나3mm/측,허용손가락32mm. GEP2006은180g,6mm/측,허용손가락60mm로 채택.                      |
| 저형 공압 파지   | SMC MHF2                                                                     | 압축공기·밸브를 포함한 시스템 필요. 전동구성 유지 목적으로 비교안.                                           |
| 실제 무더기 볼트 | Dürr x-elect / Optonic                                                       | 전용그리퍼와네스트를 사용한 실사례. 공개 치수 부족하므로 기구 복제근거로 사용하지 않음.                      |
| 유지 소켓        | Ko-ken NUT GRIP, Desoutter magnetic/nut setters                              | 비교만 수행. 규격 교환을 요구하므로 채택하지 않음.                                                           |
| 진공 유지        | DEPRAG, WEBER SEV-E                                                          | 유연하지만씰·진공회로·스트로크가추가됨. 이번육각외측헤드는기계유지선택.                                      |
| 체결 스핀들      | DEPRAG EC-Servo, Desoutter EFM43-45, Kolver KDS-PL50CA                       | 범위·부피·중량을비교. Kolver5~50Nm/1.8kg를설치공간기준으로선택.                                              |
| 커스텀 감속 구동 | maxon GP42C/GPX52, FAULHABER44/1                                             | 감속기만으로토크센싱/브레이크/열설계/반력이해결되지않음. 완제품체결스핀들보다근거없는경량화를주장하지않는다. |
| 손안 회전        | Roller Grasper V2, passive roller fingertips, tactile gravitational pivoting | 단순파지력완화로볼트가원하는대로돌아간다는가정삭제. 회전패드+보조접촉으로자유도를명시.                       |

출처(확인 2026-09-30):

- https://schunk.com/us/en/gripping-systems/parallel-gripper/egp/egp-25-n-s-b/p/000000000000310902
- https://www.zimmer-group.com/fileadmin/pim/MER/GD/PG/MER_GD_PG_GEP2006IL-00-B__SEN__APD__V1.pdf
- https://onrobot.com/sites/default/files/documents/Datasheet_RG2_v1.0_EN.pdf
- https://www.smcworld.com/catalog/New-products-en/mpv/es20-263-MHF2-F/data/es20-263-MHF2-F.pdf
- https://www.koken-tool.co.jp/panflets/KOKEN201710.pdf
- https://www.deprag.com/fileadmin/bilder_content/emedia/broschueren_pics/emedia_schraubtechnik/D3161/D3161en.pdf
- https://www.weber-online.com/en/fixtured-screwdriving-systems/fixtured-screwdriver-sev-e/
- https://files.desouttertools.com/content/leaflet/Multi_leaflet_Desoutter_EN.pdf
- https://kolver.com/upl/EN_Catalog_KDUCER.pdf
- https://www.maxongroup.com/medias/sys_master/root/8882587140126/EN-21-364.pdf
- https://www.faulhaber.com/en/products/precision-gearheads/planetary-gearheads/
- https://arxiv.org/abs/2004.08499
- https://arxiv.org/abs/2603.27452
- https://support.franka.de/docs/control_parameters.html

## 구현과 검증 범위

- 구현: 동일 일자형 테이퍼 팁, 수동 회전 패드, 50mm 엄지, 6조 가변 척, 18mm 착좌, 파지 모듈 후퇴, 실치수 체결 스핀들 설치 공간, 고정 반력 지그.
- 운동: 총 70초. 체결 23~61초(피치 M6=1, M8=1.25, M10=1.5mm), 최종 토크 구간 61~63초, 해제 63~65초. 가장 긴 M10의 최고 회전속도는 약 79rpm으로 기준 스핀들의 90rpm 이내다. 강체 회전·삽입만 계산하며 토크-각도 곡선이나 체결부 탄성은 계산하지 않는다.
- 질량: 알려진 구매부품 1.8+0.18=1.98kg. 척·레일·엄지 구동·장착부·배선 추가 질량은 아직 산정하지 않았다. 전체 도구가 기존보다 가볍다고 확정하지 않는다. 제조 전 무게중심·FR3 하중 조건 검토가 필요하다.
- 모델은 공개 CAD 복제가 아닌 설치 공간/개념 형상이며 GEP 모듈 이외 후퇴 구동기와 텐던 모터의 형상·치수는 설계용 가정이다.
- 자동 검사: 세 규격에서 접근~후퇴 구간의 엄지 베이스·팔꿈치·두 링크와 볼트 외접 원통 사이의 표본 간극, 엄지 접촉·강체 길이·파지 인계·관절 제한·볼트 자세 연속성·체결면 착좌. 전체 메쉬 충돌, 응력, 마찰, 제어 성공률은 검사하지 않는다.

추가 출처:

- https://originalgatorgrip.com/product/gator-grip-universal-socket/
- https://originalgatorgrip.com/faq/
- https://www.wera.de/en/tools/6004-joker-4-set-1-self-setting-spanner-set
- https://ifdesign.com/en/winner-ranking/project/bionic-wrench/24065

최적화는 기능을 누락하지 않는 설계 비교와 치수 축소를 뜻한다. 세계의 모든 그리퍼를 열거했다거나 실물 최적해를 증명했다는 주장은 하지 않는다. 최종 제작 전에는 강도/수명/체결공정 승인이 필요하다. 현재 목표는 이 사항을 숨기지 않는 현실적인 3D 설계안이다.

엄지 간섭 수정: 베이스를 파지점 기준 Y+33mm, Z−10mm에 배치하고 M6/M8과 M10의 팔꿈치 방향을 구분했다. M10은 접근 시 바깥쪽으로 우회하며 모든 규격에서 모듈 후퇴 후 엄지를 접는다. 팁 접촉만 검사하던 이전 검증 범위를 넓혀 고정부와 링크까지 확인한다.

내부 공간: 이동 캠 외반경 20.5mm, 외부 하우징 내반경 20.8mm로 방사상 0.3mm 여유를 둔다. 이는 개념 모델의 기하 간극이며 제조 공차·윤활·변형을 포함한 베어링 설계값은 아니다. 엄지 지지봉과 텐던은 닫힌 주집게 사이를 통과하지 않도록 본체 뒤로 우회한다.
