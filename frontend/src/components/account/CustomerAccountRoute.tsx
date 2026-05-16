import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

/**
 * Chỉ khách (không vào được admin). Bảo vệ toàn bộ /dashboard/*.
 */
export default function CustomerAccountRoute() {
  const { user, loading } = useAuth();
  const token = localStorage.getItem("access_token");

  if (loading) {
    return (
      <div className="loading" style={{ padding: "3rem", textAlign: "center" }}>
        Đang tải…
      </div>
    );
  }

  if (!token || !user) {
    return <Navigate to="/login?redirect=/dashboard" replace />;
  }

  if (user.can_access_admin) {
    return <Navigate to="/admin" replace />;
  }

  const role = user.role ?? localStorage.getItem("user_role") ?? "";
  if (role === "staff" || role === "admin") {
    return <Navigate to="/admin" replace />;
  }

  return <Outlet />;
}
