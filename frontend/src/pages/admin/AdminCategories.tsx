import { useEffect, useState } from 'react';
import { admin } from '../../api/client';
import AdminLayout from '../../components/admin/AdminLayout';
import "../../styles/admin/Admin.css";

interface Category {
  id: number;
  name: string;
  description: string;
  image?: string;
  is_active?: boolean;
}

interface CategoryFormData {
  name: string;
  description: string;
  is_active: boolean;
}

export default function AdminCategories() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [formData, setFormData] = useState<CategoryFormData>({
    name: '',
    description: '',
    is_active: true,
  });
  /** File ảnh mới chọn (thêm/sửa); gửi multipart lên API */
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);

  const loadCategories = () => {
    admin.categories
      .list()
      .then((res) => {
        setCategories(res.data.results || res.data);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadCategories();
  }, []);

  useEffect(() => {
    return () => {
      if (imagePreview?.startsWith('blob:')) {
        URL.revokeObjectURL(imagePreview);
      }
    };
  }, [imagePreview]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const fd = new FormData();
      fd.append('name', formData.name.trim());
      fd.append('description', formData.description.trim());
      fd.append('is_active', String(formData.is_active));
      if (imageFile) {
        fd.append('image', imageFile);
      }

      if (editingCategory) {
        await admin.categories.update(editingCategory.id, fd);
      } else {
        await admin.categories.create(fd);
      }
      setShowModal(false);
      setEditingCategory(null);
      setFormData({ name: '', description: '', is_active: true });
      setImageFile(null);
      setImagePreview(null);
      loadCategories();
    } catch {
      window.alert('Có lỗi xảy ra! Kiểm tra quyền admin và định dạng ảnh.');
    }
  };

  const handleEdit = (category: Category) => {
    setEditingCategory(category);
    setFormData({
      name: category.name,
      description: category.description,
      is_active: category.is_active ?? true,
    });
    setImageFile(null);
    setImagePreview(category.image || null);
    setShowModal(true);
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Bạn có chắc chắn muốn xóa danh mục này?')) return;
    try {
      await admin.categories.delete(id);
      loadCategories();
    } catch {
      window.alert('Có lỗi xảy ra!');
    }
  };

  const openAddModal = () => {
    setEditingCategory(null);
    setFormData({ name: '', description: '', is_active: true });
    setImageFile(null);
    setImagePreview(null);
    setShowModal(true);
  };

  const onPickImage = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setImageFile(f);
    if (imagePreview?.startsWith('blob:')) {
      URL.revokeObjectURL(imagePreview);
    }
    setImagePreview(URL.createObjectURL(f));
  };

  const clearPickedImage = () => {
    setImageFile(null);
    if (imagePreview?.startsWith('blob:')) {
      URL.revokeObjectURL(imagePreview);
    }
    setImagePreview(editingCategory?.image || null);
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
          <h3>Quản lý danh mục</h3>
          <button type="button" className="btn-primary" onClick={openAddModal}>
            + Thêm danh mục
          </button>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>Ảnh</th>
              <th>ID</th>
              <th>Tên danh mục</th>
              <th>Mô tả</th>
              <th>Trạng thái</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {categories.map((category) => (
              <tr key={category.id}>
                <td className="admin-cat-thumb-cell">
                  <img
                    className="admin-cat-thumb"
                    src={category.image}
                    alt=""
                    loading="lazy"
                    decoding="async"
                  />
                </td>
                <td>{category.id}</td>
                <td>{category.name}</td>
                <td className="message-cell">{category.description}</td>
                <td>
                  <span className={`status-badge ${category.is_active !== false ? 'success' : 'error'}`}>
                    {category.is_active !== false ? 'Hiển thị' : 'Đã ẩn'}
                  </span>
                </td>
                <td>
                  <button type="button" className="btn-edit" onClick={() => handleEdit(category)}>
                    Sửa
                  </button>{' '}
                  <button type="button" className="btn-delete" onClick={() => handleDelete(category.id)}>
                    Xóa
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {showModal && (
          <div className="modal-overlay">
            <div className="modal modal--category">
              <h3>{editingCategory ? 'Sửa danh mục' : 'Thêm danh mục'}</h3>
              <form onSubmit={handleSubmit}>
                <div className="form-group">
                  <label htmlFor="cat-name">Tên danh mục</label>
                  <input
                    id="cat-name"
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="cat-desc">Mô tả</label>
                  <textarea
                    id="cat-desc"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  />
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '15px' }}>
                  <label htmlFor="cat-active" style={{ marginBottom: 0 }}>Kích hoạt (Hiển thị):</label>
                  <input
                    id="cat-active"
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="cat-image">Ảnh danh mục</label>
                  <p className="admin-field-hint">JPG, PNG, WebP — tùy chọn; để trống khi sửa nếu giữ ảnh cũ.</p>
                  <input
                    id="cat-image"
                    type="file"
                    accept="image/jpeg,image/png,image/webp,image/gif"
                    onChange={onPickImage}
                  />
                  {(imagePreview || editingCategory?.image) && (
                    <div className="admin-cat-preview">
                      <img src={imagePreview || editingCategory?.image} alt="Xem trước" />
                      {imageFile && (
                        <button type="button" className="btn-secondary btn-sm" onClick={clearPickedImage}>
                          Bỏ ảnh vừa chọn
                        </button>
                      )}
                    </div>
                  )}
                </div>
                <div className="form-actions">
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
