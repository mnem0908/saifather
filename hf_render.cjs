// SA Motion Studio — HyperFrames engine renderer (v2).
// تركيبة HTML حتمية → إطارات (Chromium) → ffmpeg. الميزات: اكتشاف المتصفح تلقائياً، رندر متوازٍ، عزل الشبكة، مهلة لكل إطار.
// node hf_render.cjs spec.json   |   node hf_render.cjs --probe
const fs = require("fs");
const os = require("os");
const path = require("path");
const http = require("http");
const { spawn } = require("child_process");

const PROBE = process.argv[2] === "--probe";
const spec = PROBE ? { root: process.cwd() } : JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const emit = (o) => process.stdout.write("@@" + JSON.stringify(o) + "\n");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml",
  ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif", ".mp4": "video/mp4", ".webm": "video/webm",
  ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4", ".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf", ".otf": "font/otf" };
// الشبكة: مسموح فقط الخادم المحلي + عناوين data/blob + هذه المضيفات (خطوط ومكتبات شائعة). كل ما عداها يُحجب (حماية SSRF).
const NET_ALLOW = new Set(["fonts.googleapis.com", "fonts.gstatic.com", "cdnjs.cloudflare.com", "cdn.jsdelivr.net"]);

function tryRequire(names) {
  const bases = [spec.root, __dirname, process.cwd(), ...(process.env.NODE_PATH || "").split(path.delimiter).filter(Boolean)];
  for (const n of names) for (const base of bases) { try { return require(require.resolve(n, { paths: [base || "."] })); } catch (e) {} }
  return null;
}

function walk(dir, depth, test, out) {
  if (depth < 0) return;
  let ents; try { ents = fs.readdirSync(dir, { withFileTypes: true }); } catch (e) { return; }
  for (const e of ents) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, depth - 1, test, out);
    else if (test(e.name, p)) out.push(p);
  }
}

