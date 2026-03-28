import React from 'react';
import { IllustrationProps } from './types';

export function Lightbulb({ size = 24, color = 'currentColor', className }: IllustrationProps) {
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
      <path d="M24 26c0-6 4-10 8-10s8 4 8 10c0 4-2 7-5 9-1 1-1 2-1 3v2h-4v-2c0-1 0-2-1-3-3-2-5-5-5-9Z" />
      <path d="M28 48h8" />
      <path d="M26 52h12" />
      <path d="M24 30c-3 0-5-2-6-4" />
      <path d="M40 30c3 0 5-2 6-4" />
      <path d="M28 18c0-2 2-4 4-4" />
    </svg>
  );
}
