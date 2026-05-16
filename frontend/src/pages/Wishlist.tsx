import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import ProductCard from '../components/ProductCard';
import { useWishlist } from '../hooks/useWishlist';
import { products } from '../api/client';
import { normalizeProduct } from '../utils/productUtils';
import { mockHotDeals, mockNewArrivals } from '../data/mockData';
import type { Product } from '../types';
import '../styles/pages/Wishlist.css';

function findMockProduct(id: number): Product | null {
  const all = [...mockHotDeals, ...mockNewArrivals];
  return all.find((p) => p.id === id) ?? null;
}

export default function Wishlist() {
  const { ids, remove } = useWishlist();
  const [productList, setProductList] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchProducts = useCallback(async () => {
    if (ids.length === 0) {
      setProductList([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    const results: Product[] = [];
    for (const id of ids) {
      try {
        const res = await products.get(id);
        results.push(normalizeProduct(res.data as Parameters<typeof normalizeProduct>[0]));
      } catch {
        const mock = findMockProduct(id);
        if (mock) results.push(mock);
      }
    }
    setProductList(results);
    setLoading(false);
  }, [ids]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  return (
    <section className="pageSection wishlist-page">
      <div className="sectionContainer">
        <h1 className="wishlistTitle">Sản phẩm yêu thích</h1>

        {loading ? (
          <div className="loading">Đang tải...</div>
        ) : productList.length === 0 ? (
          <div className="wishlistEmpty">
            <div className="wishlistEmptyIconWrap">
              <svg width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="#E24B4A" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
              </svg>
            </div>
            <p>Bạn chưa thêm sản phẩm nào vào danh sách yêu thích</p>
            <Link to="/products" className="wishlistEmptyBtn">Khám phá sản phẩm</Link>
          </div>
        ) : (
          <div className="wishlistGrid">
            {productList.map((product) => (
              <div key={product.id} className="wishlistCardWrap">
                <button
                  type="button"
                  className="wishlistRemove"
                  onClick={() => void remove(product.id)}
                  aria-label="Xóa khỏi yêu thích"
                >
                  ✕
                </button>
                <ProductCard product={product} />
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}