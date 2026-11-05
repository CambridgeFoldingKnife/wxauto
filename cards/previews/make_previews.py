# -*- coding: utf-8 -*-
"""同一张卡，四种内容策略 → HTML → PNG（0 成本，不调任何 API）

V1 数据说服型：三个阈值数字当主角
V2 场景问答型：家长口吻的三问三答
V3 图解标注型：图为主，文字只做标注
V4 对比反差型：会量 ≠ 会判

用法: python make_previews.py
"""
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "previews"
CHROMES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

CSS = """
/* ---------- V1 数据说服 ---------- */
.numrow{display:flex;gap:18px;margin-top:22px;flex:1 1 auto}
.nblock{flex:1;background:#f8fbfe;border:2px solid #e8f1f9;border-radius:22px;padding:26px 22px;
  display:flex;flex-direction:column;justify-content:center}
.nblock .big{font-family:Georgia,Arial,sans-serif;font-size:100px;font-weight:800;color:#32afaf;line-height:.95;letter-spacing:-3px}
.nblock .nt{font-size:29px;font-weight:800;color:#16375f;margin:12px 0 10px}
.nblock .nd{font-size:22px;color:#47607d;line-height:1.6}
.note-line{margin-top:14px;font-size:19px;color:#47607d;line-height:1.5}
.quote{margin-top:18px;padding:18px 24px;background:#fffaea;border-left:8px solid #32afaf;
  border-radius:14px;font-size:25px;font-weight:800;color:#16375f;line-height:1.5}

/* ---------- V2 场景问答 ---------- */
.qa{display:flex;flex-direction:column;gap:16px;flex:1 1 auto;justify-content:space-between;margin-top:8px}
.qarow{display:flex;gap:18px;align-items:center;flex:1 1 auto}
.q{flex:0 0 36%;background:#eef8ff;border-radius:18px;padding:20px 20px;
  font-size:23px;font-weight:800;color:#2c5b93;line-height:1.5;display:flex;align-items:center}
.a{flex:1;background:#fff;border:2px solid #e8f1f9;border-radius:18px;padding:20px 22px;
  font-size:22px;color:#1b2a3d;line-height:1.65}
.a em{font-style:normal;color:#32afaf;font-weight:800}

/* ---------- V3 图解标注 ---------- */
.figureWrap{flex:0 0 52%;display:flex;align-items:center;justify-content:center;position:relative}
.imgBox{position:relative;height:100%;width:fit-content;margin:0 auto}
.imgBox img{height:100%;width:auto;max-width:100%;object-fit:contain;display:block}
.col-text{justify-content:center}
.hot{position:absolute;transform:translate(-50%,-50%);width:44px;height:44px;border-radius:50%;background:#16375f;color:#fff;
  display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:800;font-family:Arial;
  box-shadow:0 0 0 6px rgba(22,55,95,.12)}
.legend{flex:1;display:flex;flex-direction:column;justify-content:center;gap:20px;padding-left:10px}
.lg{display:flex;gap:16px;align-items:flex-start}
.lg .n{flex:0 0 40px;height:40px;border-radius:50%;background:#32afaf;color:#fff;
  display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:800;font-family:Arial}
.lg .tx{font-size:22px;color:#1b2a3d;line-height:1.6}
.lg .tx b{display:block;font-size:25px;color:#16375f;margin-bottom:2px}

/* ---------- V4 对比反差 ---------- */
.versus{display:flex;align-items:stretch;flex:1 1 auto;gap:0;margin-top:10px}
.vcol{flex:1;border-radius:22px;padding:26px 24px;display:flex;flex-direction:column;justify-content:center}
.vcol.left{background:#fff2f2;border:2px solid #ffd8d8}
.vcol.right{background:#eefaf6;border:2px solid #c6eee1}
.vs{flex:0 0 96px;display:flex;align-items:center;justify-content:center;
  font-size:58px;font-weight:800;color:#c3ccd8;font-family:Arial}
.vh{font-size:25px;font-weight:800;margin-bottom:16px;letter-spacing:1px}
.vcol.left .vh{color:#b52d2d}
.vcol.right .vh{color:#127a5e}
.vlist{display:flex;flex-direction:column;gap:16px;flex:0 0 auto}
.vi{font-size:21px;line-height:1.6;color:#1b2a3d;padding-left:34px;position:relative}
.vi::before{position:absolute;left:0;top:1px;width:24px;height:24px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;font-size:15px;color:#fff}
.vcol.left .vi::before{content:"×";background:#e05252}
.vcol.right .vi::before{content:"✓";background:#2fa87f}
"""

