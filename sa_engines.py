# -*- coding: utf-8 -*-
"""SA Motion Studio — محركات الرندر: Remotion · HyperFrames · دمج.

* HyperFrames هنا = تركيبة HTML حتمية: عناصر بـ data-start / data-duration + مخطط زمني (window.__timelines أو drawFrame(t)).
  يُرندر إطاراً بإطار عبر Chromium ثم ffmpeg (hf_render.cjs). لا يحتاج إنترنت، ولا يغيّر شيئاً في مسار Remotion.
* الدمج: «طبقات» (HyperFrames خلفية + Remotion شفاف فوقها، أو العكس) أو «تتابع» (كل مقطع زمني بمحرك).
* السكربت → تصميم: بناء حتمي بقواعد (بدون أي نموذج ذكاء اصطناعي): تقسيم الجمل، اختيار نوع المشهد، الكلمات المفتاحية.
"""
import os, re, json, subprocess, shutil, html as _html

ENGINES = ("remotion", "hyperframes", "merge")
MARK = re.compile(r"^[ \t]*(?://|<!--)\s*@@ENGINE\s+(remotion|hyperframes)\s*(?:-->)?[ \t]*$", re.M)


# ----------------------------------------------------------------------------- code split
def split_code(code, engine, hf_code=None):
    """-> (engine, remotion_code, hf_html). يدعم حقلاً منفصلاً hf_code أو فواصل //@@ENGINE داخل نص واحد."""
    engine = engine if engine in ENGINES else "remotion"
    code = code or ""
    parts, ms = {}, list(MARK.finditer(code))
    if ms:
        for i, m in enumerate(ms):
            end = ms[i + 1].start() if i + 1 < len(ms) else len(code)
            parts[m.group(1)] = code[m.end():end].strip("\n")
    rem = parts.get("remotion")
    hf = hf_code if (hf_code or "").strip() else parts.get("hyperframes")
    if rem is None:
        rem = "" if (engine == "hyperframes" or looks_html(code)) else code
    if hf is None and looks_html(code):
        hf = code
    return engine, rem, hf or ""


def looks_html(code):
    return bool(re.match(r"\s*(<!doctype|<html|<div|<body|<style|<svg|<section|<main)", code or "", re.I))


# ----------------------------------------------------------------------------- HyperFrames runtime
RUNTIME_JS = r"""
(function(){
  var clamp=function(x,a,b){a=a==null?0:a;b=b==null?1:b;return Math.min(b,Math.max(a,x))};
  var lerp=function(a,b,t){return a+(b-a)*t};
  var E={lin:function(t){return t},out:function(t){return 1-Math.pow(1-t,3)},expo:function(t){return t>=1?1:1-Math.pow(2,-10*t)},
    inOut:function(t){return t<.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2},
    back:function(t){var c=1.70158,d=c+1;return 1+d*Math.pow(t-1,3)+c*Math.pow(t-1,2)},
    spring:function(t){return t>=1?1:1-Math.exp(-6*t)*Math.cos(t*9)},in:function(t){return t*t*t}};
  var SA=window.SA={clamp:clamp,lerp:lerp,ease:E,t:0,fps:30,total:300,props:window.SA_PROPS||{},
    // تقدّم 0..1 بين زمنين مع منحنى: SA.p(t, a, b, 'expo')
    p:function(t,a,b,e){var x=clamp((t-a)/Math.max(1e-6,b-a));return (E[e||'out']||E.out)(x)},
    // «ينبثق» عنصر بمبالغة بسيطة: يعيد scale/opacity
    pop:function(t,a,d){var x=SA.p(t,a,a+(d||.45),'back');return {s:lerp(.6,1,x),o:clamp((t-a)/.18)}},
    rand:function(seed){var x=Math.sin((seed||1)*12.9898)*43758.5453;return x-Math.floor(x)},
    css:function(el,o){if(!el)return;for(var k in o){el.style[k]=o[k]}},
    // نص كلمة بكلمة: الكلمة تُضاء لحظة نطقها بالضبط
    words:function(){var w=(SA.props.words||[]);return w.length?w:[]},
    fit:function(root,dw,dh){var W=innerWidth,H=innerHeight,land=W>H*1.05,s=land?Math.min(W/dw,H/dh):Math.max(W/dw,H/dh);
      if(land){try{document.body.style.background=getComputedStyle(root).backgroundColor}catch(e){}}root.style.transformOrigin='0 0';
      root.style.position='absolute';root.style.left=((W-dw*s)/2)+'px';root.style.top=((H-dh*s)/2)+'px';root.style.transform='scale('+s+')'}};
  var clips=[],vids=[];
  function num(v,d){var n=parseFloat(v);return isFinite(n)?n:d}
  function collect(){
    clips=[].slice.call(document.querySelectorAll('[data-start]')).map(function(el){
      var s=num(el.getAttribute('data-start'),0),d=el.getAttribute('data-duration');
      return {el:el,s:s,d:d==null?Infinity:num(d,Infinity),track:num(el.getAttribute('data-track-index'),0)}});
    clips.forEach(function(c){if(!c.el.style.zIndex&&c.track)c.el.style.zIndex=String(c.track)});
    vids=[].slice.call(document.querySelectorAll('video[data-start]'));
  }
  function seekVideo(v,t){return new Promise(function(ok){
    var s=num(v.getAttribute('data-start'),0),off=num(v.getAttribute('data-media-start'),0);
    var tt=Math.max(0,t-s)+off;if(v.duration&&v.loop)tt=tt%v.duration;
    if(Math.abs(v.currentTime-tt)<0.001){ok();return}
    var done=false,f=function(){if(!done){done=true;v.removeEventListener('seeked',f);ok()}};
    v.addEventListener('seeked',f);v.muted=true;try{v.pause()}catch(e){};v.currentTime=tt;setTimeout(f,1500)})}
  function raf2(){return new Promise(function(r){requestAnimationFrame(function(){requestAnimationFrame(r)})})}
  window.__sa={
    ready:function(P){return new Promise(function(ok){
      SA.fps=P.fps;SA.total=P.total;SA.props=Object.assign({},SA.props,P.props||{});
      collect();
      var wait=vids.map(function(v){return new Promise(function(r){if(v.readyState>=1)r();else{v.addEventListener('loadedmetadata',r);setTimeout(r,4000)}})});
      Promise.all(wait).then(function(){return window.SA_SETUP?window.SA_SETUP(SA):null}).then(function(){ok(true)})})},
    duration:function(){return SA.total/SA.fps},
    seek:function(t){
      SA.t=t;
      clips.forEach(function(c){var r=t-c.s,on=r>=-1e-6&&r<c.d-1e-6;c.el.style.visibility=on?'visible':'hidden';
        if(on)c.el.style.setProperty('--t',r.toFixed(4))});
      var tl=window.__timelines;
      if(tl){Object.keys(tl).forEach(function(k){var T=tl[k];if(!T)return;var el=document.querySelector('[data-composition-id="'+k+'"]');
        var off=el?num(el.getAttribute('data-start'),0):0;try{if(T.pause)T.pause();if(T.time)T.time(Math.max(0,t-off),false);else if(T.seek)T.seek(Math.max(0,t-off))}catch(e){}})}
      if(typeof window.drawFrame==='function')window.drawFrame(t,SA);
      return Promise.all(vids.map(function(v){return seekVideo(v,t)})).then(raf2)}
  };
})();
"""

FONT_STACK = "'Cairo','Noto Sans Arabic','Noto Naskh Arabic','IBM Plex Sans Arabic','Noto Color Emoji',sans-serif"


FONT_EXT = (".ttf", ".otf", ".woff", ".woff2")


