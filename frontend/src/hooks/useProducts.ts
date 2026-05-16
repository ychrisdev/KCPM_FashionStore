import { useState, useEffect, useCallback } from 'react';
import { products } from '../api/client';
import { normalizeProducts } from '../utils/productUtils';
import { mockHotDeals, mockNewArrivals } from '../data/mockData';
import type { Product } from '../types';

/** Lấy danh sách sản phẩm từ API, fallback mock khi lỗi. Có thể lọc theo category hoặc search. */
export function useProducts(params?: { categoryId?: number; search?: string }) {
  const [items, setItems] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await products.list({
        category: params?.categoryId,
        search: params?.search,
        page_size: 100,
      });
      const list = Array.isArray(res.data) ? res.data : (res.data?.results ?? res.data?.items ?? []);
      setItems(normalizeProducts(list as Parameters<typeof normalizeProducts>[0]));
    } catch {
      setItems([...mockHotDeals, ...mockNewArrivals]);
      setError('Dùng dữ liệu mẫu');
    } finally {
      setLoading(false);
    }
  }, [params?.categoryId, params?.search]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { items, loading, error, refetch };
}
