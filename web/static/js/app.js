/**
 * Milodi Web UI — 上传、播放、音游音谱、导出
 */

const $ = (sel) => document.querySelector(sel);

const uploadZone = $("#uploadZone");
const fileInput = $("#fileInput");
const uploadLoading = $("#uploadLoading");
const playerPanel = $("#playerPanel");
const chartCanvas = $("#chartCanvas");
const laneLabels = $("#laneLabels");
const playBtn = $("#playBtn");
const progressBar = $("#progressBar");
const timeCurrent = $("#timeCurrent");
const timeTotal = $("#timeTotal");
const trackName = $("#trackName");
const exportBtn = $("#exportBtn");
const exportMenu = $("#exportMenu");
const errorMsg = $("#errorMsg");
const stats = $("#stats");
const statNotes = $("#statNotes");
const statDuration = $("#statDuration");
const audio = $("#audio");
const playModeEl = $("#playMode");
const chartWrap = $("#chartWrap");
const chartSelection = $("#chartSelection");
const exportRangeEl = $("#exportRange");
const exportRangeLabel = $("#exportRangeLabel");
const exportRangeClear = $("#exportRangeClear");
const skylineCtrl = $("#skylineCtrl");
const skylineMinBar = $("#skylineMinBar");
const skylineMinValue = $("#skylineMinValue");

const HIT_LINE_X = 100;
const PX_PER_MS = 0.12;
const LOOKAHEAD_MS = 6000;
const LANE_COUNT = 7;
const LANE_NAMES = ["B5", "G5", "E5", "C5", "A4", "F4", "C4"];
const LANE_COLORS = [
  "#e17055", "#fd79a8", "#fdcb6e", "#55efc4",
  "#00cec9", "#a29bfe", "#6c5ce7",
];

let state = {
  fileId: null,
  filename: "",
  notes: [],
  durationMs: 0,
  playing: false,
  animId: null,
  playMode: "mp3", // "mp3" | "midi"
  exportRange: { startMs: null, endMs: null },
};

let dragSelect = null;

const ctx = chartCanvas.getContext("2d");

/** 仅 MIDI 试听：同时刻取最高音（skyline 主旋律），音谱仍显示原多声部。 */
function noteHz(n) {
  if (n.hz > 0) return n.hz;
  return 440 * Math.pow(2, (n.midi - 69) / 12);
}

function highestNoteMelodyForPlayback(notes) {
  if (!notes.length) return [];

  const bounds = new Set();
  for (const n of notes) {
    bounds.add(n.start_ms);
    bounds.add(n.start_ms + n.duration_ms);
  }
  const times = [...bounds].sort((a, b) => a - b);
  const merged = [];

  for (let i = 0; i < times.length - 1; i++) {
    const t0 = times[i];
    const t1 = times[i + 1];
    const dur = t1 - t0;
    if (dur < 1) continue;

    const active = notes.filter(
      (n) => n.start_ms < t1 && n.start_ms + n.duration_ms > t0,
    );
    if (!active.length) continue;

    const top = active.reduce(
      (best, n) => (n.midi > best.midi ? n : best),
      active[0],
    );

    const prev = merged[merged.length - 1];
    if (prev && prev.midi === top.midi && prev.start_ms + prev.duration_ms === t0) {
      prev.duration_ms += dur;
      prev.velocity = Math.max(prev.velocity, top.velocity ?? 100);
    } else {
      merged.push({
        start_ms: t0,
        duration_ms: dur,
        midi: top.midi,
        hz: Math.round(noteHz(top)),
        velocity: top.velocity ?? 100,
        name: top.name,
      });
    }
  }

  return merged;
}

const SKYLINE_MERGE_GAP_MS = 50;

function getSkylineMinMs() {
  return Number(skylineMinBar?.value) || 200;
}

function updateSkylineMinLabel() {
  if (skylineMinValue) {
    skylineMinValue.textContent = `${getSkylineMinMs()} ms`;
  }
}

function bridgeShortSpikes(segs, minMs) {
  if (segs.length < 3) return segs;
  const out = [];
  let i = 0;
  while (i < segs.length) {
    const a = segs[i];
    const b = segs[i + 1];
    const c = segs[i + 2];
    if (
      b &&
      c &&
      a.midi === c.midi &&
      b.duration_ms < minMs &&
      b.midi !== a.midi
    ) {
      const end = c.start_ms + c.duration_ms;
      out.push({
        ...a,
        duration_ms: end - a.start_ms,
        velocity: Math.max(a.velocity, c.velocity),
      });
      i += 3;
    } else {
      out.push({ ...a });
      i += 1;
    }
  }
  return out;
}

