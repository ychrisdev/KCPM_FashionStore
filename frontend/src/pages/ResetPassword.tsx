import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import axios from "axios";
import { auth } from "../api/client";
import "../styles/pages/AuthPages.css";

function apiErrorMessage(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    const d = err.response?.data as Record<string, unknown> | undefined;
    if (d?.detail) {
      if (typeof d.detail === "string") return d.detail;
      if (Array.isArray(d.detail) && typeof d.detail[0] === "string") {
        return d.detail[0];
      }
    }
    if (d && typeof d === "object") {
      for (const v of Object.values(d)) {
        if (Array.isArray(v) && typeof v[0] === "string") return v[0];
        if (typeof v === "string") return v;
      }
    }
  }
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const userIdRaw = searchParams.get("user_id") ?? "";

  const userId = useMemo(() => {
    const n = parseInt(userIdRaw, 10);
    return Number.isFinite(n) && n > 0 ? n : null;
  }, [userIdRaw]);

  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const linkInvalid = !token || userId === null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (linkInvalid || userId === null) return;

    if (password.length < 8) {
      setError("Mật khẩu phải có ít nhất 8 ký tự");
      return;
    }
    if (password !== passwordConfirm) {
      setError("Mật khẩu xác nhận không khớp");
      return;
    }

    setLoading(true);
    try {
      await auth.confirmPasswordReset({
        user_id: userId,
        token,
        new_password: password,
        new_password_confirm: passwordConfirm,
      });
      setSuccess(true);
    } catch (err: unknown) {
      setError(apiErrorMessage(err, "Không đặt lại được mật khẩu. Vui lòng thử lại."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-header">
            <div className="forgot-icon">
              <svg
                width="48"
                height="48"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
            </div>
            <h1>Đặt lại mật khẩu</h1>
            <p>Nhập mật khẩu mới cho tài khoản của bạn</p>
          </div>

          {linkInvalid ? (
            <div className="auth-error" style={{ marginBottom: "1rem" }}>
              Liên kết không hợp lệ hoặc thiếu thông tin. Vui lòng dùng đúng liên kết
              trong email hoặc yêu cầu gửi lại.
            </div>
          ) : null}

          {success ? (
            <div className="auth-success">
              <svg
                width="64"
                height="64"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
              <h2>Đã đổi mật khẩu</h2>
              <p>Bạn có thể đăng nhập bằng mật khẩu mới.</p>
              <Link
                to="/login"
                className="auth-submit-btn"
                style={{ marginTop: "20px", display: "inline-block", textAlign: "center" }}
              >
                Đăng nhập
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="auth-form">
              {error ? <div className="auth-error">{error}</div> : null}

              <div className="form-group">
                <label htmlFor="new-password">Mật khẩu mới</label>
                <div style={{ position: "relative" }}>
                  <input
                    type={showPassword ? "text" : "password"}
                    id="new-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Tối thiểu 8 ký tự"
                    required
                    minLength={8}
                    disabled={linkInvalid}
                    autoComplete="new-password"
                  />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="new-password-confirm">Xác nhận mật khẩu</label>
                <input
                  type={showPassword ? "text" : "password"}
                  id="new-password-confirm"
                  value={passwordConfirm}
                  onChange={(e) => setPasswordConfirm(e.target.value)}
                  placeholder="Nhập lại mật khẩu"
                  required
                  minLength={8}
                  disabled={linkInvalid}
                  autoComplete="new-password"
                />
              </div>

              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  marginBottom: "12px",
                  fontSize: "0.9rem",
                  cursor: "pointer",
                }}
              >
                <input
                  type="checkbox"
                  checked={showPassword}
                  onChange={(e) => setShowPassword(e.target.checked)}
                />
                Hiện mật khẩu
              </label>

              <button
                type="submit"
                className="auth-submit-btn"
                disabled={loading || linkInvalid}
              >
                {loading ? <span className="loading-spinner" /> : "Lưu mật khẩu mới"}
              </button>
            </form>
          )}

          <div className="auth-footer">
            <p>
              <Link to="/forgot-password" className="auth-link">
                Gửi lại email đặt lại mật khẩu
              </Link>
              {" · "}
              <Link to="/login" className="auth-link">
                Đăng nhập
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
