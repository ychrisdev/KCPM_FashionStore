import { useEffect, useState } from "react";
import { admin } from "../../api/client";
import AdminLayout from "../../components/admin/AdminLayout";
import "../../styles/admin/Admin.css";

interface Promotion {
  id: number;
  name: string;
  discount_percent: number;
  start_date: string;
  end_date: string;
  is_active: boolean;
}

interface PromotionFormData {
  name: string;
  discount_percent: number;
  start_date: string;
  end_date: string;
}

interface DiscountCode {
  id: number;
  name: string;
  code: string;
  discount_percent: number;
  min_order_value: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
  effective_is_active: boolean;
  usage_limit: number | null;
  used_count: number;
  status: "active" | "expired";
  status_label: string;
}

interface DiscountCodeFormData {
  name: string;
  code: string;
  discount_percent: number;
  min_order_value: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
  usage_limit: string;
}

const emptyPromotionForm: PromotionFormData = {
  name: "",
  discount_percent: 0,
  start_date: "",
  end_date: "",
};

const emptyDiscountCodeForm: DiscountCodeFormData = {
  name: "",
  code: "",
  discount_percent: 0,
  min_order_value: "0",
  start_date: "",
  end_date: "",
  is_active: true,
  usage_limit: "",
};

function getApiErrorMessage(error: unknown, fallback: string): string {
  const responseData = (error as { response?: { data?: unknown } })?.response
    ?.data;

  if (typeof responseData === "string") {
    if (
      responseData.includes("orders_discountcode") ||
      responseData.includes("does not exist")
    ) {
      return "Database chưa cập nhật cho bảng mã giảm giá. Hãy chạy migrate backend rồi thử lại.";
    }
    return fallback;
  }

  if (
    responseData &&
    typeof responseData === "object" &&
    "detail" in responseData &&
    typeof (responseData as { detail?: unknown }).detail === "string"
  ) {
    return (responseData as { detail: string }).detail;
  }

  return fallback;
}

