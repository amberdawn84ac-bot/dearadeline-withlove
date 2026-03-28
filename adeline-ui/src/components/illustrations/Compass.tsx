import React from 'react';
import { IllustrationProps } from './types';

export function Compass({ size = 24, color = 'currentColor', className }: IllustrationProps) {
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
      <circle cx="32" cy="32" r="18" />
      <path d="M32 10v6" />
      <path d="M32 48v6" />
      <path d="M48 32h6" />
      <path d="M10 32h6" />
      <path d="M26 38l-6 10 18-8 8-18-20 16Z" />
    </svg>
  );
}
