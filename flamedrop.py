import argparse
import hmac
import json
import os
import re
import secrets
import shutil
import socket
import sys
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, unquote, urlparse

BLOCKED_EXT = frozenset(
    {".exe", ".bat", ".cmd", ".com", ".scr", ".msi", ".ps1", ".vbs", ".dll", ".jar"}
)
COOKIE_NAME = "fd_session"
MAX_CODE_FAILURES = 5
WRITE_LOCK = threading.Lock()

PAGE = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n<meta name="color-scheme" content="light dark">\n<title>FlameDrop</title>\n<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 64 64\'%3E%3Crect width=\'64\' height=\'64\' rx=\'14\' fill=\'%23e8590c\'/%3E%3Cpath fill=\'%23fff\' d=\'M34 10c2 10 12 15 12 28a14 14 0 0 1-28 0c0-7 3-10 6-13 1 4 3 6 5 7-2-8 0-16 5-22z\'/%3E%3C/svg%3E">\n<style>\n:root{\n  --bg:#f4f5f7;--surface:#ffffff;--surface-2:#f9fafb;--line:#e4e7ec;--line-strong:#d0d5dd;\n  --ink:#101828;--ink-2:#344054;--muted:#667085;\n  --accent:#e8590c;--accent-hover:#cf4f0a;--accent-ink:#ffffff;--accent-soft:#fff1e8;\n  --ok:#067647;--bad:#b42318;--warn:#b54708;--warn-soft:#fffaeb;\n  --shadow:0 1px 2px rgba(16,24,40,.05);\n}\n@media (prefers-color-scheme:dark){\n  :root{\n    --bg:#0c0f13;--surface:#14181e;--surface-2:#191e25;--line:#252b34;--line-strong:#333b47;\n    --ink:#f2f4f7;--ink-2:#d0d5dd;--muted:#98a2b3;\n    --accent:#ff7a2e;--accent-hover:#ff8f4d;--accent-ink:#1a0d03;--accent-soft:#2b1a0f;\n    --ok:#47cd89;--bad:#f97066;--warn:#fdb022;--warn-soft:#2b2008;\n    --shadow:none;\n  }\n}\n*{box-sizing:border-box}\n[hidden]{display:none!important}\nhtml{-webkit-text-size-adjust:100%}\nbody{\n  margin:0;min-height:100vh;background:var(--bg);color:var(--ink);\n  font:14px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;\n  -webkit-font-smoothing:antialiased;\n}\nh1,h2,p,ul{margin:0}\nul{list-style:none;padding:0}\n:focus-visible{outline:2px solid var(--accent);outline-offset:2px}\n.sprite{position:absolute;width:0;height:0;overflow:hidden}\n.ic{\n  width:18px;height:18px;flex:none;fill:none;stroke:currentColor;\n  stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round;\n}\n\n.top{position:sticky;top:0;z-index:5;background:var(--surface);border-bottom:1px solid var(--line)}\n.top-in{\n  max-width:960px;height:60px;margin:0 auto;padding:0 20px;\n  display:flex;align-items:center;justify-content:space-between;gap:12px;\n}\n.brand{display:flex;align-items:center;gap:10px;font-size:17px;font-weight:650;letter-spacing:-.01em}\n.logo{width:30px;height:30px;border-radius:8px;background:var(--accent);display:grid;place-items:center}\n.logo svg{width:18px;height:18px;fill:var(--accent-ink)}\n.top-actions{display:flex;align-items:center;gap:8px}\n.pill{\n  display:inline-flex;align-items:center;gap:6px;height:32px;padding:0 12px;\n  border:1px solid var(--line);border-radius:999px;background:var(--surface-2);\n  color:var(--ink-2);font-size:13px;font-variant-numeric:tabular-nums;\n}\n.pill.warn{color:var(--warn);background:var(--warn-soft);border-color:transparent}\n\nmain{max-width:960px;margin:0 auto;padding:28px 20px 56px}\n.page-head{margin-bottom:20px}\n.page-head h1{font-size:24px;line-height:1.25;font-weight:650;letter-spacing:-.02em}\n.sub{margin-top:4px;color:var(--muted)}\n\n.btn{\n  display:inline-flex;align-items:center;justify-content:center;gap:8px;\n  height:36px;padding:0 14px;border:1px solid transparent;border-radius:8px;\n  font:inherit;font-size:14px;font-weight:600;white-space:nowrap;text-decoration:none;cursor:pointer;\n  transition:background-color .15s,border-color .15s,color .15s;\n}\n.btn.primary{background:var(--accent);color:var(--accent-ink)}\n.btn.primary:hover{background:var(--accent-hover)}\n.btn.ghost{background:var(--surface);color:var(--ink-2);border-color:var(--line-strong)}\n.btn.ghost:hover{background:var(--surface-2)}\n.btn.text{height:30px;padding:0 10px;background:transparent;color:var(--muted);font-weight:500}\n.btn.text:hover{background:var(--surface-2);color:var(--ink)}\n.btn.sm{height:32px;padding:0 12px;font-size:13px}\n.btn.block{width:100%;height:44px}\n.btn:disabled{opacity:.6;cursor:default}\n.icon-btn{\n  width:32px;height:32px;flex:none;display:grid;place-items:center;border:0;border-radius:8px;\n  background:transparent;color:var(--muted);cursor:pointer;\n}\n.icon-btn:hover{background:var(--surface-2);color:var(--ink)}\n\n.auth{display:flex;justify-content:center;padding-top:6vh}\n.auth-card{\n  width:100%;max-width:400px;padding:32px 28px;border:1px solid var(--line);border-radius:14px;\n  background:var(--surface);box-shadow:0 8px 24px rgba(16,24,40,.06);\n}\n.auth-icon{\n  width:44px;height:44px;margin-bottom:18px;display:grid;place-items:center;\n  border-radius:10px;background:var(--accent-soft);color:var(--accent);\n}\n.auth-icon .ic{width:22px;height:22px}\n.auth-card h1{font-size:20px;font-weight:650;letter-spacing:-.01em}\n.auth-card .sub{margin-bottom:22px}\n.field{display:block;margin-bottom:6px;font-size:13px;font-weight:600;color:var(--ink-2)}\n#code{\n  width:100%;height:56px;border:1px solid var(--line-strong);border-radius:8px;\n  background:var(--surface);color:var(--ink);text-align:center;text-indent:.5em;letter-spacing:.5em;\n  font:600 26px/1 ui-monospace,"SF Mono",Menlo,Consolas,monospace;\n}\n#code::placeholder{color:var(--line-strong)}\n#code:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 4px var(--accent-soft)}\n.auth-card .btn{margin-top:14px}\n.err{min-height:20px;margin-top:12px;color:var(--bad);font-size:13px}\n.facts{\n  display:grid;gap:6px;margin-top:18px;padding-top:18px;border-top:1px solid var(--line);\n  color:var(--muted);font-size:13px;\n}\n\n.callout{\n  display:flex;align-items:center;flex-wrap:wrap;gap:8px 20px;margin-bottom:20px;padding:16px 20px;\n  border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:10px;\n  background:var(--surface);box-shadow:var(--shadow);\n}\n.callout-text{flex:1;min-width:200px}\n.callout-title{font-weight:600}\n.callout-text p{color:var(--muted);font-size:13px}\n.digits{\n  font:700 30px/1.2 ui-monospace,"SF Mono",Menlo,Consolas,monospace;\n  letter-spacing:.12em;font-variant-numeric:tabular-nums;\n}\n.callout .icon-btn{align-self:flex-start}\n\n.card{\n  margin-bottom:20px;overflow:hidden;border:1px solid var(--line);border-radius:10px;\n  background:var(--surface);box-shadow:var(--shadow);\n}\n.card-head{\n  display:flex;align-items:center;justify-content:space-between;gap:12px;\n  padding:12px 20px;min-height:54px;border-bottom:1px solid var(--line);\n}\n.card-head h2{font-size:15px;font-weight:600}\n.count{\n  margin-left:6px;padding:1px 8px;border:1px solid var(--line);border-radius:999px;\n  background:var(--surface-2);color:var(--muted);font-size:12px;font-weight:500;\n}\n.count:empty{display:none}\n\n.drop{\n  display:flex;flex-direction:column;align-items:center;gap:6px;margin:16px 20px;padding:32px 16px;\n  border:1.5px dashed var(--line-strong);border-radius:10px;background:var(--surface-2);\n  text-align:center;cursor:pointer;transition:border-color .15s,background-color .15s;\n}\n.drop:hover,.drop.over{border-color:var(--accent);background:var(--accent-soft)}\n.drop:focus-within{outline:2px solid var(--accent);outline-offset:2px}\n.drop-icon{\n  width:44px;height:44px;margin-bottom:4px;display:grid;place-items:center;\n  border:1px solid var(--line);border-radius:50%;background:var(--surface);color:var(--accent);\n}\n.drop-title{font-size:15px;font-weight:600}\n.drop-title u{color:var(--accent);text-underline-offset:3px}\n.drop-sub{color:var(--muted);font-size:13px}\n\n.queue:empty{display:none}\n.qitem{display:flex;align-items:center;gap:12px;padding:12px 20px;border-top:1px solid var(--line)}\n.qmain{flex:1;min-width:0}\n.qtop{display:flex;justify-content:space-between;align-items:baseline;gap:12px}\n.name{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:550}\n.state{flex:none;color:var(--muted);font-size:13px;font-variant-numeric:tabular-nums}\n.state.ok{color:var(--ok)}\n.state.bad{color:var(--bad)}\n.track{height:6px;margin-top:8px;overflow:hidden;border-radius:3px;background:var(--line)}\n.track i{display:block;width:0;height:100%;border-radius:3px;background:var(--accent)}\n.track.done i{background:var(--ok)}\n.qsub{margin-top:4px;color:var(--muted);font-size:12px;font-variant-numeric:tabular-nums}\n\n.badge{\n  --c:#667085;flex:none;width:40px;height:40px;display:grid;place-items:center;\n  border-radius:8px;background:var(--surface-2);color:var(--c);\n  font-size:11px;font-weight:700;letter-spacing:.02em;\n  background:color-mix(in srgb,var(--c) 14%,var(--surface));\n}\n.k-image{--c:#3b82f6}\n.k-video{--c:#8b5cf6}\n.k-audio{--c:#ec4899}\n.k-doc{--c:#ef4444}\n.k-sheet{--c:#10b981}\n.k-slide{--c:#f59e0b}\n.k-archive{--c:#14b8a6}\n\n.thead,.frow{\n  display:grid;grid-template-columns:minmax(0,1fr) 90px 150px 118px;\n  align-items:center;gap:16px;padding:0 20px;\n}\n.thead{height:36px;border-bottom:1px solid var(--line);background:var(--surface-2);color:var(--muted);font-size:12px;font-weight:600}\n.frow{min-height:64px;border-bottom:1px solid var(--line)}\n.frow:last-child{border-bottom:0}\n.frow:hover{background:var(--surface-2)}\n.fname{display:flex;align-items:center;gap:12px;min-width:0}\n.ftext{display:flex;flex-direction:column;min-width:0}\n.fmeta{display:none;gap:10px;color:var(--muted);font-size:12px}\n.fsize,.fdate{color:var(--ink-2);font-variant-numeric:tabular-nums}\n.frow .btn{justify-self:end}\n.empty{\n  display:flex;flex-direction:column;align-items:center;gap:8px;padding:44px 20px;\n  color:var(--muted);text-align:center;\n}\n.empty .ic{width:28px;height:28px}\n.empty strong{color:var(--ink-2);font-weight:600}\n\n@media (prefers-reduced-motion:no-preference){\n  .track i{transition:width .15s linear}\n}\n@media (prefers-reduced-motion:reduce){\n  *{transition:none!important}\n}\n@media (max-width:640px){\n  .top-in{padding:0 14px}\n  main{padding:20px 14px 40px}\n  .btn.collapse{width:36px;padding:0}\n  .btn.collapse .lbl{display:none}\n  .card-head{padding:12px 14px}\n  .drop{margin:14px}\n  .qitem{padding:12px 14px}\n  .thead{display:none}\n  .frow{grid-template-columns:minmax(0,1fr) auto;padding:0 14px}\n  .fsize,.fdate{display:none}\n  .fmeta{display:flex}\n  .auth{padding-top:2vh}\n  .auth-card{padding:26px 20px}\n}\n</style>\n</head>\n<body>\n<svg class="sprite" aria-hidden="true" focusable="false">\n  <symbol id="i-upload" viewBox="0 0 24 24"><path d="M12 16V4m0 0L7 9m5-5 5 5"/><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"/></symbol>\n  <symbol id="i-download" viewBox="0 0 24 24"><path d="M12 4v12m0 0-5-5m5 5 5-5"/><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"/></symbol>\n  <symbol id="i-clock" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></symbol>\n  <symbol id="i-lock" viewBox="0 0 24 24"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></symbol>\n  <symbol id="i-phone" viewBox="0 0 24 24"><rect x="7" y="3" width="10" height="18" rx="2"/><path d="M11 18h2"/></symbol>\n  <symbol id="i-logout" viewBox="0 0 24 24"><path d="M9 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h3"/><path d="M16 8l4 4-4 4M20 12H9"/></symbol>\n  <symbol id="i-x" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></symbol>\n  <symbol id="i-folder" viewBox="0 0 24 24"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></symbol>\n</svg>\n\n<header class="top">\n  <div class="top-in">\n    <div class="brand">\n      <span class="logo"><svg viewBox="0 0 64 64" aria-hidden="true"><path d="M34 6c2 11 14 17 14 32a14 14 0 0 1-28 0c0-8 3-11 6-14 1 4 3 6 5 7-2-8 0-16 3-25z"/></svg></span>\n      <span>FlameDrop</span>\n    </div>\n    <div id="topActions" class="top-actions" hidden>\n      <span id="sessionPill" class="pill" title="Time left in this session">\n        <svg class="ic" aria-hidden="true"><use href="#i-clock"/></svg>\n        <span id="timer">0:00</span>\n      </span>\n      <button id="newCode" class="btn ghost sm collapse" type="button" aria-label="Pair another device" title="Pair another device">\n        <svg class="ic" aria-hidden="true"><use href="#i-phone"/></svg><span class="lbl">Pair device</span>\n      </button>\n      <button id="logout" class="btn ghost sm collapse" type="button" aria-label="Disconnect" title="Disconnect">\n        <svg class="ic" aria-hidden="true"><use href="#i-logout"/></svg><span class="lbl">Disconnect</span>\n      </button>\n    </div>\n  </div>\n</header>\n\n<main>\n  <section id="pair" class="auth" hidden>\n    <div class="auth-card">\n      <div class="auth-icon"><svg class="ic" aria-hidden="true"><use href="#i-lock"/></svg></div>\n      <h1>Pair this device</h1>\n      <p id="pairMsg" class="sub"></p>\n      <label class="field" for="code">Pairing code</label>\n      <input id="code" type="text" inputmode="numeric" pattern="[0-9]*" maxlength="6" autocomplete="one-time-code" placeholder="000000">\n      <p id="pairErr" class="err" role="alert"></p>\n      <button id="pairBtn" class="btn primary block" type="button">Pair device</button>\n      <ul class="facts">\n        <li>Each code works once and expires after a few minutes.</li>\n        <li>Files move directly between devices on this network.</li>\n      </ul>\n    </div>\n  </section>\n\n  <section id="app" hidden>\n    <div class="page-head">\n      <h1>Transfer files</h1>\n      <p class="sub">Send files to this computer or download what has been shared. Everything stays on your local network.</p>\n    </div>\n\n    <div id="codeBox" class="callout" hidden>\n      <div class="callout-text">\n        <div class="callout-title">Pair another device</div>\n        <p>Enter this code on the other device. <span id="codeLeft"></span></p>\n      </div>\n      <div id="codeVal" class="digits"></div>\n      <button id="codeClose" class="icon-btn" type="button" aria-label="Dismiss"><svg class="ic" aria-hidden="true"><use href="#i-x"/></svg></button>\n    </div>\n\n    <section class="card">\n      <div class="card-head">\n        <h2>Send files</h2>\n        <button id="clearQueue" class="btn text" type="button" hidden>Clear finished</button>\n      </div>\n      <label id="drop" class="drop">\n        <input id="file" type="file" multiple hidden>\n        <span class="drop-icon"><svg class="ic" aria-hidden="true"><use href="#i-upload"/></svg></span>\n        <span class="drop-title">Drag files here or <u>browse</u></span>\n        <span class="drop-sub">Up to <span id="max"></span> per file</span>\n      </label>\n      <ul id="queue" class="queue"></ul>\n    </section>\n\n    <section class="card">\n      <div class="card-head">\n        <h2>Shared files<span id="count" class="count"></span></h2>\n        <button id="refreshBtn" class="btn text" type="button">Refresh</button>\n      </div>\n      <div class="thead"><span>Name</span><span>Size</span><span>Modified</span><span></span></div>\n      <ul id="files"></ul>\n    </section>\n  </section>\n</main>\n\n<script>\nconst $ = s => document.querySelector(s);\nconst NS = "http://www.w3.org/2000/svg";\nconst PAIR_HELP = "Enter the 6-digit code shown in the terminal on the computer running FlameDrop.";\nconst SESSION_ENDED = "Your session has ended. Enter a new pairing code to continue.";\nconst KINDS = {\n  image: ["jpg", "jpeg", "png", "gif", "webp", "heic", "svg", "bmp"],\n  video: ["mp4", "mov", "mkv", "avi", "webm"],\n  audio: ["mp3", "wav", "flac", "m4a", "aac"],\n  doc: ["pdf", "doc", "docx", "txt", "md", "rtf", "odt"],\n  sheet: ["xls", "xlsx", "csv", "ods"],\n  slide: ["ppt", "pptx", "key"],\n  archive: ["zip", "rar", "7z", "tar", "gz"]\n};\nlet cfg = {max_size: 0, blocked: []};\nlet expiresAt = 0;\nlet codeUntil = 0;\nlet tick = null;\nlet codeTick = null;\nlet busy = false;\nlet pairing = false;\nconst queue = [];\nconst items = [];\n\nfunction icon(name) {\n  const s = document.createElementNS(NS, "svg");\n  s.setAttribute("class", "ic");\n  s.setAttribute("aria-hidden", "true");\n  const u = document.createElementNS(NS, "use");\n  u.setAttribute("href", "#i-" + name);\n  s.append(u);\n  return s;\n}\n\nfunction el(tag, cls, text) {\n  const e = document.createElement(tag);\n  if (cls) e.className = cls;\n  if (text !== undefined) e.textContent = text;\n  return e;\n}\n\nfunction fmt(n) {\n  const u = ["B", "KB", "MB", "GB", "TB"];\n  let i = 0;\n  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }\n  return (i ? n.toFixed(n >= 100 ? 0 : 1) : n) + " " + u[i];\n}\n\nfunction clock(s) {\n  return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");\n}\n\nfunction badge(name) {\n  const m = name.match(/\\.([^.]+)$/);\n  const ext = m ? m[1].toLowerCase() : "";\n  let kind = "other";\n  for (const k in KINDS) {\n    if (KINDS[k].includes(ext)) { kind = k; break; }\n  }\n  return el("span", "badge k-" + kind, (ext || "file").slice(0, 4));\n}\n\nfunction show(view, msg) {\n  $("#pair").hidden = view !== "pair";\n  $("#app").hidden = view !== "app";\n  $("#topActions").hidden = view !== "app";\n  if (view === "pair") {\n    clearInterval(tick);\n    $("#pairMsg").textContent = msg || PAIR_HELP;\n    $("#code").focus();\n  }\n}\n\nasync function api(path, opts, quiet) {\n  const r = await fetch(path, Object.assign({credentials: "same-origin"}, opts));\n  if (r.status === 401) {\n    show("pair", quiet ? null : SESSION_ENDED);\n    throw new Error("auth");\n  }\n  return r;\n}\n\nfunction renderFiles(files) {\n  const ul = $("#files");\n  ul.replaceChildren();\n  $("#count").textContent = files.length ? String(files.length) : "";\n  if (!files.length) {\n    const li = el("li", "empty");\n    li.append(icon("folder"));\n    li.append(el("strong", null, "No files yet"));\n    li.append(el("span", null, "Files sent from any paired device will appear here."));\n    ul.append(li);\n    return;\n  }\n  for (const f of files) {\n    const when = new Date(f.mtime * 1000).toLocaleString(undefined, {\n      month: "short", day: "numeric", hour: "numeric", minute: "2-digit"\n    });\n    const li = el("li", "frow");\n    const cell = el("div", "fname");\n    const text = el("div", "ftext");\n    const meta = el("div", "fmeta");\n    meta.append(el("span", null, fmt(f.size)), el("span", null, when));\n    text.append(el("span", "name", f.name), meta);\n    cell.append(badge(f.name), text);\n    const a = el("a", "btn ghost sm collapse");\n    a.href = "/download/" + encodeURIComponent(f.name);\n    a.setAttribute("download", f.name);\n    a.setAttribute("aria-label", "Download " + f.name);\n    a.title = "Download";\n    a.append(icon("download"), el("span", "lbl", "Download"));\n    li.append(cell, el("span", "fsize", fmt(f.size)), el("span", "fdate", when), a);\n    ul.append(li);\n  }\n}\n\nfunction startTimer() {\n  clearInterval(tick);\n  const update = () => {\n    const s = Math.max(0, Math.round((expiresAt - Date.now()) / 1000));\n    $("#timer").textContent = clock(s);\n    $("#sessionPill").classList.toggle("warn", s < 300);\n    if (s <= 0) show("pair", "Your session has expired. Enter a new pairing code to continue.");\n  };\n  update();\n  tick = setInterval(update, 1000);\n}\n\nasync function refresh(first) {\n  const r = await api("/api/files", undefined, first);\n  const d = await r.json();\n  cfg = d;\n  expiresAt = Date.now() + d.expires_in * 1000;\n  $("#max").textContent = fmt(d.max_size);\n  renderFiles(d.files);\n  show("app");\n  startTimer();\n}\n\nasync function pair() {\n  if (pairing) return;\n  const code = $("#code").value.trim();\n  if (code.length !== 6) {\n    $("#pairErr").textContent = "Enter all 6 digits.";\n    return;\n  }\n  pairing = true;\n  $("#pairBtn").disabled = true;\n  $("#pairErr").textContent = "";\n  try {\n    const r = await fetch("/api/pair", {\n      method: "POST",\n      credentials: "same-origin",\n      headers: {"Content-Type": "application/json"},\n      body: JSON.stringify({code})\n    });\n    if (r.ok) {\n      $("#code").value = "";\n      await refresh();\n    } else {\n      const d = await r.json().catch(() => ({}));\n      $("#pairErr").textContent = d.error || "Pairing failed. Try again.";\n      $("#code").select();\n    }\n  } catch (e) {\n    $("#pairErr").textContent = "Could not reach FlameDrop. Check your Wi-Fi connection.";\n  } finally {\n    pairing = false;\n    $("#pairBtn").disabled = false;\n  }\n}\n\nfunction syncClear() {\n  $("#clearQueue").hidden = !items.some(i => i.status === "done" || i.status === "failed");\n}\n\nfunction settle(item, status) {\n  item.status = status;\n  item.btn.setAttribute("aria-label", "Remove from list");\n  item.btn.title = "Remove from list";\n  syncClear();\n}\n\nfunction fail(item, msg) {\n  item.state.textContent = msg;\n  item.state.className = "state bad";\n  item.track.hidden = true;\n  settle(item, "failed");\n}\n\nfunction finish(item, name) {\n  item.bar.style.width = "100%";\n  item.track.classList.add("done");\n  item.state.textContent = "Uploaded";\n  item.state.className = "state ok";\n  item.sub.textContent = name !== item.file.name ? "Saved as " + name : fmt(item.file.size);\n  settle(item, "done");\n}\n\nfunction dismiss(item) {\n  if (item.status === "queued") {\n    const i = queue.indexOf(item);\n    if (i >= 0) queue.splice(i, 1);\n    fail(item, "Cancelled");\n  } else if (item.status === "active") {\n    item.xhr.abort();\n  } else {\n    item.li.remove();\n    const i = items.indexOf(item);\n    if (i >= 0) items.splice(i, 1);\n    syncClear();\n  }\n}\n\nfunction makeItem(file) {\n  const li = el("li", "qitem");\n  const main = el("div", "qmain");\n  const top = el("div", "qtop");\n  const state = el("span", "state", "Waiting");\n  top.append(el("span", "name", file.name), state);\n  const track = el("div", "track");\n  const bar = document.createElement("i");\n  track.append(bar);\n  const sub = el("div", "qsub", fmt(file.size));\n  main.append(top, track, sub);\n  const btn = el("button", "icon-btn");\n  btn.type = "button";\n  btn.setAttribute("aria-label", "Cancel upload");\n  btn.title = "Cancel upload";\n  btn.append(icon("x"));\n  li.append(badge(file.name), main, btn);\n  $("#queue").append(li);\n  const item = {file, li, bar, track, state, sub, btn, xhr: null, status: "queued"};\n  btn.onclick = () => dismiss(item);\n  items.push(item);\n  return item;\n}\n\nfunction send(item) {\n  return new Promise(resolve => {\n    const x = new XMLHttpRequest();\n    const t0 = Date.now();\n    item.xhr = x;\n    item.status = "active";\n    item.state.textContent = "0%";\n    x.open("POST", "/api/upload");\n    x.setRequestHeader("X-Filename", encodeURIComponent(item.file.name));\n    x.setRequestHeader("Content-Type", "application/octet-stream");\n    x.upload.onprogress = e => {\n      if (!e.lengthComputable) return;\n      const p = e.loaded / e.total;\n      const speed = e.loaded / Math.max(0.2, (Date.now() - t0) / 1000);\n      item.bar.style.width = (p * 100).toFixed(1) + "%";\n      item.state.textContent = Math.round(p * 100) + "%";\n      item.sub.textContent = fmt(e.loaded) + " of " + fmt(e.total) + " at " + fmt(speed) + "/s";\n    };\n    x.onload = () => {\n      let d = {};\n      try { d = JSON.parse(x.responseText); } catch (e) {}\n      if (x.status === 200) {\n        finish(item, d.name);\n      } else {\n        if (x.status === 401) show("pair", SESSION_ENDED);\n        fail(item, d.error || "Upload failed");\n      }\n      resolve();\n    };\n    x.onerror = () => { fail(item, "Connection lost"); resolve(); };\n    x.onabort = () => { fail(item, "Cancelled"); resolve(); };\n    x.send(item.file);\n  });\n}\n\nasync function pump() {\n  if (busy) return;\n  busy = true;\n  while (queue.length) await send(queue.shift());\n  busy = false;\n  refresh().catch(() => {});\n}\n\nfunction addFiles(list) {\n  for (const file of list) {\n    const item = makeItem(file);\n    const ext = (file.name.match(/\\.[^.]*$/) || [""])[0].toLowerCase();\n    if (file.size === 0) fail(item, "File is empty");\n    else if (file.size > cfg.max_size) fail(item, "Over the " + fmt(cfg.max_size) + " limit");\n    else if (cfg.blocked.includes(ext)) fail(item, "File type not allowed");\n    else queue.push(item);\n  }\n  pump();\n}\n\nfunction hideCode() {\n  clearInterval(codeTick);\n  $("#codeBox").hidden = true;\n}\n\n$("#pairBtn").onclick = pair;\n$("#code").addEventListener("keydown", e => { if (e.key === "Enter") pair(); });\n$("#code").addEventListener("input", e => {\n  e.target.value = e.target.value.replace(/\\D/g, "").slice(0, 6);\n  $("#pairErr").textContent = "";\n  if (e.target.value.length === 6) pair();\n});\n$("#file").addEventListener("change", e => {\n  addFiles(Array.from(e.target.files));\n  e.target.value = "";\n});\nconst drop = $("#drop");\ndrop.addEventListener("dragover", e => { e.preventDefault(); drop.classList.add("over"); });\ndrop.addEventListener("dragleave", () => drop.classList.remove("over"));\ndrop.addEventListener("drop", e => {\n  e.preventDefault();\n  drop.classList.remove("over");\n  addFiles(Array.from(e.dataTransfer.files));\n});\n$("#clearQueue").onclick = () => {\n  for (const item of items.slice()) {\n    if (item.status === "done" || item.status === "failed") dismiss(item);\n  }\n};\n$("#refreshBtn").onclick = () => refresh().catch(() => {});\n$("#newCode").onclick = async () => {\n  const r = await api("/api/newcode", {method: "POST"});\n  const d = await r.json();\n  $("#codeVal").textContent = d.code.slice(0, 3) + " " + d.code.slice(3);\n  codeUntil = Date.now() + d.expires_in * 1000;\n  $("#codeBox").hidden = false;\n  clearInterval(codeTick);\n  const update = () => {\n    const s = Math.max(0, Math.round((codeUntil - Date.now()) / 1000));\n    $("#codeLeft").textContent = "Expires in " + clock(s) + ".";\n    if (s <= 0) hideCode();\n  };\n  update();\n  codeTick = setInterval(update, 1000);\n};\n$("#codeClose").onclick = hideCode;\n$("#logout").onclick = async () => {\n  await fetch("/api/logout", {method: "POST", credentials: "same-origin"});\n  hideCode();\n  show("pair", "You have been disconnected. Enter a pairing code to reconnect.");\n};\n\nsetInterval(() => {\n  if (!$("#app").hidden && !busy && !document.hidden) refresh().catch(() => {});\n}, 10000);\n\nrefresh(true).catch(() => show("pair"));\n</script>\n</body>\n</html>\n'


