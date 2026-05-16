import QRCode from "qrcode";
import { useEffect, useState } from "react";
import "./ZaloPayQrModal.css";

export type ZaloPayQrPanelProps = {
  orderUrl: string | null;
  orderId?: number;
  onDone: () => void;
  onDismiss?: () => void;
  /** `inline` = khối trên trang thanh toán; `dialogBody` = nội dung bên trong modal */
  variant?: "dialogBody" | "inline";
};

export default function ZaloPayQrPanel({
  orderUrl,
  orderId,
  onDone,
  onDismiss,
  variant = "dialogBody",
}: ZaloPayQrPanelProps) {
  const [dataUrl, setDataUrl] = useState<string | null>(null);
  const [qrError, setQrError] = useState<string | null>(null);

  useEffect(() => {
    if (!orderUrl) {
      setDataUrl(null);
      setQrError(null);
      return;
    }
    let cancelled = false;
    setQrError(null);
    QRCode.toDataURL(orderUrl, {
      width: 240,
      margin: 1,
      errorCorrectionLevel: "M",
    })
      .then((url) => {
        if (!cancelled) setDataUrl(url);
      })
      .catch(() => {
        if (!cancelled)
          setQrError("Không tạo được mã QR. Dùng nút mở cổng bên dưới.");
      });
    return () => {
      cancelled = true;
    };
  }, [orderUrl]);

  if (!orderUrl) return null;

  const inner = (
    <>
      <h2 id="zlpQrTitle" className="zlpQrTitle">
        Thanh toán ZaloPay (sandbox)
      </h2>
      <p className="zlpQrHint">
        Mở <strong>app ZaloPay sandbox</strong> trên điện thoại và quét mã QR. Nội dung mã là
        liên kết cổng thanh toán do ZaloPay cung cấp (theo tài liệu QR động).
      </p>
      {orderId != null && (
        <p className="zlpQrOrderId">Đơn hàng #{orderId}</p>
      )}
      <div className="zlpQrFrame">
        {qrError && <p className="zlpQrErr">{qrError}</p>}
        {dataUrl && !qrError && (
          <img src={dataUrl} alt="Mã QR thanh toán ZaloPay" className="zlpQrImg" />
        )}
        {!dataUrl && !qrError && <p className="zlpQrLoading">Đang tạo mã QR…</p>}
      </div>
      <div className="zlpQrActions">
        <button
          type="button"
          className="zlpQrBtn zlpQrBtnSecondary"
          onClick={() => orderUrl && window.open(orderUrl, "_blank", "noopener,noreferrer")}
          disabled={!orderUrl}
        >
          Mở cổng trên trình duyệt
        </button>
        <button type="button" className="zlpQrBtn zlpQrBtnPrimary" onClick={onDone}>
          Đã quét / về đơn hàng
        </button>
      </div>
      {onDismiss && (
        <button type="button" className="zlpQrDismiss" onClick={onDismiss}>
          Đóng
        </button>
      )}
    </>
  );

  if (variant === "inline") {
    return <div className="zlpQrPanel">{inner}</div>;
  }

  return <>{inner}</>;
}
