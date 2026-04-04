import { useRef, useMemo, Suspense } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { EffectComposer, Bloom, Vignette } from '@react-three/postprocessing'

/* ─── Strand curve definitions ─── */

interface StrandConfig {
  curve: THREE.CatmullRomCurve3;
  thickness: number;
  zOffset: number; // depth layer control
}

const strandConfigs: StrandConfig[] = [
  {
    // Top Foreground (Thick): Deep sagging U-shape hanging from top-left to top-center
    thickness: 1.0,
    zOffset: 0,
    curve: new THREE.CatmullRomCurve3([
      new THREE.Vector3(-100, -50, -10),
      new THREE.Vector3(-50, 12, 8),   // deep loop hanging down left
      new THREE.Vector3(0, 5, 6),        // rising in the mid-left
      new THREE.Vector3(20, 12, 40),     // hanging slightly mid-right
      new THREE.Vector3(30, 22, 12),      // ascending off screen right
    ], false, 'catmullrom')
  },
  {
    // Bottom Foreground (Thick): An arched hill entering from bottom left, swooping low right
    thickness: 1.0,
    zOffset: 0,
    // Increased Z coordinates across the board to pull this chain much closer to the camera
    curve: new THREE.CatmullRomCurve3([
      new THREE.Vector3(-60, 18, 14),
      new THREE.Vector3(-30, 7, 7),    // arched hill starting low, coming very close
      new THREE.Vector3(0, -3, 12),      // peaking at center
      new THREE.Vector3(20, -14, 7),     // dropping sharply
      new THREE.Vector3(60, -27, 14),    // snaking horizontally bottom right
    ], false, 'catmullrom')
  },
  {
    // Top Background (Thin): Drops almost vertically then sweeps horizontally out right
    thickness: 0.45,
    zOffset: 0,
    curve: new THREE.CatmullRomCurve3([
      new THREE.Vector3(-10, 27, 6),
      new THREE.Vector3(0, 3, 4),        // deep V drop in the middle
      new THREE.Vector3(25, 9, 0),
      new THREE.Vector3(29, -8, 20),
    ], false, 'catmullrom')
  },
  {
    // Bottom Background (Thin): Minimal loop arching up at bottom center
    thickness: 0.45,
    zOffset: 0,
    curve: new THREE.CatmullRomCurve3([
      new THREE.Vector3(-20, -25, 50),
      new THREE.Vector3(-5, -8, 4),   // peeks out bottom center
      new THREE.Vector3(30, -6, 10),
      new THREE.Vector3(80, 5, 10),
    ], false, 'catmullrom')
  },
]

/* ─── Instanced chain links ─── */
import { useGLTF, Environment } from '@react-three/drei'
import type { GLTF } from 'three-stdlib'

type GLTFResult = GLTF & {
  nodes: { Torus009: THREE.Mesh }
  materials: { ['Material.001']: THREE.MeshStandardMaterial }
}