def fonts_css(fonts_dir):
    """كل خط في مجلد fonts/ يصبح متاحاً باسم ملفه؛ وأول خط يُقدَّم في سلسلة الخطوط. (ميزة «مجلد الخطوط»)"""
    try:
        files = sorted(f for f in os.listdir(fonts_dir) if f.lower().endswith(FONT_EXT))
    except Exception:
        return "", ""
    css, fam = [], []
    for f in files:
        name = re.sub(r"[^A-Za-z0-9_\- ]", "", os.path.splitext(f)[0]) or "SAFont"
        fam.append(name)
        css.append("@font-face{font-family:'%s';src:url('/__fonts/%s');font-display:block}" % (name, f.replace("'", "")))
    return "".join(css), ", ".join("'%s'" % n for n in fam)


def prepare_html(html, props, w, h, alpha=False, fonts_dir=None):
    """يجعل أي HTML تركيبة قابلة للرندر: يضيف الوقت الحتمي + خصائص الصوت/التوقيت + أساسيات CSS."""
    html = html or ""
    props_js = json.dumps(props or {}, ensure_ascii=False).replace("</", "<\\/")
    fcss, ffam = fonts_css(fonts_dir) if fonts_dir else ("", "")
    stack = "'SADigits', " + (ffam + ", " if ffam else "") + FONT_STACK
    fcss = ("@font-face{font-family:'SADigits';src:local('Cairo'),local('Inter'),local('Segoe UI'),local('Arial'),local('Helvetica Neue'),local('Helvetica'),"
            "local('DejaVu Sans'),local('Liberation Sans');unicode-range:U+0030-0039,U+0025,U+002B,U+002E}") + fcss
    boot = (f"<style id=\"__sa_base\">{fcss}html,body{{margin:0;padding:0;width:{w}px;height:{h}px;overflow:hidden;"
            f"background:{'transparent' if alpha else '#000'};font-family:{stack}}}*{{box-sizing:border-box}}</style>"
            f"<script id=\"__sa_props\">window.SA_PROPS={props_js};</script><script id=\"__sa_rt\">{RUNTIME_JS}</script>")
    # gsap من CDN → نسخة محلية إن وُجدت (الخادم يقدّمها من node_modules)، بلا إنترنت
    html = re.sub(r"https?://[^\"']*gsap[^\"']*\.js", "/__vendor/gsap.min.js", html)
    if not re.search(r"<html", html, re.I):
        html = ("<!doctype html><html lang=\"ar\" dir=\"rtl\"><head><meta charset=\"utf-8\"></head><body>" + html + "</body></html>")
    if re.search(r"<head[^>]*>", html, re.I):
        html = re.sub(r"(<head[^>]*>)", lambda m: m.group(1) + boot, html, count=1, flags=re.I)
    else:
        html = re.sub(r"(<html[^>]*>)", lambda m: m.group(1) + "<head><meta charset=\"utf-8\">" + boot + "</head>", html, count=1, flags=re.I)
    if not re.search(r"<meta[^>]+charset", html, re.I):
        html = html.replace("<head>", "<head><meta charset=\"utf-8\">", 1)
    return html


def check_html(html):
    """فحص سريع قبل الرندر: رسائل عربية واضحة بدل فشل صامت."""
    errs = []
    if not (html or "").strip():
        return ["كود HyperFrames فارغ"]
    if not (re.search(r"data-start\s*=", html) or re.search(r"drawFrame\s*[=(]", html) or "__timelines" in html):
        errs.append("لا توجد حركة: استخدم data-start/data-duration على العناصر، أو عرّف window.drawFrame = (t) => {...}، أو سجّل مخططاً زمنياً في window.__timelines.")
    if re.search(r"\bsetTimeout\b|\bsetInterval\b|requestAnimationFrame\s*\(", html) and "drawFrame" not in html:
        errs.append("تنبيه: setTimeout/setInterval/requestAnimationFrame غير حتمية — اجعل كل شيء دالة في الزمن t (drawFrame).")
    if re.search(r"Math\.random\s*\(", html):
        errs.append("تنبيه: Math.random() يغيّر الشكل بين الإطارات — استخدم SA.rand(seed) أو قيماً ثابتة.")
    return errs


# ----------------------------------------------------------------------------- deterministic script analysis
STOP = set("""بعدين وبعدين بعدها وبعدها تخيل تخيلوا تعرف تعرفوا عارف عارفين هل يعني فعلا فعلاً الخلاصه الخلاصة خلاصه خلاصة النتيجه النتيجة والنتيجه والنتيجة اللي دلوقتي كمان تاني اكتر أكتر كتير حاجه حاجة في من على الى إلى عن مع هو هي هم انت انا احنا ده دي دول ده كده كدا ايه إيه ليه لما لو او أو ثم بعد قبل كل بس برضه
دا اللي الي ان أن إن كان كانت يكون تكون هذا هذه ذلك التي الذي هناك عند فيه فيها منه منها لكن علشان عشان زي مثل the a an of to is are in on and or for with that this it as at by be""".split())
EMOJI = [("قلب", "❤️"), ("دم", "🩸"), ("مخ", "🧠"), ("عقل", "🧠"), ("عصب", "🧠"), ("رئ", "🫁"), ("نفس", "🫁"), ("عين", "👁️"), ("سمع", "👂"), ("اذن", "👂"),
         ("معده", "🍽️"), ("معدة", "🍽️"), ("اكل", "🍎"), ("ماء", "💧"), ("مياه", "💧"), ("نوم", "😴"), ("حلم", "💭"), ("وقت", "⏳"), ("زمن", "⏳"),
         ("ضوء", "💡"), ("نور", "💡"), ("كهرب", "⚡"), ("طاقه", "⚡"), ("طاقة", "⚡"), ("شمس", "☀️"), ("قمر", "🌙"), ("نجم", "⭐"), ("كوكب", "🪐"),
         ("ارض", "🌍"), ("أرض", "🌍"), ("فضاء", "🚀"), ("صاروخ", "🚀"), ("ذره", "⚛️"), ("ذرة", "⚛️"), ("خليه", "🔬"), ("خلية", "🔬"), ("جين", "🧬"), ("dna", "🧬"),
         ("فيروس", "🦠"), ("بكتيريا", "🦠"), ("مناعه", "🛡️"), ("مناعة", "🛡️"), ("حراره", "🌡️"), ("حرارة", "🌡️"), ("سخون", "🔥"), ("نار", "🔥"), ("برد", "❄️"),
         ("صوت", "🔊"), ("موسيق", "🎵"), ("مال", "💰"), ("فلوس", "💰"), ("نمو", "📈"), ("زياد", "📈"), ("ذكاء", "🤖"), ("كمبيوتر", "💻"), ("موبايل", "📱"),
         ("سؤال", "❓"), ("سر", "🔍"), ("لغز", "🧩"), ("خطر", "⚠️"), ("امان", "🔒"), ("أمان", "🔒"), ("عظم", "🦴"), ("عضل", "💪"), ("هواء", "🌬️"), ("مطر", "🌧️")]


def norm_ar(s):
    s = re.sub(r"[\u064B-\u0652\u0640]", "", s or "")
    return s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")


def pick_emoji(text, i=0, pool=("✨", "💡", "🔬", "🚀", "🎯", "🧠")):
    n = norm_ar(text).lower()
    for k, e in EMOJI:
        if norm_ar(k).lower() in n:
            return e
    return pool[i % len(pool)]


def split_sentences(script):
    txt = re.sub(r"[ \t]+", " ", (script or "").replace("\r", ""))
    txt = re.sub(r"^\s*(TITLE|SCRIPT|SOURCES)\s*[:：].*$", lambda m: m.group(0) if m.group(1) == "SCRIPT" else "", txt, flags=re.M | re.I)
    txt = re.sub(r"^\s*SCRIPT\s*[:：]\s*", "", txt, flags=re.M | re.I)
    parts = []
    for block in re.split(r"\n+", txt):
        block = block.strip()
        if not block:
            continue
        parts += [x.strip() for x in re.split(r"(?<=[.!?؟…])\s+|(?<=[.!?؟…])$", block) if x.strip()]
    out = []
    for p in parts:  # جملة طويلة جداً → تُكسر عند الفاصلة
        if len(p.split()) > 22:
            sub = [x.strip() for x in re.split(r"(?<=[،,؛;])\s+", p) if x.strip()]
            buf = ""
            for x in sub:
                if buf and len((buf + " " + x).split()) > 16:
                    out.append(buf); buf = x
                else:
                    buf = (buf + " " + x).strip()
            if buf: out.append(buf)
        else:
            out.append(p)
    return [x for x in out if re.search(r"\w", x)][:60]


