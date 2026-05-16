import { useState } from 'react';
import '../styles/components/Auth.css';

const Auth = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  if (isLoggedIn) {
    return (
      <div className="auth-status">
        <span>Chào bạn, Thành viên!</span>
        <button onClick={() => setIsLoggedIn(false)} className="logout-btn">Đăng xuất</button>
      </div>
    );
  }

  return (
    <div className="login-box">
      <h3>Đăng Nhập</h3>
      <input type="email" placeholder="Email của bạn" />
      <input type="password" placeholder="Mật khẩu" />
      <button onClick={() => setIsLoggedIn(true)} className="login-btn">Đăng nhập</button>
      <p className="forgot-pw">Quên mật khẩu?</p>
    </div>
  );
};

export default Auth;