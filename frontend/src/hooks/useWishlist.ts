import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { wishlistApi } from '../api/client';

const getLegacyKey = (userId: number | string) => `fashion_store_wishlist_${userId}`;

function readLegacyIds(userId: number | string): number[] {
  try {
    const raw = localStorage.getItem(getLegacyKey(userId));
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed)
      ? parsed.filter((x): x is number => typeof x === 'number')
      : [];
  } catch {
    return [];
  }
}

export function useWishlist() {
  const { user } = useAuth();
  const [ids, setIds] = useState<number[]>([]);

  /** Đồng bộ từ server + merge dữ liệu localStorage cũ (một lần) */
  useEffect(() => {
    if (user?.id == null) {
      setIds([]);
      return;
    }
    let cancelled = false;
    const uid = user.id;

    (async () => {
      const legacy = readLegacyIds(uid);
      try {
        const { data: remote } = await wishlistApi.getIds();
        let next = remote?.product_ids ?? [];
        if (legacy.length > 0) {
          const merged = [...new Set([...next, ...legacy])];
          const { data: synced } = await wishlistApi.sync(merged);
          next = synced?.product_ids ?? merged;
          localStorage.removeItem(getLegacyKey(uid));
        }
        if (!cancelled) setIds(next);
      } catch {
        if (cancelled) return;
        if (legacy.length > 0) {
          setIds(legacy);
        } else {
          setIds([]);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [user?.id]);

  const refresh = useCallback(async () => {
    if (user?.id == null) {
      setIds([]);
      return;
    }
    try {
      const { data } = await wishlistApi.getIds();
      setIds(data?.product_ids ?? []);
    } catch {
      /* giữ nguyên state */
    }
  }, [user?.id]);

  const toggle = useCallback(
    async (productId: number) => {
      if (user?.id == null) return;
      try {
        const { data } = await wishlistApi.toggle(productId);
        setIds(data?.product_ids ?? []);
      } catch {
        await refresh();
      }
    },
    [user?.id, refresh]
  );

  const add = useCallback(
    async (productId: number) => {
      if (user?.id == null) return;
      if (ids.includes(productId)) return;
      await toggle(productId);
    },
    [user?.id, ids, toggle]
  );

  const remove = useCallback(
    async (productId: number) => {
      if (user?.id == null) return;
      if (!ids.includes(productId)) return;
      await toggle(productId);
    },
    [user?.id, ids, toggle]
  );

  const has = useCallback(
    (productId: number) => ids.includes(productId),
    [ids]
  );

  return { ids, add, remove, toggle, has, refresh };
}
