import type { HTMLAttributes } from "react";

interface Props extends HTMLAttributes<HTMLDivElement> {
  interactive?: boolean;
}

export function Card({
  interactive = false,
  className = "",
  children,
  ...rest
}: Props) {
  return (
    <div
      {...rest}
      className={`rounded-lg border border-neutral-800 bg-[#0f0f0f] ${
        interactive
          ? "transition-colors hover:border-neutral-700 hover:bg-[#141414]"
          : ""
      } ${className}`}
    >
      {children}
    </div>
  );
}
