# -*- coding: utf-8 -*-
"""واجهة المحركات (Remotion / HyperFrames / دمج) + السكربت←فيديو + حفظ المشروع. تُحقن في index.html وقت البناء بدون لمس بقية الواجهة."""

CSS = r"""
.engs{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.eng{background:#fff;border:1.5px solid var(--line);border-radius:14px;padding:11px 6px;cursor:pointer;text-align:center;transition:.15s}
.eng b{display:block;font-size:13px;margin-bottom:3px}.eng small{display:block;font-size:10.5px;color:var(--t3);line-height:1.5}
.eng:hover{border-color:var(--ac)}.eng.on{border-color:var(--ac);background:rgba(232,67,31,.07);box-shadow:0 4px 14px rgba(232,67,31,.14)}.eng.on b{color:var(--ac2)}
.eng.off{opacity:.45;pointer-events:none}
#mergeBox{margin-top:10px;padding:10px;border:1px dashed var(--line);border-radius:12px;background:var(--s2)}
#mergeBox textarea.in{min-height:78px;font-family:'JetBrains Mono',monospace;font-size:12px;direction:ltr;text-align:left}
.srow{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}.srow .qc{cursor:pointer}
.pipe{display:flex;gap:6px;align-items:center;justify-content:center;flex-wrap:wrap;margin-bottom:6px}
.pipe span{font-size:11px;padding:3px 10px;border-radius:20px;background:var(--s3);color:var(--t3);border:1px solid var(--line)}
.pipe span.on{background:var(--ac);color:#fff;border-color:var(--ac)}.pipe span.done{background:rgba(22,160,90,.12);color:var(--ok);border-color:rgba(22,160,90,.35)}
.tpls .tab{font-weight:600}.tpls .tab.act2{border-color:var(--ac);color:var(--ac2);background:rgba(232,67,31,.07)}
#pvModal{position:fixed;inset:0;background:rgba(10,10,12,.78);z-index:9999;display:none;align-items:center;justify-content:center;flex-direction:column;gap:10px;padding:14px}
#pvModal.on{display:flex}#pvBox{position:relative;background:#000;border-radius:14px;overflow:hidden;box-shadow:0 20px 80px rgba(0,0,0,.6)}
#pvBox iframe{border:0;position:absolute;left:0;top:0;transform-origin:0 0;background:#000}
#pvBar{display:flex;gap:10px;align-items:center;width:min(560px,94vw);direction:ltr;color:#fff;font-size:12px}#pvBar input{flex:1}
#pvBar button{background:#fff;color:#111;border:0;border-radius:9px;padding:6px 14px;font-weight:700;cursor:pointer}
.sc-list{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px}.sc-list span{font-size:10.5px;background:var(--s2);border:1px solid var(--line);border-radius:20px;padding:2px 9px;color:var(--t2)}
"""

