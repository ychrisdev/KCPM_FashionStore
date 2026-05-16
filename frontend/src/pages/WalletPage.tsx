import React, { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { useLocation, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import {
  assignGatewayUrl,
  closeGatewayTab,
  openBlankGatewayTab,
} from "../utils/gatewayTab";

const WALLET_GATEWAY_LOGO: Record<"momo" | "zalopay", string> = {
  momo: "/payments/momo.svg",
  zalopay: "/payments/zalopay.svg",
};

interface Transaction {
  transaction_id: number;
  amount: string;
  type: string;
  status: string;
  gateway?: string;
  gateway_ref?: string;
  description: string | null;
  created_at: string;
}

const TX_TYPE_VI: Record<string, string> = {
  deposit: "Nạp tiền",
  withdrawal: "Rút tiền",
  payment: "Thanh toán",
  refund: "Hoàn tiền",
};

const TX_STATUS_VI: Record<string, string> = {
  pending: "Đang xử lý",
  completed: "Thành công",
  failed: "Thất bại",
};

function formatVnd(value: string | number) {
  const n = typeof value === "number" ? value : parseFloat(String(value));
  if (Number.isNaN(n)) return String(value);
  return `${new Intl.NumberFormat("vi-VN").format(n)} đ`;
}

function formatWhen(iso: string) {
  try {
    return new Date(iso).toLocaleString("vi-VN", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function apiErr(e: unknown): string {
  if (!axios.isAxiosError(e) || !e.response) {
    return "Không thực hiện được. Thử lại sau.";
  }
  const d = e.response.data as { error?: string; detail?: string };
  if (typeof d?.error === "string") return d.error;
  if (typeof d?.detail === "string") return d.detail;
  return "Không thực hiện được. Thử lại sau.";
}

const QUICK_AMOUNTS = [100_000, 200_000, 500_000, 1_000_000];

const WalletPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const fetchWalletDataRef = useRef<() => Promise<void>>(async () => {});

  const [balance, setBalance] = useState<number>(0);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [flash, setFlash] = useState<{ kind: "success" | "error"; text: string } | null>(
    null,
  );

  const [modal, setModal] = useState<null | "deposit">(null);
  const [amountStr, setAmountStr] = useState("");
  const [modalSubmitting, setModalSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const fetchWalletData = useCallback(async () => {
    setLoadError(null);
    try {
      const response = await api.get("/wallets/my-wallet/");
      const b = response.data.balance;
      setBalance(typeof b === "string" ? parseFloat(b) : Number(b));
      setTransactions(response.data.transactions ?? []);
    } catch (e) {
      console.error("Lỗi khi lấy thông tin ví:", e);
      setLoadError(apiErr(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWalletDataRef.current = fetchWalletData;
  }, [fetchWalletData]);

  useEffect(() => {
    fetchWalletData();
  }, [fetchWalletData]);

  /** Sau khi quay lại từ MoMo / ZaloPay (query payment, deposit_tx). */
  useEffect(() => {
    const sp = new URLSearchParams(location.search);
    const payment = sp.get("payment");
    const depositTx = sp.get("deposit_tx");
    if (!payment) return;

    const clearQuery = () => {
      navigate({ pathname: location.pathname, search: "" }, { replace: true });
    };

    if (payment === "success") {
      setFlash({
        kind: "success",
        text: "Nạp tiền vào ví đã được ghi nhận.",
      });
      void fetchWalletDataRef.current();
      clearQuery();
      return;
    }

    if (payment === "failed") {
      setFlash({
        kind: "error",
        text: depositTx
          ? "Thanh toán nạp ví chưa thành công hoặc đã hủy."
          : "Thanh toán nạp ví chưa thành công.",
      });
      void fetchWalletDataRef.current();
      clearQuery();
      return;
    }

    if (payment === "pending" && depositTx) {
      const tid = parseInt(depositTx, 10);
      if (Number.isNaN(tid)) {
        clearQuery();
        return undefined;
      }

      const ctl: { cancelled: boolean; timer?: number } = { cancelled: false };
      let attempts = 0;
      const maxAttempts = 36;

      const runSync = async (): Promise<boolean> => {
        try {
          const { data } = await api.post(`/wallets/deposit/${tid}/zalopay-sync/`);
          if (ctl.cancelled) return true;
          await fetchWalletDataRef.current();
          const st = data.transaction?.status as string | undefined;
          if (st === "completed") {
            setFlash({ kind: "success", text: "Nạp tiền vào ví đã được ghi nhận." });
            clearQuery();
            return true;
          }
          if (st === "failed") {
            setFlash({ kind: "error", text: "Giao dịch nạp ví không thành công." });
            clearQuery();
            return true;
          }
        } catch {
          /* giữ polling */
        }
        return false;
      };

      void (async () => {
        const doneEarly = await runSync();
        if (ctl.cancelled || doneEarly) return;
        ctl.timer = window.setInterval(async () => {
          if (ctl.cancelled) return;
          attempts += 1;
          const done = await runSync();
          if (done || ctl.cancelled || attempts >= maxAttempts) {
            if (ctl.timer) window.clearInterval(ctl.timer);
            ctl.timer = undefined;
            if (!ctl.cancelled && !done && attempts >= maxAttempts) {
              setFlash({
                kind: "error",
                text:
                  "Chưa nhận được xác nhận từ ZaloPay. Kiểm tra lại sau trong lịch sử giao dịch hoặc tải lại trang.",
              });
              clearQuery();
            }
          }
        }, 5000);
      })();

      return () => {
        ctl.cancelled = true;
        if (ctl.timer) window.clearInterval(ctl.timer);
      };
    }

    return undefined;
  }, [location.search, location.pathname, navigate]);

  useEffect(() => {
    if (!flash) return;
    const t = window.setTimeout(() => setFlash(null), 5000);
    return () => window.clearTimeout(t);
  }, [flash]);

  const closeModal = useCallback(() => {
    setModal(null);
    setAmountStr("");
    setModalError(null);
    setModalSubmitting(false);
  }, []);

  useEffect(() => {
    if (!modal) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeModal();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [modal, closeModal]);

  const openDepositModal = () => {
    setModal("deposit");
    setAmountStr("");
    setModalError(null);
  };

  const parseModalAmount = (): number | null => {
    const raw = amountStr.replace(/\s/g, "").replace(/\./g, "").replace(/,/g, "");
    const amount = parseInt(raw, 10);
    if (Number.isNaN(amount) || amount <= 0) return null;
    return amount;
  };

  const startGatewayDeposit = async (provider: "momo" | "zalopay") => {
    if (modal !== "deposit") return;
    const amount = parseModalAmount();
    if (amount === null) {
      setModalError("Nhập số tiền hợp lệ (VNĐ, số nguyên dương).");
      return;
    }
    const gatewayTab = openBlankGatewayTab();
    setModalSubmitting(true);
    setModalError(null);
    try {
      const { data } = await api.post<{
        payment_url?: string;
        error?: string;
      }>("/wallets/deposit/start/", { amount, provider });
      const url = data.payment_url;
      if (!url || typeof url !== "string") {
        closeGatewayTab(gatewayTab);
        setModalError("Không nhận được liên kết thanh toán.");
        return;
      }
      if (assignGatewayUrl(gatewayTab, url)) {
        setFlash({
          kind: "success",
          text:
            provider === "zalopay"
              ? "Đã mở tab ZaloPay. Hoàn tất nạp tiền ở đó, sau đó quay lại trang ví để xem số dư."
              : "Đã mở tab MoMo. Hoàn tất nạp tiền ở đó, sau đó quay lại trang ví để xem số dư.",
        });
        closeModal();
        return;
      }
      closeGatewayTab(gatewayTab);
      window.location.href = url;
    } catch (e) {
      closeGatewayTab(gatewayTab);
      setModalError(apiErr(e));
    } finally {
      setModalSubmitting(false);
    }
  };

  const amountSignForType = (type: string) => {
    if (type === "deposit" || type === "refund") return "+";
    if (type === "withdrawal" || type === "payment") return "−";
    return "";
  };

  const amountToneClass = (type: string) => {
    if (type === "deposit" || type === "refund") return "wallet-tableAmount wallet-tableAmount--in";
    if (type === "withdrawal" || type === "payment")
      return "wallet-tableAmount wallet-tableAmount--out";
    return "wallet-tableAmount";
  };

  const statusBadgeClass = (status: string) => {
    if (status === "completed") return "wallet-badge wallet-badge--completed";
    if (status === "pending") return "wallet-badge wallet-badge--pending";
    if (status === "failed") return "wallet-badge wallet-badge--failed";
    return "wallet-badge";
  };

  if (loading) {
    return (
      <div className="pageSection wallet-page wallet-page--embed">
        <div className="sectionContainer customer-account-embedInner">
          <div className="wallet-loading" role="status" aria-live="polite">
            <span className="wallet-spinner" aria-hidden />
            Đang tải ví…
          </div>
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="pageSection wallet-page wallet-page--embed">
        <div className="sectionContainer customer-account-embedInner">
          <div className="wallet-errorBox">
            <p>{loadError}</p>
            <button type="button" className="btn-primary" onClick={() => fetchWalletData()}>
              Thử lại
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="pageSection wallet-page wallet-page--embed">
      <div className="sectionContainer customer-account-embedInner">
        <p className="wallet-lead">
          Số dư dùng trong cửa hàng. Nạp tiền qua MoMo hoặc ZaloPay. Lịch sử giao dịch nằm bên dưới.
        </p>

        {flash ? (
          <div
            className={`wallet-flash wallet-flash--${flash.kind}`}
            role="status"
          >
            <span>{flash.text}</span>
            <button
              type="button"
              className="wallet-flashDismiss"
              aria-label="Đóng thông báo"
              onClick={() => setFlash(null)}
            >
              ×
            </button>
          </div>
        ) : null}

        <section className="wallet-hero" aria-labelledby="wallet-balance-label">
          <p id="wallet-balance-label" className="wallet-heroLabel">
            Số dư khả dụng
          </p>
          <p className="wallet-balance">{formatVnd(balance)}</p>
          <div className="wallet-heroActions">
            <button type="button" className="btn-primary" onClick={openDepositModal}>
              Nạp tiền
            </button>
          </div>
        </section>

        <h2 className="wallet-sectionTitle">Lịch sử giao dịch</h2>
        <div className="wallet-panel">
          {transactions.length === 0 ? (
            <p className="wallet-empty">Chưa có giao dịch nào được ghi nhận.</p>
          ) : (
            <>
              <div className="wallet-tableWrap">
                <table className="wallet-table">
                  <thead>
                    <tr>
                      <th scope="col">Thời gian</th>
                      <th scope="col">Loại</th>
                      <th scope="col">Số tiền</th>
                      <th scope="col">Trạng thái</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transactions.map((tx) => (
                      <tr key={tx.transaction_id}>
                        <td>{formatWhen(tx.created_at)}</td>
                        <td>
                          {TX_TYPE_VI[tx.type] ?? tx.type}
                          {tx.description ? (
                            <span className="wallet-txNote">{tx.description}</span>
                          ) : null}
                        </td>
                        <td className={amountToneClass(tx.type)}>
                          {amountSignForType(tx.type)} {formatVnd(tx.amount)}
                        </td>
                        <td>
                          <span className={statusBadgeClass(tx.status)}>
                            {TX_STATUS_VI[tx.status] ?? tx.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="wallet-cards">
                {transactions.map((tx) => (
                  <article key={tx.transaction_id} className="wallet-cardRow">
                    <div className="wallet-cardRowTop">
                      <div>
                        <strong>{TX_TYPE_VI[tx.type] ?? tx.type}</strong>
                        <div className="wallet-cardRowMeta">{formatWhen(tx.created_at)}</div>
                      </div>
                      <span className={amountToneClass(tx.type)}>
                        {amountSignForType(tx.type)} {formatVnd(tx.amount)}
                      </span>
                    </div>
                    {tx.description ? (
                      <div className="wallet-cardRowMeta">{tx.description}</div>
                    ) : null}
                    <div style={{ marginTop: 8 }}>
                      <span className={statusBadgeClass(tx.status)}>
                        {TX_STATUS_VI[tx.status] ?? tx.status}
                      </span>
                    </div>
                  </article>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {modal ? (
        <div
          className="wallet-backdrop"
          role="presentation"
          onClick={(e) => {
            if (e.target === e.currentTarget) closeModal();
          }}
        >
          <div
            className="wallet-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="wallet-modal-title"
          >
            <h3 id="wallet-modal-title" className="wallet-modalTitle">
              Nạp tiền vào ví
            </h3>
            <p className="wallet-modalHint">
              Nhập số tiền (10.000 – 50.000.000 VNĐ), sau đó chọn MoMo hoặc ZaloPay để chuyển sang cổng thanh toán.
            </p>
            <label className="wallet-fieldLabel" htmlFor="wallet-amount-input">
              Số tiền (VNĐ)
            </label>
            <input
              id="wallet-amount-input"
              className="wallet-input"
              inputMode="numeric"
              autoComplete="off"
              placeholder="Ví dụ: 500000"
              value={amountStr}
              onChange={(e) => setAmountStr(e.target.value)}
              disabled={modalSubmitting}
            />
            <div className="wallet-chips">
              {QUICK_AMOUNTS.map((n) => (
                <button
                  key={n}
                  type="button"
                  className="wallet-chip"
                  disabled={modalSubmitting}
                  onClick={() => setAmountStr(String(n))}
                >
                  {new Intl.NumberFormat("vi-VN").format(n)}
                </button>
              ))}
            </div>
            {modalError ? <p className="wallet-modalError">{modalError}</p> : null}
            <div className="wallet-modalActions wallet-modalActions--deposit">
              <div className="wallet-modalPayRow">
                <button
                  type="button"
                  className="wallet-btnPayIcon"
                  onClick={() => void startGatewayDeposit("momo")}
                  disabled={modalSubmitting}
                  aria-label="Thanh toán MoMo"
                >
                  {modalSubmitting ? (
                    <span className="wallet-payBtnLoading">Đang mở…</span>
                  ) : (
                    <img
                      src={WALLET_GATEWAY_LOGO.momo}
                      alt=""
                      className="wallet-payLogo"
                      width={112}
                      height={40}
                      decoding="async"
                    />
                  )}
                </button>
                <button
                  type="button"
                  className="wallet-btnPayIcon"
                  onClick={() => void startGatewayDeposit("zalopay")}
                  disabled={modalSubmitting}
                  aria-label="Thanh toán ZaloPay"
                >
                  {modalSubmitting ? (
                    <span className="wallet-payBtnLoading">Đang mở…</span>
                  ) : (
                    <img
                      src={WALLET_GATEWAY_LOGO.zalopay}
                      alt=""
                      className="wallet-payLogo"
                      width={112}
                      height={40}
                      decoding="async"
                    />
                  )}
                </button>
              </div>
              <button
                type="button"
                className="btn-secondary wallet-modalCancelWide"
                onClick={closeModal}
                disabled={modalSubmitting}
              >
                Hủy
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default WalletPage;
