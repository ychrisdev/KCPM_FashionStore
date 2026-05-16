import { useState, useEffect, useRef } from "react";
import type { Product } from "../types";
import { cart } from "../api/client";
import { useAuth } from "../context/AuthContext";
import "../styles/components/ProductDetail.css";
import "../styles/components/ProductCardModal.css";

type NotifType = "success" | "error" | "info" | "warning";
interface Notification {
  id: number;
  type: NotifType;
  message: string;
}

let _notifId = 0;

interface ProductCardModalProps {
  isOpen: boolean;
  onClose: () => void;
  product: Product;
}

const PLACEHOLDER_IMAGE = "https://via.placeholder.com/300x400?text=San+pham";

export default function ProductCardModal({
  isOpen,
  onClose,
  product,
}: ProductCardModalProps) {
  const { user } = useAuth();
  const [isAdding, setIsAdding] = useState(false);
  const [selectedSize, setSelectedSize] = useState<string>("");
  const [selectedColor, setSelectedColor] = useState<string>("");
  const [quantity, setQuantity] = useState(1);
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const productImage = product.image || PLACEHOLDER_IMAGE;
  const productStock = product.stock ?? 99;
  const variants = product.variants ?? [];

  const findVariantForColor = (colorName: string, preferredSize?: string) =>
    variants.find(
      (v) => v.color.name === colorName && v.size.name === preferredSize,
    ) ||
    variants.find((v) => v.color.name === colorName && (v.stock ?? 0) > 0) ||
    variants.find((v) => v.color.name === colorName) ||
    null;

  const findVariantForSize = (sizeName: string, preferredColor?: string) =>
    variants.find(
      (v) => v.size.name === sizeName && v.color.name === preferredColor,
    ) ||
    variants.find((v) => v.size.name === sizeName && (v.stock ?? 0) > 0) ||
    variants.find((v) => v.size.name === sizeName) ||
    null;

  const discountedPrice = (price: string, pct: number) =>
    (parseFloat(price) * (1 - pct / 100)).toFixed(0);

  useEffect(() => {
    if (isOpen) {
      const firstVariant =
        variants.find((v) => (v.stock ?? 0) > 0) || variants[0];
      setSelectedColor(firstVariant?.color.name || "");
      setSelectedSize(firstVariant?.size.name || "");
      setQuantity(1);
    }
  }, [isOpen, variants]);

  useEffect(() => {
    if (!variants.length) return;
    const selectedVariantExists = variants.some(
      (v) => v.size.name === selectedSize && v.color.name === selectedColor,
    );
    if (selectedVariantExists) return;

    const fallbackVariant =
      findVariantForColor(selectedColor, selectedSize) ||
      findVariantForSize(selectedSize, selectedColor) ||
      variants.find((v) => (v.stock ?? 0) > 0) ||
      variants[0];

    if (!fallbackVariant) return;
    setSelectedColor(fallbackVariant.color.name);
    setSelectedSize(fallbackVariant.size.name);
  }, [selectedColor, selectedSize, variants]);

  const sizes =
    variants.length > 0
      ? [
          ...new Map(
            [...variants]
              .sort((a, b) => (a.size.order ?? 0) - (b.size.order ?? 0))
              .map((v) => [v.size.name, v.size.name]),
          ).keys(),
        ]
      : [];
  const colors =
    variants.length > 0 ? [...new Set(variants.map((v) => v.color.name))] : [];

  const selectedVariant = variants.find(
    (v) => v.size.name === selectedSize && v.color.name === selectedColor,
  );
  const variantStock =
    variants.length > 0 ? (selectedVariant?.stock ?? 0) : productStock;

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

  const addingRef = useRef(false);

  const handleAddToCartConfirm = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (addingRef.current) return;
    if (!user) {
      notify("Vui lòng đăng nhập để thêm vào giỏ hàng", "warning");
      return;
    }

    if (product.variants?.length && !selectedVariant) {
      notify("Vui lòng chọn size và màu sắc.", "warning");
      return;
    }

    addingRef.current = true;
    setIsAdding(true);
    try {
      await cart.addItem({
        quantity,
        ...(selectedVariant
          ? { product_variant_id: selectedVariant.id }
          : { product_id: product.id }),
      });
      notify("Đã thêm vào giỏ hàng!", "success");
      await new Promise((res) => setTimeout(res, 1500));
      setTimeout(() => onClose(), 0);
    } catch (err: unknown) {
      const ax = err as {
        response?: {
          status?: number;
          data?: { quantity?: string[]; detail?: string };
        };
      };

      const status = ax.response?.status;
      const data = ax.response?.data;
      const q = data?.quantity;
      const apiMsg = Array.isArray(q) ? q[0] : data?.detail;

      if (status === 401) {
        notify("Phiên đăng nhập hết hạn, vui lòng đăng nhập lại.", "error");
      } else if (typeof apiMsg === "string") {
        notify(apiMsg, "error");
      } else {
        notify("Không thể thêm vào giỏ hàng. Vui lòng thử lại.", "error");
      }
    } finally {
      setIsAdding(false);
      addingRef.current = false;
    }
  };

  if (!isOpen) return null;

  return (
    <>
      <div
        className="modal-overlay"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          if (e.target === e.currentTarget) onClose();
        }}
        style={{ zIndex: 1000 }}
      >
        <div
          className="modal product-card-modal"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
          }}
        >
          <div className="modal-header">
            <h3>Thêm vào giỏ hàng</h3>
            <button
              type="button"
              className="modal-close"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onClose();
              }}
            >
              &#215;
            </button>
          </div>

          <div
            className="modal-body"
            style={{ display: "flex", flexDirection: "column", gap: "20px" }}
          >
            <div style={{ display: "flex", gap: "15px" }}>
              <img
                src={productImage}
                alt={product.name}
                style={{
                  width: "80px",
                  height: "80px",
                  objectFit: "cover",
                  borderRadius: "8px",
                }}
              />
              <div>
                <div
                  style={{
                    fontWeight: "bold",
                    fontSize: "1rem",
                    color: "var(--pd-text)",
                  }}
                >
                  {product.name}
                </div>
                <div className="productCardPrice" style={{ marginTop: "5px" }}>
                  {product.promotion ? (
                    <>
                      <span className="productCardCurrentPrice">
                        {Number(
                          discountedPrice(
                            product.price,
                            product.promotion.discount_percent,
                          ),
                        ).toLocaleString("vi-VN")}
                        đ
                      </span>
                      <span
                        className="productCardOldPrice"
                        style={{ marginLeft: "8px" }}
                      >
                        {Number(product.price).toLocaleString("vi-VN")}đ
                      </span>
                    </>
                  ) : (
                    <span className="productCardCurrentPrice">
                      {Number(product.price).toLocaleString("vi-VN")}đ
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="product-options" style={{ marginBottom: 0 }}>
              {colors.length > 0 && (
                <div className="option-group color-selection">
                  <label>
                    Màu sắc:{" "}
                    <span className="color-name-label">{selectedColor}</span>
                  </label>
                  <div className="color-buttons">
                    {colors.map((color) => {
                      const variant = variants.find(
                        (v) => v.color.name === color,
                      );
                      const code = variant?.color.code || "#888";
                      const isWhite = ["#ffffff", "#fff", "white"].includes(
                        code.toLowerCase(),
                      );
                      const hasStock = variants.some(
                        (v) => v.color.name === color && (v.stock ?? 0) > 0,
                      );
                      return (
                        <button
                          key={color}
                          type="button"
                          className={`color-btn${selectedColor === color ? " selected" : ""}${isWhite ? " white" : ""}${!hasStock ? " out-of-stock" : ""}`}
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            const nextVariant = findVariantForColor(
                              color,
                              selectedSize,
                            );
                            if (!nextVariant) return;
                            setSelectedColor(nextVariant.color.name);
                            setSelectedSize(nextVariant.size.name);
                          }}
                          style={{ backgroundColor: code }}
                          title={`${color}${!hasStock ? " (Hết hàng)" : ""}`}
                          aria-label={color}
                        />
                      );
                    })}
                  </div>
                </div>
              )}

              {sizes.length > 0 && (
                <div className="option-group size-selection">
                  <label>Kích thước:</label>
                  <div className="size-buttons">
                    {sizes.map((size) => {
                      const variantForSize = variants.find(
                        (v) =>
                          v.size.name === size &&
                          v.color.name === selectedColor,
                      );
                      const sizeHasStock = variantForSize
                        ? (variantForSize.stock ?? 0) > 0
                        : false;
                      return (
                        <button
                          key={size}
                          type="button"
                          className={`size-btn${selectedSize === size ? " selected" : ""}${!sizeHasStock ? " out-of-stock" : ""}`}
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            const nextVariant = findVariantForSize(
                              size,
                              selectedColor,
                            );
                            if (!nextVariant) return;
                            setSelectedColor(nextVariant.color.name);
                            setSelectedSize(nextVariant.size.name);
                          }}
                          title={!sizeHasStock ? `${size} (Hết hàng)` : size}
                        >
                          {size}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              <div className="option-group quantity-selection">
                <label>Số lượng:</label>
                <div className="qty-row">
                  <div className="quantity-controls">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setQuantity(Math.max(1, quantity - 1));
                      }}
                    >
                      −
                    </button>
                    <span>{quantity}</span>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setQuantity(Math.min(variantStock, quantity + 1));
                      }}
                      disabled={variantStock === 0}
                    >
                      +
                    </button>
                  </div>
                  <span
                    className={`stock-info${variantStock === 0 ? " out" : variantStock <= 5 ? " low" : ""}`}
                  >
                    {variantStock === 0
                      ? "Hết hàng"
                      : variantStock <= 5
                        ? `Chỉ còn ${variantStock} sản phẩm`
                        : `${variantStock} sản phẩm có sẵn`}
                  </span>
                </div>
              </div>
            </div>

            <button
              className="add-to-cart-btn"
              onClick={handleAddToCartConfirm}
              disabled={variantStock === 0 || isAdding}
              style={{ width: "100%", marginTop: "10px" }}
              type="button"
            >
              {variantStock === 0
                ? "Hết hàng"
                : isAdding
                  ? "Thêm vào giỏ hàng"
                  : "Thêm vào giỏ hàng"}
            </button>
          </div>
        </div>
      </div>

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
