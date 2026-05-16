import { useState, useEffect, useCallback, useRef } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { cart } from "../api/client";
import SearchBar from "./SearchBar";
import { CART_UPDATED_EVENT } from "../utils/cartEvents";
import "../styles/components/Header.css";

const CartIcon = () => (
  <svg
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
  >
    <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z" />
    <line x1="3" y1="6" x2="21" y2="6" />
    <path d="M16 10a4 4 0 01-8 0" />
  </svg>
);

const UserIcon = () => (
  <svg
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
  >
    <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
);

const ArrowIcon = () => (
  <svg
    width="14"
    height="14"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2.5"
  >
    <path d="M5 12h14M12 5l7 7-7 7" />
  </svg>
);

const navLinks = [
  { to: "/", label: "Trang Chủ" },
  { to: "/products", label: "Sản Phẩm" },
  { to: "/about", label: "Giới Thiệu" },
  { to: "/policy", label: "Chính Sách" },
  { to: "/feedback", label: "Góp Ý" },
  { to: "/contact", label: "Liên Hệ" },
];

async function fetchCartItemCount(): Promise<number> {
  try {
    const res = await cart.get();
    const items = (res.data as { items?: { quantity: number }[] })?.items ?? [];
    return items.reduce((sum, it) => sum + (it.quantity ?? 0), 0);
  } catch {
    return 0;
  }
}

// Avatar nhỏ dùng trong header dropdown trigger
function HeaderAvatar({ src, initial }: { src?: string | null; initial: string }) {
  if (src) {
    return (
      <img
        src={src}
        alt=""
        style={{
          width: 28,
          height: 28,
          borderRadius: "50%",
          objectFit: "cover",
          border: "1.5px solid rgba(245,85,84,0.35)",
          display: "block",
        }}
      />
    );
  }
  return (
    <span
      className="headerAvatarLetter"
      style={{
        width: 28,
        height: 28,
        borderRadius: "50%",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 12,
        fontWeight: 700,
        background: "rgba(245,85,84,0.12)",
        color: "#c96b65",
      }}
    >
      {initial}
    </span>
  );
}

