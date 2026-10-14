<!-- RECORD_START 3ebbf010-5ac9-8137-9e65-c20e9e332bcb -->
# 볼트 그리퍼 설계·모델링 버전 기록
Record URL: https://app.notion.com/p/3ebbf0105ac981379e65c20e9e332bcb?pvs=204

초기 브라우저 시연부터 후속 그리퍼 변경을 버전별로 보존합니다. 최초 기록일은 2026-09-30이며 문서 갱신일은 2026-10-01입니다. 모델 제작 완료와 실물 검증 완료를 구분합니다.
## 기록 원칙
- R00\~R03은 이번 보존 작업에서 붙인 순서 식별자입니다. R04\~R07은 설계 작업의 버전명을 유지합니다.
- 원본 파일이 남은 버전만 ZIP으로 첨부하고 코드·문서·사진의 누락을 각 버전에 표시합니다. 다른 버전의 사진을 대체 자료로 사용하지 않습니다. 보존 구현의 재실행 사진은 재현 촬영일을 표시하고 당시 원본 사진과 구분합니다.
- 보존 파일마다 SHA256 해시를 기록합니다. 개념 모델을 제조사 CAD·실제 토크 시험·물리 시뮬레이션으로 설명하지 않습니다.
- R05는 동결 스냅샷입니다. R06은 내부 체결 구조 두 안의 검토 기록이며 구동 방식과 간섭 문제가 미해결된 상태입니다. 제작용 승인 대상이 아닙니다.
## 공통 범위
FR3 브라우저 시연, 한국어 조작 화면, M6×20 / M8×35 / M10×50 볼트. ROS 제어 코드를 수정하지 않는 독립 도구입니다. 과거 버전의 테스트 수는 당시 기록이며 현재 코드를 다시 실행한 결과가 아닙니다.
## 버전 목록
하위 페이지에 구조, 수치, 변경 이유, 증거와 누락 내역을 기록합니다.
<table header-row="true">
<tr>
<td>버전</td>
<td>핵심 변경</td>
<td>보존 상태</td>
</tr>
<tr>
<td>R00 초기</td>
<td>절차적 집게·슬라이드·깔때기·3조 척</td>
<td>이력만, 독립 코드·사진 없음</td>
</tr>
<tr>
<td>R01 DG3FM</td>
<td>실제 메시·12관절·30mm 손바닥 인입</td>
<td>부분 소스와 원본 자산 ZIP, 사진 없음</td>
</tr>
<tr>
<td>R02 Hand-E</td>
<td>기존 2지 + 2직선축 보조 막대</td>
<td>이력만, 독립 코드·사진 없음</td>
</tr>
<tr>
<td>R03 생체모방</td>
<td>3관절 주손가락 2개 + 2관절 엄지</td>
<td>이력만, 독립 코드·사진 없음</td>
</tr>
<tr>
<td>R04 2F-85</td>
<td>실제 제품 링크 + 교환 손끝 + 70mm 척 전진</td>
<td>부분 소스 ZIP·제품 자산, 사진 없음</td>
</tr>
<tr>
<td>R05 일자 팁</td>
<td>동일 테이퍼 팁·50mm 엄지·6조 척·18mm 착좌</td>
<td>코드·문서·검사·사진 5장 스냅샷 ZIP</td>
</tr>
<tr>
<td>R06 진행 중</td>
<td>A 내부 척 + 수납 / B 같은 집게로 파지·체결</td>
<td>설계·검토 기록 + 2026-10-01 재현 사진 8장. 구동·간섭 미해결</td>
</tr>
<tr>
<td>R07 조립 검토</td>
<td>A 2R 엄지·6제어축 / B 카세트 전체 1R·5제어축, 공통 내부 6조 척</td>
<td>최신 사진 12장·GLB 2개·부품군 CSV·하중 JSON·기계 검토 문서. 제작 미승인</td>
</tr>
</table>
## 공통 이력·출처 파일
<file src="https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/96dff602-e4ea-4535-8466-aa7a691bd6e1/history-evidence.zip?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4664656UZDO%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002831Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIDXIMsHuEgZmETPAaGDwaPvcSYrB8LcUKzRFKsdEA%2BP%2BAiAwzxKNqi07aVT3EM%2FWYTOoojbAgQTnH5JMZBHYmGNXyCr%2FAwhwEAAaDDYzNzQyMzE4MzgwNSIM5nyu%2FSrEDyPi5D8GKtwDSjWy3um7JRfBOl%2FQgZBKui%2BG9YwfikTEhBWtBGJZ4qEvZ3LkIs%2BQ3q9VMyTYAGQlHm1IpOHclaindz1bLBJOpktJcZzE4mRlMARNCGnkX2tZ%2BDfXIxVvkWdiQJhJcXbOhkBvnhdGp7CCeYn2ab%2ByEjgwSQn2XMzn5KdlkB6F%2BJgdUrD0mizsswo5R7at%2B9P8EGb%2FN%2B6DWmTSw%2BqTMBSjxKbp%2BgnPo1wRBwiXVzkffact9%2B7syB2bM55QoaF3WBU5AexvDGi7ju6MYR9b6YYPuI7vsB83ZmXMGGOAUnuwm2KptDdi4Y%2BNEswlrzlfWeGghiSCIuVxcjSwwMLyPB0A3DFmaQ3g6freEgb8PtIR9MiSIgEACEeNctvX4JmYL6jpy3ZNTAVUt0UgDNa2TpnneZB8Ioe65sBxgOmylZdbaQQ0lweFpt347oeONZSYYsN%2F4VFA4FONKFYnsuxv%2BggTN8zlgOJpwfgbHpvhOwUqYGFR8efng7NjB%2Bu7qaqyiqjYTJQ%2F7ZqJC3blXd%2FTSrW9aO3vIkHwHnQlp3SXU4Pr1lud4I4%2FYhIBRuPz%2B7AwWRaCQVtjf4lPKiKR5rpFNF%2F6PGw1X4Ga6hLA8dBnTFLjBL6vtZEvFhQHazvWB8kwg6L21QY6pgEmRJjBtXHRfMeovi9UFRhRPMsjJuztvHZzGOxcMDP%2Buj7vnfpHdinNxK59VpcMAXDEw2YNxyUqZYrji0m1oPbtBmR206Ct185wr4Soj7UWpXyG%2FD8eEJ7eKzFq%2B0RuCxo8%2BMczfAgf3H0lfZ6E11Pbk%2BL8YfDMkDEcehUs85YPoOYsiiA2JBIOmEaLnHSMZyIQ9YxP2k58cVgjddzmc0FqkAPbhvXq&X-Amz-Signature=aea32622f90996ef5d4660eb3c4a28f3fbef948fa36f55ffcbd70fd12e49dfdf&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject"></file>
`history-evidence.zip`: 초기부터 R04까지의 `IMPLEMENTATION.md`, R04의 `GRIPPER_SELECTION.md`, Robotiq 2F-85 원본 모델·라이선스·해시를 보존합니다. ZIP SHA256: `bf93f8cf24676f0cf24fe02aed122f90b890bd435179795607fcc57d3e7bc500`.
## 공통 모델 자산
<file src="https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/ea440aba-f595-481b-88e3-59a59d4bd343/common-assets.zip?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4664656UZDO%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002831Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIDXIMsHuEgZmETPAaGDwaPvcSYrB8LcUKzRFKsdEA%2BP%2BAiAwzxKNqi07aVT3EM%2FWYTOoojbAgQTnH5JMZBHYmGNXyCr%2FAwhwEAAaDDYzNzQyMzE4MzgwNSIM5nyu%2FSrEDyPi5D8GKtwDSjWy3um7JRfBOl%2FQgZBKui%2BG9YwfikTEhBWtBGJZ4qEvZ3LkIs%2BQ3q9VMyTYAGQlHm1IpOHclaindz1bLBJOpktJcZzE4mRlMARNCGnkX2tZ%2BDfXIxVvkWdiQJhJcXbOhkBvnhdGp7CCeYn2ab%2ByEjgwSQn2XMzn5KdlkB6F%2BJgdUrD0mizsswo5R7at%2B9P8EGb%2FN%2B6DWmTSw%2BqTMBSjxKbp%2BgnPo1wRBwiXVzkffact9%2B7syB2bM55QoaF3WBU5AexvDGi7ju6MYR9b6YYPuI7vsB83ZmXMGGOAUnuwm2KptDdi4Y%2BNEswlrzlfWeGghiSCIuVxcjSwwMLyPB0A3DFmaQ3g6freEgb8PtIR9MiSIgEACEeNctvX4JmYL6jpy3ZNTAVUt0UgDNa2TpnneZB8Ioe65sBxgOmylZdbaQQ0lweFpt347oeONZSYYsN%2F4VFA4FONKFYnsuxv%2BggTN8zlgOJpwfgbHpvhOwUqYGFR8efng7NjB%2Bu7qaqyiqjYTJQ%2F7ZqJC3blXd%2FTSrW9aO3vIkHwHnQlp3SXU4Pr1lud4I4%2FYhIBRuPz%2B7AwWRaCQVtjf4lPKiKR5rpFNF%2F6PGw1X4Ga6hLA8dBnTFLjBL6vtZEvFhQHazvWB8kwg6L21QY6pgEmRJjBtXHRfMeovi9UFRhRPMsjJuztvHZzGOxcMDP%2Buj7vnfpHdinNxK59VpcMAXDEw2YNxyUqZYrji0m1oPbtBmR206Ct185wr4Soj7UWpXyG%2FD8eEJ7eKzFq%2B0RuCxo8%2BMczfAgf3H0lfZ6E11Pbk%2BL8YfDMkDEcehUs85YPoOYsiiA2JBIOmEaLnHSMZyIQ9YxP2k58cVgjddzmc0FqkAPbhvXq&X-Amz-Signature=acaddb21ccf5021e33c33a0935a24cc6b45e93daa21622286861fdc6a44965ff&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject"></file>
`common-assets.zip`: FR3 시각 메시 8개, 관절·제한 YAML, Franka LICENSE·NOTICE, Robotiq 2F-85 자산, 저장소 LICENSE·NOTICE와 파일별 해시. ZIP SHA256: `7028ea8c63c130284b66d41a5894201b4399290faab743dc1b818baac6e510ad`. 원본 파일 26개와 설명·해시 목록 2개입니다.
R05를 재현하려면 빈 디렉터리에 공통 자산 ZIP을 풀고 R05 ZIP 내부의 `R05/` 내용을 `tools/gripper_concept_demo/`에 배치합니다. 해당 폴더에서 Node.js 22.12 이상으로 `npm ci`, `npm run dev`를 실행합니다. 의존성 설치는 네트워크가 필요할 수 있습니다. R01/R04는 부분 보존본이므로 이 절차만으로 당시 전체 앱이 복원된다고 보장하지 않습니다.
## 버전 관리 규칙
새 버전마다 이 페이지 아래 새 하위 페이지를 만들고 요구사항·변경 이유·부품 구조·치수·동작 순서·검증 결과·사진·ZIP·SHA256·누락을 함께 기록합니다. 이전 버전은 덮어쓰지 않습니다. 재사용 사진은 원래 버전을 표시합니다. 명령 결과가 없는 항목은 검증 완료로 표시하지 않습니다.
## 버전별 상세 페이지
<page url="https://app.notion.com/p/3ebbf0105ac981508ae0d879bc1cba6b">R00 · 초기 절차적 집게·슬라이드 개념</page>
<page url="https://app.notion.com/p/3ebbf0105ac98134a27df322ffd3e53f">R01 · Tesollo DG3FM 12관절·손바닥 인입</page>
<page url="https://app.notion.com/p/3ebbf0105ac981bf8875dea23699008d">R02 · Hand-E + 직선 보조 막대</page>
<page url="https://app.notion.com/p/3ebbf0105ac98188a499c668571ea817">R03 · 생체모방 3관절 주집게 + 2관절 엄지</page>
<page url="https://app.notion.com/p/3ebbf0105ac981769857d32420c74e3f">R04 · Robotiq 2F-85 + 슬림 손끝·보조 엄지</page>
<page url="https://app.notion.com/p/3ebbf0105ac9811b88c3d7fec5ef2b7a">R05 · 일자형 테이퍼 팁·50mm 엄지·6조 척</page>
<page url="https://app.notion.com/p/3ebbf0105ac9816f9ec2d0129c5e1161">R06 · 내부 체결·최소 이동 구조 비교 — 진행 중</page>
<page url="https://app.notion.com/p/3ecbf0105ac98126b38cc13e55b71d62">R07 · 기계 조립 검토 — A/B 구조·모델·검증</page>
<!-- RECORD_END 3ebbf010-5ac9-8137-9e65-c20e9e332bcb -->

<!-- RECORD_START 3ebbf010-5ac9-8150-8ae0-d879bc1cba6b -->
# R00 · 초기 절차적 집게·슬라이드 개념
Record URL: https://app.notion.com/p/3ebbf0105ac981508ae0d879bc1cba6b?pvs=204

상태: 후속안으로 대체. 제작일: 2026-09-30. R00은 이번 아카이브에서 부여한 순서 식별자입니다.
## 목적과 구조
FR3 전체 팔이 볼트를 집어 정렬하고 체결하는 최초 브라우저 시연입니다. 자체 절차적 형상의 몸통 집게, 인입 슬라이드·깔때기, 가변 3조 헤드 척을 조합했습니다. 파지 → 인출 → 손목 정렬 → 슬라이드 인입·가이드 정렬 → 헤드 척 인계 → 집게·안내부 후퇴 → 회전 체결을 보여줬습니다.
## 스펙과 화면
- 볼트: M6×20, M8×35, M10×50.
- 총 재생 길이 36초. FR3는 7축 링크 메시·관절 위치·각도 제한을 저장소의 Franka 자산에서 가져왔습니다.
- 전체/그리퍼 확대/정면/측면, 타임라인, 규격 선택, 외장 투명, 부품 이름표, 확대창, 분해 보기를 제공했습니다.
- 당시 상세 그리퍼 치수와 완전한 형상 파일은 보존되지 않아 확정하지 않습니다.
## 설계 변경 근거
초기 절차적 형상만으로는 관절식 파지와 손바닥 방향 인입을 충분히 표현하기 어려웠습니다. 고정된 손가락 뿌리와 실제 관절 계층을 기준으로 인입 동작을 검토하려고 DG3FM 모델을 적용했습니다. 이 변경안을 R01로 기록했습니다.
## 당시 확인 기록
`IMPLEMENTATION.md`의 초기 Completion evidence에 단위 테스트 8개, TypeScript·빌드·포맷·strict UI 감사 통과가 남아 있습니다. 캐시된 페이지 복귀 시 렌더러를 해제하던 문제와 단계 번호 명도 대비 문제를 수정했습니다. 기존 Python 245개 통과는 저장소 회귀 기록이며 이 그리퍼의 물리 검증이 아닙니다.
## 파일·사진·누락
독립 원본 코드 ZIP과 당시 사진은 확보하지 못했습니다. 이후 버전 사진으로 대체하지 않습니다. 상위 페이지의 `history-evidence.zip` 안 `IMPLEMENTATION.md`가 남아 있는 이력 근거입니다.
## 한계
정해진 경로 재생이며 무더기 접촉, 마찰, 파지력, 토크, 실기 제어를 계산하지 않습니다. FR3 자산은 Apache-2.0이며 자체 코드는 저장소 라이선스를 따릅니다.
<!-- RECORD_END 3ebbf010-5ac9-8150-8ae0-d879bc1cba6b -->

<!-- RECORD_START 3ebbf010-5ac9-8134-a27d-f322ffd3e53f -->
# R01 · Tesollo DG3FM 12관절·손바닥 인입
Record URL: https://app.notion.com/p/3ebbf0105ac98134a27df322ffd3e53f?pvs=204

