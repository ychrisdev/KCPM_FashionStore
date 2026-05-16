import { useState, useEffect, useCallback } from 'react';
import { categories } from '../api/client';
import { mockCategories } from '../data/mockData';
import type { Category } from '../types';

const DEFAULT_IMAGE =
  'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400&h=400&fit=crop';

/** Lấy danh sách danh mục từ API, fallback mock khi lỗi. */
export function useCategories() {
  const [items, setItems] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await categories.list();
      const list = Array.isArray(res.data) ? res.data : (res.data?.results ?? []);
      setItems(
        list.map((c: { id: number; name: string; description?: string }) => ({
          id: c.id,
          name: c.name,
          description: c.description ?? '',
          image: DEFAULT_IMAGE,
        }))
      );
    } catch {
      setItems(mockCategories);
      setError('Dùng dữ liệu mẫu');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { items, loading, error, refetch };
}
