#!/usr/bin/env python3
"""R07 예비 하중 민감도 계산. 표준 라이브러리만 사용하며 정격을 판정하지 않는다.

입력: 토크 N·m, 길이 mm, 힘 N. 출력: 힘 N, 전단응력 MPa, 토크 N·m.
원형 패드는 균일 접촉압력과 쿨롱 마찰을 가정한다. N은 패드 한 개의 법선력이다.
"""

import argparse
import json
import math


def nonnegative(value):
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("유한한 0 이상의 수를 입력하세요.")
    return number


def positive(value):
    number = nonnegative(value)
    if number == 0:
        raise argparse.ArgumentTypeError("0보다 큰 수를 입력하세요.")
    return number


def equivalent_tangential_force(torque_nm, across_flats_mm):
    """AF/2를 등가 반경으로 둔 접선력. 턱의 법선 파지력이 아니다."""
    return 2 * torque_nm / (across_flats_mm / 1000)


def solid_shaft_shear_mpa(torque_nm, diameter_mm):
    """노치 없는 중실 원형축, 순수 비틀림의 외주 최대 전단응력."""
    return 16 * torque_nm * 1000 / (math.pi * diameter_mm**3)


def reaction_tab_force(torque_nm, radius_mm):
    """반대편 두 탭이 같은 반경에서 토크를 균등 분담할 때 탭당 접선력."""
    return torque_nm / (2 * radius_mm / 1000)


def pad_torque_nm(mu, normal_force_per_pad_n, radius_mm):
    """패드 한 개의 면내 마찰 비틀림 한계. 패드 회전축과 법선이 일치."""
    return 2 * mu * normal_force_per_pad_n * (radius_mm / 1000) / 3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--torques", nargs="+", type=nonnegative, default=[20, 40, 60],
                        help="민감도용 토크 N·m. 실제 체결 토크가 아님 (기본: 20 40 60)")
    parser.add_argument("--across-flats", nargs="+", type=positive, default=[10, 13, 17],
                        help="예시 육각 헤드 대변 mm (기본: 10 13 17)")
    parser.add_argument("--shaft-diameters", nargs="+", type=positive, default=[6, 8, 10, 12],
                        help="예시 중실 출력축 지름 mm. 볼트 호칭이 아님")
    parser.add_argument("--tab-radius", type=positive, default=25,
                        help="스핀들 중심에서 반력 탭까지 거리 mm (가정: 25)")
    parser.add_argument("--mu", type=nonnegative, default=0.2,
                        help="마찰계수 (가정: 0.2, 측정값 아님)")
    parser.add_argument("--pad-normal-force", type=nonnegative, default=20,
                        help="패드 한 개의 법선력 N (가정: 20)")
    parser.add_argument("--pad-radius", type=positive, default=1,
                        help="균일 압력 원형 패드의 반지름 mm (가정: 1)")
    parser.add_argument("--json", action="store_true", help="단위가 명시된 JSON 출력")
    args = parser.parse_args()

    result = {
        "status": "예비 민감도 계산 / 실제 토크·재료·안전계수 미정 / 정격 판정 없음",
        "assumptions": {
            "torques_nm": args.torques,
            "head_across_flats_mm": args.across_flats,
            "solid_output_shaft_diameters_mm": args.shaft_diameters,
            "equal_load_sharing_reaction_tabs": 2,
            "tab_radius_mm": args.tab_radius,
            "friction_coefficient": args.mu,
            "normal_force_per_pad_n": args.pad_normal_force,
            "uniform_pressure_circular_pad_radius_mm": args.pad_radius,
        },
        "head_force": [
            {"torque_nm": t, "across_flats_mm": af,
             "equivalent_tangential_force_n": equivalent_tangential_force(t, af)}
            for t in args.torques for af in args.across_flats
        ],
        "shaft_stress": [
            {"torque_nm": t, "solid_shaft_diameter_mm": d,
             "max_shear_mpa": solid_shaft_shear_mpa(t, d)}
            for t in args.torques for d in args.shaft_diameters
        ],
        "reaction_tabs": [
            {"torque_nm": t, "equal_share_force_per_tab_n": reaction_tab_force(t, args.tab_radius),
             "one_tab_only_force_n": 2 * reaction_tab_force(t, args.tab_radius)}
            for t in args.torques
        ],
        "pad_friction_torque": {
            "single_pad_nm": pad_torque_nm(args.mu, args.pad_normal_force, args.pad_radius),
            "two_equal_pads_nm": 2 * pad_torque_nm(args.mu, args.pad_normal_force, args.pad_radius),
            "limitation": (
                "균일 압력 원형 면접촉의 개산값. 원통·나사산의 실제 접촉에는 직접 적용할 수 없음. "
                "패드 자체 법선축 주위 비틀림이며 볼트 축 주위 체결 토크 정격이 아님."
            ),
        },
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(result["status"])
    print("\n헤드 등가 접선력: F_eq = 2T/AF (턱 법선력·접촉압력과 다름)")
    print("토크 [N·m] | 대변 [mm] | 등가 접선력 [N]")
    for row in result["head_force"]:
        print(f'{row["torque_nm"]:10.2f} | {row["across_flats_mm"]:9.2f} | '
              f'{row["equivalent_tangential_force_n"]:14.2f}')
    print("\n중실 출력축: tau_max = 16T/(pi*d^3), 응력집중·굽힘·피로 제외")
    print("토크 [N·m] | 축 지름 [mm] | 전단응력 [MPa]")
    for row in result["shaft_stress"]:
        print(f'{row["torque_nm"]:10.2f} | {row["solid_shaft_diameter_mm"]:12.2f} | '
              f'{row["max_shear_mpa"]:14.2f}')
    print(f"\n반력 탭 반경 {args.tab_radius:g} mm: 두 탭 균등분담 F = T/(2r)")
    print("토크 [N·m] | 균등분담 탭당 [N] | 한 탭만 접촉 [N]")
    for row in result["reaction_tabs"]:
        print(f'{row["torque_nm"]:10.2f} | {row["equal_share_force_per_tab_n"]:17.2f} | '
              f'{row["one_tab_only_force_n"]:16.2f}')
    pad = result["pad_friction_torque"]
    print(f"\n원형 패드 가정: mu={args.mu:g}, N={args.pad_normal_force:g} N/패드, "
          f"a={args.pad_radius:g} mm")
    print(f'한 패드 T ≈ 2*mu*N*a/3 = {pad["single_pad_nm"]:.6f} N·m; '
          f'같은 패드 두 개의 이상적 합계 = {pad["two_equal_pads_nm"]:.6f} N·m')
    print(pad["limitation"])


if __name__ == "__main__":
    main()