CARDS = r"""
 <div class="card" id="engCard"><h3><b>00</b>محرك الرندر</h3>
  <div class="engs" id="engs">
   <div class="eng" data-e="remotion"><b>Remotion</b><small>React · قوالب وانتقالات غنية</small></div>
   <div class="eng" data-e="hyperframes"><b>HyperFrames</b><small>HTML حتمي · خفيف وسريع</small></div>
   <div class="eng" data-e="merge"><b>دمج ⚡</b><small>الاثنان معاً في فيديو واحد</small></div>
  </div>
  <div id="mergeBox" style="display:none">
   <label class="l" style="margin-top:0">طريقة الدمج</label>
   <select class="in" id="mgMode"><option value="layers">طبقات — فوق بعض (شفافية)</option><option value="sequence">تتابع — كل مقطع زمني بمحرك</option></select>
   <div id="mgLayers"><label class="l">الطبقة العلوية (الشفافة)</label>
    <select class="in" id="mgTop"><option value="remotion">Remotion فوق HyperFrames</option><option value="hyperframes">HyperFrames فوق Remotion</option></select>
    <label class="l">شفافية الطبقة العلوية <span id="mgOpV">100%</span></label><input type="range" id="mgOp" min="10" max="100" value="100"></div>
   <div id="mgSeq" style="display:none"><label class="l">المقاطع (ثانية-ثانية محرك)</label>
    <textarea class="in" id="mgCuts" spellcheck="false" placeholder="0-4 hyperframes&#10;4-10 remotion"></textarea>
    <div class="srow"><span class="qc" id="mgAuto">تقسيم تلقائي متبادل</span></div>
    <label class="l">المحرك لأي فراغ</label><select class="in" id="mgDef"><option value="hyperframes">HyperFrames</option><option value="remotion">Remotion</option></select></div>
  </div>
  <div class="hint" id="engHint"></div>
  <button class="btn b2" id="prevBtn" type="button" style="display:none">▶ معاينة حية للتصميم (بدون رندر)</button></div>
 <div class="card" id="scriptCard"><h3><b>✦</b>السكربت ← فيديو</h3>
  <textarea class="in" id="sScript" rows="6" spellcheck="false" placeholder="الصق السكربت هنا (جملة بعد جملة). يُقسَّم تلقائياً لمشاهد: مقدمة · سؤال · رقم · خطوات · تشبيه · خلاصة — بقواعد ثابتة بدون ذكاء اصطناعي."></textarea>
  <input class="in" id="sSeries" placeholder="اسم السلسلة (يظهر أعلى الفيديو) — علوم ببساطة" style="margin-top:8px">
  <label class="l">الثيم</label>
  <select class="in" id="sTheme"><option value="sci">علمي داكن</option><option value="neon">نيون</option><option value="paper">ورقي فاتح</option><option value="gold">ذهبي فاخر</option></select>
  <div class="switch">تعليق صوتي من السكربت<div class="tg on" id="sVoiceTg"></div></div>
  <div class="switch">ترجمة كلمة بكلمة داخل التصميم<div class="tg on" id="sCapTg"></div></div>
  <button class="btn b1" id="sBuild" type="button">ابنِ التصميم من السكربت</button>
  <div class="sc-list" id="sList"></div><div class="hint" id="sInfo"></div></div>
 <div class="card" id="projCard"><h3><b>💾</b>المشروع</h3>
  <div class="row"><button class="btn b2" id="pjSave" type="button" style="margin-top:0">حفظ المشروع</button><button class="btn b2" id="pjLoad" type="button" style="margin-top:0">فتح مشروع</button></div>
  <input type="file" id="pjFile" accept=".json,application/json" hidden>
  <div class="hint">يحفظ: المحرك والأكواد والسكربت والإعدادات والتفريغ والتوقيتات، ليكمل العمل لاحقاً بدون إعادة تفريغ الصوت. ويُحفظ تلقائياً في المتصفح.</div></div>
"""

TABS = r"""<div class="tpl tab" id="tabR" style="display:none">Remotion · TSX</div><div class="tpl tab" id="tabH" style="display:none">HyperFrames · HTML</div><span id="hfTpls" style="display:none;gap:6px;align-items:center"><div class="tpl" data-h="hf_explainer">شرح علمي</div><div class="tpl" data-h="hf_captions">ترجمة كلمة بكلمة</div><div class="tpl" data-h="hf_title">عنوان</div><div class="tpl" data-h="merge_pro">دمج احترافي</div></span>"""

MODAL = r"""<div id="pvModal"><div id="pvBox"><iframe id="pvFrame" sandbox="allow-scripts"></iframe></div><div id="pvBar"><button id="pvPlay" type="button">❚❚</button><input type="range" id="pvSeek" min="0" max="1000" value="0"><span id="pvT">0.0s</span><button id="pvClose" type="button">إغلاق ✕</button></div></div>"""

PIPE = r"""<div class="pipe" id="pipe"><span data-s="script">سكربت</span><span data-s="voice">صوت</span><span data-s="timing">توقيت</span><span data-s="scenes">مشاهد</span><span data-s="render">رندر</span></div>"""