function absorbShortIntoPrev(segs, minMs) {
  if (!segs.length) return segs;
  let work = segs.map((s) => ({ ...s }));

  if (work.length >= 2 && work[0].duration_ms < minMs) {
    const head = work.shift();
    work[0].start_ms = head.start_ms;
    work[0].duration_ms =
      work[0].start_ms + work[0].duration_ms - head.start_ms;
    work[0].velocity = Math.max(head.velocity, work[0].velocity);
  }

  const out = [];
  for (const s of work) {
    if (s.duration_ms >= minMs || !out.length) {
      out.push(s);
      continue;
    }
    const prev = out[out.length - 1];
    prev.duration_ms = s.start_ms + s.duration_ms - prev.start_ms;
    prev.velocity = Math.max(prev.velocity, s.velocity);
  }
  return out;
}

function mergeAdjacentMelody(segs, gapMs) {
  if (!segs.length) return segs;
  const out = [{ ...segs[0] }];
  for (let i = 1; i < segs.length; i++) {
    const s = segs[i];
    const prev = out[out.length - 1];
    const gap = s.start_ms - (prev.start_ms + prev.duration_ms);
    if (s.midi === prev.midi && gap <= gapMs) {
      prev.duration_ms = s.start_ms + s.duration_ms - prev.start_ms;
      prev.velocity = Math.max(prev.velocity, s.velocity);
    } else {
      out.push({ ...s });
    }
  }
  return out;
}

function refineSkylineMelody(segments) {
  if (!segments.length) return segments;
  const minMs = getSkylineMinMs();
  let segs = bridgeShortSpikes(segments, minMs);
  segs = absorbShortIntoPrev(segs, minMs);
  segs = mergeAdjacentMelody(segs, SKYLINE_MERGE_GAP_MS);
  return segs;
}

function melodyForPlayback(notes) {
  return refineSkylineMelody(highestNoteMelodyForPlayback(notes));
}

/* ── MIDI 合成播放器（Web Audio API） ── */

class MidiSynthPlayer {
  constructor() {
    this.ctx = null;
    this.nodes = [];
    this.offsetMs = 0;
    this.wallStart = 0;
    this.playing = false;
    this.endTimer = null;
  }

