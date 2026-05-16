import { NavLink } from "react-router-dom";
import "../styles/components/SupportSubnav.css";

const ITEMS: { to: string; label: string; end?: boolean }[] = [
  { to: "/contact", label: "Liên hệ", end: true },
  { to: "/feedback", label: "Góp ý", end: true },
  { to: "/policy", label: "Chính sách", end: false },
];

export default function SupportSubnav() {
  return (
    <nav className="supportSubnav" aria-label="Trang hỗ trợ khách hàng">
      <ul className="supportSubnavList">
        {ITEMS.map(({ to, label, end }) => (
          <li key={to}>
            <NavLink
              to={to}
              end={end}
              className={({ isActive }) =>
                "supportSubnavLink" + (isActive ? " is-active" : "")
              }
            >
              {label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
