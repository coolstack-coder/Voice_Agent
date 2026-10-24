import { Canvas, useFrame } from "@react-three/fiber";
import { ContactShadows, Float, RoundedBox, Sparkles } from "@react-three/drei";
import { cloneElement, useMemo, useRef, type ReactElement } from "react";
import * as THREE from "three";
import { voice } from "../audio";

export type MascotState = "idle" | "listening" | "thinking" | "speaking";

const INK = "#2B2250";
const STATE_COLOR: Record<MascotState, string> = {
  idle: "#FFB800",
  listening: "#FF5A5F",
  thinking: "#8B5CF6",
  speaking: "#2EC4B6",
};

// 3-step gradient map = hard cel-shading bands, the "cartoon" look
function useToonGradient() {
  return useMemo(() => {
    const data = new Uint8Array([150, 210, 255]);
    const tex = new THREE.DataTexture(data, data.length, 1, THREE.RedFormat);
    tex.minFilter = tex.magFilter = THREE.NearestFilter;
    tex.needsUpdate = true;
    return tex;
  }, []);
}

function Toon({ color, emissive }: { color: string; emissive?: string }) {
  const gradientMap = useToonGradient();
  return (
    <meshToonMaterial
      color={color}
      gradientMap={gradientMap}
      emissive={emissive ?? "#000"}
      emissiveIntensity={emissive ? 0.6 : 0}
    />
  );
}


/** Cartoon ink line: the same geometry, slightly bigger, drawn back-faces only in ink. */
function Inked({
  geometry,
  color,
  emissive,
  ink = 0.05,
  ...props
}: { geometry: ReactElement; color: string; emissive?: string; ink?: number } & JSX.IntrinsicElements["group"]) {
  return (
    <group {...props}>
      <mesh castShadow>
        {geometry}
        <Toon color={color} emissive={emissive} />
      </mesh>
      <mesh scale={1 + ink}>
        {cloneElement(geometry)}
        <meshBasicMaterial color={INK} side={THREE.BackSide} />
      </mesh>
    </group>
  );
}

