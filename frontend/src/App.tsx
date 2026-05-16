import { Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import Home from "./pages/Home";
import About from "./pages/About";
import Policy from "./pages/Policy";
import Contact from "./pages/Contact";
import Feedback from "./pages/Feedback";
import Careers from "./pages/Careers";
import Products from "./pages/Products";
import Search from "./pages/Search";
import Cart from "./pages/Cart";
import Checkout from "./pages/Checkout";
import Profile from "./pages/Profile";
import OrderHistory from "./pages/OrderHistory";
import MyFeedback from "./pages/MyFeedback";
import WalletPage from "./pages/WalletPage";
import Wishlist from "./pages/Wishlist";
import Layout from "./components/Layout";
import ProductDetail from "./components/ProductDetail";
import AdminDashboard from "./pages/admin/AdminDashboard";
import AdminProducts from "./pages/admin/AdminProducts";
import AdminCategories from "./pages/admin/AdminCategories";
import AdminPromotions from "./pages/admin/AdminPromotions";
import AdminOrders from "./pages/admin/AdminOrders";
import AdminUsers from "./pages/admin/AdminUsers";
import AdminReviews from "./pages/admin/AdminReviews";
import AdminContacts from "./pages/admin/AdminContacts";
import AdminFeedbacks from "./pages/admin/AdminFeedbacks";
import AdminPolicies from "./pages/admin/AdminPolicies";
import AdminBirthdayEmail from "./pages/admin/AdminBirthdayEmail";
import AdminRoute from "./components/admin/AdminRoute";
import MyReturns from "./pages/MyReturns";
import CustomerAccountRoute from "./components/account/CustomerAccountRoute";
import CustomerAccountLayout from "./components/account/CustomerAccountLayout";
import AccountDashboardHome from "./pages/account/AccountDashboardHome";
import AdminReturns from "./pages/admin/AdminReturns";
import AdminSizes from "./pages/admin/AdminSizes";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import ScrollToTop from "./components/ScrollToTop";
import "./styles/index.css";
import "./App.css";

function App() {
  const { pathname, search } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname, search]);

  return (
    <AuthProvider>
      <ScrollToTop />
      <div className="app">
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/auth/google/callback" element={<Login />} />
            <Route path="/auth/facebook/callback" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/cart" element={<Cart />} />
            <Route path="/products" element={<Products />} />
            <Route path="/search" element={<Search />} />
            <Route path="/checkout" element={<Checkout />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/orders" element={<OrderHistory />} />
            <Route path="/my-feedback" element={<MyFeedback />} />
            <Route path="/wishlist" element={<Wishlist />} />
            <Route path="/my-returns" element={<MyReturns />} />
            <Route path="/product/:id" element={<ProductDetail />} />
            <Route path="/about" element={<About />} />
            <Route path="/contact" element={<Contact />} />
            <Route path="/feedback" element={<Feedback />} />
            <Route path="/careers" element={<Careers />} />
            <Route path="/policy" element={<Policy />} />
            <Route path="/policy/view/:policyId" element={<Policy />} />
            <Route path="/policy/:slug" element={<Policy />} />
          </Route>
          <Route path="/dashboard" element={<CustomerAccountRoute />}>
            <Route element={<CustomerAccountLayout />}>
              <Route index element={<AccountDashboardHome />} />
              <Route path="orders" element={<OrderHistory embedded />} />
              <Route path="profile" element={<Profile embedded />} />
              <Route path="returns" element={<MyReturns embedded />} />
              <Route path="wallet" element={<WalletPage />} />
            </Route>
          </Route>
          <Route path="/admin" element={<AdminRoute />}>
            <Route index element={<AdminDashboard />} />
            <Route path="products" element={<AdminProducts />} />
            <Route path="categories" element={<AdminCategories />} />
            <Route path="promotions" element={<AdminPromotions />} />
            <Route path="orders" element={<AdminOrders />} />
            <Route path="users" element={<AdminUsers />} />
            <Route path="reviews" element={<AdminReviews />} />
            <Route path="contacts" element={<AdminContacts />} />
            <Route path="feedbacks" element={<AdminFeedbacks />} />
            <Route path="policies" element={<AdminPolicies />} />
            <Route path="birthday-email" element={<AdminBirthdayEmail />} />
            <Route path="returns" element={<AdminReturns />} />
            <Route path="sizes" element={<AdminSizes />} />
          </Route>
        </Routes>
      </div>
    </AuthProvider>
  );
}

export default App;