FRAME = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<link rel="stylesheet" href="../../_base.css">
<link rel="stylesheet" href="preview.css">
<title>{name}</title></head><body>
<div class="card">
  <header class="top">
    <div class="pill pill-solid"><span class="star">★</span>治疗师必看</div>
    <div class="top-right">
      <div class="pill pill-line">脊柱侧弯评估 ｜ Cobb角解读</div>
      <div class="pageno">02</div>
    </div>
  </header>
  <div class="side-left">BETTER<br>FUNCTION<br>BRIGHTER<br>TOMORROW</div>
  <div class="side-right">早评估<br>早干预<br>助力更好功能</div>
  <div class="head">
    <h1 class="title" style="font-size:{size}px">{title}</h1>
    <div class="subbar">{sub}</div>
  </div>
  <div class="body">
{body}
  </div>
  <div class="keybar">
    <div class="krow">
      <svg class="kico" width="42" height="64" viewBox="0 0 42 64">
        <rect x="15" y="0" width="16" height="8" rx="4" fill="#fff"/><rect x="12" y="9" width="22" height="8" rx="4" fill="#fff"/>
        <rect x="15" y="18" width="16" height="8" rx="4" fill="#fff"/><rect x="12" y="27" width="22" height="8" rx="4" fill="#fff"/>
        <rect x="15" y="36" width="16" height="8" rx="4" fill="#fff"/><rect x="12" y="45" width="22" height="8" rx="4" fill="#fff"/>
      </svg>
      <div class="ktext" style="font-size:{ksize}px"><span class="k1">核心：</span>{key}</div>
      <div class="kside">以专业<br>守护每一份挺拔</div>
    </div>
    <div class="kfoot"><span class="dash"></span>科学评估 · 个体化干预 · 改善功能 · 提升生活质量<span class="dash"></span></div>
  </div>
  <div class="foot">REHABILITATION &nbsp; MAKES &nbsp; A &nbsp; BETTER &nbsp; TOMORROW</div>
  <svg class="wm-tile" viewBox="0 0 1086 1448" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <defs><pattern id="wmP" width="540" height="400" patternUnits="userSpaceOnUse" patternTransform="rotate(-24)">
      <text x="0" y="200" font-family="微软雅黑" font-size="32" font-weight="700" fill="#16375f" fill-opacity="0.05">健衡学园 · 康复科普</text>
    </pattern></defs><rect width="1086" height="1448" fill="url(#wmP)"/>
  </svg>
