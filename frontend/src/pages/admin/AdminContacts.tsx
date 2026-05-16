import { useEffect, useState } from 'react';
import { admin } from '../../api/client';
import AdminLayout from '../../components/admin/AdminLayout';
import "../../styles/admin/Admin.css";

interface Contact {
  id: number;
  name: string;
  email: string;
  phone?: string;
  subject: string;
  message: string;
  handled: boolean;
  created_at: string;
}

export default function AdminContacts() {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'open' | 'done'>('all');
  const [detail, setDetail] = useState<Contact | null>(null);

  const loadContacts = () => {
    admin.contacts
      .list()
      .then((res) => {
        const data = res?.data;
        const list = Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : []);
        setContacts(list as Contact[]);
      })
      .catch((err) => {
        console.error('Load contacts failed:', err);
        setContacts([]);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadContacts();
  }, []);

  const filtered = contacts.filter((c) => {
    if (filter === 'open') return !c.handled;
    if (filter === 'done') return c.handled;
    return true;
  });

  const setHandled = async (id: number, handled: boolean) => {
    try {
      await admin.contacts.patch(id, { handled });
      setContacts((prev) => prev.map((c) => (c.id === id ? { ...c, handled } : c)));
      if (detail?.id === id) setDetail((d) => (d ? { ...d, handled } : null));
    } catch {
      window.alert('Không cập nhật được.');
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Xóa liên hệ này?')) return;
    try {
      await admin.contacts.delete(id);
      loadContacts();
      setDetail((d) => (d?.id === id ? null : d));
    } catch {
      window.alert('Có lỗi xảy ra!');
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
          <h3>Quản lý liên hệ</h3>
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
              <th>Tên</th>
              <th>Email</th>
              <th>SĐT</th>
              <th>Chủ đề</th>
              <th>Nội dung</th>
              <th>Đã xử lý</th>
              <th>Ngày gửi</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((contact) => (
              <tr key={contact.id}>
                <td>{contact.id}</td>
                <td>{contact.name}</td>
                <td>{contact.email}</td>
                <td>{contact.phone || '—'}</td>
                <td>{contact.subject}</td>
                <td className="message-cell">{contact.message}</td>
                <td>
                  <input
                    type="checkbox"
                    checked={contact.handled}
                    onChange={(e) => setHandled(contact.id, e.target.checked)}
                    aria-label="Đã xử lý"
                  />
                </td>
                <td>{new Date(contact.created_at).toLocaleDateString('vi-VN')}</td>
                <td>
                  <button type="button" className="btn-secondary btn-sm" onClick={() => setDetail(contact)}>
                    Chi tiết
                  </button>{' '}
                  <button type="button" className="btn-delete btn-sm" onClick={() => handleDelete(contact.id)}>
                    Xóa
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {detail && (
          <div className="modal-overlay" role="dialog" aria-modal="true">
            <div className="modal modal--wide">
              <h3>Liên hệ #{detail.id}</h3>
              <p>
                <strong>{detail.name}</strong> — {detail.email}
              </p>
              {detail.phone ? <p>SĐT: {detail.phone}</p> : null}
              <p>Chủ đề: {detail.subject || '—'}</p>
              <p className="admin-pre">{detail.message}</p>
              <label className="admin-inlineCheck">
                <input
                  type="checkbox"
                  checked={detail.handled}
                  onChange={(e) => setHandled(detail.id, e.target.checked)}
                />{' '}
                Đã xử lý
              </label>
              <p>
                <button type="button" className="btn-secondary" onClick={() => setDetail(null)}>
                  Đóng
                </button>
              </p>
            </div>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
