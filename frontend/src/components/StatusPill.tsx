import React from 'react';

export type PillVariant = 'success' | 'warning' | 'danger' | 'neutral' | 'info';
export type PillSize = 'sm' | 'md';

interface StatusPillProps {
  variant?: PillVariant;
  children: React.ReactNode;
  icon?: React.ReactNode;
  pulse?: boolean;
  size?: PillSize;
  className?: string;
}

export const StatusPill: React.FC<StatusPillProps> = ({
  variant = 'neutral',
  children,
  icon,
  pulse = false,
  size = 'md',
  className = '',
}) => {
  const getVariantStyles = (v: PillVariant) => {
    switch (v) {
      case 'success':
        return 'bg-[#e6f7ec] text-[#006323] border-[#a7f3d0]';
      case 'warning':
        return 'bg-[#fef7e6] text-[#b45309] border-[#fde68a]';
      case 'danger':
        return 'bg-[#feecee] text-[#b91c1c] border-[#fecaca]';
      case 'info':
        return 'bg-[#e0f2fe] text-[#0369a1] border-[#bae6fd]';
      case 'neutral':
      default:
        return 'bg-[#f1f3ee] text-[#202318] border-[#e9ebe3]';
    }
  };

  const getSizeStyles = (s: PillSize) => {
    switch (s) {
      case 'sm':
        return 'text-[11px] px-2.5 py-0.5';
      case 'md':
      default:
        return 'text-xs px-3 py-1';
    }
  };

  const getPulseDotColor = (v: PillVariant) => {
    switch (v) {
      case 'success':
        return 'bg-[#006323]';
      case 'warning':
        return 'bg-amber-500';
      case 'danger':
        return 'bg-rose-500';
      case 'info':
        return 'bg-sky-500';
      case 'neutral':
      default:
        return 'bg-[#707367]';
    }
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-bold border ${getVariantStyles(
        variant
      )} ${getSizeStyles(size)} ${className}`}
    >
      {pulse && (
        <span className="relative flex h-2 w-2">
          <span
            className={`animate-ping absolute inline-flex h-full w-full rounded-full ${getPulseDotColor(
              variant
            )} opacity-75`}
          />
          <span
            className={`relative inline-flex rounded-full h-2 w-2 ${getPulseDotColor(
              variant
            )}`}
          />
        </span>
      )}
      {icon && <span className="shrink-0">{icon}</span>}
      <span>{children}</span>
    </span>
  );
};
