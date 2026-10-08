"""座席エリア用ピン画像の SVG を生成（既存マーカーと同じ 320x320・赤/白/ベージュの線画スタイル）

使い方: python3 make_seat_pins.py <出力ディレクトリ>
PNG 化はブラウザで SVG を透過背景のまま書き出す（Inter フォントを使用）
"""
import sys, pathlib
OUT = pathlib.Path(sys.argv[1])
RED, BEIGE, WHITE, GRAY = "#A6192E", "#DFD9D4", "#FFFFFF", "#44403F"
SW = 14  # 既存アイコンと同程度の線幅

def seat(dx=0, dy=0, s=1.0):
    """スタジアムのイス（背もたれ＋座面＋左右の脚）"""
    return f'''<g transform="translate({dx},{dy}) scale({s})" stroke="{RED}" stroke-width="{SW}" stroke-linejoin="round" stroke-linecap="round">
  <path d="M86 196 L86 268 M234 196 L234 268 M86 240 H234" fill="none"/>
  <rect x="96" y="28" width="128" height="148" rx="30" fill="{WHITE}"/>
  <rect x="114" y="46" width="92" height="112" rx="16" fill="{BEIGE}" stroke="none"/>
  <rect x="60" y="164" width="200" height="46" rx="20" fill="{WHITE}"/>
  <rect x="76" y="176" width="150" height="14" rx="7" fill="{BEIGE}" stroke="none"/>
</g>'''

def sofa():
    return f'''<g stroke="{RED}" stroke-width="{SW}" stroke-linejoin="round" stroke-linecap="round">
  <rect x="62" y="70" width="196" height="110" rx="30" fill="{WHITE}"/>
  <rect x="84" y="90" width="152" height="70" rx="18" fill="{BEIGE}" stroke="none"/>
  <rect x="30" y="140" width="58" height="110" rx="26" fill="{WHITE}"/>
  <rect x="232" y="140" width="58" height="110" rx="26" fill="{WHITE}"/>
  <rect x="84" y="170" width="152" height="80" rx="16" fill="{WHITE}"/>
  <rect x="98" y="184" width="124" height="20" rx="10" fill="{BEIGE}" stroke="none"/>
  <path d="M70 252 v26 M250 252 v26" fill="none"/>
</g>'''

def badge(label, color=RED, size=None):
    n = len(label)
    fs = size or (118 if n == 1 else 84 if n == 2 else 64)
    return f'''<circle cx="236" cy="236" r="74" fill="{color}" stroke="{WHITE}" stroke-width="12"/>
<text x="236" y="236" dy="0.36em" text-anchor="middle" font-family="Inter" font-weight="900" font-size="{fs}" fill="{WHITE}" letter-spacing="-2">{label}</text>'''

def star_badge(color=RED):
    import math
    pts = []
    for i in range(10):
        r = 48 if i % 2 == 0 else 21
        a = math.radians(-90 + 36 * i)
        pts.append(f"{236 + r*math.cos(a):.1f},{240 + r*math.sin(a):.1f}")
    return f'''<circle cx="236" cy="236" r="74" fill="{color}" stroke="{WHITE}" stroke-width="12"/>
<polygon points="{' '.join(pts)}" fill="{WHITE}" stroke="{WHITE}" stroke-width="6" stroke-linejoin="round"/>'''

def wheelchair_badge(color="#1F5FAD"):
    # 車いすマーク風（頭・体・車輪）
    return f'''<circle cx="236" cy="236" r="74" fill="{color}" stroke="{WHITE}" stroke-width="12"/>
<g fill="none" stroke="{WHITE}" stroke-width="11" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="226" cy="186" r="11" fill="{WHITE}" stroke="none"/>
  <path d="M222 204 v42 h36 l14 34"/>
  <path d="M222 224 h26"/>
  <path d="M206 222 a36 36 0 1 0 50 44"/>
</g>'''

def svg(*parts):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="320" height="320" viewBox="0 0 320 320">{"".join(parts)}</svg>'

pins = {
    "seat": svg(seat(0, 10)),
    **{f"seat_cat{i}": svg(seat(-28, -6, 0.92), badge(str(i))) for i in range(1, 7)},
    "seat_west": svg(seat(-28, -6, 0.92), badge("W")),
    "seat_east": svg(seat(-28, -6, 0.92), badge("E")),
    "seat_home": svg(seat(-28, -6, 0.92), badge("H")),
    "seat_visitor": svg(seat(-28, -6, 0.92), badge("V", GRAY)),
    "seat_premium": svg(seat(-28, -6, 0.92), star_badge()),
    "seat_sofa": svg(sofa()),
    "seat_wheelchair": svg(seat(-28, -6, 0.92), wheelchair_badge()),
}
OUT.mkdir(parents=True, exist_ok=True)
for name, s in pins.items():
    (OUT / f"{name}.svg").write_text(s, encoding="utf-8")
print(len(pins))
