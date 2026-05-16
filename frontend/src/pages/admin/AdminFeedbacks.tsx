import { useEffect, useState } from 'react';
import { admin } from '../../api/client';
import AdminLayout from '../../components/admin/AdminLayout';
import "../../styles/admin/Admin.css";

interface FeedbackRow {
  id: number;
  user: number;
  username?: string;
  message: string;
  handled: boolean;
  created_at: string;
}

export default function AdminFeedbacks() {
  const [rows, setRows] = useState<FeedbackRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'open' | 'done'>('all');

  const loadFeedbacks = () => {
    admin.feedbacks
      .list()
      .then((res) => {
        const data = res?.data;
        const list = Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : []);
        setRows(list as FeedbackRow[]);
      })
      .catch((err) => {
        console.error('Load feedbacks failed:', err);
        setRows([]);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadFeedbacks();
  }, []);

  const filtered = rows.filter((f) => {
    if (filter === 'open') return !f.handled;
    if (filter === 'done') return f.handled;
    return true;
  });

  const setHandled = async (id: number, handled: boolean) => {
    try {
      await admin.feedbacks.patch(id, { handled });
      setRows((prev) => prev.map((r) => (r.id === id ? { ...r, handled } : r)));
    } catch {
      window.alert('Không cập nhật được.');
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Xóa góp ý này?')) return;
    try {
      await admin.feedbacks.delete(id);
      loadFeedbacks();
    } catch {
      window.alert('Có lỗi xảy ra!');
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
          <div>
            <h3>Góp ý từ khách hàng</h3>
            <p className="page-header-desc">Nội dung gửi từ trang Góp ý (đăng nhập).</p>
          </div>
        </div>

        <div className="admin-filters">
          <label>
            Lọc:{' '}
            <select value={filter} onChange={(e) => setFilter(e.target.value as typeof filter)}>
              <option value="all">Tất cả</option>
              <option value="open">Chưa xử lý</option>
              <option value="done">Đã xử lý</option>
            </select>
          </label>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Tài khoản</th>
              <th>Nội dung</th>
              <th>Đã xử lý</th>
              <th>Ngày</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', padding: '1.5rem' }}>
                  Không có góp ý phù hợp.
                </td>
              </tr>
            ) : (
              filtered.map((f) => (
                <tr key={f.id}>
                  <td>{f.id}</td>
                  <td>{f.username ?? `User #${f.user}`}</td>
                  <td className="message-cell">{f.message}</td>
                  <td>
                    <input
                      type="checkbox"
                      checked={f.handled}
                      onChange={(e) => setHandled(f.id, e.target.checked)}
                      aria-label="Đã xử lý"
                    />
                  </td>
                  <td>{new Date(f.created_at).toLocaleString('vi-VN')}</td>
                  <td>
                    <button type="button" className="btn-delete" onClick={() => void handleDelete(f.id)}>
                      Xóa
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </AdminLayout>
  );
}
