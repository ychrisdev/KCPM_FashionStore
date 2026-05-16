import { Link, Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { isStaffRole } from '../../utils/staff';
import "../../styles/admin/Admin.css";

function canEnterAdmin(user: {
  can_access_admin?: boolean;
  role?: string;
} | null): boolean {
  if (user?.can_access_admin === true) return true;
  if (user?.can_access_admin === false) return false;
  const role = user?.role ?? localStorage.getItem('user_role') ?? undefined;
  return isStaffRole(role);
}

export default function AdminRoute() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading" style={{ padding: '3rem', textAlign: 'center' }}>
        Đang tải...
      </div>
    );
  }

  const token = localStorage.getItem('access_token');
  if (!token) {
    return <Navigate to="/login?redirect=/admin" replace />;
  }

  if (!canEnterAdmin(user)) {
    return (
      <section className="admin-access-shell">
        <div className="admin-access-denied admin-access-denied--compact">
          <div className="admin-access-hero admin-access-hero--compact">
            <div className="admin-access-badge">403</div>
            <div className="admin-access-copy">
              <span className="admin-access-kicker">Truy cập bị từ chối</span>
              <h1>Bạn không có quyền vào trang quản trị</h1>
              <p>
                Tài khoản <strong>{user?.username ?? 'hiện tại'}</strong> không được cấp quyền truy cập khu vực
                quản trị.
              </p>
            </div>
          </div>

          <div className="admin-access-actions admin-access-actions--single">
            <Link to="/" className="admin-access-action admin-access-action--primary">
              Quay về trang chủ
            </Link>
          </div>
        </div>
      </section>
    );
  }

  return <Outlet />;
}
