# R08 공통 몸체 통합형 구현 계획

> 구현 방식: superpowers:executing-plans. 기존 작업 디렉터리에서 새 R08 모듈을 추가하고 보존된 R07 소스와 아카이브를 유지한다.

**목표:** 하나의 몸체에 파지·정렬·체결 기능을 배치한 브라우저 모델을 만든다.
**구조:** 운동학, Three.js 조립 모델, 화면을 별도 모듈로 작성한다. 기존 R07 화면은 engineering.html에 보존하고 기본 화면을 R08로 연결한다.
**기술:** TypeScript, Three.js, Vite, Vitest, Playwright.
**설계:** R08.md.

## 제약과 검토 항목

- 노출된 육각 헤드 M6~M10, 토크 미정, 제작 미승인 상태를 유지한다.
- 척 축방향 이동은 0 mm이며 헤드 고정 전에 몸통 파지를 풀지 않는다.
- 손가락 접힘이 끝난 다음 수납하고 수납 이후에 회전한다.
- 엄지 38 + 38 mm의 실제 링크 길이와 도달 범위를 검사한다.
- 모바일 화면, 재생·수동 탐색, 내부 보기, 규격 전환, 이전 버전 링크, GLB 저장을 확인한다.

## 작업

1. tests/integrated.test.ts에 파지 인계·엄지 도달·수납 공간 검사를 먼저 작성한다. src/integrated-kinematics.ts에 integratedPose, boltMatrix, thumbPoints, fingerMatrix를 구현한다.
2. src/integrated-model.ts에 공통 프레임, 분할 외장, 중앙 척, 측면 캐리지, 직선 팁, 엄지를 배치한다. src/integrated.ts에서 재생·시점·투명 보기·GLB·CSV 저장을 연결한다.
3. 단위 검사와 브라우저 검사를 실행하고 실제 캡처를 검토한다. 사진·GLB·소스·검증 결과를 archive/R08에 보관한다.
4. 작성한 설계 기록과 이 계획에 im-not-ai 플러그인을 적용한 뒤 Notion 상위 기록 아래 R08 페이지에 사진과 파일을 첨부한다.

검증 명령: npm test, npm run typecheck, npm run build, PLAYWRIGHT_BROWSERS_PATH=/tmp/gripper-playwright npx playwright test.
