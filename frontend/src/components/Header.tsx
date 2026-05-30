import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function Logo({ className = "" }: { className?: string }) {
  return (
    <Link
      to="/projects"
      className={`group inline-flex items-center gap-2 font-mono text-base font-semibold tracking-tight text-white ${className}`}
    >
      <span aria-hidden className="text-white">
        {"▲"}
      </span>
      <span className="lowercase">deployflow</span>
    </Link>
  );
}

export function Header() {
  const { user, logout, token } = useAuth();
  const navigate = useNavigate();

  if (!token) return null;

  return (
    <header className="sticky top-0 z-30 border-b border-neutral-900 bg-black/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-4">
          <Logo />
          <span className="hidden text-neutral-700 sm:inline">/</span>
          <Link
            to="/projects"
            className="hidden text-sm text-neutral-400 transition-colors hover:text-white sm:inline"
          >
            projects
          </Link>
        </div>
        <div className="flex items-center gap-3">
          {user ? (
            <span className="hidden font-mono text-xs text-neutral-500 sm:inline">
              {user.email}
            </span>
          ) : null}
          <button
            type="button"
            onClick={() => {
              logout();
              navigate("/login", { replace: true });
            }}
            className="rounded-md border border-neutral-800 px-3 py-1.5 text-xs text-neutral-300 transition-colors hover:border-neutral-700 hover:text-white"
          >
            Sign out
          </button>
        </div>
      </div>
    </header>
  );
}

export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-black text-neutral-100">
      <Header />
      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">{children}</main>
    </div>
  );
}
