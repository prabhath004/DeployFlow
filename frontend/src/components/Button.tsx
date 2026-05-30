import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "danger" | "ghost";
type Size = "sm" | "md";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

const base =
  "inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus:ring-1 focus:ring-neutral-500";

const variants: Record<Variant, string> = {
  primary:
    "bg-white text-black hover:bg-neutral-200 active:bg-neutral-300",
  secondary:
    "bg-transparent text-white border border-neutral-700 hover:bg-neutral-900 hover:border-neutral-600",
  danger:
    "bg-transparent text-red-400 border border-red-900/60 hover:bg-red-950/40 hover:border-red-800",
  ghost: "bg-transparent text-neutral-400 hover:text-white hover:bg-neutral-900",
};

const sizes: Record<Size, string> = {
  sm: "h-7 px-2.5 text-xs",
  md: "h-9 px-4 text-sm",
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  className = "",
  children,
  ...rest
}: Props) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
    >
      {loading ? (
        <span className="font-mono text-[0.7rem] opacity-70">…</span>
      ) : null}
      {children}
    </button>
  );
}