function Kavach({ state }: { state: MascotState }) {
  const root = useRef<THREE.Group>(null!);
  const mouth = useRef<THREE.Mesh>(null!);
  const eyes = useRef<THREE.Group>(null!);
  const bulb = useRef<THREE.Group>(null!);
  const armL = useRef<THREE.Group>(null!);
  const armR = useRef<THREE.Group>(null!);
  const orbit = useRef<THREE.Group>(null!);
  const waves = useRef<THREE.Group>(null!);
  const color = STATE_COLOR[state];

  useFrame(({ clock }, dt) => {
    const t = clock.elapsedTime;
    const lvl = voice.level;
    // lean towards the user while listening, gentle sway otherwise
    const lean = state === "listening" ? 0.18 : 0;
    root.current.rotation.x = THREE.MathUtils.damp(root.current.rotation.x, lean, 6, dt);
    root.current.rotation.y = Math.sin(t * 0.6) * 0.18;
    // mouth opens with the voice level
    const open = state === "speaking" ? 0.3 + Math.min(lvl, 1) * 0.9 : state === "listening" ? 0.45 : 0.22;
    mouth.current.scale.y = THREE.MathUtils.damp(mouth.current.scale.y, open, 18, dt);
    // blink every ~3.5s
    const blink = t % 3.5 < 0.12 ? 0.1 : 1;
    eyes.current.scale.y = THREE.MathUtils.damp(eyes.current.scale.y, state === "thinking" ? 0.55 : blink, 30, dt);
    // antenna bulb pulses
    const s = 1 + (state === "idle" ? Math.sin(t * 2) * 0.08 : lvl * 0.9 + Math.sin(t * 8) * 0.06);
    bulb.current.scale.setScalar(s);
    // arms: wave hello when idle, flap a little while speaking
    const wave = state === "idle" ? Math.sin(t * 3) * 0.5 - 0.9 : state === "speaking" ? -0.4 - lvl : -0.25;
    armR.current.rotation.z = THREE.MathUtils.damp(armR.current.rotation.z, wave, 8, dt);
    armL.current.rotation.z = THREE.MathUtils.damp(armL.current.rotation.z, state === "thinking" ? 1.2 : 0.25, 8, dt);
    orbit.current.rotation.y = t * 3;
    orbit.current.visible = state === "thinking";
    waves.current.visible = state === "listening";
    waves.current.children.forEach((m, i) => {
      const p = (t * 0.9 + i / 3) % 1;
      m.scale.setScalar(0.6 + p * 1.6 + lvl);
      ((m as THREE.Mesh).material as THREE.MeshBasicMaterial).opacity = (1 - p) * 0.6;
    });
  });

  return (
    <group ref={root} position={[0, -0.15, 0]}>
      {/* body */}
      <Inked scale={[1, 1.08, 0.92]} geometry={<sphereGeometry args={[1, 48, 48]} />} color="#FFC21A" ink={0.035} />
      {/* belly badge: little shield */}
      <Inked position={[0, -0.72, 0.62]} rotation={[1.0, 0, 0]} geometry={<cylinderGeometry args={[0.16, 0.16, 0.08, 6]} />} color={color} ink={0.12} />
      {/* visor */}
      <RoundedBox args={[1.3, 0.72, 0.5]} radius={0.3} smoothness={6} position={[0, 0.18, 0.72]}>
        <Toon color={INK} />
      </RoundedBox>
      {/* eyes */}
      <group ref={eyes} position={[0, 0.24, 0.99]}>
        {[-0.28, 0.28].map((x) => (
          <mesh key={x} position={[x, 0, 0]}>
            <capsuleGeometry args={[0.09, 0.14, 8, 16]} />
            <meshBasicMaterial color="#9FF7EE" />
          </mesh>
        ))}
      </group>
      {/* mouth */}
      <group position={[0, -0.36, 0.9]} rotation={[-0.35, 0, 0]}>
        <mesh ref={mouth} scale={[1, 0.3, 1]}>
          <sphereGeometry args={[0.16, 24, 16]} />
          <meshBasicMaterial color="#7A1F3D" />
        </mesh>
      </group>
      {/* cheeks */}
      {[-0.52, 0.52].map((x) => (
        <mesh key={x} position={[x * 1.05, -0.3, 0.74]} scale={[1, 0.6, 0.4]}>
          <sphereGeometry args={[0.11, 16, 16]} />
          <meshBasicMaterial color="#FF9E9E" transparent opacity={0.8} />
        </mesh>
      ))}
      {/* antenna */}
      <mesh position={[0, 1.22, 0]}>
        <cylinderGeometry args={[0.035, 0.035, 0.42]} />
        <Toon color={INK} />
      </mesh>
      <group ref={bulb} position={[0, 1.5, 0]}>
        <Inked geometry={<sphereGeometry args={[0.14, 24, 24]} />} color={color} emissive={color} ink={0.18} />
      </group>
      {/* arms */}
      <group ref={armL} position={[-0.95, -0.1, 0]}>
        <Inked position={[-0.18, -0.2, 0]} rotation={[0, 0, -0.6]} geometry={<capsuleGeometry args={[0.13, 0.35, 8, 16]} />} color="#FFC21A" ink={0.12} />
      </group>
      <group ref={armR} position={[0.95, -0.1, 0]}>
        <Inked position={[0.18, -0.2, 0]} rotation={[0, 0, 0.6]} geometry={<capsuleGeometry args={[0.13, 0.35, 8, 16]} />} color="#FFC21A" ink={0.12} />
      </group>
      {/* thinking orbit */}
      <group ref={orbit} position={[0, 1.95, 0]}>
        {[0, 1, 2].map((i) => (
          <mesh key={i} position={[Math.cos((i * Math.PI * 2) / 3) * 0.45, 0, Math.sin((i * Math.PI * 2) / 3) * 0.45]}>
            <sphereGeometry args={[0.08, 16, 16]} />
            <meshBasicMaterial color="#8B5CF6" />
          </mesh>
        ))}
      </group>
      {/* listening sound waves */}
      <group ref={waves} position={[0, 0.1, 1.1]}>
        {[0, 1, 2].map((i) => (
          <mesh key={i}>
            <torusGeometry args={[0.6, 0.025, 8, 64]} />
            <meshBasicMaterial color="#FF5A5F" transparent opacity={0.5} />
          </mesh>
        ))}
      </group>
    </group>
  );
}