</div></body></html>
"""

VARIANTS = [
    dict(
        name="v1-数据说服",
        size=62,
        title="三个数字，<em>决定侧弯怎么管</em>",
        sub="10° · 25° · 40° ｜ 每个数字对应一个动作",
        key="每个数字，都对应一个动作",
        ksize=34,
        body="""    <section class="panel">
      <div class="panel-head"><i></i>三个门槛，分别意味着什么</div>
      <div class="panel-sub">同一个角度，落在不同区间，处理方式完全不同</div>
      <div class="numrow">
        <div class="nblock"><div class="big">10°</div><div class="nt">诊断起点</div>
          <div class="nd">站立位 X 线测量 ≥10°，才进入「脊柱侧弯」的诊断讨论；低于 10° 更接近姿势异常。</div></div>
        <div class="nblock"><div class="big">25°</div><div class="nt">干预分水岭</div>
          <div class="nd">≥25° 且仍在生长期，通常需要支具配合强化训练；单靠观察往往不够。</div></div>
        <div class="nblock"><div class="big">40°</div><div class="nt">手术评估线</div>
          <div class="nd">约 ≥40~50° 且继续进展，需要外科评估；保守治疗转向控制进展。</div></div>
      </div>
      <div class="quote">真正要问的不是「多少度」，而是「在这个度数上，我该做什么」。</div>
      <div class="note-line">注：以上为国际常用参考阈值；具体方案需结合骨龄、进展速度与个体情况综合评估。</div>
    </section>""",
    ),
    dict(
        name="v2-场景问答",
        size=64,
        title="「孩子 15°，<em>要不要紧？」</em>",
        sub="家长最常问的三句话，一次说清",
        key="同一个度数，意义可能完全不同",
        ksize=34,
        body="""    <section class="panel" style="justify-content:center">
      <div class="qa">
        <div class="qarow">
          <div class="q">「才 15°，是不是不用担心？」</div>
          <div class="a">15° 属于轻中度之间。<em>要不要紧看骨龄和进展速度</em>——同样的 15°，12 岁和 16 岁意义完全不同。还在快速生长期，就需要密切随访。</div>
        </div>
        <div class="qarow">
          <div class="q">「戴支具是不是一辈子摘不掉？」</div>
          <div class="a">不是。支具的作用是<em>在生长期内控制进展</em>，通常按剩余生长潜力决定佩戴时长，骨骼成熟后多数可以逐步停用。</div>
        </div>
        <div class="qarow">
          <div class="q">「练了三个月，度数没变，是不是白练？」</div>
          <div class="a">不是。<em>度数没变本身就是结果</em>——生长期内角度没有增加，说明控制住了。训练的目标不只是降度数，还有体态、耐力和功能。</div>
        </div>
      </div>
    </section>""",
    ),
    dict(
        name="v3-图解标注",
        size=60,
        title="一条线，<em>量出侧弯多少度</em>",
        sub="图解 Cobb角 的四个关键位置",
        key="端椎选错，角度就偏",
        ksize=34,
        body="""    <section class="panel">
      <div class="split">
        <div class="col-text">
          <div class="panel-head"><i></i>图上这四个位置</div>
          <div class="legend">
            <div class="lg"><div class="n">1</div><div class="tx"><b>上端椎终板</b>弯曲上端倾斜最大的椎体</div></div>
            <div class="lg"><div class="n">2</div><div class="tx"><b>下端椎终板</b>弯曲下端倾斜最大的椎体</div></div>
            <div class="lg"><div class="n">3</div><div class="tx"><b>两条垂线夹角</b>这个角就是 Cobb角 的度数</div></div>
          </div>
        </div>
        <div class="figureWrap">
          <div class="imgBox">
            <img src="../../assets/xray-spine.png" alt="">
          </div>
          <div class="hot" style="left:47%;top:34%">1</div>
          <div class="hot" style="left:47%;top:47%">2</div>
          <div class="hot" style="left:60%;top:40%">3</div>
        </div>
      </div>
    </section>""",
    ),
    dict(
        name="v4-对比反差",
        size=62,
        title="会量角度，<em>不等于会判断</em>",
        sub="同一个 25°，两种完全不同的处理方式",
        key="角度是入口，不是结论",
        ksize=34,
        body="""    <section class="panel">
      <div class="versus">
        <div class="vcol left">
          <div class="vh">只看 Cobb角</div>
          <div class="vlist">
            <div class="vi">数字变大就紧张，变小就放松</div>
            <div class="vi">不问骨龄，也不看进展速度</div>
            <div class="vi">把一次测量当成最终结论</div>
            <div class="vi">不评估体表、旋转与功能</div>
          </div>
        </div>
        <div class="vs">≠</div>
        <div class="vcol right">
          <div class="vh">综合判断</div>
          <div class="vlist">
            <div class="vi">先看角度，再看它在谁身上</div>
            <div class="vi">结合 Risser 征与剩余生长潜力</div>
            <div class="vi">看趋势：半年内变化多少</div>
            <div class="vi">同步评估体表、旋转与日常功能</div>
          </div>
        </div>
      </div>
    </section>""",
    ),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "preview.css").write_text(CSS, encoding="utf-8")
    chrome = next((c for c in CHROMES if Path(c).exists()), None)
    if not chrome:
        raise SystemExit("找不到 Chrome/Edge")

    for v in VARIANTS:
        html = FRAME.format(**v)
        hp = OUT / (v["name"] + ".html")
        hp.write_text(html, encoding="utf-8")
        png = OUT / (v["name"] + ".png")
        subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
             "--force-device-scale-factor=1", "--window-size=1086,1448",
             "--default-background-color=FFFFFFFF", "--screenshot=" + str(png),
             "file:///" + hp.as_posix().lstrip("/")],
            capture_output=True,
        )
        print("✓", png.relative_to(ROOT))


if __name__ == "__main__":
    main()
