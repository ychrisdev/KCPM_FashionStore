export interface Category {
  id: number;
  name: string;
  description: string;
  image: string;
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
}

export const mockCategories: Category[] = [
  {
    id: 1,
    name: 'Áo Thun',
    description: 'Áo thun nam nữ',
    image: 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400&h=400&fit=crop',
  },
  {
    id: 2,
    name: 'Quần Jean',
    description: 'Quần jean nam nữ',
    image: 'https://images.unsplash.com/photo-1542272604-787c3835535d?w=400&h=400&fit=crop',
  },
  {
    id: 3,
    name: 'Áo Khoác',
    description: 'Áo khoác các loại',
    image: 'https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=400&h=400&fit=crop',
  },
  {
    id: 4,
    name: 'Váy Đầm',
    description: 'Váy đầm nữ',
    image: 'https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=400&h=400&fit=crop',
  },
];

export const mockHotDeals: Product[] = [
  {
    id: 1,
    name: 'Áo Thun Cotton Basic',
    description: 'Áo thun cotton thoáng mát',
    price: '199.000',
    old_price: '299.000',
    stock: 50,
    image: 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400&h=400&fit=crop',
    category: { id: 1, name: 'Áo Thun' },
    promotion: { id: 1, name: 'Summer Sale', discount_percent: 33 },
  },
  {
    id: 2,
    name: 'Quần Jean Slim Fit',
    description: 'Quần jean ôm body',
    price: '399.000',
    old_price: '499.000',
    stock: 30,
    image: 'https://images.unsplash.com/photo-1542272604-787c3835535d?w=400&h=400&fit=crop',
    category: { id: 2, name: 'Quần Jean' },
    promotion: { id: 1, name: 'Summer Sale', discount_percent: 20 },
  },
  {
    id: 3,
    name: 'Áo Khoác Bomber',
    description: 'Áo khoác bomber nam',
    price: '599.000',
    old_price: '799.000',
    stock: 25,
    image: 'https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=400&h=400&fit=crop',
    category: { id: 3, name: 'Áo Khoác' },
    promotion: { id: 1, name: 'Summer Sale', discount_percent: 25 },
  },
  {
    id: 4,
    name: 'Váy Maxi Hoa',
    description: 'Váy maxi hoa nhí',
    price: '349.000',
    old_price: '449.000',
    stock: 40,
    image: 'https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=400&h=400&fit=crop',
    category: { id: 4, name: 'Váy Đầm' },
    promotion: { id: 1, name: 'Summer Sale', discount_percent: 22 },
  },
];

export const mockNewArrivals: Product[] = [
  {
    id: 5,
    name: 'Áo Sơ Mi Linen',
    description: 'Sơ mi linen mùa hè',
    price: '289.000',
    old_price: null,
    stock: 60,
    image: 'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop',
    category: { id: 1, name: 'Áo Thun' },
    promotion: null,
  },
  {
    id: 6,
    name: 'Quần Short Denim',
    description: 'Quần short denim nữ',
    price: '249.000',
    old_price: null,
    stock: 45,
    image: 'https://images.unsplash.com/photo-1591195853828-11db59a44f6b?w=400&h=400&fit=crop',
    category: { id: 2, name: 'Quần Jean' },
    promotion: null,
  },
  {
    id: 7,
    name: 'Áo Blazer Classic',
    description: 'Blazer công sở',
    price: '899.000',
    old_price: null,
    stock: 20,
    image: 'https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=400&h=400&fit=crop',
    category: { id: 3, name: 'Áo Khoác' },
    promotion: null,
  },
  {
    id: 8,
    name: 'Đầm Evening',
    description: 'Đầm dạ tiệc',
    price: '699.000',
    old_price: null,
    stock: 15,
    image: 'https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?w=400&h=400&fit=crop',
    category: { id: 4, name: 'Váy Đầm' },
    promotion: null,
  },
];
