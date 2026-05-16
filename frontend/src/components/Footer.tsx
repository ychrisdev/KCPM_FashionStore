import { Link } from "react-router-dom";
import "../styles/components/Footer.css";

function SocialIcon({ type }: { type: string }) {
  const size = 18;
  const common = {
    width: size,
    height: size,
    fill: "none" as const,
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round",
    strokeLinejoin: "round",
  } as const;
  switch (type) {
    case "facebook":
      return (
        <svg viewBox="0 0 24 24" {...common}>
          <path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z" />
        </svg>
      );
    case "twitter":
      return (
        <svg viewBox="0 0 24 24" {...common}>
          <path d="M4 4l11.733 16h4L8 10.377v9.246L4 4zm4 0l6 8.313L4 20h2.667L20 4l-12 16.313V4z" />
        </svg>
      );
    case "instagram":
      return (
        <svg viewBox="0 0 24 24" {...common}>
          <rect x="2" y="2" width="20" height="20" rx="5" />
          <circle cx="12" cy="12" r="4" />
          <circle cx="18" cy="6" r="1.5" />
        </svg>
      );
    case "tiktok":
      return (
        <svg viewBox="0 0 24 24" {...common}>
          <path d="M9 12a4 4 0 1 0 4 4V4a5 5 0 0 0 5 5" />
        </svg>
      );
    case "youtube":
      return (
        <svg viewBox="0 0 24 24" {...common}>
          <path d="M22.54 6.42a2.78 2.78 0 0 0-1.94-2C18.88 4 12 4 12 4s-6.88 0-8.6.46a2.78 2.78 0 0 0-1.94 2A29 29 0 0 0 1 11.75a29 29 0 0 0 .46 5.33A2.78 2.78 0 0 0 3.4 19c1.72.46 8.6.46 8.6.46s6.88 0 8.6-.46a2.78 2.78 0 0 0 1.94-2 29 29 0 0 0 .46-5.25 29 29 0 0 0-.46-5.33z" />
          <path d="M9.75 15.02l5.75-3.27-5.75-3.27v6.54z" fill="currentColor" stroke="none" />
        </svg>
      );
    default:
      return null;
  }
}

export default function Footer() {
  const currentYear = new Date().getFullYear();

  const socialLinks = [
    { label: "Facebook", href: "#", type: "facebook" },
    { label: "Twitter", href: "#", type: "twitter" },
    { label: "Instagram", href: "#", type: "instagram" },
    { label: "TikTok", href: "#", type: "tiktok" },
    { label: "YouTube", href: "#", type: "youtube" },
  ];

  const paymentMethods = ["ZaloPay", "MoMo"];
  const shippingMethods = ["GHN", "GHTK", "Ahamove", "J&T"];

  const navLinks = [
    { to: "/search", label: "Tìm kiếm" },
    { to: "/about", label: "Giới thiệu" },
    { to: "/policy", label: "Chính sách" },
    { to: "/policy/doi-tra", label: "Đổi trả" },
    { to: "/policy/bao-mat", label: "Bảo mật" },
    { to: "/feedback", label: "Góp ý" },
    { to: "/contact", label: "Liên hệ" },
    { to: "/careers", label: "Tuyển dụng" },
  ];

  return (
    <footer className="footer">
      {/* Hàng 1: Brand | Liên hệ | Liên kết | Bản đồ */}
      <div className="footerMain">
        <div className="footerCol footerColBrand">
          <h3 className="footerHeading">FashionStore</h3>
          <p className="footerDesc">
            Hệ thống thời trang cho phái mạnh hàng đầu Việt Nam, hướng tới phong cách nam tính, lịch lãm và trẻ trung.
          </p>
          <div className="footerSocials">
            {socialLinks.map((s) => (
              <a key={s.label} href={s.href} className="footerSocialIcon" title={s.label} aria-label={s.label}>
                <SocialIcon type={s.type} />
              </a>
            ))}
          </div>
        </div>

        <div className="footerCol footerColContact">
          <h3 className="footerHeading">Thông tin liên hệ</h3>
          <div className="footerContactList">
            <p>Địa chỉ: Số 70 đường Tô Ký, phường Tân Chánh Hiệp, quận 12, TP. Hồ Chí Minh, Việt Nam</p>
            <p>Điện thoại: 0964942121</p>
            <p>Fax: 0904636356</p>
            <p>Email: <a href="mailto:cskh@fashionstore.vn">cskh@fashionstore.vn</a></p>
          </div>
        </div>

        <div className="footerCol footerColLinks">
          <h3 className="footerHeading">Nhóm liên kết</h3>
          <ul className="footerNavList">
            {navLinks.map((link) => (
              <li key={link.to}>
                <Link to={link.to} className="footerNavLink">{link.label}</Link>
              </li>
            ))}
          </ul>
        </div>

        <div className="footerCol footerColMap">
          <h3 className="footerHeading">Bản đồ</h3>
          <div className="footerMapWrap">
            <iframe
              title="Bản đồ FashionStore"
              src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3918.294614874553!2d106.61381087570398!3d10.865181857549004!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x31752a10b0f0554f%3A0xf68a0214bdab4972!2zNzAgxJAuIFTDtCBLw70sIFTDom4gQ2jDoW5oIEhp4buHcCwgUXXhuq1uIDEyLCBUaMOgbmggcGjhu5EgSOG7kyBDaMOtIE1pbmggNzAwMDAwLCBWaeG7h3QgTmFt!5e0!3m2!1svi!2s!4v1773567798654!5m2!1svi!2s"
              width="100%"
              height="100%"
              style={{ border: 0 }}
              allowFullScreen
              loading="lazy"
              referrerPolicy="no-referrer-when-downgrade"
            />
          </div>
        </div>
      </div>

      {/* Hàng 2: Thanh toán + Vận chuyển (full width) */}
      <div className="footerMiddle">
        <div className="footerMiddleBlock">
          <p className="footerSubHeading">Phương thức thanh toán</p>
          <div className="footerPaymentLogos">
            {paymentMethods.map((name) => (
              <span key={name} className="footerPaymentItem">{name}</span>
            ))}
          </div>
        </div>
        <div className="footerMiddleBlock">
          <p className="footerSubHeading">Phương thức vận chuyển</p>
          <div className="footerShippingLogos">
            {shippingMethods.map((name) => (
              <span key={name} className="footerShippingItem">{name}</span>
            ))}
          </div>
        </div>
      </div>

      <div className="footerBottom">
        <p className="footerCopy">© {currentYear} FashionStore. All rights reserved.</p>
      </div>
    </footer>
  );
}
