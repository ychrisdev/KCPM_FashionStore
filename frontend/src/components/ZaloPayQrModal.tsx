import { useEffect } from "react";
import ZaloPayQrPanel from "./ZaloPayQrPanel";
import "./ZaloPayQrModal.css";

type Props = {
  open: boolean;
  orderUrl: string | null;
  orderId?: number;
  onClose: () => void;
  onDone: () => void;
};

export default function ZaloPayQrModal({
  open,
  orderUrl,
  orderId,
  onClose,
  onDone,
}: Props) {
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);
  if (!open) return null;

  return (
    <div
      className="zlpQrOverlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="zlpQrTitle"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="zlpQrDialog" onClick={(e) => e.stopPropagation()}>
        <ZaloPayQrPanel
          variant="dialogBody"
          orderUrl={orderUrl}
          orderId={orderId}
          onDone={onDone}
          onDismiss={onClose}
        />
      </div>
    </div>
  );
}
