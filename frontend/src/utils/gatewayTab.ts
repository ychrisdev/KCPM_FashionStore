/**
 * Mở tab trống đồng bộ trong handler click, rồi gán payment_url sau khi API trả về.
 * Giúp người dùng thấy phản hồi ngay (tab mới) thay vì chờ lâu rồi mới chuyển trang.
 */
export function openBlankGatewayTab(): Window | null {
  try {
    return window.open("about:blank", "_blank");
  } catch {
    return null;
  }
}

/** Gán URL cổng thanh toán vào tab đã mở. Trả về true nếu đã gán (giữ tab hiện tại). */
export function assignGatewayUrl(tab: Window | null, url: string): boolean {
  if (!url || !tab || tab.closed) return false;
  try {
    tab.location.href = url;
    try {
      tab.opener = null;
    } catch {
      /* một số trình duyệt chặn gán opener */
    }
    return true;
  } catch {
    return false;
  }
}

export function closeGatewayTab(tab: Window | null): void {
  if (!tab || tab.closed) return;
  try {
    tab.close();
  } catch {
    /* ignore */
  }
}
