import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api/client";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { Logo } from "../components/Header";
import { ErrorMessage } from "../components/Skeleton";

type Mode = "login" | "register";

export default function LoginPage() {
  const { login, register, token, loading } = useAuth();
  const navigate = useNavigate();

  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (token && !loading) navigate("/projects", { replace: true });
  }, [token, loading, navigate]);

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    if (mode === "register" && password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setSubmitting(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password);
      navigate("/projects", { replace: true });
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
      else setError("Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-black px-4">
      <div className="mb-8">
        <Logo className="text-lg" />
      </div>
      <div className="w-full max-w-sm rounded-lg border border-neutral-800 bg-[#0f0f0f] p-6 shadow-none">
        <div className="mb-6 flex border-b border-neutral-800">
          <TabButton
            active={mode === "login"}
            onClick={() => {
              setMode("login");
              setError(null);
            }}
          >
            Sign in
          </TabButton>
          <TabButton
            active={mode === "register"}
            onClick={() => {
              setMode("register");
              setError(null);
            }}
          >
            Create account
          </TabButton>
        </div>

        <form onSubmit={onSubmit} className="space-y-4">
          <Input
            label="Email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
          <Input
            label="Password"
            type="password"
            autoComplete={
              mode === "login" ? "current-password" : "new-password"
            }
            required
            minLength={mode === "register" ? 8 : undefined}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            hint={mode === "register" ? "Minimum 8 characters." : undefined}
          />

          {error ? <ErrorMessage>{error}</ErrorMessage> : null}

          <Button
            type="submit"
            className="w-full"
            loading={submitting}
            disabled={submitting}
          >
            {mode === "login" ? "Sign in" : "Create account"}
          </Button>
        </form>
      </div>
      <p className="mt-6 font-mono text-[0.7rem] uppercase tracking-wider text-neutral-600">
        v0.1.0 · local dev
      </p>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`-mb-px flex-1 border-b-2 px-3 py-2 text-sm transition-colors ${
        active
          ? "border-white text-white"
          : "border-transparent text-neutral-500 hover:text-neutral-300"
      }`}
    >
      {children}
    </button>
  );
}
