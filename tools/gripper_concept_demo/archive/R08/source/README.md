# 볼트 그리퍼 · R08 공통 몸체 조립 검토

현재 기본 화면은 파지·볼트 정렬·헤드 고정·체결 기구를 하나의 몸체에 배치한 R08 조립 검토 모델입니다. 노출된 육각 헤드의 M6 × 20 / M8 × 35 / M10 × 50 볼트를 대상으로 합니다. 체결 토크·전체 질량은 미확정이며 모터·감속기·척 폐쇄 구동부는 새로 선정해야 합니다.

- [R08 통합 조립 보기](http://127.0.0.1:5173/)
- [R08 설계·치수·검토 범위](R08.md)
- [R08 Notion 기록](https://app.notion.com/p/3ecbf0105ac9818c970dd335a86c5a12)
- [R07 A 조립 보기](http://127.0.0.1:5173/engineering.html?variant=a&progress=50)
- [R07 B 조립 보기](http://127.0.0.1:5173/engineering.html?variant=b&progress=28)
- [R07 기계 검토·치수·남은 설계](MECHANICAL_REVIEW.md)
- [Notion 버전별 기록](NOTION_ARCHIVE.md)

R08은 일시정지 상태로 열리며 전체·확대·측면·정면 보기와 외장 투명화·커버 제거로 내부 배치를 살펴볼 수 있습니다. GLB 조립 메시와 CSV 부품 검토표를 저장할 수 있습니다. 구매부품, 척 잠금, 강도·공차가 미확정이므로 **현재 모델은 제작 승인 도면이 아닙니다.**

R07 A/B 조립 검토는 [engineering.html](http://127.0.0.1:5173/engineering.html)에, R06의 FR3 전체 동작 시연은 [concept.html](http://127.0.0.1:5173/concept.html)에 보존합니다. 아래 내용은 R06 실행·조작 기록입니다. 현재 R08 소스는 `src/integrated*.ts`, `src/integrated.css`이며 R07 소스는 `src/engineering*.ts`, `src/engineering.css`입니다.

---

# 볼트 그리퍼 · 동작 연구실

FR3 로봇팔이 볼트를 집고 보조 엄지로 세운 뒤 체결하는 **브라우저용 3D 개념 시연**입니다. ROS나 Gazebo를 실행할 필요가 없습니다.

## 실행

Node.js 22.12 이상(현재 환경: 24)을 사용합니다.

```bash
cd /home/yg1/robotarm_main/tools/gripper_concept_demo
npm ci
npm run dev
```

브라우저에서 **http://127.0.0.1:5173/** 을 엽니다. 서버는 로컬 주소에만 바인딩됩니다. 의존성 설치 후에는 모델·글꼴·스크립트를 위해 외부 서비스에 연결하지 않습니다. 포트가 이미 사용 중이면 기존 서버를 종료하거나 `npm run dev -- --port 5174`를 사용합니다.

[그리퍼 확대 · 보조 엄지로 세우기](http://127.0.0.1:5173/concept.html?view=detail&time=10)으로 바로 열 수도 있습니다.

## 조작

- **재생 / 일시정지 / 처음으로**: 70초 설명용 사이클. 끝에서 정지합니다.
- **타임라인 / 단계 버튼**: 원하는 순간으로 이동하고 멈춥니다. 이전·다음 단계 이동도 가능합니다.
- **전체 / 그리퍼 확대 / 정면 / 측면**: 재생 위치를 유지하며 시점을 바꿉니다.
- **드래그 / 휠**: 시점 회전·확대. 오른쪽 드래그는 이동입니다. 회전·확대 버튼으로도 조작할 수 있습니다.
- **볼트 규격**: M6×20, M8×35, M10×50을 바꿔 봅니다. 변경 시 사이클을 초기화합니다.
- **외장 투명하게 / 부품 이름표 / 확대창**: 내부 파지 인계를 확인합니다. 이름표는 확대 시점에서, 확대창은 넓은 화면에서 표시됩니다.
- **분해 보기**: 재생을 정지하고 부품을 벌립니다. 해제하면 조립 상태로 돌아오며 재생을 누르면 자동 복원됩니다.
- 브라우저 탭을 떠나면 재생을 정지합니다.

## 이전 모델: R06 두 가지 내부 회전 구조

- **A**: 별도 내부 6조 척이 헤드를 잡고 주집게 전체를 55.7mm 수납합니다.
- **B**: 같은 2조 회전 카세트에 몸통 팁과 헤드 접촉면을 넣고 몸통 팁만 24mm 수납합니다. 별도 6조 척을 제거한 구조 축소안이며 단순 절첩형이 아닙니다.
- 공통: 팁 6×5→1.6×2.4mm, 50mm 엄지, 체결부 전진 0mm. 본체 내부에서만 회전하고 로봇팔이 전체 도구를 전진시켜 삽입합니다.

[A 보기](http://127.0.0.1:5173/concept.html?variant=a&view=detail&time=18) · [B 보기](http://127.0.0.1:5173/concept.html?variant=b&view=detail&time=18)

오른쪽 버튼으로 같은 동작 시각에서 A/B를 전환합니다. [현재 구조·비교·한계](R06.md), [이전R05 설계 근거](REDESIGN.md), [Notion 보존 목록](NOTION_ARCHIVE.md)을 참고하세요. R05와 이전 원본은 archive/에 보존하며 실행 소스와 섞지 않습니다.

실제 캠 구동력·파지 안정성·체결 토크·전 기구 충돌은 실물 검증되지 않았습니다. 본체의 모터 크기를 생략하지 않고도 기구 기능과 운동 차이를 비교하는 동작 설명용 모델입니다.

## 구조와 자산

- `src/timeline.ts`: 단계, 시간별 주집게·엄지·척 상태. 역방향 탐색에도 같은 결과.
- `src/kinematics.ts`: FR3 순기구학, 경로 보간, 강체 볼트의 세계 좌표.
- `src/models.ts`: FR3 읽기, 볼트·작업대 형상.
- `src/gripper.ts`: 일자형 테이퍼 팁·보조 엄지·6조 척·후퇴 레일·체결 스핀들 설치 공간.
- `src/rod-kinematics.ts`: 주집게의 평행 개폐·후퇴와 보조 엄지의 관절 운동학, 파지점 기준 볼트 회전, 끝부분 접촉 경로.
- `src/viewer.ts`: 렌더링, 전체/확대 카메라, 이름표, 리소스 해제.
- `src/main.ts`, `src/style.css`: 한국어 조작 화면.
- `scripts/prepare-assets.mjs`: 저장소의 FR3 자산을 `public/fr3/`로 복사하고 출처·라이선스를 보존합니다. FR3 관절 JSON도 생성합니다. `assets/robotiq-2f85/`의 자체 포함 자산도 `public/robotiq-2f85/`로 복사합니다. dev/build 전에 자동 실행하며 원본을 수정하지 않습니다.
- `scripts/generate-motion.py`: 관절 제한을 적용한 역기구학으로 세 규격의 경로를 생성합니다. **재생에는 Python이 필요 없습니다.** 경로를 변경할 때만 NumPy/SciPy를 설치한 Python으로 실행합니다.

세계 좌표는 미터·Z-up, 그리퍼 로컬 +Z는 볼트 끝 방향입니다. FR3 DAE의 Z-up을 유지하며 link7의 시각 메시 회전과 고정 플랜지 오프셋을 반영합니다.

## 검증 및 정적 배포 파일

```bash
npm test
npm run typecheck
npm run format:check
npm run build
# 처음 한 번: 검증용 브라우저 설치
npx playwright install chromium
npm run test:browser
```

브라우저 테스트는 개발 서버를 자동 실행하거나 기존 5173 서버를 재사용합니다. 개발 환경에서 브라우저를 `/tmp/gripper-playwright`에 설치했다면 `PLAYWRIGHT_BROWSERS_PATH=/tmp/gripper-playwright npm run test:browser`를 사용합니다. 스크린샷은 `test-results/`에 생성됩니다.

`npm run build`의 `dist/`는 정적 HTTP 서버로 제공할 수 있습니다. 로컬 확인은 `npm run preview`를 사용합니다. 파일을 `file://`로 직접 열지 않습니다.

경로 재계산:

```bash
npm run prepare:assets
python3 scripts/generate-motion.py
npm test
```

## 라이선스

FR3 메시·기구학은 Franka Robotics GmbH의 `src/franka_description`에서 가져온 Apache-2.0 자산입니다. 준비 스크립트가 원본 LICENSE와 NOTICE를 시연과 빌드 결과에 포함합니다. Three.js 등 라이브러리는 각 패키지 라이선스를 따릅니다. 이 프로젝트의 코드는 저장소 최상위 Apache-2.0 라이선스를 따릅니다.

이전 R04 비교용으로 보존한 2F-85 링크 자산은 PickNik Robotics의 `ros2_robotiq_gripper` 패키지(BSD-3-Clause)에서 가져왔으며 원본 LICENSE·NOTICE·파일 해시를 포함합니다. 출처와 가공 범위는 `assets/robotiq-2f85/NOTICE`를 참조합니다. 추가 손끝·보조 엄지·척은 자체 개념 형상입니다.
