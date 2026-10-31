import React from 'react';

/**
 * RASD AI (رَصْد AI) Official Vector Brand Emblem
 * Features high-precision surveillance optics in Primary Brand Blue-Purple (#707FF0),
 * Dark Purple (#3935A8), Light Blue (#8BA8FF), and Technical Cyan (#45C5F5).
 */
export default function RasdLogo({ size = 28, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="RASD AI Logo"
    >
      <defs>
        <linearGradient id="rasdGrad" x1="4" y1="4" x2="36" y2="36" gradientUnits="userSpaceOnUse">
          <stop stopColor="#707FF0" />
          <stop offset="1" stopColor="#3935A8" />
        </linearGradient>
        <linearGradient id="rasdInnerGrad" x1="12" y1="12" x2="28" y2="28" gradientUnits="userSpaceOnUse">
          <stop stopColor="#45C5F5" />
          <stop offset="1" stopColor="#8BA8FF" />
        </linearGradient>
      </defs>

      {/* Outer Rounded Frame */}
      <rect
        x="2"
        y="2"
        width="36"
        height="36"
        rx="10"
        fill="url(#rasdGrad)"
      />

      {/* Surveillance Optics Outer Ring */}
      <circle
        cx="20"
        cy="20"
        r="12"
        stroke="#8BA8FF"
        strokeWidth="1.75"
        strokeOpacity="0.85"
        strokeDasharray="2 2"
      />

      {/* Inner Precision Aperture */}
      <circle
        cx="20"
        cy="20"
        r="7.5"
        fill="url(#rasdInnerGrad)"
        fillOpacity="0.25"
        stroke="#FFFFFF"
        strokeWidth="2"
      />

      {/* Center AI Intelligence Core */}
      <circle
        cx="20"
        cy="20"
        r="3"
        fill="#45C5F5"
      />

      {/* Corner Precision Alignment Markers */}
      <circle cx="8" cy="8" r="1.25" fill="#8BA8FF" fillOpacity="0.8" />
      <circle cx="32" cy="8" r="1.25" fill="#8BA8FF" fillOpacity="0.8" />
      <circle cx="8" cy="32" r="1.25" fill="#8BA8FF" fillOpacity="0.8" />
      <circle cx="32" cy="32" r="1.25" fill="#8BA8FF" fillOpacity="0.8" />
    </svg>
  );
}
