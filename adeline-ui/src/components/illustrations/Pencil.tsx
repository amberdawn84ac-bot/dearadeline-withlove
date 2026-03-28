import React from 'react';
import { IllustrationProps } from './types';

export function Pencil({ size = 24, color = 'currentColor', className }: IllustrationProps) {
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
      <path d="M16 48l8 8 24-24-8-8L16 48Z" />
      <path d="M40 16l8 8" />
      <path d="M18 46l6 6" />
      <path d="M14 52l6 2-2-6" />
    </svg>
  );
}
