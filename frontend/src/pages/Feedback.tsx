import { useState } from "react";
import { Link } from "react-router-dom";
import { site } from "../api/client";
import { useAuth } from "../context/AuthContext";
import SupportSubnav from "../components/SupportSubnav";
import "../styles/pages/Feedback.css";

const MAX_LEN = 2000;

export default function Feedback() {
  const { user } = useAuth();
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<{
    type: "ok" | "err";
    text: string;
  } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;
    setStatus(null);
    setLoading(true);
    try {
      await site.sendFeedback(message.trim());
      setStatus({
        type: "ok",
        text: "Cảm ơn bạn đã góp ý — chúng tôi đã ghi nhận.",
      });
      setMessage("");
    } catch {
      setStatus({
        type: "err",
        text: "Không gửi được. Vui lòng thử lại sau.",
      });
    } finally {
      setLoading(false);
    }
  };

  const len = message.length;

  return (
    <div className="feedback-page">
      <section className="feedback-hero">
        <div className="feedback-heroMesh" aria-hidden />
        <div className="feedback-heroFloat feedback-heroFloat--1" aria-hidden />
        <div className="feedback-heroFloat feedback-heroFloat--2" aria-hidden />
        <div className="feedback-heroFloat feedback-heroFloat--3" aria-hidden />
        <div
          className="feedback-heroBlob feedback-heroBlob--left"
          aria-hidden
        />
        <div
          className="feedback-heroBlob feedback-heroBlob--right"
          aria-hidden
        />
        <div className="feedback-heroInner">
          <p className="feedback-heroBadge">
            <span className="feedback-heroBadgeDot" aria-hidden />
            Tiếng nói của bạn
          </p>
          <h1 className="feedback-heroTitle">
            <span className="feedback-heroTitleGrad">Góp ý</span>
            <span className="feedback-heroTitleRest"> cho FashionStore</span>
          </h1>
          <p className="feedback-heroLead">
            Mỗi ý kiến đều quý — từ giao diện, tốc độ tải đến cách chúng tôi hỗ
            trợ bạn.
          </p>
          <div className="feedback-heroPills" role="list">
            <span className="feedback-pill" role="listitem">
              Website &amp; app
            </span>
            <span className="feedback-pill" role="listitem">
              Dịch vụ &amp; CSKH
            </span>
            <span className="feedback-pill" role="listitem">
              Trải nghiệm mua sắm
            </span>
          </div>
          <SupportSubnav />
        </div>
      </section>

      <div className="feedback-layout">
        <aside className="feedback-aside">
          <div className="feedback-tipCard feedback-tipCard--a">
            <div className="feedback-tipIcon" aria-hidden>
              <svg viewBox="0 0 32 32" fill="none">
                <path
                  d="M8 10h16v12H8V10z"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinejoin="round"
                />
                <path
                  d="M12 22v4h8v-4"
                  stroke="currentColor"
                  strokeWidth="1.8"
                />
                <path
                  d="M16 6v4"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                />
              </svg>
            </div>
            <div>
              <h3 className="feedback-tipTitle">Góp ý chung</h3>
              <p className="feedback-tipText">
                Nhận xét về cửa hàng, giao diện, cách phục vụ — lưu theo tài
                khoản khi đã đăng nhập.
              </p>
            </div>
          </div>
          <div className="feedback-tipCard feedback-tipCard--b">
            <div className="feedback-tipIcon" aria-hidden>
              <svg viewBox="0 0 32 32" fill="none">
                <path
                  d="M6 26l4-14 4 4 8-8 4 14H6z"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinejoin="round"
                />
                <circle cx="22" cy="10" r="2" fill="currentColor" />
              </svg>
            </div>
            <div>
              <h3 className="feedback-tipTitle">Đánh giá sản phẩm</h3>
              <p className="feedback-tipText">
                Sau khi mua, hãy đánh giá từng món đã nhận tại{" "}
                <Link to="/my-feedback">trang đánh giá</Link>.
              </p>
            </div>
          </div>
          <div className="feedback-tipCard feedback-tipCard--c">
            <div className="feedback-tipIcon" aria-hidden>
              <svg viewBox="0 0 32 32" fill="none">
                <path
                  d="M6 12h20v14H6V12z"
                  stroke="currentColor"
                  strokeWidth="1.8"
                />
                <path
                  d="M10 12V8a6 6 0 0112 0v4"
                  stroke="currentColor"
                  strokeWidth="1.8"
                />
                <circle cx="16" cy="19" r="2" fill="currentColor" />
              </svg>
            </div>
            <div>
              <h3 className="feedback-tipTitle">Hỗ trợ &amp; chính sách</h3>
              <p className="feedback-tipText">
                Đơn hàng, đổi trả: <Link to="/contact">Liên hệ</Link> ·{" "}
                <Link to="/policy">Chính sách</Link>.
              </p>
            </div>
          </div>
        </aside>

        <div className="feedback-main">
          {!user ? (
            <div className="feedback-guestShell">
              <div className="feedback-guestGlow" aria-hidden />
              <div className="feedback-guestCard">
                <div className="feedback-guestArt" aria-hidden>
                  <svg viewBox="0 0 120 120" className="feedback-guestSvg">
                    <defs>
                      <linearGradient
                        id="fbGrad"
                        x1="0%"
                        y1="0%"
                        x2="100%"
                        y2="100%"
                      >
                        <stop offset="0%" stopColor="#F55554" />
                        <stop offset="100%" stopColor="#FF9A8B" />
                      </linearGradient>
                    </defs>
                    <circle
                      cx="60"
                      cy="60"
                      r="52"
                      fill="url(#fbGrad)"
                      opacity="0.15"
                    />
                    <path
                      d="M40 48h40v36H40V48z"
                      fill="none"
                      stroke="url(#fbGrad)"
                      strokeWidth="2.5"
                      strokeLinejoin="round"
                    />
                    <path
                      d="M48 56h24M48 64h16"
                      stroke="url(#fbGrad)"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                    <circle
                      cx="75"
                      cy="42"
                      r="8"
                      fill="url(#fbGrad)"
                      opacity="0.9"
                    />
                    <path
                      d="M72 42l3 3 6-6"
                      stroke="#fff"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
                <h2 className="feedback-guestTitle">Đăng nhập để gửi góp ý</h2>
                <p className="feedback-guestText">
                  Chúng tôi gắn góp ý với tài khoản để xử lý minh bạch và phản
                  hồi đúng người.
                </p>
                <div className="feedback-guestActions">
                  <Link
                    to="/login?redirect=/feedback"
                    className="feedback-btn feedback-btn--primary"
                  >
                    Đăng nhập
                  </Link>
                  <Link
                    to="/register"
                    className="feedback-btn feedback-btn--ghost"
                  >
                    Tạo tài khoản
                  </Link>
                </div>
              </div>
            </div>
          ) : user.can_access_admin ? (
            <div className="feedback-guestShell">
              <div className="feedback-guestGlow" aria-hidden />
              <div className="feedback-guestCard">
                <div className="feedback-guestArt" aria-hidden>
                  <svg viewBox="0 0 120 120" className="feedback-guestSvg">
                    <defs>
                      <linearGradient
                        id="fbAdminGrad"
                        x1="0%"
                        y1="0%"
                        x2="100%"
                        y2="100%"
                      >
                        <stop offset="0%" stopColor="#6366f1" />
                        <stop offset="100%" stopColor="#818cf8" />
                      </linearGradient>
                    </defs>
                    <circle
                      cx="60"
                      cy="60"
                      r="52"
                      fill="url(#fbAdminGrad)"
                      opacity="0.12"
                    />
                    <rect
                      x="36"
                      y="38"
                      width="48"
                      height="36"
                      rx="4"
                      fill="none"
                      stroke="url(#fbAdminGrad)"
                      strokeWidth="2.5"
                      strokeLinejoin="round"
                    />
                    <path
                      d="M44 52h32M44 62h20"
                      stroke="url(#fbAdminGrad)"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                    <circle
                      cx="76"
                      cy="42"
                      r="10"
                      fill="url(#fbAdminGrad)"
                      opacity="0.9"
                    />
                    <path
                      d="M72 42l3 3 7-7"
                      stroke="#fff"
                      strokeWidth="2.2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
                <h2 className="feedback-guestTitle">
                  Kênh dành cho khách hàng
                </h2>
                <p className="feedback-guestText">
                  Tài khoản quản trị không sử dụng kênh góp ý này. Bạn có thể
                  xem và xử lý phản hồi từ khách hàng trực tiếp trong trang quản
                  trị.
                </p>
                <div className="feedback-guestActions">
                  <Link
                    to="/admin/feedbacks"
                    className="feedback-btn feedback-btn--primary"
                  >
                    Xem phản hồi
                  </Link>
                  <Link
                    to="/admin"
                    className="feedback-btn feedback-btn--ghost"
                  >
                    Trang quản trị
                  </Link>
                </div>
              </div>
            </div>
          ) : (
            <div className="feedback-formShell">
              <div className="feedback-formGlow" aria-hidden />
              <div className="feedback-formCard">
                <div className="feedback-formHead">
                  <div>
                    <h2 className="feedback-formTitle">Nội dung góp ý</h2>
                    <p className="feedback-formHint">
                      Xin chào <strong>{user.username}</strong> — viết tự do,
                      chúng tôi đọc hết.
                    </p>
                  </div>
                  <div className="feedback-formAvatar" aria-hidden>
                    {user.username.slice(0, 1).toUpperCase()}
                  </div>
                </div>
                <form onSubmit={handleSubmit} className="feedback-form">
                  <div className="feedback-field">
                    <div className="feedback-fieldLabelRow">
                      <label htmlFor="fb-body">Nội dung</label>
                      <span
                        className={`feedback-count ${len > MAX_LEN ? "is-over" : ""}`}
                      >
                        {len} / {MAX_LEN}
                      </span>
                    </div>
                    <div className="feedback-textareaWrap">
                      <textarea
                        id="fb-body"
                        value={message}
                        onChange={(e) =>
                          setMessage(e.target.value.slice(0, MAX_LEN))
                        }
                        required
                        minLength={3}
                        rows={7}
                        maxLength={MAX_LEN}
                        placeholder="Ví dụ: Trang sản phẩm nên lọc theo size nhanh hơn… / Thời gian giao hàng dự kiến hiển thị rõ hơn…"
                        className="feedback-textarea"
                      />
                    </div>
                  </div>
                  <button
                    type="submit"
                    className="feedback-submit"
                    disabled={loading || len > MAX_LEN || len < 3}
                  >
                    {loading ? (
                      <>
                        <span className="feedback-submitSpinner" aria-hidden />
                        Đang gửi…
                      </>
                    ) : (
                      <>
                        <span className="feedback-submitIcon" aria-hidden>
                          ✉
                        </span>
                        Gửi góp ý
                      </>
                    )}
                  </button>
                  {status && (
                    <div
                      className={`feedback-msg feedback-msg--${status.type}`}
                      role="status"
                    >
                      {status.type === "ok" ? "✓ " : "✕ "}
                      {status.text}
                    </div>
                  )}
                </form>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