  _ensureCtx() {
    if (!this.ctx) {
      this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (this.ctx.state === "suspended") {
      this.ctx.resume();
    }
    return this.ctx;
  }

  get currentTimeMs() {
    if (!this.playing) return this.offsetMs;
    return this.offsetMs + (performance.now() - this.wallStart);
  }

  _clearScheduled() {
    for (const n of this.nodes) {
      try { n.stop(); n.disconnect(); } catch (_) { /* already stopped */ }
    }
    this.nodes = [];
    if (this.endTimer) {
      clearTimeout(this.endTimer);
      this.endTimer = null;
    }
  }

  _scheduleNotes(notes, fromMs) {
    const ac = this._ensureCtx();
    const lead = 0.05;
    const base = ac.currentTime + lead;
    const endMs = notes.reduce((m, n) => Math.max(m, n.start_ms + n.duration_ms), 0);

    for (const note of notes) {
      if (note.start_ms + note.duration_ms <= fromMs) continue;

      const delayS = Math.max(0, (note.start_ms - fromMs) / 1000);
      const startAt = base + delayS;
      const durS = note.duration_ms / 1000;

      const osc = ac.createOscillator();
      const gain = ac.createGain();
      osc.type = "triangle";
      osc.frequency.value = note.hz;

      const vol = 0.08 + ((note.velocity ?? 100) / 127) * 0.22;
      gain.gain.setValueAtTime(0, startAt);
      gain.gain.linearRampToValueAtTime(vol, startAt + 0.008);
      gain.gain.setValueAtTime(vol, startAt + durS - 0.012);
      gain.gain.linearRampToValueAtTime(0, startAt + durS);

      osc.connect(gain);
      gain.connect(ac.destination);
      osc.start(startAt);
      osc.stop(startAt + durS + 0.02);

      this.nodes.push(osc);
      this.nodes.push(gain);
    }

    const remainMs = endMs - fromMs;
    if (remainMs > 0) {
      this.endTimer = setTimeout(() => {
        if (this.playing) this.onEnded?.();
      }, remainMs + lead * 1000);
    }
  }

  play(notes, fromMs) {
    this._clearScheduled();
    this.offsetMs = fromMs ?? this.offsetMs;
    this.wallStart = performance.now();
    this.playing = true;
    this._scheduleNotes(melodyForPlayback(notes), this.offsetMs);
  }

  pause() {
    if (!this.playing) return;
    this.offsetMs = this.currentTimeMs;
    this.playing = false;
    this._clearScheduled();
  }

  stop() {
    this.playing = false;
    this.offsetMs = 0;
    this._clearScheduled();
  }

  seek(ms, notes) {
    const wasPlaying = this.playing;
    this.pause();
    this.offsetMs = ms;
    if (wasPlaying) this.play(notes, ms);
  }
}

const midiPlayer = new MidiSynthPlayer();
midiPlayer.onEnded = () => {
  state.playing = false;
  midiPlayer.playing = false;
  midiPlayer.offsetMs = 0;
  updatePlayIcon();
  stopAnim();
  updateProgress();
};

/* ── 工具函数 ── */

function formatTime(ms) {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  return `${m}:${String(s % 60).padStart(2, "0")}`;
}

function showError(msg) {
  errorMsg.textContent = msg;
  errorMsg.hidden = false;
}

function hideError() {
  errorMsg.hidden = true;
}

function getMelodyDurationMs() {
  if (!state.notes.length) return state.durationMs;
  return state.notes.reduce((m, n) => Math.max(m, n.start_ms + n.duration_ms), 0);
}

function getDurationMs() {
  if (state.playMode === "mp3" && audio.duration && isFinite(audio.duration)) {
    return audio.duration * 1000;
  }
  return getMelodyDurationMs() || state.durationMs;
}

function getCurrentTimeMs() {
  if (state.playMode === "midi") return midiPlayer.currentTimeMs;
  return audio.currentTime * 1000;
}

function setCurrentTimeMs(ms) {
  const dur = getDurationMs();
  const t = Math.max(0, Math.min(ms, dur));
  if (state.playMode === "midi") {
    midiPlayer.seek(t, state.notes);
  } else {
    audio.currentTime = t / 1000;
  }
  updateProgress();
  drawChart();
}

function getMidiRange() {
  if (!state.notes.length) return { lo: 60, hi: 83 };
  let lo = Infinity;
  let hi = -Infinity;
  for (const n of state.notes) {
    lo = Math.min(lo, n.midi);
    hi = Math.max(hi, n.midi);
  }
  if (hi - lo < 12) {
    lo -= 6;
    hi += 6;
  }
  return { lo, hi };
}

function midiToLane(midi) {
  const { lo, hi } = getMidiRange();
  const t = Math.max(0, Math.min(1, (midi - lo) / (hi - lo || 1)));
  return LANE_COUNT - 1 - Math.round(t * (LANE_COUNT - 1));
}

function formatNoteLabel(name) {
  return name.replace(/^NOTE_/, "").replace(/S/g, "#");
}

function chartXToMs(x) {
  const t = getCurrentTimeMs();
  return Math.max(0, t + (x - HIT_LINE_X) / PX_PER_MS);
}

function updateExportRangeLabel() {
  const { startMs, endMs } = state.exportRange;
  if (startMs == null || endMs == null || endMs <= startMs) {
    exportRangeLabel.textContent = "全部";
    return;
  }
  exportRangeLabel.textContent = `${formatTime(startMs)} – ${formatTime(endMs)}`;
}

function updateSelectionOverlay() {
  const { startMs, endMs } = state.exportRange;
  if (startMs == null || endMs == null || endMs <= startMs) {
    chartSelection.hidden = true;
    return;
  }
  const lo = Math.min(startMs, endMs);
  const hi = Math.max(startMs, endMs);
  const t = getCurrentTimeMs();
  const x0 = HIT_LINE_X + (lo - t) * PX_PER_MS;
  const x1 = HIT_LINE_X + (hi - t) * PX_PER_MS;
  chartSelection.hidden = false;
  chartSelection.style.left = `${Math.min(x0, x1)}px`;
  chartSelection.style.width = `${Math.max(8, Math.abs(x1 - x0))}px`;
}

function clearExportRange() {
  state.exportRange = { startMs: null, endMs: null };
  updateExportRangeLabel();
  updateSelectionOverlay();
}

function buildLaneLabels() {
  laneLabels.innerHTML = LANE_NAMES.map(
    (name) => `<div class="lane-label">${name}</div>`
  ).join("");
}

/* ── 音谱绘制（音游风格） ── */

function resizeCanvas() {
  const wrap = chartCanvas.parentElement;
  const dpr = window.devicePixelRatio || 1;
  chartCanvas.width = wrap.clientWidth * dpr;
  chartCanvas.height = wrap.clientHeight * dpr;
  chartCanvas.style.width = wrap.clientWidth + "px";
  chartCanvas.style.height = wrap.clientHeight + "px";
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function drawChart() {
  const w = chartCanvas.clientWidth;
  const h = chartCanvas.clientHeight;
  const laneH = h / LANE_COUNT;
  const t = getCurrentTimeMs();

  ctx.clearRect(0, 0, w, h);

  // 轨道背景
  for (let i = 0; i < LANE_COUNT; i++) {
    const y = i * laneH;
    ctx.fillStyle = i % 2 === 0 ? "rgba(255,255,255,0.02)" : "rgba(0,0,0,0.15)";
    ctx.fillRect(HIT_LINE_X, y, w - HIT_LINE_X, laneH);
    ctx.strokeStyle = "rgba(255,255,255,0.04)";
    ctx.beginPath();
    ctx.moveTo(HIT_LINE_X, y + laneH);
    ctx.lineTo(w, y + laneH);
    ctx.stroke();
  }

  // 音符块
  for (const note of state.notes) {
    const lane = midiToLane(note.midi);
    const x = HIT_LINE_X + (note.start_ms - t) * PX_PER_MS;
    const nw = Math.max(note.duration_ms * PX_PER_MS, 6);
    const y = lane * laneH + 4;
    const nh = laneH - 8;

    if (x + nw < HIT_LINE_X - 20 || x > w + 20) continue;

    const color = LANE_COLORS[lane];
    const atHit = t >= note.start_ms && t < note.start_ms + note.duration_ms;
    const dist = Math.abs(t - note.start_ms);
    const glow = atHit ? 1 : Math.max(0, 1 - dist / 300);

    // 拖尾
    const grad = ctx.createLinearGradient(x, y, x + nw, y);
    grad.addColorStop(0, color + "00");
    grad.addColorStop(0.3, color + (atHit ? "cc" : "88"));
    grad.addColorStop(1, color + (atHit ? "ff" : "aa"));
    ctx.fillStyle = grad;

    if (glow > 0.1) {
      ctx.shadowColor = color;
      ctx.shadowBlur = 8 + glow * 16;
    } else {
      ctx.shadowBlur = 0;
    }

    roundRect(ctx, x, y, nw, nh, 4);
    ctx.fill();
    ctx.shadowBlur = 0;

    // 音名
    if (nw > 30) {
      ctx.fillStyle = "rgba(255,255,255,0.85)";
      ctx.font = "bold 10px Orbitron, sans-serif";
      ctx.fillText(formatNoteLabel(note.name), x + 4, y + nh / 2 + 4);
    }
  }

  // 判定线脉冲
  const pulse = 0.5 + 0.5 * Math.sin(Date.now() / 200);
  const activeNotes = state.notes.filter(
    (n) => t >= n.start_ms && t < n.start_ms + n.duration_ms
  );
  if (activeNotes.length > 0) {
    for (const note of activeNotes) {
      const lane = midiToLane(note.midi);
      const y = lane * laneH;
      const color = LANE_COLORS[lane];
      ctx.fillStyle = color + Math.round(40 + pulse * 40).toString(16).padStart(2, "0");
      ctx.fillRect(HIT_LINE_X - 2, y + 2, 6, laneH - 4);
    }
  }

  // 频谱模拟条（判定线处）
  drawSpectrumBars(w, h, laneH, t, activeNotes.length > 0 ? pulse : 0);
  updateSelectionOverlay();
}

function drawSpectrumBars(w, h, laneH, t, intensity) {
  const barCount = 12;
  const barW = 3;
  const gap = 2;
  const totalW = barCount * (barW + gap);
  const startX = HIT_LINE_X - totalW - 12;
  const baseH = h * 0.15;

  for (let i = 0; i < barCount; i++) {
    const freq = (i + 1) / barCount;
    const wave = Math.sin(t * 0.008 + i * 1.2) * 0.5 + 0.5;
    const hFactor = wave * (0.3 + intensity * 0.7) + (intensity > 0 ? 0.4 : 0.1);
    const barH = baseH * hFactor * (0.5 + freq);
    const x = startX + i * (barW + gap);
    const y = h - barH - 10;

    const hue = 260 + i * 8;
    ctx.fillStyle = `hsla(${hue}, 80%, 65%, ${0.4 + intensity * 0.5})`;
    ctx.fillRect(x, y, barW, barH);
  }
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}

function animLoop() {
  drawChart();
  if (state.playing) {
    updateProgress();
    if (
      state.playMode === "midi" &&
      getCurrentTimeMs() >= getMelodyDurationMs()
    ) {
      midiPlayer.onEnded?.();
      return;
    }
    state.animId = requestAnimationFrame(animLoop);
  }
}

function startAnim() {
  if (!state.animId) state.animId = requestAnimationFrame(animLoop);
}

function stopAnim() {
  if (state.animId) {
    cancelAnimationFrame(state.animId);
    state.animId = null;
  }
  drawChart();
}

/* ── 上传与分析 ── */

async function handleFile(file) {
  if (!file) return;
  hideError();
  uploadLoading.hidden = false;
  uploadZone.querySelector(".upload-zone__inner").style.visibility = "hidden";

  const form = new FormData();
  form.append("file", file);
  const modeInput = document.querySelector('input[name="extractMode"]:checked');
  form.append("mode", modeInput ? modeInput.value : "piano");

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10 * 60 * 1000);

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      body: form,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    let data;
    try {
      data = await res.json();
    } catch {
      throw new Error("服务器响应异常，请确认 Web 服务已启动（milodi-web）");
    }
    if (!res.ok) throw new Error(data.error || "分析失败");

    state.fileId = data.fileId;
    state.filename = data.filename;
    state.notes = data.notes;
    state.durationMs = data.durationMs;

    audio.src = `/api/audio/${data.fileId}`;
    audio.load();
    midiPlayer.stop();

    trackName.textContent = data.filename;
    statNotes.textContent = data.noteCount;
    const displayDur = Math.max(data.durationMs, getMelodyDurationMs());
    statDuration.textContent = formatTime(displayDur);
    timeTotal.textContent = formatTime(displayDur);
    progressBar.max = 1000;

    uploadZone.hidden = true;
    playerPanel.hidden = false;
    stats.hidden = false;
    exportRangeEl.hidden = false;
    skylineCtrl.hidden = false;
    updateSkylineMinLabel();
    clearExportRange();

    resizeCanvas();
    drawChart();
  } catch (err) {
    let msg = err.message || "分析失败";
    if (err.name === "AbortError") {
      msg = "分析超时，请换较短的音频或稍后重试";
    } else if (err instanceof TypeError) {
      msg = "无法连接服务器，请先运行：.venv/bin/python -m milodi.web.app";
    }
    showError(msg);
    uploadZone.querySelector(".upload-zone__inner").style.visibility = "visible";
  } finally {
    clearTimeout(timeoutId);
    uploadLoading.hidden = true;
  }
}

