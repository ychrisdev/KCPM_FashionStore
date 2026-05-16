import { useState, useEffect, useRef } from "react";
import {
  admin,
  categories,
  colors as colorsApi,
  sizes as sizesApi,
  variants as variantsApi,
} from "../../api/client";
import AdminLayout from "../../components/admin/AdminLayout";
import { useAuth } from "../../context/AuthContext";
import "../../styles/admin/AdminProducts.css";

interface Product {
  id: number;
  name: string;
  description: string;
  price: string;
  category: { id: number; name: string };
  promotion: { id: number; name: string } | null;
  variants?: Variant[];
  image?: string;
  images?: { id: number; image: string | null }[];
  size_chart?: string | null;
}

interface Category {
  id: number;
  name: string;
  description: string;
}

interface Color {
  id: number;
  name: string;
  code: string;
}

interface Size {
  id: number;
  name: string;
  order: number;
}

interface Variant {
  id: number;
  color: Color;
  size: Size;
  stock: number;
  price: number | null;
  effective_price?: number;
}

interface ProductFormData {
  name: string;
  description: string;
  price: string;
  category_id: number;
  promotion_id: number | null;
  upload_images?: File[];
  size_chart?: File | null;
  clear_size_chart?: boolean;
  delete_image_ids?: number[];
}

interface VariantFormData {
  color_id: number;
  size_id: number;
  stock: number;
  price: number | null;
}

function getApiErrorMessage(
  error: unknown,
  fallback = "Có lỗi xảy ra!",
): string {
  const responseData = (error as { response?: { data?: unknown } })?.response
    ?.data;
  if (!responseData) return fallback;
  if (typeof responseData === "string") return responseData;
  if (Array.isArray(responseData) && typeof responseData[0] === "string")
    return responseData[0];
  if (typeof responseData === "object") {
    if (
      "detail" in responseData &&
      typeof (responseData as { detail?: unknown }).detail === "string"
    ) {
      return (responseData as { detail: string }).detail;
    }
    const firstValue = Object.values(
      responseData as Record<string, unknown>,
    )[0];
    if (typeof firstValue === "string") return firstValue;
    if (Array.isArray(firstValue) && typeof firstValue[0] === "string")
      return firstValue[0];
  }
  return fallback;
}

function variantStockTone(stock: number): "empty" | "low" | "ok" {
  if (stock <= 0) return "empty";
  if (stock <= 5) return "low";
  return "ok";
}

function productImageGallery(p: Product): string[] {
  const fromDb = (p.images ?? [])
    .map((x) => x.image)
    .filter((u): u is string => Boolean(u));
  if (fromDb.length > 0) return fromDb;
  if (p.image) return [p.image];
  return [];
}

