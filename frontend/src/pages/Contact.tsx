import axios from "axios";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { site, type ContactMeta } from "../api/client";
import { useAuth } from "../context/AuthContext";
import SupportSubnav from "../components/SupportSubnav";
import "../styles/pages/Contact.css";

const FALLBACK_META: ContactMeta = {
  brand: "FashionStore",
  hotline_display: "0964 942 121",
  hotline_e164: "+84964942121",
  email: "cskh@fashionstore.vn",
  address:
    "70 Tô Ký, Phường Tân Chánh Hiệp, Quận 12, TP. Hồ Chí Minh",
  hours:
    "Thứ Hai – Thứ Sáu: 8:30 – 17:30 (GMT+7). Thứ Bảy, Chủ nhật & ngày lễ: không làm việc tại văn phòng.",
  response_note:
    "Chúng tôi phản hồi qua email trong 1–2 ngày làm việc. Trường hợp khẩn về đơn đang giao, vui lòng gọi hotline.",
  stats: [
    { label: "Phản hồi email", value: "1–2 ngày làm việc" },
    { label: "Hotline", value: "Giờ hành chính" },
    { label: "Làm việc", value: "Thứ 2 – Thứ 6" },
  ],
  subject_options: [
    { value: "order", label: "Đơn hàng & vận chuyển" },
    { value: "return", label: "Đổi trả & hoàn tiền" },
    { value: "product", label: "Sản phẩm & tồn kho" },
    { value: "account", label: "Tài khoản & bảo mật" },
    { value: "partner", label: "Hợp tác / B2B" },
    { value: "other", label: "Khác" },
  ],
};

function contactErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const d = err.response?.data;
    if (typeof d === "string" && d.trim()) return d;
    if (d && typeof d === "object" && !Array.isArray(d)) {
      const o = d as Record<string, unknown>;
      if (typeof o.detail === "string") return o.detail;
      const parts: string[] = [];
      for (const [k, v] of Object.entries(o)) {
        if (k === "detail") continue;
        if (Array.isArray(v)) parts.push(`${k}: ${v.join(", ")}`);
        else if (typeof v === "string") parts.push(`${k}: ${v}`);
      }
      if (parts.length) return parts.join(" · ");
    }
  }
  return "Không gửi được. Vui lòng kiểm tra nội dung và thử lại.";
}

