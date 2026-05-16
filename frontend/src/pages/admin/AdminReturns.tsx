import { useEffect, useState } from "react";
import { admin } from "../../api/client";
import AdminLayout from "../../components/admin/AdminLayout";
import "../../styles/admin/Admin.css";

interface ReturnOrderItem {
  id: number;
  product?: { name: string; image?: string };
  variant_info?: {
    color: { name: string; code: string };
    size: { name: string };
  } | null;
  quantity: number;
  price: string;
}

interface ReturnRequest {
  id: number;
  order: number;
  user: number;
  username: string;
  reason: string;
  description: string;
  status: string;
  admin_note: string;
  order_total: string;
  order_items: ReturnOrderItem[];
  created_at: string;
  updated_at: string;
}

const REASON_LABEL: Record<string, string> = {
  wrong_item: "Sản phẩm sai",
  damaged: "Sản phẩm hỏng/lỗi",
  not_as_described: "Không đúng mô tả",
  changed_mind: "Thay đổi quyết định",
  other: "Lý do khác",
};

const STATUS_LABEL: Record<string, string> = {
  pending: "Chờ duyệt",
  approved: "Đã duyệt",
  rejected: "Từ chối",
  completed: "Hoàn thành",
};

const STATUS_BADGE: Record<string, string> = {
  pending: "status-pending",
  approved: "status-shipping",
  rejected: "status-cancelled",
  completed: "status-completed",
};

