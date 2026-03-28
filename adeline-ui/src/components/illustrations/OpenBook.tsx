import React from 'react';
import { IllustrationProps } from './types';

export function OpenBook({ size = 24, color = 'currentColor', className }: IllustrationProps) {
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
      <path d="M12 16h18c4 0 6 2 6 6v26c-2-2-4-3-6-3H12V16Z" />
      <path d="M52 16H34c-4 0-6 2-6 6v26c2-2 4-3 6-3h18V16Z" />
      <path d="M28 22c-2-1-4-2-6-2h-6" />
      <path d="M36 22c2-1 4-2 6-2h6" />
      <path d="M28 30c-2-1-4-2-6-2h-6" />
      <path d="M36 30c2-1 4-2 6-2h6" />
    </svg>
  );
}