export default function AdminPromotions() {
  const [promotions, setPromotions] = useState<Promotion[]>([]);
  const [discountCodes, setDiscountCodes] = useState<DiscountCode[]>([]);
  const [loading, setLoading] = useState(true);

  const [showPromotionModal, setShowPromotionModal] = useState(false);
  const [editingPromotion, setEditingPromotion] = useState<Promotion | null>(
    null,
  );
  const [promotionForm, setPromotionForm] =
    useState<PromotionFormData>(emptyPromotionForm);

  const [showDiscountCodeModal, setShowDiscountCodeModal] = useState(false);
  const [editingDiscountCode, setEditingDiscountCode] =
    useState<DiscountCode | null>(null);
  const [discountCodeForm, setDiscountCodeForm] =
    useState<DiscountCodeFormData>(emptyDiscountCodeForm);

  useEffect(() => {
    void loadData();
  }, []);

  const loadData = async () => {
    try {
      const [promotionsRes, discountCodesRes] = await Promise.all([
        admin.promotions.list(),
        admin.discountCodes.list(),
      ]);
      setPromotions(promotionsRes.data.results || promotionsRes.data);
      setDiscountCodes(discountCodesRes.data.results || discountCodesRes.data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
    admin.promotions.list().then((res) => {
      console.log("promotions raw:", res.data);
    });
  };

  const handlePromotionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (promotionForm.end_date < promotionForm.start_date) {
      alert("Ngày kết thúc phải sau ngày bắt đầu");
      return;
    }

    const payload: Record<string, unknown> = { ...promotionForm };

    try {
      if (editingPromotion) {
        await admin.promotions.update(editingPromotion.id, payload);
      } else {
        await admin.promotions.create(payload);
      }
      setShowPromotionModal(false);
      setEditingPromotion(null);
      setPromotionForm(emptyPromotionForm);
      await loadData();
    } catch (error) {
      alert(getApiErrorMessage(error, "Có lỗi xảy ra khi lưu khuyến mãi."));
    }
  };

  const handleDiscountCodeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (discountCodeForm.end_date < discountCodeForm.start_date) {
      alert("Ngày kết thúc phải sau ngày bắt đầu");
      return;
    }

    const payload: Record<string, unknown> = {
      ...discountCodeForm,
      code: discountCodeForm.code.trim().toUpperCase(),
      min_order_value: Number(discountCodeForm.min_order_value || "0"),
      usage_limit: discountCodeForm.usage_limit.trim()
        ? Number(discountCodeForm.usage_limit)
        : null,
    };

    try {
      if (editingDiscountCode) {
        await admin.discountCodes.update(editingDiscountCode.id, payload);
      } else {
        await admin.discountCodes.create(payload);
      }
      setShowDiscountCodeModal(false);
      setEditingDiscountCode(null);
      setDiscountCodeForm(emptyDiscountCodeForm);
      await loadData();
    } catch (error) {
      alert(getApiErrorMessage(error, "Có lỗi xảy ra khi lưu mã giảm giá."));
    }
  };

  const handleEditPromotion = (promotion: Promotion) => {
    setEditingPromotion(promotion);
    setPromotionForm({
      name: promotion.name,
      discount_percent: promotion.discount_percent,
      start_date: promotion.start_date,
      end_date: promotion.end_date,
    });
    setShowPromotionModal(true);
  };

  const handleDeletePromotion = async (id: number) => {
    if (!confirm("Bạn có chắc chắn muốn xóa khuyến mãi này?")) return;
    try {
      await admin.promotions.delete(id);
      await loadData();
    } catch (error) {
      alert(getApiErrorMessage(error, "Không thể xóa khuyến mãi."));
    }
  };

  const handleEditDiscountCode = (discountCode: DiscountCode) => {
    setEditingDiscountCode(discountCode);
    setDiscountCodeForm({
      name: discountCode.name,
      code: discountCode.code,
      discount_percent: discountCode.discount_percent,
      min_order_value: discountCode.min_order_value,
      start_date: discountCode.start_date,
      end_date: discountCode.end_date,
      is_active: discountCode.is_active,
      usage_limit:
        discountCode.usage_limit == null
          ? ""
          : String(discountCode.usage_limit),
    });
    setShowDiscountCodeModal(true);
  };

  const handleDeleteDiscountCode = async (id: number) => {
    if (!confirm("Bạn có chắc chắn muốn xóa mã giảm giá này?")) return;
    try {
      await admin.discountCodes.delete(id);
      await loadData();
    } catch (error) {
      alert(getApiErrorMessage(error, "Không thể xóa mã giảm giá."));
    }
  };

  if (loading) {
    return (
      <AdminLayout>
        <div className="loading">Loading...</div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="admin-page">
        <div className="page-header">
          <h3>Quản lý khuyến mãi và mã giảm giá</h3>
          <p className="page-header-desc">
            Khuyến mãi sản phẩm dùng để gắn vào sản phẩm. Mã giảm giá áp dụng ở
            bước thanh toán cho toàn đơn hàng.
          </p>
        </div>

        <div className="page-header">
          <h3>Khuyến mãi sản phẩm</h3>
          <button
            className="btn-primary"
            onClick={() => {
              setEditingPromotion(null);
              setPromotionForm(emptyPromotionForm);
              setShowPromotionModal(true);
            }}
          >
            + Thêm khuyến mãi
          </button>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Tên khuyến mãi</th>
              <th>Giảm giá (%)</th>
              <th>Ngày bắt đầu</th>
              <th>Ngày kết thúc</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {promotions.map((promotion) => (
              <tr key={promotion.id}>
                <td>{promotion.id}</td>
                <td>{promotion.name}</td>
                <td>{promotion.discount_percent}%</td>
                <td>
                  {new Date(promotion.start_date).toLocaleDateString("vi-VN")}
                </td>
                <td>
                  {new Date(promotion.end_date).toLocaleDateString("vi-VN")}
                </td>
                <td>
                  <button
                    className="btn-edit"
                    onClick={() => handleEditPromotion(promotion)}
                  >
                    Sửa
                  </button>
                  <button
                    className="btn-delete"
                    onClick={() => handleDeletePromotion(promotion.id)}
                  >
                    Xóa
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="page-header" style={{ marginTop: "2rem" }}>
          <h3>Mã giảm giá đơn hàng</h3>
          <button
            className="btn-primary"
            onClick={() => {
              setEditingDiscountCode(null);
              setDiscountCodeForm(emptyDiscountCodeForm);
              setShowDiscountCodeModal(true);
            }}
          >
            + Thêm mã giảm giá
          </button>
        </div>

        <table className="data-table discount-table">
          <thead>
            <tr>
              <th>Mã</th>
              <th>Tên</th>
              <th>Giảm (%)</th>
              <th>Đơn tối thiểu</th>
              <th>Hiệu lực</th>
              <th>Lượt dùng</th>
              <th>Trạng thái</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {discountCodes.map((discountCode) => (
              <tr key={discountCode.id}>
                <td className="col-code">
                    {discountCode.code}
                </td>
                <td className="col-name">{discountCode.name}</td>
                <td>{discountCode.discount_percent}%</td>
                <td>
                  {(Number(discountCode.min_order_value) || 0).toLocaleString(
                    "vi-VN",
                  )}
                  đ
                </td>
                <td>
                  {new Date(discountCode.start_date).toLocaleDateString(
                    "vi-VN",
                  )}{" "}
                  -{" "}
                  {new Date(discountCode.end_date).toLocaleDateString("vi-VN")}
                </td>
                <td>
                  {discountCode.used_count}
                  {discountCode.usage_limit != null
                    ? ` / ${discountCode.usage_limit}`
                    : ""}
                </td>
                <td>
                  <span
                    className={`status-badge ${discountCode.effective_is_active ? "status-completed" : "status-cancelled"}`}
                  >
                    {discountCode.effective_is_active
                      ? "Đang hoạt động"
                      : "Hết hạn"}
                  </span>
                </td>
                <td>
                  <button
                    className="btn-edit"
                    onClick={() => handleEditDiscountCode(discountCode)}
                  >
                    Sửa
                  </button>
                  <button
                    className="btn-delete"
                    onClick={() => handleDeleteDiscountCode(discountCode.id)}
                  >
                    Xóa
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {showPromotionModal && (
          <div className="modal-overlay">
            <div className="modal">
              <h3>{editingPromotion ? "Sửa khuyến mãi" : "Thêm khuyến mãi"}</h3>
              <form onSubmit={handlePromotionSubmit}>
                <div className="form-group">
                  <label>Tên khuyến mãi</label>
                  <input
                    type="text"
                    value={promotionForm.name}
                    onChange={(e) =>
                      setPromotionForm({
                        ...promotionForm,
                        name: e.target.value,
                      })
                    }
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Giảm giá (%)</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={promotionForm.discount_percent}
                    onChange={(e) =>
                      setPromotionForm({
                        ...promotionForm,
                        discount_percent: Number(e.target.value),
                      })
                    }
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Ngày bắt đầu</label>
                  <input
                    type="date"
                    value={promotionForm.start_date}
                    onChange={(e) =>
                      setPromotionForm({
                        ...promotionForm,
                        start_date: e.target.value,
                      })
                    }
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Ngày kết thúc</label>
                  <input
                    type="date"
                    value={promotionForm.end_date}
                    onChange={(e) =>
                      setPromotionForm({
                        ...promotionForm,
                        end_date: e.target.value,
                      })
                    }
                    required
                  />
                </div>
                <div className="form-actions">
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setShowPromotionModal(false)}
                  >
                    Hủy
                  </button>
                  <button type="submit" className="btn-primary">
                    Lưu
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {showDiscountCodeModal && (
          <div className="modal-overlay">
            <div className="modal">
              <h3>
                {editingDiscountCode ? "Sửa mã giảm giá" : "Thêm mã giảm giá"}
              </h3>
              <form onSubmit={handleDiscountCodeSubmit}>
                <div className="form-group">
                  <label>Tên chương trình</label>
                  <input
                    type="text"
                    value={discountCodeForm.name}
                    onChange={(e) =>
                      setDiscountCodeForm({
                        ...discountCodeForm,
                        name: e.target.value,
                      })
                    }
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Mã giảm giá</label>
                  <input
                    type="text"
                    value={discountCodeForm.code}
                    onChange={(e) =>
                      setDiscountCodeForm({
                        ...discountCodeForm,
                        code: e.target.value.toUpperCase(),
                      })
                    }
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Giảm giá (%)</label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={discountCodeForm.discount_percent}
                    onChange={(e) =>
                      setDiscountCodeForm({
                        ...discountCodeForm,
                        discount_percent: Number(e.target.value),
                      })
                    }
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Đơn tối thiểu (đ)</label>
                  <input
                    type="number"
                    min="0"
                    value={discountCodeForm.min_order_value}
                    onChange={(e) =>
                      setDiscountCodeForm({
                        ...discountCodeForm,
                        min_order_value: e.target.value,
                      })
                    }
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Ngày bắt đầu</label>
                  <input
                    type="date"
                    value={discountCodeForm.start_date}
                    onChange={(e) =>
                      setDiscountCodeForm({
                        ...discountCodeForm,
                        start_date: e.target.value,
                      })
                    }
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Ngày kết thúc</label>
                  <input
                    type="date"
                    value={discountCodeForm.end_date}
                    onChange={(e) =>
                      setDiscountCodeForm({
                        ...discountCodeForm,
                        end_date: e.target.value,
                      })
                    }
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Giới hạn lượt dùng</label>
                  <input
                    type="number"
                    min="1"
                    value={discountCodeForm.usage_limit}
                    onChange={(e) =>
                      setDiscountCodeForm({
                        ...discountCodeForm,
                        usage_limit: e.target.value,
                      })
                    }
                    placeholder="Để trống nếu không giới hạn"
                  />
                </div>
                <div className="form-group">
                  <label>Trạng thái</label>
                  <button
                    type="button"
                    className={`admin-statusToggle ${discountCodeForm.is_active ? "is-active" : "is-expired"}`}
                    onClick={() =>
                      setDiscountCodeForm({
                        ...discountCodeForm,
                        is_active: !discountCodeForm.is_active,
                      })
                    }
                  >
                    {discountCodeForm.is_active ? "Đang hoạt động" : "Hết hạn"}
                  </button>
                </div>
                <div className="form-actions">
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setShowDiscountCodeModal(false)}
                  >
                    Hủy
                  </button>
                  <button type="submit" className="btn-primary">
                    Lưu
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
