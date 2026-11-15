"""Interactive local 3D truck model for the DT-CARGO fleet workspace."""

from __future__ import annotations

from textwrap import dedent

import streamlit.components.v1 as components


def render_3d_fleet_canvas(
    active_vehicles: int = 0,
    tracks_count: int = 0,
    recorded_km: float = 0.0,
    height: int = 440,
) -> None:
    """Show the local cargo-truck model with touch, mouse, and keyboard controls."""
    html_code = dedent(
        """
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <style>
            * { box-sizing: border-box; }
            html, body { margin: 0; width: 100%; height: 100%; overflow: hidden; }
            body { color: #f4f6f7; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
            #canvas-container {
              position: relative; width: 100%; height: __HEIGHT__px; overflow: hidden;
              border: 1px solid rgba(255,255,255,.12); border-radius: 20px;
              background: radial-gradient(ellipse at 52% 38%, #35484d 0%, #1a272c 48%, #10191e 100%);
              box-shadow: 0 16px 38px rgba(0,0,0,.2);
            }
            canvas { display: block; width: 100%; height: 100%; cursor: grab; touch-action: pan-y; }
            canvas:active { cursor: grabbing; }
            .truck-poster {
              position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover;
              padding: 0; opacity: .62; pointer-events: none;
            }
            .scene-label, .motion-toggle, .scene-controls, .hud-stats {
              position: absolute; z-index: 3; border: 1px solid rgba(255,255,255,.18);
              background: rgba(14,23,28,.78); backdrop-filter: blur(12px) saturate(130%);
              -webkit-backdrop-filter: blur(12px) saturate(130%);
            }
            .scene-label { top: 12px; left: 12px; padding: 9px 12px; border-radius: 12px; }
            .scene-eyebrow { color: #bfc9ca; font-size: 11px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }
            .scene-title { margin-top: 2px; font-size: 13px; font-weight: 750; }
            .motion-toggle {
              top: 12px; right: 12px; min-height: 40px; padding: 0 12px;
              color: #f4f6f7; border-radius: 999px; font-size: 12px; font-weight: 700; cursor: pointer;
            }
            .scene-controls {
              right: 12px; bottom: 70px; display: flex; gap: 5px; padding: 5px; border-radius: 12px;
            }
            .scene-controls button {
              min-width: 40px; min-height: 40px; padding: 0 9px;
              border: 1px solid rgba(255,255,255,.13); border-radius: 9px;
              color: #f4f6f7; background: rgba(255,255,255,.07);
              font: 700 12px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; cursor: pointer;
            }
            .scene-controls button:hover, .motion-toggle:hover { background: rgba(255,255,255,.15); }
            button:focus-visible, canvas:focus-visible { outline: 3px solid #b7d8e4; outline-offset: 2px; }
            .hud-stats {
              left: 12px; right: 12px; bottom: 12px; display: flex; gap: 8px; padding: 7px;
              border-radius: 13px;
            }
            .stat-pill { display: flex; flex: 1; min-width: 0; flex-direction: column; gap: 2px; padding: 5px 8px; }
            .stat-label { color: #c1cbcd; font-size: 11px; font-weight: 650; }
            .stat-num { color: #fff; font-size: 14px; font-weight: 760; white-space: nowrap; }
            .scene-error { position: absolute; inset: 50% 16px auto; z-index: 4; text-align: center; color: #f4f6f7; font-size: 12px; }
            @media (max-width: 520px) {
              #canvas-container { height: min(__HEIGHT__px, 330px); border-radius: 16px; }
              .scene-label { max-width: calc(100% - 120px); }
              .scene-title { font-size: 12px; }
              .scene-controls { bottom: 68px; }
              .scene-controls button { min-width: 38px; min-height: 40px; }
              .hud-stats { gap: 2px; padding: 5px; }
              .stat-pill { padding: 4px 5px; }
              .stat-label { font-size: 10px; }
              .stat-num { font-size: 12px; }
            }
            @media (prefers-reduced-motion: reduce) {
              *, *::before, *::after { scroll-behavior: auto !important; transition: none !important; }
            }
          </style>
        </head>
        <body>
          <div id="canvas-container" aria-label="Interactive 3D cargo-truck model">
            <img class="truck-poster" id="truck-poster" src="/app/static/truck-medium.jpg" alt="Illustrative blue freight truck on a highway">
            <div class="scene-label">
              <div class="scene-eyebrow">Historic fleet records</div>
              <div class="scene-title">DT-CARGO truck model</div>
            </div>
            <button class="motion-toggle" id="motion-toggle" type="button" aria-pressed="false">Start slow turn</button>
            <div class="scene-controls" role="group" aria-label="Truck view controls">
              <button id="turn-left" type="button" aria-label="Turn truck left">←</button>
              <button id="turn-right" type="button" aria-label="Turn truck right">→</button>
              <button id="zoom-in" type="button" aria-label="Zoom in">+</button>
              <button id="zoom-out" type="button" aria-label="Zoom out">−</button>
              <button id="reset-view" type="button" aria-label="Reset truck view">Reset</button>
            </div>
            <div class="hud-stats" aria-label="Recorded fleet totals">
              <div class="stat-pill"><span class="stat-label">Vehicles</span><span class="stat-num">__VEHICLES__</span></div>
              <div class="stat-pill"><span class="stat-label">Tracks</span><span class="stat-num">__TRACKS__</span></div>
              <div class="stat-pill"><span class="stat-label">Recorded distance</span><span class="stat-num">__DISTANCE__ km</span></div>
            </div>
            <div class="scene-error" id="scene-error" role="status" hidden>3D model unavailable. An illustrative truck image is shown instead.</div>
          </div>
          <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
          <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
          <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
          <script>
            const container = document.getElementById('canvas-container');
            const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
            const toggle = document.getElementById('motion-toggle');
            let autoTurn = false;
            let controlsActive = false;
            let settleFrames = 0;
            let animationFrame = 0;
            let renderer;
            let controls;
            try {
              const width = Math.max(1, container.clientWidth);
              const height = Math.max(1, container.clientHeight);
              const scene = new THREE.Scene();
              scene.background = new THREE.Color('#18252b');
              scene.fog = new THREE.Fog('#18252b', 22, 48);
              const camera = new THREE.PerspectiveCamera(36, width / height, .1, 100);
              camera.position.set(9, 6, 15);
              camera.lookAt(0, 1, 0);
              renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'low-power' });
              renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
              renderer.outputEncoding = THREE.sRGBEncoding;
              renderer.toneMapping = THREE.ACESFilmicToneMapping;
              renderer.toneMappingExposure = 1.08;
              renderer.shadowMap.enabled = true;
              renderer.shadowMap.type = THREE.PCFSoftShadowMap;
              renderer.domElement.tabIndex = 0;
              renderer.domElement.setAttribute('aria-label', '3D cargo truck. Drag or swipe to rotate. Use the labeled view buttons or arrow keys when focused.');
              container.appendChild(renderer.domElement);
              controls = new THREE.OrbitControls(camera, renderer.domElement);
              controls.enableDamping = true;
              controls.dampingFactor = .075;
              controls.enablePan = false;
              controls.minDistance = 6;
              controls.maxDistance = 25;
              controls.maxPolarAngle = Math.PI / 2.04;
              controls.target.set(0, 1.15, 0);
              controls.autoRotate = false;
              controls.autoRotateSpeed = .42;

              scene.add(new THREE.HemisphereLight('#edf2f1', '#283238', 2.1));
              const keyLight = new THREE.DirectionalLight('#fff0d7', 3.1);
              keyLight.position.set(-5, 9, 7);
              keyLight.castShadow = true;
              scene.add(keyLight);
              const fillLight = new THREE.DirectionalLight('#a8c9d6', 1.2);
              fillLight.position.set(7, 5, -6);
              scene.add(fillLight);
              const floor = new THREE.Mesh(
                new THREE.CircleGeometry(8, 64),
                new THREE.MeshStandardMaterial({ color: '#202d32', roughness: .88, metalness: .08 })
              );
              floor.rotation.x = -Math.PI / 2;
              floor.position.y = -.03;
              floor.receiveShadow = true;
              scene.add(floor);
              for (const radius of [4.4, 6.5]) {
                const ring = new THREE.Mesh(
                  new THREE.RingGeometry(radius - .012, radius + .012, 96),
                  new THREE.MeshBasicMaterial({ color: '#80a6ac', transparent: true, opacity: .2, side: THREE.DoubleSide })
                );
                ring.rotation.x = -Math.PI / 2;
                ring.position.y = .01;
                scene.add(ring);
              }

              const render = () => {
                if (!renderer || !controls) return;
                controls.update();
                renderer.render(scene, camera);
                if (autoTurn || controlsActive || settleFrames > 0) {
                  if (settleFrames > 0) settleFrames -= 1;
                  animationFrame = requestAnimationFrame(render);
                } else animationFrame = 0;
              };
              const renderOnce = () => {
                if (animationFrame) return;
                animationFrame = requestAnimationFrame(() => {
                  animationFrame = 0;
                  controls.update();
                  renderer.render(scene, camera);
                });
              };
              const loader = new THREE.GLTFLoader();
              loader.load('/app/static/truck.glb', (gltf) => {
                const truck = gltf.scene;
                const bounds = new THREE.Box3().setFromObject(truck);
                const size = new THREE.Vector3();
                bounds.getSize(size);
                truck.scale.setScalar(6.5 / (Math.max(size.x, size.y, size.z) || 1));
                const scaledBounds = new THREE.Box3().setFromObject(truck);
                truck.position.y -= scaledBounds.min.y;
                truck.rotation.y = Math.PI;
                truck.traverse((object) => {
                  if (object.isMesh) { object.castShadow = true; object.receiveShadow = true; }
                });
                scene.add(truck);
                document.getElementById('truck-poster').hidden = true;
                renderOnce();
              }, undefined, () => {
                document.getElementById('scene-error').hidden = false;
              });

              const turn = (amount) => {
                controls.rotateLeft(amount);
                controls.update();
                renderer.render(scene, camera);
              };
              const zoom = (factor) => {
                if (factor < 1) controls.dollyIn(1 / factor);
                else controls.dollyOut(factor);
                controls.update();
                renderer.render(scene, camera);
              };
              document.getElementById('turn-left').addEventListener('click', () => turn(Math.PI / 10));
              document.getElementById('turn-right').addEventListener('click', () => turn(-Math.PI / 10));
              document.getElementById('zoom-in').addEventListener('click', () => zoom(.88));
              document.getElementById('zoom-out').addEventListener('click', () => zoom(1.14));
              document.getElementById('reset-view').addEventListener('click', () => {
                controls.reset();
                renderer.render(scene, camera);
              });
              renderer.domElement.addEventListener('keydown', (event) => {
                if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', '+', '-', '='].includes(event.key)) return;
                event.preventDefault();
                if (event.key === 'ArrowLeft') turn(Math.PI / 12);
                if (event.key === 'ArrowRight') turn(-Math.PI / 12);
                if (event.key === 'ArrowUp') zoom(.92);
                if (event.key === 'ArrowDown') zoom(1.09);
                if (event.key === '+' || event.key === '=') zoom(.88);
                if (event.key === '-') zoom(1.14);
              });
              controls.addEventListener('change', () => {
                if (!autoTurn) renderer.render(scene, camera);
              });
              controls.addEventListener('start', () => {
                controlsActive = true;
                settleFrames = 0;
                if (!animationFrame) animationFrame = requestAnimationFrame(render);
              });
              controls.addEventListener('end', () => {
                controlsActive = false;
                settleFrames = 24;
                if (!animationFrame) animationFrame = requestAnimationFrame(render);
              });
              toggle.disabled = reducedMotion.matches;
              if (reducedMotion.matches) toggle.textContent = 'Reduced motion';
              toggle.addEventListener('click', () => {
                if (reducedMotion.matches) return;
                autoTurn = !autoTurn;
                controls.autoRotate = autoTurn;
                toggle.textContent = autoTurn ? 'Pause slow turn' : 'Start slow turn';
                toggle.setAttribute('aria-pressed', String(autoTurn));
                if (autoTurn) render();
                else {
                  cancelAnimationFrame(animationFrame);
                  animationFrame = 0;
                  renderer.render(scene, camera);
                }
              });
              reducedMotion.addEventListener?.('change', (event) => {
                toggle.disabled = event.matches;
                if (event.matches) {
                  autoTurn = false;
                  controls.autoRotate = false;
                  toggle.textContent = 'Reduced motion';
                  toggle.setAttribute('aria-pressed', 'false');
                  cancelAnimationFrame(animationFrame);
                  animationFrame = 0;
                  renderer.render(scene, camera);
                } else {
                  toggle.textContent = 'Start slow turn';
                }
              });
              window.addEventListener('resize', () => {
                const nextWidth = Math.max(1, container.clientWidth);
                const nextHeight = Math.max(1, container.clientHeight);
                camera.aspect = nextWidth / nextHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(nextWidth, nextHeight);
                renderer.render(scene, camera);
              });
              renderer.render(scene, camera);
            } catch (error) {
              document.getElementById('scene-error').hidden = false;
            }
          </script>
        </body>
        </html>
        """
    )
    html_code = (
        html_code.replace("__HEIGHT__", str(max(280, int(height))))
        .replace("__VEHICLES__", f"{max(0, int(active_vehicles)):,}")
        .replace("__TRACKS__", f"{max(0, int(tracks_count)):,}")
        .replace("__DISTANCE__", f"{max(0.0, float(recorded_km)):,.0f}")
    )
    components.html(html_code, height=height + 10, scrolling=False)