export default function Header() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [cartCount, setCartCount] = useState(0);
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const isAdmin = Boolean(user?.can_access_admin);

  const closeMenu = () => setMenuOpen(false);
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const closeAccountMenu = () => setAccountMenuOpen(false);
  const accountMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (accountMenuRef.current && !accountMenuRef.current.contains(e.target as Node)) {
        setAccountMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);
  const userId = user?.id ?? null;
    const refreshCartCount = useCallback(async () => {
      if (!userId || isAdmin) {
      setCartCount(0);
      return;
    }
    const count = await fetchCartItemCount();
    setCartCount(count);
  },  [userId, isAdmin]); 

  useEffect(() => {
    void refreshCartCount();
  }, [refreshCartCount]);

  useEffect(() => {
    const onCartUpdated = () => {
      void refreshCartCount();
    };
    window.addEventListener(CART_UPDATED_EVENT, onCartUpdated);
    return () => window.removeEventListener(CART_UPDATED_EVENT, onCartUpdated);
  }, [refreshCartCount]);

  const displayName =
    user?.first_name || user?.last_name
      ? [user.first_name, user.last_name].filter(Boolean).join(" ").trim()
      : user?.username || "Bạn";

  const cartBadgeLabel =
    cartCount <= 0 ? "" : cartCount > 99 ? "99+" : String(cartCount);

  return (
    <>
      <header className="header">
        <div className="headerInner">
          <Link to="/" className="logo" onClick={closeMenu}>
            <div className="logoMark">F</div>
            <span className="logoText">
              Fashion<span>Store</span>
            </span>
          </Link>

          <nav className="nav">
            {navLinks.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  `navLink ${isActive ? "navLinkActive" : ""}`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="searchWrapper">
            <SearchBar />
          </div>

          <div className="actions">
            {!isAdmin && (
              <button
                type="button"
                className="iconBtn"
                onClick={() => navigate("/cart")}
                aria-label={`Giỏ hàng${cartCount > 0 ? `, ${cartCount} sản phẩm` : ""}`}
              >
                <CartIcon />
                {cartBadgeLabel ? (
                  <span className="cartBadge">{cartBadgeLabel}</span>
                ) : null}
              </button>
            )}

            {user ? (
              <div className="headerUserMenu">
                <div className="accountDropdown" ref={accountMenuRef}>
                  <button type="button" className="iconBtn accountTrigger" aria-label="Tài khoản"
                    onClick={() => setAccountMenuOpen(prev => !prev)}>
                    <HeaderAvatar
                      src={user.avatar}
                      initial={(user.first_name?.[0] ?? user.username?.[0] ?? "U").toUpperCase()}
                    />
                  </button>
                  {accountMenuOpen && <div className={`accountMenu ${accountMenuOpen ? "accountMenuOpen" : ""}`}>
                    <div className="accountMenuHeader">
                      {/* Avatar lớn hơn trong dropdown */}
                      {user.avatar && (
                        <img
                          src={user.avatar}
                          alt=""
                          style={{
                            width: 36,
                            height: 36,
                            borderRadius: "50%",
                            objectFit: "cover",
                            border: "2px solid rgba(245,85,84,0.3)",
                            marginBottom: "0.4rem",
                            display: "block",
                          }}
                        />
                      )}
                      <span className="accountMenuLabel">Tài khoản</span>
                      <strong>{displayName}</strong>
                    </div>
                    {!isAdmin && (
                      <Link to="/dashboard" className="accountMenuItem" onClick={closeAccountMenu}>
                        Tổng quan tài khoản
                      </Link>
                    )}
                    <Link to="/profile" className="accountMenuItem" onClick={closeAccountMenu}>
                      Thông tin tài khoản
                    </Link>
                    {isAdmin ? (
                      <Link to="/admin" className="accountMenuItem" onClick={closeAccountMenu}>
                        Trang quản trị
                      </Link>
                    ) : (
                      <>
                        <Link to="/wishlist" className="accountMenuItem" onClick={closeAccountMenu}>
                          Yêu thích
                        </Link>
                        <Link to="/orders" className="accountMenuItem" onClick={closeAccountMenu}>
                          Lịch sử đơn hàng
                        </Link>
                        <Link to="/my-returns" className="accountMenuItem" onClick={closeAccountMenu}>
                          Trả hàng &amp; hoàn tiền
                        </Link>
                        <Link to="/my-feedback" className="accountMenuItem" onClick={closeAccountMenu}>
                          Đánh giá sản phẩm
                        </Link>
                      </>
                    )}
                    <button
                      type="button"
                      className="accountMenuLogout"
                      onClick={() => {
                        closeMenu();
                        logout();
                        navigate("/");
                      }}
                    >
                      Đăng xuất
                    </button>
                  </div>
                  } {/* đóng accountMenuOpen && */}
                </div>
              </div>
            ) : (
              <>
                <button
                  type="button"
                  className="iconBtn"
                  onClick={() => navigate("/login")}
                >
                  <UserIcon />
                </button>
                <Link to="/login" className="loginBtn">
                  Đăng Nhập <ArrowIcon />
                </Link>
              </>
            )}

            <button
              type="button"
              className={`hamburger ${menuOpen ? "hamburgerOpen" : ""}`}
              onClick={() => setMenuOpen(!menuOpen)}
              aria-expanded={menuOpen}
              aria-label="Mở menu"
            >
              <span className="hamburgerLine" />
              <span className="hamburgerLine" />
              <span className="hamburgerLine" />
            </button>
          </div>
        </div>
      </header>

      <div className={`mobileMenu ${menuOpen ? "mobileMenuOpen" : ""}`}>
        <div className="mobileSearchWrapper">
          <SearchBar />
        </div>

        <nav className="mobileNavLinks">
          {navLinks.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              className="mobileNavLink"
              onClick={closeMenu}
            >
              {label}
            </Link>
          ))}
          {!isAdmin && (
            <Link to="/cart" className="mobileNavLink" onClick={closeMenu}>
              Giỏ hàng
              {cartCount > 0 ? ` (${cartCount > 99 ? "99+" : cartCount})` : ""}
            </Link>
          )}
        </nav>

        <div className="mobileActions">
          {user ? (
            <>
              {/* Avatar trong mobile menu */}
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.25rem" }}>
                {user.avatar && (
                  <img
                    src={user.avatar}
                    alt=""
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: "50%",
                      objectFit: "cover",
                      border: "1.5px solid rgba(245,85,84,0.35)",
                      flexShrink: 0,
                    }}
                  />
                )}
                <span className="mobileUserName">Chào, {displayName}</span>
              </div>
              {!isAdmin && (
                <Link to="/dashboard" className="mobileNavLink" onClick={closeMenu}>
                  Tổng quan tài khoản
                </Link>
              )}
              <Link to="/profile" className="mobileNavLink" onClick={closeMenu}>
                Tài khoản
              </Link>
              {isAdmin ? (
                <Link to="/admin" className="mobileNavLink" onClick={closeMenu}>
                  Trang quản trị
                </Link>
              ) : (
                <>
                  <Link to="/orders" className="mobileNavLink" onClick={closeMenu}>
                    Đơn hàng
                  </Link>
                  <Link to="/my-returns" className="mobileNavLink" onClick={closeMenu}>
                    Trả hàng &amp; hoàn tiền
                  </Link>
                  <Link to="/my-feedback" className="mobileNavLink" onClick={closeMenu}>
                    Đánh giá sản phẩm
                  </Link>
                  <Link to="/wishlist" className="mobileNavLink" onClick={closeMenu}>
                    Yêu thích
                  </Link>
                </>
              )}
              <button
                type="button"
                className="mobileLogoutBtn"
                onClick={() => {
                  closeMenu();
                  logout();
                  navigate("/");
                }}
              >
                Đăng xuất
              </button>
            </>
          ) : (
            <Link to="/login" className="mobileLoginBtn" onClick={closeMenu}>
              Đăng Nhập / Đăng Ký
            </Link>
          )}
        </div>
      </div>
    </>
  );
}