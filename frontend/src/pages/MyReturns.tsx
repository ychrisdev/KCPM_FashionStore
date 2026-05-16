import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { returns } from '../api/client';
import { useAuth } from '../context/AuthContext';
import '../styles/pages/MyReturns.css';

const REASON_OPTIONS = [
  { value: 'wrong_item', label: 'Sản phẩm sai' },
  { value: 'damaged', label: 'Sản phẩm hỏng/lỗi' },
  { value: 'not_as_described', label: 'Không đúng mô tả' },
  { value: 'changed_mind', label: 'Thay đổi quyết định' },
  { value: 'other', label: 'Lý do khác' },
];

const STATUS_LABEL: Record<string, string> = {
  pending: 'Chờ duyệt',
  approved: 'Đã duyệt',
  rejected: 'Từ chối',
  completed: 'Hoàn thành',
};

const STATUS_CLASS: Record<string, string> = {
  pending: 'return-status--pending',
  approved: 'return-status--approved',
  rejected: 'return-status--rejected',
  completed: 'return-status--completed',
};

interface ReturnOrderItem {
  id: number;
  product?: { name: string; image?: string };
  variant_info?: { color: { name: string; code: string }; size: { name: string } } | null;
  quantity: number;
  price: string;
}

interface ReturnRequest {
  id: number;
  order: number;
  reason: string;
  description: string;
  status: string;
  admin_note: string;
  order_total: string;
  order_items: ReturnOrderItem[];
  created_at: string;
}

type MyReturnsProps = { embedded?: boolean };

export default function MyReturns({ embedded = false }: MyReturnsProps) {
  const { user } = useAuth();
  const ordersPath = embedded ? "/dashboard/orders" : "/orders";
  const loginRedirect = embedded ? "/login?redirect=/dashboard/returns" : "/login";
  const shellClass = embedded ? "my-returns-page my-returns-page--embed" : "pageSection my-returns-page";
  const innerClass = embedded ? "sectionContainer customer-account-embedInner" : "sectionContainer";
  const [returnList, setReturnList] = useState<ReturnRequest[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }
    returns
      .list()
      .then((res) => {
        const data = res.data as ReturnRequest[] | { results?: ReturnRequest[] };
        setReturnList(Array.isArray(data) ? data : (data.results ?? []));
      })
      .catch(() => setReturnList([]))
      .finally(() => setLoading(false));
  }, [user]);

  if (!user) {
    return (
      <section className={shellClass}>
        <div className={innerClass}>
          <p className="returns-login-hint">
            Vui lòng <Link to={loginRedirect}>đăng nhập</Link> để xem yêu cầu trả hàng.
          </p>
        </div>
      </section>
    );
  }

  if (loading) {
    return (
      <section className={shellClass}>
        <div className={innerClass}>
          <div className="loading">Đang tải...</div>
        </div>
      </section>
    );
  }

  return (
    <section className={shellClass}>
      <div className={innerClass}>
        <div className="returns-header">
          <div>
            <h1 className={`returns-title ${embedded ? 'returns-title--embed' : ''}`.trim()}>Yêu cầu trả hàng & hoàn tiền</h1>
          </div>
        </div>

        {returnList.length === 0 ? (
          <div className="returns-empty">
            <p>Bạn chưa có yêu cầu trả hàng nào.</p>
            <Link to={ordersPath} className="returns-link">Xem lịch sử đơn hàng</Link>
          </div>
        ) : (
          <ul className="returns-list">
            {returnList.map((r) => (
              <li key={r.id} className="returns-card">
                <div className="returns-card-header">
                  <span className="returns-card-id">Yêu cầu #{r.id}</span>
                  <span className="returns-card-order">Đơn #{r.order}</span>
                  <span className={`return-status ${STATUS_CLASS[r.status] ?? ''}`}>
                    {STATUS_LABEL[r.status] ?? r.status}
                  </span>
                </div>
                <div className="returns-card-body">
                  <p className="returns-card-reason">
                    <span className="returns-label">Lý do:</span>{' '}
                    {REASON_OPTIONS.find((o) => o.value === r.reason)?.label ?? r.reason}
                  </p>
                  {r.description && (
                    <p className="returns-card-desc">
                      <span className="returns-label">Mô tả:</span> {r.description}
                    </p>
                  )}
                  {r.order_items && r.order_items.length > 0 && (
                    <div className="returns-items">
                      <p className="returns-label returns-items-title">Sản phẩm trong đơn:</p>
                      <ul className="returns-items-list">
                        {r.order_items.map((item) => (
                          <li key={item.id} className="returns-item-row">
                            <span className="returns-item-name">{item.product?.name ?? 'Sản phẩm'}</span>
                            {item.variant_info && (
                              <span className="returns-item-variant">
                                <span className="returns-item-color-dot" style={{ backgroundColor: item.variant_info.color.code }} />
                                {item.variant_info.color.name} / {item.variant_info.size.name}
                              </span>
                            )}
                            <span className="returns-item-qty">x{item.quantity}</span>
                            <span className="returns-item-price">{Number(item.price).toLocaleString('vi-VN')}đ</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {r.admin_note && (
                    <p className="returns-card-admin-note">
                      <span className="returns-label">Phản hồi từ cửa hàng:</span> {r.admin_note}
                    </p>
                  )}
                  <p className="returns-card-date">
                    Gửi lúc: {new Date(r.created_at).toLocaleString('vi-VN')}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}