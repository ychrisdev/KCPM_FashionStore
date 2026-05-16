export interface Category {
  id: number;
  name: string;
  description: string;
  image: string;
  is_active?: boolean;
}

export interface Product {
  id: number;
  name: string;
  description: string;
  price: string;
  old_price: string | null;
  stock: number;
  image: string;
  category: { id: number; name: string };
  promotion: { id: number; name: string; discount_percent: number } | null;
  variants?: ProductVariant[];
  rating?: number;
  sold_count?: number;
  review_count?: number;
  size_chart?: string | null;
}

export interface ProductVariant {
  id: number;
  color: { id: number; name: string; code: string };
  size: { id: number; name: string; order: number };
  stock: number;
  price?: number | null;
  effective_price?: number;
}

export interface ApiProduct {
  id: number;
  name: string;
  description: string;
  price: string | number;
  category: { id: number; name: string };
  promotion: { id: number; name: string; discount_percent: number } | null;
  image?: string;
  old_price?: string | null;
  stock?: number;
  variants?: ProductVariant[];
  rating?: number;
  sold_count?: number;
  review_count?: number;
}

export interface Profile {
  id: number;
  user: number;
  phone: string;
  address: string;
  role: string;
  avatar?: string | null;
  /** YYYY-MM-DD từ API; khách có thể để trống */
  birth_date?: string | null;
}

export interface OrderItem {
  id: number;
  product: ApiProduct;
  variant_info?: { color: { id: number; name: string; code: string }; size: { id: number; name: string } } | null;
  quantity: number;
  price: string;
}

export interface Order {
  id: number;
  user: number;
  subtotal?: string;
  discount_code?: string;
  discount_amount?: string;
  shipping_fee?: string;
  total_price: string;
  payment_method?: string;
  /** Trả về từ POST zalopay-sync khi ZaloPay chưa ghi nhận thanh toán */
  zalopay_pending_message?: string;
  gateway_status?: string;
  inventory_deducted?: boolean;
  status: string;
  created_at: string;
  items: OrderItem[];
  confirmed_by_user?: boolean;
  completed_at?: string | null;
  shipping?: {
    name: string;
    phone: string;
    address: string;
    note?: string;
  };
}

export interface PurchasableProduct {
  order_id: number;
  variant_id: number;
  product_name: string;
  variant_info: { color: { id: number; name: string; code: string }; size: { id: number; name: string } };
  price: string;
  purchased_at: string;
  days_remaining: number;
}

export interface Review {
  id: number;
  user: { id: number; username: string; avatar?: string | null };
  product: number;
  product_name: string;
  variant_info: { color: { id: number; name: string; code: string }; size: { id: number; name: string } } | null;
  rating: number;
  feedback_type: string;
  content: string;
  is_visible?: boolean;
  created_at: string;
}