export default function AdminProducts() {
  const { user } = useAuth();
  const canManageVariantStock = user?.is_admin === true;

  const [products, setProducts] = useState<Product[]>([]);
  const [categoriesList, setCategoriesList] = useState<Category[]>([]);
  const [colorsList, setColorsList] = useState<Color[]>([]);
  const [sizesList, setSizesList] = useState<Size[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [promotionsList, setPromotionsList] = useState<
    { id: number; name: string; discount_percent: number; is_active: boolean }[]
  >([]);

  const [showProductModal, setShowProductModal] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [formData, setFormData] = useState<ProductFormData>({
    name: "",
    description: "",
    price: "",
    category_id: 0,
    promotion_id: null,
    upload_images: [],
    size_chart: null,
  });

  const [showVariantModal, setShowVariantModal] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [productVariants, setProductVariants] = useState<Variant[]>([]);
  const [editingVariant, setEditingVariant] = useState<Variant | null>(null);
  const [variantForm, setVariantForm] = useState<VariantFormData>({
    color_id: 0,
    size_id: 0,
    stock: 0,
    price: null,
  });
  const [warehouseDelta, setWarehouseDelta] = useState("");
  const [variantImageIndex, setVariantImageIndex] = useState(0);
  const variantFormPanelRef = useRef<HTMLElement | null>(null);
  const variantColorSelectRef = useRef<HTMLSelectElement | null>(null);

  // Quick-add màu
  const [showQuickAddColor, setShowQuickAddColor] = useState(false);
  const [quickAddColorName, setQuickAddColorName] = useState("");
  const [quickAddColorCode, setQuickAddColorCode] = useState("#000000");
  const [quickAddColorLoading, setQuickAddColorLoading] = useState(false);
  const [quickAddColorError, setQuickAddColorError] = useState("");

  // Quick-add size (trong variant modal)
  const [showQuickAddSize, setShowQuickAddSize] = useState(false);
  const [quickAddSizeName, setQuickAddSizeName] = useState("");
  const [quickAddSizeOrder, setQuickAddSizeOrder] = useState(0);
  const [quickAddSizeLoading, setQuickAddSizeLoading] = useState(false);
  const [quickAddSizeError, setQuickAddSizeError] = useState("");

  // Inline order editing (trong variant modal)
  const [editingOrders, setEditingOrders] = useState<Record<number, number>>(
    {},
  );
  const [savingOrderId, setSavingOrderId] = useState<number | null>(null);

  // ── Size CRUD trong product form ──
  const [sizeManagerName, setSizeManagerName] = useState("");
  const [sizeManagerOrder, setSizeManagerOrder] = useState(0);
  const [sizeManagerError, setSizeManagerError] = useState("");
  const [sizeManagerLoading, setSizeManagerLoading] = useState(false);
  const [editingSizeId, setEditingSizeId] = useState<number | null>(null);
  const [editingSizeName, setEditingSizeName] = useState("");
  const [editingSizeOrder, setEditingSizeOrder] = useState(0);
  const [deletingSizeId, setDeletingSizeId] = useState<number | null>(null);
  const [productCount, setProductCount] = useState(0);
  const [productPage, setProductPage] = useState(1);
  const PRODUCT_PAGE_SIZE = 10;

  const loadData = (search?: string, lowStock?: boolean, page = 1) => {
    const q = search !== undefined ? search : searchQuery;
    const low = lowStock !== undefined ? lowStock : lowStockOnly;
    const params: Record<string, string | number> = {
      page,
      page_size: PRODUCT_PAGE_SIZE,
    };
    if (q.trim()) params.search = q.trim();
    if (low) {
      params.low_stock = "true";
      params.stock_threshold = "5";
    }

    Promise.all([
      admin.products.list(params),
      categories.list(),
      colorsApi.list(),
      sizesApi.list(),
      admin.promotions.list(),
    ])
      .then(
        ([productsRes, categoriesRes, colorsRes, sizesRes, promotionsRes]) => {
          const pdata = productsRes.data as {
            results?: Product[];
            count?: number;
          };
          setProducts(pdata.results || (productsRes.data as Product[]) || []);
          setProductCount(pdata.count ?? 0);
          setCategoriesList(categoriesRes.data.results || categoriesRes.data);
          setColorsList(colorsRes.data.results || colorsRes.data);
          const rawSizes: Size[] = sizesRes.data.results || sizesRes.data;
          setSizesList(
            [...rawSizes].sort((a, b) => (a.order ?? 0) - (b.order ?? 0)),
          );
          const prom = promotionsRes.data as
            | { results?: typeof promotionsList }
            | typeof promotionsList;
          setPromotionsList(Array.isArray(prom) ? prom : (prom.results ?? []));
        },
      )
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  const reloadSizes = async () => {
    const res = await sizesApi.list();
    const rawSizes: Size[] = res.data.results || res.data;
    setSizesList([...rawSizes].sort((a, b) => (a.order ?? 0) - (b.order ?? 0)));
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (showVariantModal && selectedProduct?.id) {
      setVariantImageIndex(0);
    }
  }, [showVariantModal, selectedProduct?.id]);

  const applyProductFilters = (e: React.FormEvent) => {
    e.preventDefault();
    setProductPage(1);
    loadData(searchQuery, lowStockOnly, 1);
  };

  const handleSubmitProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const formDataToSend = new FormData();
      formDataToSend.append("name", formData.name);
      formDataToSend.append("description", formData.description);
      formDataToSend.append("price", formData.price);
      formDataToSend.append("category_id", formData.category_id.toString());
      if (formData.promotion_id != null) {
        formDataToSend.append("promotion_id", String(formData.promotion_id));
      } else if (editingProduct) {
        formDataToSend.append("clear_promotion", "true");
      }
      if (formData.upload_images && formData.upload_images.length > 0) {
        formData.upload_images.forEach((file) => {
          formDataToSend.append("upload_images", file);
        });
      }
      if (formData.size_chart) {
        formDataToSend.append("size_chart_upload", formData.size_chart);
      }
      if (formData.clear_size_chart && !formData.size_chart) {
        formDataToSend.append("clear_size_chart", "true");
      }

      if (editingProduct) {
        if (formData.delete_image_ids && formData.delete_image_ids.length > 0) {
          await Promise.all(
            formData.delete_image_ids.map((imgId) =>
              admin.products.deleteImage(imgId),
            ),
          );
        }
        await admin.products.update(editingProduct.id, formDataToSend);
      } else {
        await admin.products.create(formDataToSend);
      }

      setShowProductModal(false);
      setEditingProduct(null);
      setFormData({
        name: "",
        description: "",
        price: "",
        category_id: 0,
        promotion_id: null,
        upload_images: [],
        size_chart: null,
        clear_size_chart: false,
        delete_image_ids: [],
      });
      loadData();
    } catch (error) {
      alert(getApiErrorMessage(error));
    }
  };

  const handleEditProduct = async (product: Product) => {
    try {
      const res = await admin.products.get(product.id);
      const full = res.data as Product;
      setEditingProduct(full);
      setFormData({
        name: full.name,
        description: full.description,
        price: full.price,
        category_id: full.category.id,
        promotion_id: full.promotion?.id || null,
        upload_images: [],
        size_chart: null,
        clear_size_chart: false,
        delete_image_ids: [],
      });
      setShowProductModal(true);
    } catch (error) {
      alert(getApiErrorMessage(error, "Không tải được chi tiết sản phẩm."));
    }
  };

  const handleSizeChartUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      setFormData((prev) => ({ ...prev, size_chart: e.target.files![0] }));
    }
  };

  const handleDeleteProduct = async (id: number) => {
    if (confirm("Bạn có chắc chắn muốn xóa sản phẩm này?")) {
      try {
        await admin.products.delete(id);
        loadData();
      } catch {
        alert("Có lỗi xảy ra!");
      }
    }
  };

  const openAddProductModal = () => {
    setEditingProduct(null);
    setFormData({
      name: "",
      description: "",
      price: "",
      category_id: 0,
      promotion_id: null,
      upload_images: [],
      size_chart: null,
      clear_size_chart: false,
      delete_image_ids: [],
    });
    setShowProductModal(true);
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const picked = e.target.files ? Array.from(e.target.files) : [];
    e.target.value = "";
    if (picked.length === 0) return;
    setFormData((prev) => ({
      ...prev,
      upload_images: [...(prev.upload_images ?? []), ...picked],
    }));
  };

  // ── Size Manager trong product form ──
  const handleAddSize = async () => {
    const name = sizeManagerName.trim();
    if (!name) {
      setSizeManagerError("Vui lòng nhập tên size.");
      return;
    }
    setSizeManagerError("");
    setSizeManagerLoading(true);
    try {
      await admin.sizes.create({ name, order: sizeManagerOrder });
      await reloadSizes();
      setSizeManagerName("");
      setSizeManagerOrder(0);
    } catch (error) {
      setSizeManagerError(getApiErrorMessage(error, "Không thể thêm size."));
    } finally {
      setSizeManagerLoading(false);
    }
  };

  const startEditSize = (s: Size) => {
    setEditingSizeId(s.id);
    setEditingSizeName(s.name);
    setEditingSizeOrder(s.order);
  };

  const cancelEditSize = () => {
    setEditingSizeId(null);
    setEditingSizeName("");
    setEditingSizeOrder(0);
  };

  const handleUpdateSize = async (id: number) => {
    const name = editingSizeName.trim();
    if (!name) return;
    setSizeManagerLoading(true);
    try {
      await admin.sizes.update(id, { name, order: editingSizeOrder });
      await reloadSizes();
      cancelEditSize();
    } catch (error) {
      alert(getApiErrorMessage(error, "Không thể cập nhật size."));
    } finally {
      setSizeManagerLoading(false);
    }
  };

  const handleDeleteSize = async (id: number) => {
    if (
      !confirm("Xóa size này? Các biến thể dùng size này có thể bị ảnh hưởng.")
    )
      return;
    setDeletingSizeId(id);
    try {
      await admin.sizes.delete(id);
      await reloadSizes();
    } catch (error) {
      alert(getApiErrorMessage(error, "Không thể xóa size."));
    } finally {
      setDeletingSizeId(null);
    }
  };

  // ── Variant modal helpers ──
  const closeVariantModal = () => {
    setShowVariantModal(false);
    loadData();
  };

  const syncVariantModalFromServer = async (productId: number) => {
    const [detailRes, varRes] = await Promise.all([
      admin.products.get(productId),
      variantsApi.list({ product: productId }),
    ]);
    const detail = detailRes.data as Product;
    setSelectedProduct((prev) =>
      prev && prev.id === productId ? { ...prev, ...detail } : prev,
    );
    setProductVariants(varRes.data.results || varRes.data);
  };

  const openVariantModal = async (product: Product) => {
    setEditingVariant(null);
    setVariantForm({ color_id: 0, size_id: 0, stock: 0, price: null });
    setWarehouseDelta("");
    setSelectedProduct(product);
    setVariantImageIndex(0);
    setShowQuickAddColor(false);
    setShowQuickAddSize(false);
    setQuickAddColorName("");
    setQuickAddColorCode("#000000");
    setQuickAddSizeName("");
    setQuickAddSizeOrder(0);
    setQuickAddColorError("");
    setQuickAddSizeError("");
    setEditingOrders({});

    try {
      const [detailRes, varRes] = await Promise.all([
        admin.products.get(product.id),
        variantsApi.list({ product: product.id }),
      ]);
      const detail = detailRes.data as Product;
      setSelectedProduct({ ...product, ...detail });
      setProductVariants(varRes.data.results || varRes.data);
    } catch (err) {
      console.error(err);
      try {
        const res = await variantsApi.list({ product: product.id });
        setProductVariants(res.data.results || res.data);
      } catch {
        setProductVariants([]);
      }
    }

    setShowVariantModal(true);
  };

  const handleQuickAddColor = async () => {
    const name = quickAddColorName.trim();
    if (!name) {
      setQuickAddColorError("Vui lòng nhập tên màu.");
      return;
    }
    setQuickAddColorError("");
    setQuickAddColorLoading(true);
    try {
      await admin.colors.create({ name, code: quickAddColorCode });
      const res = await colorsApi.list();
      setColorsList(res.data.results || res.data);
      setQuickAddColorName("");
      setQuickAddColorCode("#000000");
      setShowQuickAddColor(false);
    } catch (error) {
      setQuickAddColorError(getApiErrorMessage(error, "Không thể thêm màu."));
    } finally {
      setQuickAddColorLoading(false);
    }
  };

  const handleQuickAddSize = async () => {
    const name = quickAddSizeName.trim();
    if (!name) {
      setQuickAddSizeError("Vui lòng nhập tên size.");
      return;
    }
    setQuickAddSizeError("");
    setQuickAddSizeLoading(true);
    try {
      await admin.sizes.create({ name, order: quickAddSizeOrder });
      const res = await sizesApi.list();
      const rawSizes: Size[] = res.data.results || res.data;
      setSizesList(
        [...rawSizes].sort((a, b) => (a.order ?? 0) - (b.order ?? 0)),
      );
      setQuickAddSizeName("");
      setQuickAddSizeOrder(0);
      setShowQuickAddSize(false);
    } catch (error) {
      setQuickAddSizeError(getApiErrorMessage(error, "Không thể thêm size."));
    } finally {
      setQuickAddSizeLoading(false);
    }
  };

  const handleSaveOrder = async (s: Size, newOrder: number) => {
    setSavingOrderId(s.id);
    try {
      await admin.sizes.update(s.id, { name: s.name, order: newOrder });
      const res = await sizesApi.list();
      const rawSizes: Size[] = res.data.results || res.data;
      setSizesList(
        [...rawSizes].sort((a, b) => (a.order ?? 0) - (b.order ?? 0)),
      );
      setEditingOrders((prev) => {
        const next = { ...prev };
        delete next[s.id];
        return next;
      });
    } catch {
      alert("Không thể lưu thứ tự size.");
    } finally {
      setSavingOrderId(null);
    }
  };

  const handleSubmitVariant = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProduct) return;
    if (!canManageVariantStock) return;

    const variantPayload = {
      product_id: selectedProduct.id,
      color_id: variantForm.color_id,
      size_id: variantForm.size_id,
      stock: variantForm.stock,
      price: variantForm.price,
    };

    try {
      if (editingVariant) {
        await admin.variants.update(editingVariant.id, variantPayload);
      } else {
        await admin.variants.create(variantPayload);
      }

      await syncVariantModalFromServer(selectedProduct.id);
      setVariantForm({ color_id: 0, size_id: 0, stock: 0, price: null });
      setWarehouseDelta("");
      setEditingVariant(null);
    } catch (error: unknown) {
      console.error("Variant error:", (error as any)?.response?.data);
      const msg = (error as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      alert(msg || "Có lỗi xảy ra!");
    }
  };

  const handleEditVariant = (variant: Variant) => {
    setEditingVariant(variant);
    setWarehouseDelta("");
    setVariantForm({
      color_id: variant.color.id,
      size_id: variant.size.id,
      stock: variant.stock,
      price: variant.price ?? null,
    });
    window.setTimeout(() => {
      variantFormPanelRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
      variantColorSelectRef.current?.focus({ preventScroll: false });
    }, 0);
  };

  const applyWarehouseDelta = () => {
    const raw = warehouseDelta.trim();
    if (raw === "") return;
    const d = Number(raw);
    if (Number.isNaN(d) || !Number.isFinite(d)) {
      alert("Nhập số hợp lệ (có thể âm khi điều chỉnh giảm).");
      return;
    }
    setVariantForm((f) => ({
      ...f,
      stock: Math.max(0, Math.round(f.stock + d)),
    }));
    setWarehouseDelta("");
  };

  const bumpStock = (delta: number) => {
    setVariantForm((f) => ({ ...f, stock: Math.max(0, f.stock + delta) }));
  };

  const handleDeleteVariant = async (id: number) => {
    if (confirm("Bạn có chắc chắn muốn xóa biến thể này?")) {
      try {
        await admin.variants.delete(id);
        if (selectedProduct) {
          await syncVariantModalFromServer(selectedProduct.id);
        }
      } catch {
        alert("Có lỗi xảy ra!");
      }
    }
  };

  if (loading)
    return (
      <AdminLayout>
        <div className="loading">Loading...</div>
      </AdminLayout>
    );

  const variantGallery =
    showVariantModal && selectedProduct
      ? productImageGallery(selectedProduct)
      : [];
  const variantMainSrc =
    variantGallery[variantImageIndex] ?? variantGallery[0] ?? "";

  return (
    <AdminLayout>
      <div className="admin-page">
        <div className="page-header">
          <div>
            <h3>Quản lý sản phẩm</h3>
            <p className="page-header-desc">
              {canManageVariantStock ? (
                <>
                  Tồn kho theo màu &amp; size không hiện trên bảng — bấm nút tím{" "}
                  <strong className="page-header-desc-em">Biến thể</strong> trên
                  từng sản phẩm để nhập kho / chỉnh số lượng.
                </>
              ) : (
                <>
                  Bấm <strong className="page-header-desc-em">Biến thể</strong>{" "}
                  để <strong>xem</strong> tồn theo màu &amp; size (nhân viên chỉ
                  xem).
                </>
              )}
            </p>
          </div>
          <button className="btn-primary" onClick={openAddProductModal}>
            + Thêm sản phẩm
          </button>
        </div>

        <form className="admin-filters" onSubmit={applyProductFilters}>
          <input
            type="search"
            placeholder="Tìm theo tên, mô tả, danh mục…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="admin-filters__search"
          />
          <label className="admin-inlineCheck">
            <input
              type="checkbox"
              checked={lowStockOnly}
              onChange={(e) => setLowStockOnly(e.target.checked)}
            />{" "}
            Chỉ SP có biến thể tồn ≤ 5
          </label>
          <button type="submit" className="btn-primary">
            Lọc
          </button>
        </form>

        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Tên sản phẩm</th>
              <th>Danh mục</th>
              <th>Giá</th>
              <th>Biến thể</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {products.map((product) => (
              <tr key={product.id}>
                <td>{product.id}</td>
                <td>{product.name}</td>
                <td>{product.category.name}</td>
                <td>{Number(product.price).toLocaleString("vi-VN")}đ</td>
                <td>
                  <button
                    type="button"
                    className="btn-variant"
                    onClick={() => openVariantModal(product)}
                  >
                    <span className="btn-variant__text">Biến thể</span>
                    <span className="btn-variant__count">
                      {product.variants?.length ?? 0}
                    </span>
                  </button>
                </td>
                <td>
                  <button
                    className="btn-edit"
                    onClick={() => handleEditProduct(product)}
                  >
                    Sửa
                  </button>
                  <button
                    className="btn-delete"
                    onClick={() => handleDeleteProduct(product.id)}
                  >
                    Xóa
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Pagination sản phẩm */}
        {productCount > PRODUCT_PAGE_SIZE && (
          <div className="admin-pagination">
            <button
              type="button"
              className="btn-secondary"
              disabled={productPage <= 1}
              onClick={() => {
                const newPage = productPage - 1;
                setProductPage(newPage);
                loadData(searchQuery, lowStockOnly, newPage);
              }}
            >
              ← Trước
            </button>
            <span className="numPages">
              Trang {productPage} /{" "}
              {Math.ceil(productCount / PRODUCT_PAGE_SIZE)}
            </span>
            <button
              type="button"
              className="btn-secondary"
              disabled={
                productPage >= Math.ceil(productCount / PRODUCT_PAGE_SIZE)
              }
              onClick={() => {
                const newPage = productPage + 1;
                setProductPage(newPage);
                loadData(searchQuery, lowStockOnly, newPage);
              }}
            >
              Sau →
            </button>
          </div>
        )}

        {/* ── Product Modal ── */}
        {showProductModal && (
          <div className="modal-overlay">
            <div className="modal product-modal">
              <div className="product-modal__header">
                <h3>{editingProduct ? "Sửa sản phẩm" : "Thêm sản phẩm"}</h3>
              </div>

              <form onSubmit={handleSubmitProduct} className="product-form">
                {/* Cột trái */}
                <div className="product-form__col">
                  <div className="product-form__section-label">
                    Thông tin cơ bản
                  </div>

                  <div className="form-group">
                    <label>Tên sản phẩm</label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) =>
                        setFormData({ ...formData, name: e.target.value })
                      }
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label>Mô tả</label>
                    <textarea
                      value={formData.description}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          description: e.target.value,
                        })
                      }
                      required
                    />
                  </div>

                  <div className="product-form__row2">
                    <div className="form-group">
                      <label>Giá (đ)</label>
                      <input
                        type="number"
                        step="1"
                        value={formData.price}
                        onChange={(e) =>
                          setFormData({ ...formData, price: e.target.value })
                        }
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label>Danh mục</label>
                      <select
                        value={formData.category_id}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            category_id: Number(e.target.value),
                          })
                        }
                        required
                      >
                        <option value="">Chọn danh mục</option>
                        {categoriesList.map((cat) => (
                          <option key={cat.id} value={cat.id}>
                            {cat.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="form-group">
                    <label>Khuyến mãi</label>
                    <select
                      value={formData.promotion_id ?? ""}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          promotion_id: e.target.value
                            ? Number(e.target.value)
                            : null,
                        })
                      }
                    >
                      <option value="">Không có khuyến mãi</option>
                      {promotionsList
                        .filter(
                          (p) => p.is_active || p.id === formData.promotion_id,
                        )
                        .map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.name} (-{p.discount_percent}%)
                            {!p.is_active ? " [Hết hạn]" : ""}
                          </option>
                        ))}
                    </select>
                  </div>
                </div>

                {/* Cột phải */}
                <div className="product-form__col">
                  {/* ── Bảng kích thước ── */}
                  <div className="product-form__section-label">
                    Bảng kích thước
                  </div>

                  {/* Ảnh size chart */}
                  <div className="form-group">
                    <label>Ảnh bảng size</label>

                    {editingProduct?.size_chart &&
                      !formData.clear_size_chart &&
                      !formData.size_chart && (
                        <div className="size-chart-preview">
                          <img
                            src={editingProduct.size_chart}
                            alt="Bảng size hiện tại"
                            className="size-chart-preview__img"
                          />
                          <div className="size-chart-preview__footer">
                            <span className="size-chart-preview__hint">
                              Ảnh hiện tại — chọn file mới để thay thế
                            </span>
                            <button
                              type="button"
                              className="btn-delete btn-sm"
                              onClick={() =>
                                setFormData((prev) => ({
                                  ...prev,
                                  clear_size_chart: true,
                                }))
                              }
                            >
                              Xóa ảnh
                            </button>
                          </div>
                        </div>
                      )}

                    {formData.clear_size_chart && !formData.size_chart && (
                      <div className="size-chart-deleted-notice">
                        <span>Bảng size sẽ bị xóa khi lưu.</span>
                        <button
                          type="button"
                          className="size-chart-deleted-notice__undo"
                          onClick={() =>
                            setFormData((prev) => ({
                              ...prev,
                              clear_size_chart: false,
                            }))
                          }
                        >
                          Hoàn tác
                        </button>
                      </div>
                    )}

                    {formData.size_chart && (
                      <div className="size-chart-preview">
                        <img
                          src={URL.createObjectURL(formData.size_chart)}
                          alt="Preview bảng size"
                          className="size-chart-preview__img"
                        />
                        <div className="size-chart-preview__footer">
                          <span className="size-chart-preview__hint">
                            {formData.size_chart.name}
                          </span>
                          <button
                            type="button"
                            className="btn-delete btn-sm"
                            onClick={() =>
                              setFormData((prev) => ({
                                ...prev,
                                size_chart: null,
                              }))
                            }
                          >
                            Bỏ chọn
                          </button>
                        </div>
                      </div>
                    )}

                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleSizeChartUpload}
                    />
                  </div>

                  {/* Hình ảnh sản phẩm */}
                  <div className="form-group">
                    <label>Hình ảnh sản phẩm</label>

                    {editingProduct &&
                      (() => {
                        const existingImages = (
                          editingProduct.images ?? []
                        ).filter(
                          (img) =>
                            img.image &&
                            !formData.delete_image_ids?.includes(img.id),
                        );
                        return existingImages.length > 0 ? (
                          <div className="image-list">
                            <div className="image-preview-list">
                              {existingImages.map((img) => (
                                <div
                                  key={img.id}
                                  className="image-preview-item"
                                >
                                  <img src={img.image!} alt="" />
                                  <button
                                    type="button"
                                    className="image-preview-item__del"
                                    onClick={() =>
                                      setFormData((prev) => ({
                                        ...prev,
                                        delete_image_ids: [
                                          ...(prev.delete_image_ids ?? []),
                                          img.id,
                                        ],
                                      }))
                                    }
                                  >
                                    Xóa
                                  </button>
                                </div>
                              ))}
                            </div>
                          </div>
                        ) : null;
                      })()}

                    <input
                      type="file"
                      accept="image/*"
                      multiple
                      onChange={handleImageUpload}
                    />

                    {formData.upload_images &&
                      formData.upload_images.length > 0 && (
                        <div className="image-preview-list image-preview-list--new">
                          {formData.upload_images.map((file, index) => (
                            <div key={index} className="image-preview-item">
                              <img
                                src={URL.createObjectURL(file)}
                                alt={`Preview ${index}`}
                              />
                              <button
                                type="button"
                                className="image-preview-item__del"
                                onClick={() =>
                                  setFormData((prev) => ({
                                    ...prev,
                                    upload_images: (
                                      prev.upload_images ?? []
                                    ).filter((_, i) => i !== index),
                                  }))
                                }
                              >
                                Xóa
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                  </div>
                </div>

                {/* Actions */}
                <div className="form-actions product-form__actions">
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setShowProductModal(false)}
                  >
                    Hủy
                  </button>
                  <button type="submit" className="btn-primary">
                    {editingProduct ? "Lưu thay đổi" : "Thêm sản phẩm"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ── Variant Modal ── */}
        {showVariantModal && selectedProduct && (
          <div
            className="modal-overlay variant-modal-overlay"
            role="presentation"
            onClick={(e) => {
              if (e.target === e.currentTarget) closeVariantModal();
            }}
          >
            <div
              className="modal modal-large variant-modal"
              role="dialog"
              aria-modal="true"
              aria-labelledby="variant-modal-title"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="variant-modal__layout">
                {/* Cột trái — ảnh + thumbnail */}
                <aside className="variant-modal__media">
                  {variantMainSrc ? (
                    <>
                      <div className="variant-modal__preview-main">
                        <img
                          src={variantMainSrc}
                          alt=""
                          loading="lazy"
                          decoding="async"
                        />
                      </div>
                      {variantGallery.length > 1 && (
                        <div
                          className="variant-modal__thumbs"
                          role="tablist"
                          aria-label="Ảnh sản phẩm"
                        >
                          {variantGallery.map((url, idx) => (
                            <button
                              key={`${url}-${idx}`}
                              type="button"
                              role="tab"
                              aria-selected={variantImageIndex === idx}
                              className={`variant-modal__thumb ${variantImageIndex === idx ? "is-active" : ""}`}
                              onClick={() => setVariantImageIndex(idx)}
                            >
                              <img src={url} alt="" loading="lazy" />
                            </button>
                          ))}
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="variant-modal__preview-placeholder">
                      <span>Chưa có ảnh</span>
                      <small>Thêm ảnh khi sửa sản phẩm</small>
                    </div>
                  )}
                </aside>

                {/* Cột phải */}
                <div className="variant-modal__content">
                  <div className="variant-modal__header">
                    <div>
                      <h3 id="variant-modal-title">
                        {canManageVariantStock
                          ? "Biến thể & nhập kho"
                          : "Biến thể (chỉ xem tồn)"}
                      </h3>
                      <p className="variant-modal__product-name">
                        {selectedProduct.name}
                      </p>
                    </div>
                    <span className="variant-modal__badge" title="Số biến thể">
                      {productVariants.length} SKU
                    </span>
                  </div>

                  <div className="variant-modal__body">
                    {!canManageVariantStock && (
                      <div
                        className="admin-banner variant-modal__staff-readonly-banner"
                        role="status"
                      >
                        <strong>Nhân viên:</strong> chỉ xem tồn theo màu &amp;
                        size. Thêm/sửa/xóa biến thể và nhập kho do{" "}
                        <strong>quản trị viên</strong> thực hiện.
                      </div>
                    )}

                    {canManageVariantStock && (
                      <section
                        className="variant-modal__panel variant-modal__panel--quick"
                        aria-label="Thêm nhanh màu và size"
                      >
                        <h4 className="variant-modal__panel-title">
                          Mở rộng danh mục dùng chung
                        </h4>
                        <p className="variant-modal__hint">
                          Thêm màu hoặc size mới để chọn ở form bên dưới (áp
                          dụng cho toàn cửa hàng).
                        </p>
                        <div className="variant-quick-grid">
                          {/* Quick-add màu */}
                          <div className="variant-quick-card">
                            <div className="variant-quick-card__label">
                              <span
                                className="variant-quick-card__dot"
                                style={{ background: "#6366f1" }}
                                aria-hidden
                              />
                              Màu sắc
                            </div>
                            {!showQuickAddColor ? (
                              <button
                                type="button"
                                className="variant-quick-card__trigger"
                                onClick={() => setShowQuickAddColor(true)}
                              >
                                + Thêm màu mới
                              </button>
                            ) : (
                              <div className="variant-quick-card__form">
                                <input
                                  type="text"
                                  placeholder="Tên màu (vd: Đỏ đô)"
                                  value={quickAddColorName}
                                  onChange={(e) => {
                                    setQuickAddColorName(e.target.value);
                                    setQuickAddColorError("");
                                  }}
                                  aria-label="Tên màu"
                                />
                                <label className="variant-quick-card__colorPick">
                                  <span>Mã</span>
                                  <input
                                    type="color"
                                    value={quickAddColorCode}
                                    onChange={(e) =>
                                      setQuickAddColorCode(e.target.value)
                                    }
                                    title="Chọn màu"
                                  />
                                </label>
                                {quickAddColorError && (
                                  <p className="variant-quick-card__error">
                                    {quickAddColorError}
                                  </p>
                                )}
                                <div className="variant-quick-card__actions">
                                  <button
                                    type="button"
                                    className="btn-primary btn-sm"
                                    onClick={handleQuickAddColor}
                                    disabled={quickAddColorLoading}
                                  >
                                    {quickAddColorLoading ? "Đang lưu…" : "Lưu"}
                                  </button>
                                  <button
                                    type="button"
                                    className="btn-secondary btn-sm"
                                    onClick={() => {
                                      setShowQuickAddColor(false);
                                      setQuickAddColorError("");
                                    }}
                                  >
                                    Hủy
                                  </button>
                                </div>
                              </div>
                            )}
                          </div>

                          {/* Quick-add size */}
                          <div className="variant-quick-card">
                            <div className="variant-quick-card__label">
                              <span
                                className="variant-quick-card__dot"
                                style={{ background: "#0ea5e9" }}
                                aria-hidden
                              />
                              Kích thước
                            </div>
                            {!showQuickAddSize ? (
                              <button
                                type="button"
                                className="variant-quick-card__trigger"
                                onClick={() => setShowQuickAddSize(true)}
                              >
                                + Thêm size mới
                              </button>
                            ) : (
                              <div className="variant-quick-card__form variant-quick-card__form--stack">
                                <input
                                  type="text"
                                  placeholder="Tên size (vd: M, 42)"
                                  value={quickAddSizeName}
                                  onChange={(e) => {
                                    setQuickAddSizeName(e.target.value);
                                    setQuickAddSizeError("");
                                  }}
                                  aria-label="Tên size"
                                />
                                <div className="variant-quick-card__order-row">
                                  <label>Thứ tự:</label>
                                  <input
                                    type="number"
                                    value={quickAddSizeOrder}
                                    min={0}
                                    onChange={(e) =>
                                      setQuickAddSizeOrder(
                                        Number(e.target.value),
                                      )
                                    }
                                    className="variant-quick-card__order-input"
                                    aria-label="Thứ tự hiển thị"
                                  />
                                  <span className="variant-quick-card__order-hint">
                                    số nhỏ = trước
                                  </span>
                                </div>
                                {quickAddSizeError && (
                                  <p className="variant-quick-card__error">
                                    {quickAddSizeError}
                                  </p>
                                )}
                                <div className="variant-quick-card__actions">
                                  <button
                                    type="button"
                                    className="btn-primary btn-sm"
                                    onClick={handleQuickAddSize}
                                    disabled={quickAddSizeLoading}
                                  >
                                    {quickAddSizeLoading ? "Đang lưu…" : "Lưu"}
                                  </button>
                                  <button
                                    type="button"
                                    className="btn-secondary btn-sm"
                                    onClick={() => {
                                      setShowQuickAddSize(false);
                                      setQuickAddSizeError("");
                                    }}
                                  >
                                    Hủy
                                  </button>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </section>
                    )}

                    {canManageVariantStock && (
                      <section
                        ref={variantFormPanelRef}
                        className="variant-modal__panel variant-modal__panel--form"
                        aria-label="Thêm hoặc sửa biến thể"
                      >
                        <h4 className="variant-modal__panel-title">
                          {editingVariant
                            ? "Cập nhật biến thể & tồn"
                            : "Thêm biến thể mới"}
                        </h4>
                        <p className="variant-stock-workflow-hint">
                          {editingVariant
                            ? "Chỉnh tồn kho trực tiếp hoặc dùng Nhập thêm rồi Lưu."
                            : "Chọn màu, size và tồn ban đầu; sau này mở lại để nhập thêm hàng."}
                        </p>
                        <form
                          onSubmit={handleSubmitVariant}
                          className="variant-form-compact"
                        >
                          <div className="variant-form-compact__grid">
                            <div className="form-group">
                              <label htmlFor="vf-color">Màu</label>
                              <select
                                ref={variantColorSelectRef}
                                id="vf-color"
                                value={variantForm.color_id || ""}
                                onChange={(e) =>
                                  setVariantForm({
                                    ...variantForm,
                                    color_id: Number(e.target.value),
                                  })
                                }
                                required
                              >
                                <option value="" disabled>
                                  Chọn màu
                                </option>
                                {colorsList.map((c) => (
                                  <option key={c.id} value={c.id}>
                                    {c.name}
                                  </option>
                                ))}
                              </select>
                            </div>
                            <div className="form-group">
                              <label htmlFor="vf-size">Size</label>
                              <select
                                id="vf-size"
                                value={variantForm.size_id || ""}
                                onChange={(e) =>
                                  setVariantForm({
                                    ...variantForm,
                                    size_id: Number(e.target.value),
                                  })
                                }
                                required
                              >
                                <option value="" disabled>
                                  Chọn size
                                </option>
                                {sizesList.map((s) => (
                                  <option key={s.id} value={s.id}>
                                    {s.name} (#{s.order})
                                  </option>
                                ))}
                              </select>
                            </div>
                            <div className="form-group form-group--stock">
                              <label htmlFor="vf-stock">
                                {editingVariant
                                  ? "Tồn kho (sau cập nhật)"
                                  : "Tồn kho ban đầu"}
                              </label>
                              <input
                                id="vf-stock"
                                type="number"
                                min="0"
                                inputMode="numeric"
                                value={variantForm.stock}
                                onChange={(e) =>
                                  setVariantForm({
                                    ...variantForm,
                                    stock: Math.max(
                                      0,
                                      Number(e.target.value) || 0,
                                    ),
                                  })
                                }
                                required
                              />
                              <div
                                className="variant-stock-quick"
                                role="group"
                                aria-label="Cộng nhanh vào tồn"
                              >
                                <span className="variant-stock-quick__label">
                                  Cộng nhanh:
                                </span>
                                {[1, 5, 10, 50, 100].map((n) => (
                                  <button
                                    key={n}
                                    type="button"
                                    className="variant-stock-quick__btn"
                                    onClick={() => bumpStock(n)}
                                  >
                                    +{n}
                                  </button>
                                ))}
                              </div>
                              <div className="variant-stock-inbound">
                                <label htmlFor="vf-warehouse-delta">
                                  Nhập thêm vào kho
                                </label>
                                <div className="variant-stock-inbound__row">
                                  <input
                                    id="vf-warehouse-delta"
                                    type="number"
                                    inputMode="numeric"
                                    placeholder="VD: 20 hoặc -3"
                                    value={warehouseDelta}
                                    onChange={(e) =>
                                      setWarehouseDelta(e.target.value)
                                    }
                                  />
                                  <button
                                    type="button"
                                    className="btn-secondary btn-sm"
                                    onClick={applyWarehouseDelta}
                                  >
                                    Áp dụng
                                  </button>
                                </div>
                                <p className="variant-stock-inbound__hint">
                                  Số dương = nhập thêm; số âm = trừ tồn (kiểm
                                  kê). Bấm Áp dụng để cộng vào ô tồn phía trên,
                                  rồi Lưu.
                                </p>
                              </div>
                            </div>
                            <div className="form-group">
                              <label htmlFor="vf-price">
                                Giá riêng cho size này
                              </label>
                              <p className="form-hint">
                                Để trống = dùng giá sản phẩm (
                                {Number(selectedProduct.price).toLocaleString(
                                  "vi-VN",
                                )}
                                đ).
                              </p>
                              <input
                                id="vf-price"
                                type="number"
                                min="0"
                                inputMode="numeric"
                                placeholder={`Mặc định: ${Number(selectedProduct.price).toLocaleString("vi-VN")}đ`}
                                value={variantForm.price ?? ""}
                                onChange={(e) =>
                                  setVariantForm({
                                    ...variantForm,
                                    price:
                                      e.target.value === ""
                                        ? null
                                        : Math.max(0, Number(e.target.value)),
                                  })
                                }
                              />
                            </div>
                            <div className="variant-form-compact__submit">
                              <button
                                type="submit"
                                className="btn-primary variant-form-compact__btn-main"
                              >
                                {editingVariant
                                  ? "Lưu thay đổi"
                                  : "Thêm biến thể"}
                              </button>
                              {editingVariant && (
                                <button
                                  type="button"
                                  className="btn-secondary"
                                  onClick={() => {
                                    setEditingVariant(null);
                                    setWarehouseDelta("");
                                    setVariantForm({
                                      color_id: 0,
                                      size_id: 0,
                                      stock: 0,
                                      price: null,
                                    });
                                  }}
                                >
                                  Hủy sửa
                                </button>
                              )}
                            </div>
                          </div>
                        </form>
                      </section>
                    )}

                    <section
                      className="variant-modal__panel"
                      aria-label="Danh sách biến thể"
                    >
                      <div className="variant-modal__list-head">
                        <h4 className="variant-modal__panel-title variant-modal__panel-title--inline">
                          {canManageVariantStock
                            ? "Danh sách"
                            : "Danh sách (màu · size · tồn)"}
                        </h4>
                        <p className="variant-modal__legend">
                          Ô tồn:{" "}
                          <span className="variant-legend-tag variant-legend-tag--ok">
                            đủ
                          </span>
                          <span className="variant-legend-tag variant-legend-tag--low">
                            thấp ≤5
                          </span>
                          <span className="variant-legend-tag variant-legend-tag--empty">
                            hết
                          </span>
                        </p>
                      </div>
                      <div className="variant-table-wrap">
                        <table className="data-table variant-table">
                          <thead>
                            <tr>
                              <th>Màu</th>
                              <th>Size</th>
                              <th>Giá riêng</th>
                              <th>Tồn</th>
                              {canManageVariantStock && (
                                <th className="variant-table__actions">
                                  Thao tác
                                </th>
                              )}
                            </tr>
                          </thead>
                          <tbody>
                            {productVariants.length === 0 ? (
                              <tr>
                                <td colSpan={canManageVariantStock ? 5 : 4}>
                                  <div className="variant-empty">
                                    <p className="variant-empty__title">
                                      Chưa có biến thể
                                    </p>
                                    <p className="variant-empty__text">
                                      {canManageVariantStock
                                        ? "Chọn màu, size và tồn kho ở form phía trên rồi bấm Thêm biến thể."
                                        : "Chưa có SKU — quản trị viên thêm biến thể và tồn kho."}
                                    </p>
                                  </div>
                                </td>
                              </tr>
                            ) : (
                              productVariants.map((v) => (
                                <tr key={v.id}>
                                  <td>
                                    <div className="variant-cell-color">
                                      <span
                                        className="color-dot color-dot--lg"
                                        style={{
                                          backgroundColor: v.color.code,
                                        }}
                                        title={v.color.name}
                                      />
                                      <span>{v.color.name}</span>
                                    </div>
                                  </td>
                                  <td>
                                    <span className="variant-size-pill">
                                      {v.size.name}
                                    </span>
                                  </td>
                                  <td>
                                    {v.price != null ? (
                                      Number(v.price).toLocaleString("vi-VN") +
                                      "đ"
                                    ) : (
                                      <span className="variant-price-default">
                                        = giá SP
                                      </span>
                                    )}
                                  </td>
                                  <td>
                                    <span
                                      className={`variant-stock variant-stock--${variantStockTone(v.stock)}`}
                                    >
                                      {v.stock}
                                    </span>
                                  </td>
                                  {canManageVariantStock && (
                                    <td className="variant-table__actions">
                                      <button
                                        type="button"
                                        className="btn-edit btn-edit--compact"
                                        onClick={() => handleEditVariant(v)}
                                      >
                                        Sửa
                                      </button>
                                      <button
                                        type="button"
                                        className="btn-delete btn-delete--compact"
                                        onClick={() =>
                                          handleDeleteVariant(v.id)
                                        }
                                      >
                                        Xóa
                                      </button>
                                    </td>
                                  )}
                                </tr>
                              ))
                            )}
                          </tbody>
                        </table>
                      </div>
                    </section>
                  </div>
                </div>
              </div>

              <div className="variant-modal__footer">
                <button
                  type="button"
                  className="btn-secondary variant-modal__close"
                  onClick={() => closeVariantModal()}
                >
                  Đóng cửa sổ
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