function ChainLinks() {
  const meshRef = useRef<THREE.InstancedMesh>(null!)
  const timeRef = useRef(0)
  const { nodes } = useGLTF('/chain.glb') as GLTFResult

  const caseHardenedTexture = useMemo(() => {
    const canvas = document.createElement('canvas')
    canvas.width = 1024
    canvas.height = 1024
    const context = canvas.getContext('2d')
    if (context) {
      context.fillStyle = '#b0a888' // Base silver/gold
      context.fillRect(0, 0, 1024, 1024)

      const colors = [
        'rgba(30, 80, 200, 0.4)',  // Deep blue
        'rgba(0, 120, 255, 0.3)',  // Bright cyan
        'rgba(180, 150, 40, 0.3)', // Gold/Yellow
        'rgba(120, 40, 180, 0.2)', // Purple/Magenta
        'rgba(150, 160, 180, 0.5)' // Grey/Silver
      ]

      for (let i = 0; i < 3000; i++) {
        context.beginPath()
        context.arc(Math.random() * 1024, Math.random() * 1024, Math.random() * 80 + 10, 0, Math.PI * 2)
        context.fillStyle = colors[Math.floor(Math.random() * colors.length)]
        context.fill()
      }

      for (let i = 0; i < 60000; i++) {
        context.fillStyle = Math.random() > 0.5 ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'
        context.fillRect(Math.random() * 1024, Math.random() * 1024, 2, 2)
      }
    }
    const tex = new THREE.CanvasTexture(canvas)
    tex.colorSpace = THREE.SRGBColorSpace
    tex.wrapS = THREE.RepeatWrapping
    tex.wrapT = THREE.RepeatWrapping
    tex.repeat.set(1.5, 1.5)
    return tex
  }, [])

  const { geometry, instances, totalLinks } = useMemo(() => {
    // Clone geometry so we don't mutate the cached version
    const geo = nodes.Torus009.geometry.clone()

    geo.center()

    geo.computeBoundingBox()
    const size = new THREE.Vector3()
    geo.boundingBox!.getSize(size)
    const axes = [
      { axis: 'x', len: size.x },
      { axis: 'y', len: size.y },
      { axis: 'z', len: size.z }
    ].sort((a, b) => b.len - a.len)

    if (axes[0].axis === 'x') geo.rotateZ(Math.PI / 2)
    else if (axes[0].axis === 'z') geo.rotateX(Math.PI / 2)

    geo.computeBoundingBox()
    geo.boundingBox!.getSize(size)

    if (size.x < size.z) {
      geo.rotateY(Math.PI / 2)
    }

    geo.computeBoundingBox()
    geo.boundingBox!.getSize(size)

    // Base target length for thickness 1.0
    const targetLength = 2.1
    const scaleFactor = targetLength / size.y
    geo.scale(scaleFactor, scaleFactor, scaleFactor)

    // Compute exact lengths and link counts dynamically for each custom curve
    let total = 0
    const instancesData: { curve: THREE.CatmullRomCurve3, thickness: number, zOffset: number, count: number }[] = []

    strandConfigs.forEach(conf => {
      const length = conf.curve.getLength()
      const actualLinkLength = targetLength * conf.thickness
      // Count is curve length / effective reach of the link (accounting for tighter overlap)
      const count = Math.floor(length / (actualLinkLength * 0.65))
      instancesData.push({ curve: conf.curve, thickness: conf.thickness, zOffset: conf.zOffset, count })
      total += count
    })

    return { geometry: geo, instances: instancesData, totalLinks: total }
  }, [nodes])

  // Pre-allocate temp vectors
  const tmpMat = useMemo(() => new THREE.Matrix4(), [])
  const tmpRight = useMemo(() => new THREE.Vector3(), [])
  const tmpUp = useMemo(() => new THREE.Vector3(), [])
  const tmpNeg = useMemo(() => new THREE.Vector3(), [])

  useFrame((_, delta) => {
    if (!meshRef.current) return
    timeRef.current += delta * 0.15

    let idx = 0
    instances.forEach((strand, si) => {
      const { curve, thickness, zOffset, count } = strand
      // Set flow speed. Slightly offset speed per strand for parallax depth illusion.
      let speed = 0.06 + si * 0.015
      // Reverse direction for one bottom chain (3) and top right (2)
      if (si === 2 || si === 3) {
        speed = -speed
      }
      for (let i = 0; i < count; i++) {
        const baseT = i / (count - 1)
        // Offset t by time, modulo 1.0 to loop infinitely along the curve path
        let t = (baseT + timeRef.current * speed) % 1.0
        if (t < 0) t += 1.0 // JS negative modulo fix

        const pos = curve.getPointAt(t)
        const tan = curve.getTangentAt(t).normalize()

        // Push chain forward in z based on zOffset
        pos.z += zOffset

        // Build orthonormal frame
        tmpUp.set(0, 1, 0)
        tmpRight.crossVectors(tan, tmpUp).normalize()
        if (tmpRight.lengthSq() < 0.001) {
          tmpUp.set(0, 0, 1)
          tmpRight.crossVectors(tan, tmpUp).normalize()
        }
        tmpUp.crossVectors(tmpRight, tan).normalize()

        // Alternate link orientation for interlocking
        if (i % 2 === 0) {
          tmpMat.makeBasis(tmpRight, tan, tmpUp)
        } else {
          tmpNeg.copy(tmpRight).negate()
          tmpMat.makeBasis(tmpUp, tan, tmpNeg)
        }

        tmpMat.setPosition(pos)
        // Scale instance matrix by the thickness so 'Thin' chains are physically smaller
        tmpMat.scale(new THREE.Vector3(thickness, thickness, thickness))

        meshRef.current.setMatrixAt(idx, tmpMat)
        idx++
      }
    })

    meshRef.current.instanceMatrix.needsUpdate = true
  })

  return (
    <instancedMesh
      ref={meshRef}
      args={[geometry, undefined, totalLinks]}
      frustumCulled={false}
    >
      <meshPhysicalMaterial
        color="#ffffff"
        map={caseHardenedTexture}
        emissive="#000000"
        emissiveIntensity={0.0}
        metalness={1.0}
        roughness={0.25}
        bumpMap={caseHardenedTexture}
        bumpScale={0.005}
        clearcoat={0.1}
        clearcoatRoughness={0.15}
        iridescence={0.0}
        toneMapped={false}
      />
    </instancedMesh>
  )
}

useGLTF.preload('/chain.glb')

/* ─── Scene ─── */

function Scene() {
  return (
    <>
      <color attach="background" args={['#000000']} />

      <ambientLight intensity={0.15} />
      {/* Neutral key lights to highlight the case-hardened colors */}
      <directionalLight position={[8, 6, 10]} intensity={1.5} color="#ffffff" />
      <directionalLight position={[-8, -4, 8]} intensity={1.0} color="#ffeedd" />
      <directionalLight position={[0, 0, 12]} intensity={0.8} color="#ffffff" />

      {/* Rim lights for edge definition */}
      <directionalLight position={[0, 10, -5]} intensity={1.0} color="#ffffff" />
      <directionalLight position={[0, -10, -5]} intensity={1.0} color="#e0e8f0" />

      {/* Point lights for depth */}
      <pointLight position={[-15, 8, 10]} intensity={1.5} color="#ffffff" distance={40} />
      <pointLight position={[15, -8, 10]} intensity={1.2} color="#ffffff" distance={40} />
      <pointLight position={[0, 0, 15]} intensity={1.0} color="#ffffff" distance={30} />
      <pointLight position={[-10, -10, 8]} intensity={1.0} color="#ffffff" distance={25} />
      <pointLight position={[10, 10, 8]} intensity={1.0} color="#ffffff" distance={25} />

      <Suspense fallback={null}>
        <Environment preset="city" environmentIntensity={0.5} />
        <group scale={1.0} position={[0, 0, 0]}>
          <ChainLinks />
        </group>
      </Suspense>

      <EffectComposer>
        <Bloom
          intensity={1.5}
          luminanceThreshold={0.15}
          luminanceSmoothing={0.9}
          mipmapBlur
        />
        <Vignette eskil={false} offset={0.1} darkness={1.1} />
      </EffectComposer>
    </>
  )
}

/* ─── App ─── */

export default function App() {
  return (
    <Canvas
      camera={{ position: [0, 0, 15], fov: 85 }}
      style={{ width: '100vw', height: '100vh', background: '#000' }}
      gl={{ antialias: true, alpha: false }}
      dpr={[1, 2]}
    >
      <Scene />
    </Canvas>
  )
}
