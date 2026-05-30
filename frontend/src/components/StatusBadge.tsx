import type { DeploymentStatus } from "../api/types";

interface Props {
  status: string;
  size?: "sm" | "md";
}

type Tone = {
  bg: string;
  border: string;
  text: string;
  dot: string;
  animated: boolean;
};

const PALETTE: Record<string, Tone> = {
  PENDING: {
    bg: "bg-neutral-900",
    border: "border-neutral-700",
    text: "text-neutral-300",
    dot: "bg-neutral-500",
    animated: false,
  },
  QUEUED: {
    bg: "bg-neutral-900",
    border: "border-neutral-700",
    text: "text-neutral-300",
    dot: "bg-neutral-500",
    animated: false,
  },
  RETRYING: {
    bg: "bg-neutral-900",
    border: "border-neutral-700",
    text: "text-neutral-300",
    dot: "bg-neutral-400",
    animated: true,
  },
  RUNNING: {
    bg: "bg-amber-950/40",
    border: "border-amber-900/70",
    text: "text-amber-300",
    dot: "bg-amber-400",
    animated: true,
  },
  BUILDING: {
    bg: "bg-amber-950/40",
    border: "border-amber-900/70",
    text: "text-amber-300",
    dot: "bg-amber-400",
    animated: true,
  },
  PUSHING_IMAGE: {
    bg: "bg-amber-950/40",
    border: "border-amber-900/70",
    text: "text-amber-300",
    dot: "bg-amber-400",
    animated: true,
  },
  DEPLOYING: {
    bg: "bg-amber-950/40",
    border: "border-amber-900/70",
    text: "text-amber-300",
    dot: "bg-amber-400",
    animated: true,
  },
  SUCCEEDED: {
    bg: "bg-emerald-950/40",
    border: "border-emerald-900/70",
    text: "text-emerald-300",
    dot: "bg-emerald-400",
    animated: false,
  },
  FAILED: {
    bg: "bg-red-950/40",
    border: "border-red-900/70",
    text: "text-red-300",
    dot: "bg-red-400",
    animated: false,
  },
  CANCELLED: {
    bg: "bg-slate-900/60",
    border: "border-slate-700/60",
    text: "text-slate-300",
    dot: "bg-slate-400",
    animated: false,
  },
};

const FALLBACK: Tone = {
  bg: "bg-neutral-900",
  border: "border-neutral-800",
  text: "text-neutral-400",
  dot: "bg-neutral-600",
  animated: false,
};

export function StatusBadge({ status, size = "sm" }: Props) {
  const tone = PALETTE[status as DeploymentStatus] ?? FALLBACK;
  const sz =
    size === "md"
      ? "h-7 px-2.5 text-[0.7rem] gap-2"
      : "h-5 px-2 text-[0.65rem] gap-1.5";
  return (
    <span
      className={`inline-flex items-center rounded-full border font-mono font-semibold uppercase tracking-wider ${tone.bg} ${tone.border} ${tone.text} ${sz}`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${tone.dot} ${tone.animated ? "animate-pulse-dot" : ""}`}
        aria-hidden
      />
      {status}
    </span>
  );
}
