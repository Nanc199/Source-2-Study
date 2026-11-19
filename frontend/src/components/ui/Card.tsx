'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  onClick?: () => void;
}

const paddingMap = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
};

export default function Card({
  children,
  className = '',
  hover = false,
  padding = 'md',
  onClick,
}: CardProps) {
  const Component = hover ? motion.div : 'div';
  const motionProps = hover
    ? {
        whileHover: { y: -2, boxShadow: '0 8px 30px rgba(0,0,0,0.08)' },
        transition: { duration: 0.2 },
      }
    : {};

  return (
    <Component
      className={`
        bg-white rounded-2xl border border-navy-100 shadow-sm
        ${hover ? 'cursor-pointer' : ''}
        ${paddingMap[padding]}
        ${className}
      `}
      onClick={onClick}
      {...motionProps}
    >
      {children}
    </Component>
  );
}
