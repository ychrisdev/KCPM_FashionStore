import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import {
  Area,
  AreaChart,
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
} from 'recharts';
import {
  admin,
  type AdminDashboardStats,
  type DashboardStats,
  type StaffDashboardStats,
} from '../../api/client';
import AdminLayout from '../../components/admin/AdminLayout';

const STATUS_VI: Record<string, string> = {
  pending: 'Chờ xử lý',
  shipping: 'Đang giao',
  awaiting_confirmation: "Chờ xác nhận",
  refunded: "Đã hoàn tiền",
  returning: 'Hoàn trả',
  completed: 'Hoàn thành',
  cancelled: 'Đã hủy',
};

const ROLE_VI: Record<string, string> = {
  customer: 'Khách hàng',
  staff: 'Nhân viên',
  admin: 'Quản trị viên',
};

const PIE_COLORS = ['#6366f1', '#f59e0b', '#14b8a6', '#10b981', '#ef4444'];

function statsErrorMessage(err: unknown): string {
  if (!axios.isAxiosError(err) || !err.response) {
    return 'Không tải được thống kê. Kiểm tra backend đang chạy và đăng nhập lại.';
  }
  const { status, data } = err.response;
  const detail =
    data && typeof data === 'object' && 'detail' in data
      ? (data as { detail?: unknown }).detail
      : undefined;
  const text = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.join(' ') : '';
  if (status === 401) return 'Phiên đăng nhập hết hạn. Vui lòng đăng nhập lại.';
  if (status === 403) return text || 'Bạn không có quyền xem thống kê (cần vai trò nhân viên hoặc tài khoản staff).';
  if (status >= 500) return 'Lỗi máy chủ khi tải thống kê. Xem log backend.';
  return text || 'Không tải được thống kê.';
}

function formatVnd(value: string | number) {
  const n = typeof value === 'number' ? value : parseFloat(String(value));
  if (Number.isNaN(n)) return String(value);
  return `${new Intl.NumberFormat('vi-VN').format(n)} đ`;
}