def keywords(text, n=3):
    toks = re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}|[\u0621-\u064A]{3,}", text or "")
    seen, c = set(), []
    for i, w in enumerate(toks):
        k = norm_ar(w).lower()
        k2 = re.sub(r"^(ال|لل|وال|بال|كال)", "", k)
        if k in STOP or k2 in STOP or k in seen or len(k2) < 3:
            continue
        seen.add(k); c.append((len(w) + (3 if re.match(r"[A-Za-z]", w) else 0), i, w))
    best = sorted(c, key=lambda x: -x[0])[:n]
    return [w for _, _, w in sorted(best, key=lambda x: x[1])]


_AR_DIG = {ord(c): str(i) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩")}


def find_number(text):
    m = re.search(r"(\d[\d٠-٩.,]*)\s*(%|٪|في المية|في المائة|مليون|مليار|ألف|الف)?", (text or "").translate(_AR_DIG))
    if not m:
        return None
    raw = m.group(1).replace(",", "").rstrip(".")
    try:
        v = float(raw)
    except ValueError:
        return None
    unit = m.group(2) or ""
    if unit in ("٪", "في المية", "في المائة"): unit = "%"
    return {"value": v, "unit": unit}


def classify(lines):
    """نوع مشهد لكل سطر بقواعد واضحة (intro / question / stat / flow / concept / cards / recap)."""
    n, out, prev = len(lines), [], None
    for i, t in enumerate(lines):
        low = norm_ar(t)
        if i == 0: ty = "intro"
        elif i == n - 1 and n > 2: ty = "recap"
        elif "؟" in t or "?" in t or "عارف ليه" in low or "تعرف ليه" in low: ty = "question"
        elif find_number(t) and re.search(r"\d", t.translate(_AR_DIG)): ty = "stat"
        elif re.search(r"(مقابل|الفرق|بينما| vs |عكس|اما |مش .{2,14} بس)", low): ty = "compare"
        elif re.search(r"(دوره|يرجع|بيرجع|يتكرر|بيتكرر|حلقه|ويرجع تاني|وتاني)", low): ty = "cycle"
        elif re.search(r"(بعدين|وبعدين|ثم|الخطوه|الاول|اولا|تاني|ثانيا|→|->|يتحول|بيتحول|يوصل|بيوصل|ينتقل|بينتقل)", low): ty = "flow"
        elif re.search(r"(زي |زيّ|تخيل|كانه|كانها|مثل |شبه|لو |كده)", low): ty = "concept"
        else: ty = "cards" if prev == "concept" else "concept"
        if ty == prev and ty not in ("intro", "recap", "stat"):
            ty = "cards" if ty == "concept" else "concept"
        out.append(ty); prev = ty
    return out


def analyze(script):
    lines = split_sentences(script)
    types = classify(lines)
    scenes = []
    for i, (t, ty) in enumerate(zip(lines, types)):
        sc = {"text": t, "type": ty, "keys": keywords(t, 3), "emoji": pick_emoji(t, i), "num": find_number(t) if ty == "stat" else None}
        if ty == "compare":
            halves = re.split(r"\s(?:مقابل|بينما|عكس|vs|اما|أما)\s", t, maxsplit=1, flags=re.I)
            if len(halves) < 2:
                m2 = re.search(r"الفرق بين\s+(.+?)\s+و\s*(.+)", t)
                halves = [m2.group(1), m2.group(2)] if m2 else halves
            if len(halves) >= 2:
                ka, kb = keywords(re.sub(r"^.*?الفرق بين", "", halves[0]), 2), keywords(halves[1], 2)
                if ka and kb: sc["a"], sc["b"] = " ".join(ka), " ".join(kb)
        scenes.append(sc)
    return scenes


# ----------------------------------------------------------------------------- templates
def _esc_js(o):
    return json.dumps(o, ensure_ascii=False).replace("</", "<\\/")


def narration_block(lines, opts=None):
    if not lines:
        return ""
    hdr = "{ provider: \"auto\", lang: \"ar\", speed: 1, gap: 0.25 }," if opts is None else opts
    body = ",\n  ".join("{ text: " + json.dumps(l, ensure_ascii=False) + " }" for l in lines)
    return "export const NARRATION = [\n  " + hdr + "\n  " + body + "\n];"


THEMES = {
    "sci": ("علمي داكن", "--bg:#0C1014;--card:#161C22;--el:#202830;--tx:#F4F3EE;--tx2:#9AA5AE;--ac:#27B8C7;--ac2:#5978FF;--ok:#36C98F;--warn:#F28A30;--line:#26313A"),
    "neon": ("نيون", "--bg:#07040F;--card:#120B22;--el:#1B1033;--tx:#FFFFFF;--tx2:#B8A8E8;--ac:#FF3DCB;--ac2:#7A5CFF;--ok:#3DF2B5;--warn:#FFC93D;--line:#2A1B4D"),
    "paper": ("ورقي فاتح", "--bg:#F3EFE6;--card:#FFFFFF;--el:#ECE6D8;--tx:#1A1A1A;--tx2:#6B6558;--ac:#E8431F;--ac2:#2D5BFF;--ok:#16A05A;--warn:#D9780F;--line:#DDD5C2"),
    "gold": ("ذهبي فاخر", "--bg:#0B0A08;--card:#17140F;--el:#221D14;--tx:#FBF3DC;--tx2:#B5A783;--ac:#F2B632;--ac2:#E8731F;--ok:#7BD88F;--warn:#FF8A5C;--line:#3A3120"),
}

EXPLAINER_HTML = r"""<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>__TITLE__</title>
<style>
:root{__THEME__}
#root{position:absolute;width:1080px;height:1920px;background:var(--bg);color:var(--tx);overflow:hidden;direction:rtl}
.grid{position:absolute;inset:0;background-image:linear-gradient(rgba(154,165,174,.07) 2px,transparent 2px),linear-gradient(90deg,rgba(154,165,174,.07) 2px,transparent 2px);background-size:90px 90px}
.glow{position:absolute;width:900px;height:900px;border-radius:50%;filter:blur(120px);opacity:.22}
.tag{position:absolute;top:110px;right:70px;display:flex;gap:16px;align-items:center;font-size:38px;font-weight:700;color:var(--tx2)}
.tag i{width:18px;height:18px;border-radius:50%;background:var(--ac);display:block;box-shadow:0 0 24px var(--ac)}
.film{position:absolute;top:230px;left:70px;width:940px;height:1000px;border-radius:56px;background:var(--card);border:3px solid var(--line);overflow:hidden;box-shadow:0 40px 120px rgba(0,0,0,.55)}
.film:before{content:"";position:absolute;inset:0;background:radial-gradient(ellipse at 50% 0,rgba(39,184,199,.12),transparent 60%)}
.scene{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:34px;padding:60px;text-align:center}
.big{font-size:150px;font-weight:900;line-height:1.1;letter-spacing:-2px}
.mid{font-size:68px;font-weight:800;line-height:1.35}
.sub{font-size:44px;color:var(--tx2);font-weight:600}
.chip{display:inline-flex;align-items:center;gap:14px;padding:22px 40px;border-radius:999px;background:var(--el);border:3px solid var(--line);font-size:52px;font-weight:800}
.node{width:240px;height:240px;border-radius:50%;background:var(--el);border:4px solid var(--ac);display:flex;align-items:center;justify-content:center;font-size:110px;box-shadow:0 0 60px rgba(39,184,199,.25)}
.lbl{font-size:44px;font-weight:800;margin-top:18px}
.caps{position:absolute;left:70px;right:70px;top:1300px;height:420px;display:flex;flex-wrap:wrap;gap:6px 22px;justify-content:center;align-content:flex-start;direction:rtl}
.w{font-size:88px;font-weight:900;line-height:1.35;color:var(--tx2);opacity:.55}
.w.on{color:var(--tx);opacity:1}.w.hot{color:var(--ac);opacity:1}
.bar{position:absolute;left:70px;right:70px;bottom:130px;height:10px;border-radius:9px;background:var(--el);overflow:hidden;direction:ltr}
.bar b{display:block;height:100%;background:linear-gradient(90deg,var(--ac),var(--ac2));width:0}
svg{overflow:visible}
</style></head><body>
<div id="root">
  <div class="grid"></div><div class="glow" id="g1" style="background:var(--ac);top:-200px;left:-250px"></div><div class="glow" id="g2" style="background:var(--ac2);bottom:-300px;right:-300px"></div>
  <div class="tag"><i></i><span>__SERIES__</span></div>
  <div class="film" id="film"></div>
  <div class="caps" id="caps"></div>
  <div class="bar"><b id="prog"></b></div>
</div>
<script>
/* __NARRATION__ */
const LINES = __LINES__;
const SHOW_CAPTIONS = __CAPTIONS__;
const root=document.getElementById('root'),film=document.getElementById('film'),capsEl=document.getElementById('caps'),prog=document.getElementById('prog');
if(!SHOW_CAPTIONS)capsEl.style.display='none';
const el=(h)=>{const d=document.createElement('div');d.innerHTML=h.trim();return d.firstChild};
const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function build(L,i){
  const k=L.keys||[],e=L.emoji||'✨',s=document.createElement('div');s.className='scene';
  if(L.type==='intro'){s.innerHTML=`<div class="node" data-a="pop" style="width:320px;height:320px;font-size:150px">${e}</div><div class="big" data-a="rise" data-d=".15" style="font-size:110px">${esc(k[0]||L.text)}</div><div class="sub" data-a="rise" data-d=".3">${esc(k.slice(1).join(' · '))}</div>`}
  else if(L.type==='question'){s.innerHTML=`<div class="big" data-a="pop" style="font-size:340px;color:var(--ac)">؟</div><div class="mid" data-a="rise" data-d=".2">${esc(L.text.replace(/[؟?]/g,''))}</div>`}
  else if(L.type==='stat'){const n=L.num||{value:0,unit:''};s.innerHTML=`<svg width="520" height="520" viewBox="0 0 520 520" data-a="pop"><circle cx="260" cy="260" r="220" fill="none" style="stroke:var(--line)" stroke-width="34"/><circle id="ring${i}" cx="260" cy="260" r="220" fill="none" stroke="var(--ac)" stroke-width="34" stroke-linecap="round" transform="rotate(-90 260 260)" stroke-dasharray="1382" stroke-dashoffset="1382"/><text x="260" y="300" text-anchor="middle" style="fill:var(--tx);direction:ltr;unicode-bidi:isolate" font-size="150" font-weight="900" letter-spacing="0" id="num${i}" data-v="${n.value}" data-u="${esc(n.unit)}">0</text></svg><div class="mid" data-a="rise" data-d=".25">${esc(k.slice(0,2).join(' · ')||L.text)}</div>`}
  else if(L.type==='flow'){const a=[k[0]||'أ',k[1]||'ب',k[2]||'ج'],em=['🔹',e,'✅'];
    s.innerHTML=`<div style="display:flex;align-items:center;gap:0;direction:rtl">`+a.map((x,j)=>`<div style="display:flex;align-items:center"><div style="text-align:center" data-a="pop" data-d="${(j*.28).toFixed(2)}"><div class="node" style="width:200px;height:200px;font-size:90px">${em[j]}</div><div class="lbl">${esc(x)}</div></div>${j<2?`<svg width="110" height="40" viewBox="0 0 110 40" style="margin:0 6px 56px"><path data-draw="${(j*.28+.2).toFixed(2)}" d="M104 20H6M22 6L6 20l16 14" fill="none" stroke="var(--ac)" stroke-width="7" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="140" stroke-dashoffset="140"/></svg>`:''}</div>`).join('')+`</div><div class="sub" data-a="rise" data-d=".9" style="font-size:46px">${esc(L.text.slice(0,70))}</div>`}
  else if(L.type==='compare'){const a=L.a||k[0]||'أ',b=L.b||k[1]||'ب';
    s.innerHTML=`<div style="display:flex;align-items:center;gap:22px;direction:rtl"><div class="chip" data-a="pop" style="flex-direction:column;width:340px;padding:50px 18px;border-color:var(--ac)"><span style="font-size:96px">${e}</span><span style="font-size:44px;line-height:1.3">${esc(a)}</span></div><div class="big" data-a="pop" data-d=".25" style="font-size:84px;color:var(--warn)">VS</div><div class="chip" data-a="pop" data-d=".15" style="flex-direction:column;width:340px;padding:50px 18px;border-color:var(--ac2)"><span style="font-size:96px">⚖️</span><span style="font-size:44px;line-height:1.3">${esc(b)}</span></div></div><div class="sub" data-a="rise" data-d=".5">${esc(L.text.slice(0,70))}</div>`}
  else if(L.type==='cycle'){const a=[k[0]||'١',k[1]||'٢',k[2]||'٣'];
    s.innerHTML=`<svg width="640" height="640" viewBox="0 0 640 640"><circle data-draw2="1" cx="320" cy="320" r="230" fill="none" style="stroke:var(--ac)" stroke-width="10" stroke-linecap="round" stroke-dasharray="1445" stroke-dashoffset="1445" transform="rotate(-90 320 320)"/>`+a.map((x,j)=>{const g=(-90+j*120)*Math.PI/180,cx=320+230*Math.cos(g),cy=320+230*Math.sin(g);return `<g data-a2="${(j*.3).toFixed(2)}" transform="translate(${cx.toFixed(1)} ${cy.toFixed(1)})"><circle r="78" style="fill:var(--el);stroke:var(--ac)" stroke-width="5"/><text y="14" text-anchor="middle" font-size="40" font-weight="800" style="fill:var(--tx)">${esc(x.slice(0,9))}</text></g>`}).join('')+`<text x="320" y="355" text-anchor="middle" font-size="120">${e}</text></svg><div class="sub" data-a="rise" data-d=".6">${esc(L.text.slice(0,70))}</div>`}
  else if(L.type==='recap'){s.innerHTML=`<div class="mid" data-a="pop" style="font-size:90px;color:var(--ok)">الخلاصة</div>`+(k.length?k:[L.text]).slice(0,3).map((x,j)=>`<div class="chip" data-a="rise" data-d="${(.2+j*.22).toFixed(2)}"><span style="color:var(--ok)">✓</span>${esc(x)}</div>`).join('')}
  else if(L.type==='cards'){s.innerHTML=(k.length?k:[L.text]).slice(0,3).map((x,j)=>`<div class="chip" data-a="rise" data-d="${(j*.2).toFixed(2)}" style="width:700px;justify-content:flex-start;font-size:58px;padding:34px 44px;border-color:${['var(--ac)','var(--ac2)','var(--ok)'][j]}"><span>${['🔹','🔸','🔷'][j]}</span>${esc(x)}</div>`).join('')}
  else{s.innerHTML=`<div class="node" data-a="pop" style="width:300px;height:300px;font-size:140px">${e}</div><div style="display:flex;gap:20px;flex-wrap:wrap;justify-content:center">`+(k.length?k:[L.text.slice(0,24)]).map((x,j)=>`<div class="chip" data-a="rise" data-d="${(.2+j*.2).toFixed(2)}">${esc(x)}</div>`).join('')+`</div>`}
  film.appendChild(s);return s}
const scenes=LINES.map(build);
function nrm(s){return String(s).replace(/[\u064B-\u0652\u0640]/g,'').replace(/[أإآ]/g,'ا').replace(/ة/g,'ه').replace(/ى/g,'ي').replace(/[^\w\u0621-\u064A]/g,'').toLowerCase()}
// محاذاة: كل سطر من السكربت يُطابَق على كلمات التفريغ بأول كلماته (يتحمّل أخطاء التفريغ) بدل التقدير بالنسبة
function align(W){const nw=W.map(w=>nrm(w.text)),st=[];let ptr=0;
  for(let i=0;i<LINES.length;i++){const toks=LINES[i].text.split(/\s+/).map(nrm).filter(Boolean);
    if(i===0){st.push(0);ptr=toks.length;continue}
    let best=-1;for(let j=Math.max(0,ptr-5);j<Math.min(nw.length,ptr+16)&&best<0;j++){let sc=0;for(let q=0;q<Math.min(3,toks.length);q++)if(nw[j+q]&&nw[j+q]===toks[q])sc++;if(sc>=Math.min(2,toks.length))best=j}
    if(best<0)best=Math.min(nw.length-1,ptr);if(best<=st[i-1])best=Math.min(nw.length-1,st[i-1]+1);st.push(best);ptr=best+toks.length}
  return st}
function timings(P,D){
  if(P.scenes&&P.scenes.length===LINES.length)return P.scenes.map((s,i)=>[i===0?0:s.start,i===LINES.length-1?D:P.scenes[i+1].start]);
  const W=P.words||[];let st=[];
  if(W.length){const ix=align(W);st=ix.map((k,i)=>i===0?0:Math.max(0,W[k].start-.05))}
  else{const cnt=LINES.map(l=>l.text.split(/\s+/).filter(Boolean).length),tot=cnt.reduce((a,b)=>a+b,0);let c=0;cnt.forEach(n=>{st.push(c/tot*D);c+=n})}
  for(let i=1;i<st.length;i++)if(st[i]<=st[i-1])st[i]=st[i-1]+.2;
  return st.map((a,i)=>[a,i<st.length-1?st[i+1]:D])}
let TM=null,CHUNKS=null;
function words(P,D,TMs){
  if(P.words&&P.words.length)return P.words.map(w=>({t:w.text,s:w.start,e:w.end}));
  const out=[];LINES.forEach((l,i)=>{const ws=l.text.split(/\s+/).filter(Boolean),[a,b]=TMs[i],d=(b-a)*.92/ws.length;ws.forEach((w,j)=>out.push({t:w,s:a+j*d,e:a+(j+1)*d}))});return out}
function chunks(W){const c=[];for(let i=0;i<W.length;i+=3)c.push(W.slice(i,i+3));return c}
function accent(w){return w.length>=5}
window.drawFrame=function(t,SA){
  const D=SA.total/SA.fps;SA.fit&&SA.fit(root,1080,1920);
  if(!TM){TM=timings(SA.props,D);CHUNKS=chunks(words(SA.props,D,TM))}
  prog.style.width=(t/D*100).toFixed(2)+'%';
  document.getElementById('g1').style.transform=`translate(${Math.sin(t*.5)*60}px,${Math.cos(t*.4)*50}px)`;
  let cur=0;TM.forEach((r,i)=>{if(t>=r[0]-.04)cur=i});
  scenes.forEach((s,i)=>{
    const [a,b]=TM[i],lt=t-a,vis=t>=a-.12&&t<b+.12;s.style.display=vis?'flex':'none';if(!vis)return;
    const fin=SA.p(t,a-.12,a+.18,'out'),fout=1-SA.p(t,b-.08,b+.12,'in');s.style.opacity=Math.min(fin,fout).toFixed(3);
    const push=1.03+.06*SA.clamp(lt/Math.max(.5,b-a));s.style.transform=`scale(${push.toFixed(4)})`;
    s.querySelectorAll('[data-a]').forEach(n=>{const d=parseFloat(n.dataset.d||0),x=lt-d;
      if(n.dataset.a==='pop'){const q=SA.pop(x,0,.5);n.style.transform=`scale(${q.s.toFixed(3)})`;n.style.opacity=q.o.toFixed(3)}
      else{const p=SA.p(x,0,.55,'expo');n.style.transform=`translateY(${((1-p)*60).toFixed(1)}px)`;n.style.opacity=p.toFixed(3)}});
    s.querySelectorAll('[data-draw2]').forEach(n=>{const p=SA.p(lt,.1,1.3,'inOut');n.setAttribute('stroke-dashoffset',(1445*(1-p)).toFixed(1))});
    s.querySelectorAll('[data-a2]').forEach(n=>{n.setAttribute('opacity',SA.p(lt,parseFloat(n.dataset.a2),parseFloat(n.dataset.a2)+.3,'out').toFixed(3))});
    s.querySelectorAll('[data-draw]').forEach(n=>{const p=SA.p(lt,parseFloat(n.dataset.draw),parseFloat(n.dataset.draw)+.4,'out');n.setAttribute('stroke-dashoffset',(140*(1-p)).toFixed(1))});
    const ring=s.querySelector('circle[id^=ring]'),num=s.querySelector('text[id^=num]');
    if(num){const v=parseFloat(num.dataset.v),u=num.dataset.u,p=SA.p(lt,.1,1.1,'expo');const cv=Number.isInteger(v)?Math.round(v*p):(Math.round(v*p*10)/10);num.textContent=cv+(u==='%'?'%':'');
      if(ring)ring.setAttribute('stroke-dashoffset',(1382*(1-Math.min(1,(u==='%'?v/100:.75))*p)).toFixed(1))}
  });
  if(SHOW_CAPTIONS){
    let ci=0;CHUNKS.forEach((c,i)=>{if(t>=c[0].s-.08)ci=i});const c=CHUNKS[ci]||[];
    const key=ci+'|'+c.map(w=>t>=w.s?1:0).join('');
    if(capsEl.dataset.k!==key){capsEl.dataset.k=key;capsEl.innerHTML=c.map(w=>`<span class="w ${t>=w.s?(accent(w.t)?'hot':'on'):''}">${esc(w.t)}</span>`).join('')}
    capsEl.style.opacity=SA.p(t,c.length?c[0].s-.08:0,c.length?c[0].s+.05:.1,'out')}
};
</script></body></html>"""


def build_explainer_html(scenes, title="", series="علوم ببساطة", captions=True, narration=None, theme="sci"):
    html = EXPLAINER_HTML.replace("__THEME__", THEMES.get(theme, THEMES["sci"])[1])
    html = html.replace("__TITLE__", _html.escape(title or "Explainer"))
    html = html.replace("__SERIES__", _html.escape(series))
    html = html.replace("__CAPTIONS__", "true" if captions else "false")
    html = html.replace("__LINES__", _esc_js(scenes))
    html = html.replace("/* __NARRATION__ */", ("/*\n" + narration.replace("*/", "* /") + "\n*/") if narration else "")
    return html


CAPTIONS_HTML = r"""<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>Captions</title>
<style>
#root{position:absolute;width:1080px;height:1920px;background:radial-gradient(1200px 900px at 50% 30%,#1b2430,#090c10);overflow:hidden}
.words{position:absolute;left:80px;right:80px;top:700px;display:flex;flex-wrap:wrap;gap:10px 26px;justify-content:center;direction:rtl}
.w{font-size:120px;font-weight:900;color:#5c6670;line-height:1.35;display:inline-block}
.w.on{color:#fff}.w.now{color:#27B8C7}
.hint{position:absolute;top:900px;width:100%;text-align:center;font-size:48px;color:#9AA5AE}
</style></head><body>
<div id="root"><div class="words" id="w"></div><div class="hint" id="h"></div></div>
<script>
// ترجمة كلمة بكلمة: كل كلمة تُضاء لحظة نطقها بالضبط (من props.words التي يملؤها زر «تفريغ الصوت»)
const root=document.getElementById('root'),box=document.getElementById('w'),hint=document.getElementById('h');
window.drawFrame=function(t,SA){
  SA.fit(root,1080,1920);
  const W=SA.props.words||[];
  if(!W.length){hint.textContent='ارفع الصوت واضغط «تفريغ الصوت» لتظهر الكلمات هنا';return}
  hint.textContent='';
  let i0=0;W.forEach((w,i)=>{if(t>=w.start-.05)i0=i});const g=Math.floor(i0/4)*4,c=W.slice(g,g+4);
  const key=g+'|'+c.map((w,j)=>t>=w.start?(g+j===i0?2:1):0).join('');
  if(box.dataset.k!==key){box.dataset.k=key;box.innerHTML=c.map((w,j)=>`<span class="w ${t>=w.start?(g+j===i0?'now':'on'):''}">${w.text}</span>`).join('')}
  const p=SA.p(t,c[0].start-.1,c[0].start+.1,'out');box.style.opacity=p;box.style.transform=`scale(${(.94+.06*p).toFixed(3)})`;
};
</script></body></html>"""

TITLE_HTML = r"""<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>Title</title>
<style>
body{background:#0C1014}
#root{position:absolute;width:1080px;height:1920px;background:radial-gradient(900px 900px at 70% 20%,rgba(89,120,255,.35),transparent 60%),radial-gradient(900px 900px at 20% 80%,rgba(39,184,199,.3),transparent 60%),#0C1014;overflow:hidden;color:#F4F3EE;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:50px}
.t{font-size:150px;font-weight:900;text-align:center;line-height:1.25;padding:0 70px}
.l{height:14px;border-radius:9px;background:linear-gradient(90deg,#27B8C7,#5978FF)}
</style></head><body>
<div id="root"><div class="t" id="t">عنوان الفيديو هنا</div><div class="l" id="l"></div></div>
<script>
const root=document.getElementById('root'),t_=document.getElementById('t'),l_=document.getElementById('l');
window.drawFrame=function(t,SA){SA.fit(root,1080,1920);
  const a=SA.p(t,.2,1.0,'expo');t_.style.opacity=a;t_.style.transform=`translateY(${(1-a)*80}px) scale(${1+(1-a)*.08})`;
  l_.style.width=(SA.p(t,.7,1.5,'expo')*420)+'px'};
</script></body></html>"""

# طبقة Remotion شفافة للدمج: ترجمة + شريط تقدم فوق خلفية HyperFrames
MERGE_OVERLAY_TSX = r"""import React from "react";
import { AbsoluteFill, getInputProps, useVideoConfig } from "remotion";
import { Captions, ProgressBar, SA } from "./sa_kit";

// طبقة شفافة (alpha) تُركَّب فوق تركيبة HyperFrames. لا تضع خلفية هنا.
export const Motion: React.FC<any> = (props) => {
  let inp: any = {};
  try { inp = getInputProps() || {}; } catch (e) {}
  const segments = (props.segments && props.segments.length ? props.segments : inp.segments) || [];
  return (
    <AbsoluteFill style={{ background: "transparent" }}>
      <Captions segments={segments} variant="karaoke" anchor="bottom" size={0.085} emoji={false} />
      <ProgressBar color={SA.c} />
    </AbsoluteFill>
  );
};
"""

HF_TEMPLATES = {
    "hf_explainer": ("شرح علمي (HyperFrames)", None),
    "hf_captions": ("ترجمة كلمة بكلمة (HyperFrames)", CAPTIONS_HTML),
    "hf_title": ("عنوان سينمائي (HyperFrames)", TITLE_HTML),
}
DEMO_SCRIPT = ("هل تعرف إن قلبك بينبض أكتر من 100 ألف مرة في اليوم؟ عارف ليه؟ "
               "تخيل القلب زي طلمبة مية بتدفع الدم في كل الجسم. "
               "بعدين الدم يوصل للرئة ياخد الأكسجين ويرجع تاني. "
               "والنتيجة إن الجسم كله بياخد الطاقة اللي محتاجها. "
               "الخلاصة: القلب مش بيرتاح، وده سر إنك عايش.")


def template_code(name):
    if name == "hf_explainer":
        return build_from_script(DEMO_SCRIPT, "hyperframes")["code"]
    if name in HF_TEMPLATES:
        return HF_TEMPLATES[name][1]
    if name == "merge_pro":
        b = build_from_script(DEMO_SCRIPT, "merge")
        return b["code"]
    return None


# ----------------------------------------------------------------------------- script -> design
def build_from_script(script, engine="hyperframes", title="", series="علوم ببساطة", voice=True, captions=True, theme="sci"):
    scenes = analyze(script)
    if not scenes:
        raise ValueError("السكربت فارغ")
    lines = [s["text"] for s in scenes]
    nar = narration_block(lines) if voice else None
    if engine == "remotion":
        from_tpl = REMOTION_VO_FALLBACK
        code = (nar + "\n\n" if nar else "") + from_tpl
        return {"engine": "remotion", "code": code, "scenes": scenes, "hf": "", "remotion": code}
    if engine == "merge":
        hf = build_explainer_html(scenes, title, series, captions=False, narration=nar, theme=theme)
        rem = MERGE_OVERLAY_TSX
        combined = "//@@ENGINE hyperframes\n" + hf + "\n//@@ENGINE remotion\n" + rem
        return {"engine": "merge", "code": combined, "scenes": scenes, "hf": hf, "remotion": rem}
    hf = build_explainer_html(scenes, title, series, captions=captions, narration=nar, theme=theme)
    return {"engine": "hyperframes", "code": hf, "scenes": scenes, "hf": hf, "remotion": ""}


REMOTION_VO_FALLBACK = r"""// قالب «تعليق صوتي»: كل جملة من NARRATION تصبح مشهداً يبدأ لحظة نطقها، والكلمات تُضاء حسب التوقيت الحقيقي.
export { Motion } from "./tpl_voiceover";
"""


# ----------------------------------------------------------------------------- running
_ENV_DROP = ("SA_MASTER", "ADMIN_PASS", "ADMIN_EMAIL", "GH_TOKEN", "TG_BOT_TOKEN", "TG_CHAT_ID", "TG_STORAGE_CHAT", "SA_KEY")


_PROBE = {"t": 0.0, "v": None}


def probe_browser(W, force=False):
    """يشغّل المتصفح فعلياً مرة (ويخزّن النتيجة) ليعرف المستخدم السبب الحقيقي إن لم يكن جاهزاً."""
    import time
    now = time.time()
    if not force and _PROBE["v"] is not None and now - _PROBE["t"] < (300 if _PROBE["v"].get("ok") else 20):
        return _PROBE["v"]
    try:
        r = subprocess.run(["node", os.path.join(W, "hf_render.cjs"), "--probe"], cwd=W, capture_output=True, text=True, timeout=60)
        line = [x for x in r.stdout.strip().split("\n") if x.startswith("{")][-1:]
        v = json.loads(line[0]) if line else {"ok": False, "error": (r.stderr or "no output")[-300:]}
    except Exception as e:
        v = {"ok": False, "error": str(e)[:300]}
    _PROBE.update(t=now, v=v)
    return v


def hf_ready(W, deep=True):
    """يتحقق من: ملف الرندر + ffmpeg + node + متصفح يعمل فعلياً."""
    ok_script = os.path.exists(os.path.join(W, "hf_render.cjs"))
    ok_ff = bool(shutil.which("ffmpeg"))
    ok_node = bool(shutil.which("node"))
    pr = probe_browser(W) if (deep and ok_script and ok_ff and ok_node) else {"ok": ok_script and ok_ff and ok_node}
    why = None
    if not ok_script: why = "ملف hf_render.cjs غير موجود"
    elif not ok_ff: why = "ffmpeg غير مثبّت"
    elif not ok_node: why = "node غير مثبّت"
    elif not pr.get("ok"): why = pr.get("error") or "المتصفح لا يعمل"
    return {"script": ok_script, "ffmpeg": ok_ff, "browser": pr.get("browser"), "ready": ok_script and ok_ff and ok_node and bool(pr.get("ok")), "why": why}


def run_hf(host, jid, J, spec, lo=1, hi=90, label="HyperFrames"):
    """يشغّل hf_render.cjs ويحوّل أحداثه إلى تقدّم المهمة. -> (rc, err, tail)"""
    W = host.W
    sfile = f"{W}/out/{jid}_hf_{abs(hash(spec['output'])) % 99999}.json"
    json.dump(spec, open(sfile, "w", encoding="utf-8"), ensure_ascii=False)
    env = {k: v for k, v in os.environ.items() if k not in _ENV_DROP}
    p = subprocess.Popen(["node", f"{W}/hf_render.cjs", sfile], cwd=W, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, bufsize=1, start_new_session=True)
    host.PROCS[jid] = p
    tail, err, logs = [], None, []
    try:
        for line in p.stdout:
            line = line.rstrip()
            if not line.startswith("@@"):
                if line.strip(): tail.append(line); tail = tail[-60:]
                continue
            try: ev = json.loads(line[2:])
            except Exception: continue
            st = ev.get("stage")
            if st == "compose": J.update(stage=f"تحضير {label}", progress=lo, details="")
            elif st == "render":
                pr = float(ev.get("progress", 0) or 0)
                sp = f" · {ev['fps']} إطار/ث" if ev.get("fps") else ""
                J.update(stage=f"رندر {label}", progress=lo + int(pr * (hi - lo)), details=f"{ev.get('rendered', 0)} / {ev.get('total', 0)} إطار{sp}")
            elif st == "log": logs.append(ev.get("text", "")); J["logs"] = logs[-10:]
            elif st == "error": err = ev.get("text", "")
        p.wait()
    finally:
        try: os.remove(sfile)
        except Exception: pass
    return p.returncode, err, tail


def _first_line(msg):
    ls = [x.strip() for x in str(msg or "").split("\n") if x.strip() and not x.strip().startswith(("at ", "node:", "^", "requireStack"))]
    hit = next((x for x in ls if re.search(r"error|cannot|خطأ|failed|فشل", x, re.I)), None)
    return (hit or (ls[0] if ls else "خطأ غير معروف"))[:240]


def probe_has_alpha(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=pix_fmt:stream_tags=alpha_mode", "-of", "json", path],
                       capture_output=True, text=True)
    return "yuva" in r.stdout or "alpha_mode" in r.stdout


def composite_layers(bottom, top, out, fps, w, h, top_opacity=1.0):
    """bottom: mp4 معتم · top: webm (VP9 alpha) → mp4 واحد. libvpx-vp9 كمفكّك ضروري لقراءة قناة الشفافية."""
    op = f",colorchannelmixer=aa={top_opacity:.3f}" if top_opacity < 0.999 else ""
    fc = f"[1:v]format=yuva420p{op}[t];[0:v][t]overlay=0:0:format=auto,format=yuv420p[v]"
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", bottom, "-c:v", "libvpx-vp9", "-i", top, "-filter_complex", fc, "-map", "[v]",
                        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(fps), "-movflags", "+faststart", out],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg overlay: " + r.stderr[-700:])


