import { useCallback, useEffect, useRef, useState } from "react";
import { admin } from "../../api/client";
import AdminLayout from "../../components/admin/AdminLayout";
import "../../styles/admin/Admin.css";

type DiscountOption = {
  id: number;
  code: string;
  name: string;
  discount_percent: number;
};

type BirthdayTemplate = {
  id: number;
  email_subject: string;
  intro_text: string;
  cta_button_label: string;
  footer_text: string;
  discount_code: number | null;
  discount_code_detail: DiscountOption | null;
};

const defaultForm: BirthdayTemplate = {
  id: 1,
  email_subject: "",
  intro_text: "",
  cta_button_label: "Vào FashionStore",
  footer_text: "",
  discount_code: null,
  discount_code_detail: null,
};

export default function AdminBirthdayEmail() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [codes, setCodes] = useState<DiscountOption[]>([]);
  const [form, setForm] = useState(defaultForm);
  const [previewHtml, setPreviewHtml] = useState<string | null>(null);
  const [previewSubject, setPreviewSubject] = useState<string | null>(null);
  const [previewName, setPreviewName] = useState("Nguyễn Văn A");
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const loadCodes = useCallback(() => {
    admin.discountCodes
      .list()
      .then((res) => {
        const raw = res.data as
          | { results?: DiscountOption[] }
          | DiscountOption[];
        const list = Array.isArray(raw) ? raw : (raw.results ?? []);
        setCodes(list);
      })
      .catch(console.error);
  }, []);

  const loadTemplate = useCallback(() => {
    setLoading(true);
    admin.birthdayEmail
      .get()
      .then((res) => {
        const t = res.data as BirthdayTemplate;
        setForm({
          ...defaultForm,
          ...t,
          discount_code: t.discount_code ?? null,
        });
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadTemplate();
    loadCodes();
  }, [loadTemplate, loadCodes]);

  useEffect(() => {
    if (!previewHtml || !iframeRef.current) return;
    const doc = iframeRef.current.contentDocument;
    if (!doc) return;
    doc.open();
    doc.write(previewHtml);
    doc.close();
  }, [previewHtml]);

  const payloadFromForm = () => ({
    email_subject: form.email_subject,
    intro_text: form.intro_text,
    cta_button_label: form.cta_button_label,
    footer_text: form.footer_text,
    discount_code: form.discount_code,
  });

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await admin.birthdayEmail.update(payloadFromForm());
      const t = res.data as BirthdayTemplate;
      setForm({
        ...defaultForm,
        ...t,
        discount_code: t.discount_code ?? null,
      });
      window.alert("Đã lưu mẫu email sinh nhật.");
    } catch {
      window.alert("Không lưu được (cần quyền nhân viên).");
    } finally {
      setSaving(false);
    }
  };

  const handlePreview = async () => {
    setPreviewing(true);
    try {
      const res = await admin.birthdayEmail.preview({
        ...payloadFromForm(),
        preview_display_name: previewName.trim() || "Khách hàng thân mến",
      });
      const d = res.data as { html?: string; subject?: string };
      setPreviewHtml(d.html ?? "");
      setPreviewSubject(d.subject ?? null);
    } catch {
      window.alert("Không tạo được xem trước.");
    } finally {
      setPreviewing(false);
    }
  };

  if (loading) {
    return (
      <AdminLayout>
        <div className="loading">Đang tải…</div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="admin-page admin-birthday-page">
        <div className="page-header">
          <div>
            <h3>Email nhắc sinh nhật</h3>
            <p className="admin-birthday-lead">
              Soạn nội dung gửi khách trước 1 ngày. Chọn mã giảm giá có sẵn
              trong hệ thống hoặc để trống và dùng biến môi trường{" "}
              <code>BIRTHDAY_VOUCHER_CODE</code> trên server.
            </p>
          </div>
        </div>

        <div className="admin-birthday-grid">
          {/* ── Form cột trái ── */}
          <form className="admin-birthday-form" onSubmit={handleSave}>
            <label className="admin-birthday-field">
              <span className="admin-birthday-label">Tiêu đề email</span>
              <input
                className="admin-input"
                value={form.email_subject}
                onChange={(e) =>
                  setForm((f) => ({ ...f, email_subject: e.target.value }))
                }
                maxLength={200}
              />
            </label>

            <label className="admin-birthday-field">
              <span className="admin-birthday-label">
                Lời mở đầu (nội dung chính)
              </span>
              <textarea
                className="admin-textarea admin-textarea--tall"
                rows={6}
                value={form.intro_text}
                onChange={(e) =>
                  setForm((f) => ({ ...f, intro_text: e.target.value }))
                }
                placeholder="Ví dụ: Ngày mai là sinh nhật của bạn — chúng tôi xin gửi lời chúc…"
              />
            </label>

            <label className="admin-birthday-field">
              <span className="admin-birthday-label">
                Mã giảm giá gắn vào email
              </span>
              <select
                className="admin-input"
                value={form.discount_code ?? ""}
                onChange={(e) => {
                  const v = e.target.value;
                  setForm((f) => ({
                    ...f,
                    discount_code: v === "" ? null : Number(v),
                  }));
                }}
              >
                <option value="">— Không chọn (dùng .env nếu có) —</option>
                {codes.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.code} · {c.discount_percent}% · {c.name}
                  </option>
                ))}
              </select>
              <span className="admin-birthday-hint">
                Tạo / sửa mã tại mục quản trị mã giảm giá (API đơn hàng).
              </span>
            </label>

            <label className="admin-birthday-field">
              <span className="admin-birthday-label">Chữ nút CTA</span>
              <input
                className="admin-input"
                value={form.cta_button_label}
                onChange={(e) =>
                  setForm((f) => ({ ...f, cta_button_label: e.target.value }))
                }
                maxLength={80}
                placeholder="Vào FashionStore"
              />
            </label>

            <label className="admin-birthday-field">
              <span className="admin-birthday-label">Chân trang / lưu ý</span>
              <textarea
                className="admin-textarea"
                rows={3}
                value={form.footer_text}
                onChange={(e) =>
                  setForm((f) => ({ ...f, footer_text: e.target.value }))
                }
              />
            </label>

            <div className="admin-birthday-actions">
              <button type="submit" className="btn-primary" disabled={saving}>
                {saving ? "Đang lưu…" : "Lưu cấu hình"}
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={handlePreview}
                disabled={previewing}
              >
                {previewing ? "Đang tạo xem trước…" : "Xem trước email"}
              </button>
            </div>
          </form>

          {/* ── Preview cột phải ── */}
          <div className="admin-birthday-previewCol">
            <label className="admin-birthday-field">
              <span className="admin-birthday-label">
                Tên hiển thị khi xem trước
              </span>
              <input
                className="admin-input"
                value={previewName}
                onChange={(e) => setPreviewName(e.target.value)}
                placeholder="Họ tên mẫu"
              />
            </label>

            {previewSubject && (
              <p className="admin-birthday-subjectPreview">
                <strong>Tiêu đề:</strong> {previewSubject}
              </p>
            )}

            <div className="admin-birthday-previewShell">
              {previewHtml ? (
                <iframe
                  ref={iframeRef}
                  title="Xem trước email sinh nhật"
                  className="admin-birthday-iframe"
                />
              ) : (
                <p className="admin-birthday-previewPlaceholder">
                  Bấm &quot;Xem trước email&quot; để hiển thị giao diện thư gửi
                  khách.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}
