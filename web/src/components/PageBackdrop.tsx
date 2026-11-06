/** Frosted Dunes backdrop: brand light (CSS), four dune contour lines in --shadow at 50%, 7% fractal-noise grain. */
export function PageBackdrop() {
  return (
    <div aria-hidden="true" className="page-light">
      <svg className="absolute inset-0 h-full w-full" preserveAspectRatio="none" viewBox="0 0 1440 900">
        <defs>
          <filter id="grain">
            <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch" />
            <feColorMatrix type="saturate" values="0" />
          </filter>
        </defs>
        <g fill="none" stroke="var(--shadow)" strokeWidth="1.5" opacity="0.5">
          <path d="M0 640 C 240 590, 420 690, 720 630 S 1200 570, 1440 640" />
          <path d="M0 700 C 260 650, 460 760, 760 690 S 1220 640, 1440 700" />
          <path d="M0 770 C 300 720, 500 820, 800 760 S 1240 710, 1440 770" />
          <path d="M0 840 C 320 800, 540 880, 840 830 S 1260 790, 1440 845" />
        </g>
        <rect width="100%" height="100%" filter="url(#grain)" opacity="0.07" style={{ mixBlendMode: 'multiply' }} />
      </svg>
    </div>
  )
}