def concat_parts(parts, out, fps):
    lst = out + ".txt"
    open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "16",
                        "-pix_fmt", "yuv420p", "-r", str(fps), "-movflags", "+faststart", out], capture_output=True, text=True)
    try: os.remove(lst)
    except Exception: pass
    if r.returncode != 0:
        raise RuntimeError("ffmpeg concat: " + r.stderr[-700:])


def normalize_cuts(cuts, duration, default="hyperframes"):
    """يرتّب فواصل التتابع ويملأ الفراغات: [{from,to,engine}] تغطي 0..duration بلا تداخل."""
    clean = []
    for c in cuts or []:
        try:
            a, b = float(c.get("from", 0)), float(c.get("to", 0))
        except Exception:
            continue
        e = c.get("engine") if c.get("engine") in ("remotion", "hyperframes") else default
        a, b = max(0.0, min(duration, a)), max(0.0, min(duration, b))
        if b - a >= 0.04: clean.append({"from": a, "to": b, "engine": e})
    clean.sort(key=lambda c: c["from"])
    out, cur = [], 0.0
    for c in clean:
        a = max(c["from"], cur)
        if a - cur > 0.04: out.append({"from": cur, "to": a, "engine": default})
        if c["to"] - a >= 0.04: out.append({"from": a, "to": c["to"], "engine": c["engine"]}); cur = c["to"]
    if duration - cur > 0.04: out.append({"from": cur, "to": duration, "engine": default})
    if not out: out = [{"from": 0.0, "to": duration, "engine": default}]
    return out


