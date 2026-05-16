import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { customerAccountPageTitle } from "./customerAccountTitles";
import "../../styles/admin/Admin.css";
import "./CustomerAccountLayout.css";

const IconDashboard = () => (
  <svg viewBox="0 0 24 24" className="icon">
    <rect x="3" y="3" width="7" height="7" />
    <rect x="14" y="3" width="7" height="7" />
    <rect x="3" y="14" width="7" height="7" />
    <rect x="14" y="14" width="7" height="7" />
  </svg>
);

const IconShoppingBag = () => (
  <svg viewBox="0 0 24 24" className="icon">
    <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" />
    <line x1="3" y1="6" x2="21" y2="6" />
    <path d="M16 10a4 4 0 0 1-8 0" />
  </svg>
);

const IconUsers = () => (
  <svg viewBox="0 0 24 24" className="icon">
    <circle cx="9" cy="7" r="4" />
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
    <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
  </svg>
);

const IconRefreshCcw = () => (
  <svg viewBox="0 0 24 24" className="icon">
    <polyline points="1 4 1 10 7 10" />
    <polyline points="23 20 23 14 17 14" />
    <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15" />
  </svg>
);

const IconLogout = () => (
  <svg viewBox="0 0 24 24" className="icon">
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
    <polyline points="16 17 21 12 16 7" />
    <line x1="21" y1="12" x2="9" y2="12" />
  </svg>
);

const IconWallet = () => (
  <svg viewBox="0 0 24 24" className="icon" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M20 18a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2" />
    <path d="M16 11V7" />
    <path d="M16 17v-2" />
    <rect x="16" y="11" width="4" height="4" rx="1" />
  </svg>
);

const menuItems = [
  { path: "/dashboard", label: "Tổng quan", icon: <IconDashboard />, end: true },
  { path: "/dashboard/orders", label: "Đơn hàng", icon: <IconShoppingBag /> },
  { path: "/dashboard/profile", label: "Hồ sơ", icon: <IconUsers /> },
  { path: "/dashboard/returns", label: "Trả hàng", icon: <IconRefreshCcw /> },
  { path: "/dashboard/wallet", label: "Ví của tôi", icon: <IconWallet /> },
];

export default function CustomerAccountLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const pageTitle = customerAccountPageTitle(location.pathname);

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <div className="admin-layout customer-account-layout">
      <aside className="admin-sidebar">
        <div className="admin-sidebar-header">
          <h2>Tài khoản</h2>
          <p className="customer-account-tagline">FashionStore</p>
        </div>

        <nav className="admin-sidebar-nav">
          {menuItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.end ?? false}
              className={({ isActive }) =>
                `admin-nav-item${isActive ? " active" : ""}`
              }
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="admin-sidebar-footer">
          <button
            type="button"
            onClick={handleLogout}
            className="admin-nav-item logout-btn"
          >
            <span className="nav-icon">
              <IconLogout />
            </span>
            <span className="nav-label">Đăng xuất</span>
          </button>
        </div>
      </aside>

      <main className="admin-main">
        <header className="admin-header">
          <h1>{pageTitle}</h1>
          <div className="admin-header-right">
            <div className="admin-header-actions">
              <Link
                to="/"
                className="admin-header-action-link admin-header-action-link--primary"
              >
                Về trang chủ
              </Link>
              <Link to="/products" className="admin-header-action-link">
                Cửa hàng
              </Link>
            </div>
            <div className="admin-header-user">
              {user?.username ?? "Khách"}
              {user?.role ? ` · ${user.role}` : ""}
            </div>
          </div>
        </header>

        <div className="admin-content customer-account-content">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
