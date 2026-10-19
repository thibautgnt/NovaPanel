// Base de l'Arctis Nova Pro Wireless en 3D : l'ecran affiche l'image OLED en direct,
// la molette tourne avec le volume. Sans WebGL, on affiche l'ecran a plat.
import * as THREE from 'three';
import { RoundedBoxGeometry } from './vendor/RoundedBoxGeometry.js';
import { RoomEnvironment } from './vendor/RoomEnvironment.js';

const W = 1.5, H = 0.5, D = 0.95;
const SCREEN = { w: 0.74, h: 0.37, x: -0.27 };
const KNOB = { r: 0.19, x: 0.47 };
const YAW = 0.42, PITCH = 0.2;

export function createBaseView(container, oled) {
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  } catch {
    oled.className = 'flat';
    container.appendChild(oled);
    return { update() {}, setVolume() {} };
  }
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.domElement.className = 'gl';
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.9;

  const camera = new THREE.PerspectiveCamera(26, 2, 0.1, 50);
  camera.position.set(0, 1.1, 3.2);
  camera.lookAt(0, -0.02, 0);

  const model = new THREE.Group();
  scene.add(model);

  const shell = new THREE.MeshPhysicalMaterial({ color: 0x222429, roughness: 0.55, clearcoat: 0.25, clearcoatRoughness: 0.5 });
  const body = new THREE.Mesh(new RoundedBoxGeometry(W, H, D, 6, 0.07), shell);
  model.add(body);

  // face avant legerement en retrait, plus brillante
  const face = new THREE.Mesh(new RoundedBoxGeometry(W - 0.06, H - 0.08, 0.02, 4, 0.008),
    new THREE.MeshPhysicalMaterial({ color: 0x0c0d0f, roughness: 0.3, clearcoat: 0.6 }));
  face.position.z = D / 2 - 0.002;
  model.add(face);

  const tex = new THREE.CanvasTexture(oled);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(SCREEN.w, SCREEN.h),
    new THREE.MeshBasicMaterial({ map: tex, toneMapped: false }));
  screen.position.set(SCREEN.x, 0, D / 2 + 0.0095);
  model.add(screen);
  const glass = new THREE.Mesh(new THREE.PlaneGeometry(SCREEN.w + 0.03, SCREEN.h + 0.03),
    new THREE.MeshPhysicalMaterial({ color: 0x000000, roughness: 0.05, transparent: true, opacity: 0.18, clearcoat: 1 }));
  glass.position.set(SCREEN.x, 0, D / 2 + 0.011);
  model.add(glass);

  // molette crantee : on deforme le bord du cylindre
  const knobGeo = new THREE.CylinderGeometry(KNOB.r, KNOB.r, 0.09, 180, 1, false);
  const p = knobGeo.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), z = p.getZ(i), r = Math.hypot(x, z);
    if (r > KNOB.r * 0.99) {
      const a = Math.atan2(z, x), k = 1 + 0.025 * (Math.sin(a * 60) > 0 ? 1 : 0);
      p.setXYZ(i, x * k, p.getY(i), z * k);
    }
  }
  knobGeo.computeVertexNormals();
  knobGeo.rotateX(Math.PI / 2);
  const knob = new THREE.Group();
  knob.position.set(KNOB.x, 0, D / 2 + 0.045);
  knob.add(new THREE.Mesh(knobGeo, new THREE.MeshPhysicalMaterial({ color: 0x2b2d32, metalness: 0.7, roughness: 0.35 })));
  const cap = new THREE.Mesh(new THREE.CylinderGeometry(KNOB.r * 0.86, KNOB.r * 0.86, 0.006, 96).rotateX(Math.PI / 2),
    new THREE.MeshPhysicalMaterial({ color: 0x18191c, roughness: 0.45, clearcoat: 0.4 }));
  cap.position.z = 0.046;
  knob.add(cap);
  const mark = new THREE.Mesh(new THREE.CircleGeometry(0.012, 24), new THREE.MeshBasicMaterial({ color: 0xd8dade }));
  mark.position.set(0, KNOB.r * 0.66, 0.05);
  knob.add(mark);
  model.add(knob);

  // trappe de la batterie de rechange, sur le dessus
  const lid = new THREE.Mesh(new RoundedBoxGeometry(0.5, 0.01, 0.6, 3, 0.004),
    new THREE.MeshPhysicalMaterial({ color: 0x101113, roughness: 0.5 }));
  lid.position.set(0.38, H / 2 + 0.001, -0.05);
  model.add(lid);

  const shadowTex = (() => {
    const c = document.createElement('canvas');
    c.width = c.height = 128;
    const g = c.getContext('2d'), grad = g.createRadialGradient(64, 64, 4, 64, 64, 64);
    grad.addColorStop(0, 'rgba(0,0,0,.55)');
    grad.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = grad;
    g.fillRect(0, 0, 128, 128);
    return new THREE.CanvasTexture(c);
  })();
  const shadow = new THREE.Mesh(new THREE.PlaneGeometry(W * 1.9, D * 2.2),
    new THREE.MeshBasicMaterial({ map: shadowTex, transparent: true, depthWrite: false }));
  shadow.rotation.x = -Math.PI / 2;
  shadow.position.y = -H / 2 - 0.001;
  model.add(shadow);

  const key = new THREE.DirectionalLight(0xffffff, 1.6);
  key.position.set(-2, 3, 2.5);
  scene.add(key);

  let yaw = -0.28, pitch = 0, knobAngle = 0, knobTarget = 0, queued = false;
  const render = () => {
    queued = false;
    knobAngle += (knobTarget - knobAngle) * 0.25;
    model.rotation.set(pitch, yaw, 0);
    knob.rotation.z = knobAngle;
    renderer.render(scene, camera);
    if (Math.abs(knobTarget - knobAngle) > 0.002) invalidate();
  };
  const invalidate = () => { if (!queued) { queued = true; requestAnimationFrame(render); } };

  const resize = () => {
    const { clientWidth: w, clientHeight: h } = container;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    // recule la camera si la vue est etroite, pour que la base tienne en largeur
    camera.position.setLength(Math.max(3.1, 5.6 / camera.aspect + 0.4));
    camera.updateProjectionMatrix();
    invalidate();
  };
  new ResizeObserver(resize).observe(container);

  let drag = null;
  container.addEventListener('pointerdown', e => { drag = { x: e.clientX, y: e.clientY, yaw, pitch }; container.setPointerCapture(e.pointerId); });
  container.addEventListener('pointermove', e => {
    if (!drag) return;
    yaw = Math.max(-YAW * 2, Math.min(YAW * 2, drag.yaw + (e.clientX - drag.x) * 0.006));
    pitch = Math.max(-PITCH, Math.min(PITCH * 2, drag.pitch + (e.clientY - drag.y) * 0.004));
    invalidate();
  });
  const end = () => { drag = null; };
  container.addEventListener('pointerup', end);
  container.addEventListener('pointercancel', end);
  container.addEventListener('dblclick', () => { yaw = -0.28; pitch = 0; invalidate(); });

  return {
    update() { tex.needsUpdate = true; invalidate(); },
    // molette : 0 % en butee gauche, 100 % en butee droite
    setVolume(v) { knobTarget = (0.5 - v / 100) * Math.PI * 1.5; invalidate(); },
  };
}