상태: 후속안으로 대체, 부분 원본 보존. 제작일: 2026-09-30. R01은 이번 아카이브에서 부여한 순서 식별자입니다.
## 설계 목적과 변경
관절 굽힘을 이용한 손바닥 방향 인입을 검토하려고 DG3FM을 기준 모델로 선정했습니다. 초기 슬라이드 집게를 DG3FM 시각 메시와 관절 계층으로 교체했습니다.
## 구조·스펙
- 손가락 3개 × 구동 관절 4개 = 12관절. 원본 URDF의 관절 원점·축·각도 제한을 사용합니다.
- 원본 넓은 손끝 대신 길이 18mm의 작은 볼트용 팁과 반경 3mm 접촉 패드를 추가했습니다.
- 기울어진 볼트를 세 패드가 잡은 채 손가락 뿌리를 고정하고 관절을 굽혀 손바닥 쪽으로 30mm 인입합니다.
- 중앙 안내부·가변 3조 헤드 척·회전 스핀들은 자체 추가 개념 부품입니다. Tesollo의 제공 기능이나 검증 제품으로 주장하지 않습니다.
- 헤드 척이 잡은 뒤 손가락을 열고 바깥쪽으로 펴며 안내부를 후퇴시킨 후 체결합니다. 세 볼트 규격과 36초 시연을 유지했습니다.
## 계산과 당시 검증
순기구학과 각도 제한을 적용한 역기구학으로 오프라인 경로를 생성했습니다. 손가락 뿌리 고정, 강체 링크 길이, 관절 제한, 보간 접촉 오차 0.1mm 미만, 체결 전 팁 공간 확보를 단위 검사했습니다. 당시 단위 12개·브라우저 10개, TypeScript·빌드·포맷·strict UI 감사 통과 및 독립 코드 리뷰 승인 기록이 있습니다. 기하 계산 잔차이며 실제 파지 정확도나 안정성 검증이 아닙니다.
## 원본 첨부
<file src="https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/6afc86b3-5228-4e1f-ad4c-f58199f503a2/DG3FM.zip?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466W2E4X5WL%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002830Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQC3L1zZc8ixHdKIAbucMCgpTQUcqXXgEeuQKLBXiI%2BIxwIgMjJLZLcDXIN53a1dFRs3VioCFXTQnVjCnLs38iPcA1cq%2FwMIcBAAGgw2Mzc0MjMxODM4MDUiDG0OTNp8guk2dkNASyrcA3Zby2pPvq%2FXI2ndSBa%2FuvTn8LLuSIX5ARjFv6p5PTrMwxZs%2FZTqzFogiIYA3N8vxkudpx78u3by4mcYUQ8d8ZYsDcSJuO3W%2BFAe2JeUh%2F3yMYyoNVThzvudxmmk09lT7Lc6Z%2BatsOf66XJTuK9aPoFuyjjyPnGFLHhW6gxT1Ki7fUiiFlLQTnJqN4Y1djFDMhk0PNEspb6xzSwY3fGNfKbhzqGRitCAe370mokM1FyKqRGd%2Bd%2BMCiL4Rni%2FBrfrH42dELnrc%2BTMVchcJDMpjW%2BuUD0mu%2FTArk1EI6IgZStnbQHs8BXEYJmmJFBEo33AxfEZqtf2lqZ68jSbVTPDKHZ35ANF3g3pUt3t8JkOY1t1yhbTS526Z%2Fkc%2B2XN%2Bd%2B%2B3VGxBQyIlhP%2BnENtEK7A1oewsQGGjtdMQs085G5u33HFhFEy5PNp0adq3o3nIOb%2BPxh5W72fIS5tdnpUSMpFZY5O3AGqFG0BqyeTMDoRuE6muuYLQljEUQR7WJxzKAFvOX%2FWzHlTR3oNRRGJFtJwFlg8MCzo5kAboWu8MVjbKgkR7m%2FS2Oe64LbWi7wqQAVjP0V4YqnMmC6B3KXTnZ49gWGZh2vQ51raWkvatMv2PZgjzYsJIYSO3AUIClriMIWh9tUGOqUBNA0WGNICS9M342lDDCQCQ7g715RdYDVM0oHhIIdAjxgnZqD5OctYILcriGWgHkaq508fsMWCmboGtl%2BC4aCSUC3tPu6ipG4WQAFJKSLLEG%2BkH7g7LjA7qV8BSfym5zrNp6t9x1%2BCKSHr%2B2TRjeYbIhP1SkC25K%2FJADyC%2BNhJyHibqGbRV3IeCnhq38xydg2uyB7KvJxpCa338kjBndlBrOpUkAy5&X-Amz-Signature=dcd17a62540ce5edc0bc5debbb07fecef4de50e4421aa31d26e5bab6df39e630&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject"></file>
ZIP SHA256: `7adcfa4c62b1f5234ac9e137ec51e74035926eb48cb65afb7d0f678e543d6a36`.
22개 파일: finger-kinematics.ts, `generate-fingers.py`, fingers.test.ts, dg3fm-data.json, finger-motion.json, SHA256.json, 원본 URDF·MuJoCo XML·DAE 시각 메시 12개·LICENSE·NOTICE.
## 누락과 재현 범위
그리퍼 렌더러·전체 UI·팔 경로를 포함한 당시 실행 프로젝트 전체는 남아 있지 않습니다. 사진은 확보하지 못했습니다. /tmp/dg-\*.png는 나중에 R05 이미지로 덮어써져 이름만 보고 DG3FM 사진으로 사용하지 않았습니다. 원본 충돌 STL도 이 시각 자산 묶음에 없습니다.
## 출처·라이선스
[DG3FM 원본 모델](https://github.com/tesollodelto/tesollo_model/tree/c49d3768900b30e6724fd2c56fe911f04cdfbf18/dg3fm). 고정 커밋 c49d3768900b30e6724fd2c56fe911f04cdfbf18. BSD-3-Clause LICENSE와 Tesollo 저작권·변경 NOTICE를 보존했습니다.
## 다음 변경 이유
파지와 세우기 기능을 분리한 대안을 검토하려고 기존 2지 Robotiq 그리퍼와 작은 보조 막대를 조합했습니다. 깔때기를 제거하고 R02로 전환했습니다.
<!-- RECORD_END 3ebbf010-5ac9-8134-a27d-f322ffd3e53f -->

<!-- RECORD_START 3ebbf010-5ac9-81bf-8875-dea23699008d -->
# R02 · Hand-E + 직선 보조 막대
Record URL: https://app.notion.com/p/3ebbf0105ac981bf8875dea23699008d?pvs=204

상태: 후속안으로 대체, 이력 문서만 보존. 제작일: 2026-09-30.
## 설계 목적과 구조 변화
기존 Robotiq 2지 그리퍼와 작은 보조 도구를 조합해 파지·정렬 기능을 분리하고 깔때기를 제거했습니다. 초기 보조 관절안은 하나의 곧은 막대가 볼트 끝을 위아래로 누르는 구조로 바꿨습니다. 막대의 접근·후퇴와 수직 스트로크를 두 직선축으로 구성했습니다.
## 파지·정렬·체결
Hand-E 본체·손가락 메시와 직선 턱 이동을 유지했습니다. 막대는 나사 끝에서 3mm 떨어진 부분에 접촉하고 주집게의 고정 파지점을 중심으로 볼트를 돌려 헤드가 위를 향하도록 합니다. 보조 접촉 → 파지력 감소 가정 → 세우기 → 재파지 → 막대 이탈 순서입니다.
기존 헤드 척으로 인계한 뒤 척이 53mm 전진해 Hand-E 손끝과 체결면 사이 공간을 확보했습니다. 새 도구 높이에 맞춰 팔 경로를 다시 계산했습니다.
## 설계 변경 근거
주집게의 관절 굽힘까지 활용하는 구조를 검토하려고 양쪽 손가락을 재설계하고 R03 생체모방안으로 변경했습니다.
## 파일·사진·검증
이 버전의 독립 소스 스냅샷·사진·개별 테스트 결과 원본은 확보하지 못했습니다. 상위 페이지 `history-evidence.zip`의 `IMPLEMENTATION.md`, Hand-E + straight rod revision 절에 변경 기록이 남아 있습니다. DG3FM 원본 일부를 /tmp/gripper-demo-dg3fm-reference로 옮긴 사실도 해당 기록에 있습니다.
## 한계·출처
원래 저장소의 Hand-E 자산을 활용했고 vendored 원본이나 ROS 소스는 바꾸지 않았다는 기록이 있습니다. 여기에는 당시 자산 자체가 없으므로 제조사 CAD 재배포나 라이선스 전체 확보를 주장하지 않습니다. 파지력 감소·마찰·회전 안정성은 설명용 가정이며 물리 시뮬레이션이 아닙니다.
<!-- RECORD_END 3ebbf010-5ac9-81bf-8875-dea23699008d -->

<!-- RECORD_START 3ebbf010-5ac9-8188-a499-c668571ea817 -->
# R03 · 생체모방 3관절 주집게 + 2관절 엄지
Record URL: https://app.notion.com/p/3ebbf0105ac98188a499c668571ea817?pvs=204

상태: 후속안으로 대체, 이력 문서만 보존. 제작일: 2026-09-30.
## 설계 판단과 구조
양쪽 주집게의 관절 굽힘으로 파지와 자세 변경을 수행하는 생체모방 구조를 검토했습니다. Hand-E 본체와 직선 막대 대신 자체 절차적 손바닥, 주손가락 2개(각 3관절), 더 가는 보조 엄지(2관절)를 구성했습니다. 깔때기와 직선 슬라이더 정렬 장치는 제거했습니다.
## 동작·스펙
주손가락이 몸통을 잡고 보조 엄지가 나사 끝에서 3mm 떨어진 지점을 눌러 고정 파지점 주위로 회전시킵니다. 헤드는 위, 나사 끝은 아래로 정렬한 뒤 별도 척에 인계합니다. 헤드 홀더 연장량은 70mm로 바뀌었습니다. M6×20, M8×35, M10×50을 대상으로 했습니다.
## 당시 검증
강체 손가락 길이, 양쪽 주손가락 접촉, 엄지 접촉, 공간 확보, 헤드 위쪽 방향을 검사하는 회귀 테스트를 추가했습니다. 단위 테스트 14개가 통과했다는 결과는 `IMPLEMENTATION.md`에 기록되어 있습니다. 당시 브라우저 전체 결과나 정밀 치수표는 독립 기록이 없어 확정하지 않습니다.
## 다음 변경 이유
실제 빈픽킹 제품의 링크 구조를 기준으로 설계 타당성을 검토하려고 공개 자산을 확보할 수 있는 Robotiq 2F-85로 바꿨습니다. 임의 생체모방 형상을 제품의 검증 성능으로 설명하지 않도록 실제 본체·종속 관절과 커스텀 부품을 구분했습니다.
## 파일·사진·누락
독립 코드·당시 사진은 확보하지 못했습니다. 상위 `history-evidence.zip` 안 `IMPLEMENTATION.md`의 Final biomimetic revision 절이 이력 근거입니다. 원본이 없는 관절 링크 수치나 구동기 정격은 복원해 만들지 않았습니다.
## 한계
단순 형상·설명용 모션입니다. 접촉 안정성·마찰·구동력·전 기구 충돌·실물 제작 성능을 검증하지 않았습니다.
<!-- RECORD_END 3ebbf010-5ac9-8188-a499-c668571ea817 -->

<!-- RECORD_START 3ebbf010-5ac9-8176-9857-d32420c74e3f -->
# R04 · Robotiq 2F-85 + 슬림 손끝·보조 엄지
Record URL: https://app.notion.com/p/3ebbf0105ac981769857d32420c74e3f?pvs=204

상태: 후속안으로 대체, 부분 소스와 제품 자산 보존. 제작일: 2026-09-30.
## 변경 이유와 선정 근거
관절식 2지 파지와 실제 빈픽킹 제품의 링크 구조를 함께 검토하려고 Robotiq 2F-85 본체·관절 링크를 적용했습니다. 실제 무더기 볼트 사례인 Dürr x-elect/Optonic, 작은 나사 공급 사례, 손끝 설계 지침을 비교했습니다. 전체 조건에서 최적인 그리퍼를 입증했다는 결론은 아닙니다.
## 구조·스펙
- 공개 모델의 실제 메시 7개와 URDF 링크 구조·종속 관절 관계를 사용합니다.
- 폭 6mm의 규격별 슬림 교환 손끝, 별도 2R 엄지, 별도 3조 헤드 척은 자체 개념 부품입니다.
- 주집게 몸통 파지 → 리프트 → 엄지 접촉 → 낮은 파지력 가정 → 끝부분을 눌러 헤드를 위로 세움 → 헤드 척 인계 → 손끝 이탈.
- 척 전진 70mm. 열린 척 반경 24mm, 허브 후퇴, 볼트와 척의 공통 30° 위상으로 확인된 간섭을 수정했습니다.
- 제품 자체 손가락을 각각 독립 구동하는 것으로 표현하지 않습니다. 엄지는 별도 구동부입니다.
## 당시 검증
단위 테스트 15개, 브라우저 10개, TypeScript·Vite 빌드·Prettier·strict UI 감사 통과. 독립 코드 검토에서 추가 중요 지적이 없었다는 이력입니다. 당시 결과 기록이며 새 실행은 하지 않았습니다.
## 원본 파일
<file src="https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/292f4f81-459c-4a4e-96eb-0459e313bcf0/R04.zip?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4666MF3NXZL%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002831Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJIMEYCIQDR2WjkRiLjatYgW0wFnDhLl1gNBFqWFiRnUhxszkRU0QIhANw2YcYipzB6AwQYl5hPul85SYf1F1pUzjkG9zKLce1SKv8DCG8QABoMNjM3NDIzMTgzODA1IgwpIC1B9Q%2Fjc801BLcq3AMIjKJLwrUGv%2FIeJ68YQk2Ko6jitFqTOnmGoUWP9sTcM15yVt6Xot7zGiKbkAnsu9UsgORLuNcneTBBRtDCGZezn8AhkCkrZghuGLMnYpqogpmqfCEjEup5gBCiFt9IOdq3oQdkK60n%2BVjdHiIyo8ZJN14yIO0VFF%2FBrNLea%2FdUtpQHhxvunrpneKD7IMfqn9gDljmBjeqYjbBZeQL4JGTjG9uoMjmlVV65BpWjrRiEu5zOchsfuEQPzLWI7EXWFxQ%2FqMy3EP1nJse0zNJ5N9IPYAeePxVzC0oySjU1jMEe1HGzsDHsfpwMbefCSWH9vSHdFmwfJek%2BtV7LFQv5CD0Vp6W7LiXrRsSW8vVICciuJhQ89LgN2rHJgxW8mOWE42xpE0oXY380oeAWoxpYzNeEgMDqmMjwq3%2FqerPIfrzhVdpqvLG0iNi%2FlJv3ITkNU63Lv4GfRC13TwtD19SpiQryNLPnG2yfUTqLOwtdarVe9ugFrJfcTcedPB9V0NotMLFxqHbI31rftaqSER0iHUJ2vBP7PCNdLlZd%2F%2FPMPoJE%2F%2Bn9hIrWdqznesSlvK7bbmvTjd174C1nQl%2Fnb%2FzgoHM%2BJc2IMmIURX7bAn3ZUynamOW%2BbuE7tY1tSUrw%2FzCwn%2FbVBjqkAY25JIU9gvCguFZwUU2%2BErTuPKKmAilFCF1DLzJya3mMjObCaOu6kotI9lbOnictaTlKeWRrsRLn27N8Hc1C6M0jg0wArGTzKNhiCawzWkJOIjn%2F71iGM%2FRjLhCixkccDewKul%2FN%2BxUP%2FGSY1mb2kLzqmQ2y8wzND2A67QTNvbaa%2B6gl7dgJlYwqZWHJIcbLqJXAPnImOt1MRQftxeqmu4phb7Ex&X-Amz-Signature=3a6a1a2bce9d3384b47163891d4232d5b98161e457cd480e9bae5a15efcb4042&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject"></file>
ZIP SHA256: `b3d44c35ec4526a30d5f91259d42a9b84d869fd487a816cc56faf57cba80a7c4`.
당시 남아 있던 8개 소스 파일과 SHA256.json입니다: gripper.ts, rod-kinematics.ts, kinematics.ts, motion-data.json, timeline.ts, main.ts, models.ts, viewer.ts.
상위 `history-evidence.zip`에 `GRIPPER_SELECTION.md`와 robotiq-2f85 원본 메시·URDF·LICENSE·NOTICE·해시를 별도로 보존했습니다.
## 누락
당시 사진은 확보하지 못했습니다. R04의 package/lockfile·테스트·스타일을 포함한 전체 실행 스냅샷은 남아 있지 않습니다. 보존 ZIP을 완전한 재실행 패키지로 안내하지 않습니다.
## R05로 변경한 이유
규격마다 손끝을 바꾸는 방식과 길게 전진하는 척을 재검토했습니다. 전체 구조 경량화·작은 엄지·모든 규격에서 같은 팁·헤드 자동 조절이 다음 목표였습니다. R04에는 실제 체결 구동부가 생략되어 있어 이후 완성 도구의 질량·길이 비교 기준으로 쓰지 않습니다.
## 출처·라이선스
[Robotiq 제품](https://robotiq.com/products/adaptive-grippers), [Dürr 적용 사례](https://www.durr-group.com/en/duerrmore/helper-with-a-sharp-eye), [Optonic 볼트 빈픽킹](https://www.optonic.com/en/usecases/bolt-picking-with-mikado/), [Pickit 도구 설계](https://docs.pickit3d.com/en/3.5/optimize-your-application/hardware/faq-robot-tool.html).
시각 자산은 PickNik Robotics ros2_robotiq_gripper 패키지의 BSD-3-Clause 자산이며 보존한 NOTICE에 가공 범위를 명시합니다. 실제 파지 성공률·유분 조건·반력·토크는 미검증입니다.
<!-- RECORD_END 3ebbf010-5ac9-8176-9857-d32420c74e3f -->

<!-- RECORD_START 3ebbf010-5ac9-811b-88c3-d7fec5ef2b7a -->
# R05 · 일자형 테이퍼 팁·50mm 엄지·6조 척
Record URL: https://app.notion.com/p/3ebbf0105ac9811b88c3d7fec5ef2b7a?pvs=204

상태: R06 착수 전 동결 스냅샷. 기록일: 2026-09-30.
## 설계 조건과 변경
M6\~M10을 모두 최종 체결하고 규격별 소켓을 교환하지 않으며 헤드에 자동으로 맞물리는 여러 턱을 사용합니다. 주집게는 관절 손가락에서 일자형 테이퍼 팁 2개로 변경했습니다. 모든 규격에 같은 팁과 같은 척을 쓰고 간격만 조절합니다. 깔때기와 Gator-Grip 핀 배열은 채택하지 않았습니다.
## 부품 스펙과 구조
- 파지 모듈: Zimmer GEP2006IL-03-B급 설치 공간, 6mm/측 스트로크, 180g. 본체 44×22×69mm, 턱 포함 높이 85.5mm. 제조사 CAD 복제가 아닙니다.
- 주집게: 길이 58mm 강체 팁. 뿌리 8×8mm → 끝 3×4mm. 끝의 수동 회전 패드가 볼트 회전을 따릅니다.
- 보조 엄지: 25+25=50mm의 2링크. 이전 55+50=105mm보다 총길이를 약 52% 줄였습니다. 두 구동기는 본체 쪽에 두고 텐던을 통해 전달합니다.
- 엄지 베이스는 파지점 기준 Y+33mm, Z−10mm. M6/M8과 M10의 팔꿈치 방향을 구분하고 M10 접근은 바깥으로 우회합니다. 모듈 후퇴 후 엄지를 접습니다.
- 헤드 척: 육각 대변 10/13/17mm에 맞춰 닫히는 6개 방사형 강체 턱. 착좌 전진 18mm, 쐐기 캠·추력 베어링·잠금 구조의 개념 형상.
- 캠 외반경 20.5mm / 하우징 내반경 20.8mm: 방사상 기하 간극 0.3mm. 제조 공차나 변형을 포함한 설계 허용값은 아닙니다.
- 파지 모듈 후퇴: 뒤 35mm·위 35mm의 단일 대각 레일, 스트로크 약 49.5mm.
- 체결부: Kolver KDS-PL50CA급 설치 공간 Ø57×322mm, 1.8kg, 기준 범위 5\~50Nm. 고정 하우징·회전축·베어링·축방향 컴플라이언스를 구분합니다.
- 알려진 구매부품 질량 합계 1.98kg. 척·레일·엄지·구동기·장착·배선 질량은 미산정이므로 총질량 경량화를 확정하지 않습니다.
## 동작과 체결
몸통 파지 → 인출 → 수동 회전 패드와 엄지로 약 90° 세움 → 척 18mm 착좌 → 6조 헤드 잠금 → 집게 해제 → 파지 모듈 대각 후퇴 → 지그 도킹 → 회전·삽입 → 해제.
총 70초. 삽입 23\~61초, 최종 토크 단계 61\~63초, 해제 63\~65초. 피치 M6=1 / M8=1.25 / M10=1.5mm로 회전량과 삽입량을 맞췄습니다. M10 최대 약 79rpm로 기준 스핀들의 90rpm 이내라는 계산입니다. 표시 8/20/40Nm는 시연 목표값이며 추천값·측정값이 아닙니다.
체결 지그의 수직 키 홈이 하우징 탭을 받아 반력을 작업대로 전달하고 축방향 이동을 허용합니다. 로봇 손목으로 체결 반력을 모두 지탱한다고 가정하지 않습니다.
## 당시 검증 기록
당시 개발 검증 결과 요약: 단위 18/18, 브라우저 10/10(약 1.4분), 마지막 하우징·라벨 변경 후 관련 브라우저 2개 재검증(16.7초), TypeScript·format:check·build 통과. Vite 약 890kB raw / 248kB gzip 크기 경고만 남았습니다. 보존된 test-results/.last-run.json은 passed입니다.
FR3 경로는 규격별 701프레임, 최대 계산 위치 잔차 약 0.0001mm였습니다. 실제 로봇 정확도를 뜻하지 않습니다. 이번 아카이브 작업에서 테스트를 새로 실행하지 않았습니다.
## 원본 코드·문서 ZIP
<file src="https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/64574f98-2a01-4345-8793-68e8a5ac0ed5/R05.zip?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466TZSDUK34%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002831Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIEBHXUqppQLmWefI851N5qwXv0KlBdn4HC%2B2xxDVeSolAiBEVPDwshafMzEJ%2FMzmf6vio0l0DMCi7w6sqxCK795v0ir%2FAwhwEAAaDDYzNzQyMzE4MzgwNSIMFRJiwyQNWPDjwyrfKtwD%2FYfm7ylElC1y6IJdKU1o%2FsBEwBOb3%2B5ibVKAvZQLzKT9tHVX1rd%2BKMiuQAJ5Loe%2BUnkkuRPa4keBDwqfmgzsqWbB6nR%2BJ%2BgFWRafzu6SKCMUC5hZVu4jRfupaUEVUosT2ORYAbQjw2xtoGpZPfZFIRducqVXwCUJxTRTdEVizUtMR4TZsYvRdaX8cy7uLri0i2OVUMTKrNRbDz1Jf9K9SmEbuHkmDPhJpJTWIt1C4YK%2F33E%2BMNnTB8gNoRXELmfSGnCUKvgrum0%2BEzJxW%2BiP%2Bzc1S3TyePDqGzgva8u3eg43k32dX7mwOGEuhxpDrOLquJCaB0bgBgJ%2FmPeSvcVTwwM0FH7Rt3abY17tG8j29gZO0It4NFMBbaiZi78pyCCVcCaxQQ9UxJQd0p%2BkthvHbhVskMUhyDBi0c%2F8V9b3Y3xstAKbWj6ikATdQ3WT8zF2sDCuBO9cflIClKc6qrChpxKUJdn6QoWAyvQFmi99ly8VL%2FzpRzslpa7IJQit02Sy2tyP%2FOo8TTLk0%2BgLLKyM0DSWpP%2FlgAKv%2FAF1G0Bwsn4EGq%2BSfvFHTRUkPqe7bZWH25bJi4zrXbHPuawvcp9MsCc04Wy6FaZY6Vo8PA5m0ceZfaluAXcBY7BclP0wn6H21QY6pgH6fJkTc6%2FTKqqb5XrNVgo2SRzkPJNBT7RtiY3vsSkWV3Trgqgelawj8LrhZnH8JHWJWMzDdlzwzdf8dFSOiTXw14mA%2FaCPepBvhtGKvrXtruSH9cKwiWmhl%2B7ntXp5TExsqhrBXAzujqBeeH8wx%2B39UbdxojoFrD%2BU0ith94l%2BPn3mbhacuOMk6VghDJ2PlfBK6OOq3GyxwgtSREmi%2B3Rp0PnEESGL&X-Amz-Signature=26b54539e7a380bfc99dd44e87426860d3a234621cba7401514eeda26a98a2af&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject"></file>
ZIP SHA256: `2c6fc2465ca237eeaeb8904e27d3055887d8679287164e3fa4bb7d6d5d15a3ff`.
35개 파일: src 전체, tests, scripts, README·REDESIGN·DESIGN·IMPLEMENTATION, package/lockfile, Vite/TypeScript/Playwright 설정, index.html, test-results 사진 5장과 결과, SHA256.json.
이 ZIP에는 node_modules·빌드 결과와 FR3 공통 자산이 포함되지 않습니다. prepare-assets.mjs는 원래 저장소의 Franka 자산을 참조하므로 독립 실행 완전 패키지로 오인하지 않습니다.
공통 모델 자산은 상위 기록 페이지의 `common-assets.zip`에 별도로 첨부했습니다. 함께 받아 기록된 상대 경로대로 배치하면 R05 준비 스크립트에 필요한 원본이 확보됩니다.
## 실제 R05 화면
### 전체 로봇
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/26241b16-8f6e-43c3-b873-acedb5c5af29/R05-whole.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466TZSDUK34%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002831Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIEBHXUqppQLmWefI851N5qwXv0KlBdn4HC%2B2xxDVeSolAiBEVPDwshafMzEJ%2FMzmf6vio0l0DMCi7w6sqxCK795v0ir%2FAwhwEAAaDDYzNzQyMzE4MzgwNSIMFRJiwyQNWPDjwyrfKtwD%2FYfm7ylElC1y6IJdKU1o%2FsBEwBOb3%2B5ibVKAvZQLzKT9tHVX1rd%2BKMiuQAJ5Loe%2BUnkkuRPa4keBDwqfmgzsqWbB6nR%2BJ%2BgFWRafzu6SKCMUC5hZVu4jRfupaUEVUosT2ORYAbQjw2xtoGpZPfZFIRducqVXwCUJxTRTdEVizUtMR4TZsYvRdaX8cy7uLri0i2OVUMTKrNRbDz1Jf9K9SmEbuHkmDPhJpJTWIt1C4YK%2F33E%2BMNnTB8gNoRXELmfSGnCUKvgrum0%2BEzJxW%2BiP%2Bzc1S3TyePDqGzgva8u3eg43k32dX7mwOGEuhxpDrOLquJCaB0bgBgJ%2FmPeSvcVTwwM0FH7Rt3abY17tG8j29gZO0It4NFMBbaiZi78pyCCVcCaxQQ9UxJQd0p%2BkthvHbhVskMUhyDBi0c%2F8V9b3Y3xstAKbWj6ikATdQ3WT8zF2sDCuBO9cflIClKc6qrChpxKUJdn6QoWAyvQFmi99ly8VL%2FzpRzslpa7IJQit02Sy2tyP%2FOo8TTLk0%2BgLLKyM0DSWpP%2FlgAKv%2FAF1G0Bwsn4EGq%2BSfvFHTRUkPqe7bZWH25bJi4zrXbHPuawvcp9MsCc04Wy6FaZY6Vo8PA5m0ceZfaluAXcBY7BclP0wn6H21QY6pgH6fJkTc6%2FTKqqb5XrNVgo2SRzkPJNBT7RtiY3vsSkWV3Trgqgelawj8LrhZnH8JHWJWMzDdlzwzdf8dFSOiTXw14mA%2FaCPepBvhtGKvrXtruSH9cKwiWmhl%2B7ntXp5TExsqhrBXAzujqBeeH8wx%2B39UbdxojoFrD%2BU0ith94l%2BPn3mbhacuOMk6VghDJ2PlfBK6OOq3GyxwgtSREmi%2B3Rp0PnEESGL&X-Amz-Signature=8dd64e25d2ff44eddc197ba2644af892dc026d92e5aca8f23cfff5470dc2bfa9&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
### 보조 엄지로 세우기 · 13초
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/560d5aa9-870c-4b84-8da7-a1995e6e96d1/R05-alignment.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466TZSDUK34%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002831Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIEBHXUqppQLmWefI851N5qwXv0KlBdn4HC%2B2xxDVeSolAiBEVPDwshafMzEJ%2FMzmf6vio0l0DMCi7w6sqxCK795v0ir%2FAwhwEAAaDDYzNzQyMzE4MzgwNSIMFRJiwyQNWPDjwyrfKtwD%2FYfm7ylElC1y6IJdKU1o%2FsBEwBOb3%2B5ibVKAvZQLzKT9tHVX1rd%2BKMiuQAJ5Loe%2BUnkkuRPa4keBDwqfmgzsqWbB6nR%2BJ%2BgFWRafzu6SKCMUC5hZVu4jRfupaUEVUosT2ORYAbQjw2xtoGpZPfZFIRducqVXwCUJxTRTdEVizUtMR4TZsYvRdaX8cy7uLri0i2OVUMTKrNRbDz1Jf9K9SmEbuHkmDPhJpJTWIt1C4YK%2F33E%2BMNnTB8gNoRXELmfSGnCUKvgrum0%2BEzJxW%2BiP%2Bzc1S3TyePDqGzgva8u3eg43k32dX7mwOGEuhxpDrOLquJCaB0bgBgJ%2FmPeSvcVTwwM0FH7Rt3abY17tG8j29gZO0It4NFMBbaiZi78pyCCVcCaxQQ9UxJQd0p%2BkthvHbhVskMUhyDBi0c%2F8V9b3Y3xstAKbWj6ikATdQ3WT8zF2sDCuBO9cflIClKc6qrChpxKUJdn6QoWAyvQFmi99ly8VL%2FzpRzslpa7IJQit02Sy2tyP%2FOo8TTLk0%2BgLLKyM0DSWpP%2FlgAKv%2FAF1G0Bwsn4EGq%2BSfvFHTRUkPqe7bZWH25bJi4zrXbHPuawvcp9MsCc04Wy6FaZY6Vo8PA5m0ceZfaluAXcBY7BclP0wn6H21QY6pgH6fJkTc6%2FTKqqb5XrNVgo2SRzkPJNBT7RtiY3vsSkWV3Trgqgelawj8LrhZnH8JHWJWMzDdlzwzdf8dFSOiTXw14mA%2FaCPepBvhtGKvrXtruSH9cKwiWmhl%2B7ntXp5TExsqhrBXAzujqBeeH8wx%2B39UbdxojoFrD%2BU0ith94l%2BPn3mbhacuOMk6VghDJ2PlfBK6OOq3GyxwgtSREmi%2B3Rp0PnEESGL&X-Amz-Signature=fbb16c5085be118ea0a27417f5f34de52d94dea05e94e25d3847a37048a41fa6&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
### 헤드 척 인계 · 16초
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/57328739-69a8-4a7e-bf15-3303bfbd3781/R05-handoff.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466TZSDUK34%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002831Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIEBHXUqppQLmWefI851N5qwXv0KlBdn4HC%2B2xxDVeSolAiBEVPDwshafMzEJ%2FMzmf6vio0l0DMCi7w6sqxCK795v0ir%2FAwhwEAAaDDYzNzQyMzE4MzgwNSIMFRJiwyQNWPDjwyrfKtwD%2FYfm7ylElC1y6IJdKU1o%2FsBEwBOb3%2B5ibVKAvZQLzKT9tHVX1rd%2BKMiuQAJ5Loe%2BUnkkuRPa4keBDwqfmgzsqWbB6nR%2BJ%2BgFWRafzu6SKCMUC5hZVu4jRfupaUEVUosT2ORYAbQjw2xtoGpZPfZFIRducqVXwCUJxTRTdEVizUtMR4TZsYvRdaX8cy7uLri0i2OVUMTKrNRbDz1Jf9K9SmEbuHkmDPhJpJTWIt1C4YK%2F33E%2BMNnTB8gNoRXELmfSGnCUKvgrum0%2BEzJxW%2BiP%2Bzc1S3TyePDqGzgva8u3eg43k32dX7mwOGEuhxpDrOLquJCaB0bgBgJ%2FmPeSvcVTwwM0FH7Rt3abY17tG8j29gZO0It4NFMBbaiZi78pyCCVcCaxQQ9UxJQd0p%2BkthvHbhVskMUhyDBi0c%2F8V9b3Y3xstAKbWj6ikATdQ3WT8zF2sDCuBO9cflIClKc6qrChpxKUJdn6QoWAyvQFmi99ly8VL%2FzpRzslpa7IJQit02Sy2tyP%2FOo8TTLk0%2BgLLKyM0DSWpP%2FlgAKv%2FAF1G0Bwsn4EGq%2BSfvFHTRUkPqe7bZWH25bJi4zrXbHPuawvcp9MsCc04Wy6FaZY6Vo8PA5m0ceZfaluAXcBY7BclP0wn6H21QY6pgH6fJkTc6%2FTKqqb5XrNVgo2SRzkPJNBT7RtiY3vsSkWV3Trgqgelawj8LrhZnH8JHWJWMzDdlzwzdf8dFSOiTXw14mA%2FaCPepBvhtGKvrXtruSH9cKwiWmhl%2B7ntXp5TExsqhrBXAzujqBeeH8wx%2B39UbdxojoFrD%2BU0ith94l%2BPn3mbhacuOMk6VghDJ2PlfBK6OOq3GyxwgtSREmi%2B3Rp0PnEESGL&X-Amz-Signature=d5b176f0ee396b8c98c0303e9db291bf417e6f318f62796076ce47611dc03c5f&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
### 회전 체결 · 27초
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/c592e5e9-fc76-4868-a4a0-a94c1c8ea20f/R05-fastening.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466TZSDUK34%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002831Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIEBHXUqppQLmWefI851N5qwXv0KlBdn4HC%2B2xxDVeSolAiBEVPDwshafMzEJ%2FMzmf6vio0l0DMCi7w6sqxCK795v0ir%2FAwhwEAAaDDYzNzQyMzE4MzgwNSIMFRJiwyQNWPDjwyrfKtwD%2FYfm7ylElC1y6IJdKU1o%2FsBEwBOb3%2B5ibVKAvZQLzKT9tHVX1rd%2BKMiuQAJ5Loe%2BUnkkuRPa4keBDwqfmgzsqWbB6nR%2BJ%2BgFWRafzu6SKCMUC5hZVu4jRfupaUEVUosT2ORYAbQjw2xtoGpZPfZFIRducqVXwCUJxTRTdEVizUtMR4TZsYvRdaX8cy7uLri0i2OVUMTKrNRbDz1Jf9K9SmEbuHkmDPhJpJTWIt1C4YK%2F33E%2BMNnTB8gNoRXELmfSGnCUKvgrum0%2BEzJxW%2BiP%2Bzc1S3TyePDqGzgva8u3eg43k32dX7mwOGEuhxpDrOLquJCaB0bgBgJ%2FmPeSvcVTwwM0FH7Rt3abY17tG8j29gZO0It4NFMBbaiZi78pyCCVcCaxQQ9UxJQd0p%2BkthvHbhVskMUhyDBi0c%2F8V9b3Y3xstAKbWj6ikATdQ3WT8zF2sDCuBO9cflIClKc6qrChpxKUJdn6QoWAyvQFmi99ly8VL%2FzpRzslpa7IJQit02Sy2tyP%2FOo8TTLk0%2BgLLKyM0DSWpP%2FlgAKv%2FAF1G0Bwsn4EGq%2BSfvFHTRUkPqe7bZWH25bJi4zrXbHPuawvcp9MsCc04Wy6FaZY6Vo8PA5m0ceZfaluAXcBY7BclP0wn6H21QY6pgH6fJkTc6%2FTKqqb5XrNVgo2SRzkPJNBT7RtiY3vsSkWV3Trgqgelawj8LrhZnH8JHWJWMzDdlzwzdf8dFSOiTXw14mA%2FaCPepBvhtGKvrXtruSH9cKwiWmhl%2B7ntXp5TExsqhrBXAzujqBeeH8wx%2B39UbdxojoFrD%2BU0ith94l%2BPn3mbhacuOMk6VghDJ2PlfBK6OOq3GyxwgtSREmi%2B3Rp0PnEESGL&X-Amz-Signature=c50f6907c0ee935cf408b2faf5d972e0fefbee27eb303f53824bbb3073a78cc6&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
### 분해 보기
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/74ce179d-d8d0-4b24-983c-b976f2cf4e8c/R05-exploded.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466TZSDUK34%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002831Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJGMEQCIEBHXUqppQLmWefI851N5qwXv0KlBdn4HC%2B2xxDVeSolAiBEVPDwshafMzEJ%2FMzmf6vio0l0DMCi7w6sqxCK795v0ir%2FAwhwEAAaDDYzNzQyMzE4MzgwNSIMFRJiwyQNWPDjwyrfKtwD%2FYfm7ylElC1y6IJdKU1o%2FsBEwBOb3%2B5ibVKAvZQLzKT9tHVX1rd%2BKMiuQAJ5Loe%2BUnkkuRPa4keBDwqfmgzsqWbB6nR%2BJ%2BgFWRafzu6SKCMUC5hZVu4jRfupaUEVUosT2ORYAbQjw2xtoGpZPfZFIRducqVXwCUJxTRTdEVizUtMR4TZsYvRdaX8cy7uLri0i2OVUMTKrNRbDz1Jf9K9SmEbuHkmDPhJpJTWIt1C4YK%2F33E%2BMNnTB8gNoRXELmfSGnCUKvgrum0%2BEzJxW%2BiP%2Bzc1S3TyePDqGzgva8u3eg43k32dX7mwOGEuhxpDrOLquJCaB0bgBgJ%2FmPeSvcVTwwM0FH7Rt3abY17tG8j29gZO0It4NFMBbaiZi78pyCCVcCaxQQ9UxJQd0p%2BkthvHbhVskMUhyDBi0c%2F8V9b3Y3xstAKbWj6ikATdQ3WT8zF2sDCuBO9cflIClKc6qrChpxKUJdn6QoWAyvQFmi99ly8VL%2FzpRzslpa7IJQit02Sy2tyP%2FOo8TTLk0%2BgLLKyM0DSWpP%2FlgAKv%2FAF1G0Bwsn4EGq%2BSfvFHTRUkPqe7bZWH25bJi4zrXbHPuawvcp9MsCc04Wy6FaZY6Vo8PA5m0ceZfaluAXcBY7BclP0wn6H21QY6pgH6fJkTc6%2FTKqqb5XrNVgo2SRzkPJNBT7RtiY3vsSkWV3Trgqgelawj8LrhZnH8JHWJWMzDdlzwzdf8dFSOiTXw14mA%2FaCPepBvhtGKvrXtruSH9cKwiWmhl%2B7ntXp5TExsqhrBXAzujqBeeH8wx%2B39UbdxojoFrD%2BU0ith94l%2BPn3mbhacuOMk6VghDJ2PlfBK6OOq3GyxwgtSREmi%2B3Rp0PnEESGL&X-Amz-Signature=42488b226abccb30c79cbb5dd46528717f8278ffce7c73e7cee545d5e89db935&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
## 설계 근거
ZIP의 `REDESIGN.md`에 제품 비교 전체와 원문 URL을 보존했습니다. [Zimmer 치수 자료](https://www.zimmer-group.com/fileadmin/pim/MER/GD/PG/MER_GD_PG_GEP2006IL-00-B__SEN__APD__V1.pdf), [Kolver 카탈로그](https://kolver.com/upl/EN_Catalog_KDUCER.pdf), [Franka 제어 파라미터](https://support.franka.de/docs/control_parameters.html). 해당 수치는 당시 설계 기록에서 옮겼으며 이번 보존 작업에서 제조사 최신값을 다시 검증한 것은 아닙니다.
## 남은 한계와 R06 변경 사유
육각 위상이 맞은 상태를 가정합니다. 실제 자동 위상 탐색(±30° 이내 저토크 탐색), 착좌·잠금 센서, 나사 물림 실패 복구, 마찰·응력·전체 기구 충돌·무더기 접촉 물리는 구현하지 않았습니다.
볼트 접근 단면과 체결부 전진 동작을 줄이기 위해 더 날카로운 팁과 본체 내부 회전 구조를 다음 설계 목표로 정했습니다. R06에서는 별도 내부 척과 주집게 수납안, 주집게 자체가 파지와 헤드 체결을 겸하는 최소 이동안을 비교합니다.
<!-- RECORD_END 3ebbf010-5ac9-811b-88c3-d7fec5ef2b7a -->

<!-- RECORD_START 3ebbf010-5ac9-816f-9ec2-d0129c5e1161 -->
# R06 · 내부 체결·최소 이동 구조 비교 — 진행 중
Record URL: https://app.notion.com/p/3ebbf0105ac9816f9ec2d0129c5e1161?pvs=204

상태: 내부 체결 구조 비교·검토 중. 설계 시작일: 2026-09-30. 기록 갱신일: 2026-10-01. R05 이후의 R06 설계이며 R07 조립뷰와 구분합니다. 구동 방식이 미정이고 간섭 문제가 남아 있어 제작용으로 승인할 수 없습니다.
## 설계 목표
- 볼트 접근용 팁을 더 날카롭게 합니다.
- 체결 척이 앞으로 돌출하지 않고 본체 내부에서 회전하도록 합니다.
- 구조와 움직임을 줄입니다. 수납만 추가하는 절첩 구조에 한정하지 않고 파지·정렬·체결 기능을 함께 검토합니다.
## 비교할 두 안
### A · 별도 내부 척 + 주집게 수납
주집게가 볼트를 파지·정렬한 뒤 본체 내부 척으로 인계합니다. 주집게는 체결면을 비우도록 수납합니다. 척의 전진을 최소화하거나 제거하고 내부 회전 경계를 분리하는 안입니다.
### B · 같은 집게가 파지와 헤드 체결을 겸함
하나의 집게가 몸통 파지와 헤드 체결을 겸하고 최소 움직임·구조를 지향합니다. 기능 전환, 헤드 유지, 회전축과 고정부 분리, 볼트 자세·위치 연속성은 구현·검증할 항목입니다.
## 검토 형상의 잠정 치수
보존된 `archive/R06/R06.md` 기준 형상값입니다. 구동력·잠금 강도·간섭 해소가 검증된 제작 치수는 아닙니다.
- 주집게 팁: 뿌리 6×5mm → 끝 1.6×2.4mm의 평면 3단 테이퍼. 작은 평면 접촉 패드를 남깁니다.
- 보조 엄지: 25+25mm의 2링크. 헤드 가까운 몸통을 잡은 상태에서 볼트를 세웁니다.
- 체결부 축방향 전진: A/B 모두 0mm. 내부 헤드 접촉면의 축방향 위치를 고정하고 볼트 삽입은 팔의 이동으로 표현합니다.
- A 수납 경로: 주집게 모듈이 뒤 52mm·위 20mm, 총 약 55.7mm 이동합니다. 별도 6조 헤드 척이 유지 기능을 넘겨받습니다.
- B 수납 경로: 같은 회전 카세트에 몸통 팁과 헤드 접촉면을 두고 팁만 24mm 수납합니다. 별도 6조 척을 제거한 구조입니다.
- 외장: 개념 내반경 39mm·외반경 42.5mm. 뒤쪽 개구가 있어 완전 밀폐형이 아닙니다.
## 제작 설계 미확정 항목
위 치수와 경로는 검토 형상의 잠정값입니다. 부품 수·구동 방식·총질량·수납 간극·실물 토크 정격은 확정되지 않았습니다. 공통 인덱스 캠의 홈 형상, 스프링, 힘 제어, 잠금 구조도 제작 설계가 완료되지 않았습니다. 간섭 해소와 실제 토크 전달을 검증하기 전에는 제작용으로 승인할 수 없습니다. R05의 18mm 척 전진과 35+35mm 후퇴는 이 버전에 적용하지 않습니다.
## 모델 사진 · 2026-10-01 재현 촬영
보존된 R06 구현을 2026-10-01에 다시 실행해 촬영한 재현 사진입니다. 초기 제작 당시 원본 사진이 아니며 R07 조립뷰와도 구분합니다. 화면 규격은 M8×35이고 총 70초 재생 중 5·12·18·40초의 상태를 비교합니다.
구동 방식과 간섭 문제가 미해결된 검토용 모델입니다. 사진에 표시된 움직임이나 외형은 제작 승인 또는 실제 접촉·토크 검증을 의미하지 않습니다.
### A안 · 별도 내부 6조 척 + 주집게 수납
**몸통 파지 후 인출 시작 · 5초**
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/d1c7b5c6-aabf-48dd-8294-fe2716e3b51c/R06-reproduced-2026-10-01-a-pickup.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4663S2RLAHS%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002830Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQDA2KFWPinFZpqjKzd8MrHmP4hXVwgLz7%2FtpCVhdxiaSQIgP2FPhiZQPrII527w%2B9Y64ojyxxcOPvjLdIu%2B3Bs11pQq%2FwMIbxAAGgw2Mzc0MjMxODM4MDUiDN%2FwVRfqPyUALMb6QSrcA3M6mGYz654zObn7A2jWm8QuWp8n46yN5QlOIHOLnGAXrIB2kl6eKgxBaYhZI%2FO8%2Fwl7D5pGH5yJfwE%2BJAgrdlfFJnxvh23LkNqLZqUaG9rbHagIzgGzm85lWl6qRTpuwr2i2KXzkSTWLcP%2FuviEeKCl7ZigomXJC3y%2Bu4pprQ%2FbmjcSF7ZogXhlDfyHk58Lg7MDQpx11kxvze5J6KX56noKOkWkh4lL9610znjExPAvMqnQKVSIstq2h3vuQ09TjnVbfxgjtlznrD%2FaAae6RpgeTlwB1fUFZEDYuVRphtn%2F45R9GN5k8OMh2NoaZYnU8DxvU3y0c5jGYc8lCDUSa7r9NLxkpGAtxcfdit3mzVf%2FvoerdzqFXVYv2e1x7cicrE3Bzfy3%2Br4%2BJLtnYDGenaYgofutCFTQ5OdBfNqkzyCi9wOVZmiPT84AIMXjv4BuhgHOlOeK91DGCR8QGEywKem3PoEuGA9zcU9lE9ZGrJtmcMePsm%2FyPNfTMW6MngvxbcB50OY30TWgo%2FcwG9iGJ47b7LelKBK%2FQnDzhpsoov7BW5NOfkOaEfqWPRk4E3DG6UvKLW%2BV%2BBxIhtBenJuWxidRvhl4qotpndYc8abIIhPlJKIbm1Vf0K6us1gwMMef9tUGOqUB8jsiTLo8I%2B7n2b6%2F79hYN5w7WqjlM3BycxygnNageJAUeCxythhg78yH9eqv23X%2BxMNuDLbTYxUBQ1mQEDXVKH7czfizoLVgzaTakHORcPt7503eniqU3%2FLzqBUTyf5GkauEjIOA8mt6sUWa%2BBnenf9CZUd4RG6sxN8uH4sRO3j3DKaw2xOEQrDPUHFQPyBCKrARkZyrAir8ffRrvnf%2B4jnbDNRS&X-Amz-Signature=9574413e789976b7aa71dd577dfac024f91470daad06663b403969c72c3e6b26&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
통 벽에 접촉부 일부가 가려져 있어 파지 상태의 상세 접촉 검증 자료로 사용하지 않습니다.
**보조 엄지로 세우기 · 12초**
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/590f02f8-d8da-4852-875c-189653180f2b/R06-reproduced-2026-10-01-a-righting.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4663S2RLAHS%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002830Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQDA2KFWPinFZpqjKzd8MrHmP4hXVwgLz7%2FtpCVhdxiaSQIgP2FPhiZQPrII527w%2B9Y64ojyxxcOPvjLdIu%2B3Bs11pQq%2FwMIbxAAGgw2Mzc0MjMxODM4MDUiDN%2FwVRfqPyUALMb6QSrcA3M6mGYz654zObn7A2jWm8QuWp8n46yN5QlOIHOLnGAXrIB2kl6eKgxBaYhZI%2FO8%2Fwl7D5pGH5yJfwE%2BJAgrdlfFJnxvh23LkNqLZqUaG9rbHagIzgGzm85lWl6qRTpuwr2i2KXzkSTWLcP%2FuviEeKCl7ZigomXJC3y%2Bu4pprQ%2FbmjcSF7ZogXhlDfyHk58Lg7MDQpx11kxvze5J6KX56noKOkWkh4lL9610znjExPAvMqnQKVSIstq2h3vuQ09TjnVbfxgjtlznrD%2FaAae6RpgeTlwB1fUFZEDYuVRphtn%2F45R9GN5k8OMh2NoaZYnU8DxvU3y0c5jGYc8lCDUSa7r9NLxkpGAtxcfdit3mzVf%2FvoerdzqFXVYv2e1x7cicrE3Bzfy3%2Br4%2BJLtnYDGenaYgofutCFTQ5OdBfNqkzyCi9wOVZmiPT84AIMXjv4BuhgHOlOeK91DGCR8QGEywKem3PoEuGA9zcU9lE9ZGrJtmcMePsm%2FyPNfTMW6MngvxbcB50OY30TWgo%2FcwG9iGJ47b7LelKBK%2FQnDzhpsoov7BW5NOfkOaEfqWPRk4E3DG6UvKLW%2BV%2BBxIhtBenJuWxidRvhl4qotpndYc8abIIhPlJKIbm1Vf0K6us1gwMMef9tUGOqUB8jsiTLo8I%2B7n2b6%2F79hYN5w7WqjlM3BycxygnNageJAUeCxythhg78yH9eqv23X%2BxMNuDLbTYxUBQ1mQEDXVKH7czfizoLVgzaTakHORcPt7503eniqU3%2FLzqBUTyf5GkauEjIOA8mt6sUWa%2BBnenf9CZUd4RG6sxN8uH4sRO3j3DKaw2xOEQrDPUHFQPyBCKrARkZyrAir8ffRrvnf%2B4jnbDNRS&X-Amz-Signature=14153c2e8158d4ab436d49cc00f3298ed73adc1bb252e2dd9cd029f15acf2969&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
**파지 인계·수납 후 이동 · 18초**
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/63215bbf-5196-45fb-80ef-1382c3d2c5df/R06-reproduced-2026-10-01-a-handoff.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4663S2RLAHS%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002830Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQDA2KFWPinFZpqjKzd8MrHmP4hXVwgLz7%2FtpCVhdxiaSQIgP2FPhiZQPrII527w%2B9Y64ojyxxcOPvjLdIu%2B3Bs11pQq%2FwMIbxAAGgw2Mzc0MjMxODM4MDUiDN%2FwVRfqPyUALMb6QSrcA3M6mGYz654zObn7A2jWm8QuWp8n46yN5QlOIHOLnGAXrIB2kl6eKgxBaYhZI%2FO8%2Fwl7D5pGH5yJfwE%2BJAgrdlfFJnxvh23LkNqLZqUaG9rbHagIzgGzm85lWl6qRTpuwr2i2KXzkSTWLcP%2FuviEeKCl7ZigomXJC3y%2Bu4pprQ%2FbmjcSF7ZogXhlDfyHk58Lg7MDQpx11kxvze5J6KX56noKOkWkh4lL9610znjExPAvMqnQKVSIstq2h3vuQ09TjnVbfxgjtlznrD%2FaAae6RpgeTlwB1fUFZEDYuVRphtn%2F45R9GN5k8OMh2NoaZYnU8DxvU3y0c5jGYc8lCDUSa7r9NLxkpGAtxcfdit3mzVf%2FvoerdzqFXVYv2e1x7cicrE3Bzfy3%2Br4%2BJLtnYDGenaYgofutCFTQ5OdBfNqkzyCi9wOVZmiPT84AIMXjv4BuhgHOlOeK91DGCR8QGEywKem3PoEuGA9zcU9lE9ZGrJtmcMePsm%2FyPNfTMW6MngvxbcB50OY30TWgo%2FcwG9iGJ47b7LelKBK%2FQnDzhpsoov7BW5NOfkOaEfqWPRk4E3DG6UvKLW%2BV%2BBxIhtBenJuWxidRvhl4qotpndYc8abIIhPlJKIbm1Vf0K6us1gwMMef9tUGOqUB8jsiTLo8I%2B7n2b6%2F79hYN5w7WqjlM3BycxygnNageJAUeCxythhg78yH9eqv23X%2BxMNuDLbTYxUBQ1mQEDXVKH7czfizoLVgzaTakHORcPt7503eniqU3%2FLzqBUTyf5GkauEjIOA8mt6sUWa%2BBnenf9CZUd4RG6sxN8uH4sRO3j3DKaw2xOEQrDPUHFQPyBCKrARkZyrAir8ffRrvnf%2B4jnbDNRS&X-Amz-Signature=6421330f9b459d1b61fa6305a342377250f8bb95d79b7018e116d7268e9d7d68&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
**본체 내부 회전·체결 · 40초**
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/78e04470-d4e3-439d-93bc-f4a16fecb39f/R06-reproduced-2026-10-01-a-drive.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4663S2RLAHS%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002830Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQDA2KFWPinFZpqjKzd8MrHmP4hXVwgLz7%2FtpCVhdxiaSQIgP2FPhiZQPrII527w%2B9Y64ojyxxcOPvjLdIu%2B3Bs11pQq%2FwMIbxAAGgw2Mzc0MjMxODM4MDUiDN%2FwVRfqPyUALMb6QSrcA3M6mGYz654zObn7A2jWm8QuWp8n46yN5QlOIHOLnGAXrIB2kl6eKgxBaYhZI%2FO8%2Fwl7D5pGH5yJfwE%2BJAgrdlfFJnxvh23LkNqLZqUaG9rbHagIzgGzm85lWl6qRTpuwr2i2KXzkSTWLcP%2FuviEeKCl7ZigomXJC3y%2Bu4pprQ%2FbmjcSF7ZogXhlDfyHk58Lg7MDQpx11kxvze5J6KX56noKOkWkh4lL9610znjExPAvMqnQKVSIstq2h3vuQ09TjnVbfxgjtlznrD%2FaAae6RpgeTlwB1fUFZEDYuVRphtn%2F45R9GN5k8OMh2NoaZYnU8DxvU3y0c5jGYc8lCDUSa7r9NLxkpGAtxcfdit3mzVf%2FvoerdzqFXVYv2e1x7cicrE3Bzfy3%2Br4%2BJLtnYDGenaYgofutCFTQ5OdBfNqkzyCi9wOVZmiPT84AIMXjv4BuhgHOlOeK91DGCR8QGEywKem3PoEuGA9zcU9lE9ZGrJtmcMePsm%2FyPNfTMW6MngvxbcB50OY30TWgo%2FcwG9iGJ47b7LelKBK%2FQnDzhpsoov7BW5NOfkOaEfqWPRk4E3DG6UvKLW%2BV%2BBxIhtBenJuWxidRvhl4qotpndYc8abIIhPlJKIbm1Vf0K6us1gwMMef9tUGOqUB8jsiTLo8I%2B7n2b6%2F79hYN5w7WqjlM3BycxygnNageJAUeCxythhg78yH9eqv23X%2BxMNuDLbTYxUBQ1mQEDXVKH7czfizoLVgzaTakHORcPt7503eniqU3%2FLzqBUTyf5GkauEjIOA8mt6sUWa%2BBnenf9CZUd4RG6sxN8uH4sRO3j3DKaw2xOEQrDPUHFQPyBCKrARkZyrAir8ffRrvnf%2B4jnbDNRS&X-Amz-Signature=b9bc034f4111fdb5ff65807ad7f73b2f3fdcc94f4a9fe6ae740929d8082549f4&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
### B안 · 파지·체결 통합 2조 카세트
**몸통 파지 후 인출 시작 · 5초**
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/65074327-1f81-4db9-b7eb-ab60e59e7255/R06-reproduced-2026-10-01-b-pickup.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4663S2RLAHS%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002830Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQDA2KFWPinFZpqjKzd8MrHmP4hXVwgLz7%2FtpCVhdxiaSQIgP2FPhiZQPrII527w%2B9Y64ojyxxcOPvjLdIu%2B3Bs11pQq%2FwMIbxAAGgw2Mzc0MjMxODM4MDUiDN%2FwVRfqPyUALMb6QSrcA3M6mGYz654zObn7A2jWm8QuWp8n46yN5QlOIHOLnGAXrIB2kl6eKgxBaYhZI%2FO8%2Fwl7D5pGH5yJfwE%2BJAgrdlfFJnxvh23LkNqLZqUaG9rbHagIzgGzm85lWl6qRTpuwr2i2KXzkSTWLcP%2FuviEeKCl7ZigomXJC3y%2Bu4pprQ%2FbmjcSF7ZogXhlDfyHk58Lg7MDQpx11kxvze5J6KX56noKOkWkh4lL9610znjExPAvMqnQKVSIstq2h3vuQ09TjnVbfxgjtlznrD%2FaAae6RpgeTlwB1fUFZEDYuVRphtn%2F45R9GN5k8OMh2NoaZYnU8DxvU3y0c5jGYc8lCDUSa7r9NLxkpGAtxcfdit3mzVf%2FvoerdzqFXVYv2e1x7cicrE3Bzfy3%2Br4%2BJLtnYDGenaYgofutCFTQ5OdBfNqkzyCi9wOVZmiPT84AIMXjv4BuhgHOlOeK91DGCR8QGEywKem3PoEuGA9zcU9lE9ZGrJtmcMePsm%2FyPNfTMW6MngvxbcB50OY30TWgo%2FcwG9iGJ47b7LelKBK%2FQnDzhpsoov7BW5NOfkOaEfqWPRk4E3DG6UvKLW%2BV%2BBxIhtBenJuWxidRvhl4qotpndYc8abIIhPlJKIbm1Vf0K6us1gwMMef9tUGOqUB8jsiTLo8I%2B7n2b6%2F79hYN5w7WqjlM3BycxygnNageJAUeCxythhg78yH9eqv23X%2BxMNuDLbTYxUBQ1mQEDXVKH7czfizoLVgzaTakHORcPt7503eniqU3%2FLzqBUTyf5GkauEjIOA8mt6sUWa%2BBnenf9CZUd4RG6sxN8uH4sRO3j3DKaw2xOEQrDPUHFQPyBCKrARkZyrAir8ffRrvnf%2B4jnbDNRS&X-Amz-Signature=3b6b62f3a4cd9578ff7aea6330b2a800fecfafaff5b9ee4fc61d1f36e599f1db&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
통 벽에 접촉부 일부가 가려져 있어 파지 상태의 상세 접촉 검증 자료로 사용하지 않습니다.
**보조 엄지로 세우기 · 12초**
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/ea535da2-cc74-45c3-ba65-b863ea1956ce/R06-reproduced-2026-10-01-b-righting.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4663S2RLAHS%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002830Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQDA2KFWPinFZpqjKzd8MrHmP4hXVwgLz7%2FtpCVhdxiaSQIgP2FPhiZQPrII527w%2B9Y64ojyxxcOPvjLdIu%2B3Bs11pQq%2FwMIbxAAGgw2Mzc0MjMxODM4MDUiDN%2FwVRfqPyUALMb6QSrcA3M6mGYz654zObn7A2jWm8QuWp8n46yN5QlOIHOLnGAXrIB2kl6eKgxBaYhZI%2FO8%2Fwl7D5pGH5yJfwE%2BJAgrdlfFJnxvh23LkNqLZqUaG9rbHagIzgGzm85lWl6qRTpuwr2i2KXzkSTWLcP%2FuviEeKCl7ZigomXJC3y%2Bu4pprQ%2FbmjcSF7ZogXhlDfyHk58Lg7MDQpx11kxvze5J6KX56noKOkWkh4lL9610znjExPAvMqnQKVSIstq2h3vuQ09TjnVbfxgjtlznrD%2FaAae6RpgeTlwB1fUFZEDYuVRphtn%2F45R9GN5k8OMh2NoaZYnU8DxvU3y0c5jGYc8lCDUSa7r9NLxkpGAtxcfdit3mzVf%2FvoerdzqFXVYv2e1x7cicrE3Bzfy3%2Br4%2BJLtnYDGenaYgofutCFTQ5OdBfNqkzyCi9wOVZmiPT84AIMXjv4BuhgHOlOeK91DGCR8QGEywKem3PoEuGA9zcU9lE9ZGrJtmcMePsm%2FyPNfTMW6MngvxbcB50OY30TWgo%2FcwG9iGJ47b7LelKBK%2FQnDzhpsoov7BW5NOfkOaEfqWPRk4E3DG6UvKLW%2BV%2BBxIhtBenJuWxidRvhl4qotpndYc8abIIhPlJKIbm1Vf0K6us1gwMMef9tUGOqUB8jsiTLo8I%2B7n2b6%2F79hYN5w7WqjlM3BycxygnNageJAUeCxythhg78yH9eqv23X%2BxMNuDLbTYxUBQ1mQEDXVKH7czfizoLVgzaTakHORcPt7503eniqU3%2FLzqBUTyf5GkauEjIOA8mt6sUWa%2BBnenf9CZUd4RG6sxN8uH4sRO3j3DKaw2xOEQrDPUHFQPyBCKrARkZyrAir8ffRrvnf%2B4jnbDNRS&X-Amz-Signature=6270897731f9ac58f429c5c6f5b8def8c1635cd0b9bc5f8bb9c135846de39cf9&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
**파지 인계·수납 후 이동 · 18초**
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/3f982d23-ee99-4696-a90b-4c4db590f17c/R06-reproduced-2026-10-01-b-handoff.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4663S2RLAHS%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002830Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQDA2KFWPinFZpqjKzd8MrHmP4hXVwgLz7%2FtpCVhdxiaSQIgP2FPhiZQPrII527w%2B9Y64ojyxxcOPvjLdIu%2B3Bs11pQq%2FwMIbxAAGgw2Mzc0MjMxODM4MDUiDN%2FwVRfqPyUALMb6QSrcA3M6mGYz654zObn7A2jWm8QuWp8n46yN5QlOIHOLnGAXrIB2kl6eKgxBaYhZI%2FO8%2Fwl7D5pGH5yJfwE%2BJAgrdlfFJnxvh23LkNqLZqUaG9rbHagIzgGzm85lWl6qRTpuwr2i2KXzkSTWLcP%2FuviEeKCl7ZigomXJC3y%2Bu4pprQ%2FbmjcSF7ZogXhlDfyHk58Lg7MDQpx11kxvze5J6KX56noKOkWkh4lL9610znjExPAvMqnQKVSIstq2h3vuQ09TjnVbfxgjtlznrD%2FaAae6RpgeTlwB1fUFZEDYuVRphtn%2F45R9GN5k8OMh2NoaZYnU8DxvU3y0c5jGYc8lCDUSa7r9NLxkpGAtxcfdit3mzVf%2FvoerdzqFXVYv2e1x7cicrE3Bzfy3%2Br4%2BJLtnYDGenaYgofutCFTQ5OdBfNqkzyCi9wOVZmiPT84AIMXjv4BuhgHOlOeK91DGCR8QGEywKem3PoEuGA9zcU9lE9ZGrJtmcMePsm%2FyPNfTMW6MngvxbcB50OY30TWgo%2FcwG9iGJ47b7LelKBK%2FQnDzhpsoov7BW5NOfkOaEfqWPRk4E3DG6UvKLW%2BV%2BBxIhtBenJuWxidRvhl4qotpndYc8abIIhPlJKIbm1Vf0K6us1gwMMef9tUGOqUB8jsiTLo8I%2B7n2b6%2F79hYN5w7WqjlM3BycxygnNageJAUeCxythhg78yH9eqv23X%2BxMNuDLbTYxUBQ1mQEDXVKH7czfizoLVgzaTakHORcPt7503eniqU3%2FLzqBUTyf5GkauEjIOA8mt6sUWa%2BBnenf9CZUd4RG6sxN8uH4sRO3j3DKaw2xOEQrDPUHFQPyBCKrARkZyrAir8ffRrvnf%2B4jnbDNRS&X-Amz-Signature=f9f53e7a84802170f16cd8dc7562cc00168c3d857ada60ca835c9688e2bfe4c6&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
**본체 내부 회전·체결 · 40초**
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/d7dddfcb-0b24-4f10-9026-4902b8ada386/R06-reproduced-2026-10-01-b-drive.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4663S2RLAHS%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002830Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQDA2KFWPinFZpqjKzd8MrHmP4hXVwgLz7%2FtpCVhdxiaSQIgP2FPhiZQPrII527w%2B9Y64ojyxxcOPvjLdIu%2B3Bs11pQq%2FwMIbxAAGgw2Mzc0MjMxODM4MDUiDN%2FwVRfqPyUALMb6QSrcA3M6mGYz654zObn7A2jWm8QuWp8n46yN5QlOIHOLnGAXrIB2kl6eKgxBaYhZI%2FO8%2Fwl7D5pGH5yJfwE%2BJAgrdlfFJnxvh23LkNqLZqUaG9rbHagIzgGzm85lWl6qRTpuwr2i2KXzkSTWLcP%2FuviEeKCl7ZigomXJC3y%2Bu4pprQ%2FbmjcSF7ZogXhlDfyHk58Lg7MDQpx11kxvze5J6KX56noKOkWkh4lL9610znjExPAvMqnQKVSIstq2h3vuQ09TjnVbfxgjtlznrD%2FaAae6RpgeTlwB1fUFZEDYuVRphtn%2F45R9GN5k8OMh2NoaZYnU8DxvU3y0c5jGYc8lCDUSa7r9NLxkpGAtxcfdit3mzVf%2FvoerdzqFXVYv2e1x7cicrE3Bzfy3%2Br4%2BJLtnYDGenaYgofutCFTQ5OdBfNqkzyCi9wOVZmiPT84AIMXjv4BuhgHOlOeK91DGCR8QGEywKem3PoEuGA9zcU9lE9ZGrJtmcMePsm%2FyPNfTMW6MngvxbcB50OY30TWgo%2FcwG9iGJ47b7LelKBK%2FQnDzhpsoov7BW5NOfkOaEfqWPRk4E3DG6UvKLW%2BV%2BBxIhtBenJuWxidRvhl4qotpndYc8abIIhPlJKIbm1Vf0K6us1gwMMef9tUGOqUB8jsiTLo8I%2B7n2b6%2F79hYN5w7WqjlM3BycxygnNageJAUeCxythhg78yH9eqv23X%2BxMNuDLbTYxUBQ1mQEDXVKH7czfizoLVgzaTakHORcPt7503eniqU3%2FLzqBUTyf5GkauEjIOA8mt6sUWa%2BBnenf9CZUd4RG6sxN8uH4sRO3j3DKaw2xOEQrDPUHFQPyBCKrARkZyrAir8ffRrvnf%2B4jnbDNRS&X-Amz-Signature=51951ec21e7a2a613a3f09934aa4f1f6fcbe89491df5aacfe479cedf0f8645e7&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
## 보존 ZIP
<file src="https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/5c63608d-6bf7-4a6f-ad24-9e50d25987be/R06.zip?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB4663S2RLAHS%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002830Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQDA2KFWPinFZpqjKzd8MrHmP4hXVwgLz7%2FtpCVhdxiaSQIgP2FPhiZQPrII527w%2B9Y64ojyxxcOPvjLdIu%2B3Bs11pQq%2FwMIbxAAGgw2Mzc0MjMxODM4MDUiDN%2FwVRfqPyUALMb6QSrcA3M6mGYz654zObn7A2jWm8QuWp8n46yN5QlOIHOLnGAXrIB2kl6eKgxBaYhZI%2FO8%2Fwl7D5pGH5yJfwE%2BJAgrdlfFJnxvh23LkNqLZqUaG9rbHagIzgGzm85lWl6qRTpuwr2i2KXzkSTWLcP%2FuviEeKCl7ZigomXJC3y%2Bu4pprQ%2FbmjcSF7ZogXhlDfyHk58Lg7MDQpx11kxvze5J6KX56noKOkWkh4lL9610znjExPAvMqnQKVSIstq2h3vuQ09TjnVbfxgjtlznrD%2FaAae6RpgeTlwB1fUFZEDYuVRphtn%2F45R9GN5k8OMh2NoaZYnU8DxvU3y0c5jGYc8lCDUSa7r9NLxkpGAtxcfdit3mzVf%2FvoerdzqFXVYv2e1x7cicrE3Bzfy3%2Br4%2BJLtnYDGenaYgofutCFTQ5OdBfNqkzyCi9wOVZmiPT84AIMXjv4BuhgHOlOeK91DGCR8QGEywKem3PoEuGA9zcU9lE9ZGrJtmcMePsm%2FyPNfTMW6MngvxbcB50OY30TWgo%2FcwG9iGJ47b7LelKBK%2FQnDzhpsoov7BW5NOfkOaEfqWPRk4E3DG6UvKLW%2BV%2BBxIhtBenJuWxidRvhl4qotpndYc8abIIhPlJKIbm1Vf0K6us1gwMMef9tUGOqUB8jsiTLo8I%2B7n2b6%2F79hYN5w7WqjlM3BycxygnNageJAUeCxythhg78yH9eqv23X%2BxMNuDLbTYxUBQ1mQEDXVKH7czfizoLVgzaTakHORcPt7503eniqU3%2FLzqBUTyf5GkauEjIOA8mt6sUWa%2BBnenf9CZUd4RG6sxN8uH4sRO3j3DKaw2xOEQrDPUHFQPyBCKrARkZyrAir8ffRrvnf%2B4jnbDNRS&X-Amz-Signature=9cdada1808271aa820523a648f6461fc1be2ae839175fb3d9c1ceef168276dbe&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject"></file>
보존된 구현과 2026-10-01 재현 사진을 포함합니다. 파일 크기 1,349,871bytes. ZIP SHA256: `6849b2ffacaac113442ecec4ceecf809515a8b66bdb7629529536da9edb9d57c`. 내부 `SHA256SUMS`와 사진 8장의 해시 일치를 확인했습니다. 재현 사진은 초기 제작 당시 원본 사진이 아닙니다.
## 검토 상태와 보존 범위
R06은 구조 검토 단계이며 구동 방식 확정과 간섭 해소가 완료되지 않았습니다. 형상과 모션은 설계 비교 자료이며 제작 도면·조립 승인·실물 성능 검증 결과가 아닙니다. 보존 소스와 재현 사진을 포함한 R06 ZIP을 첨부했습니다. 확정된 실물 검증 결과는 없으며 제작 승인 상태로 변경하지 않습니다. A/B 재현 사진 8장을 첨부했습니다. 보존 구현의 재실행 촬영 자료이며 당시 원본 사진으로 분류하지 않습니다. R05·R07 사진은 이 기록에 혼용하지 않습니다.
<!-- RECORD_END 3ebbf010-5ac9-816f-9ec2-d0129c5e1161 -->

<!-- RECORD_START 3ecbf010-5ac9-8126-b38c-c13e55b71d62 -->
# R07 · 기계 조립 검토 — A/B 구조·모델·검증
Record URL: https://app.notion.com/p/3ecbf0105ac98126b38cc13e55b71d62?pvs=204

기준일: 2026-10-01. 상태: **조립 검토·제작 미승인**. 대상은 M6×20, M8×35, M10×50의 노출된 외부 육각 헤드이며 체결 토크는 미정입니다.
## 설계 목적과 이전안 판정
R06에는 구동부·힘 전달 경로의 누락, 얇은 B 턱의 최종 토크 전달 근거 부족, 부품 관통이 남아 있어 제작 승인 기준안에서 제외했습니다. R07은 기존 로봇 시연과 분리한 브라우저 조립 검토 뷰로 실제 피벗·가이드·베어링의 배치와 A/B 운동을 비교합니다.
A는 2R 엄지로 볼트를 세우고 별도 평행 픽업을 수납합니다. B는 작은 팁만 비트는 대신 직선 손가락과 평행 구동부를 포함한 픽업 카세트 전체를 1R 회전시킵니다. **두 안 모두 같은 내부 가변 6조 척에 헤드를 인계합니다.** R06 B의 통합 2조 헤드 카세트와는 다른 구조입니다.
## 제어축 비교
<table header-row="true">
<tr>
<td>운동</td>
<td>A · 기능 분리형</td>
<td>B · 카세트 전체 회전형</td>
</tr>
<tr>
<td>몸통 파지</td>
<td>평행 픽업 1축</td>
<td>평행 픽업 1축</td>
</tr>
<tr>
<td>세우기</td>
<td>보조 엄지 2R</td>
<td>카세트 전체 1R</td>
</tr>
<tr>
<td>수납</td>
<td>슬라이드 1축</td>
<td>슬라이드 1축</td>
</tr>
<tr>
<td>헤드 유지</td>
<td>내부 6조 척 닫힘 1축</td>
<td>내부 6조 척 닫힘 1축</td>
</tr>
<tr>
<td>회전</td>
<td>스핀들 1축</td>
<td>스핀들 1축</td>
</tr>
<tr>
<td>합계</td>
<td>6제어축</td>
<td>5제어축</td>
</tr>
</table>
제어축은 독립 운동 좌표의 수이며 모터 수나 구매부품 수가 아닙니다. 로봇 관절은 제외했습니다. 잠금·클러치의 별도 구동이나 추가 정렬축이 필요해지면 합계도 늘어납니다. 척 닫힘 1축은 6조 동기화 구동이 실제로 설계된다는 전제입니다.
## 공통 조립 치수
조립 좌표는 mm, +Z는 나사 끝 방향, 헤드 아래면은 Z=0입니다. 다음 값은 공간 검토용 가정이며 제작 공차·구매품 정격이 아닙니다.
- 몸통 파지점: (0, 0, 14).
- 손가락: 중심선 약 113.1mm, 뿌리 12×10mm → 끝 3×4mm. 뿌리는 측면으로 20mm 벌어집니다.
- 평행 모듈 설치 공간: 80×45×65mm, 중심 (0, 100, −80).
- 픽업 수납: (0, +60, −35), 총 69.5mm. Ø10 가이드 축 2개와 중공 부시를 배치했습니다.
- 척의 축방향 돌출 이동: 0mm. 내부 닫힘 구동용 드로바 이동과 척 자체의 이동은 구분합니다.
- 척 외장: 외경 104mm, 내경 96mm, 뒤쪽 개구. 완전 밀폐 구조가 아닙니다.
- 출력축 가정: Ø16mm, 지지 베어링 간격 24mm. 반력 접촉 검토 반경 65mm.
- 스핀들 설치 공간: Ø57×322mm. 구매품과 목표 토크는 선정하지 않았습니다.
긴 손가락은 스핀들과 회전 카세트 사이 공간을 확보한 결과입니다. 기존 소형 모듈의 허용 길이를 만족한다고 가정하지 않으며 파지력·처짐·모듈 선정 검토가 필요합니다.
## 파지 인계와 검토 범위
몸통 파지 확인 → 인출 → 세우기 → 축 정렬·헤드 착좌 → 척 잠금 확인 → 몸통 집게 해제 → 수납 확인 → 내부 스핀들 회전 순서입니다. 헤드 유지가 확인되기 전에 몸통 집게를 열지 않는 순서를 표현합니다.
현재 화면은 단순 동작·조립·GLB/CSV 검토 뷰입니다. **작업물의 실제 나사 삽입, 토크 제어, 접촉 물리, 로봇 제어·경로 계획은 포함하지 않습니다.** 시간에 따른 애니메이션 전환은 실기 센서 확인을 구현한 제어기가 아닙니다.
## 검토 결과와 미확정 항목
A의 엄지 회전에 동일한 보간을 두 번 적용해 접촉이 어긋나던 오류를 수정했고 엄지 모터와 평행 모듈 설치 공간이 12.5mm 겹치던 배치도 분리했습니다. 렌더링 롤러의 볼트 접촉과 모터 설치 공간 분리를 자동 검사에 추가했습니다.
구매 구동기, 척의 쐐기·잠금, 재료·강도·공차·끼워맞춤, 배선, 완성 도구의 질량·관성, 파지 안정성, 헤드 위상 탐색·착좌 검출, 반력 지그는 확정되지 않았습니다. 단면과 전체 운동 영역의 연속 충돌 검토, 토크 전달·내구·낙하 방지 시험이 필요합니다. 현재 모델로 제작 발주할 수 없습니다.
## 개발 검증 기록
2026-10-01 최종 확인 기록: 단위 테스트 26개, 브라우저 검사 13개 전체(약 1.8분), 타입 검사·빌드·Prettier 통과. GLB 2개는 헤더와 변환행렬 대각의 0.001 스케일을 확인해 미터 단위로 내보냈습니다.
자동 검사 통과는 강도, 전 기구 연속 충돌, 실물 파지·체결 성능 또는 제작 승인을 뜻하지 않습니다.
## 부품군·하중 자료
<file src="https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/ddaf90de-bb7a-41fc-a869-16bbb343984a/R07-component-review.csv?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466ZCHN3FGA%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002830Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQCwlRFsAmC19d%2BLTZxoCtRez9tsIXaHZdn19zk9uIcUJgIgODFD1cEg62PDl1R8SIH%2BLj3QJuRjckNfUsQz9m9NO54q%2FwMIcBAAGgw2Mzc0MjMxODM4MDUiDIFsvMh%2F2FLwbdyoLCrcAw4RT9PvfTpKl4Cq%2BbOASf9w8tQspe8bActSLMRL5x%2FSkpVKY3LhYxyeWpuSLaK%2BejoscyOZ5mO%2F7gdye7LSFnwo1ZccI63T%2FE%2BeMi5WBpR9qavtRynQwA0PbasL%2FMg%2Fdmo4sfHvZaKRsiNxt3reEqdghYWNnZsb1p1ZyYPUcXm5GaJAUtwXxKQvM1vg71RyJOoDkREhKjum6n35xvHC%2FwUAcYECSf8QmH%2F4HwbdgJ7BIK9hw7Q5OfRIJpGJe69pbuhyJYSiJw0xW%2BLUNpkUgL0SnYxCRWJgDjSCXzIP2oMyk2stA4KLPmXCmXBfwF9RAK2a8HhcJVmJ01gopakdSJ7KZW7aTqWC6fadEDH9OIj4RYh0Xpyt9KH10QWhZHJpB8jSwATJFtv6YekKPZqN5Imleg1sDnPGIC%2Fud9CNN6NCjPG4GKOgMD6%2FmJDno9C8Pb3F5eaLtdckibdksBKSo7tNGkhKH1%2BGNN0CNPOO8HfLsU%2FBcPpyj%2BzT0cbTu23RjWBFpqV3crZ3PsHhqfKq3KFZw0R%2BdaO3erVwace%2BRbaxLxN9fkq0WRpjFiN5bQE5lb%2B5m4MJV6fON1svzOe8nw4rgy4DOXh3XOmU42ke2vsRGGdIpO4aQx50qnghMJei9tUGOqUB3Jmcl0JXRCjQwyQRfQ2FOXCjdDskLGeH0lFpDvUuyjuPOmTVTJbEQZJOp3GOi4x4MaO7dKf5cUBlNU%2BzyekD%2FYgNd5Gjjflm5KzUw8HXNPZZIL0E2K1u99mu%2BgJAggrTmJ79%2BdHOAPK9Ck%2BePh3DMWOY4y7vEbN5Gv2hf0UZYzJQ20AJOtJfbQBZcn71HHRO8hFJeOhR5i4rp4oHiWQXsG1V3Lc7&X-Amz-Signature=ddbea53b8732f3106b4eb6716ecdb51c69a441c7a044b785812f45c1213a1ae0&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject"></file>
CSV는 구매 확정 BOM이 아닌 부품군 검토표입니다.
<file src="https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/3a1a17e0-e3a1-4397-9ae6-cac498cb5f16/R07-load-sensitivity.json?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466ZCHN3FGA%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002830Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQCwlRFsAmC19d%2BLTZxoCtRez9tsIXaHZdn19zk9uIcUJgIgODFD1cEg62PDl1R8SIH%2BLj3QJuRjckNfUsQz9m9NO54q%2FwMIcBAAGgw2Mzc0MjMxODM4MDUiDIFsvMh%2F2FLwbdyoLCrcAw4RT9PvfTpKl4Cq%2BbOASf9w8tQspe8bActSLMRL5x%2FSkpVKY3LhYxyeWpuSLaK%2BejoscyOZ5mO%2F7gdye7LSFnwo1ZccI63T%2FE%2BeMi5WBpR9qavtRynQwA0PbasL%2FMg%2Fdmo4sfHvZaKRsiNxt3reEqdghYWNnZsb1p1ZyYPUcXm5GaJAUtwXxKQvM1vg71RyJOoDkREhKjum6n35xvHC%2FwUAcYECSf8QmH%2F4HwbdgJ7BIK9hw7Q5OfRIJpGJe69pbuhyJYSiJw0xW%2BLUNpkUgL0SnYxCRWJgDjSCXzIP2oMyk2stA4KLPmXCmXBfwF9RAK2a8HhcJVmJ01gopakdSJ7KZW7aTqWC6fadEDH9OIj4RYh0Xpyt9KH10QWhZHJpB8jSwATJFtv6YekKPZqN5Imleg1sDnPGIC%2Fud9CNN6NCjPG4GKOgMD6%2FmJDno9C8Pb3F5eaLtdckibdksBKSo7tNGkhKH1%2BGNN0CNPOO8HfLsU%2FBcPpyj%2BzT0cbTu23RjWBFpqV3crZ3PsHhqfKq3KFZw0R%2BdaO3erVwace%2BRbaxLxN9fkq0WRpjFiN5bQE5lb%2B5m4MJV6fON1svzOe8nw4rgy4DOXh3XOmU42ke2vsRGGdIpO4aQx50qnghMJei9tUGOqUB3Jmcl0JXRCjQwyQRfQ2FOXCjdDskLGeH0lFpDvUuyjuPOmTVTJbEQZJOp3GOi4x4MaO7dKf5cUBlNU%2BzyekD%2FYgNd5Gjjflm5KzUw8HXNPZZIL0E2K1u99mu%2BgJAggrTmJ79%2BdHOAPK9Ck%2BePh3DMWOY4y7vEbN5Gv2hf0UZYzJQ20AJOtJfbQBZcn71HHRO8hFJeOhR5i4rp4oHiWQXsG1V3Lc7&X-Amz-Signature=3cba0dfdaeba619f5e02073a17455d7d46d92f454d1f39b6be7f93c884f7f343&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject"></file>
하중 JSON은 가정 토크 20/40/60N·m, 헤드 대변 10/13/17mm, 중실 출력축 Ø16mm, 반력 반경 65mm의 예비 민감도 계산입니다. 토크 추천이나 정격 합격 판정이 아닙니다.
예를 들어 40N·m에서 Ø16mm 중실축의 순수 비틀림 최대 전단응력은 약 49.7MPa, 두 반력 탭이 균등 분담할 때 탭당 힘은 약 307.7N입니다. 한 탭만 접촉하면 약 615.4N입니다. 재료·키홈·단차·굽힘·피로·안전계수는 포함하지 않았습니다.
기계 검토 문서의 기본 예시 표는 Ø10mm 축·반경 25mm 조건이며 첨부 JSON의 Ø16mm·반경 65mm 조건과 다릅니다. 조건을 섞어 비교하지 않습니다.
## 기계 검토 원문과 출처
<file src="https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/afc867c9-97f2-47ae-aa79-4b1a0cf96d94/R07-MECHANICAL_REVIEW.md?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466ZCHN3FGA%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002830Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIQCwlRFsAmC19d%2BLTZxoCtRez9tsIXaHZdn19zk9uIcUJgIgODFD1cEg62PDl1R8SIH%2BLj3QJuRjckNfUsQz9m9NO54q%2FwMIcBAAGgw2Mzc0MjMxODM4MDUiDIFsvMh%2F2FLwbdyoLCrcAw4RT9PvfTpKl4Cq%2BbOASf9w8tQspe8bActSLMRL5x%2FSkpVKY3LhYxyeWpuSLaK%2BejoscyOZ5mO%2F7gdye7LSFnwo1ZccI63T%2FE%2BeMi5WBpR9qavtRynQwA0PbasL%2FMg%2Fdmo4sfHvZaKRsiNxt3reEqdghYWNnZsb1p1ZyYPUcXm5GaJAUtwXxKQvM1vg71RyJOoDkREhKjum6n35xvHC%2FwUAcYECSf8QmH%2F4HwbdgJ7BIK9hw7Q5OfRIJpGJe69pbuhyJYSiJw0xW%2BLUNpkUgL0SnYxCRWJgDjSCXzIP2oMyk2stA4KLPmXCmXBfwF9RAK2a8HhcJVmJ01gopakdSJ7KZW7aTqWC6fadEDH9OIj4RYh0Xpyt9KH10QWhZHJpB8jSwATJFtv6YekKPZqN5Imleg1sDnPGIC%2Fud9CNN6NCjPG4GKOgMD6%2FmJDno9C8Pb3F5eaLtdckibdksBKSo7tNGkhKH1%2BGNN0CNPOO8HfLsU%2FBcPpyj%2BzT0cbTu23RjWBFpqV3crZ3PsHhqfKq3KFZw0R%2BdaO3erVwace%2BRbaxLxN9fkq0WRpjFiN5bQE5lb%2B5m4MJV6fON1svzOe8nw4rgy4DOXh3XOmU42ke2vsRGGdIpO4aQx50qnghMJei9tUGOqUB3Jmcl0JXRCjQwyQRfQ2FOXCjdDskLGeH0lFpDvUuyjuPOmTVTJbEQZJOp3GOi4x4MaO7dKf5cUBlNU%2BzyekD%2FYgNd5Gjjflm5KzUw8HXNPZZIL0E2K1u99mu%2BgJAggrTmJ79%2BdHOAPK9Ck%2BePh3DMWOY4y7vEbN5Gv2hf0UZYzJQ20AJOtJfbQBZcn71HHRO8hFJeOhR5i4rp4oHiWQXsG1V3Lc7&X-Amz-Signature=8ff2b3f24340c44446a7ce65358bd84f4d672e174f060ff6671f631bfaeeef4d&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject"></file>
원문에는 자유도·구속·힘 전달 경로·계산 가정·제작 전 수용 기준·제조사 참고 자료를 보존했습니다. 제조사 구조는 원리와 부품 구성의 근거이며 이 조립체의 정격이나 구매 확정을 뜻하지 않습니다.
[Festo HGDS](https://media.festo.com/media/114116_documentation.pdf), [Zimmer SBZ](https://www.zimmer-group.com/en/products/components/handling-technology/swivel-and-rotary-modules/series-sbz), [Kolver 카탈로그](https://kolver.com/upl/EN_Catalog_KDUCER.pdf).
## 파일 보존 상태
A/B별 최신 사진 6장과 미터 단위 GLB는 아래 하위 페이지에 첨부합니다. GLB는 시각 조립 메시이며 STEP 솔리드·부품도·공차 설계·가공 데이터가 아닙니다. 소스·정적뷰어·검토기록 묶음은 문서 정리 후 아래에 첨부합니다.
`R07_ZIP_ATTACHMENT_PENDING`
## A/B 상세 기록
<page url="https://app.notion.com/p/3ecbf0105ac98118ba85f4a0e4a15424">R07 A · 2R 엄지·분리형 픽업 — 6제어축</page>
<page url="https://app.notion.com/p/3ecbf0105ac9810c9938e5264b5aa442">R07 B · 카세트 전체 1R 회전 — 5제어축</page>
<!-- RECORD_END 3ecbf010-5ac9-8126-b38c-c13e55b71d62 -->

<!-- RECORD_START 3ecbf010-5ac9-8118-ba85-f4a0e4a15424 -->
# R07 A · 2R 엄지·분리형 픽업 — 6제어축
Record URL: https://app.notion.com/p/3ecbf0105ac98118ba85f4a0e4a15424?pvs=204

기준일: 2026-10-01. 상태: **조립 검토·제작 미승인**.
## 구조와 설계 판단
평행 픽업이 볼트 몸통을 유지하고 별도 2R 엄지가 볼트를 세웁니다. 내부 6조 척에 헤드를 인계한 뒤 평행 모듈 전체를 슬라이드로 수납합니다. 몸통 파지 1축 + 엄지 2R + 수납 1축 + 척 닫힘 1축 + 스핀들 1축, 총 6제어축입니다.
엄지는 25+25mm의 2링크이며 구동기 2개의 설치 공간은 각각 20×30×35mm, 중심 (±12,145,−75)입니다. 실제 구동기는 미선정입니다. 주집게 접촉부의 수동 자세 추종, 베어링·마찰·엄지 접촉력이 설계되어야 합니다. 파지력 감소만으로 낙하 없는 회전을 보장하지 않습니다.
공통 손가락 길이는 약 113.1mm, 뿌리 12×10mm·끝 3×4mm, 수납 행정은 69.5mm입니다. 척 축방향 돌출 이동은 0mm입니다.
## 검토 과제
엄지 접촉부·텐던 전달·파지 안정성과 모듈 수납 경로를 검토해야 합니다. 기능을 분리한 만큼 엄지 링크와 구동 전달부의 공간이 필요합니다.
구매부품, 척 쐐기·잠금, 재료·공차·강도·연속 간섭 검토가 미완료입니다. 실제 나사 삽입·토크 제어·로봇 제어는 포함하지 않습니다.
## GLB 모델
<file src="https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/16efd7e2-3ed6-414e-9d78-ec36b012a997/R07-a-assembly-review.glb?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466QK4FF7EZ%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002830Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIE6QDxdxa1Aokd3onEbRI4fFfDBynZTdbRtbZHMeq%2FXxAiEA%2FV%2BgGvDJ7sveXfTvKLJ6NQlH84A11OX5XiAoZXDaflUq%2FwMIbxAAGgw2Mzc0MjMxODM4MDUiDAoitMHYTTmrTWzwLSrcAwug6ggjA%2FYXSFSv%2FOHVdmbpRtnDVtjMvswsdPjDXJMMOT3TiQcLl6KinLTkwjdiqYBAwUkVdZySFwuqIy868xKiI1DJhfRrjAhr1Syhn1vaXflRmjYkw5uPraBcb6e00%2FUHH8GEylIlz0%2B7QSqHL93lggJW0aaicSBptnWLf%2BUD4kDF4e0tysGQLFi8POKEB6RuUicHBbtNrlBWdyAibfA1m3%2F%2B8D%2FYWM3H8B0Rm5cVDQcqGLIeRhST4P3CfzQC2bKSWj7iA6lcpsZBSMMSxrGMs1dKRS6wm8eKZ74e70%2BCbu8GW0upteuOCNt4RP%2FaiJilGh%2F5oiQBXO6%2BRFILC8X7jk%2FP5463kTK2kvDBGJvCEOHeP0KLXpTAXRP%2BoS5KejIEcWfHz9FU8aUbSOXez1xmudzgv4HHANdbdfPklUHa5sCi6fu5QpAT46DwtTSzdG3wqPvLLD9xOFIyFjiL5Pa7bfsqKIbnbJUsLF%2B9h2fCCVbrXzpwLk3SkVGSART8%2FkP3CHYF%2BrUEFCl1EtxgepwP9vnDA59G9M3V7BZY5sBg%2Bifj8MNzOPEobZow49GPye4oxVclDOhX%2BrjuZrGEjszConuhgB7WkbyNFV4x2lvm9mkU07FmyigLDnv9MK%2Bg9tUGOqUBEoCKxoVz%2FiphIN%2B1sQxk4mFvgaQAIYFaRV0HpJ51qCQdOoU4VuV%2BRHrmsZdCzu%2FADhE15wbhNtGW4GNQnipY3jYwIO7J0xbx6gSmI9kdCYMW%2FJxOlxuph%2F4QxQVw4Kyb7VlCGo2DVW6NTiyH2WistmmW7p8Lb6DX3Dpt8Ja5LlPV8FlVcMs9iS6lyHkcpuJQD8wr%2Bjp1cFpPMtk9BjJpLQJ1TRVG&X-Amz-Signature=2d428fa8626d147576a63597266c293d27b75a78b3323048e12511c379239eca&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject"></file>
미터 단위 시각 조립 메시입니다. 4×4 변환행렬의 대각 0.001 스케일과 GLB 헤더를 확인했습니다. STEP 솔리드나 가공용 부품도가 아니며 제작 발주에 사용할 수 없습니다.
## 모델 사진 · 2026-10-01
R07 조립 검토 뷰의 최신 사진 6장입니다. R06 재현 사진과 구분합니다. M8×35 조건을 보여주며 화면의 진행값은 조립 모션 단계입니다.
### 몸통 파지
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/96902143-d010-4668-b516-acfe4a9feec7/R07-a-pickup.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466QK4FF7EZ%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002831Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIE6QDxdxa1Aokd3onEbRI4fFfDBynZTdbRtbZHMeq%2FXxAiEA%2FV%2BgGvDJ7sveXfTvKLJ6NQlH84A11OX5XiAoZXDaflUq%2FwMIbxAAGgw2Mzc0MjMxODM4MDUiDAoitMHYTTmrTWzwLSrcAwug6ggjA%2FYXSFSv%2FOHVdmbpRtnDVtjMvswsdPjDXJMMOT3TiQcLl6KinLTkwjdiqYBAwUkVdZySFwuqIy868xKiI1DJhfRrjAhr1Syhn1vaXflRmjYkw5uPraBcb6e00%2FUHH8GEylIlz0%2B7QSqHL93lggJW0aaicSBptnWLf%2BUD4kDF4e0tysGQLFi8POKEB6RuUicHBbtNrlBWdyAibfA1m3%2F%2B8D%2FYWM3H8B0Rm5cVDQcqGLIeRhST4P3CfzQC2bKSWj7iA6lcpsZBSMMSxrGMs1dKRS6wm8eKZ74e70%2BCbu8GW0upteuOCNt4RP%2FaiJilGh%2F5oiQBXO6%2BRFILC8X7jk%2FP5463kTK2kvDBGJvCEOHeP0KLXpTAXRP%2BoS5KejIEcWfHz9FU8aUbSOXez1xmudzgv4HHANdbdfPklUHa5sCi6fu5QpAT46DwtTSzdG3wqPvLLD9xOFIyFjiL5Pa7bfsqKIbnbJUsLF%2B9h2fCCVbrXzpwLk3SkVGSART8%2FkP3CHYF%2BrUEFCl1EtxgepwP9vnDA59G9M3V7BZY5sBg%2Bifj8MNzOPEobZow49GPye4oxVclDOhX%2BrjuZrGEjszConuhgB7WkbyNFV4x2lvm9mkU07FmyigLDnv9MK%2Bg9tUGOqUBEoCKxoVz%2FiphIN%2B1sQxk4mFvgaQAIYFaRV0HpJ51qCQdOoU4VuV%2BRHrmsZdCzu%2FADhE15wbhNtGW4GNQnipY3jYwIO7J0xbx6gSmI9kdCYMW%2FJxOlxuph%2F4QxQVw4Kyb7VlCGo2DVW6NTiyH2WistmmW7p8Lb6DX3Dpt8Ja5LlPV8FlVcMs9iS6lyHkcpuJQD8wr%2Bjp1cFpPMtk9BjJpLQJ1TRVG&X-Amz-Signature=81badbecf74cce4040e686724639a3ecbda85c6f861d0b3f7fda01ba8083216b&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
### 헤드를 위로 세우기
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/e5466157-ca8c-4d98-9af1-06be4db02082/R07-a-righting.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466QK4FF7EZ%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002830Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIE6QDxdxa1Aokd3onEbRI4fFfDBynZTdbRtbZHMeq%2FXxAiEA%2FV%2BgGvDJ7sveXfTvKLJ6NQlH84A11OX5XiAoZXDaflUq%2FwMIbxAAGgw2Mzc0MjMxODM4MDUiDAoitMHYTTmrTWzwLSrcAwug6ggjA%2FYXSFSv%2FOHVdmbpRtnDVtjMvswsdPjDXJMMOT3TiQcLl6KinLTkwjdiqYBAwUkVdZySFwuqIy868xKiI1DJhfRrjAhr1Syhn1vaXflRmjYkw5uPraBcb6e00%2FUHH8GEylIlz0%2B7QSqHL93lggJW0aaicSBptnWLf%2BUD4kDF4e0tysGQLFi8POKEB6RuUicHBbtNrlBWdyAibfA1m3%2F%2B8D%2FYWM3H8B0Rm5cVDQcqGLIeRhST4P3CfzQC2bKSWj7iA6lcpsZBSMMSxrGMs1dKRS6wm8eKZ74e70%2BCbu8GW0upteuOCNt4RP%2FaiJilGh%2F5oiQBXO6%2BRFILC8X7jk%2FP5463kTK2kvDBGJvCEOHeP0KLXpTAXRP%2BoS5KejIEcWfHz9FU8aUbSOXez1xmudzgv4HHANdbdfPklUHa5sCi6fu5QpAT46DwtTSzdG3wqPvLLD9xOFIyFjiL5Pa7bfsqKIbnbJUsLF%2B9h2fCCVbrXzpwLk3SkVGSART8%2FkP3CHYF%2BrUEFCl1EtxgepwP9vnDA59G9M3V7BZY5sBg%2Bifj8MNzOPEobZow49GPye4oxVclDOhX%2BrjuZrGEjszConuhgB7WkbyNFV4x2lvm9mkU07FmyigLDnv9MK%2Bg9tUGOqUBEoCKxoVz%2FiphIN%2B1sQxk4mFvgaQAIYFaRV0HpJ51qCQdOoU4VuV%2BRHrmsZdCzu%2FADhE15wbhNtGW4GNQnipY3jYwIO7J0xbx6gSmI9kdCYMW%2FJxOlxuph%2F4QxQVw4Kyb7VlCGo2DVW6NTiyH2WistmmW7p8Lb6DX3Dpt8Ja5LlPV8FlVcMs9iS6lyHkcpuJQD8wr%2Bjp1cFpPMtk9BjJpLQJ1TRVG&X-Amz-Signature=58547abde973c0bcb0b27d3e6627bd2d36e7b866ae4f63bee7d7650d0bcba893&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
### 내부 6조 척에 헤드 인계
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/a824dbac-dbe1-4ce3-bb50-ec311f7f55b8/R07-a-handoff.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466QK4FF7EZ%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002830Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIE6QDxdxa1Aokd3onEbRI4fFfDBynZTdbRtbZHMeq%2FXxAiEA%2FV%2BgGvDJ7sveXfTvKLJ6NQlH84A11OX5XiAoZXDaflUq%2FwMIbxAAGgw2Mzc0MjMxODM4MDUiDAoitMHYTTmrTWzwLSrcAwug6ggjA%2FYXSFSv%2FOHVdmbpRtnDVtjMvswsdPjDXJMMOT3TiQcLl6KinLTkwjdiqYBAwUkVdZySFwuqIy868xKiI1DJhfRrjAhr1Syhn1vaXflRmjYkw5uPraBcb6e00%2FUHH8GEylIlz0%2B7QSqHL93lggJW0aaicSBptnWLf%2BUD4kDF4e0tysGQLFi8POKEB6RuUicHBbtNrlBWdyAibfA1m3%2F%2B8D%2FYWM3H8B0Rm5cVDQcqGLIeRhST4P3CfzQC2bKSWj7iA6lcpsZBSMMSxrGMs1dKRS6wm8eKZ74e70%2BCbu8GW0upteuOCNt4RP%2FaiJilGh%2F5oiQBXO6%2BRFILC8X7jk%2FP5463kTK2kvDBGJvCEOHeP0KLXpTAXRP%2BoS5KejIEcWfHz9FU8aUbSOXez1xmudzgv4HHANdbdfPklUHa5sCi6fu5QpAT46DwtTSzdG3wqPvLLD9xOFIyFjiL5Pa7bfsqKIbnbJUsLF%2B9h2fCCVbrXzpwLk3SkVGSART8%2FkP3CHYF%2BrUEFCl1EtxgepwP9vnDA59G9M3V7BZY5sBg%2Bifj8MNzOPEobZow49GPye4oxVclDOhX%2BrjuZrGEjszConuhgB7WkbyNFV4x2lvm9mkU07FmyigLDnv9MK%2Bg9tUGOqUBEoCKxoVz%2FiphIN%2B1sQxk4mFvgaQAIYFaRV0HpJ51qCQdOoU4VuV%2BRHrmsZdCzu%2FADhE15wbhNtGW4GNQnipY3jYwIO7J0xbx6gSmI9kdCYMW%2FJxOlxuph%2F4QxQVw4Kyb7VlCGo2DVW6NTiyH2WistmmW7p8Lb6DX3Dpt8Ja5LlPV8FlVcMs9iS6lyHkcpuJQD8wr%2Bjp1cFpPMtk9BjJpLQJ1TRVG&X-Amz-Signature=8f5871ab8a84f01f4409eea9e1796ae4593c3c43d84b2b2bfed0aea642dcce13&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
### 픽업 모듈 수납
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/5607ce0e-a865-4ca0-8e24-1044c0cbbcf8/R07-a-retracted.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466QK4FF7EZ%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002830Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIE6QDxdxa1Aokd3onEbRI4fFfDBynZTdbRtbZHMeq%2FXxAiEA%2FV%2BgGvDJ7sveXfTvKLJ6NQlH84A11OX5XiAoZXDaflUq%2FwMIbxAAGgw2Mzc0MjMxODM4MDUiDAoitMHYTTmrTWzwLSrcAwug6ggjA%2FYXSFSv%2FOHVdmbpRtnDVtjMvswsdPjDXJMMOT3TiQcLl6KinLTkwjdiqYBAwUkVdZySFwuqIy868xKiI1DJhfRrjAhr1Syhn1vaXflRmjYkw5uPraBcb6e00%2FUHH8GEylIlz0%2B7QSqHL93lggJW0aaicSBptnWLf%2BUD4kDF4e0tysGQLFi8POKEB6RuUicHBbtNrlBWdyAibfA1m3%2F%2B8D%2FYWM3H8B0Rm5cVDQcqGLIeRhST4P3CfzQC2bKSWj7iA6lcpsZBSMMSxrGMs1dKRS6wm8eKZ74e70%2BCbu8GW0upteuOCNt4RP%2FaiJilGh%2F5oiQBXO6%2BRFILC8X7jk%2FP5463kTK2kvDBGJvCEOHeP0KLXpTAXRP%2BoS5KejIEcWfHz9FU8aUbSOXez1xmudzgv4HHANdbdfPklUHa5sCi6fu5QpAT46DwtTSzdG3wqPvLLD9xOFIyFjiL5Pa7bfsqKIbnbJUsLF%2B9h2fCCVbrXzpwLk3SkVGSART8%2FkP3CHYF%2BrUEFCl1EtxgepwP9vnDA59G9M3V7BZY5sBg%2Bifj8MNzOPEobZow49GPye4oxVclDOhX%2BrjuZrGEjszConuhgB7WkbyNFV4x2lvm9mkU07FmyigLDnv9MK%2Bg9tUGOqUBEoCKxoVz%2FiphIN%2B1sQxk4mFvgaQAIYFaRV0HpJ51qCQdOoU4VuV%2BRHrmsZdCzu%2FADhE15wbhNtGW4GNQnipY3jYwIO7J0xbx6gSmI9kdCYMW%2FJxOlxuph%2F4QxQVw4Kyb7VlCGo2DVW6NTiyH2WistmmW7p8Lb6DX3Dpt8Ja5LlPV8FlVcMs9iS6lyHkcpuJQD8wr%2Bjp1cFpPMtk9BjJpLQJ1TRVG&X-Amz-Signature=1666c18f0fea61a034ec84831075550636c6445ee7bce7892e5a18856a80a28b&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
### 고정 외장 내부 회전
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/ebe8735e-7b5e-4122-9425-132658e6893a/R07-a-drive.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466QK4FF7EZ%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002831Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIE6QDxdxa1Aokd3onEbRI4fFfDBynZTdbRtbZHMeq%2FXxAiEA%2FV%2BgGvDJ7sveXfTvKLJ6NQlH84A11OX5XiAoZXDaflUq%2FwMIbxAAGgw2Mzc0MjMxODM4MDUiDAoitMHYTTmrTWzwLSrcAwug6ggjA%2FYXSFSv%2FOHVdmbpRtnDVtjMvswsdPjDXJMMOT3TiQcLl6KinLTkwjdiqYBAwUkVdZySFwuqIy868xKiI1DJhfRrjAhr1Syhn1vaXflRmjYkw5uPraBcb6e00%2FUHH8GEylIlz0%2B7QSqHL93lggJW0aaicSBptnWLf%2BUD4kDF4e0tysGQLFi8POKEB6RuUicHBbtNrlBWdyAibfA1m3%2F%2B8D%2FYWM3H8B0Rm5cVDQcqGLIeRhST4P3CfzQC2bKSWj7iA6lcpsZBSMMSxrGMs1dKRS6wm8eKZ74e70%2BCbu8GW0upteuOCNt4RP%2FaiJilGh%2F5oiQBXO6%2BRFILC8X7jk%2FP5463kTK2kvDBGJvCEOHeP0KLXpTAXRP%2BoS5KejIEcWfHz9FU8aUbSOXez1xmudzgv4HHANdbdfPklUHa5sCi6fu5QpAT46DwtTSzdG3wqPvLLD9xOFIyFjiL5Pa7bfsqKIbnbJUsLF%2B9h2fCCVbrXzpwLk3SkVGSART8%2FkP3CHYF%2BrUEFCl1EtxgepwP9vnDA59G9M3V7BZY5sBg%2Bifj8MNzOPEobZow49GPye4oxVclDOhX%2BrjuZrGEjszConuhgB7WkbyNFV4x2lvm9mkU07FmyigLDnv9MK%2Bg9tUGOqUBEoCKxoVz%2FiphIN%2B1sQxk4mFvgaQAIYFaRV0HpJ51qCQdOoU4VuV%2BRHrmsZdCzu%2FADhE15wbhNtGW4GNQnipY3jYwIO7J0xbx6gSmI9kdCYMW%2FJxOlxuph%2F4QxQVw4Kyb7VlCGo2DVW6NTiyH2WistmmW7p8Lb6DX3Dpt8Ja5LlPV8FlVcMs9iS6lyHkcpuJQD8wr%2Bjp1cFpPMtk9BjJpLQJ1TRVG&X-Amz-Signature=d5a45b333336145eebb36ae1fbf3fad9a5f1119b048e4db5ab2bc44e8566bf25&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
### 전체 조립 길이
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/c981f47b-b673-457f-b1c4-5a3292234c3f/R07-a-whole.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466QK4FF7EZ%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002831Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJHMEUCIE6QDxdxa1Aokd3onEbRI4fFfDBynZTdbRtbZHMeq%2FXxAiEA%2FV%2BgGvDJ7sveXfTvKLJ6NQlH84A11OX5XiAoZXDaflUq%2FwMIbxAAGgw2Mzc0MjMxODM4MDUiDAoitMHYTTmrTWzwLSrcAwug6ggjA%2FYXSFSv%2FOHVdmbpRtnDVtjMvswsdPjDXJMMOT3TiQcLl6KinLTkwjdiqYBAwUkVdZySFwuqIy868xKiI1DJhfRrjAhr1Syhn1vaXflRmjYkw5uPraBcb6e00%2FUHH8GEylIlz0%2B7QSqHL93lggJW0aaicSBptnWLf%2BUD4kDF4e0tysGQLFi8POKEB6RuUicHBbtNrlBWdyAibfA1m3%2F%2B8D%2FYWM3H8B0Rm5cVDQcqGLIeRhST4P3CfzQC2bKSWj7iA6lcpsZBSMMSxrGMs1dKRS6wm8eKZ74e70%2BCbu8GW0upteuOCNt4RP%2FaiJilGh%2F5oiQBXO6%2BRFILC8X7jk%2FP5463kTK2kvDBGJvCEOHeP0KLXpTAXRP%2BoS5KejIEcWfHz9FU8aUbSOXez1xmudzgv4HHANdbdfPklUHa5sCi6fu5QpAT46DwtTSzdG3wqPvLLD9xOFIyFjiL5Pa7bfsqKIbnbJUsLF%2B9h2fCCVbrXzpwLk3SkVGSART8%2FkP3CHYF%2BrUEFCl1EtxgepwP9vnDA59G9M3V7BZY5sBg%2Bifj8MNzOPEobZow49GPye4oxVclDOhX%2BrjuZrGEjszConuhgB7WkbyNFV4x2lvm9mkU07FmyigLDnv9MK%2Bg9tUGOqUBEoCKxoVz%2FiphIN%2B1sQxk4mFvgaQAIYFaRV0HpJ51qCQdOoU4VuV%2BRHrmsZdCzu%2FADhE15wbhNtGW4GNQnipY3jYwIO7J0xbx6gSmI9kdCYMW%2FJxOlxuph%2F4QxQVw4Kyb7VlCGo2DVW6NTiyH2WistmmW7p8Lb6DX3Dpt8Ja5LlPV8FlVcMs9iS6lyHkcpuJQD8wr%2Bjp1cFpPMtk9BjJpLQJ1TRVG&X-Amz-Signature=cbb72a651aedc0c58c2a691b91efdbf41e85ee46378ae6848044b8c637ca95ec&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
<!-- RECORD_END 3ecbf010-5ac9-8118-ba85-f4a0e4a15424 -->

<!-- RECORD_START 3ecbf010-5ac9-810c-9938-e5264b5aa442 -->
# R07 B · 카세트 전체 1R 회전 — 5제어축
Record URL: https://app.notion.com/p/3ecbf0105ac9810c9938e5264b5aa442?pvs=204

기준일: 2026-10-01. 상태: **조립 검토·제작 미승인**.
## 구조와 설계 판단
직선 손가락과 평행 구동부를 포함한 픽업 카세트 전체를 1R 베어링·구동기로 90° 회전시킵니다. 볼트는 카세트에 대한 몸통 파지를 유지한 채 함께 원호를 그립니다. 작은 팁만 비트는 구조가 아닙니다. 몸통 파지 1축 + 카세트 1R + 수납 1축 + 내부 6조 척 닫힘 1축 + 스핀들 1축, 총 5제어축입니다.
회전축은 (0,100,−80)mm의 X축 방향이며 −90°에서 0°로 움직입니다. 파지점 (0,0,14)mm의 궤적 반경은 약 137.2mm입니다. 종료점에서 볼트 축과 척 축을 맞추고 인계 후 수납합니다. 착좌 오차를 흡수하기 위해 추가 정렬축이 필요해지면 5제어축 구성이 유지되지 않을 수 있습니다.
공통 손가락 길이는 약 113.1mm, 뿌리 12×10mm·끝 3×4mm, 수납 행정은 69.5mm입니다. 척 축방향 돌출 이동은 0mm입니다.
## 검토 과제
카세트·손가락·볼트·배선 전체의 회전 영역과 관성이 검토 대상입니다. B는 A보다 제어축이 하나 적지만 소형화·경량화·사이클 단축이 입증된 것은 아닙니다.
구매부품, 척 쐐기·잠금, 재료·공차·강도·연속 간섭 검토가 미완료입니다. 실제 나사 삽입·토크 제어·로봇 제어는 포함하지 않습니다.
## GLB 모델
<file src="https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/9dee80af-983b-44a5-ae89-bbc9a8c7a4f2/R07-b-assembly-review.glb?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466UALVSTAT%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002830Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJIMEYCIQCIDizD2O%2FpSVuQ4A%2BUmkhiu2rbAaax8yKygaYw64imKAIhALRVbKLXtOkqVa7GZYu7q%2F92IlFvAtmX3vrezL7mPMa2Kv8DCHAQABoMNjM3NDIzMTgzODA1IgzOPWWQUdzZehYCB1Eq3ANsO%2ByjjW%2FbDyD14XBVzVfkxSLBZUMmRwerCHxaj7Lmd95diyyAWD48WQyF2tvO2YeOhQtMGU%2BYuDCBToVfErn9KGz8bUJRlbT9pXXaW%2FTqqO15axxxcqW4%2BhFEUdbOQCln61OAsYd%2BKr0GfWdOyYlGgwNXVdkVvHpi%2FvJeDn9sFjsueDewwADFEOfbbXwraHVE99iOKEnm7QY%2FmVNOErlAOAoYa%2FgJkOK9rf%2FkUTRucSLufTPRe6Tz06FgH3T0cNjjvz1Ut5Mim5xcSXKLzRm5NTGI9qBNPp4TIgIr0XXFLzQdgG3LOFn1zMivGfc4UkMUjXHHJHtf0wm2lpnCjbovgqokjKkKUEcRv1PknwPROjnZzsPJCMMCo38gpOzP4xcM8DUl%2FRzuI%2FpNsx%2Fxm2%2FqZ8qg%2FwT3EgUL%2FV4cwGsFz%2FwxPyU0aztP6GbjCFSZHE1pUaYn9fRWYJROpQzqmvAL7nFxsVO2RHrFCcB7Fra5E8t8x48ttBMtAEOdn0EU9%2FgT1YuG73BnGLYRe0Bl7IHdNFduXzZefDVEsUq9B%2FKXnDq74gxi74%2Bs4J7NRZoBS%2F99Mzco1OiE4deRxORhSDjRELcXuaoX5LIexVqmKcmECf%2BeT%2BKdsi9N2Bn%2FZzCIn%2FbVBjqkAWssF%2FI48gFUH%2FDs%2ByF8WF6AR%2BNfK9ET4VLhdEctl678%2BFoe7s4Fup%2FY4KfKjnLD14077HmXArfZ9m6i%2BSSr%2FiM3sAu3loKPtboieF8%2F13lVVJfnw3DQsGqHXKg4TxsV9UWbV3aie4p9Xb2xTJZQZ6HI8URgGgKsmDFfkPaDyHt6GI1kHp%2FPFr7%2BmxxmA3IlpNHgdn9idoncSsPWSAOVtkXAVVEJ&X-Amz-Signature=4e467445935aa35b889dd5c365bb40bce05df5b9785a684502271b81f1bb98f8&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject"></file>
미터 단위 시각 조립 메시입니다. 4×4 변환행렬의 대각 0.001 스케일과 GLB 헤더를 확인했습니다. STEP 솔리드나 가공용 부품도가 아니며 제작 발주에 사용할 수 없습니다.
## 모델 사진 · 2026-10-01
R07 조립 검토 뷰의 최신 사진 6장입니다. R06 재현 사진과 구분합니다. M8×35 조건을 보여주며 화면의 진행값은 조립 모션 단계입니다.
### 몸통 파지
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/8c834116-fcc7-4e1d-b0db-f6389bb337ec/R07-b-pickup.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466UALVSTAT%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002830Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJIMEYCIQCIDizD2O%2FpSVuQ4A%2BUmkhiu2rbAaax8yKygaYw64imKAIhALRVbKLXtOkqVa7GZYu7q%2F92IlFvAtmX3vrezL7mPMa2Kv8DCHAQABoMNjM3NDIzMTgzODA1IgzOPWWQUdzZehYCB1Eq3ANsO%2ByjjW%2FbDyD14XBVzVfkxSLBZUMmRwerCHxaj7Lmd95diyyAWD48WQyF2tvO2YeOhQtMGU%2BYuDCBToVfErn9KGz8bUJRlbT9pXXaW%2FTqqO15axxxcqW4%2BhFEUdbOQCln61OAsYd%2BKr0GfWdOyYlGgwNXVdkVvHpi%2FvJeDn9sFjsueDewwADFEOfbbXwraHVE99iOKEnm7QY%2FmVNOErlAOAoYa%2FgJkOK9rf%2FkUTRucSLufTPRe6Tz06FgH3T0cNjjvz1Ut5Mim5xcSXKLzRm5NTGI9qBNPp4TIgIr0XXFLzQdgG3LOFn1zMivGfc4UkMUjXHHJHtf0wm2lpnCjbovgqokjKkKUEcRv1PknwPROjnZzsPJCMMCo38gpOzP4xcM8DUl%2FRzuI%2FpNsx%2Fxm2%2FqZ8qg%2FwT3EgUL%2FV4cwGsFz%2FwxPyU0aztP6GbjCFSZHE1pUaYn9fRWYJROpQzqmvAL7nFxsVO2RHrFCcB7Fra5E8t8x48ttBMtAEOdn0EU9%2FgT1YuG73BnGLYRe0Bl7IHdNFduXzZefDVEsUq9B%2FKXnDq74gxi74%2Bs4J7NRZoBS%2F99Mzco1OiE4deRxORhSDjRELcXuaoX5LIexVqmKcmECf%2BeT%2BKdsi9N2Bn%2FZzCIn%2FbVBjqkAWssF%2FI48gFUH%2FDs%2ByF8WF6AR%2BNfK9ET4VLhdEctl678%2BFoe7s4Fup%2FY4KfKjnLD14077HmXArfZ9m6i%2BSSr%2FiM3sAu3loKPtboieF8%2F13lVVJfnw3DQsGqHXKg4TxsV9UWbV3aie4p9Xb2xTJZQZ6HI8URgGgKsmDFfkPaDyHt6GI1kHp%2FPFr7%2BmxxmA3IlpNHgdn9idoncSsPWSAOVtkXAVVEJ&X-Amz-Signature=3e210ba2b35d790e560522a42ac33d471a0f3030ef65bfebd38442405a995fa2&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
### 헤드를 위로 세우기
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/de42f1bd-e10f-4177-8f87-ab1e869f00ae/R07-b-righting.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466UALVSTAT%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002830Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJIMEYCIQCIDizD2O%2FpSVuQ4A%2BUmkhiu2rbAaax8yKygaYw64imKAIhALRVbKLXtOkqVa7GZYu7q%2F92IlFvAtmX3vrezL7mPMa2Kv8DCHAQABoMNjM3NDIzMTgzODA1IgzOPWWQUdzZehYCB1Eq3ANsO%2ByjjW%2FbDyD14XBVzVfkxSLBZUMmRwerCHxaj7Lmd95diyyAWD48WQyF2tvO2YeOhQtMGU%2BYuDCBToVfErn9KGz8bUJRlbT9pXXaW%2FTqqO15axxxcqW4%2BhFEUdbOQCln61OAsYd%2BKr0GfWdOyYlGgwNXVdkVvHpi%2FvJeDn9sFjsueDewwADFEOfbbXwraHVE99iOKEnm7QY%2FmVNOErlAOAoYa%2FgJkOK9rf%2FkUTRucSLufTPRe6Tz06FgH3T0cNjjvz1Ut5Mim5xcSXKLzRm5NTGI9qBNPp4TIgIr0XXFLzQdgG3LOFn1zMivGfc4UkMUjXHHJHtf0wm2lpnCjbovgqokjKkKUEcRv1PknwPROjnZzsPJCMMCo38gpOzP4xcM8DUl%2FRzuI%2FpNsx%2Fxm2%2FqZ8qg%2FwT3EgUL%2FV4cwGsFz%2FwxPyU0aztP6GbjCFSZHE1pUaYn9fRWYJROpQzqmvAL7nFxsVO2RHrFCcB7Fra5E8t8x48ttBMtAEOdn0EU9%2FgT1YuG73BnGLYRe0Bl7IHdNFduXzZefDVEsUq9B%2FKXnDq74gxi74%2Bs4J7NRZoBS%2F99Mzco1OiE4deRxORhSDjRELcXuaoX5LIexVqmKcmECf%2BeT%2BKdsi9N2Bn%2FZzCIn%2FbVBjqkAWssF%2FI48gFUH%2FDs%2ByF8WF6AR%2BNfK9ET4VLhdEctl678%2BFoe7s4Fup%2FY4KfKjnLD14077HmXArfZ9m6i%2BSSr%2FiM3sAu3loKPtboieF8%2F13lVVJfnw3DQsGqHXKg4TxsV9UWbV3aie4p9Xb2xTJZQZ6HI8URgGgKsmDFfkPaDyHt6GI1kHp%2FPFr7%2BmxxmA3IlpNHgdn9idoncSsPWSAOVtkXAVVEJ&X-Amz-Signature=51e7f4bbadfad063d23c813bc0fe0135df9347b00fabc259bd15dd892e1feae2&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
### 내부 6조 척에 헤드 인계
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/dcf1fc15-2738-42bd-acdd-0c64b7f7ec1f/R07-b-handoff.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466UALVSTAT%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002830Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJIMEYCIQCIDizD2O%2FpSVuQ4A%2BUmkhiu2rbAaax8yKygaYw64imKAIhALRVbKLXtOkqVa7GZYu7q%2F92IlFvAtmX3vrezL7mPMa2Kv8DCHAQABoMNjM3NDIzMTgzODA1IgzOPWWQUdzZehYCB1Eq3ANsO%2ByjjW%2FbDyD14XBVzVfkxSLBZUMmRwerCHxaj7Lmd95diyyAWD48WQyF2tvO2YeOhQtMGU%2BYuDCBToVfErn9KGz8bUJRlbT9pXXaW%2FTqqO15axxxcqW4%2BhFEUdbOQCln61OAsYd%2BKr0GfWdOyYlGgwNXVdkVvHpi%2FvJeDn9sFjsueDewwADFEOfbbXwraHVE99iOKEnm7QY%2FmVNOErlAOAoYa%2FgJkOK9rf%2FkUTRucSLufTPRe6Tz06FgH3T0cNjjvz1Ut5Mim5xcSXKLzRm5NTGI9qBNPp4TIgIr0XXFLzQdgG3LOFn1zMivGfc4UkMUjXHHJHtf0wm2lpnCjbovgqokjKkKUEcRv1PknwPROjnZzsPJCMMCo38gpOzP4xcM8DUl%2FRzuI%2FpNsx%2Fxm2%2FqZ8qg%2FwT3EgUL%2FV4cwGsFz%2FwxPyU0aztP6GbjCFSZHE1pUaYn9fRWYJROpQzqmvAL7nFxsVO2RHrFCcB7Fra5E8t8x48ttBMtAEOdn0EU9%2FgT1YuG73BnGLYRe0Bl7IHdNFduXzZefDVEsUq9B%2FKXnDq74gxi74%2Bs4J7NRZoBS%2F99Mzco1OiE4deRxORhSDjRELcXuaoX5LIexVqmKcmECf%2BeT%2BKdsi9N2Bn%2FZzCIn%2FbVBjqkAWssF%2FI48gFUH%2FDs%2ByF8WF6AR%2BNfK9ET4VLhdEctl678%2BFoe7s4Fup%2FY4KfKjnLD14077HmXArfZ9m6i%2BSSr%2FiM3sAu3loKPtboieF8%2F13lVVJfnw3DQsGqHXKg4TxsV9UWbV3aie4p9Xb2xTJZQZ6HI8URgGgKsmDFfkPaDyHt6GI1kHp%2FPFr7%2BmxxmA3IlpNHgdn9idoncSsPWSAOVtkXAVVEJ&X-Amz-Signature=6ebbcc2d81fa33f106b4977d1877ce7207091242c4c43cdfa9465aa9bd8cf71c&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
### 픽업 모듈 수납
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/7018bbe9-e8b7-4bca-be7e-d6951a681ac6/R07-b-retracted.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466UALVSTAT%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002830Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJIMEYCIQCIDizD2O%2FpSVuQ4A%2BUmkhiu2rbAaax8yKygaYw64imKAIhALRVbKLXtOkqVa7GZYu7q%2F92IlFvAtmX3vrezL7mPMa2Kv8DCHAQABoMNjM3NDIzMTgzODA1IgzOPWWQUdzZehYCB1Eq3ANsO%2ByjjW%2FbDyD14XBVzVfkxSLBZUMmRwerCHxaj7Lmd95diyyAWD48WQyF2tvO2YeOhQtMGU%2BYuDCBToVfErn9KGz8bUJRlbT9pXXaW%2FTqqO15axxxcqW4%2BhFEUdbOQCln61OAsYd%2BKr0GfWdOyYlGgwNXVdkVvHpi%2FvJeDn9sFjsueDewwADFEOfbbXwraHVE99iOKEnm7QY%2FmVNOErlAOAoYa%2FgJkOK9rf%2FkUTRucSLufTPRe6Tz06FgH3T0cNjjvz1Ut5Mim5xcSXKLzRm5NTGI9qBNPp4TIgIr0XXFLzQdgG3LOFn1zMivGfc4UkMUjXHHJHtf0wm2lpnCjbovgqokjKkKUEcRv1PknwPROjnZzsPJCMMCo38gpOzP4xcM8DUl%2FRzuI%2FpNsx%2Fxm2%2FqZ8qg%2FwT3EgUL%2FV4cwGsFz%2FwxPyU0aztP6GbjCFSZHE1pUaYn9fRWYJROpQzqmvAL7nFxsVO2RHrFCcB7Fra5E8t8x48ttBMtAEOdn0EU9%2FgT1YuG73BnGLYRe0Bl7IHdNFduXzZefDVEsUq9B%2FKXnDq74gxi74%2Bs4J7NRZoBS%2F99Mzco1OiE4deRxORhSDjRELcXuaoX5LIexVqmKcmECf%2BeT%2BKdsi9N2Bn%2FZzCIn%2FbVBjqkAWssF%2FI48gFUH%2FDs%2ByF8WF6AR%2BNfK9ET4VLhdEctl678%2BFoe7s4Fup%2FY4KfKjnLD14077HmXArfZ9m6i%2BSSr%2FiM3sAu3loKPtboieF8%2F13lVVJfnw3DQsGqHXKg4TxsV9UWbV3aie4p9Xb2xTJZQZ6HI8URgGgKsmDFfkPaDyHt6GI1kHp%2FPFr7%2BmxxmA3IlpNHgdn9idoncSsPWSAOVtkXAVVEJ&X-Amz-Signature=4f20f01b65556d538bc34fefef66881a8be83f2c3b1527b6346fb3fd19c8620f&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
### 고정 외장 내부 회전
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/f0888035-958b-4392-80ff-83ee95cab939/R07-b-drive.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466UALVSTAT%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002830Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJIMEYCIQCIDizD2O%2FpSVuQ4A%2BUmkhiu2rbAaax8yKygaYw64imKAIhALRVbKLXtOkqVa7GZYu7q%2F92IlFvAtmX3vrezL7mPMa2Kv8DCHAQABoMNjM3NDIzMTgzODA1IgzOPWWQUdzZehYCB1Eq3ANsO%2ByjjW%2FbDyD14XBVzVfkxSLBZUMmRwerCHxaj7Lmd95diyyAWD48WQyF2tvO2YeOhQtMGU%2BYuDCBToVfErn9KGz8bUJRlbT9pXXaW%2FTqqO15axxxcqW4%2BhFEUdbOQCln61OAsYd%2BKr0GfWdOyYlGgwNXVdkVvHpi%2FvJeDn9sFjsueDewwADFEOfbbXwraHVE99iOKEnm7QY%2FmVNOErlAOAoYa%2FgJkOK9rf%2FkUTRucSLufTPRe6Tz06FgH3T0cNjjvz1Ut5Mim5xcSXKLzRm5NTGI9qBNPp4TIgIr0XXFLzQdgG3LOFn1zMivGfc4UkMUjXHHJHtf0wm2lpnCjbovgqokjKkKUEcRv1PknwPROjnZzsPJCMMCo38gpOzP4xcM8DUl%2FRzuI%2FpNsx%2Fxm2%2FqZ8qg%2FwT3EgUL%2FV4cwGsFz%2FwxPyU0aztP6GbjCFSZHE1pUaYn9fRWYJROpQzqmvAL7nFxsVO2RHrFCcB7Fra5E8t8x48ttBMtAEOdn0EU9%2FgT1YuG73BnGLYRe0Bl7IHdNFduXzZefDVEsUq9B%2FKXnDq74gxi74%2Bs4J7NRZoBS%2F99Mzco1OiE4deRxORhSDjRELcXuaoX5LIexVqmKcmECf%2BeT%2BKdsi9N2Bn%2FZzCIn%2FbVBjqkAWssF%2FI48gFUH%2FDs%2ByF8WF6AR%2BNfK9ET4VLhdEctl678%2BFoe7s4Fup%2FY4KfKjnLD14077HmXArfZ9m6i%2BSSr%2FiM3sAu3loKPtboieF8%2F13lVVJfnw3DQsGqHXKg4TxsV9UWbV3aie4p9Xb2xTJZQZ6HI8URgGgKsmDFfkPaDyHt6GI1kHp%2FPFr7%2BmxxmA3IlpNHgdn9idoncSsPWSAOVtkXAVVEJ&X-Amz-Signature=bec4408437e04a15cc84ac9d2a9c0ec46cb29e7bebb86f02568cc04f4170d82d&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
### 전체 조립 길이
![](https://prod-files-secure.s3.us-west-2.amazonaws.com/e7b440a6-94ca-478d-bec0-bb0968af7523/8dddb0d0-7cd0-437b-adb8-8c265ca3feca/R07-b-whole.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAZI2LB466UALVSTAT%2F20261001%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20261001T002830Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJIMEYCIQCIDizD2O%2FpSVuQ4A%2BUmkhiu2rbAaax8yKygaYw64imKAIhALRVbKLXtOkqVa7GZYu7q%2F92IlFvAtmX3vrezL7mPMa2Kv8DCHAQABoMNjM3NDIzMTgzODA1IgzOPWWQUdzZehYCB1Eq3ANsO%2ByjjW%2FbDyD14XBVzVfkxSLBZUMmRwerCHxaj7Lmd95diyyAWD48WQyF2tvO2YeOhQtMGU%2BYuDCBToVfErn9KGz8bUJRlbT9pXXaW%2FTqqO15axxxcqW4%2BhFEUdbOQCln61OAsYd%2BKr0GfWdOyYlGgwNXVdkVvHpi%2FvJeDn9sFjsueDewwADFEOfbbXwraHVE99iOKEnm7QY%2FmVNOErlAOAoYa%2FgJkOK9rf%2FkUTRucSLufTPRe6Tz06FgH3T0cNjjvz1Ut5Mim5xcSXKLzRm5NTGI9qBNPp4TIgIr0XXFLzQdgG3LOFn1zMivGfc4UkMUjXHHJHtf0wm2lpnCjbovgqokjKkKUEcRv1PknwPROjnZzsPJCMMCo38gpOzP4xcM8DUl%2FRzuI%2FpNsx%2Fxm2%2FqZ8qg%2FwT3EgUL%2FV4cwGsFz%2FwxPyU0aztP6GbjCFSZHE1pUaYn9fRWYJROpQzqmvAL7nFxsVO2RHrFCcB7Fra5E8t8x48ttBMtAEOdn0EU9%2FgT1YuG73BnGLYRe0Bl7IHdNFduXzZefDVEsUq9B%2FKXnDq74gxi74%2Bs4J7NRZoBS%2F99Mzco1OiE4deRxORhSDjRELcXuaoX5LIexVqmKcmECf%2BeT%2BKdsi9N2Bn%2FZzCIn%2FbVBjqkAWssF%2FI48gFUH%2FDs%2ByF8WF6AR%2BNfK9ET4VLhdEctl678%2BFoe7s4Fup%2FY4KfKjnLD14077HmXArfZ9m6i%2BSSr%2FiM3sAu3loKPtboieF8%2F13lVVJfnw3DQsGqHXKg4TxsV9UWbV3aie4p9Xb2xTJZQZ6HI8URgGgKsmDFfkPaDyHt6GI1kHp%2FPFr7%2BmxxmA3IlpNHgdn9idoncSsPWSAOVtkXAVVEJ&X-Amz-Signature=ceedd0399027af7ea6a884a9e5aa9c627fe7eff05b257e971da9f297c71e91c7&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject)
<!-- RECORD_END 3ecbf010-5ac9-810c-9938-e5264b5aa442 -->

<!-- RECORD_START LOCAL_NOTION_ARCHIVE -->
# NOTION_ARCHIVE.md
Record URL: /home/yg1/robotarm_main/tools/gripper_concept_demo/NOTION_ARCHIVE.md

# Notion 버전 기록

최초 기록일: 2026-09-30. 갱신일: 2026-10-01. 위치: Bin_Picking 문서 데이터베이스.

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

<!-- RECORD_END LOCAL_NOTION_ARCHIVE -->

