"""Subset the showcase fonts into src/fonts/*.woff2 (one file per weight).

Usage: python3 scripts/subset-fonts.py
Sources: github.com/google/fonts (ofl/ibmplexsanskr, ofl/barlowcondensed), SIL OFL 1.1,
downloaded once into ~/.cache/r11-fonts. Keeps ASCII, Latin-1 and every character used in
the page sources; the fonts are inlined into the CSS, so they stay small. Re-run after copy
edits: a character added later falls back to the system font until then.
"""
import pathlib
import urllib.request

from fontTools import subset

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCES = ["r11.html", "src/r11-showcase.ts", "src/compact-kinematics.ts", "src/viewer.ts", "src/timeline.ts"]
# OFL: a subset is a modified version, so it must not carry the Reserved Font Name ("Plex").
# Both families are renamed; CSS refers to "R11 Text" and "R11 Figures".
FONTS = {
    "IBMPlexSansKR-Regular": ("r11-text-400", "R11 Text", "Regular"),
    "IBMPlexSansKR-Medium": ("r11-text-500", "R11 Text", "Medium"),
    "IBMPlexSansKR-Bold": ("r11-text-700", "R11 Text", "Bold"),
    "BarlowCondensed-Medium": ("r11-figures-500", "R11 Figures", "Medium"),
    "BarlowCondensed-SemiBold": ("r11-figures-600", "R11 Figures", "SemiBold"),
}


def rename(font, family: str, style: str) -> None:
    names = {1: family, 2: style, 4: f"{family} {style}", 6: f"{family.replace(' ', '')}-{style}", 16: family, 17: style}
    for record in font["name"].names:
        if record.nameID in names:
            record.string = names[record.nameID]
        elif record.nameID == 3:
            record.string = f"{family} {style} subset"


def fetch(stem: str) -> pathlib.Path:
    cache = pathlib.Path.home() / ".cache" / "r11-fonts"
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{stem}.ttf"
    if not path.exists():
        folder = "ibmplexsanskr" if stem.startswith("IBM") else "barlowcondensed"
        url = f"https://raw.githubusercontent.com/google/fonts/main/ofl/{folder}/{stem}.ttf"
        urllib.request.urlretrieve(url, path)
    return path


def main() -> None:
    chars = {chr(c) for c in range(0x20, 0x7F)} | {chr(c) for c in range(0xA0, 0x100)}
    chars |= set("·×Ø°³²→←↶↷−–—‘’“”…≤≥±µ")
    for name in SOURCES:
        chars |= set((ROOT / name).read_text(encoding="utf-8"))
    text = "".join(sorted(c for c in chars if c.isprintable()))
    out = ROOT / "src" / "fonts"
    out.mkdir(exist_ok=True)
    for stem, (target, family, style) in FONTS.items():
        options = subset.Options()
        options.flavor = "woff2"
        options.layout_features = ["*"]
        font = subset.load_font(str(fetch(stem)), options)
        subsetter = subset.Subsetter(options)
        subsetter.populate(text=text)
        subsetter.subset(font)
        rename(font, family, style)
        path = out / f"{target}.woff2"
        subset.save_font(font, str(path), options)
        print(f"{path.relative_to(ROOT)} {path.stat().st_size // 1024} KB")
    # Every page character must be covered by the Korean text face.
    font = subset.load_font(str(out / "r11-text-400.woff2"), subset.Options())
    cmap = font.getBestCmap()
    page = set()
    for name in SOURCES:
        page |= {c for c in (ROOT / name).read_text(encoding="utf-8") if c.isprintable() and ord(c) > 0x7F}
    missing = sorted(c for c in page if ord(c) not in cmap)
    print("not in R11 Text (system fallback):", "".join(missing) or "none")


if __name__ == "__main__":
    main()