JS = r"""
/* ===== SAE: المحركات + السكربت + المشروع ===== */
const SAE={eng:'remotion',tab:'remotion',codes:{remotion:'',hyperframes:''},engines:null};
(function(){
 const HINTS={remotion:'Remotion: كود React/TSX — الأنسب للقوالب الغنية والانتقالات.',
  hyperframes:'HyperFrames: تركيبة HTML حتمية (data-start / data-duration أو window.drawFrame(t)) — رندر خفيف بلا حزم ثقيلة.',
  merge:'الدمج: اكتب/ولّد كوداً للمحركين (تبويبان فوق المحرر). «طبقات» = HyperFrames خلفية + Remotion شفاف فوقها، أو العكس. «تتابع» = كل مقطع زمني بمحرك.'};
 const origSave=window.save;
 function persist(){try{lsSet('sa_codes',JSON.stringify(SAE.codes));lsSet('sa_eng',SAE.eng);lsSet('sa_merge',JSON.stringify(mergeCfg(true)));lsSet('sa_script',$('sScript').value);lsSet('sa_series',$('sSeries').value)}catch(e){}}
 function sync(){SAE.codes[SAE.tab]=code.value}
 window.save=function(){sync();if(SAE.tab==='remotion'){origSave()}else{$('saved').textContent='saved';setTimeout(()=>$('saved').textContent='',1200)}persist()};
 function parseCuts(){const out=[];($('mgCuts').value||'').split(/\n+/).forEach(l=>{const m=l.trim().match(/^([\d.]+)\s*[-–—~]\s*([\d.]+)\s*(remotion|hyperframes|hf|rem|r|h)?/i);if(!m)return;
   const e=/^(h|hf|hyper)/i.test(m[3]||'')?'hyperframes':'remotion';out.push({from:+m[1],to:+m[2],engine:m[3]?e:$('mgDef').value})});return out}
 function mergeCfg(raw){return {mode:$('mgMode').value,top:$('mgTop').value,opacity:(+$('mgOp').value||100)/100,default:$('mgDef').value,cuts:raw?[]:parseCuts(),cutsText:$('mgCuts').value}}
 function paintTabs(){
  const e=SAE.eng,hf=e!=='remotion';
  $('tabR').style.display=e==='merge'?'inline-flex':'none';$('tabH').style.display=e==='merge'?'inline-flex':'none';
  $('tabR').classList.toggle('act2',SAE.tab==='remotion');$('tabH').classList.toggle('act2',SAE.tab==='hyperframes');
  $('hfTpls').style.display=hf?'inline-flex':'none';
  document.querySelectorAll('.tpl[data-t]').forEach(t=>t.style.display=SAE.tab==='remotion'?'':'none');
  const ph=document.querySelector('#p-code .ph');if(ph&&ph.lastChild)ph.lastChild.textContent=SAE.tab==='remotion'?'Motion.tsx':'composition.html';
 }
 async function setTab(t){sync();SAE.tab=t;code.value=SAE.codes[t]||'';if(t==='hyperframes'&&!code.value.trim())await loadHf('hf_explainer',true);paintTabs();persist()}
 async function setEngine(e,silent){
  sync();SAE.eng=e;document.querySelectorAll('#engs .eng').forEach(x=>x.classList.toggle('on',x.dataset.e===e));
  $('mergeBox').style.display=e==='merge'?'block':'none';$('prevBtn').style.display=e==='remotion'?'none':'block';$('engHint').textContent=HINTS[e];
  const want=e==='hyperframes'?'hyperframes':'remotion';SAE.tab=want;code.value=SAE.codes[want]||'';
  if(want==='hyperframes'&&!code.value.trim())await loadHf('hf_explainer',true);
  if(e==='merge'&&!(SAE.codes.hyperframes||'').trim()){try{const t=await (await api('/api/hf/template/hf_explainer')).text();SAE.codes.hyperframes=t}catch(x){}}
  paintTabs();persist();if(!silent)log('المحرك: '+({remotion:'Remotion',hyperframes:'HyperFrames',merge:'دمج (Remotion + HyperFrames)'})[e],'h')}
 async function loadHf(name,quiet){try{const t=await (await api('/api/hf/template/'+name)).text();
   if(name==='merge_pro'){const parts=t.split(/^\/\/@@ENGINE (remotion|hyperframes)\s*$/m);const m={};for(let i=1;i<parts.length;i+=2)m[parts[i]]=(parts[i+1]||'').replace(/^\n+|\n+$/g,'');
     SAE.codes.hyperframes=m.hyperframes||'';SAE.codes.remotion=m.remotion||'';if(SAE.eng!=='merge'){await setEngine('merge',true)}else{code.value=SAE.codes[SAE.tab]||'';paintTabs()}}
   else{SAE.codes.hyperframes=t;if(SAE.tab==='hyperframes'||SAE.eng==='hyperframes'){SAE.tab='hyperframes';code.value=t}}
   if(!quiet)log('تم تحميل القالب: '+name,'h');persist()}catch(e){log('فشل تحميل القالب: '+e.message,'e')}}
 document.querySelectorAll('#engs .eng').forEach(x=>x.onclick=()=>setEngine(x.dataset.e));
 $('tabR').onclick=()=>setTab('remotion');$('tabH').onclick=()=>setTab('hyperframes');
 document.querySelectorAll('.tpl[data-h]').forEach(t=>t.onclick=()=>{if(SAE.tab==='hyperframes'&&code.value.trim()&&t.dataset.h!=='merge_pro'&&!confirm('استبدال الكود الحالي؟'))return;if(t.dataset.h!=='merge_pro'&&SAE.eng==='remotion')return setEngine('hyperframes',true).then(()=>loadHf(t.dataset.h));loadHf(t.dataset.h)});
 // فحص الكود: HTML → فحص HyperFrames، وإلا الفاحص الأصلي
 const origCheck=$('checkBtn').onclick;
 $('checkBtn').onclick=async function(){ if(SAE.tab!=='hyperframes')return origCheck&&origCheck.apply(this,arguments);
  if(!code.value.trim())return log('الكود فارغ','e');status('فحص',1);
  try{const r=await (await postJ('/api/hf/check',{code:code.value})).json();(r.notes||[]).forEach(n=>log(n,/^تنبيه/.test(n)?'h':'e'));if(r.ok)log('كود HyperFrames سليم','s')}catch(e){log('فشل الفحص: '+e.message,'e')}status('جاهز')};
 // دمج: عناصر التحكم
 function paintMerge(){const seq=$('mgMode').value==='sequence';$('mgLayers').style.display=seq?'none':'block';$('mgSeq').style.display=seq?'block':'none';$('mgOpV').textContent=$('mgOp').value+'%';persist()}
 $('mgMode').onchange=paintMerge;$('mgTop').onchange=persist;$('mgDef').onchange=persist;$('mgOp').oninput=paintMerge;$('mgCuts').oninput=persist;
 $('mgAuto').onclick=()=>{const d=getDur(),n=Math.max(2,Math.min(6,Math.round(d/4))),st=d/n;let o=[];for(let i=0;i<n;i++)o.push(`${(i*st).toFixed(1)}-${((i+1)*st).toFixed(1)} ${i%2?'remotion':'hyperframes'}`);$('mgCuts').value=o.join('\n');persist()};
 // الطلب: يُضاف المحرك والأكواد
 SAE.decorate=function(b){sync();b.engine=SAE.eng;
  if(SAE.eng==='hyperframes'){b.code=SAE.codes.hyperframes;b.hf_code=SAE.codes.hyperframes}
  else if(SAE.eng==='merge'){b.code=SAE.codes.remotion;b.hf_code=SAE.codes.hyperframes;b.merge=mergeCfg(false)}
  return b};
 // السكربت ← تصميم
 $('sVoiceTg').onclick=()=>$('sVoiceTg').classList.toggle('on');$('sCapTg').onclick=()=>$('sCapTg').classList.toggle('on');
 $('sScript').oninput=persist;$('sSeries').oninput=persist;
 $('sBuild').onclick=async()=>{const sc=$('sScript').value.trim();if(!sc)return log('اكتب السكربت أولاً','e');
  if(SAE.codes[SAE.tab]&&code.value.trim()&&!confirm('سيُستبدل الكود الحالي بتصميم مبني من السكربت. متابعة؟'))return;
  $('sBuild').disabled=true;status('بناء من السكربت',1);
  try{const r=await (await postJ('/api/script/build',{script:sc,engine:SAE.eng,series:$('sSeries').value.trim(),voice:$('sVoiceTg').classList.contains('on'),captions:$('sCapTg').classList.contains('on'),theme:$('sTheme').value})).json();
   if(SAE.eng==='hyperframes'){SAE.codes.hyperframes=r.hf;SAE.tab='hyperframes'}
   else if(SAE.eng==='merge'){SAE.codes.hyperframes=r.hf;SAE.codes.remotion=r.remotion;SAE.tab='hyperframes'}
   else{SAE.codes.remotion=r.code;SAE.tab='remotion'}
   code.value=SAE.codes[SAE.tab];paintTabs();window.save();
   const d=Math.max(3,Math.ceil(r.seconds_estimate+1.2));$('dur').value=d;try{saveCfg();syncTime()}catch(e){}
   const names={intro:'مقدمة',question:'سؤال',stat:'رقم',flow:'خطوات',concept:'مفهوم',cards:'نقاط',recap:'خلاصة',compare:'مقارنة',cycle:'دورة'};
   $('sList').innerHTML=r.scenes.map((s,i)=>`<span>${i+1}· ${names[s.type]||s.type}</span>`).join('');
   $('sInfo').textContent=`${r.scenes.length} مشاهد · ${r.words} كلمة · ~${r.seconds_estimate}ث (المدة ضُبطت تلقائياً). ${$('sVoiceTg').classList.contains('on')?'الصوت يُولَّد عند الرندر من NARRATION والمشاهد تتزامن مع نطق كل جملة.':'بدون صوت مولّد: ارفع صوتك وفرّغه لتتزامن المشاهد مع الكلمات.'}`;
   log(`بُني التصميم من السكربت: ${r.scenes.length} مشاهد`,'s')}catch(e){log(e.message,'e')}
  $('sBuild').disabled=false;status('جاهز')};
 // المشروع: حفظ/فتح
 $('pjSave').onclick=()=>{sync();const P={v:1,engine:SAE.eng,codes:SAE.codes,merge:mergeCfg(true),script:$('sScript').value,series:$('sSeries').value,cfg:JSON.parse(lsGet('sa_cfg')||'{}'),words:S.words||[],segments:S.segments||[]};
  const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(P)],{type:'application/json'}));a.download='project.samotion.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),4000);log('حُفظ المشروع (يتضمن التفريغ والتوقيتات)','s')};
 $('pjLoad').onclick=()=>$('pjFile').click();
 $('pjFile').onchange=async e=>{const f=e.target.files[0];e.target.value='';if(!f)return;try{const P=JSON.parse(await f.text());if(!P||P.v!==1)throw new Error('ملف مشروع غير صالح');
   SAE.codes=Object.assign({remotion:'',hyperframes:''},P.codes||{});$('sScript').value=P.script||'';$('sSeries').value=P.series||'';
   const m=P.merge||{};if(m.mode)$('mgMode').value=m.mode;if(m.top)$('mgTop').value=m.top;if(m.default)$('mgDef').value=m.default;$('mgOp').value=Math.round((m.opacity||1)*100);$('mgCuts').value=m.cutsText||'';paintMerge();
   if(P.cfg){lsSet('sa_cfg',JSON.stringify(P.cfg));try{loadCfg();syncTime()}catch(x){}}
   S.words=P.words||[];S.segments=P.segments||[];await setEngine(P.engine||'remotion',true);log(`فُتح المشروع · ${S.segments.length} سطر ترجمة`,'s')}catch(x){log('تعذّر فتح المشروع: '+x.message,'e')}};
 // شريط الخطوات يتبع نص التقدّم الموجود أصلاً
 const STEPS=['script','voice','timing','scenes','render'];
 function pipe(stage){let cur=-1;const s=stage||'';
  if(/(توليد الصوت|الصوت من الكود)/.test(s))cur=1;else if(/(تفريغ|مزامنة|توقيت)/.test(s))cur=2;else if(/(تجميع|تحميل الخطوط|تحضير|فحص|تجهيز الملفات)/.test(s))cur=3;else if(/(رندر|طبقة|مقطع|دمج|تركيب|مزج|مؤثرات)/.test(s))cur=4;else if(s)cur=0;
  document.querySelectorAll('#pipe span').forEach((x,i)=>{x.classList.toggle('on',i===cur);x.classList.toggle('done',cur>i)})}
 new MutationObserver(()=>pipe($('ovT').textContent)).observe($('ovT'),{childList:true,characterData:true,subtree:true});
 // معاينة حية: iframe معزول، والزمن يُدار من هنا عبر postMessage
 const PV={on:false,t:0,play:true,busy:false,ready:false,dur:5,fps:30,w:1080,h:1920,raf:0,last:0};
 function pvFit(){const box=$('pvBox'),mw=Math.min(innerWidth*.94,560),mh=innerHeight*.74,s=Math.min(mw/PV.w,mh/PV.h);box.style.width=(PV.w*s)+'px';box.style.height=(PV.h*s)+'px';const f=$('pvFrame');f.style.width=PV.w+'px';f.style.height=PV.h+'px';f.style.transform='scale('+s+')'}
 function pvSeek(t){if(!PV.ready||PV.busy)return;PV.busy=true;$('pvFrame').contentWindow.postMessage({k:'seek',t:t},'*')}
 function pvLoop(ts){if(!PV.on)return;if(PV.play&&PV.ready){const dt=PV.last?(ts-PV.last)/1000:0;PV.t+=dt;if(PV.t>=PV.dur)PV.t=0}PV.last=ts;
  if(PV.ready){pvSeek(PV.t);$('pvSeek').value=Math.round(PV.t/PV.dur*1000);$('pvT').textContent=PV.t.toFixed(1)+'s / '+PV.dur.toFixed(1)+'s'}PV.raf=requestAnimationFrame(pvLoop)}
 addEventListener('message',e=>{const m=e.data||{};if(!PV.on)return;
  if(m.k==='loaded'){$('pvFrame').contentWindow.postMessage({k:'init',fps:PV.fps,total:Math.round(PV.dur*PV.fps),props:{words:S.words||[],segments:S.segments||[]}},'*')}
  else if(m.k==='ready'){PV.ready=true;PV.busy=false}else if(m.k==='seeked'){PV.busy=false}});
 $('prevBtn').onclick=async()=>{sync();const html=SAE.codes.hyperframes;if(!(html||'').trim())return log('لا يوجد كود HyperFrames للمعاينة','e');
  try{const cfg=JSON.parse(lsGet('sa_cfg')||'{}');PV.w=+(cfg.width||1080);PV.h=+(cfg.height||1920)}catch(e){}
  PV.dur=Math.max(1,getDur());PV.fps=30;PV.t=0;PV.ready=false;PV.busy=false;PV.last=0;PV.play=true;$('pvPlay').textContent='❚❚';
  try{const r=await (await postJ('/api/hf/preview',{code:html,width:PV.w,height:PV.h,words:S.words||[],segments:S.segments||[]})).json();
   (r.notes||[]).forEach(n=>log(n,'h'));PV.on=true;$('pvModal').classList.add('on');pvFit();$('pvFrame').srcdoc=r.html;cancelAnimationFrame(PV.raf);PV.raf=requestAnimationFrame(pvLoop)}catch(e){log('تعذّرت المعاينة: '+e.message,'e')}};
 $('pvPlay').onclick=()=>{PV.play=!PV.play;$('pvPlay').textContent=PV.play?'❚❚':'▶'};
 $('pvSeek').oninput=()=>{PV.t=$('pvSeek').value/1000*PV.dur};
 $('pvClose').onclick=()=>{PV.on=false;cancelAnimationFrame(PV.raf);$('pvModal').classList.remove('on');$('pvFrame').srcdoc=''};
 addEventListener('resize',()=>{if(PV.on)pvFit()});
 // تهيئة
 (function init(){let c={};try{c=JSON.parse(lsGet('sa_codes')||'{}')}catch(e){}
  SAE.codes.remotion=code.value;SAE.codes.hyperframes=c.hyperframes||'';
  try{const m=JSON.parse(lsGet('sa_merge')||'{}');if(m.mode)$('mgMode').value=m.mode;if(m.top)$('mgTop').value=m.top;if(m.default)$('mgDef').value=m.default;if(m.opacity)$('mgOp').value=Math.round(m.opacity*100);$('mgCuts').value=m.cutsText||''}catch(e){}
  $('sTheme').value=lsGet('sa_theme')||'sci';$('sTheme').onchange=()=>lsSet('sa_theme',$('sTheme').value);
  $('sScript').value=lsGet('sa_script')||'';$('sSeries').value=lsGet('sa_series')||'';paintMerge();
  setEngine(lsGet('sa_eng')||'remotion',true);
  api('/api/engines').then(r=>r.json()).then(j=>{SAE.engines=j;j.engines.forEach(e=>{const n=document.querySelector(`#engs .eng[data-e="${e.id}"]`);if(n&&!e.ready){n.classList.add('off');n.title='غير جاهز: '+(e.why||'تحقق من ffmpeg والمتصفح');if(e.why&&!SAE._warned){SAE._warned=1;log('HyperFrames غير جاهز: '+e.why,'e')}}})}).catch(()=>{});
 })();
})();
"""


