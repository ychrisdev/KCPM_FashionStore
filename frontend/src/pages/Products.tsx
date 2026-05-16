import { useSearchParams } from 'react-router-dom';
import ProductCard from '../components/ProductCard';
import { useProducts } from '../hooks/useProducts';
import { useCategories } from '../hooks/useCategories';
import { useMemo, useState, useEffect } from 'react';
import {
  filterAndSortCatalogProducts,
  parseCatalogSortKey,
  type CatalogSortKey,
} from '../utils/productSort';
import '../styles/pages/Products.css';

export default function Products() {
  const [searchParams, setSearchParams] = useSearchParams();

  const categoryId = searchParams.get('category')
    ? Number(searchParams.get('category'))
    : undefined;

  // Đọc từ khoá từ navbar search (URL param ?search=...)
  const query = searchParams.get('search') ?? '';

  const { items: products, loading, error } = useProducts({ categoryId });
  const { items: categories } = useCategories();

  const sort: CatalogSortKey = parseCatalogSortKey(searchParams.get('sort'));

  const currentCategory = categories.find(c => c.id === categoryId);
  const PAGE_SIZE = 12;
  const [currentPage, setCurrentPage] = useState(1);
  useEffect(() => { setCurrentPage(1); }, [categoryId, query, sort]);
  const titleMain   = query ? 'Kết quả' : currentCategory ? 'Danh mục' : 'Tất cả';
  const titleItalic = query ? `"${query}"` : currentCategory ? currentCategory.name : 'Sản Phẩm';
  
  /* Filter + sort — client-side */
  const displayed = useMemo(
    () => filterAndSortCatalogProducts(products, query, sort),
    [products, query, sort],
  );
  const totalPages = Math.ceil(displayed.length / PAGE_SIZE);
  const paginated = displayed.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [currentPage]);
  // Khi chọn danh mục thì xoá search để tránh conflict
  const handleCategoryClick = (id?: number) => {
    setSearchParams(id ? { category: String(id) } : {});
  };

  const handleSortClick = (value: CatalogSortKey) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value === 'default') {
        next.delete('sort');
      } else {
        next.set('sort', value);
      }
      return next;
    });
  };

  return (
    <section className="products-page">
      <div className="sectionContainer">

        {/* ── Header ── */}
        <div className="sectionHeader">
          <div>
            <h1 className="sectionTitle">
              {titleMain} <em>{titleItalic}</em>
            </h1>
            <p className="sectionSubtitle">
              {loading ? 'Đang tải sản phẩm…' : `${displayed.length} sản phẩm có sẵn`}
            </p>
          </div>
        </div>

        {/* ── Body ── */}
        <div className="productsLayout">

          {/* ── Sidebar ── */}
          <aside className="productsSidebar">

            {/* Danh mục */}
            <h3 className="sidebarTitle">Danh mục</h3>
            <nav className="categoryNav">
              <button
                type="button"
                className={`categoryNavItem ${!categoryId && !query ? 'active' : ''}`}
                onClick={() => handleCategoryClick()}
              >
                Tất cả
              </button>
              {categories.map((cat) => (
                <button
                  key={cat.id}
                  type="button"
                  className={`categoryNavItem ${categoryId === cat.id ? 'active' : ''}`}
                  onClick={() => handleCategoryClick(cat.id)}
                >
                  {cat.name}
                </button>
              ))}
            </nav>

            {/* Sắp xếp */}
            <h3 className="sidebarTitle" style={{ marginTop: '28px' }}>Sắp xếp</h3>
            <div className="sortNav">
              {([
                { value: 'default',    label: 'Mặc định' },
                { value: 'price-asc',  label: 'Giá tăng dần' },
                { value: 'price-desc', label: 'Giá giảm dần' },
                { value: 'name-asc',   label: 'Tên A → Z' },
                { value: 'popular',    label: 'Bán chạy' },
                { value: 'discount',   label: 'Giảm giá lớn' },
              ] as const).map(opt => (
                <button
                  key={opt.value}
                  type="button"
                  className={`sortNavItem ${sort === opt.value ? 'active' : ''}`}
                  onClick={() => handleSortClick(opt.value)}
                >
                  <span className="sortRadio" />
                  {opt.label}
                </button>
              ))}
            </div>

          </aside>

          {/* ── Main ── */}
          <div className="productsMain">

            {error && <p className="productsFallbackNote">{error}</p>}

            {loading ? (
              <div className="productsLoading">
                <div className="loading">Đang tải</div>
              </div>
            ) : displayed.length === 0 ? (
              <p className="productsEmpty">
                {query
                  ? `Không tìm thấy sản phẩm nào cho "${query}".`
                  : 'Chưa có sản phẩm nào trong danh mục này.'}
              </p>
            ) : (
              <>
                <div className="productsResults">
                  <span className="productsResultsCount">
                    Hiển thị <strong>{displayed.length}</strong> sản phẩm
                    {query && <> cho <strong>"{query}"</strong></>}
                  </span>
                </div>

                <div className="productGrid">
                  {paginated.map((product) => (
                    <ProductCard key={product.id} product={product} />
                  ))}
                </div>
                {totalPages > 1 && (
                  <div className="pagination">
                    <button className="paginationBtn" onClick={() => { setCurrentPage(p => Math.max(1, p - 1)); window.scrollTo({ top: 0, behavior: 'smooth' }); }} disabled={currentPage === 1}>‹</button>
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
                      <button key={page} className={`paginationBtn ${currentPage === page ? 'active' : ''}`} onClick={() => { setCurrentPage(page); window.scrollTo({ top: 0, behavior: 'smooth' }); }}>{page}</button>
                    ))}
                    <button className="paginationBtn" onClick={() => { setCurrentPage(p => Math.min(totalPages, p + 1)); window.scrollTo({ top: 0, behavior: 'smooth' }); }} disabled={currentPage === totalPages}>›</button>
                  </div>
                )}
              </>
            )}
          </div>

        </div>
      </div>
    </section>
  );
}