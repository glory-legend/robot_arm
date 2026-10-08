export function cssColor(name: string, fallback: string) {
  return (
    getComputedStyle(document.documentElement).getPropertyValue(name).trim() ||
    fallback
  );
}
export const palette = () => ({
  blue: cssColor("--finger", "#286ca8"),
  orange: cssColor("--chuck", "#bb591f"),
  ink: cssColor("--ink", "#20313d"),
  surface: cssColor("--canvas", "#e9edef"),
  teal: cssColor("--active", "#185c56"),
});
