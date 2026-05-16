import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { cart } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { notifyCartUpdated } from "../utils/cartEvents";
import "../styles/pages/Cart.css";

const PLACEHOLDER_IMAGE = "https://via.placeholder.com/120x160?text=SP";

interface CartProduct {
  id: number;
  name: string;
  price: string;
  image?: string;
  promotion?: { discount_percent: number } | null;
}

interface VariantInfo {
  color: { id: number; name: string; code: string };
  size: { id: number; name: string };
}

interface CartItemType {
  id: number;
  product?: CartProduct;
  variant_info?: VariantInfo | null;
  quantity: number;
  stock?: number;
}

function getUnitPrice(item: CartItemType): number {
  const product = item.product;
  if (!product) return 0;
  let price = parseFloat(String(product.price ?? 0));
  if (product.promotion?.discount_percent) {
    price = price * (1 - product.promotion.discount_percent / 100);
  }
  return price;
}

function formatCurrency(value: number): string {
  return `${value.toLocaleString("vi-VN")}đ`;
}

export default function Cart() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [items, setItems] = useState<CartItemType[]>([]);
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [selectedItemIds, setSelectedItemIds] = useState<number[]>([]);
  const [selectionInitialized, setSelectionInitialized] = useState(false);

  const fetchCart = () => {
    if (!user) {
      setItems([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    cart
      .get()
      .then((res) => {
        const raw = res.data as { items?: CartItemType[] } | CartItemType[];
        const list = Array.isArray(raw)
          ? ((raw[0] as { items?: CartItemType[] })?.items ?? [])
          : (raw.items ?? []);
        const safeList = Array.isArray(list) ? list : [];

        setItems(safeList);
        setSelectedItemIds((prev) => {
          if (!selectionInitialized) {
            return safeList.map((item) => item.id);
          }
          const availableIds = new Set(safeList.map((item) => item.id));
          return prev.filter((id) => availableIds.has(id));
        });
        setSelectionInitialized(true);
      })
      .catch(() => setItems([]))
      .finally(() => {
        setLoading(false);
        notifyCartUpdated();
      });
  };

  useEffect(() => {
    fetchCart();
  }, [user]);

  const selectedItems = items.filter((item) =>
    selectedItemIds.includes(item.id),
  );
  const allSelected =
    items.length > 0 && selectedItemIds.length === items.length;
  const selectedSubtotal = selectedItems.reduce(
    (sum, item) => sum + getUnitPrice(item) * item.quantity,
    0,
  );
  const shipping = selectedSubtotal >= 500000 ? 0 : 30000;
  const total = selectedSubtotal + shipping;

  const handleToggleItem = (itemId: number) => {
    setSelectedItemIds((prev) =>
      prev.includes(itemId)
        ? prev.filter((id) => id !== itemId)
        : [...prev, itemId],
    );
  };

  const handleToggleAll = () => {
    setSelectedItemIds((prev) =>
      prev.length === items.length ? [] : items.map((item) => item.id),
    );
  };

  const handleUpdateQty = async (id: number, newQty: number) => {
    if (newQty < 1) return;

    const item = items.find((entry) => entry.id === id);
    if (item?.stock != null && newQty > item.stock) {
      alert(`Chỉ còn ${item.stock} sản phẩm trong kho.`);
      return;
    }

    setUpdatingId(id);
    try {
      await cart.updateItem(id, newQty);
      setItems((prev) =>
        prev.map((entry) =>
          entry.id === id ? { ...entry, quantity: newQty } : entry,
        ),
      );
      notifyCartUpdated();
    } catch (err) {
      const response = (
        err as {
          response?: { data?: { quantity?: string[]; detail?: string } };
        }
      )?.response;
      const quantityError = response?.data?.quantity;
      const message =
        Array.isArray(quantityError) && typeof quantityError[0] === "string"
          ? quantityError[0]
          : response?.data?.detail || "Không thể cập nhật số lượng.";
      alert(message);
      fetchCart();
    } finally {
      setUpdatingId(null);
    }
  };

  const handleRemove = async (id: number) => {
    await cart.removeItem(id);
    setItems((prev) => prev.filter((item) => item.id !== id));
    setSelectedItemIds((prev) => prev.filter((itemId) => itemId !== id));
    notifyCartUpdated();
  };

  const handleCheckout = () => {
    if (selectedItemIds.length === 0) {
      alert("Vui lòng chọn ít nhất một sản phẩm để thanh toán.");
      return;
    }
    const params = new URLSearchParams();
    params.set("items", selectedItemIds.join(","));
    navigate(`/checkout?${params.toString()}`);
  };

  if (user?.can_access_admin) {
    return (
      <section className="pageSection">
          <div className="cart-empty">
            <h2>Không khả dụng</h2>
            <p>Tài khoản quản trị không thể sử dụng giỏ hàng.</p>
            <div className="cart-empty-actions">
              <Link to="/admin" className="cart-btn-primary">
                Trang quản trị
              </Link>
            </div>
          </div>
      </section>
    );
  }

  if (!user) {
    return (
      <div className="cart-empty-wrapper">
        <div className="cart-empty">
          <h2>Chưa đăng nhập</h2>
          <p>Vui lòng đăng nhập để xem giỏ hàng của bạn.</p>
          <div className="cart-empty-actions">
            <Link to="/login" className="cart-btn-primary">
              Đăng nhập
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return <div className="cart-loading">Đang tải...</div>;
  }

  if (items.length === 0) {
    return (
      <section className="cart-container">
        <h1 className="cart-title">Giỏ hàng</h1>

        <div className="cart-empty-wrapper">
          <div className="cart-empty">
            <h2>Giỏ hàng trống</h2>
            <p>Bạn chưa thêm sản phẩm nào vào giỏ hàng.</p>

            <Link to="/products" className="cart-btn-primary">
              Mua ngay
            </Link>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="cart-container">
      <h1 className="cart-title">Giỏ hàng</h1>

      <div className="cart-layout">
        <div className="cart-list">
          <div className="cart-selection-bar">
            <label className="cart-check cart-check--master">
              <input
                type="checkbox"
                checked={allSelected}
                onChange={handleToggleAll}
              />
              <span>Chọn tất cả ({items.length} sản phẩm)</span>
            </label>
            <span className="cart-selection-meta">
              Đã chọn {selectedItems.length}/{items.length} sản phẩm
            </span>
          </div>

          {items.map((item) => {
            const price = getUnitPrice(item);
            const totalItem = price * item.quantity;
            const isSelected = selectedItemIds.includes(item.id);

            return (
              <div
                key={item.id}
                className={`cart-item ${isSelected ? "cart-item--selected" : ""}`}
              >
                <label className="cart-check">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => handleToggleItem(item.id)}
                    aria-label={`Chọn ${item.product?.name ?? "sản phẩm"}`}
                  />
                </label>

                <img
                  src={item.product?.image || PLACEHOLDER_IMAGE}
                  alt={item.product?.name ?? "Sản phẩm"}
                />

                <div className="cart-info">
                  <h3>{item.product?.name}</h3>

                  {item.variant_info && (
                    <span className="variant">
                      {item.variant_info.color.name} /{" "}
                      {item.variant_info.size.name}
                    </span>
                  )}

                  {item.product?.promotion && (
                    <span className="badge">
                      -{item.product.promotion.discount_percent}%
                    </span>
                  )}
                </div>

                <div className="price">{formatCurrency(price)}</div>

                <div className="qty">
                  <button
                    type="button"
                    disabled={updatingId === item.id}
                    onClick={() => handleUpdateQty(item.id, item.quantity - 1)}
                  >
                    -
                  </button>
                  <span>{item.quantity}</span>
                  <button
                    type="button"
                    disabled={
                      updatingId === item.id ||
                      (item.stock != null && item.quantity >= item.stock)
                    }
                    title={
                      item.stock != null ? `Tối đa ${item.stock}` : undefined
                    }
                    onClick={() => handleUpdateQty(item.id, item.quantity + 1)}
                  >
                    +
                  </button>
                </div>

                <div className="total">{formatCurrency(totalItem)}</div>

                <button
                  type="button"
                  className="remove"
                  onClick={() => handleRemove(item.id)}
                >
                  Xóa
                </button>
              </div>
            );
          })}
        </div>

        <aside className="cart-summary">
          <h3>Tóm tắt đơn hàng</h3>

          <div className="cart-summary-selected">
            Bạn đang chọn <strong>{selectedItems.length}</strong> sản phẩm để
            thanh toán.
          </div>

          {selectedItems.length > 0 && shipping === 0 && (
            <div className="free-ship">Miễn phí vận chuyển</div>
          )}

          <div className="row">
            <span>Tạm tính</span>
            <span>{formatCurrency(selectedSubtotal)}</span>
          </div>

          <div className="row">
            <span>Phí vận chuyển</span>
            <span>
              {selectedItems.length === 0
                ? "—"
                : shipping === 0
                  ? "Miễn phí"
                  : formatCurrency(shipping)}
            </span>
          </div>

          <div className="total-final">
            {formatCurrency(selectedItems.length === 0 ? 0 : total)}
          </div>

          <button
            type="button"
            className="checkout"
            disabled={selectedItems.length === 0}
            onClick={handleCheckout}
          >
            {selectedItems.length === 0
              ? "Chọn sản phẩm để thanh toán"
              : "Thanh toán sản phẩm đã chọn"}
          </button>
        </aside>
      </div>
    </section>
  );
}