/** The golden-hour ring: a 3D arc that drains as the minutes run out. */
function HourRing({ fraction, urgent }: { fraction: number; urgent: boolean }) {
  const ref = useRef<THREE.Mesh>(null!);
  const geo = useMemo(
    () => new THREE.TorusGeometry(1.85, 0.09, 16, 128, Math.max(0.001, fraction) * Math.PI * 2),
    [Math.round(fraction * 200)],
  );
  useFrame(({ clock }) => {
    const pulse = urgent ? 1 + Math.sin(clock.elapsedTime * 6) * 0.03 : 1;
    ref.current.scale.setScalar(pulse);
  });
  return (
    <group rotation={[Math.PI / 2, 0, Math.PI / 2]} position={[0, -1.35, 0]}>
      <mesh>
        <torusGeometry args={[1.85, 0.05, 12, 128]} />
        <meshBasicMaterial color="#2B2250" transparent opacity={0.12} />
      </mesh>
      <mesh ref={ref} geometry={geo}>
        <meshToonMaterial color={urgent ? "#FF5A5F" : "#FFB800"} emissive={urgent ? "#FF5A5F" : "#FFB800"} emissiveIntensity={0.35} />
      </mesh>
    </group>
  );
}

function Coins() {
  const group = useRef<THREE.Group>(null!);
  const coins = useMemo(
    () => Array.from({ length: 7 }, (_, i) => ({
      x: (i % 2 ? 1 : -1) * (2.1 + (i % 3) * 0.45),
      y: -0.6 + (i % 3) * 0.9,
      z: -1.2 + Math.sin(i * 1.7) * 0.8,
      s: 0.18 + (i % 3) * 0.05,
    })),
    [],
  );
  useFrame(({ clock }) => {
    group.current.children.forEach((c, i) => {
      c.rotation.y = clock.elapsedTime * (1 + i * 0.15);
      c.position.y = coins[i].y + Math.sin(clock.elapsedTime + i) * 0.15;
    });
  });
  return (
    <group ref={group}>
      {coins.map((c, i) => (
        <Inked key={i} position={[c.x, c.y, c.z]} rotation={[Math.PI / 2, 0, 0]}
          geometry={<cylinderGeometry args={[c.s, c.s, c.s * 0.3, 32]} />} color="#FFC94A" ink={0.1} />
      ))}
    </group>
  );
}

export function MascotScene({
  state,
  ringFraction,
  urgent,
}: {
  state: MascotState;
  ringFraction: number | null;
  urgent: boolean;
}) {
  return (
    <Canvas camera={{ position: [0, 0.35, 4.6], fov: 42 }} dpr={[1, 2]} shadows flat>
      <ambientLight intensity={1.1} />
      <directionalLight position={[3, 5, 4]} intensity={1.6} castShadow />
      <directionalLight position={[-4, 2, -2]} intensity={0.5} color="#B9A7FF" />
      <Float speed={2.2} rotationIntensity={0.15} floatIntensity={0.6}>
        <Kavach state={state} />
      </Float>
      {ringFraction !== null && <HourRing fraction={ringFraction} urgent={urgent} />}
      <Coins />
      <Sparkles count={40} scale={[6, 4, 3]} size={3} speed={0.4} color="#FFB800" />
      <ContactShadows position={[0, -1.55, 0]} opacity={0.35} scale={6} blur={2.4} far={3} color={INK} />
    </Canvas>
  );
}
