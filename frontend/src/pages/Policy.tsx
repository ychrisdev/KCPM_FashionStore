import { useEffect, useMemo, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import { site } from "../api/client";
import SupportSubnav from "../components/SupportSubnav";
import { getPolicyDetailBlock } from "../content/policyDetailContent";
import "../styles/pages/Policy.css";

type ApiPolicy = { id: number; title: string; content: string };

type PolicyTemplate = {
  slug: string;
  title: string;
  desc: string;
  matchKeys: string[];
  accent: string;
  bg: string;
  icon: ReactNode;
};

function normVi(s: string): string {
  return s
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function findApiForTemplate(apiList: ApiPolicy[], keys: string[]): ApiPolicy | undefined {
  return apiList.find((p) => {
    const n = normVi(p.title);
    return keys.some((k) => n.includes(normVi(k)));
  });
}

const POLICY_TEMPLATES: PolicyTemplate[] = [
  {
    slug: "giao-hang",
    title: "Chính sách giao hàng",
    desc: "Chúng tôi giao hàng toàn quốc trong 2–5 ngày làm việc tùy khu vực.",
    matchKeys: ["giao hang", "van chuyen", "ship", "giao"],
    accent: "#3B82F6",
    bg: "linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%)",
    icon: (
      <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="4" y="24" width="38" height="22" rx="3" fill="#BFDBFE" stroke="#3B82F6" strokeWidth="2" />
        <rect x="8" y="16" width="26" height="12" rx="2" fill="#93C5FD" stroke="#3B82F6" strokeWidth="1.5" />
        <path
          d="M42 32 L42 40 Q42 46 48 46 L58 46 L58 36 L52 28 L42 28 Z"
          fill="#BFDBFE"
          stroke="#3B82F6"
          strokeWidth="2"
        />
        <path d="M44 28 L52 28 L58 36 L44 36 Z" fill="#93C5FD" stroke="#3B82F6" strokeWidth="1.5" />
        <circle cx="14" cy="46" r="6" fill="#1D4ED8" stroke="#3B82F6" strokeWidth="1.5" />
        <circle cx="14" cy="46" r="2.5" fill="#DBEAFE" />
        <circle cx="50" cy="46" r="6" fill="#1D4ED8" stroke="#3B82F6" strokeWidth="1.5" />
        <circle cx="50" cy="46" r="2.5" fill="#DBEAFE" />
        <line x1="2" y1="30" x2="10" y2="30" stroke="#3B82F6" strokeWidth="2" strokeLinecap="round" />
        <line x1="2" y1="35" x2="7" y2="35" stroke="#93C5FD" strokeWidth="2" strokeLinecap="round" />
        <line x1="2" y1="40" x2="9" y2="40" stroke="#3B82F6" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    slug: "doi-tra",
    title: "Chính sách đổi trả",
    desc: "Bạn có thể đổi hoặc trả sản phẩm trong vòng 30 ngày nếu chưa sử dụng.",
    matchKeys: ["doi tra", "tra hang", "hoan", "doi"],
    accent: "#10B981",
    bg: "linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%)",
    icon: (
      <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="12" y="20" width="24" height="24" rx="3" fill="#A7F3D0" stroke="#10B981" strokeWidth="2" />
        <line x1="12" y1="28" x2="36" y2="28" stroke="#10B981" strokeWidth="1.5" />
        <path d="M21 24 L27 24" stroke="#10B981" strokeWidth="2" strokeLinecap="round" />
        <path d="M38 30 Q50 20 52 34" stroke="#10B981" strokeWidth="2.5" strokeLinecap="round" fill="none" />
        <path d="M48 38 L52 34 L56 38" stroke="#10B981" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
        <circle cx="44" cy="48" r="8" fill="#10B981" />
        <path d="M40 48 L43 51 L48 45" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    slug: "thanh-toan",
    title: "Thanh toán",
    desc: "Hỗ trợ thanh toán khi nhận hàng (COD) và các phương thức thanh toán trực tuyến.",
    matchKeys: ["thanh toan", "cod", "chuyen khoan"],
    accent: "#F59E0B",
    bg: "linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%)",
    icon: (
      <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="8" y="18" width="48" height="30" rx="5" fill="#FDE68A" stroke="#F59E0B" strokeWidth="2" />
        <rect x="8" y="26" width="48" height="8" fill="#F59E0B" opacity="0.6" />
        <rect x="14" y="34" width="12" height="8" rx="2" fill="#FBBF24" stroke="#F59E0B" strokeWidth="1.5" />
        <circle cx="38" cy="38" r="2.5" fill="#F59E0B" opacity="0.8" />
        <circle cx="44" cy="38" r="2.5" fill="#F59E0B" />
        <circle cx="50" cy="38" r="2.5" fill="#F59E0B" opacity="0.6" />
        <path d="M30 20 Q32 17 34 20" stroke="#F59E0B" strokeWidth="1.5" strokeLinecap="round" fill="none" />
        <path d="M27 22 Q32 15 37 22" stroke="#F59E0B" strokeWidth="1.5" strokeLinecap="round" fill="none" />
      </svg>
    ),
  },
  {
    slug: "bao-mat",
    title: "Bảo mật thông tin",
    desc: "Thông tin cá nhân của khách hàng luôn được bảo mật tuyệt đối.",
    matchKeys: ["bao mat", "bao ve", "rieng tu"],
    accent: "#8B5CF6",
    bg: "linear-gradient(135deg, #F5F3FF 0%, #EDE9FE 100%)",
    icon: (
      <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M32 8 L52 16 L52 32 Q52 46 32 56 Q12 46 12 32 L12 16 Z" fill="#DDD6FE" stroke="#8B5CF6" strokeWidth="2" />
        <path d="M32 14 L46 20 L46 32 Q46 42 32 50 Q18 42 18 32 L18 20 Z" fill="#EDE9FE" stroke="#8B5CF6" strokeWidth="1.5" />
        <rect x="25" y="33" width="14" height="10" rx="2" fill="#8B5CF6" />
        <path d="M27 33 L27 29 Q27 24 32 24 Q37 24 37 29 L37 33" stroke="#8B5CF6" strokeWidth="2.5" strokeLinecap="round" fill="none" />
        <circle cx="32" cy="38" r="2" fill="white" />
      </svg>
    ),
  },
  {
    slug: "dong-goi",
    title: "Đóng gói sản phẩm",
    desc: "Tất cả sản phẩm đều được đóng gói cẩn thận trước khi giao đến khách hàng.",
    matchKeys: ["dong goi", "goi hang", "bao bi"],
    accent: "#EC4899",
    bg: "linear-gradient(135deg, #FDF2F8 0%, #FCE7F3 100%)",
    icon: (
      <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M10 30 L32 40 L54 30 L54 52 Q54 54 52 55 L32 62 L12 55 Q10 54 10 52 Z" fill="#FBCFE8" stroke="#EC4899" strokeWidth="2" />
        <path d="M10 30 L32 20 L32 40 L10 30 Z" fill="#F9A8D4" stroke="#EC4899" strokeWidth="1.5" />
        <path d="M54 30 L32 20 L32 40 L54 30 Z" fill="#FBCFE8" stroke="#EC4899" strokeWidth="1.5" />
        <path d="M10 30 L54 30" stroke="#EC4899" strokeWidth="2" />
        <path d="M32 20 L32 62" stroke="#EC4899" strokeWidth="2" />
        <path d="M32 18 Q26 12 22 16 Q18 20 26 22 Z" fill="#EC4899" />
        <path d="M32 18 Q38 12 42 16 Q46 20 38 22 Z" fill="#BE185D" />
        <circle cx="32" cy="20" r="3" fill="#EC4899" />
      </svg>
    ),
  },
  {
    slug: "cam-ket",
    title: "Cam kết chất lượng",
    desc: "Chúng tôi cam kết cung cấp sản phẩm chính hãng và chất lượng cao.",
    matchKeys: ["cam ket", "chat luong", "chinh hang"],
    accent: "#EF4444",
    bg: "linear-gradient(135deg, #FEF2F2 0%, #FEE2E2 100%)",
    icon: (
      <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M26 8 L38 8 L38 30 L32 26 L26 30 Z" fill="#FCA5A5" stroke="#EF4444" strokeWidth="1.5" />
        <circle cx="32" cy="42" r="16" fill="#FEE2E2" stroke="#EF4444" strokeWidth="2" />
        <circle cx="32" cy="42" r="12" fill="#FCA5A5" stroke="#EF4444" strokeWidth="1.5" />
        <path d="M32 32 L34 38 L40 38 L35.5 42 L37.5 48 L32 44.5 L26.5 48 L28.5 42 L24 38 L30 38 Z" fill="#EF4444" />
      </svg>
    ),
  },
];

const CARD_PREVIEW_LEN = 220;

function previewText(text: string): string {
  const t = text.trim();
  if (t.length <= CARD_PREVIEW_LEN) return t;
  return `${t.slice(0, CARD_PREVIEW_LEN).trim()}…`;
}

function parsePoliciesPayload(data: unknown): ApiPolicy[] {
  if (Array.isArray(data)) return data as ApiPolicy[];
  if (data && typeof data === "object" && "results" in data && Array.isArray((data as { results: unknown }).results)) {
    return (data as { results: ApiPolicy[] }).results;
  }
  return [];
}

function PolicyHeroDecor({ themed = false }: { themed?: boolean }) {
  return (
    <>
      <div className="policy-heroMesh" aria-hidden />
      <div
        className={`policy-heroFloat policy-heroFloat--1${themed ? " policy-heroFloat--accent" : ""}`}
        aria-hidden
      />
      <div className="policy-heroFloat policy-heroFloat--2" aria-hidden />
      <div className="policy-heroFloat policy-heroFloat--3" aria-hidden />
      <div
        className={`policy-heroBlob policy-heroBlob--left${themed ? " policy-heroBlob--accentL" : ""}`}
        aria-hidden
      />
      <div
        className={`policy-heroBlob policy-heroBlob--right${themed ? " policy-heroBlob--accentR" : ""}`}
        aria-hidden
      />
    </>
  );
}

/** Icon nhỏ cho từng ô highlight (chu kỳ 3 kiểu) */
function PolicyHighlightGlyph({ variant }: { variant: 0 | 1 | 2 }) {
  const c = "policy-highlightGlyphSvg";
  if (variant === 0) {
    return (
      <svg className={c} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  if (variant === 1) {
    return (
      <svg className={c} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
        <path d="M22 11.08V12a10 10 0 11-5.93-9.14" strokeLinecap="round" />
        <path d="M22 4L12 14.01l-3-3" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  return (
    <svg className={c} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function Policy() {
  const { slug, policyId } = useParams<{ slug?: string; policyId?: string }>();
  const [apiPolicies, setApiPolicies] = useState<ApiPolicy[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchErr, setFetchErr] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setFetchErr(false);
    site
      .getPolicies()
      .then((res) => {
        if (!cancelled) setApiPolicies(parsePoliciesPayload(res.data));
      })
      .catch(() => {
        if (!cancelled) {
          setFetchErr(true);
          setApiPolicies([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const viewPolicyId = useMemo(() => {
    if (policyId == null || policyId === "") return null;
    const n = Number(policyId);
    return Number.isFinite(n) && n > 0 ? n : null;
  }, [policyId]);

  if (policyId != null && policyId !== "" && viewPolicyId == null) {
    return <Navigate to="/policy" replace />;
  }

  const templateBySlug = useMemo(() => {
    if (!slug) return undefined;
    return POLICY_TEMPLATES.find((t) => t.slug === slug);
  }, [slug]);

  if (viewPolicyId != null) {
    if (loading) {
      return (
        <div className="policy-page">
          <section className="policy-hero">
            <PolicyHeroDecor />
            <div className="policy-heroInner">
              <h1 className="policy-heroTitle policy-heroTitle--home">Chính sách</h1>
              <p className="policy-heroSubtitle">Đang tải nội dung…</p>
              <SupportSubnav />
            </div>
          </section>
        </div>
      );
    }
    const pol = apiPolicies.find((p) => p.id === viewPolicyId);
    if (!pol) {
      return <Navigate to="/policy" replace />;
    }
    return (
      <div className="policy-page policy-page--detail">
        <section className="policy-hero policy-hero--detail">
          <PolicyHeroDecor />
          <div className="policy-heroInner policy-heroInner--detail">
            <p className="policy-heroBack">
              <Link to="/policy" className="policy-backLink">
                <span className="policy-backIcon" aria-hidden>
                  ←
                </span>
                Tất cả chính sách
              </Link>
            </p>
            <h1 className="policy-detailHeroTitle">{pol.title}</h1>
            <p className="policy-heroSubtitle policy-heroSubtitle--detail">
              Nội dung do quản trị viên cập nhật trên hệ thống.
            </p>
            <SupportSubnav />
          </div>
        </section>
        <section className="policy-section">
          <div className="policy-container">
            <div
              className="policy-detailProse policy-detailProse--premium"
              style={{ whiteSpace: "pre-wrap" }}
            >
              {pol.content}
            </div>
          </div>
        </section>
      </div>
    );
  }

  if (slug && !templateBySlug) {
    return <Navigate to="/policy" replace />;
  }

  const detailApi = templateBySlug ? findApiForTemplate(apiPolicies, templateBySlug.matchKeys) : undefined;
  const detailBlock = slug ? getPolicyDetailBlock(slug) : undefined;
  const apiContent = detailApi?.content?.trim() ?? "";
  const useApiBody = apiContent.length >= 24;

  if (slug && templateBySlug) {
    const displayTitle = detailApi?.title?.trim() || templateBySlug.title;
    const pageStyle = {
      "--detail-accent": templateBySlug.accent,
      "--detail-hero-bg": templateBySlug.bg,
    } as CSSProperties;

    return (
      <div className="policy-page policy-page--detail policy-page--detailPremium" style={pageStyle}>
        <div className="policy-detailHeroStage">
          <section className="policy-hero policy-hero--detail policy-hero--detailThemed policy-hero--detailPremium">
            <div className="policy-detailHeroGrid" aria-hidden />
            <div className="policy-detailHeroNoise" aria-hidden />
            <PolicyHeroDecor themed />
            <div className="policy-heroInner policy-heroInner--detail">
              <p className="policy-heroBack">
                <Link to="/policy" className="policy-backLink">
                  <span className="policy-backIcon" aria-hidden>
                    ←
                  </span>
                  Tất cả chính sách
                </Link>
              </p>
              <div className="policy-detailHeroIconCluster">
                <span className="policy-detailHeroRing policy-detailHeroRing--a" aria-hidden />
                <span className="policy-detailHeroRing policy-detailHeroRing--b" aria-hidden />
                <span className="policy-detailHeroSpark policy-detailHeroSpark--1" aria-hidden />
                <span className="policy-detailHeroSpark policy-detailHeroSpark--2" aria-hidden />
                <div className="policy-detailHeroIcon policy-detailHeroIcon--premium">{templateBySlug.icon}</div>
              </div>
              <p className="policy-detailHeroTag">
                <span className="policy-detailHeroTagGlow" aria-hidden />
                <span className="policy-detailHeroTagText">
                  {detailBlock?.heroTag ?? "Chính sách FashionStore"}
                </span>
              </p>
              <h1 className="policy-detailHeroTitle">{displayTitle}</h1>
              <p className="policy-heroSubtitle policy-heroSubtitle--detail">
                {useApiBody
                  ? "Bản chính thức từ hệ thống — cập nhật theo thời điểm quản trị viên chỉnh sửa."
                  : "Tóm tắt thao tác nhanh và phần đọc sâu bên dưới — thiết kế giống trải nghiệm thương mại điện tử hàng đầu."}
              </p>
              <SupportSubnav />
            </div>
            <div className="policy-detailHeroCurve" aria-hidden />
          </section>

          <div className="policy-detailTrustStrip" role="list">
            <div className="policy-trustChip" role="listitem">
              <span className="policy-trustChipIcon" aria-hidden>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
              </span>
              <span className="policy-trustChipText">Minh bạch điều khoản</span>
            </div>
            <div className="policy-trustChip" role="listitem">
              <span className="policy-trustChipIcon" aria-hidden>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                  <path d="M21 15a4 4 0 01-4 4H7l-4 4V7a4 4 0 014-4h10a4 4 0 014 4v8z" />
                </svg>
              </span>
              <span className="policy-trustChipText">Hỗ trợ qua đơn hàng</span>
            </div>
            <div className="policy-trustChip" role="listitem">
              <span className="policy-trustChipIcon" aria-hidden>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 6v6l4 2" strokeLinecap="round" />
                </svg>
              </span>
              <span className="policy-trustChipText">Cập nhật thường xuyên</span>
            </div>
          </div>
        </div>

        <section className="policy-section policy-section--detailRich">
          <div className="policy-container policy-container--detail">
            {fetchErr && (
              <p className="policy-detailErr policy-detailErr--banner" role="alert">
                Không tải được chính sách từ máy chủ — đang hiển thị nội dung mặc định trên trang.
              </p>
            )}

            {detailBlock && (
              <header className="policy-detailSectionHead">
                <span className="policy-detailEyebrow">Ưu tiên của khách hàng</span>
                <h2 className="policy-detailSubhead">Điểm then chốt</h2>
                <p className="policy-detailSectionLead">
                  Ba thông tin quan trọng nhất — lướt nhanh trước khi đọc chi tiết.
                </p>
              </header>
            )}

            {detailBlock && (
              <div className="policy-detailHighlights">
                {detailBlock.highlights.map((h, hi) => (
                  <div key={h.title} className="policy-highlightCard policy-highlightCard--premium">
                    <div className="policy-highlightShine" aria-hidden />
                    <div className="policy-highlightBar" />
                    <div className="policy-highlightIconWrap">
                      <PolicyHighlightGlyph variant={(hi % 3) as 0 | 1 | 2} />
                    </div>
                    <h3 className="policy-highlightTitle">{h.title}</h3>
                    <p className="policy-highlightText">{h.text}</p>
                  </div>
                ))}
              </div>
            )}

            <div className="policy-detailMainGrid">
              <div className="policy-detailSheet policy-detailSheet--rich policy-detailSheet--editorial">
                <header className="policy-detailSheetHead">
                  <span className="policy-detailEyebrow policy-detailEyebrow--sheet">Nội dung đầy đủ</span>
                  <h2 className="policy-detailSheetTitle">Chi tiết chính sách</h2>
                </header>
                {loading ? (
                  <div className="policy-detailSkeleton" aria-busy="true">
                    <div className="policy-skelLine policy-skelLine--long" />
                    <div className="policy-skelLine" />
                    <div className="policy-skelLine" />
                    <div className="policy-skelLine policy-skelLine--medium" />
                  </div>
                ) : useApiBody ? (
                  <div className="policy-detailProse policy-detailProse--api policy-detailProse--premium">{apiContent}</div>
                ) : detailBlock ? (
                  <div className="policy-detailSections">
                    {detailBlock.sections.map((sec, si) => (
                      <section key={sec.heading} className="policy-detailBlock policy-detailBlock--premium">
                        <h2 className="policy-detailBlockTitle">
                          <span className="policy-detailBlockNum">{String(si + 1).padStart(2, "0")}</span>
                          {sec.heading}
                        </h2>
                        {sec.paragraphs.map((para, i) => (
                          <p key={i} className="policy-detailBlockP">
                            {para}
                          </p>
                        ))}
                      </section>
                    ))}
                  </div>
                ) : (
                  <div className="policy-detailProse policy-detailProse--premium">{templateBySlug.desc}</div>
                )}
              </div>

              <aside className="policy-detailAside">
                <div className="policy-detailCta policy-detailCta--premium">
                  <div className="policy-detailCtaGlow" aria-hidden />
                  <p className="policy-detailCtaLabel">Hỗ trợ 1–1</p>
                  <p className="policy-detailCtaText">
                    Cần làm rõ trường hợp cá nhân? Đội ngũ phản hồi trong giờ hành chính, thường dưới 24h qua
                    email.
                  </p>
                  <div className="policy-detailCtaQuick">
                    <a href="tel:0964942121" className="policy-detailCtaMini">
                      <span className="policy-detailCtaMiniIcon" aria-hidden>
                        📞
                      </span>
                      0964 942 121
                    </a>
                    <a href="mailto:cskh@fashionstore.vn" className="policy-detailCtaMini">
                      <span className="policy-detailCtaMiniIcon" aria-hidden>
                        ✉
                      </span>
                      Email CSKH
                    </a>
                  </div>
                  <Link to="/contact" className="policy-detailCtaBtn">
                    Mở trang liên hệ
                  </Link>
                  <Link to="/feedback" className="policy-detailCtaLink">
                    Gửi góp ý cải thiện
                  </Link>
                </div>
              </aside>
            </div>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="policy-page">
      <section className="policy-hero">
        <PolicyHeroDecor />
        <div className="policy-heroInner">
          <p className="policy-heroBadge">
            <span className="policy-heroBadgeDot" aria-hidden />
            Minh bạch &amp; an toàn
          </p>
          <h1 className="policy-heroTitle policy-heroTitle--home">
            <span className="policy-heroTitleGrad">Chính sách</span>
            <span className="policy-heroTitleRest"> khách hàng</span>
          </h1>
          <p className="policy-heroSubtitle">
            Cam kết rõ ràng về giao hàng, đổi trả, thanh toán và bảo mật — chạm vào từng mục để đọc chi tiết.
            {fetchErr && (
              <span className="policy-fetchErr">
                Không tải được dữ liệu từ máy chủ — đang dùng nội dung mặc định.
              </span>
            )}
          </p>
          <div className="policy-heroPills" role="list">
            <span className="policy-pill" role="listitem">
              Giao hàng
            </span>
            <span className="policy-pill" role="listitem">
              Đổi trả
            </span>
            <span className="policy-pill" role="listitem">
              Bảo mật
            </span>
          </div>
          <SupportSubnav />
        </div>
      </section>

      <section className="policy-section">
        <div className="policy-container">
          <div className="policyGrid">
            {POLICY_TEMPLATES.map((p, index) => {
              const matched = findApiForTemplate(apiPolicies, p.matchKeys);
              const text = matched?.content?.trim()
                ? previewText(matched.content.trim())
                : p.desc;
              const title = matched?.title?.trim() ? matched.title.trim() : p.title;
              const cardStyle = {
                "--card-accent": p.accent,
                "--card-bg": p.bg,
                "--enter-delay": `${index * 55}ms`,
              } as CSSProperties;
              return (
                <Link
                  key={p.slug}
                  to={`/policy/${p.slug}`}
                  className={`policyCard policyCard--interactive${loading ? " policyCard--loading" : ""}`}
                  style={cardStyle}
                >
                  <div className="policyCardShine" aria-hidden />
                  <div className="policyIconWrap">
                    <div className="policyIconInner">{p.icon}</div>
                  </div>
                  <h3 className="policyCardTitle">{title}</h3>
                  <p className="policyCardExcerpt">
                    {loading ? (
                      <>
                        <span className="policy-excerptSkel" />
                        <span className="policy-excerptSkel policy-excerptSkel--mid" />
                        <span className="policy-excerptSkel policy-excerptSkel--short" />
                      </>
                    ) : (
                      text
                    )}
                  </p>
                  <div className="policyAccentBar" />
                  <span className="policyCardCta">
                    Xem chi tiết
                    <span className="policyCardCtaArrow" aria-hidden>
                      →
                    </span>
                  </span>
                </Link>
              );
            })}
            {(() => {
              const used = new Set(
                POLICY_TEMPLATES.map((t) => findApiForTemplate(apiPolicies, t.matchKeys))
                  .filter(Boolean)
                  .map((p) => p!.id),
              );
              const extra = apiPolicies.filter((p) => !used.has(p.id));
              return extra.map((pol, i) => (
                <Link
                  key={pol.id}
                  to={`/policy/view/${pol.id}`}
                  className={`policyCard policyCard--interactive policyCard--extra${loading ? " policyCard--loading" : ""}`}
                  style={
                    {
                      "--card-accent": "#64748b",
                      "--card-bg": "linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)",
                      "--enter-delay": `${(POLICY_TEMPLATES.length + i) * 55}ms`,
                    } as CSSProperties
                  }
                >
                  <div className="policyCardShine" aria-hidden />
                  <h3 className="policyCardTitle">{pol.title}</h3>
                  <p className="policyCardExcerpt">
                    {loading ? (
                      <>
                        <span className="policy-excerptSkel" />
                        <span className="policy-excerptSkel policy-excerptSkel--mid" />
                        <span className="policy-excerptSkel policy-excerptSkel--short" />
                      </>
                    ) : (
                      previewText(pol.content)
                    )}
                  </p>
                  <div className="policyAccentBar" />
                  <span className="policyCardCta">
                    Xem chi tiết
                    <span className="policyCardCtaArrow" aria-hidden>
                      →
                    </span>
                  </span>
                </Link>
              ));
            })()}
          </div>
        </div>
      </section>
    </div>
  );
}
