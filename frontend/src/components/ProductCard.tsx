import { useState, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { Product } from "../types";
import { useAuth } from "../context/AuthContext";
import { useWishlist } from "../hooks/useWishlist";
import ProductCardModal from "./ProductCardModal";
import "../styles/components/ProductCard.css";

const PLACEHOLDER_IMAGE = "https://via.placeholder.com/300x400?text=San+pham";

type NotifType = "success" | "error" | "info" | "warning";
interface Notification {
  id: number;
  type: NotifType;
  message: string;
}

let _notifId = 0;

interface ProductCardProps {
  product: Product;
  onAddToCart?: (product: Product) => void;
}

export default function ProductCard({
  product,
  onAddToCart,
}: ProductCardProps) {
  const { user } = useAuth();
  const { ids, toggle: toggleWishlist } = useWishlist();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const notify = (
    message: string,
    type: NotifType = "info",
    duration = 4000,
  ) => {
    const notif: Notification = { id: ++_notifId, type, message };
    setNotifications((prev) => [...prev, notif]);
    if (duration > 0) setTimeout(() => removeNotif(notif.id), duration);
  };

  const removeNotif = (notifId: number) => {
    setNotifications((prev) => prev.filter((n) => n.id !== notifId));
  };

  const isAdmin = Boolean(user?.can_access_admin);
  const isWishlisted = ids.includes(product.id);
  const productImage = product.image || PLACEHOLDER_IMAGE;
  const productStock = product.stock ?? 99;

  const discountedPrice = (price: string, pct: number) =>
    (parseFloat(price) * (1 - pct / 100)).toFixed(0);

  const handleOpenModal = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (onAddToCart) {
      onAddToCart(product);
      return;
    }
    setIsModalOpen(true);
  };

  const handleWishlist = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!user) {
      notify("Vui lòng đăng nhập để dùng yêu thích.", "warning");
      return;
    }
    toggleWishlist(product.id);
  };

  const outOfStock = productStock === 0;

  const minVariantPrice = useMemo(() => {
    const vs = product.variants ?? [];
    if (vs.length === 0) return null;
    const prices = vs
      .map((v) => v.effective_price ?? v.price ?? Number(product.price))
      .filter((p) => p > 0);
    return prices.length > 0 ? Math.min(...prices) : null;
  }, [product]);

  const minVariantOriginalPrice = useMemo(() => {
    const vs = product.variants ?? [];
    if (vs.length === 0 || !product.promotion) return null;
    const prices = vs
      .map((v) => v.price ?? Number(product.price))
      .filter((p) => p > 0);
    return prices.length > 0 ? Math.min(...prices) : null;
  }, [product]);

  const priceRange = useMemo(() => {
    const vs = product.variants ?? [];
    if (vs.length === 0) return null;

    const prices = vs
      .map((v) => v.effective_price ?? v.price ?? Number(product.price))
      .filter((p) => p > 0);

    if (prices.length === 0) return null;

    const min = Math.min(...prices);
    const max = Math.max(...prices);
    return { min, max, hasRange: min !== max };
  }, [product]);

  const originalPriceRange = useMemo(() => {
    const vs = product.variants ?? [];
    if (vs.length === 0 || !product.promotion) return null;

    const prices = vs
      .map((v) => v.price ?? Number(product.price))
      .filter((p) => p > 0);

    if (prices.length === 0) return null;
    return Math.min(...prices);
  }, [product]);

  const displayCurrentPrice =
    priceRange?.min ??
    (product.promotion
      ? Math.round(
          parseFloat(product.price) *
            (1 - product.promotion.discount_percent / 100),
        )
      : Number(product.price));

  return (
    <>
      <div
        onClick={() => navigate(`/product/${product.id}`)}
        className="productCard"
        style={{ cursor: "pointer" }}
      >
        <div className="productCardImageWrapper">
          <img
            src={productImage}
            alt={product.name}
            className="productCardImage"
            loading="lazy"
          />

          {product.promotion && (
            <span className="productCardDiscount">
              -{product.promotion.discount_percent}%
            </span>
          )}

          <div className="productCardActions">
            {!isAdmin && (
              <button
                className={`productCardActionBtn${isWishlisted ? " wishlisted" : ""}`}
                onClick={handleWishlist}
                aria-label={isWishlisted ? "Bỏ yêu thích" : "Thêm yêu thích"}
              >
                {isWishlisted ? "♥" : "♡"}
              </button>
            )}
            <Link
              to={`/product/${product.id}`}
              className="productCardActionBtn"
              onClick={(e) => e.stopPropagation()}
              aria-label="Xem chi tiết"
            >
              👁
            </Link>
          </div>
        </div>

        <div className="productCardContent">
          <p className="productCardCategory">{product.category.name}</p>
          <h3 className="productCardName">{product.name}</h3>

          <div className="productCardPrice">
            {product.promotion ? (
              <>
                <span className="productCardCurrentPrice">
                  {priceRange?.hasRange
                    ? `${priceRange.min.toLocaleString("vi-VN")}đ – ${priceRange.max.toLocaleString("vi-VN")}đ`
                    : `${displayCurrentPrice.toLocaleString("vi-VN")}đ`}
                </span>
                <span className="productCardOldPrice">
                  {(originalPriceRange ?? Number(product.price)).toLocaleString(
                    "vi-VN",
                  )}
                  đ
                </span>
              </>
            ) : (
              <span className="productCardCurrentPrice">
                {priceRange?.hasRange
                  ? `${priceRange.min.toLocaleString("vi-VN")}đ – ${priceRange.max.toLocaleString("vi-VN")}đ`
                  : `${displayCurrentPrice.toLocaleString("vi-VN")}đ`}
              </span>
            )}
          </div>

          <div className="productCardMeta">
            <span className="productCardRating">
              ⭐ {Number(product.rating ?? 0).toFixed(1)}
            </span>
            <span className="productCardSold">
              Đã bán {(product.sold_count ?? 0).toLocaleString("vi-VN")}
            </span>
          </div>
          {!isAdmin && (
            <button
              className="productCardAddBtn"
              onClick={handleOpenModal}
              disabled={outOfStock}
            >
              {outOfStock ? "Hết hàng" : "Thêm vào giỏ"}
            </button>
          )}
        </div>
      </div>

      {!isAdmin && (
        <ProductCardModal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          product={product}
        />
      )}

      {notifications.length > 0 && (
        <div className="notification-stack">
          {notifications.map((n) => (
            <div key={n.id} className={`notification notification--${n.type}`}>
              <span className="notification__icon">
                {n.type === "success" && "✓"}
                {n.type === "error" && "✕"}
                {n.type === "warning" && "!"}
                {n.type === "info" && "i"}
              </span>
              <span className="notification__message">{n.message}</span>
              <button
                type="button"
                className="notification__close"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  removeNotif(n.id);
                }}
                aria-label="Đóng thông báo"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