def inject(html):
    """يحقن الواجهة في index.html؛ إن لم تُوجد نقطة الربط يترك الصفحة كما هي (لا يكسر شيئاً)."""
    def put(s, anchor, text, before=True, count=1):
        i = s.find(anchor)
        if i < 0:
            print("⚠ sa_engines_ui: نقطة الربط غير موجودة:", anchor[:40], flush=True)
            return s
        j = i if before else i + len(anchor)
        return s[:j] + text + s[j:]

    h = html
    h = put(h, "</style></head>", CSS)
    h = put(h, '<div class="scroll">\n', CARDS, before=False)
    h = put(h, '<div class="tpls">', TABS, before=False)
    h = put(h, '<div class="pct" id="ovP">0%</div>', PIPE, before=True)
    h = put(h, "<body>", MODAL, before=False)
    h = put(h, "</script></body></html>", JS)
    # الطلب: يمرّ عبر SAE.decorate
    a = "const body={mode,time:t,code:code.value,"
    if a in h:
        h = h.replace(a, "let body={mode,time:t,code:code.value,", 1)
        b = "style:$('musicStyle').value}};"
        k = h.find(b, h.find("let body={mode,time:t"))
        if k >= 0:
            h = h[:k + len(b)] + "body=window.SAE?SAE.decorate(body):body;" + h[k + len(b):]
        else:
            print("⚠ sa_engines_ui: نهاية جسم الطلب غير موجودة", flush=True)
    else:
        print("⚠ sa_engines_ui: بداية جسم الطلب غير موجودة", flush=True)
    return h
