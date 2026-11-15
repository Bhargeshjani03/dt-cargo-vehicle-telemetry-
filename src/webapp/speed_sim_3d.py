"""Interactive replay of one real DT-CARGO speed trace in a local 3D truck scene."""

from __future__ import annotations

import json

import streamlit.components.v1 as components


def render_3d_speed_simulator(
    *,
    track_id: int,
    vehicle_id: int,
    cluster_name: str,
    distance_km: float | None,
    duration_minutes: float | None,
    trace_points: list[list[float]],
    height: int = 560,
) -> None:
    """Replay sampled telemetry; only the road scene is schematic, never GPS."""
    payload = {
        "trackId": int(track_id),
        "vehicleId": int(vehicle_id),
        "cluster": str(cluster_name),
        "distanceKm": round(float(distance_km), 2) if distance_km is not None else None,
        "durationMinutes": round(float(duration_minutes), 1) if duration_minutes is not None else None,
        "points": [[round(float(t), 2), round(float(v), 2), round(float(p), 5)] for t, v, p in trace_points],
    }
    html_code = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  *{box-sizing:border-box}body{margin:0;background:transparent;color:#f2f5f4;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
  button,select,input{font:inherit}button{cursor:pointer}
  #replay{--signal:#84d8b3;position:relative;height:__HEIGHT__px;overflow:hidden;border:1px solid rgba(255,255,255,.12);border-radius:22px;background:#101a1d;isolation:isolate}
  #scene{position:absolute;inset:0;z-index:0}#scene canvas{display:block;width:100%;height:100%}
  .scene-shade{position:absolute;inset:0;z-index:1;pointer-events:none;background:linear-gradient(90deg,rgba(7,14,18,.56),transparent 48%,rgba(7,14,18,.1)),linear-gradient(0deg,rgba(7,14,18,.9),transparent 38%,rgba(7,14,18,.42))}
  .scene-head{position:absolute;z-index:3;left:20px;right:20px;top:17px;display:flex;justify-content:space-between;align-items:flex-start;gap:14px}
  .eyebrow{display:block;color:#a9c6bb;font-size:10px;font-weight:800;letter-spacing:.14em;text-transform:uppercase}
  .title{display:block;margin-top:5px;color:#fff;font-size:clamp(18px,2.2vw,25px);font-weight:760;letter-spacing:-.025em}
  .meta{display:block;margin-top:5px;color:#d0dbd7;font-size:12px}
  .data-badge{display:inline-flex;align-items:center;gap:8px;max-width:44%;padding:9px 11px;border:1px solid rgba(255,255,255,.17);border-radius:12px;background:rgba(13,24,27,.82);color:#e6efeb;font-size:11px;line-height:1.35;text-align:right;backdrop-filter:blur(12px)}
  .data-dot{width:8px;height:8px;flex:0 0 8px;border-radius:50%;background:var(--signal);box-shadow:0 0 0 4px rgba(132,216,179,.13)}
  .telemetry{position:absolute;z-index:3;right:18px;top:94px;display:grid;grid-template-columns:repeat(2,minmax(105px,1fr));gap:8px;width:min(290px,46%)}
  .metric{padding:10px 12px;border:1px solid rgba(255,255,255,.14);border-radius:13px;background:rgba(13,24,27,.82);backdrop-filter:blur(12px)}
  .metric span{display:block;color:#b4c3be;font-size:9px;font-weight:800;letter-spacing:.1em;text-transform:uppercase}
  .metric strong{display:block;margin-top:5px;color:#fff;font-size:18px;font-variant-numeric:tabular-nums;line-height:1.1}
  .scene-note{position:absolute;z-index:3;left:19px;bottom:102px;padding:7px 9px;border-radius:9px;background:rgba(9,17,19,.78);color:#dae4e0;font-size:10px;letter-spacing:.06em;text-transform:uppercase}
  .fallback{display:none;position:absolute;z-index:4;inset:42% 12% auto;text-align:center;padding:12px;border-radius:12px;background:rgba(8,17,20,.9);color:#fff;font-size:13px}
  .controls{position:absolute;z-index:5;left:14px;right:14px;bottom:13px;display:grid;grid-template-columns:auto auto minmax(100px,1fr) auto;align-items:center;gap:9px;padding:10px;border:1px solid rgba(255,255,255,.14);border-radius:15px;background:rgba(10,18,20,.93);backdrop-filter:blur(18px)}
  .control{min-height:44px;padding:0 13px;border:1px solid rgba(255,255,255,.16);border-radius:11px;background:rgba(255,255,255,.08);color:#f3f6f5;font-size:12px;font-weight:720}
  .control.primary{background:#e1f2ea;border-color:#e1f2ea;color:#10221c}.control:hover{border-color:rgba(255,255,255,.4)}
  .control:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #9adbbd;outline-offset:2px}
  .range-wrap{display:grid;grid-template-columns:auto minmax(80px,1fr) auto;align-items:center;gap:9px;min-width:0;color:#c5d1cd;font-size:10px;font-variant-numeric:tabular-nums}
  input[type=range]{width:100%;min-height:32px;accent-color:#84d8b3;touch-action:pan-x}
  select{min-height:44px;padding:0 10px;border:1px solid rgba(255,255,255,.16);border-radius:10px;background:#182426;color:#eef4f1;font-size:11px}
  .scene-tools{position:absolute;z-index:4;left:18px;top:96px;display:flex;gap:7px}
  .scene-tools button{width:42px;height:42px;border:1px solid rgba(255,255,255,.18);border-radius:12px;background:rgba(13,24,27,.78);color:#fff;font-size:19px;backdrop-filter:blur(10px)}
  .scene-tools button:hover{background:rgba(255,255,255,.14)}
  .status{position:absolute;z-index:4;left:19px;bottom:70px;color:#e4ece8;font-size:11px}
  @media(max-width:760px){#replay{height:__MOBILE_HEIGHT__px}.scene-head{left:13px;right:13px;top:13px}.data-badge{max-width:48%;font-size:10px}.telemetry{right:12px;top:82px;width:min(250px,53%);gap:6px}.metric{padding:8px 9px}.metric strong{font-size:16px}.scene-tools{left:12px;top:85px}.scene-note{left:12px;bottom:112px}.controls{left:9px;right:9px;bottom:9px;grid-template-columns:auto auto minmax(75px,1fr);gap:6px;padding:8px}.range-wrap{grid-column:1/-1;grid-row:2}.controls select{grid-column:3;grid-row:1}.controls .control{padding:0 10px;font-size:11px}}
  @media(max-width:460px){#replay{height:__PHONE_HEIGHT__px}.title{font-size:18px}.meta{font-size:10px}.data-badge{max-width:46%;padding:7px;font-size:9px}.telemetry{top:82px;width:51%;grid-template-columns:1fr 1fr}.metric span{font-size:8px}.metric strong{font-size:14px}.scene-tools{top:83px}.scene-tools button{width:38px;height:38px}.scene-note{bottom:122px;max-width:46%;font-size:9px}.status{bottom:86px;font-size:10px;max-width:48%}.controls{grid-template-columns:auto auto minmax(65px,1fr);}.controls select{max-width:86px;padding:0 4px}.controls .control{min-width:0;padding:0 8px}}
  @media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition-duration:.01ms!important;animation-duration:.01ms!important}}
</style>
</head>
<body>
<main id="replay" aria-label="Interactive 3D replay of a recorded truck speed trace">
  <div id="scene" aria-hidden="true"></div><div class="scene-shade" aria-hidden="true"></div>
  <header class="scene-head">
    <div><span class="eyebrow">Recorded telemetry · replay</span><strong class="title">Track <span id="track-label"></span></strong><span class="meta" id="vehicle-meta"></span></div>
    <div class="data-badge"><i class="data-dot" aria-hidden="true"></i><span>Measured speed trace<br>Historical record</span></div>
  </header>
  <div class="scene-tools" aria-label="Truck model view controls">
    <button id="zoom-in" type="button" aria-label="Zoom in on the truck" title="Zoom in">+</button>
    <button id="zoom-out" type="button" aria-label="Zoom out from the truck" title="Zoom out">−</button>
  </div>
  <section class="telemetry" aria-label="Recorded trip telemetry">
    <div class="metric"><span>Recorded speed</span><strong><b id="speed-value">0</b> km/h</strong></div>
    <div class="metric"><span>Trace progress</span><strong id="progress-value">0%</strong></div>
    <div class="metric"><span>Elapsed in trace</span><strong id="elapsed-value">0:00</strong></div>
    <div class="metric"><span>Recorded distance</span><strong id="distance-value">—</strong></div>
  </section>
  <div class="scene-note">Schematic road · no GPS route shown</div>
  <div id="fallback" class="fallback" role="status">The 3D truck model did not load. The recorded speed chart below is still available.</div>
  <div id="playback-status" class="status" role="status" aria-live="polite">Replay ready · press play to follow the recorded speed trace.</div>
  <footer class="controls" aria-label="Replay controls">
    <button class="control primary" id="play" type="button" aria-pressed="false">Play replay</button>
    <button class="control" id="reset" type="button">Restart</button>
    <label class="range-wrap"><span>Start</span><input id="timeline" type="range" min="0" max="1000" step="1" value="0" aria-label="Scrub through recorded trip"><span id="time-total">End</span></label>
    <select id="playback-rate" aria-label="Replay speed">
      <option value="60">60×</option><option value="120" selected>120×</option><option value="240">240×</option>
    </select>
  </footer>
</main>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
<script>
(() => {
  const replay = __PAYLOAD__;
  const points = replay.points || [];
  const $ = (id) => document.getElementById(id);
  $('track-label').textContent = String(replay.trackId);
  $('vehicle-meta').textContent = `Vehicle ${replay.vehicleId} · ${replay.cluster} · drag or pinch to rotate the truck`;
  $('distance-value').textContent = replay.distanceKm == null ? '—' : `${replay.distanceKm.toLocaleString()} km`;
  const durationSec = points.length ? points[points.length - 1][0] : 0;
  const formatTime = (seconds) => {
    const s = Math.max(0, Math.round(seconds));
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
  };
  $('time-total').textContent = formatTime(durationSec);
  let currentTime = 0, running = false, lastFrame = 0, frameHandle = 0;
  let renderer, camera, controls, truck, scene3d;
  const status = $('playback-status');
  const slider = $('timeline');
  slider.max = String(Math.max(1, Math.round(durationSec * 10)));

  function sampleAt(time) {
    if (!points.length) return [0, 0, 0];
    let lo = 0, hi = points.length - 1;
    while (lo < hi) { const mid = (lo + hi) >> 1; if (points[mid][0] < time) lo = mid + 1; else hi = mid; }
    const i = Math.max(0, lo - 1), a = points[i], b = points[Math.min(i + 1, points.length - 1)];
    const span = Math.max(.001, b[0] - a[0]), f = Math.max(0, Math.min(1, (time - a[0]) / span));
    return [a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f, i];
  }
  function renderSample() {
    const [speed, progress] = sampleAt(currentTime);
    $('speed-value').textContent = speed.toFixed(1);
    $('progress-value').textContent = `${Math.round(progress * 100)}%`;
    $('elapsed-value').textContent = formatTime(currentTime);
    slider.value = String(Math.round(currentTime * 10));
    if (truck) {
      const nextZ = 90 - progress * 180;
      const shift = nextZ - controls.target.z;
      truck.position.z = nextZ;
      controls.target.z = nextZ;
      camera.position.z += shift;
    }
    if (renderer && controls && scene3d) { controls.update(); renderer.render(scene3d, camera); }
  }
  function finishFrame(now) {
    if (!running) return;
    if (lastFrame) currentTime += Math.max(0, now - lastFrame) / 1000 * Number($('playback-rate').value);
    lastFrame = now;
    if (currentTime >= durationSec) {
      currentTime = durationSec; running = false; $('play').textContent = 'Replay again'; $('play').setAttribute('aria-pressed', 'false');
      status.textContent = `Replay complete · ${points.length.toLocaleString()} recorded speed samples summarized.`;
    }
    renderSample();
    if (running) frameHandle = requestAnimationFrame(finishFrame);
  }
  $('play').addEventListener('click', () => {
    if (!points.length) { status.textContent = 'No recorded speed samples are available for this track.'; return; }
    if (running) { running = false; cancelAnimationFrame(frameHandle); $('play').textContent = 'Resume replay'; $('play').setAttribute('aria-pressed', 'false'); status.textContent = 'Replay paused · use the slider to inspect the trace.'; return; }
    if (currentTime >= durationSec) currentTime = 0;
    running = true; lastFrame = 0; $('play').textContent = 'Pause replay'; $('play').setAttribute('aria-pressed', 'true');
    status.textContent = 'Replay active · truck motion follows recorded speed samples.'; frameHandle = requestAnimationFrame(finishFrame);
  });
  $('reset').addEventListener('click', () => { running = false; cancelAnimationFrame(frameHandle); currentTime = 0; lastFrame = 0; $('play').textContent = 'Play replay'; $('play').setAttribute('aria-pressed', 'false'); status.textContent = 'Replay reset · ready to follow the recorded speed trace.'; renderSample(); });
  slider.addEventListener('input', () => { running = false; cancelAnimationFrame(frameHandle); currentTime = Number(slider.value) / 10; lastFrame = 0; $('play').textContent = currentTime >= durationSec ? 'Replay again' : 'Play replay'; $('play').setAttribute('aria-pressed', 'false'); status.textContent = 'Trace position adjusted · speed values remain from the recorded track.'; renderSample(); });

  try {
    if (!window.THREE || !THREE.GLTFLoader) throw new Error('3D library is unavailable');
    const container = $('scene');
    scene3d = new THREE.Scene(); scene3d.background = new THREE.Color(0x94a9ad); scene3d.fog = new THREE.Fog(0x94a9ad, 80, 230);
    camera = new THREE.PerspectiveCamera(39, container.clientWidth / container.clientHeight, .1, 260); camera.position.set(10, 6.5, 100);
    renderer = new THREE.WebGLRenderer({antialias:true,alpha:false}); renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5)); renderer.setSize(container.clientWidth, container.clientHeight); renderer.outputEncoding = THREE.sRGBEncoding; renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05; renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap; container.appendChild(renderer.domElement);
    scene3d.add(new THREE.HemisphereLight(0xe7f2ef, 0x36403a, 1.6));
    const sun = new THREE.DirectionalLight(0xfff0d5, 2.4); sun.position.set(-15, 26, 18); sun.castShadow = true; sun.shadow.mapSize.set(1024,1024); scene3d.add(sun);
    const rim = new THREE.DirectionalLight(0xb8d6e4, 1.1); rim.position.set(12, 9, -18); scene3d.add(rim);
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(260,300), new THREE.MeshStandardMaterial({color:0x52635b,roughness:1})); ground.rotation.x = -Math.PI/2; ground.position.y = -.12; ground.receiveShadow = true; scene3d.add(ground);
    const road = new THREE.Mesh(new THREE.PlaneGeometry(12,300), new THREE.MeshStandardMaterial({color:0x30383a,roughness:.91})); road.rotation.x = -Math.PI/2; road.position.y = -.01; road.receiveShadow = true; scene3d.add(road);
    const edgeMat = new THREE.MeshStandardMaterial({color:0xc8cbc1,roughness:.85});
    [-5.65,5.65].forEach(x => { const line = new THREE.Mesh(new THREE.BoxGeometry(.09,.018,300), edgeMat); line.position.set(x,.012,0); scene3d.add(line); });
    const dashMat = new THREE.MeshStandardMaterial({color:0xe2dfc7,roughness:.75});
    for (let z=-102;z<=104;z+=8) { const dash = new THREE.Mesh(new THREE.BoxGeometry(.16,.02,3.5),dashMat); dash.position.set(0,.02,z); dash.userData.baseZ = z; scene3d.add(dash);  }
    const shoulder = new THREE.MeshStandardMaterial({color:0x737d74,roughness:1});
    [-7.8,7.8].forEach(x => { const strip = new THREE.Mesh(new THREE.BoxGeometry(3,.08,300),shoulder); strip.position.set(x,-.06,0); scene3d.add(strip); });
    const controls3d = new THREE.OrbitControls(camera, renderer.domElement); controls3d.enableDamping = true; controls3d.dampingFactor = .08; controls3d.enablePan = false; controls3d.minDistance = 7; controls3d.maxDistance = 24; controls3d.maxPolarAngle = Math.PI/2.04; controls3d.target.set(0,1.2,90); controls = controls3d;
    controls.addEventListener('change', () => renderer.render(scene3d,camera));
    const modelLoader = new THREE.GLTFLoader();
    modelLoader.load('/app/static/truck.glb', (gltf) => {
      truck = gltf.scene; truck.traverse(node => { if (node.isMesh) { node.castShadow = true; node.receiveShadow = true; if (node.material) { node.material.roughness = Math.max(.28, node.material.roughness || .5); } } });
      let bounds = new THREE.Box3().setFromObject(truck), size = bounds.getSize(new THREE.Vector3());
      const scale = 6 / Math.max(size.x, size.z, .01); truck.scale.setScalar(scale);
      bounds = new THREE.Box3().setFromObject(truck); truck.position.y -= bounds.min.y; truck.position.z = 2; truck.rotation.y = Math.PI;
      scene3d.add(truck); renderSample();
    }, undefined, () => { $('fallback').style.display = 'block'; });
    const zoom = (factor) => { const offset = camera.position.clone().sub(controls.target).multiplyScalar(factor).clampLength(7,24); camera.position.copy(controls.target).add(offset); controls.update(); renderer.render(scene3d,camera); };
    $('zoom-in').addEventListener('click', () => zoom(.86));
    $('zoom-out').addEventListener('click', () => zoom(1.16));
    const resize = new ResizeObserver(() => { const w=container.clientWidth,h=container.clientHeight; if(!w||!h)return; camera.aspect=w/h; camera.updateProjectionMatrix(); renderer.setSize(w,h); renderSample(); }); resize.observe(container);
    renderSample();
  } catch (error) { $('fallback').style.display = 'block'; }
})();
</script>
</body></html>"""
    html_code = html_code.replace("__HEIGHT__", str(height))
    html_code = html_code.replace("__MOBILE_HEIGHT__", str(max(470, int(height * 0.94))))
    html_code = html_code.replace("__PHONE_HEIGHT__", str(max(470, int(height * 0.90))))
    html_code = html_code.replace("__PAYLOAD__", json.dumps(payload, separators=(",", ":")))
    components.html(html_code, height=height + 15, scrolling=False)
