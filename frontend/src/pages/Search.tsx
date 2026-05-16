import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import ProductCard from '../components/ProductCard';
import { useProducts } from '../hooks/useProducts';
import '../styles/pages/Search.css';

export default function Search() {
  const [searchParams, setSearchParams] = useSearchParams();
  const q = searchParams.get('q') ?? '';
  const [inputValue, setInputValue] = useState(q);

  const { items: products, loading, error } = useProducts({
    search: q || undefined,
  });

  useEffect(() => {
    setInputValue(q);
  }, [q]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = inputValue.trim();
    if (trimmed) {
      setSearchParams({ q: trimmed });
    } else {
      setSearchParams({});
    }
  };

  return (
    <section className="pageSection search-page">
      <div className="sectionContainer searchContainer">
        <div className="sectionHeader">
          <div>
            <h1 className="sectionTitle">Tìm kiếm sản phẩm</h1>
            <p className="sectionSubtitle">
              {q ? `Kết quả cho "${q}"` : 'Nhập từ khóa để tìm kiếm'}
            </p>
          </div>
        </div>

        <form
          onSubmit={handleSubmit}
          className="searchToolbar"
          style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginBottom: "1.25rem" }}
        >
          <input
            type="search"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Từ khóa…"
            aria-label="Từ khóa tìm kiếm"
            style={{
              flex: "1 1 200px",
              padding: "10px 14px",
              borderRadius: "8px",
              border: "1px solid #e5e7eb",
            }}
          />
          <button type="submit" className="btn-primary" style={{ padding: "10px 20px" }}>
            Tìm kiếm
          </button>
        </form>

        {error && <p className="searchFallbackNote">{error}</p>}

        {loading ? (
          <div className="loading">Đang tải...</div>
        ) : q ? (
          products.length === 0 ? (
            <p className="searchEmpty">Không tìm thấy sản phẩm phù hợp.</p>
          ) : (
            <div className="productGrid">
              {products.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                />
              ))}
            </div>
          )
        ) : (
          <p className="searchHint">Nhập từ khóa và nhấn Tìm kiếm.</p>
        )}
      </div>
    </section>
  );
}
