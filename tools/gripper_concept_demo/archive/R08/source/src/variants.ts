export type Variant = "a" | "b";
export const VARIANTS = {
  a: {
    title: "A · 내부 척 + 집게 수납",
    short: "분리 수납형",
    structure: "몸통 집게 2개 + 내부 6조 척",
    motion: "별도 척이 헤드를 잡으면 주집게를 약 56mm 수납합니다.",
    tradeoff:
      "파지와 체결을 분리해 역할이 명확합니다. 뒤쪽 수납 공간과 별도 인계 기구가 필요합니다.",
  },
  b: {
    title: "B · 통합 2조 · 구조 축소",
    short: "파지·체결 통합형",
    structure: "2단 접촉면을 가진 회전 집게 2개",
    motion:
      "같은 2조 카세트의 헤드 접촉면을 잠그고 얇은 몸통 팁만 24mm 수납합니다.",
    tradeoff:
      "별도 6조 척을 없앤 설계안입니다. 한 캠으로 접촉면 잠금과 팁 수납을 연계하며, 구동력과 잠금 신뢰성은 추가 검증이 필요합니다.",
  },
} as const;