// يبحث عن Chrome بالترتيب: متغيّر بيئة ← متصفح Remotion المثبّت ← ms-playwright ← مسارات النظام
function findChrome() {
  const env = process.env.SA_CHROME || process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE;
  if (env && fs.existsSync(env)) return env;
  const found = [];
  const isBin = (n) => n === "chrome-headless-shell" || n === "chrome" || n === "headless_shell";
  for (const base of [spec.root, __dirname, process.cwd()]) {
    if (!base) continue;
    walk(path.join(base, "node_modules", ".remotion"), 6, isBin, found);
  }
  const pwRoots = [process.env.PLAYWRIGHT_BROWSERS_PATH, path.join(os.homedir(), ".cache", "ms-playwright"), "/opt/pw-browsers"].filter(Boolean);
  for (const r of pwRoots) walk(r, 4, (n) => n === "chrome-headless-shell" || n === "chrome", found);
  if (found.length) return found.sort((a, b) => (/headless/.test(b) ? 1 : 0) - (/headless/.test(a) ? 1 : 0))[0];
  for (const p of ["/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/snap/bin/chromium",
    "/data/data/com.termux/files/usr/bin/chromium", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"]) if (fs.existsSync(p)) return p;
  return null;
}

async function launchBrowser() {
  const pw = tryRequire(["playwright-core", "playwright"]);
  if (!pw || !pw.chromium) throw new Error("حزمة playwright-core غير مثبتة. شغّل: npm install playwright-core --no-audit --no-fund");
  const exe = findChrome();
  const opts = { headless: true, args: ["--no-sandbox", "--disable-dev-shm-usage", "--hide-scrollbars", "--force-color-profile=srgb", "--font-render-hinting=none",
    "--autoplay-policy=no-user-gesture-required", "--disable-gpu-vsync", "--disable-background-timer-throttling", "--disable-renderer-backgrounding"] };
  if (exe) opts.executablePath = exe;
  try { return { browser: await pw.chromium.launch(opts), exe: exe || "playwright" }; }
  catch (e) { throw new Error("تعذّر تشغيل المتصفح" + (exe ? " (" + exe + ")" : "") + ": " + String(e.message).split("\n")[0].slice(0, 220)); }
}

if (PROBE) {
  (async () => {
    try { const h = await launchBrowser(); await h.browser.close(); process.stdout.write(JSON.stringify({ ok: true, browser: h.exe }) + "\n"); process.exit(0); }
    catch (e) { process.stdout.write(JSON.stringify({ ok: false, error: String(e.message) }) + "\n"); process.exit(0); }
  })();
  return;
}

function startServer() {
  const pub = spec.publicDir || path.join(spec.root || ".", "public");
  const fontsDir = spec.fontsDir || null;
  const vendor = {};
  for (const base of [spec.root, __dirname, process.cwd()]) {
    const p = path.join(base || ".", "node_modules", "gsap", "dist", "gsap.min.js");
    if (fs.existsSync(p)) { vendor["/__vendor/gsap.min.js"] = p; break; }
  }
  const srv = http.createServer((req, res) => {
    const u = decodeURIComponent((req.url || "/").split("?")[0]);
    if (u === "/__comp.html") { res.writeHead(200, { "Content-Type": MIME[".html"], "Cache-Control": "no-store" }); return res.end(spec.html); }
    let file = vendor[u];
    if (!file && fontsDir && u.startsWith("/__fonts/")) {
      file = path.join(fontsDir, path.basename(u));
    }
    if (!file) {
      const safe = path.normalize(u).replace(/^([/\\])+/, "");
      file = path.join(pub, safe);
      if (!path.resolve(file).startsWith(path.resolve(pub))) { res.writeHead(403); return res.end(); }
    }
    fs.stat(file, (err, st) => {
      if (err || !st.isFile()) { res.writeHead(404); return res.end("not found"); }
      const type = MIME[path.extname(file).toLowerCase()] || "application/octet-stream";
      const range = req.headers.range;
      if (range) {
        const m = /bytes=(\d*)-(\d*)/.exec(range) || [];
        const start = m[1] ? parseInt(m[1], 10) : 0, end = m[2] ? parseInt(m[2], 10) : st.size - 1;
        res.writeHead(206, { "Content-Type": type, "Content-Range": `bytes ${start}-${end}/${st.size}`, "Accept-Ranges": "bytes", "Content-Length": end - start + 1 });
        return fs.createReadStream(file, { start, end }).pipe(res);
      }
      res.writeHead(200, { "Content-Type": type, "Content-Length": st.size, "Accept-Ranges": "bytes" });
      fs.createReadStream(file).pipe(res);
    });
  });
  return new Promise((ok) => srv.listen(0, "127.0.0.1", () => ok({ srv, port: srv.address().port })));
}

function withTimeout(p, ms, msg) {
  let t; return Promise.race([p, new Promise((_, rej) => { t = setTimeout(() => rej(new Error(msg)), ms); })]).finally(() => clearTimeout(t));
}

async function openPage(browser, port, W, H, errs) {
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1, javaScriptEnabled: true, acceptDownloads: false });
  await ctx.route("**/*", (route) => {
    const u = route.request().url();
    if (u.startsWith("data:") || u.startsWith("blob:") || u.startsWith("about:") || u.startsWith(`http://127.0.0.1:${port}/`)) return route.continue();
    try { const h = new URL(u); if (h.protocol === "https:" && NET_ALLOW.has(h.hostname)) return route.continue(); } catch (e) {}
    return route.abort("blockedbyclient");
  });
  const page = await ctx.newPage();
  page.on("console", (m) => { if (m.type() === "error") emit({ stage: "log", text: String(m.text()).slice(0, 400) }); });
  page.on("pageerror", (e) => { errs.push(String(e.message || e)); emit({ stage: "log", text: "JS: " + String(e.message || e).slice(0, 400) }); });
  await page.goto(`http://127.0.0.1:${port}/__comp.html`, { waitUntil: "load", timeout: 120000 });
  await page.evaluate(() => (document.fonts && document.fonts.ready) ? document.fonts.ready.then(() => 1) : 1);
  const info = await withTimeout(page.evaluate(async (P) => {
    if (!window.__sa || !window.__sa.ready) return { ok: false, why: "runtime missing" };
    await window.__sa.ready(P); return { ok: true };
  }, { fps: spec.fps, total: spec.frames, props: spec.props || {} }), 60000, "انتهت مهلة تهيئة التركيبة (60ث) — تحقق من الوسائط والسكربتات");
  if (!info.ok) throw new Error("وقت تشغيل HyperFrames غير موجود في التركيبة: " + (info.why || ""));
  return page;
}