export default function Contact() {
  const { user } = useAuth();
  const [meta, setMeta] = useState<ContactMeta>(FALLBACK_META);
  const [metaLoading, setMetaLoading] = useState(true);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [subjectKey, setSubjectKey] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<{
    type: "ok" | "err";
    text: string;
  } | null>(null);

  useEffect(() => {
    let cancelled = false;
    site
      .getContactMeta()
      .then((res) => {
        if (!cancelled && res.data) setMeta(res.data);
      })
      .catch(() => {
        if (!cancelled) setMeta(FALLBACK_META);
      })
      .finally(() => {
        if (!cancelled) setMetaLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const heroPills = useMemo(
    () => meta.subject_options.slice(0, 3).map((o) => o.label),
    [meta.subject_options],
  );

  const telHref = `tel:${meta.hotline_e164.replace(/\s/g, "")}`;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus(null);
    setLoading(true);
    const opt = meta.subject_options.find((o) => o.value === subjectKey);
    const subjectLine = opt ? `[${opt.value}] ${opt.label}` : "";
    try {
      await site.sendContact({
        name: name.trim(),
        email: email.trim(),
        phone: phone.trim(),
        subject: subjectLine,
        message: message.trim(),
      });
      setStatus({
        type: "ok",
        text: "Đã gửi tin nhắn. Chúng tôi sẽ phản hồi qua email bạn cung cấp.",
      });
      setMessage("");
      setSubjectKey("");
      setPhone("");
    } catch (err) {
      setStatus({
        type: "err",
        text: contactErrorMessage(err),
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="contact-page">
      <section className="contact-hero">
        <div className="contact-heroMesh" aria-hidden />
        <div className="contact-heroFloat contact-heroFloat--1" aria-hidden />
        <div className="contact-heroFloat contact-heroFloat--2" aria-hidden />
        <div className="contact-heroFloat contact-heroFloat--3" aria-hidden />
        <div
          className="contact-hero-blob contact-hero-blob--left"
          aria-hidden
        />
        <div
          className="contact-hero-blob contact-hero-blob--right"
          aria-hidden
        />
        <div className="contact-hero-inner">
          <p className="contact-hero-badge">
            <span className="contact-hero-badgeDot" aria-hidden />
            Luôn sẵn sàng hỗ trợ
          </p>
          <h1 className="contact-hero-title">
            <span className="contact-hero-titleGrad">Liên hệ</span>
            <span className="contact-hero-titleRest"> với {meta.brand}</span>
          </h1>
          <p className="contact-hero-lead">
            Gửi câu hỏi hoặc yêu cầu — chúng tôi phản hồi qua email, thường
            trong 1–2 ngày làm việc. Cần gấp về đơn đang giao? Gọi hotline trong
            giờ làm việc.
          </p>
          <div
            className={`contact-hero-stats ${metaLoading ? "contact-hero-stats--loading" : ""}`}
            role="list"
            aria-busy={metaLoading}
          >
            {meta.stats.map((s) => (
              <div key={s.label} className="contact-stat" role="listitem">
                <span className="contact-stat-value">{s.value}</span>
                <span className="contact-stat-label">{s.label}</span>
              </div>
            ))}
          </div>
          <div className="contact-hero-pills" role="list">
            {heroPills.map((label) => (
              <span key={label} className="contact-pill" role="listitem">
                {label}
              </span>
            ))}
          </div>
          <SupportSubnav />
        </div>
      </section>

      <div className="contact-layout">
        <aside className="contact-aside">
          <div className="contact-infoCard contact-infoCard--addr">
            <div className="contact-infoIcon" aria-hidden>
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
              >
                <path d="M12 21s7-4.5 7-11a7 7 0 10-14 0c0 6.5 7 11 7 11z" />
                <circle cx="12" cy="10" r="2.5" />
              </svg>
            </div>
            <div>
              <h3 className="contact-infoLabel">Địa chỉ</h3>
              <p className="contact-infoText">{meta.address}</p>
            </div>
          </div>
          <div className="contact-infoCard contact-infoCard--phone">
            <div className="contact-infoIcon" aria-hidden>
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
              >
                <path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 16.92z" />
              </svg>
            </div>
            <div>
              <h3 className="contact-infoLabel">Điện thoại</h3>
              <a className="contact-infoLink" href={telHref}>
                {meta.hotline_display}
              </a>
            </div>
          </div>
          <div className="contact-infoCard contact-infoCard--mail">
            <div className="contact-infoIcon" aria-hidden>
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
              >
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                <path d="M22 6l-10 7L2 6" />
              </svg>
            </div>
            <div>
              <h3 className="contact-infoLabel">Email</h3>
              <a className="contact-infoLink" href={`mailto:${meta.email}`}>
                {meta.email}
              </a>
            </div>
          </div>
          <div className="contact-infoCard contact-infoCard--hours">
            <div className="contact-infoIcon" aria-hidden>
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
              >
                <circle cx="12" cy="12" r="9" />
                <path d="M12 7v6l4 2" strokeLinecap="round" />
              </svg>
            </div>
            <div>
              <h3 className="contact-infoLabel">Giờ làm việc</h3>
              <p className="contact-infoText">{meta.hours}</p>
              <p className="contact-infoNote">{meta.response_note}</p>
            </div>
          </div>
          <div className="contact-quickLinks">
            <span className="contact-quickLinksLabel">Xem thêm</span>
            <div className="contact-quickLinksRow">
              <Link to="/policy" className="contact-quickLink">
                Chính sách
              </Link>
              <span className="contact-quickDot" aria-hidden>
                ·
              </span>
              <Link to="/feedback" className="contact-quickLink">
                Góp ý
              </Link>
            </div>
          </div>
        </aside>

        <div className="contact-main">
          {user?.can_access_admin ? (
            <div className="contact-formShell">
              <div className="contact-formGlow" aria-hidden />
              <div className="contact-formCard">
                <div className="contact-formHead">
                  <div>
                    <h2 className="contact-formTitle">
                      Kênh dành cho khách hàng
                    </h2>
                    <p className="contact-formHint">
                      Tài khoản quản trị không sử dụng form liên hệ này.
                    </p>
                  </div>
                  <div className="contact-formHeadIcon" aria-hidden>
                    <svg viewBox="0 0 32 32" fill="none">
                      <path
                        d="M16 4l10 5v9c0 6-4 10-10 13C10 28 6 24 6 18V9z"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinejoin="round"
                      />
                      <path
                        d="M12 16l3 3 6-6"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </div>
                </div>
                <p
                  style={{
                    color: "var(--color-text-muted)",
                    fontSize: "0.95rem",
                    lineHeight: "1.6",
                    margin: "0 0 20px",
                  }}
                >
                  Các liên hệ từ khách hàng được quản lý trực tiếp trong trang
                  quản trị. Bạn có thể xem và xử lý tại đó.
                </p>
                <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
                  <Link
                    to="/admin/contacts"
                    className="contact-submit"
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      textDecoration: "none",
                      width: "auto",
                      padding: "12px 24px",
                    }}
                  >
                    <span style={{ marginRight: "6px" }}>📋</span>
                    Xem liên hệ
                  </Link>
                  <Link
                    to="/admin"
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      textDecoration: "none",
                      padding: "12px 24px",
                      borderRadius: "999px",
                      border: "1.5px solid var(--color-border, #e5e7eb)",
                      color: "var(--color-text-muted)",
                      fontSize: "0.95rem",
                      fontWeight: 600,
                    }}
                  >
                    Trang quản trị
                  </Link>
                </div>
              </div>
            </div>
          ) : (
            <div className="contact-formShell">
              <div className="contact-formGlow" aria-hidden />
              <div className="contact-formCard">
                <div className="contact-formHead">
                  <div>
                    <h2 className="contact-formTitle">Gửi tin nhắn</h2>
                    <p className="contact-formHint">
                      Các trường có dấu * là bắt buộc.
                    </p>
                  </div>
                  <div className="contact-formHeadIcon" aria-hidden>
                    <svg viewBox="0 0 32 32" fill="none">
                      <path
                        d="M6 10h20v12H6V10z"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinejoin="round"
                      />
                      <path
                        d="M6 14l10 6 10-6"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                      />
                    </svg>
                  </div>
                </div>
                <form className="contact-form" onSubmit={handleSubmit}>
                  <div className="contact-fieldRow">
                    <div className="contact-field">
                      <label htmlFor="c-name">Họ tên *</label>
                      <div className="contact-inputWrap">
                        <input
                          id="c-name"
                          value={name}
                          onChange={(e) => setName(e.target.value)}
                          required
                          maxLength={100}
                          autoComplete="name"
                          placeholder="Nguyễn Văn A"
                        />
                      </div>
                    </div>
                    <div className="contact-field">
                      <label htmlFor="c-phone">Số điện thoại</label>
                      <div className="contact-inputWrap">
                        <input
                          id="c-phone"
                          inputMode="tel"
                          value={phone}
                          onChange={(e) => setPhone(e.target.value)}
                          maxLength={20}
                          autoComplete="tel"
                          placeholder="Để CSKH gọi lại khi cần"
                        />
                      </div>
                    </div>
                  </div>
                  <div className="contact-field">
                    <label htmlFor="c-email">Email *</label>
                    <div className="contact-inputWrap">
                      <input
                        id="c-email"
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        autoComplete="email"
                        placeholder="ban@email.com"
                      />
                    </div>
                  </div>
                  <div className="contact-field">
                    <label htmlFor="c-subject">Chủ đề *</label>
                    <div className="contact-selectWrap">
                      <select
                        id="c-subject"
                        value={subjectKey}
                        onChange={(e) => setSubjectKey(e.target.value)}
                        required
                      >
                        <option value="" disabled>
                          Chọn chủ đề
                        </option>
                        {meta.subject_options.map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div className="contact-field">
                    <label htmlFor="c-msg">Nội dung *</label>
                    <div className="contact-textareaWrap">
                      <textarea
                        id="c-msg"
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        required
                        minLength={5}
                        rows={6}
                        placeholder="Mô tả chi tiết để chúng tôi hỗ trợ nhanh hơn..."
                      />
                    </div>
                  </div>
                  <button
                    type="submit"
                    className="contact-submit"
                    disabled={loading}
                  >
                    {loading ? (
                      <>
                        <span className="contact-submitSpinner" aria-hidden />
                        Đang gửi…
                      </>
                    ) : (
                      <>
                        <span className="contact-submitIcon" aria-hidden>
                          ✉
                        </span>
                        Gửi liên hệ
                      </>
                    )}
                  </button>
                  {status && (
                    <div
                      className={`contact-msg contact-msg--${status.type}`}
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
