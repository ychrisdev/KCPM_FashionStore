import { useEffect, useState, useRef } from "react";
import {
  Link,
  useLocation,
  useNavigate,
  useSearchParams,
} from "react-router-dom";
import { api, cart, orders } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { notifyCartUpdated } from "../utils/cartEvents";
import {
  assignGatewayUrl,
  closeGatewayTab,
  openBlankGatewayTab,
} from "../utils/gatewayTab";
import { getEstimatedDeliveryTime } from "../utils/delivery";
import "../styles/pages/Checkout.css";

const PLACEHOLDER_IMAGE = "https://via.placeholder.com/80x100?text=SP";

interface CartItemType {
  id: number;
  product?: {
    id: number;
    name: string;
    price: string;
    image?: string;
    promotion?: { discount_percent: number } | null;
  };
  variant_info?: {
    color: { id: number; name: string; code: string };
    size: { id: number; name: string };
  } | null;
  quantity: number;
}

interface PricingPreview {
  subtotal: string;
  shipping_fee: string;
  discount_amount: string;
  total_price: string;
  discount_code: string;
  discount_name: string;
  discount_percent: number;
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

function parseMoney(value: string | number | undefined): number {
  if (value == null) return 0;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function normalizeDiscountCode(value: string): string {
  return value.trim().toUpperCase();
}

function parseSelectedCartItemIds(rawValue: string | null): number[] {
  if (!rawValue) return [];
  const ids = rawValue
    .split(",")
    .map((value) => Number(value.trim()))
    .filter((value) => Number.isInteger(value) && value > 0);
  return [...new Set(ids)];
}

const SESSION_CART_KEY = "checkout_cart_items";
const SESSION_CART_IDS_KEY = "checkout_cart_ids";

function getStoredCartItems(): { items: CartItemType[]; ids: number[] } | null {
  try {
    const items = sessionStorage.getItem(SESSION_CART_KEY);
    const ids = sessionStorage.getItem(SESSION_CART_IDS_KEY);
    if (items && ids) {
      return { items: JSON.parse(items), ids: JSON.parse(ids) };
    }
  } catch { /* ignore */ }
  return null;
}

function storeCartItems(items: CartItemType[], ids: number[]): void {
  try {
    sessionStorage.setItem(SESSION_CART_KEY, JSON.stringify(items));
    sessionStorage.setItem(SESSION_CART_IDS_KEY, JSON.stringify(ids));
  } catch { /* ignore */ }
}

function clearStoredCart(): void {
  try {
    sessionStorage.removeItem(SESSION_CART_KEY);
    sessionStorage.removeItem(SESSION_CART_IDS_KEY);
  } catch { /* ignore */ }
}

function getApiErrorMessage(data: unknown, fallback: string): string {
  if (!data) return fallback;
  if (typeof data === "string") {
    return data.trim().startsWith("<!DOCTYPE html>") ? fallback : data;
  }
  if (Array.isArray(data)) {
    return typeof data[0] === "string" ? data[0] : fallback;
  }
  if (typeof data === "object") {
    if ("detail" in data) {
      const detail = (data as { detail?: unknown }).detail;
      if (typeof detail === "string") return detail;
      if (Array.isArray(detail) && typeof detail[0] === "string")
        return detail[0];
    }
    if ("non_field_errors" in data) {
      const nonFieldErrors = (data as { non_field_errors?: unknown })
        .non_field_errors;
      if (
        Array.isArray(nonFieldErrors) &&
        typeof nonFieldErrors[0] === "string"
      )
        return nonFieldErrors[0];
    }
    const firstValue = Object.values(data as Record<string, unknown>)[0];
    if (typeof firstValue === "string") return firstValue;
    if (Array.isArray(firstValue) && typeof firstValue[0] === "string")
      return firstValue[0];
  }
  return fallback;
}

function shouldResetDiscountInput(message: string): boolean {
  const normalized = message.toLocaleLowerCase("vi-VN");
  return (
    normalized.includes("mã giảm giá") || normalized.includes("ma giam gia")
  );
}

export default function Checkout() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const selectedIdsFromQuery = parseSelectedCartItemIds(
    searchParams.get("items"),
  );
  const hasSpecificSelection = selectedIdsFromQuery.length > 0;
  const redirectTo = `${location.pathname}${location.search}` || "/checkout";

  const [items, setItems] = useState<CartItemType[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [discountLoading, setDiscountLoading] = useState(false);
  const [discountMessage, setDiscountMessage] = useState("");
  const [pricingPreview, setPricingPreview] = useState<PricingPreview | null>(
    null,
  );
  const [retryOrderStr] = useState(searchParams.get("retry_order_id"));
  const [retryOrder, setRetryOrder] = useState<any>(null);

  const [step, setStep] = useState<"shipping" | "confirm">("shipping");
  const [paymentMethod, setPaymentMethod] = useState<
    "cod" | "momo" | "zalopay" | "wallet"
  >("cod");
  const [walletBalance, setWalletBalance] = useState<number | null>(null);
  const [selectionNotice, setSelectionNotice] = useState("");
  const discountFromUrl =
    searchParams.get("discount")?.trim().toUpperCase() ?? "";

  const pendingCode = sessionStorage.getItem("pending_discount_code") ?? "";
  const [discountCode, setDiscountCode] = useState(
    discountFromUrl || pendingCode,
  );

  // Use ref to ensure cart is fetched only once on mount
  const cartFetchedRef = useRef(false);

  useEffect(() => {
    if (pendingCode) sessionStorage.removeItem("pending_discount_code");
  }, []);

  useEffect(() => {
    if (!discountFromUrl || items.length === 0) return;
    const normalized = discountFromUrl.trim().toUpperCase();
    setDiscountCode(normalized);
    orders
      .discountPreview({
        discount_code: normalized,
        cart_item_ids: items.map((item) => item.id),
      })
      .then((res) => {
        setPricingPreview(res.data as PricingPreview);
        setDiscountMessage("Áp dụng mã giảm giá thành công.");
      })
      .catch((err) => {
        const responseData = (err as { response?: { data?: unknown } })
          ?.response?.data;
        const message = getApiErrorMessage(
          responseData,
          "Mã giảm giá không hợp lệ.",
        );
        setDiscountMessage(message);
        setDiscountCode("");
      });
  }, [discountFromUrl, items.length]);

  const [form, setForm] = useState({
    name: "",
    phone: "",
    address: "",
    note: "",
  });

  const [provinces, setProvinces] = useState<any[]>([]);
  const [districts, setDistricts] = useState<any[]>([]);
  const [wards, setWards] = useState<any[]>([]);

  const [selectedProvinceCode, setSelectedProvinceCode] = useState<number | "">("");
  const [selectedDistrictCode, setSelectedDistrictCode] = useState<number | "">("");
  const [selectedWardCode, setSelectedWardCode] = useState<number | "">("");

  const [selectedProvinceName, setSelectedProvinceName] = useState("");
  const [selectedDistrictName, setSelectedDistrictName] = useState("");
  const [selectedWardName, setSelectedWardName] = useState("");

  const [addressLine, setAddressLine] = useState("");

  useEffect(() => {
    fetch("https://provinces.open-api.vn/api/p/")
      .then((res) => res.json())
      .then((data) => setProvinces(data))
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (!selectedProvinceCode) {
      setDistricts([]);
      setSelectedDistrictCode("");
      setSelectedDistrictName("");
      return;
    }
    fetch(`https://provinces.open-api.vn/api/p/${selectedProvinceCode}?depth=2`)
      .then((res) => res.json())
      .then((data) => setDistricts(data.districts || []))
      .catch(console.error);
  }, [selectedProvinceCode]);

  useEffect(() => {
    if (!selectedDistrictCode) {
      setWards([]);
      setSelectedWardCode("");
      setSelectedWardName("");
      return;
    }
    fetch(`https://provinces.open-api.vn/api/d/${selectedDistrictCode}?depth=2`)
      .then((res) => res.json())
      .then((data) => setWards(data.wards || []))
      .catch(console.error);
  }, [selectedDistrictCode]);

  useEffect(() => {
    if (!retryOrder?.payment_method) return;
    const m = String(retryOrder.payment_method).toLowerCase();
    if (m === "cod" || m === "momo" || m === "zalopay" || m === "wallet") {
      setPaymentMethod(m);
    }
  }, [retryOrder]);

  useEffect(() => {
    if (!user) return;
    if (step !== "confirm") return;
    let cancelled = false;
    api
      .get<{ balance: string | number }>("/wallets/info/")
      .then((r) => {
        if (cancelled) return;
        const b = r.data.balance;
        setWalletBalance(typeof b === "string" ? parseFloat(b) : Number(b));
      })
      .catch(() => {
        if (!cancelled) setWalletBalance(null);
      });
    return () => {
      cancelled = true;
    };
  }, [user, step, retryOrder?.id]);

  // Fetch cart only once on mount
  useEffect(() => {
    // Prevent multiple fetches
    if (cartFetchedRef.current) return;
    cartFetchedRef.current = true;

    if (!user) {
      setLoading(false);
      return;
    }

    if (retryOrderStr) {
      orders
        .get(Number(retryOrderStr))
        .then((res) => {
          const data = res.data;
          setRetryOrder(data);
          const mappedItems = (data.items || []).map((it: any) => ({
             id: it.id,
             product: {
               id: it.product?.id,
               name: it.product?.name,
               price: it.price,
               image: it.product?.image,
               promotion: null,
             },
             variant_info: it.variant_info,
             quantity: it.quantity,
          }));
          setItems(mappedItems);
          
          if (data.shipping) {
             setForm({
               name: data.shipping.name || "",
               phone: data.shipping.phone || "",
               address: data.shipping.address || "",
               note: data.shipping.note || "",
             });
             setStep("confirm");
          }
        })
        .catch(() => {
          setSelectionNotice("Không thể tải đơn hàng để thanh toán lại.");
        })
        .finally(() => setLoading(false));
      return;
    }

    // Load from sessionStorage first
    const stored = getStoredCartItems();
    if (stored && stored.items.length > 0) {
      if (!hasSpecificSelection) {
        setItems(stored.items);
        setLoading(false);
      } else {
        const filtered = stored.items.filter((item) =>
          selectedIdsFromQuery.includes(item.id),
        );
        setItems(filtered);
        setLoading(false);
        if (filtered.length === 0) {
          setSelectionNotice("Các sản phẩm bạn chọn không còn trong giỏ hàng.");
        } else if (filtered.length !== selectedIdsFromQuery.length) {
          setSelectionNotice(
            "Một số sản phẩm đã không còn trong giỏ. Hệ thống chỉ giữ lại các sản phẩm còn hợp lệ.",
          );
        } else {
          setSelectionNotice("");
        }
      }
    }

    // Fetch fresh data from API
    cart
      .get()
      .then((res) => {
        const data = res.data as { items?: CartItemType[] } | CartItemType[];
        const list = Array.isArray(data)
          ? ((data[0] as { items?: CartItemType[] })?.items ?? [])
          : (data.items ?? []);
        const safeList = Array.isArray(list) ? list : [];

        // Store in sessionStorage
        storeCartItems(safeList, safeList.map((item) => item.id));

        if (!hasSpecificSelection) {
          setItems(safeList);
          setSelectionNotice("");
        } else {
          const filtered = safeList.filter((item) =>
            selectedIdsFromQuery.includes(item.id),
          );
          setItems(filtered);

          if (filtered.length === 0) {
            setSelectionNotice("Các sản phẩm bạn chọn không còn trong giỏ hàng.");
          } else if (filtered.length !== selectedIdsFromQuery.length) {
            setSelectionNotice(
              "Một số sản phẩm đã không còn trong giỏ. Hệ thống chỉ giữ lại các sản phẩm còn hợp lệ.",
            );
          } else {
            setSelectionNotice("");
          }
        }
      })
      .catch(() => {
        // If API fails but we have stored items, keep them
        const stored = getStoredCartItems();
        if (!stored || stored.items.length === 0) {
          setItems([]);
        }
      })
      .finally(() => setLoading(false));
  }, [user]); // Only depend on user, not on selection params

  const selectedCartItemIds = items.map((item) => item.id);
  
  let subtotal = 0;
  if (retryOrder) {
    subtotal = parseMoney(retryOrder.subtotal);
  } else {
    subtotal = items.reduce(
      (sum, item) => sum + getUnitPrice(item) * item.quantity,
      0,
    );
  }
  
  const shippingFee = retryOrder ? parseMoney(retryOrder.shipping_fee) : (subtotal >= 500000 ? 0 : 30000);
  
  const pricing = retryOrder
    ? {
        subtotal,
        shippingFee,
        discountAmount: parseMoney(retryOrder.discount_amount),
        total: parseMoney(retryOrder.total_price),
      }
    : pricingPreview
    ? {
        subtotal: parseMoney(pricingPreview.subtotal),
        shippingFee: parseMoney(pricingPreview.shipping_fee),
        discountAmount: parseMoney(pricingPreview.discount_amount),
        total: parseMoney(pricingPreview.total_price),
      }
    : {
        subtotal,
        shippingFee,
        discountAmount: 0,
        total: subtotal + shippingFee,
      };

  const walletInsufficient =
    paymentMethod === "wallet" &&
    walletBalance !== null &&
    walletBalance < pricing.total;

  const appliedDiscountCode = retryOrder
    ? retryOrder.discount_code || retryOrder.discount_code_snapshot || ""
    : pricingPreview?.discount_code ?? "";
  const hasAppliedDiscount = !!appliedDiscountCode;

  const handleContinueToConfirm = () => {
    if (!form.name.trim() || !form.phone.trim() || !addressLine.trim() || !selectedProvinceName || !selectedDistrictName || !selectedWardName) {
      alert("Vui lòng điền đầy đủ họ tên, số điện thoại và địa chỉ.");
      return;
    }
    const fullAddress = `${addressLine.trim()}, ${selectedWardName}, ${selectedDistrictName}, ${selectedProvinceName}`;
    setForm((f) => ({ ...f, address: fullAddress }));
    setStep("confirm");
  };

  const handleApplyDiscount = async () => {
    const normalizedCode = normalizeDiscountCode(discountCode);
    if (!normalizedCode) {
      setPricingPreview(null);
      setDiscountMessage("Vui lòng nhập mã giảm giá.");
      return;
    }
    if (selectedCartItemIds.length === 0) {
      setPricingPreview(null);
      setDiscountMessage(
        "Vui lòng chọn sản phẩm trước khi áp dụng mã giảm giá.",
      );
      return;
    }

    setDiscountLoading(true);
    setDiscountMessage("");
    try {
      const res = await orders.discountPreview({
        discount_code: normalizedCode,
        cart_item_ids: selectedCartItemIds,
      });
      setPricingPreview(res.data as PricingPreview);
      setDiscountCode(normalizedCode);
      setDiscountMessage("Áp dụng mã giảm giá thành công.");
    } catch (err) {
      setPricingPreview(null);
      const responseData = (err as { response?: { data?: unknown } })?.response
        ?.data;
      const message = getApiErrorMessage(
        responseData,
        "Không thể áp dụng mã giảm giá.",
      );
      if (shouldResetDiscountInput(message)) {
        setDiscountCode("");
      }
      setDiscountMessage(message);
    } finally {
      setDiscountLoading(false);
    }
  };

  const handleClearDiscount = () => {
    setDiscountCode("");
    setPricingPreview(null);
    setDiscountMessage("");
  };

  const handleSubmit = async () => {
    if (!user || items.length === 0) return;

    if (walletInsufficient) {
      alert("Số dư ví không đủ để thanh toán đơn hàng này.");
      return;
    }

    const normalizedCode = normalizeDiscountCode(discountCode);
    if (!retryOrder && normalizedCode && appliedDiscountCode !== normalizedCode) {
      setDiscountCode("");
      setPricingPreview(null);
      setDiscountMessage(
        "Mã giảm giá chưa được áp dụng. Vui lòng nhập lại nếu vẫn muốn sử dụng.",
      );
      alert("Mã giảm giá chưa được áp dụng. Mã đã được xóa khỏi ô nhập.");
      return;
    }

    const gatewayTab =
      paymentMethod === "zalopay" || paymentMethod === "momo"
        ? openBlankGatewayTab()
        : null;

    setSubmitting(true);
    
    if (retryOrder) {
      try {
        const res = await orders.retryPayment(retryOrder.id, { payment_method: paymentMethod });
        const data = res.data as { payment_url?: string };
        const payUrl = typeof data.payment_url === "string" ? data.payment_url : "";
        if (payUrl) {
          if (assignGatewayUrl(gatewayTab, payUrl)) {
            navigate("/orders", {
              state: {
                orderPlaced: true,
                externalPayTab: true,
                orderId: retryOrder.id,
              },
            });
            return;
          }
          closeGatewayTab(gatewayTab);
          window.location.href = payUrl;
          return;
        }
        closeGatewayTab(gatewayTab);
        navigate("/orders", { state: { orderPlaced: true } });
      } catch (err) {
        closeGatewayTab(gatewayTab);
        const resData = (err as { response?: { data?: unknown } })?.response?.data;
        alert(getApiErrorMessage(resData, "Thanh toán lại thất bại. Vui lòng thử lại."));
      } finally {
        setSubmitting(false);
      }
      return;
    }
    try {
      const res = await orders.checkout({
        name: form.name.trim(),
        phone: form.phone.trim(),
        address: form.address.trim(),
        note: form.note.trim() || undefined,
        discount_code: appliedDiscountCode || undefined,
        cart_item_ids: selectedCartItemIds,
        payment_method: paymentMethod,
      });
      const data = res.data as {
        payment_url?: string;
        id?: number;
      };
      const payUrl =
        typeof data.payment_url === "string" ? data.payment_url : "";
      /* ZaloPay / MoMo: tab trống mở ngay khi bấm; gán URL khi có — cổng tải ở tab mới, trang này về đơn hàng. */
      if (payUrl) {
        clearStoredCart();
        notifyCartUpdated();
        if (assignGatewayUrl(gatewayTab, payUrl)) {
          setForm({ name: "", phone: "", address: "", note: "" });
          setDiscountCode("");
          setPricingPreview(null);
          setDiscountMessage("");
          navigate("/orders", {
            state: {
              orderPlaced: true,
              externalPayTab: true,
              orderId: typeof data.id === "number" ? data.id : undefined,
            },
          });
          return;
        }
        closeGatewayTab(gatewayTab);
        window.location.href = payUrl;
        return;
      }
      setForm({ name: "", phone: "", address: "", note: "" });
      setDiscountCode("");
      setPricingPreview(null);
      setDiscountMessage("");
      clearStoredCart();
      notifyCartUpdated();
      navigate("/orders", { state: { orderPlaced: true } });
    } catch (err) {
      closeGatewayTab(gatewayTab);
      const resData = (err as { response?: { data?: unknown } })?.response
        ?.data;
      alert(
        getApiErrorMessage(resData, "Đặt hàng thất bại. Vui lòng thử lại."),
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (user?.can_access_admin) {
    return (
      <section className="pageSection checkout-page">
        <div className="sectionContainer checkout-container">
          <div className="checkout-empty">
            <div className="checkout-empty-icon">🚫</div>
            <h2>Không khả dụng</h2>
            <p>Tài khoản quản trị không thể thực hiện thanh toán.</p>
            <div className="checkout-login-actions">
              <Link to="/admin" className="checkout-btn checkout-btn-primary">
                Trang quản trị
              </Link>
            </div>
          </div>
        </div>
      </section>
    );
  }

  if (!user) {
    return (
      <section className="pageSection checkout-page">
        <div className="sectionContainer checkout-container">
          <div className="checkout-login-prompt">
            <div className="checkout-login-icon">🔐</div>
            <h2>Vui lòng đăng nhập</h2>
            <p>Bạn cần đăng nhập để tiếp tục thanh toán.</p>
            <div className="checkout-login-actions">
              <Link
                to={`/login?redirect=${encodeURIComponent(redirectTo)}`}
                className="checkout-btn checkout-btn-primary"
              >
                Đăng nhập
              </Link>
              <Link
                to="/products"
                className="checkout-btn checkout-btn-secondary"
              >
                Tiếp tục mua sắm
              </Link>
            </div>
          </div>
        </div>
      </section>
    );
  }

  if (loading) {
    return (
      <section className="pageSection checkout-page">
        <div className="sectionContainer checkout-container">
          <div className="checkout-loading">Đang tải...</div>
        </div>
      </section>
    );
  }

  if (items.length === 0) {
    return (
      <section className="pageSection checkout-page">
        <div className="sectionContainer checkout-container">
          <div className="checkout-empty">
            <div className="checkout-empty-icon">🛒</div>
            <h2>Không có sản phẩm để thanh toán</h2>
            <p>{selectionNotice || "Bạn chưa có sản phẩm nào trong giỏ."}</p>
            <div className="checkout-login-actions">
              <Link to="/cart" className="checkout-btn checkout-btn-primary">
                Quay lại giỏ hàng
              </Link>
              <Link
                to="/products"
                className="checkout-btn checkout-btn-secondary"
              >
                Tiếp tục mua sắm
              </Link>
            </div>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="pageSection checkout-page">
                    {submitting &&
                      (paymentMethod === "zalopay" ||
                        paymentMethod === "momo") && (
        <div className="checkout-gatewayOverlay" role="status" aria-live="polite">
          <div className="checkout-gatewayOverlayCard">
            <span className="checkout-gatewaySpinner" aria-hidden />
            <p className="checkout-gatewayOverlayTitle">
              {paymentMethod === "zalopay"
                ? "Đang tạo phiên thanh toán ZaloPay…"
                : "Đang tạo phiên thanh toán MoMo…"}
            </p>
            <p className="checkout-gatewayOverlayHint">
              Đang liên hệ máy chủ cổng thanh toán. Nếu đã mở tab mới, vui lòng thanh toán ở đó;
              trang này sẽ chuyển tới đơn hàng sau khi sẵn sàng.
            </p>
          </div>
        </div>
      )}
      <div className="sectionContainer checkout-container">
        <div className="checkout-steps">
          <div
            className={`checkout-step ${step === "shipping" ? "active" : ""} ${step === "confirm" ? "completed" : ""}`}
          >
            <span className="checkout-step-num">
              {step === "confirm" ? "✓" : "1"}
            </span>
            <span className="checkout-step-label">Giao hàng</span>
          </div>
          <div className="checkout-step-line" />
          <div
            className={`checkout-step ${step === "confirm" ? "active" : ""}`}
          >
            <span className="checkout-step-num">2</span>
            <span className="checkout-step-label">Xác nhận</span>
          </div>
        </div>

        {selectionNotice && (
          <div className="checkout-selection-notice">{selectionNotice}</div>
        )}

        <div className="checkout-layout">
          <div className="checkout-main">
            {step === "shipping" && (
              <div className="checkout-card">
                <div className="checkout-card-header">
                  <h2 className="checkout-card-title">Thông tin giao hàng</h2>
                </div>
                <form
                  className="checkout-form"
                  onSubmit={(event) => {
                    event.preventDefault();
                    handleContinueToConfirm();
                  }}
                >
                  <div className="checkout-field">
                    <label htmlFor="name">Họ tên người nhận *</label>
                    <input
                      id="name"
                      type="text"
                      className="checkout-input"
                      placeholder="Nguyễn Văn A"
                      value={form.name}
                      onChange={(event) =>
                        setForm((current) => ({
                          ...current,
                          name: event.target.value,
                        }))
                      }
                      required
                    />
                  </div>
                  <div className="checkout-field">
                    <label htmlFor="phone">Số điện thoại *</label>
                    <input
                      id="phone"
                      type="tel"
                      className="checkout-input"
                      placeholder="0912 345 678"
                      value={form.phone}
                      onChange={(event) =>
                        setForm((current) => ({
                          ...current,
                          phone: event.target.value,
                        }))
                      }
                      required
                    />
                  </div>
                  <div className="checkout-field" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr)', gap: '16px', alignItems: 'start' }}>
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <label htmlFor="province">Tỉnh/Thành phố *</label>
                      <select
                        id="province"
                        className="checkout-input"
                        value={selectedProvinceCode}
                        onChange={(e) => {
                          const code = Number(e.target.value) || "";
                          setSelectedProvinceCode(code);
                          setSelectedProvinceName(e.target.options[e.target.selectedIndex].text);
                        }}
                        required
                      >
                        <option value="" disabled>-- Chọn Tỉnh --</option>
                        {provinces.map((p) => (
                          <option key={p.code} value={p.code}>{p.name}</option>
                        ))}
                      </select>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <label htmlFor="district">Quận/Huyện *</label>
                      <select
                        id="district"
                        className="checkout-input"
                        value={selectedDistrictCode}
                        onChange={(e) => {
                          const code = Number(e.target.value) || "";
                          setSelectedDistrictCode(code);
                          setSelectedDistrictName(e.target.options[e.target.selectedIndex].text);
                        }}
                        disabled={!selectedProvinceCode}
                        required
                      >
                        <option value="" disabled>-- Chọn Huyện --</option>
                        {districts.map((d) => (
                          <option key={d.code} value={d.code}>{d.name}</option>
                        ))}
                      </select>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <label htmlFor="ward">Phường/Xã *</label>
                      <select
                        id="ward"
                        className="checkout-input"
                        value={selectedWardCode}
                        onChange={(e) => {
                          const code = Number(e.target.value) || "";
                          setSelectedWardCode(code);
                          setSelectedWardName(e.target.options[e.target.selectedIndex].text);
                        }}
                        disabled={!selectedDistrictCode}
                        required
                      >
                        <option value="" disabled>-- Chọn Xã --</option>
                        {wards.map((w) => (
                          <option key={w.code} value={w.code}>{w.name}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div className="checkout-field">
                    <label htmlFor="addressLine">Địa chỉ cụ thể (số nhà, ngõ, đường) *</label>
                    <textarea
                      id="addressLine"
                      className="checkout-input checkout-textarea"
                      placeholder="Ví dụ: Số nhà 70, đường Tô Ký..."
                      rows={2}
                      value={addressLine}
                      onChange={(event) => setAddressLine(event.target.value)}
                      required
                    />
                  </div>
                  <div className="checkout-field">
                    <label htmlFor="note">Ghi chú (tùy chọn)</label>
                    <textarea
                      id="note"
                      className="checkout-input checkout-textarea"
                      placeholder="Ghi chú thêm cho đơn hàng..."
                      rows={2}
                      value={form.note}
                      onChange={(event) =>
                        setForm((current) => ({
                          ...current,
                          note: event.target.value,
                        }))
                      }
                    />
                  </div>
                  <button
                    type="submit"
                    className="checkout-btn checkout-btn-primary checkout-btn-full"
                  >
                    Tiếp tục
                  </button>
                </form>
              </div>
            )}

            {step === "confirm" && (
              <div className="checkout-card">
                <div className="checkout-card-header">
                  <h2 className="checkout-card-title">Xác nhận đơn hàng</h2>
                </div>

                <div className="checkout-summary-section">
                  <h3>Thông tin giao hàng</h3>
                  <div className="checkout-info-grid">
                    <div className="checkout-info-item">
                      <span className="checkout-info-label">Người nhận</span>
                      <span>{form.name}</span>
                    </div>
                    <div className="checkout-info-item">
                      <span className="checkout-info-label">Điện thoại</span>
                      <span>{form.phone}</span>
                    </div>
                    <div className="checkout-info-item">
                      <span className="checkout-info-label">Địa chỉ</span>
                      <span>{form.address}</span>
                    </div>
                  </div>
                  {!retryOrder && (
                    <button
                      type="button"
                      className="checkout-edit-btn"
                      onClick={() => setStep("shipping")}
                    >
                      Chỉnh sửa
                    </button>
                  )}
                </div>

                <div className="checkout-summary-section checkout-payment-section">
                  <h3>Phương thức thanh toán</h3>
                  <div className="checkout-payment-options" role="radiogroup">
                    <label className="checkout-payment-option">
                      <input
                        type="radio"
                        name="payment"
                        checked={paymentMethod === "cod"}
                        onChange={() => setPaymentMethod("cod")}
                      />
                      <span>
                        <strong>Thanh toán khi nhận hàng (COD)</strong>
                        <small>Trả tiền mặt lúc giao hàng</small>
                      </span>
                    </label>
                    <label className="checkout-payment-option">
                      <input
                        type="radio"
                        name="payment"
                        checked={paymentMethod === "wallet"}
                        disabled={
                          walletBalance !== null && walletBalance < pricing.total
                        }
                        onChange={() => setPaymentMethod("wallet")}
                      />
                      <span>
                        <strong>Ví trên ứng dụng</strong>
                        <small>
                          {walletBalance === null
                            ? "Đang tải số dư…"
                            : `Số dư: ${formatCurrency(walletBalance)}${
                                walletBalance < pricing.total
                                  ? " — không đủ cho đơn này"
                                  : ""
                              }`}
                        </small>
                      </span>
                    </label>
                    <label className="checkout-payment-option">
                      <input
                        type="radio"
                        name="payment"
                        checked={paymentMethod === "momo"}
                        onChange={() => setPaymentMethod("momo")}
                      />
                      <span>
                        <strong>Ví MoMo</strong>
                        <small>Quét QR hoặc thanh toán trong app MoMo</small>
                      </span>
                    </label>
                    <label className="checkout-payment-option">
                      <input
                        type="radio"
                        name="payment"
                        checked={paymentMethod === "zalopay"}
                        onChange={() => setPaymentMethod("zalopay")}
                      />
                      <span>
                        <strong>ZaloPay</strong>
                        <small>
                          Sau khi đặt hàng bạn được chuyển sang trang cổng ZaloPay (QR trên đó); quét
                          bằng app ZaloPay sandbox
                        </small>
                      </span>
                    </label>
                  </div>
                </div>

                <div className="checkout-summary-section">
                  <h3>Sản phẩm đã chọn — {items.length} món</h3>
                  <ul className="checkout-product-list">
                    {items.map((item) => {
                      const unitPrice = getUnitPrice(item);
                      const image = item.product?.image || PLACEHOLDER_IMAGE;
                      return (
                        <li key={item.id} className="checkout-product-item">
                          <img
                            src={image}
                            alt=""
                            className="checkout-product-img"
                          />
                          <div className="checkout-product-info">
                            <span className="checkout-product-name">
                              {item.product?.name}
                            </span>
                            {item.variant_info && (
                              <span className="checkout-product-variant">
                                <span
                                  className="checkout-variant-color"
                                  style={{
                                    backgroundColor:
                                      item.variant_info.color.code,
                                  }}
                                />
                                {item.variant_info.color.name} /{" "}
                                {item.variant_info.size.name}
                              </span>
                            )}
                            <span className="checkout-product-qty">
                              × {item.quantity}
                            </span>
                          </div>
                          <span className="checkout-product-price">
                            {formatCurrency(unitPrice * item.quantity)}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                </div>

                <div className="checkout-actions">
                  <button
                    type="button"
                    className="checkout-btn back-btn"
                    onClick={() => retryOrder ? navigate("/orders") : setStep("shipping")}
                    disabled={submitting}
                  >
                    ← Quay lại
                  </button>
                  <button
                    type="button"
                    className="checkout-btn checkout-btn-primary"
                    onClick={handleSubmit}
                    disabled={submitting || walletInsufficient}
                  >
                    {submitting
                      ? "Đang xử lý..."
                      : paymentMethod === "cod"
                        ? `Đặt hàng — ${formatCurrency(pricing.total)}`
                        : paymentMethod === "wallet"
                          ? `Thanh toán bằng ví — ${formatCurrency(pricing.total)}`
                          : `Thanh toán — ${formatCurrency(pricing.total)}`}
                  </button>
                </div>
              </div>
            )}
          </div>

          <aside className="checkout-sidebar">
            <div className="checkout-summary-box">
              <h3 className="checkout-summary-title">Tóm tắt đơn hàng</h3>

              <div className="checkout-summary-picked">
                Bạn đang thanh toán <strong>{items.length}</strong> sản phẩm đã
                chọn từ {retryOrder ? "đơn hàng cũ" : "giỏ hàng"}.
              </div>

              {!retryOrder && (
              <div className="checkout-discount-box">
                <label
                  htmlFor="discount-code"
                  className="checkout-discount-label"
                >
                  Mã giảm giá
                </label>
                <div className="checkout-discount-row">
                  <input
                    id="discount-code"
                    type="text"
                    className="checkout-input checkout-discount-input"
                    placeholder="Nhập mã giảm giá..."
                    value={discountCode}
                    onChange={(event) => {
                      const nextValue = event.target.value.toUpperCase();
                      setDiscountCode(nextValue);
                      if (
                        pricingPreview &&
                        normalizeDiscountCode(nextValue) !== appliedDiscountCode
                      ) {
                        setPricingPreview(null);
                      }
                      setDiscountMessage("");
                    }}
                  />
                  <button
                    type="button"
                    className="checkout-btn checkout-btn-secondary checkout-discount-apply"
                    onClick={handleApplyDiscount}
                    disabled={discountLoading}
                  >
                    {discountLoading ? "Đang áp dụng..." : "Áp dụng"}
                  </button>
                </div>

                {hasAppliedDiscount && (
                  <div className="checkout-discount-meta">
                    <span className="checkout-discount-badge">
                      {appliedDiscountCode}
                      {pricingPreview?.discount_percent
                        ? ` - ${pricingPreview.discount_percent}%`
                        : ""}
                    </span>
                    <button
                      type="button"
                      className="checkout-discount-clear"
                      onClick={handleClearDiscount}
                    >
                      Bỏ mã
                    </button>
                  </div>
                )}

                {discountMessage && (
                  <p
                    className={`checkout-discount-message ${hasAppliedDiscount ? "is-success" : "is-error"}`}
                  >
                    {discountMessage}
                  </p>
                )}
              </div>
              )}

              <div className="checkout-summary-rows">
                <div className="checkout-summary-row">
                  <span>Tạm tính ({items.length} sản phẩm)</span>
                  <span>{formatCurrency(pricing.subtotal)}</span>
                </div>
                <div className="checkout-summary-row">
                  <span>Phí vận chuyển</span>
                  {pricing.shippingFee === 0 ? (
                    <span className="checkout-free-shipping-badge">
                      Miễn phí
                    </span>
                  ) : (
                    <span>{formatCurrency(pricing.shippingFee)}</span>
                  )}
                </div>
                {pricing.discountAmount > 0 && (
                  <div className="checkout-summary-row checkout-summary-row--discount">
                    <span>
                      Giảm giá
                      {appliedDiscountCode ? ` (${appliedDiscountCode})` : ""}
                    </span>
                    <span>-{formatCurrency(pricing.discountAmount)}</span>
                  </div>
                )}
                {pricing.shippingFee > 0 && (
                  <p className="checkout-free-shipping-hint">
                    Miễn phí vận chuyển cho đơn từ 500.000đ
                  </p>
                )}
                {pricing.shippingFee === 0 && (
                  <div className="checkout-ship-note">
                    <span className="checkout-ship-note-text">
                      Các sản phẩm đã chọn đủ điều kiện miễn phí vận chuyển từ
                      500.000đ trở lên.
                    </span>
                  </div>
                )}
                {selectedProvinceName && (
                  <div className="checkout-summary-row checkout-summary-row--delivery" style={{ marginTop: '12px', fontSize: '0.9rem' }}>
                    <span>Dự kiến nhận hàng</span>
                    <span style={{ fontWeight: 500, color: 'var(--success-color, #22c55e)' }}>
                      {getEstimatedDeliveryTime(selectedProvinceName)}
                    </span>
                  </div>
                )}
              </div>

              <div className="checkout-summary-total">
                <span>Tổng cộng</span>
                <span>{formatCurrency(pricing.total)}</span>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </section>
  );
}