/* ── 播放控制 ── */

function pauseAll() {
  if (state.playMode === "midi") {
    midiPlayer.pause();
  } else {
    audio.pause();
  }
  state.playing = false;
  updatePlayIcon();
  stopAnim();
  updateProgress();
}

async function playAll() {
  if (state.playMode === "midi") {
    if (!state.notes.length) {
      showError("无旋律音符，无法 MIDI 播放");
      return;
    }
    midiPlayer.play(state.notes, midiPlayer.currentTimeMs);
    state.playing = true;
    updatePlayIcon();
    startAnim();
    updateProgress();
  } else {
    try {
      await audio.play();
    } catch (err) {
      showError("原音播放失败：" + err.message);
    }
  }
}

function togglePlay() {
  if (state.playing) {
    pauseAll();
  } else {
    playAll();
  }
}

function updatePlayIcon() {
  const iconPlay = playBtn.querySelector(".icon-play");
  const iconPause = playBtn.querySelector(".icon-pause");
  iconPlay.hidden = state.playing;
  iconPause.hidden = !state.playing;
}

function updateProgress() {
  const dur = getDurationMs();
  const cur = getCurrentTimeMs();
  progressBar.value = dur ? (cur / dur) * 1000 : 0;
  timeCurrent.textContent = formatTime(cur);
  timeTotal.textContent = formatTime(dur);
}

