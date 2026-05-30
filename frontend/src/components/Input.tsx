import { forwardRef, type InputHTMLAttributes } from "react";

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
  error?: string | null;
}

export const Input = forwardRef<HTMLInputElement, Props>(function Input(
  { label, hint, error, className = "", id, ...rest },
  ref,
) {
  const inputId =
    id ?? (label ? `in-${label.replace(/\s+/g, "-").toLowerCase()}` : undefined);
  return (
    <label htmlFor={inputId} className="block">
      {label ? (
        <span className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-neutral-400">
          {label}
        </span>
      ) : null}
      <input
        ref={ref}
        id={inputId}
        {...rest}
        className={`w-full rounded-md border bg-black px-3 py-2 text-sm text-white placeholder-neutral-600 outline-none transition-colors focus:border-neutral-500 ${
          error ? "border-red-800" : "border-neutral-800 hover:border-neutral-700"
        } ${className}`}
      />
      {error ? (
        <span className="mt-1 block text-xs text-red-400">{error}</span>
      ) : hint ? (
        <span className="mt-1 block text-xs text-neutral-500">{hint}</span>
      ) : null}
    </label>
  );
});
