import { useEffect, useState } from 'react';
import { admin } from '../../api/client';
import AdminLayout from '../../components/admin/AdminLayout';
import "../../styles/admin/Admin.css";

interface Policy {
  id: number;
  title: string;
  content: string;
}

export default function AdminPolicies() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<Policy | null>(null);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');

  const load = () => {
    admin.policies
      .list()
      .then((res) => {
        const d = res.data as { results?: Policy[] };
        setPolicies(d.results || (res.data as Policy[]) || []);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const openAdd = () => {
    setEditing(null);
    setTitle('');
    setContent('');
    setShowModal(true);
  };

  const openEdit = (p: Policy) => {
    setEditing(p);
    setTitle(p.title);
    setContent(p.content);
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editing) {
        await admin.policies.update(editing.id, { title, content });
      } else {
        await admin.policies.create({ title, content });
      }
      setShowModal(false);
      load();
    } catch {
      window.alert('Có lỗi xảy ra (cần quyền nhân viên).');
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Xóa chính sách này?')) return;
    try {
      await admin.policies.delete(id);
      load();
    } catch {
      window.alert('Không xóa được.');
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
          <h3>Chính sách (nội dung trang Policy)</h3>
          <button type="button" className="btn-primary" onClick={openAdd}>
            + Thêm chính sách
          </button>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Tiêu đề</th>
              <th>Nội dung (rút gọn)</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {policies.map((p) => (
              <tr key={p.id}>
                <td>{p.id}</td>
                <td>{p.title}</td>
                <td className="message-cell">{p.content.slice(0, 120)}{p.content.length > 120 ? '…' : ''}</td>
                <td>
                  <button type="button" className="btn-secondary btn-sm" onClick={() => openEdit(p)}>
                    Sửa
                  </button>{' '}
                  <button type="button" className="btn-delete btn-sm" onClick={() => handleDelete(p.id)}>
                    Xóa
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {showModal && (
          <div className="modal-overlay">
            <div className="modal modal--wide">
              <h3>{editing ? 'Sửa chính sách' : 'Thêm chính sách'}</h3>
              <form onSubmit={handleSubmit}>
                <div className="form-group">
                  <label htmlFor="pol-title">Tiêu đề</label>
                  <input
                    id="pol-title"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    required
                    maxLength={200}
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="pol-content">Nội dung</label>
                  <textarea
                    id="pol-content"
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    required
                    rows={12}
                    className="admin-textarea"
                  />
                </div>
                <div className="modal-actions">
                  <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>
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
