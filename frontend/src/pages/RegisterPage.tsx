import React, { useState } from "react";
import { ArrowRight, Shield } from "lucide-react";
import { api } from "../services/api";
import { User } from "../types";
import { FormField } from "../components/ui/FormField";

interface RegisterPageProps {
  onRegisterSuccess: (user: User) => void;
  onNavigateToLogin: () => void;
}

const industries = [
  "General Business Operations",
  "Software & Technology",
  "Manufacturing & Industrial",
  "Food & Beverage / Hospitality",
  "Financial & Legal Services",
  "Photography & Creative Studio",
];

export const RegisterPage: React.FC<RegisterPageProps> = ({ onRegisterSuccess, onNavigateToLogin }) => {
  const [companyName, setCompanyName] = useState("");
  const [industry, setIndustry] = useState(industries[0]);
  const [domain, setDomain] = useState("");
  const [adminName, setAdminName] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [setupToken, setSetupToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRegister = async (event: React.FormEvent) => {
    event.preventDefault();
    if (password !== confirmPassword) { setError("Passwords do not match."); return; }
    if (password.length < 12) { setError("Password must be at least 12 characters."); return; }
    setLoading(true);
    setError(null);
    try {
      const result = await api.registerCompany({
        company_name: companyName.trim(),
        industry,
        domain: domain.trim(),
        admin_name: adminName.trim(),
        admin_email: adminEmail.trim(),
        password,
        setup_token: setupToken.trim(),
      });
      onRegisterSuccess(result.user);
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : "Company setup failed. Check the details and try again.");
    } finally { setLoading(false); }
  };

  return <main className="auth-page">
    <section className="auth-card auth-card-wide" aria-labelledby="setup-title">
      <div className="auth-brand"><span className="brand-mark"><Shield size={17} aria-hidden="true" /></span><span>OracleX</span></div>
      <div className="auth-heading">
        <h1 id="setup-title">Set up company workspace</h1>
        <p>Use the one-time token provided by the company operator to create the first administrator account.</p>
      </div>
      {error && <div className="form-error" role="alert">{error}</div>}
      <form onSubmit={handleRegister} className="auth-form">
        <FormField id="setup-token" label="One-time setup token">
          <input id="setup-token" type="password" className="input-control" value={setupToken} onChange={(event) => setSetupToken(event.target.value)} autoComplete="off" required />
        </FormField>
        <div className="auth-form-grid">
          <FormField id="company-name" label="Company name">
            <input id="company-name" className="input-control" value={companyName} onChange={(event) => setCompanyName(event.target.value)} autoComplete="organization" required />
          </FormField>
          <FormField id="industry" label="Industry">
            <select id="industry" className="input-control" value={industry} onChange={(event) => setIndustry(event.target.value)}>{industries.map((item) => <option key={item} value={item}>{item}</option>)}</select>
          </FormField>
        </div>
        <FormField id="domain" label="Company domain" hint="Optional. Enter the domain only if your company uses one.">
          <input id="domain" className="input-control" value={domain} onChange={(event) => setDomain(event.target.value)} placeholder="company.example" autoComplete="off" />
        </FormField>
        <div className="auth-form-grid">
          <FormField id="admin-name" label="Administrator name">
            <input id="admin-name" className="input-control" value={adminName} onChange={(event) => setAdminName(event.target.value)} autoComplete="name" required />
          </FormField>
          <FormField id="admin-email" label="Administrator work email">
            <input id="admin-email" type="email" className="input-control" value={adminEmail} onChange={(event) => setAdminEmail(event.target.value)} autoComplete="username" required />
          </FormField>
        </div>
        <div className="auth-form-grid">
          <FormField id="admin-password" label="Password" hint="Use at least 12 characters.">
            <input id="admin-password" type="password" className="input-control" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="new-password" minLength={12} required />
          </FormField>
          <FormField id="confirm-password" label="Confirm password">
            <input id="confirm-password" type="password" className="input-control" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} autoComplete="new-password" minLength={12} required />
          </FormField>
        </div>
        <button type="submit" disabled={loading} className="btn-primary auth-submit">{loading ? "Creating workspace…" : "Create workspace"}{!loading && <ArrowRight size={16} aria-hidden="true" />}</button>
      </form>
      <div className="auth-setup"><span>Already have a company account?</span><button type="button" onClick={onNavigateToLogin}>Sign in</button></div>
    </section>
    <p className="auth-footer">First-time setup is available only when enabled by the company operator.</p>
  </main>;
};