class Auth:
    def __init__(self, session_seconds, code_seconds):
        self.session_seconds = session_seconds
        self.code_seconds = code_seconds
        self.lock = threading.Lock()
        self.sessions = {}
        self.code = None
        self.code_expires = 0.0
        self.failures = 0

    def new_code(self):
        with self.lock:
            self.code = f"{secrets.randbelow(1000000):06d}"
            self.code_expires = time.time() + self.code_seconds
            self.failures = 0
            return self.code

    def pair(self, attempt):
        with self.lock:
            now = time.time()
            if self.code and now < self.code_expires:
                if hmac.compare_digest(self.code.encode(), attempt.encode()):
                    self.code = None
                    self.failures = 0
                    self.sessions = {t: e for t, e in self.sessions.items() if e > now}
                    token = secrets.token_urlsafe(32)
                    self.sessions[token] = now + self.session_seconds
                    return token
                self.failures += 1
                if self.failures >= MAX_CODE_FAILURES:
                    self.code = None
            return None

    def expiry(self, token):
        if not token:
            return None
        with self.lock:
            exp = self.sessions.get(token)
            if exp is None:
                return None
            if time.time() >= exp:
                del self.sessions[token]
                return None
            return exp

    def drop(self, token):
        with self.lock:
            self.sessions.pop(token, None)


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def clean_name(raw, blocked):
    name = raw.replace("\\", "/").split("/")[-1]
    name = re.sub(r'[\x00-\x1f\x7f<>:"|?*]', "_", name).strip(" .")
    if not name:
        return None
    stem, ext = os.path.splitext(name)
    if ext.lower() in blocked:
        return None
    return stem[: max(1, 200 - len(ext))] + ext