function shortVnd(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}tr`;
  if (n >= 1000) return `${(n / 1000).toFixed(0)}k`;
  return `${n}`;
}

function StaffDashboardBody({ stats }: { stats: StaffDashboardStats }) {
  const pieStatusData = useMemo(() => {
    return Object.entries(stats.orders_by_status)
      .map(([key, value]) => ({
        name: STATUS_VI[key] ?? key,
        value,
        key,
      }))
      .filter((d) => d.value > 0);
  }, [stats.orders_by_status]);

  return (
    <>
      <header className="dashboard-pageHead">
        <span className="dashboard-rolePill dashboard-rolePill--staff">Nhân viên</span>
        <h2 className="dashboard-pageTitle">Dashboard vận hành</h2>
        <p className="dashboard-muted dashboard-pageSub">
          Ưu tiên đơn hàng, kho, liên hệ và trả hàng — không hiển thị báo cáo doanh thu chi tiết.
        </p>
      </header>

      <section className="dashboard-kpi" aria-label="Chỉ số vận hành">
        <div className="stats-grid stats-grid--kpi">
          <div className="stat-card stat-card--warn">
            <div className="stat-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
            </div>
            <div className="stat-info">
              <h3>{stats.pending_orders}</h3>
              <p>Đơn chờ xử lý</p>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-info">
              <h3>{stats.shipping_orders}</h3>
              <p>Đang giao</p>
            </div>
          </div>
          <div className="stat-card stat-card--accent">
            <div className="stat-info">
              <h3>{stats.pending_returns}</h3>
              <p>Yêu cầu trả hàng chờ duyệt</p>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-info">
              <h3>{stats.orders_today}</h3>
              <p>Đơn hôm nay</p>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-info">
              <h3>{stats.unhandled_contacts}</h3>
              <p>Liên hệ chưa xử lý</p>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-info">
              <h3>{stats.unhandled_feedbacks}</h3>
              <p>Góp ý chưa xử lý</p>
            </div>
          </div>
        </div>
        <div className="dashboard-catalogStrip">
          <span>
            <strong>{stats.catalog?.products ?? 0}</strong> sản phẩm
          </span>
          <span className="dashboard-catalogStrip-sep">·</span>
          <span>
            <strong>{stats.catalog?.variants ?? 0}</strong> biến thể
          </span>
          <span className="dashboard-catalogStrip-sep">·</span>
          <span>
            <strong>{stats.low_stock_products}</strong> SP có biến thể tồn thấp (≤ {stats.low_stock_threshold})
          </span>
          <Link to="/admin/products" className="dashboard-catalogStrip-link">
            Quản lý SP →
          </Link>
        </div>
      </section>

      <section className="dashboard-charts dashboard-charts--staff" aria-label="Trạng thái đơn">
        <div className="chart-card">
          <div className="chart-card-head">
            <h3>Đơn theo trạng thái</h3>
            <span className="chart-card-sub">Tổng quan</span>
          </div>
          <div className="chart-card-body chart-card-body--pie">
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
                  label={({ name, percent }) => `${name} ${(((percent ?? 0) * 100).toFixed(0))}%`}
                >
                  {pieStatusData.map((entry, i) => (
                    <Cell key={entry.key} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <div className="dashboard-row">
        <div className="dashboard-panel">
          <h3 className="dashboard-panel-title">Cần xử lý</h3>
          <ul className="dashboard-alertList">
            <li>
              <Link to="/admin/orders?status=pending">
                Đơn <strong>chờ xử lý</strong>: {stats.pending_orders}
              </Link>
            </li>
            {stats.stale_pending_order_ids.length > 0 && (
              <li className="dashboard-alertList--warn">
                <span>
                  Đơn pending &gt; 2 ngày: {stats.stale_pending_order_ids.length} — ID:{' '}
                  {stats.stale_pending_order_ids.slice(0, 8).join(', ')}
                  {stats.stale_pending_order_ids.length > 8 ? '…' : ''}
                </span>
              </li>
            )}
            <li>
              <Link to="/admin/returns">
                Trả hàng chờ duyệt: <strong>{stats.pending_returns}</strong>
              </Link>
            </li>
            <li>
              <Link to="/admin/contacts">
                Liên hệ chưa xử lý: <strong>{stats.unhandled_contacts}</strong>
              </Link>
            </li>
            <li>
              <Link to="/admin/feedbacks">
                Góp ý chưa xử lý: <strong>{stats.unhandled_feedbacks}</strong>
              </Link>
            </li>
          </ul>
        </div>

        <div className="dashboard-panel">
          <h3 className="dashboard-panel-title">Tồn kho</h3>
          <p className="dashboard-muted">
            Biến thể tồn ≤ {stats.low_stock_threshold}: <strong>{stats.low_stock_variants}</strong> — Sản phẩm có
            biến thể thấp: <strong>{stats.low_stock_products}</strong>
          </p>
          <div className="dashboard-quickLinks">
            <Link to="/admin/products" className="dashboard-quickLink">
              Sản phẩm
            </Link>
            <Link to="/admin/orders" className="dashboard-quickLink">
              Đơn hàng
            </Link>
            <Link to="/admin/policies" className="dashboard-quickLink">
              Chính sách
            </Link>
          </div>
        </div>
      </div>

      <div className="recent-orders dashboard-hint">
        <h3>Gợi ý</h3>
        <p className="dashboard-muted">
          Bạn đang dùng chế độ <strong>nhân viên</strong>. Để xem doanh thu, biểu đồ 14 ngày và thống kê tài khoản, cần
          quyền <strong>quản trị viên</strong>.
        </p>
      </div>
    </>
  );
}

function AdminDashboardBody({ stats }: { stats: AdminDashboardStats }) {
  const chartRevenueData = useMemo(() => {
    return stats.revenue_series.map((row) => ({
      ...row,
      revenueNum: parseFloat(row.revenue) || 0,
    }));
  }, [stats.revenue_series]);

  const pieStatusData = useMemo(() => {
    return Object.entries(stats.orders_by_status)
      .map(([key, value]) => ({
        name: STATUS_VI[key] ?? key,
        value,
        key,
      }))
      .filter((d) => d.value > 0);
  }, [stats.orders_by_status]);

  return (
    <>
      <header className="dashboard-pageHead">
        <span className="dashboard-rolePill dashboard-rolePill--admin">Quản trị</span>
        <h2 className="dashboard-pageTitle">Dashboard tổng quan</h2>
        <p className="dashboard-muted dashboard-pageSub">
          Doanh thu, đơn hàng, kho, người dùng và biểu đồ — đầy đủ số liệu kinh doanh.
        </p>
      </header>

      <section className="dashboard-kpi" aria-label="Chỉ số nhanh">
        <div className="stats-grid stats-grid--kpi">
          <div className="stat-card stat-card--accent">
            
            <div className="stat-info">
              <h3>{formatVnd(stats.revenue_today)}</h3>
              <p>Doanh thu hôm nay</p>
            </div>
          </div>
         <div className="stat-card stat-card--week">
          <div className="stat-info">
             <h3>{formatVnd(stats.revenue_week)}</h3>
             <p>Doanh thu 7 ngày</p>
           </div>
         </div>
          <div className="stat-card">
            <div className="stat-info">
              <h3>{formatVnd(stats.revenue_month)}</h3>
              <p>Doanh thu tháng này</p>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-info">
              <h3>{stats.orders_today}</h3>
              <p>Đơn hôm nay</p>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-info">
              <h3>{stats.orders_total}</h3>
              <p>Tổng đơn hàng</p>
            </div>
          </div>
          <div className="stat-card stat-card--warn">
            <div className="stat-info">
              <h3>{stats.pending_orders}</h3>
              <p>Đơn chờ xử lý</p>
            </div>
          </div>
        </div>
        <div className="stats-row">   
          <div className="stat-card">
              <div>
              <div className="stat-value">{stats.users_total}</div>
                <div className="stat-label">Tài khoản hoạt động</div>
              </div>
            </div>

            <div className="stat-card">
              <div>
                <div className="stat-value">{stats.users_by_role?.customer ?? 0}</div>
                <div className="stat-label">Khách hàng (profile)</div>
              </div>
            </div>

            <div className="stat-card">
              <div>
                <div className="stat-value">{stats.customers_inactive ?? 0}</div>
                <div className="stat-label">Khách chưa kích hoạt</div>
              </div>
            </div>

            <div className="stat-card">
              <div>
                <div className="stat-value">{stats.catalog?.products ?? 0}</div>
                <div className="stat-label">Sản phẩm</div>
              </div>
            </div>

            <div className="stat-card">
              <div>
                <div className="stat-value">{stats.catalog?.variants ?? 0}</div>
                <div className="stat-label">Biến thể</div>
              </div>
            </div>
        </div>  
      </section>

      <section className="dashboard-charts" aria-label="Biểu đồ">
        <div className="chart-card chart-card--wide">
          <div className="chart-card-head">
            <h3>Doanh thu 14 ngày</h3>
            <span className="chart-card-sub">Không tính đơn đã hủy</span>
          </div>
          <div className="chart-card-body">
            <ResponsiveContainer width="100%" height={320}>
              <AreaChart data={chartRevenueData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} stroke="#9ca3af" />
                <YAxis tickFormatter={(v) => shortVnd(Number(v))} tick={{ fontSize: 11 }} stroke="#9ca3af" />
                <Tooltip
                  formatter={(value) => [formatVnd(Number(value ?? 0)), 'Doanh thu']}
                  labelFormatter={(l) => `Ngày ${l}`}
                  contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb' }}
                />
                <Area
                  type="monotone"
                  dataKey="revenueNum"
                  name="Doanh thu"
                  stroke="#6366f1"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorRev)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="chart-card">
          <div className="chart-card-head">
            <h3>Đơn theo trạng thái</h3>
            <span className="chart-card-sub">Tất cả thời gian</span>
          </div>
          <div className="chart-card-body chart-card-body--pie">
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
                  label={({ name, percent }) => `${name} ${(((percent ?? 0) * 100).toFixed(0))}%`}
                >
                  {pieStatusData.map((entry, i) => (
                    <Cell key={entry.key} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="chart-card">
          <div className="chart-card-head">
            <h3>Top sản phẩm theo doanh thu</h3>
            <span className="chart-card-sub">Từ đơn không hủy</span>
          </div>
          <div className="chart-card-body chart-card-body--table">
            {stats.top_products && stats.top_products.length > 0 ? (
              <ul className="dashboard-topProducts">
                {stats.top_products.map((p, i) => (
                  <li key={`${p.id}-${i}`}>
                    <span className="dashboard-topProducts-rank">{i + 1}</span>
                    <span className="dashboard-topProducts-name" title={p.name}>
                      {p.name}
                    </span>
                    <span className="dashboard-topProducts-rev">{formatVnd(p.revenue)}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="dashboard-muted" style={{ margin: 0 }}>
                Chưa có dữ liệu bán hàng.
              </p>
            )}
          </div>
        </div>

        <div className="chart-card chart-card--wide">
          <div className="chart-card-head">
            <h3>Số đơn theo ngày (14 ngày)</h3>
          </div>
          <div className="chart-card-body">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={chartRevenueData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} stroke="#9ca3af" />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} stroke="#9ca3af" />
                <Tooltip
                  formatter={(v) => [`${Number(v ?? 0)} đơn`, 'Số đơn']}
                  labelFormatter={(l) => `Ngày ${l}`}
                  contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb' }}
                />
                <Bar dataKey="orders" name="Đơn hàng" fill="#8b5cf6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <div className="dashboard-row">
        <div className="dashboard-panel">
          <h3 className="dashboard-panel-title">Cần xử lý</h3>
          <ul className="dashboard-alertList">
            <li>
              <Link to="/admin/orders?status=pending">
                Đơn pending: <strong>{stats.pending_orders}</strong>
              </Link>
            </li>
            {stats.stale_pending_order_ids.length > 0 && (
              <li className="dashboard-alertList--warn">
                <span>
                  Đơn pending &gt; 2 ngày: {stats.stale_pending_order_ids.length} — ID:{' '}
                  {stats.stale_pending_order_ids.slice(0, 8).join(', ')}
                  {stats.stale_pending_order_ids.length > 8 ? '…' : ''}
                </span>
              </li>
            )}
            <li>
              <Link to="/admin/returns">
                Trả hàng chờ duyệt: <strong>{stats.pending_returns}</strong>
              </Link>
            </li>
            <li>
              <Link to="/admin/contacts">
                Liên hệ chưa xử lý: <strong>{stats.unhandled_contacts}</strong>
              </Link>
            </li>
            <li>
              <Link to="/admin/feedbacks">
                Góp ý chưa xử lý: <strong>{stats.unhandled_feedbacks}</strong>
              </Link>
            </li>
          </ul>
        </div>

        <div className="dashboard-panel">
          <h3 className="dashboard-panel-title">Tồn kho &amp; liên kết</h3>
          <p className="dashboard-muted">
            Biến thể tồn ≤ {stats.low_stock_threshold}: <strong>{stats.low_stock_variants}</strong> — Sản phẩm có biến
            thể thấp: <strong>{stats.low_stock_products}</strong>
          </p>
          <div className="dashboard-quickLinks">
            <Link to="/admin/products" className="dashboard-quickLink">
              Sản phẩm
            </Link>
            <Link to="/admin/orders" className="dashboard-quickLink">
              Đơn hàng
            </Link>
            <Link to="/admin/policies" className="dashboard-quickLink">
              Chính sách
            </Link>
          </div>
        </div>
      </div>

      <div className="recent-orders dashboard-hint">
        <h3>Hướng dẫn nhanh</h3>
        <p className="dashboard-muted">
          Sidebar: sản phẩm, đơn, người dùng, đánh giá. Dashboard này dành cho <strong>quản trị viên</strong> — đầy đủ
          doanh thu và phân bổ tài khoản.
        </p>
      </div>
    </>
  );
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  console.log(stats);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    admin.dashboard
      .stats()
      .then((res) => setStats(res.data))
      .catch((e) => {
        console.error(e);
        setErr(statsErrorMessage(e));
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <AdminLayout>
        <div className="loading">Đang tải dashboard…</div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="dashboard dashboard--enhanced">
        {err && (
          <div className="admin-banner admin-banner--err" role="alert">
            {err}
          </div>
        )}

        {stats && stats.role_scope === 'staff' && <StaffDashboardBody stats={stats} />}

        {stats && stats.role_scope === 'admin' && <AdminDashboardBody stats={stats} />}
      </div>
    </AdminLayout>
  );
}
