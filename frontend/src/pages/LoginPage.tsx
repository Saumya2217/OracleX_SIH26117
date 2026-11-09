import React, { useEffect, useState } from "react";
import { ArrowRight, Eye, EyeOff, Shield } from "lucide-react";
import { api } from "../services/api";
import { User } from "../types";
import { FormField } from "../components/ui/FormField";

interface LoginPageProps {
  onLoginSuccess: (user: User) => void;
  onNavigateToRegister?: () => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess, onNavigateToRegister }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [bootstrapEnabled, setBootstrapEnabled] = useState(false);

  useEffect(() => {
    let active = true;
    api.getBootstrapStatus()
      .then((result) => active && setBootstrapEnabled(result.enabled))
      .catch(() => active && setBootstrapEnabled(false));
    return () => { active = false; };
  }, []);

  const handleLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await api.login(email, password);
      onLoginSuccess(result.user);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Sign in failed. Check your email and password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="sign-in-title">
        <div className="auth-brand">
          <span className="brand-mark"><Shield size={17} aria-hidden="true" /></span>
          <span>OracleX</span>
        </div>

        <div className="auth-heading">
          <h1 id="sign-in-title">Sign in to your workspace</h1>
          <p>Use your company account to access documents, requests, and assigned work.</p>
        </div>

        {error && <div className="form-error" role="alert">{error}</div>}

        <form onSubmit={handleLogin} className="auth-form">
          <FormField id="email" label="Work email">
            <input
              id="email"
              type="email"
              className="input-control"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="name@company.com"
              autoComplete="username"
              required
            />
          </FormField>

          <FormField id="password" label="Password">
            <div className="password-field">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                className="input-control"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter your password"
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword((visible) => !visible)}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff size={17} aria-hidden="true" /> : <Eye size={17} aria-hidden="true" />}
              </button>
            </div>
          </FormField>

          <button type="submit" disabled={loading} className="btn-primary auth-submit">
            {loading ? "Signing in…" : "Sign in"}
            {!loading && <ArrowRight size={16} aria-hidden="true" />}
          </button>
        </form>

        {onNavigateToRegister && bootstrapEnabled && (
          <div className="auth-setup">
            <span>Starting a new company workspace?</span>
            <button type="button" onClick={onNavigateToRegister}>Run first-time setup</button>
          </div>
        )}
      </section>
      <p className="auth-footer">Access is limited to authorized company members.</p>
    </main>
  );
};
