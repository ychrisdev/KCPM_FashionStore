/** Tiêu đề header theo đường dẫn /dashboard/... */
export function customerAccountPageTitle(pathname: string): string {
  const p = pathname.replace(/\/$/, "") || "/dashboard";
  if (p === "/dashboard") return "Tổng quan";
  if (p.endsWith("/orders")) return "Đơn hàng";
  if (p.endsWith("/profile")) return "Hồ sơ";
  if (p.endsWith("/returns")) return "Trả hàng";
  if (p.endsWith("/wallet")) return "Ví tiền của tôi";
  return "Tài khoản";
}