def render(host, jid, d, J, props, pub, out, cfg, remotion_spec_base=None):
    """رندر المحركات غير Remotion-الخالص. -> (rc, err, tail). النتيجة تُكتب في out (mp4 بلا صوت أو مع صوت Remotion)."""
    eng = d.get("engine")
    W, fps, frames = host.W, cfg["fps"], cfg["frames"]
    w, h = cfg["width"], cfg["height"]
    html_src = d.get("hf_html", "")
    mode = d.get("mode")
    fdir = next((p for p in (os.path.join(W, "fonts"), os.path.join(W, "public", "fonts")) if os.path.isdir(p)), None)
    workers = max(1, min(4, (os.cpu_count() or 2) // 2 + (1 if (os.cpu_count() or 2) > 2 else 0)))
    base = {"root": W, "publicDir": pub, "width": w, "height": h, "fps": fps, "frames": frames, "crf": cfg["crf"], "preset": cfg["preset"], "props": props,
            "workers": int(os.environ.get("SA_HF_WORKERS", workers)), "fontsDir": fdir}

    def hf_spec(output, alpha=False, a=None, b=None):
        s = dict(base, html=prepare_html(html_src, props, w, h, alpha, fdir), output=output, alpha=alpha, mode="video")
        if a is not None: s["startFrame"], s["endFrame"] = a, b
        return s

    def rem_spec(output, alpha=False, a=None, b=None):
        s = dict(remotion_spec_base or {}, output=output, mode="video", alpha=alpha)
        if a is not None: s["frameRange"] = [a, max(a, b - 1)]
        return s

    def run_rem(spec, lo, hi):
        sf = f"{W}/out/{jid}_rem_{abs(hash(spec['output'])) % 99999}.json"
        json.dump(spec, open(sf, "w", encoding="utf-8"), ensure_ascii=False)
        try: return host.run_node_render(jid, sf, J)
        finally:
            try: os.remove(sf)
            except Exception: pass

    if eng == "hyperframes":
        if mode == "still":
            s = hf_spec(out); s["mode"] = "still"; s["frame"] = cfg.get("still_frame", 0)
            return run_hf(host, jid, J, s)
        return run_hf(host, jid, J, hf_spec(out))

    # ---- merge
    m = d.get("merge") or {}
    kind = m.get("mode", "layers")
    tmp = f"{W}/out/{jid}_mg"
    if mode == "still":
        # لقطة مدموجة: نرندر الطبقتين كلقطة واحدة ثم نركّب
        t = cfg.get("still_frame", 0)
        s = hf_spec(tmp + "_hf.jpg"); s["mode"] = "still"; s["frame"] = t
        rc, err, tail = run_hf(host, jid, J, s)
        if rc != 0: return rc, err, tail
        if kind == "layers":
            rs = rem_spec(tmp + "_rem.png", alpha=True); rs["mode"] = "still"; rs["frame"] = t; rs["alpha"] = True
            rc, err, tail = run_rem(rs, 40, 80)
            if rc != 0: return rc, err, tail
            r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp + "_hf.jpg", "-i", tmp + "_rem.png", "-filter_complex", "[0][1]overlay=0:0", "-frames:v", "1", out],
                               capture_output=True, text=True)
            if r.returncode != 0: return 1, "ffmpeg: " + r.stderr[-400:], []
        else:
            shutil.copy2(tmp + "_hf.jpg", out)
        for x in ("_hf.jpg", "_rem.png"):
            try: os.remove(tmp + x)
            except Exception: pass
        return 0, None, []

    if kind == "layers":
        top_is = m.get("top", "remotion")
        top_op = float(m.get("opacity", 1.0) or 1.0)
        hf_alpha = (top_is == "hyperframes")
        # الطبقة السفلية معتمة، العلوية شفافة (VP9 alpha)
        if top_is == "remotion":
            J.update(stage="الطبقة الأولى: HyperFrames", progress=2)
            rc, err, tail = run_hf(host, jid, J, hf_spec(tmp + "_bottom.mp4"), 2, 45)
            if rc != 0: return rc, err, tail
            J.update(stage="الطبقة الثانية: Remotion (شفاف)", progress=46)
            rc, err, tail = run_rem(rem_spec(tmp + "_top.webm", alpha=True), 46, 85)
            if rc != 0:
                if J.get("cancelled"): return rc, err, tail
                # لا نُضيّع رندر HyperFrames: نسلّمه كما هو مع تحذير يشرح سبب فشل طبقة Remotion
                shutil.move(tmp + "_bottom.mp4", out)
                d.setdefault("engine_warnings", []).append("فشلت طبقة Remotion فسُلِّم HyperFrames فقط: " + _first_line(err or "\n".join(tail[-3:])))
                return 0, None, []
        else:
            J.update(stage="الطبقة الأولى: Remotion", progress=2)
            rc, err, tail = run_rem(rem_spec(tmp + "_bottom.mp4"), 2, 45)
            if rc != 0: return rc, err, tail
            J.update(stage="الطبقة الثانية: HyperFrames (شفاف)", progress=46)
            rc, err, tail = run_hf(host, jid, J, hf_spec(tmp + "_top.webm", alpha=True), 46, 85)
            if rc != 0: return rc, err, tail
        J.update(stage="تركيب الطبقتين", progress=88)
        try: composite_layers(tmp + "_bottom.mp4", tmp + "_top.webm", out, fps, w, h, top_op)
        except Exception as e: return 1, str(e), []
        for x in ("_bottom.mp4", "_top.webm"):
            try: os.remove(tmp + x)
            except Exception: pass
        return 0, None, []

    # ---- sequence
    dur = frames / fps
    cuts = normalize_cuts(m.get("cuts"), dur, m.get("default", "hyperframes"))
    parts, n = [], len(cuts)
    for i, c in enumerate(cuts):
        a, b = int(round(c["from"] * fps)), int(round(c["to"] * fps))
        if i == n - 1: b = frames
        if b - a < 1: continue
        lo, hi = 2 + int(i / n * 84), 2 + int((i + 1) / n * 84)
        pth = f"{tmp}_p{i}.mp4"
        J.update(stage=f"مقطع {i + 1}/{n}: {'HyperFrames' if c['engine'] == 'hyperframes' else 'Remotion'}", progress=lo)
        if c["engine"] == "hyperframes": rc, err, tail = run_hf(host, jid, J, hf_spec(pth, False, a, b), lo, hi)
        else:
            rc, err, tail = run_rem(rem_spec(pth, False, a, b), lo, hi)
            if rc != 0 and not J.get("cancelled"):
                d.setdefault("engine_warnings", []).append(f"فشل مقطع Remotion ({c['from']:.1f}-{c['to']:.1f}ث) فرُندر بـ HyperFrames بدلاً منه: " + _first_line(err or "\n".join(tail[-3:])))
                rc, err, tail = run_hf(host, jid, J, hf_spec(pth, False, a, b), lo, hi)
        if rc != 0: return rc, err, tail
        parts.append(pth)
    J.update(stage="دمج المقاطع", progress=88)
    try: concat_parts(parts, out, fps)
    except Exception as e: return 1, str(e), []
    for p in parts:
        try: os.remove(p)
        except Exception: pass
    return 0, None, []


