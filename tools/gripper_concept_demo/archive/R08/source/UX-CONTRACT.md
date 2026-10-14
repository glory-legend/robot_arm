# 조작 계약

한국어 단일 화면 3D 도구다. 시각 토큰과 네이티브 컨트롤 선택 근거는 DESIGN.md를 참조한다.

| Capability     | Canonical owner                 | Source of truth         | Allowed variants              | Verification           |
| -------------- | ------------------------------- | ----------------------- | ----------------------------- | ---------------------- |
| Select/Listbox | src/main.ts native select       | DESIGN.md               | bolt / speed                  | tests/demo.e2e.ts      |
| Timeline       | src/timeline.ts and src/main.ts | approved cycle sequence | play / pause / seek           | tests/timeline.test.ts |
| Camera         | src/viewer.ts                   | DESIGN.md               | whole / detail / front / side | tests/demo.e2e.ts      |

- 최초 로딩 중에는 재생·타임라인·시점 버튼을 비활성화한다. 실패하면 인라인 설명과 다시 불러오기를 제공한다.
- 초기에는 정지한다. 재생은 끝에서 정지하며 끝에서 재생하면 처음으로 이동한다.
- 타임라인과 단계 선택은 정지하고 해당 시각으로 이동한다. 시점 변경은 재생 위치를 유지한다.
- 볼트 변경은 정지하고 처음으로 이동한다. 분해 보기 선택은 정지한다. 재생하면 조립 상태로 복원한다.
- 숨겨진 탭에서는 재생을 정지한다. 자동 재생이나 무관한 모션은 없다.
- 키보드로 네이티브 버튼·선택·슬라이더를 조작할 수 있다. 카메라 드래그의 대안으로 회전/확대 버튼을 제공한다.
- 데이터 저장, 로그인, 네트워크 명령, ROS 제어는 없다. 정적 로컬 자산만 읽는다.
