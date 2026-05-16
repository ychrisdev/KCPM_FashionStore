import { useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { auth } from "../api/client";
import { parseApiFieldErrors } from "../utils/apiErrors";
import "../styles/pages/AuthPages.css";

type ResetRequestOk = {
  message?: string;
  dev_note?: string;
  reset_url?: string;
};

function IconMail() {
  return (
    <svg
      className="forgot-input-icon-svg"
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden
    >
      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
      <polyline points="22,6 12,13 2,6" />
    </svg>
  );
}

function IconLockCircle() {
  return (
    <svg
      width="48"
      height="48"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      aria-hidden
    >
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  );
}

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [devReset, setDevReset] = useState<{ url: string; note?: string } | null>(
    null,
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess(false);
    setDevReset(null);

    if (!email) {
      setError("Vui lòng nhập địa chỉ email.");
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError("Địa chỉ email không hợp lệ.");
      return;
    }

    setLoading(true);

    try {
      const data = (await auth.requestPasswordReset(
        email.trim(),
      )) as ResetRequestOk;
      setSuccess(true);
      setDevReset(
        typeof data.reset_url === "string"
          ? { url: data.reset_url, note: data.dev_note }
          : null,
      );
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response?.data) {
        setError(parseApiFieldErrors(err.response.data));
      } else {
        setError("Có lỗi xảy ra. Vui lòng thử lại.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page forgot-page">
      <div className="auth-container">
        <div className="auth-card auth-card--forgot">
          <header className="auth-header forgot-header">
            <div className="forgot-icon" aria-hidden>
              <IconLockCircle />
            </div>
            <h1>Quên mật khẩu</h1>
            <p className="forgot-lead">
              Nhập <strong>email đã đăng ký</strong> trên cửa hàng. Chúng tôi gửi một thư
              chứa liên kết để bạn đặt mật khẩu mới (có thể khác email bạn dùng hàng
              ngày — miễn là đúng tài khoản đã tạo).
            </p>
          </header>

          {success ? (
            <div className="forgot-success" aria-live="polite">
              <div className="forgot-success-icon" aria-hidden>
                <svg
                  width="56"
                  height="56"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>
              </div>
              <h2 className="forgot-success-title">Đã gửi hướng dẫn</h2>
              <p className="forgot-success-text">
                Kiểm tra hộp thư của
              </p>
              <div className="forgot-success-email" title={email}>
                {email}
              </div>
              <p className="forgot-success-text forgot-success-text--muted">
                Mở email và bấm <strong>Đặt lại mật khẩu</strong> (hoặc dùng liên kết
                trong thư). Liên kết có thời hạn.
              </p>
              <ul className="forgot-success-tips">
                <li>Xem thêm mục <strong>Spam / Thư rác</strong></li>
                <li>Sai email? Quay lại và nhập địa chỉ đã dùng lúc đăng ký</li>
              </ul>
              {devReset ? (
                <div className="auth-dev-reset forgot-dev-reset">
                  <p className="auth-field-hint">{devReset.note}</p>
                  <a href={devReset.url} className="auth-link auth-dev-reset__link">
                    Mở liên kết đặt lại (chế độ dev)
                  </a>
                </div>
              ) : null}
              <div className="forgot-success-actions">
                <Link to="/login" className="auth-submit-btn forgot-btn-primary">
                  Quay lại đăng nhập
                </Link>
                <button
                  type="button"
                  className="forgot-btn-secondary"
                  onClick={() => {
                    setSuccess(false);
                    setDevReset(null);
                    setEmail("");
                  }}
                >
                  Gửi lại cho email khác
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="auth-form forgot-form">
              <div className="forgot-callout" role="note">
                <span className="forgot-callout__badge">Lưu ý</span>
                Chỉ gửi được nếu email <strong>đã tồn tại</strong> trong hệ thống. Nếu
                bạn đăng ký bằng Gmail nhưng nhập mail trường (hoặc ngược lại), sẽ không
                nhận được thư.
              </div>

              {error ? (
                <div className="auth-error auth-error--forgot" role="alert">
                  {error}
                </div>
              ) : null}

              <div className="forgot-field">
                <label className="forgot-label" htmlFor="forgot-email">
                  Email nhận liên kết đặt lại mật khẩu
                </label>
                <div className="forgot-input-shell">
                  <span className="forgot-input-icon" aria-hidden>
                    <IconMail />
                  </span>
                  <input
                    type="email"
                    id="forgot-email"
                    name="email"
                    className="forgot-input"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="vd: ban@email.com hoặc maillop@ut.edu.vn"
                    autoComplete="email"
                    inputMode="email"
                    required
                    disabled={loading}
                    aria-invalid={Boolean(error)}
                    aria-describedby="forgot-email-hint"
                  />
                </div>
                <p id="forgot-email-hint" className="forgot-hint">
                  Dùng đúng email bạn đã nhập khi tạo tài khoản FashionStore.
                </p>
              </div>

              <button
                type="submit"
                className="auth-submit-btn forgot-submit"
                disabled={loading}
              >
                {loading ? (
                  <span className="loading-spinner" />
                ) : (
                  "Gửi liên kết đến email này"
                )}
              </button>
            </form>
          )}

          <footer className="auth-footer forgot-footer">
            <p>
              Nhớ mật khẩu?{" "}
              <Link to="/login" className="auth-link">
                Đăng nhập
              </Link>
            </p>
          </footer>
        </div>
      </div>
    </div>
  );
}