def unique_name(directory, name):
    stem, ext = os.path.splitext(name)
    n = 0
    while True:
        candidate = name if n == 0 else f"{stem} ({n}){ext}"
        if not os.path.exists(os.path.join(directory, candidate)):
            return candidate
        n += 1


def list_files(directory):
    items = []
    with os.scandir(directory) as it:
        for e in it:
            if e.name.startswith(".") or not e.is_file(follow_symlinks=False):
                continue
            st = e.stat(follow_symlinks=False)
            items.append({"name": e.name, "size": st.st_size, "mtime": int(st.st_mtime)})
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return items


def remove_partials(directory):
    for name in os.listdir(directory):
        if name.startswith(".") and name.endswith(".part"):
            try:
                os.unlink(os.path.join(directory, name))
            except OSError:
                pass


class Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 64

    def handle_error(self, request, client_address):
        if isinstance(sys.exc_info()[1], (ConnectionError, TimeoutError)):
            return
        super().handle_error(request, client_address)


class Handler(BaseHTTPRequestHandler):
    server_version = "FlameDrop"
    sys_version = ""
    timeout = 120

    def log_message(self, fmt, *args):
        pass

    def base_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")

    def send_json(self, status, obj, extra=None):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.base_headers()
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def token(self):
        raw = self.headers.get("Cookie")
        if not raw:
            return None
        jar = SimpleCookie()
        try:
            jar.load(raw)
        except Exception:
            return None
        morsel = jar.get(COOKIE_NAME)
        return morsel.value if morsel else None

    def session_expiry(self):
        return self.server.auth.expiry(self.token())

    def read_json(self):
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None
        if n <= 0 or n > 4096:
            return None
        try:
            data = json.loads(self.rfile.read(n))
        except ValueError:
            return None
        return data if isinstance(data, dict) else None

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; img-src 'self' data:; style-src 'unsafe-inline'; "
                "script-src 'unsafe-inline'; frame-ancestors 'none'",
            )
            self.base_headers()
            self.end_headers()
            self.wfile.write(body)
            return
        expiry = self.session_expiry()
        if expiry is None:
            self.send_json(401, {"error": "Pairing required"})
            return
        if path == "/api/files":
            cfg = self.server.cfg
            self.send_json(
                200,
                {
                    "files": list_files(cfg.directory),
                    "max_size": cfg.max_size,
                    "blocked": sorted(cfg.blocked),
                    "expires_in": max(0, int(expiry - time.time())),
                },
            )
            return
        if path.startswith("/download/"):
            self.handle_download(unquote(path[len("/download/"):]))
            return
        self.send_json(404, {"error": "Not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/pair":
            self.handle_pair()
            return
        if self.session_expiry() is None:
            self.close_connection = True
            self.send_json(401, {"error": "Pairing required"})
            return
        if path == "/api/upload":
            self.handle_upload()
        elif path == "/api/newcode":
            code = self.server.auth.new_code()
            print(f"\nNew pairing code requested from a paired device: {code}\n")
            self.send_json(200, {"code": code, "expires_in": self.server.auth.code_seconds})
        elif path == "/api/logout":
            self.server.auth.drop(self.token())
            self.send_json(
                200,
                {"ok": True},
                {"Set-Cookie": f"{COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0"},
            )
        else:
            self.send_json(404, {"error": "Not found"})

    def handle_pair(self):
        data = self.read_json()
        code = str(data.get("code", "")).strip() if data else ""
        token = self.server.auth.pair(code) if code else None
        if not token:
            self.send_json(403, {"error": "Invalid or expired code. Check the terminal for a current one."})
            return
        ttl = self.server.auth.session_seconds
        self.send_json(
            200,
            {"ok": True},
            {"Set-Cookie": f"{COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={ttl}"},
        )

    def handle_download(self, name):
        cfg = self.server.cfg
        if not name or name != os.path.basename(name) or name.startswith("."):
            self.send_json(404, {"error": "Not found"})
            return
        full = os.path.join(cfg.directory, name)
        if os.path.islink(full) or not os.path.isfile(full):
            self.send_json(404, {"error": "Not found"})
            return
        size = os.path.getsize(full)
        fallback = name.encode("ascii", "replace").decode().replace('"', "_")
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(size))
        self.send_header(
            "Content-Disposition",
            f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(name)}",
        )
        self.base_headers()
        self.end_headers()
        with open(full, "rb") as f:
            while True:
                chunk = f.read(1 << 20)
                if not chunk:
                    break
                self.wfile.write(chunk)

    def handle_upload(self):
        cfg = self.server.cfg
        self.close_connection = True
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self.send_json(411, {"error": "Content-Length required"})
            return
        if length <= 0:
            self.send_json(400, {"error": "File is empty"})
            return
        if length > cfg.max_size:
            self.send_json(413, {"error": "File exceeds the size limit"})
            return
        name = clean_name(unquote(self.headers.get("X-Filename", "")), cfg.blocked)
        if not name:
            self.send_json(400, {"error": "Invalid or disallowed file name or type"})
            return
        if shutil.disk_usage(cfg.directory).free < length + (64 << 20):
            self.send_json(507, {"error": "Not enough free disk space"})
            return
        tmp = os.path.join(cfg.directory, f".{secrets.token_hex(8)}.part")
        received = 0
        try:
            with open(tmp, "wb") as f:
                while received < length:
                    chunk = self.rfile.read(min(1 << 20, length - received))
                    if not chunk:
                        break
                    f.write(chunk)
                    received += len(chunk)
            if received != length:
                os.unlink(tmp)
                return
            with WRITE_LOCK:
                final = unique_name(cfg.directory, name)
                os.replace(tmp, os.path.join(cfg.directory, final))
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            self.send_json(500, {"error": "Could not save the file"})
            return
        self.send_json(200, {"name": final, "size": length})


