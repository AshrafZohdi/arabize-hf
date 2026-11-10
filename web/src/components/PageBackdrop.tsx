/** Page background: limestone white, with a faint lattice of eight-point stars (as in Gulf mashrabiya screens) that
 *  fades out below the top of the page. The colour comes from `.page-lattice` in index.css. */
export function PageBackdrop() {
  return (
    <div aria-hidden="true" className="page-light">
      <svg className="page-lattice h-full w-full">
        <defs>
          <pattern id="lattice" width="64" height="64" patternUnits="userSpaceOnUse">
            <g fill="none" stroke="currentColor" strokeWidth="1">
              <rect x="16" y="16" width="32" height="32" />
              <path d="M32 9.4 54.6 32 32 54.6 9.4 32Z" />
              <path d="M32 0V9.4M32 54.6V64M0 32H9.4M54.6 32H64" />
            </g>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#lattice)" />
      </svg>
    </div>
  )
}
