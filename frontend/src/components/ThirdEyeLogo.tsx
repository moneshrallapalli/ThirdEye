import React, { useState, useEffect, useRef } from 'react';

interface ThirdEyeLogoProps {
  isPrivate?: boolean;
  bgColor?: string;
  width?: number;
  height?: number;
}

const ThirdEyeLogo: React.FC<ThirdEyeLogoProps> = ({
  isPrivate = false,
  bgColor = '#FAF9F7',
  width = 176,
  height = 130,
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [pupilOffset, setPupilOffset] = useState({ x: 0, y: 0 });

  // Global mouse tracking — disabled while private
  useEffect(() => {
    if (isPrivate) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!svgRef.current) return;
      const rect = svgRef.current.getBoundingClientRect();
      const eyeCenterX = rect.left + rect.width * (55 / 110);
      const eyeCenterY = rect.top + rect.height * (45 / 82);
      const dx = e.clientX - eyeCenterX;
      const dy = e.clientY - eyeCenterY;
      const svgX = dx * (110 / rect.width);
      const svgY = dy * (82 / rect.height);
      const maxR = 7;
      const dist = Math.sqrt(svgX * svgX + svgY * svgY);
      const scale = dist > maxR ? maxR / dist : 1;
      setPupilOffset({ x: svgX * scale, y: svgY * scale });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [isPrivate]);

  // Snap pupil to "looking away" position when private
  useEffect(() => {
    if (isPrivate) {
      setPupilOffset({ x: 10, y: -7 }); // Up-right: innocently not watching
    }
  }, [isPrivate]);

  const pupilStyle: React.CSSProperties = {
    animation: 'none',
    transform: `translate(${pupilOffset.x}px, ${pupilOffset.y}px)`,
    transition: isPrivate
      ? 'transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)'
      : 'transform 0.08s ease-out',
  };

  return (
    <svg
      ref={svgRef}
      width={width}
      height={height}
      viewBox="0 0 110 82"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      overflow="visible"
    >
      <defs>
        <clipPath id="auth-eye-clip">
          <path d="M3 45 C24 16 86 16 107 45 C86 74 24 74 3 45 Z"/>
        </clipPath>
      </defs>

      {/* Eyebrow */}
      <path
        d="M20 10 C42 2 68 2 90 10"
        stroke="#1A1714"
        strokeWidth="2.4"
        strokeLinecap="round"
        fill="none"
        opacity="0.5"
        className="eye-brow"
      />

      {/* Eye corner accents */}
      <line x1="3"   y1="45" x2="0"   y2="45" stroke="#1A1714" strokeWidth="1.2" opacity="0.25"/>
      <line x1="107" y1="45" x2="110" y2="45" stroke="#1A1714" strokeWidth="1.2" opacity="0.25"/>

      <g clipPath="url(#auth-eye-clip)">
        <path d="M3 45 C24 16 86 16 107 45 C86 74 24 74 3 45 Z" fill="rgba(26,23,20,0.04)"/>

        {/* Circuit traces — left sclera */}
        <path d="M 4 45 H 35"              className="ct-trace ct-a"/>
        <path d="M 7 50 H 21 V 45 H 35"    className="ct-trace ct-b"/>
        <path d="M 11 40 H 36"             className="ct-trace ct-c"/>
        <path d="M 20 32 V 40 H 37"        className="ct-trace ct-d"/>
        {/* Circuit traces — right sclera */}
        <path d="M 106 45 H 75"            className="ct-trace ct-a"/>
        <path d="M 103 50 H 89 V 45 H 75"  className="ct-trace ct-b"/>
        <path d="M 99 40 H 74"             className="ct-trace ct-c"/>
        <path d="M 90 32 V 40 H 73"        className="ct-trace ct-d"/>
        {/* Circuit traces — top/bottom */}
        <path d="M 48 18 V 27 H 52"        className="ct-trace ct-c"/>
        <path d="M 62 18 V 27 H 58"        className="ct-trace ct-d"/>
        <path d="M 48 72 V 63 H 52"        className="ct-trace ct-d"/>
        <path d="M 62 72 V 63 H 58"        className="ct-trace ct-c"/>

        {/* Junction nodes */}
        <circle cx="21" cy="45" r="1.4" className="ct-dot ct-dot-b"/>
        <circle cx="89" cy="45" r="1.4" className="ct-dot ct-dot-b"/>
        <circle cx="20" cy="40" r="1.1" className="ct-dot ct-dot-d"/>
        <circle cx="90" cy="40" r="1.1" className="ct-dot ct-dot-d"/>
        <circle cx="52" cy="27" r="1.1" className="ct-dot ct-dot-c"/>
        <circle cx="58" cy="27" r="1.1" className="ct-dot ct-dot-d"/>
        <circle cx="52" cy="63" r="1.1" className="ct-dot ct-dot-d"/>
        <circle cx="58" cy="63" r="1.1" className="ct-dot ct-dot-c"/>

        {/* Iris rings */}
        <circle cx="55" cy="45" r="20" stroke="#1A1714" strokeWidth="1"   fill="rgba(26,23,20,0.05)" opacity="0.5"/>
        <circle cx="55" cy="45" r="13" stroke="#1A1714" strokeWidth="0.7" fill="none"                opacity="0.2"/>

        {/* Orbiting scanner dot */}
        <g className="iris-orbit">
          <circle cx="55" cy="25" r="1.1" fill="#1A1714" opacity="0.12" transform="rotate(-24 55 45)"/>
          <circle cx="55" cy="25" r="1.4" fill="#1A1714" opacity="0.22" transform="rotate(-15 55 45)"/>
          <circle cx="55" cy="25" r="1.7" fill="#1A1714" opacity="0.38" transform="rotate(-8  55 45)"/>
          <line x1="55" y1="45" x2="55" y2="25" stroke="#1A1714" strokeWidth="0.8" opacity="0.12"/>
          <circle cx="55" cy="25" r="2.6" fill="#1A1714" opacity="0.9"/>
        </g>

        {/* Pupil — tracks mouse or looks away */}
        <g style={pupilStyle}>
          <circle cx="55" cy="45" r="8" fill="#1A1714"/>
          <circle cx="58.5" cy="41.5" r="2.4" fill="white" opacity="0.85"/>
        </g>

        {/* Iris ping */}
        <circle cx="55" cy="45" r="8" fill="none" stroke="#1A1714" strokeWidth="1.2" className="iris-ping"/>

        {/* Eyelids — color matches page background */}
        <rect x="-5" y="-5"  width="120" height="55" fill={bgColor} className="eyelid-top"/>
        <rect x="-5" y="45"  width="120" height="42" fill={bgColor} className="eyelid-bottom"/>
      </g>

      {/* Eye outline */}
      <path
        d="M3 45 C24 16 86 16 107 45 C86 74 24 74 3 45 Z"
        fill="none"
        stroke="#1A1714"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      {/* Lower lid crease */}
      <path
        d="M18 54 C38 63 72 63 92 54"
        stroke="#1A1714"
        strokeWidth="0.8"
        fill="none"
        opacity="0.13"
      />

      {/* Whistling notes — float up when eye is politely not watching */}
      {isPrivate && (
        <>
          <text
            x="94" y="30"
            fontSize="11"
            fill="#1A1714"
            className="whistle-note"
            style={{ userSelect: 'none', fontFamily: 'serif' }}
          >
            ♪
          </text>
          <text
            x="104" y="19"
            fontSize="8"
            fill="#1A1714"
            className="whistle-note-2"
            style={{ userSelect: 'none', fontFamily: 'serif' }}
          >
            ♫
          </text>
        </>
      )}
    </svg>
  );
};

export default ThirdEyeLogo;