def watch_stdin(auth):
    for _ in sys.stdin:
        print(f"New pairing code: {auth.new_code()}  (valid {auth.code_seconds // 60} min, single use)")


def main():
    p = argparse.ArgumentParser(description="FlameDrop: local file transfer over Wi-Fi")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--dir", default="flamedrop_files")
    p.add_argument("--max-mb", type=int, default=2048)
    p.add_argument("--session-min", type=int, default=30)
    p.add_argument("--code-min", type=int, default=5)
    p.add_argument("--allow-all-types", action="store_true")
    a = p.parse_args()

    directory = os.path.abspath(a.dir)
    os.makedirs(directory, exist_ok=True)
    remove_partials(directory)

    server = Server(("0.0.0.0", a.port), Handler)
    server.cfg = argparse.Namespace(
        directory=directory,
        max_size=a.max_mb * 1024 * 1024,
        blocked=frozenset() if a.allow_all_types else BLOCKED_EXT,
    )
    server.auth = Auth(a.session_min * 60, a.code_min * 60)
    code = server.auth.new_code()

    print("FlameDrop is running")
    print(f"  Open on any device on this Wi-Fi:  http://{lan_ip()}:{a.port}")
    print(f"  Pairing code:  {code}  (valid {a.code_min} min, single use)")
    print(f"  Files folder:  {directory}")
    print(f"  Size limit:    {a.max_mb} MB per file, sessions last {a.session_min} min")
    print("  Press Enter for a new pairing code, Ctrl+C to stop\n")

    if sys.stdin and sys.stdin.isatty():
        threading.Thread(target=watch_stdin, args=(server.auth,), daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
