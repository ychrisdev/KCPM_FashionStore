import "../styles/components/FloatingContactBar.css";

const TIKTOK_DEFAULT = "https://www.tiktok.com/@uth_hcm";
const FACEBOOK_DEFAULT =
  "https://www.facebook.com/TruongDHGiaothongvantaiTPHCM";
const GOOGLE_MAPS_DEFAULT =
  "https://www.google.com/maps/search/?api=1&query=70+%C4%90.+T%C3%B4+K%C3%BD%2C+T%C3%A2n+Ch%C3%A1nh+Hi%E1%BB%87p%2C+Trung+M%E1%BB%B9+T%C3%A2y%2C+H%E1%BB%93+Ch%C3%AD+Minh";

const TopArrow = () => (
  <svg
    className="floating-contact-bar__icon floating-contact-bar__icon--top"
    viewBox="0 0 24 24"
    aria-hidden
    fill="none"
    stroke="currentColor"
    strokeWidth="2.4"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M12 19V5M5 12l7-7 7 7" />
  </svg>
);

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: "smooth" });
}

export default function FloatingContactBar() {
  const tiktokUrl =
    (import.meta.env.VITE_TIKTOK_URL as string | undefined)?.trim() ||
    TIKTOK_DEFAULT;
  const facebookUrl =
    (import.meta.env.VITE_FACEBOOK_URL as string | undefined)?.trim() ||
    FACEBOOK_DEFAULT;
  const googleMapsUrl =
    (import.meta.env.VITE_GOOGLE_MAPS_URL as string | undefined)?.trim() ||
    GOOGLE_MAPS_DEFAULT;

  return (
    <aside className="floating-contact-bar" aria-label="Mạng xã hội & điều hướng">
      <span className="floating-contact-bar__slot">
        <a
          href={tiktokUrl}
          className="floating-contact-bar__btn floating-contact-bar__btn--brand"
          aria-label="TikTok @uth_hcm"
          target="_blank"
          rel="noopener noreferrer"
        >
          <img
            src="/social/tiktok.png"
            alt=""
            className="floating-contact-bar__logo"
            width={52}
            height={52}
            decoding="async"
          />
        </a>
      </span>
      <span className="floating-contact-bar__slot">
        <a
          href={facebookUrl}
          className="floating-contact-bar__btn floating-contact-bar__btn--brand"
          aria-label="Facebook Trường ĐH Giao thông vận tải TP.HCM"
          target="_blank"
          rel="noopener noreferrer"
        >
          <img
            src="/social/facebook.png"
            alt=""
            className="floating-contact-bar__logo"
            width={52}
            height={52}
            decoding="async"
          />
        </a>
      </span>
      <span className="floating-contact-bar__slot">
        <a
          href={googleMapsUrl}
          className="floating-contact-bar__btn floating-contact-bar__btn--brand floating-contact-bar__btn--maps"
          aria-label="Xem địa chỉ trên Google Maps - 70 Đ. Tô Ký, Tân Chánh Hiệp, Trung Mỹ Tây, Hồ Chí Minh"
          target="_blank"
          rel="noopener noreferrer"
        >
          <img
            src="/social/google-maps.png"
            alt=""
            width={28}
            height={28}
            className="floating-contact-bar__maps-logo"
            decoding="async"
          />
        </a>
      </span>
      <span className="floating-contact-bar__slot">
        <button
          type="button"
          className="floating-contact-bar__btn floating-contact-bar__btn--top"
          onClick={scrollToTop}
          aria-label="Lên đầu trang"
        >
          <TopArrow />
          TOP
        </button>
      </span>
    </aside>
  );
}