function switchPlayMode(mode) {
  if (mode === state.playMode) return;
  const cur = getCurrentTimeMs();
  pauseAll();
  state.playMode = mode;

  playModeEl.querySelectorAll(".play-mode__btn").forEach((btn) => {
    btn.classList.toggle("play-mode__btn--active", btn.dataset.mode === mode);
  });

  if (mode === "midi") {
    midiPlayer.offsetMs = Math.min(cur, getMelodyDurationMs());
  } else if (audio.duration) {
    audio.currentTime = Math.min(cur / 1000, audio.duration);
  }
  updateProgress();
  drawChart();
}

audio.addEventListener("play", () => {
  if (state.playMode !== "mp3") return;
  state.playing = true;
  updatePlayIcon();
  startAnim();
});

audio.addEventListener("pause", () => {
  if (state.playMode !== "mp3") return;
  state.playing = false;
  updatePlayIcon();
  stopAnim();
});

audio.addEventListener("ended", () => {
  if (state.playMode !== "mp3") return;
  state.playing = false;
  updatePlayIcon();
  stopAnim();
});

audio.addEventListener("loadedmetadata", () => {
  if (state.playMode === "mp3") {
    timeTotal.textContent = formatTime(getDurationMs());
  }
});

audio.addEventListener("timeupdate", () => {
  if (state.playMode === "mp3" && !state.playing) updateProgress();
});

