# Notion 버전 기록

최초 기록일: 2026-09-30. 갱신일: 2026-10-02. 위치: Bin_Picking 문서 데이터베이스.

- [볼트 그리퍼 설계·모델링 버전 기록](https://app.notion.com/p/3ebbf0105ac981379e65c20e9e332bcb?pvs=204)
- [R00 · 초기 절차적 집게·슬라이드 개념](https://app.notion.com/p/3ebbf0105ac981508ae0d879bc1cba6b?pvs=204)
- [R01 · Tesollo DG3FM 12관절·손바닥 인입](https://app.notion.com/p/3ebbf0105ac98134a27df322ffd3e53f?pvs=204)
- [R02 · Hand-E + 직선 보조 막대](https://app.notion.com/p/3ebbf0105ac981bf8875dea23699008d?pvs=204)
- [R03 · 생체모방 3관절 주집게 + 2관절 엄지](https://app.notion.com/p/3ebbf0105ac98188a499c668571ea817?pvs=204)
- [R04 · Robotiq 2F-85 + 슬림 손끝·보조 엄지](https://app.notion.com/p/3ebbf0105ac981769857d32420c74e3f?pvs=204)
- [R05 · 일자형 테이퍼 팁·50mm 엄지·6조 척](https://app.notion.com/p/3ebbf0105ac9811b88c3d7fec5ef2b7a?pvs=204)
- [R06 · 내부 체결·최소 이동 구조 비교 — 진행 중](https://app.notion.com/p/3ebbf0105ac9816f9ec2d0129c5e1161?pvs=204)

- [R07 · 기계 조립 검토](https://app.notion.com/p/3ecbf0105ac98126b38cc13e55b71d62)
- [R07 A · 2R 엄지·6제어축](https://app.notion.com/p/3ecbf0105ac98118ba85f4a0e4a15424)
- [R07 B · 카세트 전체 1R·5제어축](https://app.notion.com/p/3ecbf0105ac9810c9938e5264b5aa442)

## 첨부

- DG3FM.zip: 부분 소스·원본 메시·URDF·라이선스 22개 파일.
- R04.zip: 당시 소스 8개와 해시 목록.
- R05.zip: 코드·문서·설정·테스트·사진 5장, 총 35개 파일.
- history-evidence.zip: 과거 버전 구현 기록·R04 선정 근거·Robotiq 자산.
- common-assets.zip: FR3 메시·관절 YAML·라이선스 및 Robotiq 공통 자산. R05 재현 상대 경로 설명 포함.
- R05 사진 5장: whole, alignment, handoff, fastening, exploded.
- R06 재현 사진 8장: A/B 각각 pickup, righting, handoff, drive. 보존 구현을 2026-10-01 재실행해 촬영했으며 당시 원본 사진이 아닙니다.

## 누락·주의

R00 초기, R02 Hand-E, R03 생체모방의 독립 코드 및 사진은 확보하지 못했습니다. R01 DG3FM과 R04의 전체 실행 스냅샷·당시 사진도 없습니다. /tmp/dg-* 이미지는 R05로 덮어써진 파일이므로 DG3FM 사진으로 사용하지 않았습니다. R06은 내부 체결 구조 비교·검토 단계입니다. 구동 방식이 미정이고 간섭 문제가 남아 있어 제작용으로 승인할 수 없습니다. 보존 소스·재현 사진 ZIP을 추가했으며 실물 검증 결과는 없습니다. R07 조립뷰와 구분합니다.

## 확인

Notion 상위 페이지의 하위 7개 페이지, 첨부 ZIP 5개, R05 이미지 5개를 fetch로 확인했습니다. DG3FM/R04/R05 파일 해시가 모두 일치했고 ZIP 5개 무결성 검사도 통과했습니다. 이 작업에서는 앱 소스·테스트·README·REDESIGN을 수정하거나 서버/브라우저 테스트를 실행하지 않았습니다. 추가 보존 파일과 export 정보는 archive/ 안에 있습니다.

R05 당시 개발 검증 결과: 단위18, 브라우저10, 마지막 관련브라우저2, typecheck/format/build 통과입니다. 아카이브 작업의 새로운 실행 결과가 아닙니다.

## 문서 갱신

2026-10-01: 상위 페이지와 R00~R06을 설계 목적·판단·변경 근거 중심으로 정리했습니다. 버전별 수치·기존 검증 범위·원본 누락 표기는 유지합니다. 원본 ZIP은 변경하지 않습니다.

R06 사진: archive/R06/screenshots/의 A/B 재현 사진 8장을 Notion에 첨부하고 재조회로 확인했습니다. 촬영일 2026-10-01, 시점 5·12·18·40초. 보존 구현의 재실행 자료이며 당시 원본이나 R07 결과 사진이 아닙니다. 5초 장면은 통 벽에 접촉부 일부가 가려집니다. 구동 미정·간섭 미해결에 따른 제작용 승인 불가 상태를 유지합니다. R05 사진 5장은 보존했습니다.

## R07 조립 검토 기록

2026-10-01 R07 최신 사진 12장과 미터 단위 GLB 2개, 부품군 검토 CSV, 예비 하중 JSON, 기계 검토 문서를 Notion에 첨부했습니다. A/B 모두 내부 6조 척을 사용하며 A는 2R 엄지·6제어축, B는 카세트 전체 1R·5제어축입니다. 단위 26개·브라우저 13개(약 1.8분), 타입·빌드·Prettier 통과와 GLB 미터 단위 검증을 기록했습니다. 강도·연속 충돌·실물 토크 검증이나 제작 승인을 의미하지 않습니다. R07 최종 ZIP은 본문에 첨부 자리를 확보했습니다.

R06 ZIP도 첨부했습니다. SHA256: 6849b2ffacaac113442ecec4ceecf809515a8b66bdb7629529536da9edb9d57c.

## R09 핀셋형 소형 그리퍼 기록

2026-10-01 [R09 · 핀셋형 소형 그리퍼 · 가는 노즈](https://app.notion.com/p/3ecbf0105ac981569b46c48a74abd894) 페이지를 상위 기록 아래에 만들었습니다. 첨부는 사진 9장(whole, pick, righting, thumb-park, draw-in, release, stow, dense-wall-fastening, internal-layout), R09.zip(130개 파일, SHA256 9edca812176c5aa1b55d3c0e53b1f27ff24c9b750ef13eeec64f0e4137216d78), validation.json, component-review.csv, R09.md입니다. 재조회로 사진 9장과 파일 4개가 모두 붙은 것을 확인했습니다. 업로드 기록은 archive/R09/NOTION_UPLOADS.json에 있습니다. GLB는 만들지 않았습니다. 단위 검사 42개와 브라우저 검사 16개를 통과했으며, 제작 승인 도면은 아닙니다.

2026-10-01 추가: R09 GLB 3개(m6/m8/m10-r09-gripper.glb, 미터 단위, 원점은 FR3 플랜지, t = 12 s 자세)를 만들어 archive/R09에 넣었습니다. GLB를 포함한 새 R09.zip(133개 파일, SHA256 f11c50d8b11444c3261c9f081db14be7e9c5242693399e2620ae7c7b591ba6be)과 갱신한 validation.json을 Notion 페이지의 "GLB와 최신 묶음" 섹션에 첨부했고, 재조회로 확인했습니다. 처음 올린 ZIP은 GLB가 없는 판이며 페이지에 그렇게 표시했습니다.

2026-10-01 정리: Notion R09 페이지에서 GLB가 없던 첫 ZIP과 첫 validation.json 블록을 삭제했습니다(휴지통). 지금은 "GLB와 최신 묶음"의 파일만 남아 있습니다.

## R10 원통형 + 캠 연속 스트로크 기록

2026-10-02 [R10 · 원통형 + 캠 연속 스트로크 그리퍼](https://app.notion.com/p/3edbf0105ac98111ba0ad66cffd9a36e) 페이지를 상위 기록 아래에 만들었다. 이 판은 [R10 시안 검토](https://app.notion.com/p/3ecbf0105ac981129b5ce3ba5fad6920)에서 채택한 시안 2다.

- 첨부 사진 11장: whole, pick, righting, thumb-park, stroke-draw-in, stroke-clamp-spread, transparent-spring-chuck, stowed, dense-wall-fastening, overtravel-release, internal-layout
- 첨부 파일: GLB 3개, R10.zip(138개 파일, SHA256 f566284d797c9bcdac9a67039c375110e63bf7f191905e1a6eceed6789c13877), validation.json, component-review.csv, R10.md
- 페이지를 다시 불러와 사진 11장과 파일 7개가 모두 붙은 것을 확인했다. 업로드 기록은 archive/R10/NOTION_UPLOADS.json에 있다.
- 검증 결과는 단위 72개, 브라우저 18개, 타입 검사, 빌드, 포맷 검사 모두 통과다. 제작 승인 도면은 아니다.

## R11 구조 외피 경량화 · 정지 인계 기록

- 기록일: 2026-10-02
- [R11 · 구조 외피 경량화 · 정지 인계 그리퍼](https://app.notion.com/p/3edbf0105ac9812db9d1e965cfd79246)
- 위치: 볼트 그리퍼 설계·모델링 버전 기록 / R11
- 작성·윤문·본문 게시 모델: Claude Sonnet 5.5 (`claude-sonnet-5-5`)
- 윤문: im-not-ai humanize-korean v2.3.2, light, gate OK
- 첨부 사진: R11 원본 9장, R10 재현 2장
- 재조회 확인: 사진 11장, 비교표 2개, 검증표 1개, 기능 보존과 미확정 항목
- 검증: 단위 86개, 브라우저 18개, 타입·빌드·포맷 통과. 기존 정적검사 미해소 지적 18건 유지
- 로컬 기록: `R11.md`, `archive/R11/notion-publication-verification.json`

R11 캡처는 2026-10-02 현재 구현에서 찍은 원본입니다. `r10-reproduced` 캡처는 보존된 설계를 현재 시점에 재실행한 것으로, 당시의 원본 이미지가 아닙니다.
