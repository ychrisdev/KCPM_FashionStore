import { useEffect, useState } from "react";
import { admin, sizes as sizesApi } from "../../api/client";
import AdminLayout from "../../components/admin/AdminLayout";
import "../../styles/admin/Admin.css";

interface Size {
  id: number;
  name: string;
  order: number;
}

function getApiErrorMessage(error: unknown, fallback = "Có lỗi xảy ra!"): string {
  const responseData = (error as { response?: { data?: unknown } })?.response?.data;
  if (!responseData) return fallback;
  if (typeof responseData === "string") return responseData;
  if (Array.isArray(responseData) && typeof responseData[0] === "string") return responseData[0];
  if (typeof responseData === "object") {
    if ("detail" in responseData && typeof (responseData as { detail?: unknown }).detail === "string") {
      return (responseData as { detail: string }).detail;
    }
    const firstValue = Object.values(responseData as Record<string, unknown>)[0];
    if (typeof firstValue === "string") return firstValue;
    if (Array.isArray(firstValue) && typeof firstValue[0] === "string") return firstValue[0];
  }
  return fallback;
}

export default function AdminSizes() {
  const [sizesList, setSizesList] = useState<Size[]>([]);
  const [loading, setLoading] = useState(true);

  const [showModal, setShowModal] = useState(false);
  const [editingSize, setEditingSize] = useState<Size | null>(null);
  const [formName, setFormName] = useState("");
  const [formOrder, setFormOrder] = useState(0);
  const [formError, setFormError] = useState("");
  const [formLoading, setFormLoading] = useState(false);

  const [editingOrders, setEditingOrders] = useState<Record<number, number>>({});
  const [savingOrderId, setSavingOrderId] = useState<number | null>(null);

  const loadSizes = async () => {
    try {
      const res = await sizesApi.list();
      const raw: Size[] = res.data.results || res.data;
      setSizesList([...raw].sort((a, b) => (a.order ?? 0) - (b.order ?? 0)));
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSizes();
  }, []);

  const openAdd = () => {
    setEditingSize(null);
    setFormName("");
    setFormOrder(0);
    setFormError("");
    setShowModal(true);
  };

  const openEdit = (s: Size) => {
    setEditingSize(s);
    setFormName(s.name);
    setFormOrder(s.order);
    setFormError("");
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = formName.trim();
    if (!name) {
      setFormError("Vui lòng nhập tên kích thước.");
      return;
    }
    setFormError("");
    setFormLoading(true);
    try {
      if (editingSize) {
        await admin.sizes.update(editingSize.id, { name, order: formOrder });
      } else {
        await admin.sizes.create({ name, order: formOrder });
      }
      setShowModal(false);
      await loadSizes();
    } catch (error) {
      setFormError(getApiErrorMessage(error, "Không thể lưu kích thước."));
    } finally {
      setFormLoading(false);
    }
  };

  const handleDelete = async (id: number, name: string) => {
    if (!confirm(`Xóa kích thước "${name}"? Thao tác này không thể hoàn tác.`)) return;
    try {
      await admin.sizes.delete(id);
      await loadSizes();
    } catch (error) {
      alert(getApiErrorMessage(error, "Không thể xóa kích thước."));
    }
  };

  const handleSaveOrder = async (s: Size, newOrder: number) => {
    setSavingOrderId(s.id);
    try {
      await admin.sizes.update(s.id, { name: s.name, order: newOrder });
      await loadSizes();
      setEditingOrders((prev) => {
        const next = { ...prev };
        delete next[s.id];
        return next;
      });
    } catch {
      alert("Không thể lưu thứ tự.");
    } finally {
      setSavingOrderId(null);
    }
  };

  if (loading)
    return (
      <AdminLayout>
        <div className="loading">Loading...</div>
      </AdminLayout>
    );

  return (
    <AdminLayout>
      <div className="admin-page">
        <div className="page-header">
          <div>
            <h3>Quản lý kích thước</h3>
            <p className="page-header-desc">
              Thêm, sửa, xóa size và điều chỉnh thứ tự hiển thị trên trang sản phẩm.{" "}
              <strong>Số thứ tự nhỏ hơn = hiển thị trước.</strong>
            </p>
          </div>
          <button className="btn-primary" onClick={openAdd}>
            + Thêm kích thước
          </button>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th className="sizes-col-id">ID</th>
              <th>Tên kích thước</th>
              <th className="sizes-col-order">Thứ tự hiển thị</th>
              <th className="sizes-col-actions">Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {sizesList.length === 0 ? (
              <tr>
                <td colSpan={4} className="sizes-empty-cell">
                  Chưa có kích thước nào. Bấm <strong>+ Thêm kích thước</strong> để bắt đầu.
                </td>
              </tr>
            ) : (
              sizesList.map((s) => {
                const currentOrder = editingOrders[s.id] ?? s.order;
                const isDirty =
                  editingOrders[s.id] !== undefined && editingOrders[s.id] !== s.order;
                return (
                  <tr key={s.id}>
                    <td className="sizes-id-cell">{s.id}</td>
                    <td>
                      <span className="sizes-name-badge">{s.name}</span>
                    </td>
                    <td>
                      <div className="sizes-order-cell">
                        <input
                          type="number"
                          min={0}
                          value={currentOrder}
                          className="sizes-order-input"
                          onChange={(e) =>
                            setEditingOrders((prev) => ({
                              ...prev,
                              [s.id]: Number(e.target.value),
                            }))
                          }
                          onKeyDown={(e) => {
                            if (e.key === "Enter") handleSaveOrder(s, currentOrder);
                          }}
                        />
                        {isDirty && (
                          <button
                            type="button"
                            className="btn-primary btn-sm sizes-order-save"
                            disabled={savingOrderId === s.id}
                            onClick={() => handleSaveOrder(s, currentOrder)}
                          >
                            {savingOrderId === s.id ? "…" : "Lưu"}
                          </button>
                        )}
                      </div>
                    </td>
                    <td>
                      <button className="btn-edit" onClick={() => openEdit(s)}>
                        Sửa
                      </button>
                      <button className="btn-delete" onClick={() => handleDelete(s.id, s.name)}>
                        Xóa
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>

        {showModal && (
          <div
            className="modal-overlay"
            onClick={(e) => { if (e.target === e.currentTarget) setShowModal(false); }}
          >
            <div className="modal sizes-modal">
              <h3>{editingSize ? "Sửa kích thước" : "Thêm kích thước mới"}</h3>
              <form onSubmit={handleSubmit}>
                <div className="form-group">
                  <label>Tên kích thước</label>
                  <input
                    type="text"
                    placeholder="Vd: S, M, L, XL, 38, 40…"
                    value={formName}
                    onChange={(e) => { setFormName(e.target.value); setFormError(""); }}
                    autoFocus
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Thứ tự hiển thị</label>
                  <input
                    type="number"
                    min={0}
                    value={formOrder}
                    onChange={(e) => setFormOrder(Number(e.target.value))}
                  />
                  <p className="sizes-order-hint">
                    Số nhỏ hơn = hiển thị trước (vd: S=1, M=2, L=3…)
                  </p>
                </div>
                {formError && (
                  <p className="sizes-form-error">{formError}</p>
                )}
                <div className="form-actions">
                  <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>
                    Hủy
                  </button>
                  <button type="submit" className="btn-primary" disabled={formLoading}>
                    {formLoading ? "Đang lưu…" : "Lưu"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}