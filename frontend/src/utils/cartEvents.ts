/** Báo cho Header (và chỗ khác) cập nhật số lượng giỏ sau khi thêm/sửa/xóa/thanh toán. */
export const CART_UPDATED_EVENT = 'fashion_store_cart_updated';

export function notifyCartUpdated(): void {
  window.dispatchEvent(new CustomEvent(CART_UPDATED_EVENT));
}
