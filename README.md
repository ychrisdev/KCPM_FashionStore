# Fashion Store

E-commerce web app: Django REST API + React frontend.

## Cấu trúc

- **backend/** – Django (API: products, cart, orders, accounts, reviews, contact)
- **frontend/** – React + Vite + TypeScript

## Yêu cầu

- **Python** 3.11+ (đã kiểm tra với 3.11)
- **Node.js** 20+ (cho Vite 7)
- Mặc định backend dùng **SQLite** (`backend/db.sqlite3`) — không cần cài PostgreSQL để chạy local.

## Chạy dự án

### 1. Cấu hình backend

```bash
cd backend
copy env.example .env
```

(Tạo file `.env`; có thể chỉnh `FRONTEND_ORIGIN`, OAuth, hoặc chuyển sang Postgres — xem `env.example`.)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### 2. Frontend

Terminal khác:

```bash
cd frontend
npm install
npm run dev
```

API: `http://127.0.0.1:8000/api/`

## Đăng nhập Google / Facebook

### Lỗi 400: redirect_uri_mismatch (Google)
1. Vào [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials.
2. Mở OAuth 2.0 Client ID (Web application) của bạn.
3. Trong **Authorized redirect URIs** thêm **đúng chuỗi** (không thừa dấu `/` cuối):
   - `http://localhost:5173/auth/google/callback`
4. Lưu. Chờ vài phút rồi thử đăng nhập lại.

### "Sorry, something went wrong" / Lỗi đăng nhập Facebook
1. Vào [Facebook for Developers](https://developers.facebook.com/) → Ứng dụng của bạn → **Facebook Login** → **Cài đặt**.
2. Trong **Valid OAuth Redirect URIs** thêm **đúng từng ký tự** (không thừa dấu `/` cuối):
   - `http://localhost:5173/auth/facebook/callback`
3. Nếu app đang ở chế độ **Phát triển**: vào **Vai trò** (Roles) → thêm tài khoản Facebook của bạn làm **Người kiểm thử** (Tester) để có thể đăng nhập thử.
4. Lưu thay đổi, đợi 1–2 phút rồi thử đăng nhập lại.

### Lỗi Invalid Scopes: email (Facebook)
Ứng dụng đã chuyển sang chỉ dùng scope `public_profile`; email được xử lý tự động nếu Facebook không trả về.
