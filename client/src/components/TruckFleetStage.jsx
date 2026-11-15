import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const palette = ['#eeb84e', '#68aef4', '#70d4ad'];

export default function TruckFleetStage({ profiles = [], selectedCluster = 0, onSelectCluster, height = 340 }) {
  const mountRef = useRef(null);
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const rendererRef = useRef(null);
  const groupsRef = useRef([]);
  const padsRef = useRef([]);
  const yawRef = useRef(0.12);
  const pitchRef = useRef(0.1);
  const animateRef = useRef(false);
  const drawRef = useRef(() => {});
  const frameRef = useRef(0);
  const [loading, setLoading] = useState(true);
  const [failure, setFailure] = useState('');
  const [rotate, setRotate] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setReducedMotion(query.matches);
    update();
    query.addEventListener?.('change', update);
    return () => query.removeEventListener?.('change', update);
  }, []);

  useEffect(() => { animateRef.current = rotate && !reducedMotion; }, [rotate, reducedMotion]);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return undefined;
    let renderer;
    let scene;
    let camera;
    let observer;
    let disposed = false;
    let loadedModels = [];
    let pointerDown = false;
    let lastX = 0;
    let lastY = 0;
    let pointerStart;
    let pointerMove;
    let pointerEnd;
    let keyDown;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'low-power' });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.12;
      renderer.shadowMap.enabled = true;
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;
      renderer.domElement.tabIndex = 0;
      renderer.domElement.setAttribute('aria-label', 'Three realistic DT-CARGO truck models assigned to clusters 0, 1, and 2. Drag or swipe to rotate; use the arrow keys when focused.');
      renderer.domElement.style.touchAction = 'pan-y';
      mount.appendChild(renderer.domElement);
      scene = new THREE.Scene();
      scene.background = new THREE.Color('#111817');
      scene.fog = new THREE.Fog('#111817', 18, 34);
      camera = new THREE.PerspectiveCamera(31, 1, 0.1, 100);
      camera.position.set(0, 5.3, 14.5);
      camera.lookAt(0, 1.2, 0);
      scene.add(new THREE.HemisphereLight('#d9e8ec', '#18211e', 2.15));
      const key = new THREE.DirectionalLight('#fff0d0', 3.2);
      key.position.set(-4, 9, 7);
      key.castShadow = true;
      scene.add(key);
      const fill = new THREE.DirectionalLight('#a5c9ee', 1.2);
      fill.position.set(7, 4, -6);
      scene.add(fill);
      const floor = new THREE.Mesh(new THREE.PlaneGeometry(28, 16), new THREE.MeshStandardMaterial({ color: '#19211e', roughness: 0.92, metalness: 0.08 }));
      floor.rotation.x = -Math.PI / 2;
      floor.position.y = -0.03;
      floor.receiveShadow = true;
      scene.add(floor);
      const grid = new THREE.GridHelper(28, 28, '#39413d', '#252e2a');
      grid.position.y = -0.015;
      scene.add(grid);
      sceneRef.current = scene;
      cameraRef.current = camera;
      rendererRef.current = renderer;

      const positions = [-4.2, 0, 4.2];
      positions.forEach((x, index) => {
        const group = new THREE.Group();
        group.position.x = x;
        const pad = new THREE.Mesh(new THREE.CircleGeometry(1.8, 64), new THREE.MeshBasicMaterial({ color: palette[index], transparent: true, opacity: 0.07, side: THREE.DoubleSide }));
        pad.rotation.x = -Math.PI / 2;
        pad.position.y = 0.01;
        group.add(pad);
        const ring = new THREE.Mesh(new THREE.RingGeometry(1.72, 1.78, 64), new THREE.MeshBasicMaterial({ color: palette[index], transparent: true, opacity: 0.35, side: THREE.DoubleSide }));
        ring.rotation.x = -Math.PI / 2;
        ring.position.y = 0.035;
        group.add(ring);
        const light = new THREE.PointLight(palette[index], 13, 6, 2);
        light.position.set(0, 0.65, 0);
        group.add(light);
        scene.add(group);
        loadedModels.push(group);
        padsRef.current.push(pad, ring);
      });
      groupsRef.current = loadedModels;

      const updateCamera = () => {
        const radius = 14.5;
        camera.position.set(Math.sin(yawRef.current) * radius, 5.2 + pitchRef.current * 2.2, Math.cos(yawRef.current) * radius);
        camera.lookAt(0, 1.15, 0);
      };
      const render = () => {
        if (!disposed && renderer && scene && camera) renderer.render(scene, camera);
      };
      drawRef.current = () => {
        if (!animateRef.current || disposed) return;
        yawRef.current += 0.0026;
        updateCamera();
        render();
        frameRef.current = requestAnimationFrame(drawRef.current);
      };

      const loader = new GLTFLoader();
      loader.load('/truck.glb', (gltf) => {
        if (disposed) return;
        loadedModels.forEach((group, index) => {
          const truck = gltf.scene.clone(true);
          const initialBounds = new THREE.Box3().setFromObject(truck);
          const size = new THREE.Vector3();
          initialBounds.getSize(size);
          const maxDimension = Math.max(size.x, size.y, size.z) || 1;
          truck.scale.setScalar(3.0 / maxDimension);
          const scaledBounds = new THREE.Box3().setFromObject(truck);
          truck.position.y -= scaledBounds.min.y;
          truck.rotation.y = Math.PI;
          truck.traverse((object) => {
            if (object.isMesh) {
              object.castShadow = true;
              object.receiveShadow = true;
            }
          });
          group.add(truck);
        });
        setLoading(false);
        render();
        if (animateRef.current) drawRef.current();
      }, undefined, (error) => {
        if (!disposed) {
          setFailure(error?.message || 'The local truck model could not be loaded.');
          setLoading(false);
        }
      });

      const resize = () => {
        if (!mount || !renderer || !camera) return;
        const width = Math.max(1, mount.clientWidth);
        const heightPx = Math.max(1, mount.clientHeight);
        renderer.setSize(width, heightPx, false);
        camera.aspect = width / heightPx;
        camera.updateProjectionMatrix();
        render();
      };
      observer = new ResizeObserver(resize);
      observer.observe(mount);
      resize();

      pointerStart = (event) => {
        pointerDown = true;
        lastX = event.clientX;
        lastY = event.clientY;
        renderer.domElement.setPointerCapture?.(event.pointerId);
      };
      pointerMove = (event) => {
        if (!pointerDown) return;
        const dx = event.clientX - lastX;
        const dy = event.clientY - lastY;
        lastX = event.clientX;
        lastY = event.clientY;
        yawRef.current += dx * 0.006;
        pitchRef.current = Math.max(-0.55, Math.min(0.75, pitchRef.current + dy * 0.003));
        updateCamera();
        render();
      };
      pointerEnd = () => { pointerDown = false; };
      keyDown = (event) => {
        if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
        event.preventDefault();
        if (event.key === 'ArrowLeft') yawRef.current -= 0.12;
        if (event.key === 'ArrowRight') yawRef.current += 0.12;
        if (event.key === 'ArrowUp') pitchRef.current = Math.min(0.75, pitchRef.current + 0.06);
        if (event.key === 'ArrowDown') pitchRef.current = Math.max(-0.55, pitchRef.current - 0.06);
        updateCamera();
        render();
      };
      renderer.domElement.addEventListener('pointerdown', pointerStart);
      renderer.domElement.addEventListener('pointermove', pointerMove);
      renderer.domElement.addEventListener('pointerup', pointerEnd);
      renderer.domElement.addEventListener('pointercancel', pointerEnd);
      renderer.domElement.addEventListener('keydown', keyDown);

    } catch (error) {
      setFailure(error?.message || 'WebGL is not available in this browser.');
      setLoading(false);
    }

    return () => {
      disposed = true;
      observer?.disconnect();
      renderer?.domElement.removeEventListener('pointerdown', pointerStart);
      renderer?.domElement.removeEventListener('pointermove', pointerMove);
      renderer?.domElement.removeEventListener('pointerup', pointerEnd);
      renderer?.domElement.removeEventListener('pointercancel', pointerEnd);
      renderer?.domElement.removeEventListener('keydown', keyDown);
      cancelAnimationFrame(frameRef.current);
      renderer?.dispose();
      if (renderer?.domElement.parentNode === mount) mount.removeChild(renderer.domElement);
      loadedModels = [];
      groupsRef.current = [];
      padsRef.current = [];
      sceneRef.current = null;
      cameraRef.current = null;
      rendererRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (rotate && !reducedMotion) {
      if (!frameRef.current) drawRef.current();
    } else {
      cancelAnimationFrame(frameRef.current);
      frameRef.current = 0;
      if (rendererRef.current && sceneRef.current && cameraRef.current) rendererRef.current.render(sceneRef.current, cameraRef.current);
    }
  }, [rotate, reducedMotion]);

  useEffect(() => {
    padsRef.current.forEach((pad, index) => {
      const modelIndex = Math.floor(index / 2);
      const selected = modelIndex === selectedCluster;
      pad.material.opacity = index % 2 === 0 ? (selected ? 0.17 : 0.035) : (selected ? 0.8 : 0.22);
    });
    if (rendererRef.current && sceneRef.current && cameraRef.current) rendererRef.current.render(sceneRef.current, cameraRef.current);
  }, [selectedCluster]);

  const items = [0, 1, 2].map((cluster) => profiles.find((item) => Number(item.cluster) === cluster) || { cluster, episodes: 0, vehicles: 0 });
  return (
    <div className="truck-stage">
      <div className="stage-toolbar">
        <span className="stage-hint">DRAG OR SWIPE TO ROTATE · ARROW KEYS WHEN FOCUSED</span>
        <button className="button button-small button-quiet" onClick={() => setRotate((value) => !value)} disabled={reducedMotion} aria-pressed={rotate && !reducedMotion}>
          {reducedMotion ? 'Reduced motion' : rotate ? 'Pause turntable' : 'Start turntable'}
        </button>
      </div>
      <div className="truck-stage-canvas" ref={mountRef} style={{ '--stage-height': height + 'px' }}>
        {loading ? <div className="stage-overlay" role="status">Loading the local 3D truck model…</div> : null}
        {failure ? <div className="stage-overlay stage-failure" role="status">{failure}<span>Cluster totals remain available below.</span></div> : null}
      </div>
      <div className="truck-bay-list" aria-label="Select a saved cluster">
        {items.map((item, index) => (
          <button key={item.cluster} className={'truck-bay ' + (selectedCluster === Number(item.cluster) ? 'is-selected' : '')} onClick={() => onSelectCluster?.(Number(item.cluster))} aria-pressed={selectedCluster === Number(item.cluster)}>
            <span className="bay-mark" style={{ backgroundColor: palette[index] }} />
            <span><strong>CLUSTER {item.cluster}</strong><small>{Number(item.episodes || 0).toLocaleString()} saved episodes · {Number(item.vehicles || 0).toLocaleString()} vehicles</small></span>
          </button>
        ))}
      </div>
      <p className="stage-footnote">Each bay uses the project’s local realistic truck model; labels and counts come from saved 12-hour episode assignments.</p>
    </div>
  );
}
