import { useEffect, useState } from 'react';
import { admin } from '../../api/client';
import AdminLayout from '../../components/admin/AdminLayout';
import "../../styles/admin/Admin.css";

interface Review {
  id: number;
  user: { username: string };
  product_name: string;
  rating: number;
  is_visible: boolean;
  created_at: string;
}

export default function AdminReviews() {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState(true);
  const [ratingFilter, setRatingFilter] = useState<string>('');

  const loadReviews = () => {
    const params: Record<string, string> = {};
    if (ratingFilter) params.rating = ratingFilter;

    admin.reviews
      .list(Object.keys(params).length ? params : undefined)
      .then((res) => {
        const data = res?.data;
        const list = Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : []);
        setReviews(list as Review[]);
      })
      .catch((err) => {
        console.error('Load reviews failed:', err);
        setReviews([]);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadReviews();
  }, [ratingFilter]);

  const toggleVisible = async (id: number, is_visible: boolean) => {
    try {
      await admin.reviews.update(id, { is_visible });
      setReviews((prev) => prev.map((r) => (r.id === id ? { ...r, is_visible } : r)));
    } catch {
      window.alert('Không cập nhật được (cần quyền nhân viên).');
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Xóa đánh giá này?')) return;
    try {
      await admin.reviews.delete(id);
      loadReviews();
    } catch {
      window.alert('Có lỗi xảy ra!');
    }
  };

  const renderStars = (rating: number) => '★'.repeat(rating) + '☆'.repeat(5 - rating);

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
          <h3>Quản lý đánh giá</h3>
        </div>

        <div className="admin-filters">
          <label>
            Lọc sao:{' '}
            <select value={ratingFilter} onChange={(e) => setRatingFilter(e.target.value)}>
              <option value="">Tất cả</option>
              {[5, 4, 3, 2, 1].map((n) => (
                <option key={n} value={String(n)}>
                  {n} sao
                </option>
              ))}
            </select>
          </label>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Người dùng</th>
              <th>Sản phẩm</th>
              <th>Rating</th>
              <th>Hiển thị</th>
              <th>Ngày tạo</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {reviews.map((review) => (
              <tr key={review.id}>
                <td>{review.id}</td>
                <td>{review.user?.username || 'N/A'}</td>
                <td>{review.product_name || 'N/A'}</td>
                <td>
                  <span className="stars">{renderStars(review.rating)}</span>
                </td>
                <td>
                  <input
                    type="checkbox"
                    checked={review.is_visible !== false}
                    onChange={(e) => toggleVisible(review.id, e.target.checked)}
                    aria-label="Hiển thị trên trang sản phẩm"
                  />
                </td>
                <td>{new Date(review.created_at).toLocaleDateString('vi-VN')}</td>
                <td>
                  <button type="button" className="btn-delete" onClick={() => handleDelete(review.id)}>
                    Xóa
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AdminLayout>
  );
}
