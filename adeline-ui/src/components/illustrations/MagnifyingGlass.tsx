import React from 'react';
import { IllustrationProps } from './types';

export function MagnifyingGlass({ size = 24, color = 'currentColor', className }: IllustrationProps) {
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
      <circle cx="28" cy="28" r="12" />
      <path d="M36 36l16 16" />
      <path d="M24 24c2-2 6-2 8 0" />
    </svg>
  );
}
