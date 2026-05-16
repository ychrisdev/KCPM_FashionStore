import { useEffect, useMemo, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import axios from "axios";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { customerDashboard, type CustomerDashboardData } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import "../../styles/admin/Admin.css";

const DASH = "/dashboard";

const STATUS_VI: Record<string, string> = {
  pending: "Chờ xử lý",
  shipping: "Đang giao",
  returning: "Hoàn trả",
  awaiting_confirmation: "Chờ xác nhận",
  refunded :"Đã hoàn trả",
  completed: "Hoàn thành",
  cancelled: "Đã hủy",
};

const PIE_COLORS = ["#6366f1", "#f59e0b", "#14b8a6", "#10b981", "#ef4444"];

function formatVnd(value: string | number) {
  const n = typeof value === "number" ? value : parseFloat(String(value));
  if (Number.isNaN(n)) return String(value);
  return `${new Intl.NumberFormat("vi-VN").format(n)} đ`;
}

function formatDate(iso: string) {
  try {
    const d = new Date(iso);
    return d.toLocaleString("vi-VN", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function errMessage(e: unknown): string {
  if (!axios.isAxiosError(e) || !e.response) {
    return "Không tải được dữ liệu. Thử lại sau.";
  }
  const d = e.response.data as { detail?: unknown };
  const detail = d?.detail;
  if (typeof detail === "string") return detail;
  return "Không tải được dữ liệu.";
}

function DashboardInner({ data }: { data: CustomerDashboardData }) {
  const pieStatusData = useMemo(() => {
    return Object.entries(data.orders_by_status)
      .map(([key, value]) => ({
        name: STATUS_VI[key] ?? key,
        value,
        key,
      }))
      .filter((d) => d.value > 0);
  }, [data.orders_by_status]);

  const pendingN = data.orders_by_status.pending ?? 0;
  const shippingN = data.orders_by_status.shipping ?? 0;

  const barDaily = useMemo(
    () => data.orders_daily_7d?.map((row) => ({ ...row })) ?? [],
    [data.orders_daily_7d],
  );

  return (
    <div className="dashboard dashboard--enhanced">
      <header className="dashboard-pageHead">
        <span className="dashboard-rolePill customer-dash-pill">Khách hàng</span>
        <h2 className="dashboard-pageTitle">Tổng quan tài khoản</h2>
        <p className="dashboard-muted dashboard-pageSub">
          Đơn hàng, giỏ và yêu thích của bạn — dùng menu bên trái để mở Đơn hàng, Hồ sơ, Trả hàng.
        </p>
      </header>

      <section className="dashboard-kpi" aria-label="Chỉ số của bạn">
        <div className="stats-grid stats-grid--kpi">
          <Link to={`${DASH}/orders`} className="stat-card stat-card--warn">
            <div className="stat-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
            </div>
            <div className="stat-info">
              <h3>{pendingN}</h3>
              <p>Đơn chờ xử lý</p>
            </div>
          </Link>
          <Link to={`${DASH}/orders`} className="stat-card">
            <div className="stat-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </div>
            <div className="stat-info">
              <h3>{shippingN}</h3>
              <p>Đang giao</p>
            </div>
          </Link>
          <Link to={`${DASH}/orders`} className="stat-card">
            <div className="stat-info">
              <h3>{data.orders_total}</h3>
              <p>Tổng đơn đã đặt</p>
            </div>
          </Link>
          <Link to="/cart" className="stat-card stat-card--accent">
            <div className="stat-info">
              <h3>{data.cart_item_count}</h3>
              <p>Sản phẩm trong giỏ (SL)</p>
            </div>
          </Link>
          <Link to="/wishlist" className="stat-card">
            <div className="stat-info">
              <h3>{data.wishlist_count}</h3>
              <p>Yêu thích</p>
            </div>
          </Link>
          <Link to={`${DASH}/returns`} className="stat-card">
            <div className="stat-info">
              <h3>{data.pending_returns}</h3>
              <p>Trả hàng chờ duyệt</p>
            </div>
          </Link>
        </div>

        <div className="dashboard-catalogStrip">
          <span>
            Cần hỗ trợ? <Link to={`${DASH}/orders`} className="dashboard-catalogStrip-link" style={{ display: "inline" }}>Đơn hàng</Link>
            {" · "}
            <Link to="/contact" className="dashboard-catalogStrip-link" style={{ display: "inline" }}>
              Liên hệ
            </Link>
          </span>
        </div>
      </section>

      <section className="dashboard-charts" aria-label="Biểu đồ">
        <div className="chart-card">
          <div className="chart-card-head">
            <h3>Đơn theo trạng thái</h3>
            <span className="chart-card-sub">Của bạn</span>
          </div>
          <div className="chart-card-body chart-card-body--pie">
            {pieStatusData.length === 0 ? (
              <p className="dashboard-muted" style={{ padding: "1.5rem", margin: 0 }}>
                Chưa có đơn nào.
              </p>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={pieStatusData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={52}
                    outerRadius={88}
                    paddingAngle={2}
                    label={({ name, percent }) =>
                      `${name} ${(((percent ?? 0) * 100).toFixed(0))}%`
                    }
                  >
                    {pieStatusData.map((entry, i) => (
                      <Cell key={entry.key} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="chart-card chart-card--wide">
          <div className="chart-card-head">
            <h3>Số đơn 7 ngày gần đây</h3>
            <span className="chart-card-sub">Theo ngày đặt</span>
          </div>
          <div className="chart-card-body">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={barDaily} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} stroke="#9ca3af" />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} stroke="#9ca3af" />
                <Tooltip
                  formatter={(v) => [`${Number(v ?? 0)} đơn`, "Số đơn"]}
                  labelFormatter={(l) => `Ngày ${l}`}
                  contentStyle={{ borderRadius: 8, border: "1px solid #e5e7eb" }}
                />
                <Bar dataKey="orders" name="Đơn" fill="#8b5cf6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <div className="dashboard-row">
        <div className="dashboard-panel">
          <h3 className="dashboard-panel-title">Đơn gần đây</h3>
          {data.recent_orders.length === 0 ? (
            <p className="dashboard-muted" style={{ padding: "0 0 0.5rem", margin: 0 }}>
              Bạn chưa có đơn hàng.{" "}
              <Link to="/products" className="dashboard-catalogStrip-link">
                Mua sắm ngay
              </Link>
            </p>
          ) : (
            <ul className="dashboard-topProducts" style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {data.recent_orders.map((o, i) => (
                <li
                  key={o.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.75rem",
                    padding: "0.65rem 0",
                    borderBottom: i < data.recent_orders.length - 1 ? "1px solid #f2f0ed" : "none",
                  }}
                >
                  <span className="dashboard-topProducts-rank">{i + 1}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <Link
                      to={`${DASH}/orders`}
                      style={{ fontWeight: 700, color: "#2a2825", textDecoration: "none" }}
                    >
                      #{o.id}
                    </Link>
                    <span style={{ marginLeft: "0.5rem", fontSize: "0.72rem", color: "#8a8680" }}>
                      {STATUS_VI[o.status] ?? o.status}
                    </span>
                    <div style={{ fontSize: "0.78rem", color: "#a8a39c", marginTop: "0.15rem" }}>
                      {formatDate(o.created_at)} · {o.item_count} mặt hàng
                    </div>
                  </div>
                  <span className="dashboard-topProducts-rev">{formatVnd(o.total_price)}</span>
                </li>
              ))}
            </ul>
          )}
          <div style={{ marginTop: "0.75rem" }}>
            <Link to={`${DASH}/orders`} className="dashboard-catalogStrip-link">
              Xem tất cả đơn →
            </Link>
          </div>
        </div>

        <div className="dashboard-panel">
          <h3 className="dashboard-panel-title">Tiện ích</h3>
          <ul className="dashboard-alertList">
            <li>
              <Link to={`${DASH}/profile`}>Hồ sơ &amp; địa chỉ giao hàng</Link>
            </li>
            <li>
              <Link to="/checkout">Thanh toán từ giỏ hàng</Link>
            </li>
            <li>
              <Link to="/my-feedback">Đánh giá sản phẩm đã mua</Link>
            </li>
            <li>
              <Link to="/contact">Liên hệ cửa hàng</Link>
            </li>
            {data.active_returns > 0 && (
              <li>
                <Link to={`${DASH}/returns`}>
                  Bạn có <strong>{data.active_returns}</strong> yêu cầu trả đang xử lý
                </Link>
              </li>
            )}
          </ul>
          <div className="dashboard-quickLinks" style={{ marginTop: "0.75rem" }}>
            <Link to="/cart" className="dashboard-quickLink">
              Giỏ hàng
            </Link>
            <Link to="/wishlist" className="dashboard-quickLink">
              Yêu thích
            </Link>
            <Link to={`${DASH}/returns`} className="dashboard-quickLink">
              Trả hàng
            </Link>
          </div>
        </div>
      </div>

      <div className="recent-orders dashboard-hint">
        <h3>Mẹo</h3>
        <p className="dashboard-muted">
          Menu <strong>Tổng quan · Đơn hàng · Hồ sơ · Trả hàng</strong> bên trái giúp bạn điều hướng trong khu vực tài
          khoản.
        </p>
      </div>
    </div>
  );
}

/** Trang chủ /dashboard — tổng quan (API customer dashboard). */
export default function AccountDashboardHome() {
  const { user, loading: authLoading } = useAuth();
  const [data, setData] = useState<CustomerDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      setLoading(false);
      setData(null);
      return;
    }
    setLoading(true);
    setErr(null);
    let cancelled = false;
    customerDashboard
      .get()
      .then((res) => {
        if (!cancelled) setData(res.data);
      })
      .catch((e) => {
        if (!cancelled) {
          setErr(errMessage(e));
          setData(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [authLoading, user]);

  if (authLoading) {
    return (
      <div className="loading" style={{ padding: "2rem", textAlign: "center" }}>
        Đang tải bảng điều khiển…
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login?redirect=/dashboard" replace />;
  }

  if (loading) {
    return (
      <div className="loading" style={{ padding: "2rem", textAlign: "center" }}>
        Đang tải bảng điều khiển…
      </div>
    );
  }

  return (
    <>
      {err && (
        <div className="admin-banner admin-banner--err" role="alert" style={{ marginBottom: "1rem" }}>
          {err}
        </div>
      )}
      {data && <DashboardInner data={data} />}
    </>
  );
}
