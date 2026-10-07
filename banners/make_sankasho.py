import os, subprocess
from PIL import Image
CHROME="/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
gift='''<svg width="420" height="420" viewBox="0 0 420 420">
<ellipse cx="210" cy="392" rx="170" ry="16" fill="rgba(59,42,34,.15)"/>
<rect x="60" y="190" width="300" height="190" rx="8" fill="#FBF3E6" stroke="#3B2A22" stroke-width="8"/>
<rect x="40" y="140" width="340" height="62" rx="8" fill="#C8322B" stroke="#3B2A22" stroke-width="8"/>
<rect x="182" y="140" width="56" height="240" fill="#3B2A22"/>
<rect x="192" y="140" width="36" height="240" fill="#F7C548"/>
<path d="M210 140 C150 60 70 80 110 132 C130 150 190 146 210 140Z" fill="#C8322B" stroke="#3B2A22" stroke-width="8" stroke-linejoin="round"/>
<path d="M210 140 C270 60 350 80 310 132 C290 150 230 146 210 140Z" fill="#C8322B" stroke="#3B2A22" stroke-width="8" stroke-linejoin="round"/>
<circle cx="210" cy="138" r="18" fill="#F7C548" stroke="#3B2A22" stroke-width="8"/>
<g fill="#C8322B" opacity=".9"><path d="M100 250 l6 14 15 2 -11 10 3 15 -13 -8 -13 8 3 -15 -11 -10 15 -2z"/><path d="M300 300 l5 11 12 2 -9 8 2 12 -10 -6 -10 6 2 -12 -9 -8 12 -2z"/></g>
</svg>'''
html=f'''<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Dela+Gothic+One&family=Yusei+Magic&family=Anton&family=Zen+Kaku+Gothic+New:wght@700;900&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1200px;height:630px;overflow:hidden;background:#F6EBDD;position:relative;font-family:'Zen Kaku Gothic New',sans-serif;color:#3B2A22}}
.bg{{position:absolute;inset:0;background:radial-gradient(circle at 20% 15%,#FBF3E6 0,transparent 55%),repeating-linear-gradient(135deg,rgba(200,50,43,.05) 0 14px,transparent 14px 28px)}}
.frame{{position:absolute;inset:18px;border:3px solid #3B2A22;border-radius:6px}}
.leaf{{position:absolute;font-size:34px;opacity:.85}}
.tag{{position:absolute;left:70px;top:58px;font-family:'Yusei Magic';font-size:32px;transform:rotate(-6deg);transform-origin:left}}
.tag b{{color:#C8322B;font-weight:400;font-size:40px}}
.tag:after{{content:"";display:block;height:3px;background:#3B2A22;margin-top:4px;width:105%}}
.logo{{position:absolute;left:72px;top:138px;display:flex;align-items:baseline;gap:10px}}
.logo .ja{{font-family:'Dela Gothic One';font-size:40px}}
.logo .ni{{font-family:'Dela Gothic One';font-size:30px;color:#C8322B}}
.logo .try{{font-family:Anton;font-size:52px;color:#C8322B;letter-spacing:1px}}
.logo .sr{{font-family:Anton;font-size:20px;letter-spacing:2px;margin-left:6px}}
.zan{{position:absolute;left:62px;top:218px;font-family:'Dela Gothic One';font-size:118px;letter-spacing:4px;line-height:1}}
.zan .sweat{{display:inline-block;font-size:60px;color:#7FA7C9;transform:translateY(-50px) rotate(15deg)}}
.sub{{position:absolute;left:72px;top:356px;font-size:30px;font-weight:900}}
.gift{{position:absolute;left:70px;top:418px;background:#C8322B;color:#FBF3E6;font-weight:900;font-size:46px;padding:10px 30px 12px;border-radius:4px;transform:skew(-6deg);box-shadow:6px 6px 0 #3B2A22}}
.gift em{{font-style:normal;color:#F7C548}}
.note{{position:absolute;left:74px;top:534px;font-size:20px;font-weight:700}}
.box{{position:absolute;left:720px;top:150px}}
.badge{{position:absolute;left:650px;top:52px;width:170px;height:170px;border-radius:50%;background:#3B2A22;color:#FBF3E6;display:flex;flex-direction:column;align-items:center;justify-content:center;transform:rotate(-10deg);box-shadow:0 0 0 6px #F6EBDD,0 0 0 9px #3B2A22}}
.badge .s{{font-family:Anton;font-size:22px;letter-spacing:2px;color:#F7C548}}
.badge .n{{font-family:'Dela Gothic One';font-size:46px;line-height:1.1}}
.thanks{{position:absolute;left:880px;top:84px;font-family:Anton;font-size:40px;color:#C8322B;transform:rotate(6deg);letter-spacing:1px}}
</style></head><body><div class="bg"></div><div class="frame"></div>
<div class="leaf" style="left:560px;top:40px;transform:rotate(-20deg)">🍁</div>
<div class="leaf" style="left:610px;top:520px;transform:rotate(25deg);font-size:28px">🍂</div>
<div class="leaf" style="left:1100px;top:470px;transform:rotate(-10deg);font-size:30px">🍁</div>
<div class="tag">今年の<b>秋</b>はどんな私で出かけよう</div>
<div class="logo"><span class="ja">試着</span><span class="ni">に</span><span class="try">TRY!</span><span class="sr">STAMP RALLY</span></div>
<div class="zan">ざんねん…<span class="sweat">💧</span></div>
<div class="sub">今回はハズレでしたが…</div>
<div class="gift"><em>参加賞</em>をプレゼント！</div>
<div class="note">ご参加いただきありがとうございました</div>
<div class="box">{gift}</div>
<div class="badge"><span class="s">THANK YOU</span><span class="n">参加賞</span></div>
</body></html>'''
open("sankasho.html","w").write(html)
subprocess.run([CHROME,"--headless","--no-sandbox","--hide-scrollbars","--disable-gpu","--virtual-time-budget=8000","--window-size=1200,900","--screenshot=_full.png",f"file://{os.getcwd()}/sankasho.html"],check=True,capture_output=True)
Image.open("_full.png").crop((0,0,1200,630)).save("roulette_sankasho.png"); os.remove("_full.png")
print("ok")