# ----------------------------------------------------------------------------- routes
def register(app, host):
    from flask import request, jsonify

    @app.route("/api/engines")
    def api_engines():
        st = hf_ready(host.W)
        return jsonify({"engines": [
            {"id": "remotion", "name": "Remotion", "desc": "React · قوالب غنية وانتقالات", "ready": True},
            {"id": "hyperframes", "name": "HyperFrames", "desc": "HTML حتمي · سريع وخفيف", "ready": st["ready"], "why": st.get("why")},
            {"id": "merge", "name": "دمج", "desc": "طبقات أو تتابع بين المحركين", "ready": st["ready"], "why": st.get("why")}],
            "themes": [{"id": k, "name": v[0]} for k, v in THEMES.items()],
            "templates": [{"id": k, "name": v[0]} for k, v in HF_TEMPLATES.items()] + [{"id": "merge_pro", "name": "دمج احترافي (طبقات)"}]})

    @app.route("/api/hf/template/<name>")
    def api_hf_template(name):
        code = template_code(name)
        if code is None:
            return "قالب غير موجود", 404
        return code, 200, {"Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store"}

    @app.route("/api/script/build", methods=["POST"])
    def api_script_build():
        d = request.json or {}
        eng = d.get("engine") if d.get("engine") in ENGINES else "hyperframes"
        try:
            b = build_from_script(d.get("script", ""), eng, d.get("title", ""), (d.get("series") or "علوم ببساطة")[:40],
                                  voice=bool(d.get("voice", True)), captions=bool(d.get("captions", True)), theme=d.get("theme") if d.get("theme") in THEMES else "sci")
        except ValueError as e:
            return str(e), 400
        words = sum(len(s["text"].split()) for s in b["scenes"])
        return jsonify({"engine": b["engine"], "code": b["code"], "hf": b["hf"], "remotion": b["remotion"],
                        "scenes": [{"type": s["type"], "text": s["text"][:80]} for s in b["scenes"]],
                        "seconds_estimate": round(words / 2.6, 1), "words": words})

    @app.route("/api/hf/preview", methods=["POST"])
    def api_hf_preview():
        """يعيد HTML جاهزاً للمعاينة الحية داخل iframe معزول (sandbox)؛ العميل يحرّك الزمن عبر postMessage."""
        d = request.json or {}
        code = d.get("code", "")
        if not (code or "").strip():
            return "الكود فارغ", 400
        w = max(64, min(3840, int(d.get("width", 1080) or 1080)))
        h = max(64, min(3840, int(d.get("height", 1920) or 1920)))
        words = [x for x in (d.get("words") or []) if isinstance(x, dict)][:6000]
        props = {"words": words, "segments": (d.get("segments") or [])[:3000]}
        page = prepare_html(code, props, w, h, False, None)
        bridge = ("<script>addEventListener('message',function(e){var m=e.data||{};if(m.k==='init'){window.__sa.ready({fps:m.fps,total:m.total,props:m.props||{}})"
                  ".then(function(){parent.postMessage({k:'ready'},'*')})}else if(m.k==='seek'){window.__sa.seek(m.t).then(function(){parent.postMessage({k:'seeked'},'*')})}});"
                  "addEventListener('load',function(){parent.postMessage({k:'loaded'},'*')});</script>")
        page = page.replace("</body>", bridge + "</body>", 1) if "</body>" in page else page + bridge
        return jsonify({"html": page, "notes": check_html(code)})

    @app.route("/api/hf/check", methods=["POST"])
    def api_hf_check():
        errs = check_html((request.json or {}).get("code", ""))
        return jsonify({"ok": not [e for e in errs if not e.startswith("تنبيه")], "notes": errs})
