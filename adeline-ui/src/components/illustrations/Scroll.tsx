import React from 'react';
import { IllustrationProps } from './types';

export function Scroll({ size = 24, color = 'currentColor', className }: IllustrationProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      stroke={color}
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M18 18h28v26c0 4-3 6-6 6H24c-4 0-6-2-6-6V18Z" />
      <path d="M18 24h28" />
      <path d="M24 32h16" />
      <path d="M24 38h12" />
      <path d="M18 44c-2 0-4 2-4 4 0 3 2 4 4 4" />
      <path d="M46 18c2 0 4-2 4-4 0-3-2-4-4-4" />
    </svg>
  );
}
