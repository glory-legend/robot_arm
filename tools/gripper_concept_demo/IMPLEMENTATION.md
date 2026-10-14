# Implementation ledger

Authority: approved conversation plan, 2026-09-30.

- Scope: standalone browser demonstrator, full FR3, procedural custom gripper, deterministic animated cycle, Korean controls, three illustrative bolt presets.
- Ruling: implement only in a new tools/gripper_concept_demo directory in the current feature checkout; preserve all pre-existing dirty files and vendored originals. No commit or branch change requested.
- Task 1: dependencies, asset preparation, deterministic timeline and tests.
- Task 2: robot chain, offline trajectory generation, procedural model, scene.
- Task 3: responsive controls and browser verification.
- Task 4: independent final review and fixes.

## Completion evidence

- Task 1 complete: timeline tests were observed failing against the stub, then passed after implementation. Asset preparation copies eight FR3 meshes and retains LICENSE/NOTICE without changing vendor files.
- Task 2 complete: three offline paths generated, 361 samples each, maximum flange position residual below 0.001 mm at sampled poses. This is an IK residual, not real robot accuracy or collision validation.
- Task 3 complete: browser UI, full arm, inset and detail views, presets, seek/playback, transparent and exploded states implemented. Desktop/mobile screenshots inspected.
- Ruling: background bolts are static illustration; gripper motion is prescribed, not contact dynamics. Hex/chuck angular alignment is assumed. Guide and fingers retract before fastening for visible clearance.
- Final review: independent reviewer found one significant lifecycle issue (unconditional pagehide disposal). Added a cached-page resize regression, observed it fail, and guarded persisted pagehide. Reviewer verified the fix; no remaining significant findings.
- Accessibility regression: phase-number contrast failed automated WCAG checks; changed it to the existing muted text token, then checked again.
- Verification: build, TypeScript, 8 unit tests, formatter, strict UI audit pass. Existing Python suite: 245 passed with 2 existing websockets deprecation warnings. Browser suite covers full continuous cycle, three presets, arbitrary seeking, mobile/keyboard/reduced motion, asset/WebGL errors, automated accessibility and cached-page restoration.
- Integration: all work remains in this new folder on the existing feature checkout. No commits, merges, publications or modifications to existing ROS source were performed. Local development server remains available at 127.0.0.1:5173.

## DG3FM reference revision · 2026-09-30

- User requested articulated curling fingers and then specified Tesollo DG3FM as the reference. Replaced the previous slide gripper with the official mesh and 12-joint hierarchy.
- Upstream visual meshes and URDF are pinned to c49d3768900b30e6724fd2c56fe911f04cdfbf18 with BSD-3-Clause LICENSE and NOTICE. Custom narrow fingertips replace stock broad pads; the central guide/chuck is a separate conceptual addition.
- Offline bounded IK keeps three contact pads against M6/M8/M10 bolts during a 30 mm palm draw. Fixed knuckles, rigid link distances, angle limits, interpolated contact error below 0.1 mm and stowed fingertip clearance are covered by four new unit tests. These checks do not establish collision-free or physically stable real grasps.
- Full-arm path updated for the new receiver height. Default detail camera looks between fingers, housing starts opaque, explanatory copy describes joint curling. Optional view/time URL parameters open a particular demonstration state.
- Final DG3FM verification: 12 unit tests, 10 browser tests, TypeScript/build, formatter and strict UI audit pass. Desktop draw/handoff/stow screenshots inspected. Independent code review found no critical or important issues.
- Test-run note: an overlapping asset-preparation build triggered Vite reload during the first continuous-playback run; a clean run with no source writes passed all 10 browser tests. The production bundle emits a non-blocking size warning (about 881 kB raw / 223 kB gzip).

## Hand-E + straight rod revision · 2026-09-30

- User replaced the DG3FM concept with an existing two-jaw Robotiq gripper plus one small two-axis rod, removing the funnel. Follow-up clarified a single straight rod pressing the bolt end up/down, with the head ultimately facing upward. The temporary articulated accessory was replaced by two linear axes (approach/retract and vertical stroke).
- Original vendored Hand-E body/fingers and prismatic jaw travel retained. The accessory contacts the shaft 3 mm from its end and rotates it around a fixed grasp point. It supports the bolt before grip force is reduced, then regripping precedes support withdrawal. Force reduction, friction and stability remain explanatory assumptions.
- Earlier head-chuck fastening sequence retained. After transfer the chuck advances 53 mm to clear the stock jaw tips; arm path recomputed for the new tool height. DG3FM runtime sources/assets removed from this app; previous reference files copied to /tmp/gripper-demo-dg3fm-reference for local recovery.
- Scope stays within tools/gripper_concept_demo; vendored Hand-E and all ROS sources remain unchanged.

## Final biomimetic revision · 2026-09-30

- User explicitly selected redesigning both main jaws into human/animal-inspired fingers. Supersedes the Hand-E and straight-rod sections above.
- Entire gripper is now an original procedural palm, two 3-joint main fingers, and a slimmer 2-joint auxiliary thumb. Thumb contacts 3 mm from bolt end and rotates the shaft about the main pinch, ending head-up. No funnel or linear-slider righting mechanism.
- The former stock-jaw/head collision issue no longer applies to these new shapes. Geometry and motion remain illustrative, with no full collision/contact/force certification.
- Added rigid-bone, two-main-finger contact, auxiliary-thumb contact, clearance and head-up regression checks. Current unit suite: 14 tests. Head-holder extension is now 70 mm, leaving final head height and fastening path unchanged.

## 2026-09-30 · 실제 빈픽킹 기준 모델 적용

실제 빈픽킹 기준 모델로 2F-85 본체·관절 링크 메시를 적용했다. 비교와 선정 근거는 GRIPPER_SELECTION.md를 참조한다. 폭 6mm의 규격별 교환 손끝, 별도 2R 엄지와 헤드 척은 자체 개념 설계다. 주집게 URDF 종속 관절과 고정 길이 손끝, 헤드 위로 정렬, 70mm 척 전진을 구현했다. 척의 개방 반경 24mm, 허브 후퇴 및 볼트·척 공통 30° 위상으로 확인된 간섭을 수정했다.

검증: 단위 테스트 15개, 브라우저 테스트 10개, TypeScript·Vite 빌드·Prettier·strict UI 감사 통과. 코드 검토에서 추가 중요 지적 없음. 실물 파지 성공률·마찰·토크·전체 기구 충돌은 검증하지 않았다.
