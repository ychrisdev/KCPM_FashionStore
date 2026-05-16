import { useState, useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { admin } from '../../api/client';
import AdminLayout from '../../components/admin/AdminLayout';
import { useAuth } from '../../context/AuthContext';
import "../../styles/admin/Admin.css";

interface UserProfile {
  id: number;
  user: {
    id: number;
    username: string;
    email: string;
  };
  phone: string;
  address: string;
  role: string;
}

const ROLE_CHOICES = [
  { value: 'customer', label: 'Customer' },
  { value: 'staff', label: 'Staff' },
  { value: 'admin', label: 'Admin' },
];

export default function AdminUsers() {
  const { user: authUser } = useAuth();
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [loading, setLoading] = useState(true);

  const loadUsers = () => {
    admin.users
      .list()
      .then((res) => {
        setUsers(res.data.results || res.data);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleRoleChange = async (profileId: number, newRole: string) => {
    try {
      await admin.users.update(profileId, { role: newRole });
      loadUsers();
    } catch {
      alert('Có lỗi xảy ra!');
    }
  };

  const getRoleBadge = (role: string) => {
    const roleMap: Record<string, string> = {
      admin: 'role-admin',
      staff: 'role-staff',
      customer: 'role-customer',
    };
    return roleMap[role] || '';
  };

  const getRoleLabel = (role: string) => {
    return ROLE_CHOICES.find((r) => r.value === role)?.label || role;
  };

  if (!authUser?.is_admin) {
    return <Navigate to="/admin" replace />;
  }

  if (loading) return <AdminLayout><div className="loading">Loading...</div></AdminLayout>;

  return (
    <AdminLayout>
      <div className="admin-page">
        <div className="page-header">
          <h3>Quản lý người dùng</h3>
          <p className="page-header-hint" style={{ marginTop: 8, opacity: 0.85 }}>
            Chỉ quản trị viên mới có thể thay đổi vai trò tài khoản.
          </p>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Username</th>
              <th>Email</th>
              <th>Phone</th>
              <th>Role</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {users.map((profile) => (
              <tr key={profile.id}>
                <td>{profile.user.id}</td>
                <td>{profile.user.username}</td>
                <td>{profile.user.email}</td>
                <td>{profile.phone || '-'}</td>
                <td>
                  <span className={`role-badge ${getRoleBadge(profile.role)}`}>
                    {getRoleLabel(profile.role)}
                  </span>
                </td>
                <td>
                  <select
                    className="role-select"
                    value={profile.role}
                    aria-label={`Đổi vai trò ${profile.user.username}`}
                    onChange={(e) =>
                      handleRoleChange(profile.id, e.target.value)
                    }
                  >
                    {ROLE_CHOICES.map((role) => (
                      <option key={role.value} value={role.value}>
                        {role.label}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AdminLayout>
  );
}
