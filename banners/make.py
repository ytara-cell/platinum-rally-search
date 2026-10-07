import math, subprocess, sys
CHROME="/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
def wheel():
    n=8; r=200; cx=cy=220; out=[]
    cols=["#C8322B","#FBF3E6","#3B2A22","#FBF3E6"]
    for i in range(n):
        a0=math.radians(i*360/n-90); a1=math.radians((i+1)*360/n-90)
        x0,y0=cx+r*math.cos(a0),cy+r*math.sin(a0); x1,y1=cx+r*math.cos(a1),cy+r*math.sin(a1)
        out.append(f'<path d="M{cx},{cy} L{x0:.1f},{y0:.1f} A{r},{r} 0 0 1 {x1:.1f},{y1:.1f} Z" fill="{cols[i%4]}"/>')
        am=math.radians((i+.5)*360/n-90); tx,ty=cx+130*math.cos(am),cy+130*math.sin(am)
        c="#C8322B" if cols[i%4]=="#FBF3E6" else "#FBF3E6"
        out.append(f'<text x="{tx:.1f}" y="{ty:.1f}" fill="{c}" font-size="40" font-weight="900" font-family="Zen Kaku Gothic New" text-anchor="middle" dominant-baseline="central" transform="rotate({(i+.5)*360/n:.1f} {tx:.1f} {ty:.1f})">¥</text>')
    dots="".join(f'<circle cx="{cx+(r+9)*math.cos(math.radians(k*15)):.1f}" cy="{cy+(r+9)*math.sin(math.radians(k*15)):.1f}" r="4.5" fill="#F6E7CF"/>' for k in range(24))
    return f'''<svg width="440" height="440" viewBox="0 0 440 440">
<circle cx="220" cy="220" r="219" fill="#3B2A22"/>{dots}
<circle cx="220" cy="220" r="202" fill="#3B2A22"/>{''.join(out)}
<circle cx="220" cy="220" r="44" fill="#3B2A22"/><circle cx="220" cy="220" r="33" fill="#C8322B"/>
<text x="220" y="222" fill="#FBF3E6" font-family="Anton" font-size="26" text-anchor="middle" dominant-baseline="central">GO!</text></svg>'''
def page(n):
    return f'''<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Dela+Gothic+One&family=Yusei+Magic&family=Anton&family=Zen+Kaku+Gothic+New:wght@700;900&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1200px;height:630px;overflow:hidden;background:#F6EBDD;position:relative;font-family:'Zen Kaku Gothic New',sans-serif;color:#3B2A22}}
.bg{{position:absolute;inset:0;background:radial-gradient(circle at 20% 15%,#FBF3E6 0,transparent 55%),repeating-linear-gradient(135deg,rgba(200,50,43,.05) 0 14px,transparent 14px 28px)}}
.frame{{position:absolute;inset:18px;border:3px solid #3B2A22;border-radius:6px}}
.leaf{{position:absolute;font-size:34px;color:#C8322B;opacity:.85}}
.tag{{position:absolute;left:70px;top:58px;font-family:'Yusei Magic';font-size:32px;transform:rotate(-6deg);transform-origin:left}}
.tag b{{color:#C8322B;font-weight:400;font-size:40px}}
.tag:after{{content:"";display:block;height:3px;background:#3B2A22;margin-top:4px;width:105%}}
.logo{{position:absolute;left:72px;top:138px;display:flex;align-items:baseline;gap:10px}}
.logo .ja{{font-family:'Dela Gothic One';font-size:40px}}
.logo .ni{{font-family:'Dela Gothic One';font-size:30px;color:#C8322B}}
.logo .try{{font-family:Anton;font-size:52px;color:#C8322B;letter-spacing:1px}}
.logo .sr{{font-family:Anton;font-size:20px;letter-spacing:2px;margin-left:6px}}
.title{{position:absolute;left:66px;top:222px;font-family:'Dela Gothic One';line-height:1.02}}
.title .l1{{font-size:96px;letter-spacing:2px}}
.title .l2{{font-size:96px;letter-spacing:2px;color:#C8322B}}
.gift{{position:absolute;left:70px;top:448px;background:#3B2A22;color:#FBF3E6;font-weight:900;font-size:40px;padding:10px 28px 12px;border-radius:4px;transform:skew(-6deg)}}
.gift em{{font-style:normal;color:#F7C548}}
.note{{position:absolute;left:74px;top:532px;font-size:20px;font-weight:700}}
.wheel{{position:absolute;left:700px;top:132px;filter:drop-shadow(6px 8px 0 rgba(59,42,34,.18))}}
.pointer{{position:absolute;left:894px;top:104px;width:0;height:0;border-left:26px solid transparent;border-right:26px solid transparent;border-top:52px solid #C8322B;filter:drop-shadow(0 3px 0 #3B2A22)}}
.badge{{position:absolute;left:630px;top:44px;width:160px;height:160px;border-radius:50%;background:#C8322B;color:#FBF3E6;display:flex;flex-direction:column;align-items:center;justify-content:center;transform:rotate(-10deg);box-shadow:0 0 0 6px #F6EBDD,0 0 0 9px #C8322B}}
.badge .s{{font-size:22px;font-weight:900;letter-spacing:2px}}
.badge .n{{font-family:'Dela Gothic One';font-size:64px;line-height:1}}
.badge .n small{{font-size:28px;font-family:'Zen Kaku Gothic New';font-weight:900;margin-left:2px}}
</style></head><body><div class="bg"></div><div class="frame"></div>
<div class="leaf" style="left:560px;top:40px;transform:rotate(-20deg)">🍁</div>
<div class="leaf" style="left:600px;top:520px;transform:rotate(25deg);font-size:28px">🍂</div>
<div class="tag">今年の<b>秋</b>はどんな私で出かけよう</div>
<div class="logo"><span class="ja">試着</span><span class="ni">に</span><span class="try">TRY!</span><span class="sr">STAMP RALLY</span></div>
<div class="title"><div class="l1">ルーレット</div><div class="l2">チャレンジ</div></div>
<div class="gift"><em>商品券</em>がもらえる！</div>
<div class="note">スタンプを集めてルーレットに挑戦しよう</div>
<div class="wheel">{wheel()}</div><div class="pointer"></div>
<div class="badge"><span class="s">CHALLENGE</span><span class="n">{n}<small>回目</small></span></div>
</body></html>'''
for n in (1,2):
    open(f"roulette_{n}.html","w").write(page(n))
    subprocess.run([CHROME,"--headless","--no-sandbox","--hide-scrollbars","--disable-gpu","--virtual-time-budget=8000","--window-size=1200,900",f"--screenshot=_full_{n}.png",f"file://{__import__('os').getcwd()}/roulette_{n}.html"],check=True,capture_output=True)
from PIL import Image
for n in (1,2):
    Image.open(f"_full_{n}.png").crop((0,0,1200,630)).save(f"roulette_challenge_{n}.png")
    __import__("os").remove(f"_full_{n}.png")
print("ok")
