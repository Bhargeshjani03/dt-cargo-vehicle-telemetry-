"""Interactive 3D Cluster Spatial Topology Visualization for DT-CARGO."""

from __future__ import annotations

import json

import streamlit.components.v1 as components


def render_3d_cluster_topology(
    episodes_count: int = 1500,
    clusters_info: list | None = None,
    height: int = 400,
) -> None:
    """Renders assignment-matched trucks on an illustrative 3D route map."""
    palette_hex = ["#0071e3", "#feae0f"]
    fallback_count = max(1, episodes_count // 2)
    source_clusters = clusters_info or [
        {"id": index, "episodes": fallback_count, "vehicles": 0}
        for index in range(2)
    ]
    cluster_rows = [
        {
            "id": int(row.get("id", index)),
            "name": str(row.get("name", f"Cluster {int(row.get('id', index))}")),
            "episodes": max(0, int(row.get("episodes", 0))),
            "vehicles": max(0, int(row.get("vehicles", 0))),
        }
        for index, row in enumerate(source_clusters[:2])
    ]
    if not cluster_rows:
        cluster_rows = [
            {"id": index, "episodes": fallback_count, "vehicles": 0}
            for index in range(2)
        ]
    cluster_info_json = json.dumps(cluster_rows)
    legend_html = "".join(
        f'<div class="legend-item"><span class="legend-dot" style="background:{color};box-shadow:0 0 10px {color};"></span><span class="legend-copy"><strong>{row["name"]}</strong><small>Cluster {row["id"]} · {row["episodes"]:,} episodes · {row["vehicles"]:,} vehicles</small></span></div>'
        for row, color in zip(cluster_rows, palette_hex)
    )
    html_code = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
          overflow: hidden;
          background: transparent;
          font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Inter', sans-serif;
        }}
        #topology-container {{
          position: relative;
          width: 100%;
          height: {height}px;
          border-radius: 20px;
          overflow: hidden;
          background: radial-gradient(ellipse at 78% 15%, rgba(254, 174, 15, .16), transparent 34%), radial-gradient(ellipse at 50% 42%, #252321 0%, #0e0d0c 76%);
          box-shadow: 0 16px 40px rgba(0, 0, 0, 0.45);
          border: 1px solid rgba(255, 255, 255, 0.08);
        }}
        .cluster-hud {{
          position: absolute;
          backdrop-filter: blur(20px) saturate(180%);
          -webkit-backdrop-filter: blur(20px) saturate(180%);
          background: rgba(18, 24, 38, 0.72);
          border: 1px solid rgba(255, 255, 255, 0.12);
          border-radius: 12px;
          padding: 10px 16px;
          color: #fff;
          z-index: 10;
        }}
        .hud-tl {{
          top: 14px;
          left: 14px;
          display: flex;
          align-items: center;
          gap: 10px;
        }}
        .hud-legend {{
          position: absolute;
          left: 14px;
          bottom: 14px;
          display: grid;
          grid-template-columns: repeat({max(1, len(cluster_rows))}, minmax(0, 1fr));
          gap: 7px;
          width: min(460px, calc(100% - 28px));
          z-index: 10;
        }}
        .legend-item {{
          min-width: 0;
          display: flex;
          align-items: center;
          gap: 7px;
          padding: 8px 9px;
          border-radius: 10px;
          background: rgba(28, 25, 23, .9);
          border: 1px solid rgba(255, 255, 255, .16);
          backdrop-filter: blur(12px);
          color: #f5f5f4;
        }}
        .legend-copy {{ display: grid; gap: 2px; min-width: 0; }}
        .legend-item strong {{ color: #fff; font-size: 11px; line-height: 1.2; }}
        .legend-item small {{ color: #d6d3d1; font-size: 10px; line-height: 1.2; white-space: nowrap; }}
        .legend-dot {{
          flex: 0 0 auto;
          width: 9px;
          height: 9px;
          border-radius: 50%;
        }}
        .cluster-kicker {{
          color: #feae0f;
          font-size: 10px;
          font-weight: 800;
          letter-spacing: .14em;
          text-transform: uppercase;
          margin-bottom: 5px;
        }}
        .cluster-title {{
          color: #fff;
          font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
          font-size: clamp(18px, 2.3vw, 23px);
          font-weight: 800;
          letter-spacing: -.025em;
          line-height: 1.02;
          text-transform: uppercase;
        }}
        .scene-help {{
          position:absolute;top:14px;right:14px;z-index:10;display:flex;align-items:center;gap:9px;
          color:#d6d3d1;font-size:10px;letter-spacing:.08em;
        }}
        .scene-help button {{
          min-height:34px;padding:0 11px;border-radius:999px;border:1px solid rgba(255,255,255,.22);
          background:rgba(18,24,38,.86);color:#fff;font:700 11px -apple-system,BlinkMacSystemFont,sans-serif;cursor:pointer;
        }}
        .scene-help button:focus-visible {{ outline:3px solid #ffd174;outline-offset:2px; }}
        @media (max-width: 520px) {{
          .cluster-hud {{ left: 10px; top: 10px; padding: 9px 11px; }}
          .hud-legend {{ left: 10px; bottom: 10px; width: calc(100% - 20px); gap: 5px; }}
          .legend-item {{ gap: 5px; padding: 7px 5px; }}
          .legend-item strong {{ font-size: 10px; }}
          .legend-item small {{ font-size: 9px; }}
          .scene-help {{ right:10px;top:10px;font-size:9px; }}
        }}
      </style>
    </head>
    <body>
      <div id="topology-container">
        <div class="cluster-hud hud-tl">
          <div class="cluster-kicker">DT-CARGO · SAVED TOUR ASSIGNMENTS</div>
          <div class="cluster-title">TWO MOVEMENT<br>PATTERNS.</div>
        </div>
        <div class="scene-help"><span>DRAG TO ORBIT</span><button id="motion-toggle" type="button" aria-pressed="false">Play motion</button></div>
        <div class="hud-legend">{legend_html}</div>
      </div>

      <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>

      <script>
        const container = document.getElementById('topology-container');
        const w = container.clientWidth;
        const h = container.clientHeight;

        const scene = new THREE.Scene();
        scene.fog = new THREE.FogExp2(0x06090f, 0.035);

        const camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 1000);
        camera.position.set(14, 10, 16);

        const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
        renderer.setSize(w, h);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        container.appendChild(renderer.domElement);

        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        let motionEnabled = false;
        controls.autoRotate = false;
        controls.autoRotateSpeed = 0.32;
        const motionToggle = document.getElementById('motion-toggle');
        motionToggle.addEventListener('click', () => {{
          motionEnabled = !motionEnabled;
          controls.autoRotate = motionEnabled;
          motionToggle.textContent = motionEnabled ? 'Pause motion' : 'Play motion';
          motionToggle.setAttribute('aria-pressed', String(motionEnabled));
        }});

        // Ambient & Axis lights
        scene.add(new THREE.AmbientLight(0xffffff, 0.8));
        const p1 = new THREE.PointLight(0x0071e3, 3, 30);
        p1.position.set(10, 10, 10);
        scene.add(p1);

        const p2 = new THREE.PointLight(0x34c759, 2.5, 30);
        p2.position.set(-10, -5, -10);
        scene.add(p2);

        const clusterRows = {cluster_info_json};
        const clusterPositions = [
          new THREE.Vector3(-3.6, 0, 0),
          new THREE.Vector3(3.6, 0, 0)
        ];
        const clusterPalette = [0x0071e3, 0xfeae0f];
        const clusters = clusterRows.map((info, index) => ({{
          info: info,
          center: clusterPositions[index],
          color: new THREE.Color(clusterPalette[index % clusterPalette.length])
        }}));
        const centers = clusters.map((cluster) => cluster.center);
        const colors = clusters.map((cluster) => cluster.color);

        function makeTruck(paintColor) {{
          const truck = new THREE.Group();
          const trailerPaint = new THREE.MeshStandardMaterial({{
            color: paintColor,
            metalness: 0.18,
            roughness: 0.38
          }});
          const cabPaint = new THREE.MeshStandardMaterial({{
            color: paintColor.clone().multiplyScalar(0.82),
            metalness: 0.3,
            roughness: 0.32
          }});
          const trim = new THREE.MeshStandardMaterial({{
            color: 0xd7dde3,
            metalness: 0.58,
            roughness: 0.3
          }});
          const glass = new THREE.MeshStandardMaterial({{
            color: 0x14202d,
            metalness: 0.25,
            roughness: 0.18
          }});
          const rubber = new THREE.MeshStandardMaterial({{
            color: 0x15181c,
            roughness: 0.82
          }});
          const hubMaterial = new THREE.MeshStandardMaterial({{
            color: 0x8995a0,
            metalness: 0.72,
            roughness: 0.26
          }});
          const lamps = new THREE.MeshStandardMaterial({{
            color: 0xffe3a3,
            emissive: 0xffc45e,
            emissiveIntensity: 0.55,
            roughness: 0.25
          }});
          const addBox = (size, material, position) => {{
            const mesh = new THREE.Mesh(
              new THREE.BoxGeometry(size[0], size[1], size[2]),
              material
            );
            mesh.position.set(position[0], position[1], position[2]);
            truck.add(mesh);
          }};

          addBox([1.48, 1.04, 2.3], trailerPaint, [0, 1.08, 0.42]);
          addBox([1.51, 0.09, 2.34], trim, [0, 1.64, 0.42]);
          addBox([1.54, 0.1, 2.38], hubMaterial, [0, 0.51, 0.42]);
          addBox([1.02, 0.92, 1.08], cabPaint, [0, 0.94, -1.18]);
          addBox([0.82, 0.07, 0.7], trim, [0, 1.43, -1.16]);
          addBox([0.73, 0.34, 0.035], glass, [0, 1.19, -1.74]);
          addBox([0.035, 0.29, 0.43], glass, [0.515, 1.12, -1.22]);
          addBox([0.035, 0.29, 0.43], glass, [-0.515, 1.12, -1.22]);
          addBox([1.04, 0.12, 0.16], trim, [0, 0.51, -1.76]);
          addBox([0.17, 0.13, 0.055], lamps, [-0.35, 0.7, -1.78]);
          addBox([0.17, 0.13, 0.055], lamps, [0.35, 0.7, -1.78]);
          addBox([0.045, 0.12, 1.8], trim, [0.75, 1.08, 0.45]);
          addBox([0.045, 0.12, 1.8], trim, [-0.75, 1.08, 0.45]);

          [-1, 1].forEach((side) => {{
            [-1.18, 0.48, 1.08].forEach((axleZ) => {{
              const wheel = new THREE.Mesh(
                new THREE.CylinderGeometry(0.25, 0.25, 0.2, 24),
                rubber
              );
              wheel.rotation.z = Math.PI / 2;
              wheel.position.set(side * 0.78, 0.31, axleZ);
              truck.add(wheel);

              const hub = new THREE.Mesh(
                new THREE.CylinderGeometry(0.12, 0.12, 0.215, 20),
                hubMaterial
              );
              hub.rotation.z = Math.PI / 2;
              hub.position.set(side * 0.79, 0.31, axleZ);
              truck.add(hub);
            }});
          }});
          return truck;
        }}

        clusters.forEach((cluster, index) => {{
          const origin = cluster.center;
          const route = new THREE.CatmullRomCurve3([
            new THREE.Vector3(origin.x - 2.2, 0.08, origin.z - 1.2),
            new THREE.Vector3(origin.x - 1.35, 0.08, origin.z + 0.05),
            new THREE.Vector3(origin.x - 0.25, 0.08, origin.z + 0.95),
            new THREE.Vector3(origin.x + 0.95, 0.08, origin.z + 0.55),
            new THREE.Vector3(origin.x + 2.1, 0.08, origin.z - 0.82)
          ]);
          cluster.route = route;
          cluster.baseY = origin.y + 0.05;

          const road = new THREE.Mesh(
            new THREE.TubeGeometry(route, 72, 0.09, 8, false),
            new THREE.MeshStandardMaterial({{
              color: 0x41444b,
              roughness: 0.92,
              metalness: 0.02
            }})
          );
          scene.add(road);

          const routeTrace = new THREE.Mesh(
            new THREE.TubeGeometry(route, 72, 0.025, 6, false),
            new THREE.MeshBasicMaterial({{
              color: cluster.color,
              transparent: true,
              opacity: 0.92
            }})
          );
          scene.add(routeTrace);

          cluster.stopMarkers = [0.12, 0.5, 0.88].map((progress, markerIndex) => {{
            const marker = new THREE.Mesh(
              new THREE.SphereGeometry(markerIndex === 1 ? 0.105 : 0.075, 18, 18),
              new THREE.MeshStandardMaterial({{
                color: cluster.color,
                emissive: cluster.color,
                emissiveIntensity: markerIndex === 1 ? 0.45 : 0.2,
                roughness: 0.25,
                metalness: 0.2
              }})
            );
            marker.position.copy(route.getPointAt(progress));
            scene.add(marker);
            return marker;
          }});

          const truck = makeTruck(cluster.color);
          truck.position.set(origin.x, cluster.baseY, origin.z);
          truck.rotation.y = Math.PI + (index - 1) * 0.1;
          truck.scale.setScalar(0.84);
          scene.add(truck);
          cluster.truck = truck;
        }});

        // Episode markers follow the illustrative route layout in saved assignment proportions.
        const totalEpisodes = Math.max(
          1,
          clusters.reduce((sum, cluster) => sum + Math.max(0, cluster.info.episodes), 0)
        );
        const clusterWeights = clusters.map((cluster) => Math.max(1, cluster.info.episodes));
        const totalWeight = clusterWeights.reduce((sum, value) => sum + value, 0);
        const N = Math.min(1100, Math.max(240, Math.round(totalEpisodes * 0.025)));
        const positions = new Float32Array(N * 3);
        const colArray = new Float32Array(N * 3);

        for (let i = 0; i < N; i++) {{
          let weightedPick = Math.random() * totalWeight;
          let cIdx = 0;
          while (cIdx < clusters.length - 1 && weightedPick >= clusterWeights[cIdx]) {{
            weightedPick -= clusterWeights[cIdx];
            cIdx += 1;
          }}
          const cluster = clusters[cIdx];
          const point = cluster.route.getPointAt(Math.random());
          const col = cluster.color;
          const i3 = i * 3;
          positions[i3] = point.x + (Math.random() - 0.5) * 0.34;
          positions[i3 + 1] = point.y + 0.04 + Math.random() * 0.16;
          positions[i3 + 2] = point.z + (Math.random() - 0.5) * 0.34;
          colArray[i3] = Math.min(1, col.r + (Math.random() - 0.5) * 0.08);
          colArray[i3 + 1] = Math.min(1, col.g + (Math.random() - 0.5) * 0.08);
          colArray[i3 + 2] = Math.min(1, col.b + (Math.random() - 0.5) * 0.08);
        }}

        const pGeo = new THREE.BufferGeometry();
        pGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        pGeo.setAttribute('color', new THREE.BufferAttribute(colArray, 3));

        const pMat = new THREE.PointsMaterial({{
          size: 0.18,
          vertexColors: true,
          transparent: true,
          opacity: 0.85,
          blending: THREE.AdditiveBlending
        }});
        const cloud = new THREE.Points(pGeo, pMat);
        scene.add(cloud);

        // Operations-style grid beneath the illustrative routes.
        const grid = new THREE.GridHelper(28, 28, 0x55534f, 0x302e2b);
        grid.position.y = -0.08;
        scene.add(grid);

        let clock = new THREE.Clock();
        function animate() {{
          requestAnimationFrame(animate);
          const t = clock.getElapsedTime();
          controls.update();

          clusters.forEach((cluster, index) => {{
            if (motionEnabled && !prefersReducedMotion) {{
              cluster.truck.position.y = cluster.baseY + Math.sin(t * 0.6 + index) * 0.018;
              const pulse = 1 + Math.sin(t * 1.1 + index) * 0.07;
              cluster.stopMarkers[1].scale.set(pulse, pulse, pulse);
            }} else {{
              cluster.truck.position.y = cluster.baseY;
              cluster.stopMarkers[1].scale.set(1, 1, 1);
            }}
          }});

          renderer.render(scene, camera);
        }}
        animate();

        window.addEventListener('resize', () => {{
          const nw = container.clientWidth;
          const nh = container.clientHeight;
          camera.aspect = nw / nh;
          camera.updateProjectionMatrix();
          renderer.setSize(nw, nh);
        }});
      </script>
    </body>
    </html>
    """
    components.html(html_code, height=height + 10)