export default function AdminReturns() {
  const [rows, setRows] = useState<ReturnRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");
  const [detail, setDetail] = useState<ReturnRequest | null>(null);
  const [adminNote, setAdminNote] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState("");

  const load = (statusFilter: string) => {
    const params: Record<string, string> = {};
    if (statusFilter) params.status = statusFilter;
    admin.returns
      .list(Object.keys(params).length ? params : undefined)
      .then((res) => {
        const data = res?.data;
        const list = Array.isArray(data)
          ? data
          : Array.isArray(data?.results)
            ? data.results
            : [];
        setRows(list as ReturnRequest[]);
      })
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load(filter);
  }, [filter]);

  const openDetail = (r: ReturnRequest) => {
    setDetail(r);
    setAdminNote(r.admin_note ?? "");
    setActionError("");
  };

  const doAction = async (action: 'approve' | 'reject' | 'complete') => {
    if (!detail) return;
    setActionLoading(true);
    setActionError("");
    try {
      const fn = admin.returns[action];
      const res = await fn(detail.id, adminNote);
      const updated = res.data as ReturnRequest;
      setRows((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      setDetail(updated);
      setAdminNote(updated.admin_note ?? "");
    } catch (err) {
      const msg = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      setActionError(msg ?? "Thao tác thất bại.");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <AdminLayout>
        <div className="loading">Đang tải...</div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="admin-page">
        <div className="page-header">
          <h3>Yêu cầu trả hàng & hoàn tiền</h3>
        </div>

        <div className="admin-filters">
          <label>
            Trạng thái{" "}
            <select value={filter} onChange={(e) => setFilter(e.target.value)}>
              <option value="">Tất cả</option>
              {Object.entries(STATUS_LABEL).map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </label>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Khách hàng</th>
              <th>Đơn hàng</th>
              <th>Lý do</th>
              <th>Trạng thái</th>
              <th>Ngày gửi</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td
                  colSpan={7}
                  style={{
                    textAlign: "center",
                    padding: "1.5rem",
                    color: "#888",
                  }}
                >
                  Không có yêu cầu nào.
                </td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr key={r.id}>
                  <td>#{r.id}</td>
                  <td>{r.username}</td>
                  <td>Đơn #{r.order}</td>
                  <td>{REASON_LABEL[r.reason] ?? r.reason}</td>
                  <td>
                    <span
                      className={`status-badge ${STATUS_BADGE[r.status] ?? ""}`}
                    >
                      {STATUS_LABEL[r.status] ?? r.status}
                    </span>
                  </td>
                  <td>{new Date(r.created_at).toLocaleDateString("vi-VN")}</td>
                  <td>
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      onClick={() => openDetail(r)}
                    >
                      Chi tiết
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {detail && (
          <div className="modal-overlay" role="dialog" aria-modal="true">
            <div className="modal modal--wide">
              <h3>Yêu cầu trả hàng #{detail.id}</h3>
              <p>
                <strong>Khách hàng:</strong> {detail.username}
              </p>
              <p>
                <strong>Đơn hàng:</strong> #{detail.order} — Tổng:{" "}
                {Number(detail.order_total).toLocaleString("vi-VN")}đ
              </p>
              <p>
                <strong>Lý do:</strong>{" "}
                {REASON_LABEL[detail.reason] ?? detail.reason}
              </p>
              {detail.description && (
                <p>
                  <strong>Mô tả:</strong> {detail.description}
                </p>
              )}

              {detail.order_items && detail.order_items.length > 0 && (
                <div className="admin-return-items">
                  <p>
                    <strong>Sản phẩm trong đơn:</strong>
                  </p>
                  <table className="data-table admin-return-items-table">
                    <thead>
                      <tr>
                        <th>Sản phẩm</th>
                        <th>Phân loại</th>
                        <th>SL</th>
                        <th>Đơn giá</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detail.order_items.map((item) => (
                        <tr key={item.id}>
                          <td>{item.product?.name ?? "Sản phẩm"}</td>
                          <td>
                            {item.variant_info ? (
                              <span
                                style={{
                                  display: "flex",
                                  alignItems: "center",
                                  gap: 6,
                                }}
                              >
                                <span
                                  style={{
                                    width: 10,
                                    height: 10,
                                    borderRadius: "50%",
                                    backgroundColor:
                                      item.variant_info.color.code,
                                    border: "1px solid rgba(0,0,0,0.1)",
                                    display: "inline-block",
                                    flexShrink: 0,
                                  }}
                                />
                                {item.variant_info.color.name} /{" "}
                                {item.variant_info.size.name}
                              </span>
                            ) : (
                              "—"
                            )}
                          </td>
                          <td>{item.quantity}</td>
                          <td>{Number(item.price).toLocaleString("vi-VN")}đ</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <p>
                <strong>Trạng thái:</strong>{" "}
                <span
                  className={`status-badge ${STATUS_BADGE[detail.status] ?? ""}`}
                >
                  {STATUS_LABEL[detail.status] ?? detail.status}
                </span>
              </p>
              <p>
                <strong>Ngày gửi:</strong>{" "}
                {new Date(detail.created_at).toLocaleString("vi-VN")}
              </p>

              {detail.status === "pending" && (
                <div style={{ marginTop: "16px" }}>
                  <label
                    style={{
                      display: "block",
                      fontWeight: 600,
                      marginBottom: "6px",
                    }}
                  >
                    Ghi chú phản hồi (tuỳ chọn)
                  </label>
                  <textarea
                    className="admin-textarea"
                    rows={3}
                    value={adminNote}
                    onChange={(e) => setAdminNote(e.target.value)}
                    placeholder="Ghi chú gửi đến khách hàng..."
                    style={{ width: "100%", marginBottom: "12px" }}
                  />
                  {actionError && (
                    <p
                      style={{
                        color: "#b91c1c",
                        fontSize: "0.88rem",
                        marginBottom: "10px",
                      }}
                    >
                      {actionError}
                    </p>
                  )}
                  <div
                    style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}
                  >
                    <button
                      type="button"
                      className="btn-primary"
                      disabled={actionLoading}
                      onClick={() => doAction("approve")}
                    >
                      Duyệt yêu cầu
                    </button>
                    <button
                      type="button"
                      className="btn-delete"
                      disabled={actionLoading}
                      onClick={() => doAction("reject")}
                    >
                      Từ chối
                    </button>
                  </div>
                </div>
              )}

              {detail.status === "approved" && (
                <div style={{ marginTop: "16px" }}>
                  <label
                    style={{
                      display: "block",
                      fontWeight: 600,
                      marginBottom: "6px",
                    }}
                  >
                    Ghi chú hoàn tiền (tuỳ chọn)
                  </label>
                  <textarea
                    className="admin-textarea"
                    rows={2}
                    value={adminNote}
                    onChange={(e) => setAdminNote(e.target.value)}
                    placeholder="Ví dụ: Đã hoàn tiền qua tài khoản..."
                    style={{ width: "100%", marginBottom: "12px" }}
                  />
                  {actionError && (
                    <p
                      style={{
                        color: "#b91c1c",
                        fontSize: "0.88rem",
                        marginBottom: "10px",
                      }}
                    >
                      {actionError}
                    </p>
                  )}
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={actionLoading}
                    onClick={() => doAction("complete")}
                  >
                    Xác nhận hoàn tiền
                  </button>
                </div>
              )}

              {detail.admin_note && detail.status !== "pending" && (
                <div
                  style={{
                    marginTop: "14px",
                    padding: "10px 14px",
                    background: "#eff6ff",
                    borderLeft: "3px solid #3b82f6",
                    borderRadius: "0 6px 6px 0",
                    fontSize: "0.9rem",
                  }}
                >
                  <strong>Ghi chú của admin:</strong> {detail.admin_note}
                </div>
              )}

              <div style={{ marginTop: "20px" }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setDetail(null)}
                >
                  Đóng
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