(async () => {
  let h = null, server = null, ff = null, failed = null;
  try {
    const W = spec.width, H = spec.height, fps = spec.fps, total = spec.frames, alpha = !!spec.alpha;
    emit({ stage: "compose" });
    server = await startServer();
    h = await launchBrowser();
    const errs = [];
    const shotOpts = alpha ? { type: "png", omitBackground: true } : { type: "jpeg", quality: spec.quality || 92 };
    const seekShot = (page, f) => withTimeout(page.evaluate(async (tt) => { await window.__sa.seek(tt); }, f / fps).then(() => page.screenshot(shotOpts)), (spec.frameTimeout || 90000),
      "انتهت مهلة الإطار " + f + " (" + Math.round((spec.frameTimeout || 90000) / 1000) + "ث): الكود يعلق — ابحث عن حلقة لا نهائية أو وسائط لا تُحمَّل");

    if (spec.mode === "still") {
      const pg = await openPage(h.browser, server.port, W, H, errs);
      fs.writeFileSync(spec.output, await seekShot(pg, Math.min(spec.frame || 0, total - 1)));
      emit({ stage: "done" }); return;
    }

    const f0 = Math.max(0, spec.startFrame || 0), f1 = Math.min(total, spec.endFrame || total), span = Math.max(1, f1 - f0);
    const N = Math.max(1, Math.min(spec.workers || 1, 6, span));
    const pages = [];
    for (let i = 0; i < N; i++) pages.push(await openPage(h.browser, server.port, W, H, errs));
    emit({ stage: "log", text: `HyperFrames: ${N} عامل متوازٍ · ${W}×${H} · ${span} إطار` });

    const args = ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(fps), "-vcodec", alpha ? "png" : "mjpeg", "-i", "-"];
    if (alpha) args.push("-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", String(Math.max(18, spec.crf || 22)), "-auto-alt-ref", "0", "-row-mt", "1", "-deadline", "realtime", "-cpu-used", "5", spec.output);
    else args.push("-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", spec.preset || "medium", "-crf", String(spec.crf || 18), "-movflags", "+faststart", "-r", String(fps), spec.output);
    ff = spawn(spec.ffmpeg || "ffmpeg", args, { stdio: ["pipe", "ignore", "pipe"] });
    let ffErr = ""; ff.stderr.on("data", (d) => { ffErr += d.toString(); ffErr = ffErr.slice(-3000); });
    const ffDone = new Promise((ok) => ff.on("close", (c) => ok(c)));
    ff.stdin.on("error", () => {});

    // عمّال يرندرون إطارات مختلفة بالتوازي، والكاتب يرسلها لـ ffmpeg بالترتيب الصحيح
    const bufs = new Map(); let nextF = f0, writeF = f0; const AHEAD = N * 4; const t0 = Date.now();
    const workers = pages.map(async (pg) => {
      while (!failed) {
        if (nextF >= f1) return;
        if (nextF - writeF >= AHEAD) { await sleep(4); continue; }
        const f = nextF++;
        try { bufs.set(f, await seekShot(pg, f)); } catch (e) { failed = failed || e; return; }
      }
    });
    let last = -1;
    for (let f = f0; f < f1; f++) {
      while (!bufs.has(f)) { if (failed) throw failed; await sleep(2); }
      const buf = bufs.get(f); bufs.delete(f); writeF = f + 1;
      if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
      const v = Math.floor(((f + 1 - f0) / span) * 100);
      if (v !== last || f === f1 - 1) {
        last = v; const el = (Date.now() - t0) / 1000;
        emit({ stage: "render", progress: (f + 1 - f0) / span, rendered: f + 1 - f0, total: span, fps: el > 0.5 ? Math.round(((f + 1 - f0) / el) * 10) / 10 : 0, stitch: "" });
      }
    }
    await Promise.all(workers);
    if (failed) throw failed;
    ff.stdin.end();
    const code = await ffDone;
    if (code !== 0) throw new Error("ffmpeg فشل: " + ffErr);
    emit({ stage: "done", seconds: (Date.now() - t0) / 1000 });
  } catch (e) {
    emit({ stage: "error", text: String((e && (e.stack || e.message)) || e).slice(0, 6000) }); process.exitCode = 1;
  } finally {
    try { if (ff && !ff.killed) ff.kill("SIGKILL"); } catch (_) {}
    try { if (h) await withTimeout(h.browser.close(), 5000, "close"); } catch (_) {}
    try { if (server) server.srv.close(); } catch (_) {}
    setTimeout(() => process.exit(process.exitCode || 0), 200);
  }
})();