progressBar.addEventListener("input", () => {
  const dur = getDurationMs();
  if (!dur) return;
  setCurrentTimeMs((progressBar.value / 1000) * dur);
});

playBtn.addEventListener("click", togglePlay);

playModeEl.addEventListener("click", (e) => {
  const btn = e.target.closest(".play-mode__btn[data-mode]");
  if (btn) switchPlayMode(btn.dataset.mode);
});

/* ── 导出 ── */

exportBtn.addEventListener("click", () => {
  exportMenu.hidden = !exportMenu.hidden;
});

exportMenu.addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-format]");
  if (!btn) return;
  exportMenu.hidden = true;

  const { startMs, endMs } = state.exportRange;
  const payload = {
    notes: state.notes,
    format: btn.dataset.format,
  };
  if (startMs != null && endMs != null && endMs > startMs) {
    payload.startMs = Math.round(startMs);
    payload.endMs = Math.round(endMs);
  }

  try {
    const res = await fetch("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || "导出失败");
    }

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = btn.dataset.format === "h300-detail" ? "melody.txt" : "melody.hex";
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    showError(err.message);
  }
});

exportRangeClear.addEventListener("click", clearExportRange);

skylineMinBar.addEventListener("input", () => {
  updateSkylineMinLabel();
  if (state.playMode === "midi" && state.playing && state.notes.length) {
    const t = getCurrentTimeMs();
    midiPlayer.play(state.notes, t);
  }
});

chartCanvas.addEventListener("mousedown", (e) => {
  if (e.button !== 0 || playerPanel.hidden) return;
  const rect = chartCanvas.getBoundingClientRect();
  const x = e.clientX - rect.left;
  if (x < HIT_LINE_X - 4) return;
  e.preventDefault();
  const ms = chartXToMs(x);
  dragSelect = { anchorMs: ms, currentMs: ms };
  state.exportRange = { startMs: ms, endMs: ms };
  updateExportRangeLabel();
  updateSelectionOverlay();
});

window.addEventListener("mousemove", (e) => {
  if (!dragSelect) return;
  const rect = chartCanvas.getBoundingClientRect();
  const x = Math.max(HIT_LINE_X, e.clientX - rect.left);
  dragSelect.currentMs = chartXToMs(x);
  state.exportRange = {
    startMs: Math.min(dragSelect.anchorMs, dragSelect.currentMs),
    endMs: Math.max(dragSelect.anchorMs, dragSelect.currentMs),
  };
  updateExportRangeLabel();
  updateSelectionOverlay();
});

window.addEventListener("mouseup", () => {
  if (!dragSelect) return;
  dragSelect = null;
  const { startMs, endMs } = state.exportRange;
  if (startMs != null && endMs != null && endMs - startMs < 80) {
    clearExportRange();
  }
});

/* ── 上传交互 ── */

uploadZone.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) handleFile(fileInput.files[0]);
});

uploadZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  uploadZone.classList.add("dragover");
});

uploadZone.addEventListener("dragleave", () => {
  uploadZone.classList.remove("dragover");
});

uploadZone.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadZone.classList.remove("dragover");
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});

window.addEventListener("resize", () => {
  resizeCanvas();
  drawChart();
});

buildLaneLabels();
updateSkylineMinLabel();
resizeCanvas();
drawChart();
