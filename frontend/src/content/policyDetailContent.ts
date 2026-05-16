/**
 * Nội dung mặc định cho từng trang chi tiết chính sách (khi API chưa có bài dài).
 * Highlights luôn hiển thị; sections hiển thị khi không dùng nội dung API dài.
 */

export type PolicyHighlight = { title: string; text: string };
export type PolicySection = { heading: string; paragraphs: string[] };

export type PolicyDetailBlock = {
  heroTag: string;
  highlights: [PolicyHighlight, PolicyHighlight, PolicyHighlight];
  sections: PolicySection[];
};

export const POLICY_DETAIL_BLOCKS: Record<string, PolicyDetailBlock> = {
  "giao-hang": {
    heroTag: "Giao hàng toàn quốc",
    highlights: [
      {
        title: "Thời gian",
        text: "Thông thường 2–5 ngày làm việc kể từ khi đơn được xác nhận, tùy khu vực và đợt sale.",
      },
      {
        title: "Miễn phí ship",
        text: "Đơn từ 500.000đ được miễn phí giao hàng tiêu chuẩn trên toàn quốc (trừ khu vực đặc biệt có phụ phí).",
      },
      {
        title: "Theo dõi đơn",
        text: "Mã vận đơn và trạng thái giao hàng được cập nhật trên tài khoản và qua email/SMS khi có.",
      },
    ],
    sections: [
      {
        heading: "Phạm vi giao hàng",
        paragraphs: [
          "FashionStore giao hàng đến hầu hết tỉnh thành trên lãnh thổ Việt Nam thông qua các đối tác vận chuyển (GHN, GHTK, Ahamove, J&T… tùy tuyến và thời điểm).",
          "Địa chỉ giao hàng cần ghi rõ: họ tên, số điện thoại, địa chỉ chi tiết (số nhà, ngõ, phường/xã, quận/huyện). Trường hợp shipper không liên lạc được trong 3 lần, đơn có thể hoàn kho — bạn vui lòng theo dõi thông báo và chủ động liên hệ CSKH.",
        ],
      },
      {
        heading: "Phí vận chuyển & ưu đãi",
        paragraphs: [
          "Đơn dưới 500.000đ: phí ship được hiển thị rõ tại bước thanh toán (theo biểu phí đối tác vận chuyển và khu vực).",
          "Đơn từ 500.000đ: miễn phí giao hàng tiêu chuẩn. Một số chương trình khuyến mãi có thể điều chỉnh ngưỡng miễn phí — chúng tôi sẽ ghi chú trên trang khuyến mãi hoặc tại giỏ hàng.",
          "Giao hàng hỏa tốc / nội thành (nếu có): phí và thời gian hiển thị khi chọn phương thức.",
        ],
      },
      {
        heading: "Thời gian xử lý & giao",
        paragraphs: [
          "Thời gian chuẩn bị hàng: thường trong 24–48 giờ làm việc (không tính thứ Bảy, Chủ nhật và ngày lễ, trừ khi có thông báo khác trong đợt sale).",
          "Thời gian vận chuyển: 2–5 ngày làm việc sau khi bàn giao cho đơn vị vận chuyển; khu vực miền núi, đảo hoặc thời tiết xấu có thể kéo dài thêm.",
          "Trong các đợt sale lớn (Black Friday, Tết…), thời gian giao có thể cộng thêm 1–3 ngày — chúng tôi sẽ cập nhật trên website và email xác nhận đơn.",
        ],
      },
      {
        heading: "Kiểm tra khi nhận hàng",
        paragraphs: [
          "Quý khách nên kiểm tra ngoại quan thùng/túi đóng gói trước khi ký nhận. Nếu thấy rách, móp nặng, ướt bất thường, có thể từ chối nhận và ghi nhận với shipper, đồng thời liên hệ CSKH kèm mã đơn và hình ảnh.",
          "Sau khi ký nhận, vui lòng mở gói và kiểm tra sản phẩm trong 48 giờ. Mọi khiếu nại về thiếu hàng, sai hàng cần được báo trong thời gian này để xử lý nhanh theo chính sách đổi trả.",
        ],
      },
    ],
  },
  "doi-tra": {
    heroTag: "Đổi trả linh hoạt",
    highlights: [
      {
        title: "Thời hạn",
        text: "Trong vòng 30 ngày kể từ ngày nhận hàng — sản phẩm chưa sử dụng, còn tem mác và phụ kiện đi kèm (nếu có).",
      },
      {
        title: "Điều kiện",
        text: "Còn hóa đơn điện tử / mã đơn và tình trạng sản phẩm nguyên vẹn theo quy định từng loại hàng.",
      },
      {
        title: "Hoàn tiền",
        text: "Hoàn tiền qua phương thức thanh toán ban đầu trong khoảng 5–10 ngày làm việc sau khi kho nhận và kiểm tra lại hàng.",
      },
    ],
    sections: [
      {
        heading: "Sản phẩm được đổi / trả",
        paragraphs: [
          "Đổi size, đổi màu: trong 30 ngày nếu sản phẩm chưa mặc giặt, chưa sử dụng, còn nguyên tem mác, hộp/túi (nếu có) và phụ kiện đi kèm.",
          "Trả hàng hoàn tiền: áp dụng khi sản phẩm lỗi sản xuất, sai so với mô tả trên website, hoặc gửi nhầm mẫu so với đơn đặt — cần có hình ảnh/video minh chứng trong 48 giờ đầu sau khi nhận.",
          "Hàng khuyến mãi, đồng giá, combo: chỉ đổi/trả nếu lỗi từ nhà sản xuất hoặc do lỗi giao hàng; không đổi trả vì lý do chủ quan (không vừa ý) trừ khi có ghi chú riêng trên trang sản phẩm.",
        ],
      },
      {
        heading: "Sản phẩm không áp dụng hoặc hạn chế",
        paragraphs: [
          "Đồ lót, phụ kiện cá nhân (vớ, mũ đã thử form đặc biệt…) vì lý do vệ sinh — chỉ xử lý khi lỗi kỹ thuật.",
          "Sản phẩm đã giặt, đã cắt mác, có mùi, dấu vết sử dụng rõ rệt.",
          "Hàng nhận quá 30 ngày hoặc không còn chứng từ mua hàng trừ trường hợp bảo hành đặc biệt được xác nhận bằng email.",
        ],
      },
      {
        heading: "Quy trình gửi yêu cầu",
        paragraphs: [
          "Bước 1: Gửi email hoặc form liên hệ kèm mã đơn, SKU sản phẩm, lý do và hình ảnh (toàn thân sản phẩm, tem mác, lỗi nếu có).",
          "Bước 2: CSKH phản hồi trong 1–2 ngày làm việc với mã yêu cầu (RMA) và hướng dẫn đóng gói gửi về kho.",
          "Bước 3: Sau khi kho kiểm tra (thường 2–5 ngày làm việc), chúng tôi xác nhận đổi hàng mới hoặc hoàn tiền. Phí ship gửi về có thể được hoàn/hỗ trợ một phần tùy nguyên nhân (lỗi từ cửa hàng được hoàn phí).",
        ],
      },
    ],
  },
  "thanh-toan": {
    heroTag: "Thanh toán đa dạng",
    highlights: [
      {
        title: "COD",
        text: "Thanh toán khi nhận hàng — kiểm tra gói hàng trước khi trả tiền cho shipper (theo quy định đơn vị vận chuyển).",
      },
      {
        title: "Chuyển khoản / ví / thẻ",
        text: "Thanh toán trực tuyến qua cổng an toàn; danh sách phương thức hiển thị tại bước thanh toán.",
      },
      {
        title: "Bảo mật",
        text: "Giao dịch được mã hóa SSL; chúng tôi không lưu đầy đủ thông tin thẻ trên máy chủ bán lẻ.",
      },
    ],
    sections: [
      {
        heading: "Phương thức thanh toán",
        paragraphs: [
          "COD (Cash on Delivery): thanh toán tiền mặt khi nhận hàng. Một số khu vực hoặc giá trị đơn có thể giới hạn COD — hệ thống sẽ thông báo khi không đủ điều kiện.",
          "Chuyển khoản ngân hàng: thông tin tài khoản hiển thị sau khi đặt hàng; vui lòng ghi đúng mã đơn trong nội dung chuyển khoản để đối soát trong 24 giờ.",
          "Ví điện tử / thẻ quốc tế / QR: theo từng giai đoạn triển khai và hiển thị tại giỏ hàng. Phí giao dịch (nếu có) do ngân hàng/ví thu — FashionStore không thu thêm phí ẩn.",
        ],
      },
      {
        heading: "Xác nhận & xử lý đơn",
        paragraphs: [
          "Đơn thanh toán trực tuyến: được xử lý sau khi cổng thanh toán xác nhận thành công. Nếu giao dịch treo hoặc thất bại, đơn có thể tự hủy sau thời gian chờ — bạn sẽ nhận email thông báo.",
          "Đơn COD: được xác nhận sau khi hệ thống ghi nhận đặt hàng thành công; bạn có thể hủy trước khi hàng chuyển sang trạng thái đang giao (tùy chính sách từng đợt sale).",
        ],
      },
      {
        heading: "Hóa đơn & chứng từ",
        paragraphs: [
          "Hóa đơn điện tử (nếu yêu cầu): gửi trong vòng 7–10 ngày sau khi giao hàng thành công, theo thông tin công ty/cá nhân bạn cung cấp.",
          "Biên lai thanh toán: có thể tải từ email xác nhận đơn hoặc mục Đơn hàng trong tài khoản.",
        ],
      },
    ],
  },
  "bao-mat": {
    heroTag: "Bảo vệ dữ liệu của bạn",
    highlights: [
      {
        title: "Thu thập tối thiểu",
        text: "Chỉ thu thập họ tên, SĐT, email, địa chỉ giao hàng và lịch sử đơn phục vụ giao dịch & hỗ trợ.",
      },
      {
        title: "An toàn lưu trữ",
        text: "Truy cập hệ thống theo vai trò; sao lưu và cập nhật bảo mật định kỳ.",
      },
      {
        title: "Minh bạch",
        text: "Không bán danh sách khách hàng cho bên thứ ba vì mục đích tiếp thị ngoài phạm vi vận hành website.",
      },
    ],
    sections: [
      {
        heading: "Thông tin chúng tôi thu thập",
        paragraphs: [
          "Thông tin tài khoản: email, mật khẩu đã mã hóa, họ tên hiển thị (nếu có).",
          "Thông tin giao dịch: địa chỉ giao hàng, số điện thoại, lịch sử đơn hàng, nội dung chat/email hỗ trợ.",
          "Dữ liệu kỹ thuật: địa chỉ IP, loại thiết bị, cookie (khi bạn đồng ý hoặc theo cài đặt trình duyệt) để vận hành website và chống gian lận.",
        ],
      },
      {
        heading: "Cookie & công cụ phân tích",
        paragraphs: [
          "Cookie phiên: giúp duy trì giỏ hàng và đăng nhập. Cookie phân tích (nếu bật): giúp chúng tôi hiểu hành vi chung trên site (ẩn danh hóa) để cải thiện giao diện và tốc độ.",
          "Bạn có thể xóa cookie trong cài đặt trình duyệt; một số tính năng (giỏ hàng, đăng nhập) có thể yêu cầu bật cookie.",
        ],
      },
      {
        heading: "Quyền của bạn",
        paragraphs: [
          "Yêu cầu xem, chỉnh sửa thông tin liên hệ sai hoặc lỗi thời qua tài khoản hoặc email CSKH.",
          "Yêu cầu xóa tài khoản: trong phạm vi pháp luật cho phép và sau khi hoàn tất nghĩa vụ đơn hàng / bảo hành còn tồn tại.",
          "Rút lại đồng nhận nhận bản tin marketing: bấm 'Hủy đăng ký' trong email hoặc cài đặt tài khoản (khi tính năng có sẵn).",
        ],
      },
      {
        heading: "Liên hệ DPO / bảo mật",
        paragraphs: [
          "Mọi thắc mắc về xử lý dữ liệu cá nhân vui lòng gửi qua trang Liên hệ với tiêu đề 'Bảo mật dữ liệu' — chúng tôi phản hồi trong thời gian hợp lý theo quy định hiện hành.",
        ],
      },
    ],
  },
  "dong-goi": {
    heroTag: "Gói hàng cẩn thận",
    highlights: [
      {
        title: "Nguyên seal",
        text: "Sản phẩm trong túi niêm phong / tem thương hiệu trước khi cho vào hộp carton có dán băng keo.",
      },
      {
        title: "Chống sốc",
        text: "Giấy nền, xốp nổ hoặc tấm đệm phù hợp từng loại — giảm va đập khi vận chuyển.",
      },
      {
        title: "Quà tặng",
        text: "Có thể ghi chú 'Quà tặng — không ghi giá ngoài thùng' khi đặt hàng (tùy khả năng vận hành từng đợt).",
      },
    ],
    sections: [
      {
        heading: "Quy trình đóng gói",
        paragraphs: [
          "Kiểm tra sản phẩm, đối chiếu mã SKU và size trước khi gói.",
          "Bọc mềm bằng giấy chống ẩm (nếu cần), cho vào túi có thương hiệu hoặc túi zip.",
          "Đặt vào thùng carton đúng cỡ, lót đệm, dán băng keo và dán nhãn vận đơn rõ ràng.",
        ],
      },
      {
        heading: "Đồ dễ vỡ & phụ kiện nhỏ",
        paragraphs: [
          "Kính, đồ trang trí cứng: bọc thêm lớp xốp và ghi chú 'Dễ vỡ' trên thùng khi đối tác hỗ trợ.",
          "Phụ kiện nhỏ (khuy, nút dự phòng): đựng trong túi zip gắn trong hộp sản phẩm để tránh rơi rớt.",
        ],
      },
      {
        heading: "Bao bì & môi trường",
        paragraphs: [
          "Chúng tôi ưu tiên giảm nhựa dùng một lần không cần thiết và tái sử dụng thùng carton đạt chuẩn khi phù hợp.",
          "Khách hàng có thể tái chế hoặc tái sử dụng hộp carton, túi giấy sau khi nhận hàng.",
        ],
      },
    ],
  },
  "cam-ket": {
    heroTag: "Chất lượng & chính hãng",
    highlights: [
      {
        title: "Nguồn gốc",
        text: "Hàng hóa nhập qua nhà phân phối / đại lý chính thức hoặc nguồn được kiểm duyệt nội bộ.",
      },
      {
        title: "Kiểm tra",
        text: "Kiểm tra ngẫu nhiên và kiểm tra theo lô trước khi xuất kho — giảm thiểu lỗi đến tay khách.",
      },
      {
        title: "Sau bán",
        text: "Khiếu nại chất lượng được tiếp nhận qua CSKH; xử lý theo chính sách đổi trả và bảo hành (nếu có từng mặt hàng).",
      },
    ],
    sections: [
      {
        heading: "Cam kết minh bạch",
        paragraphs: [
          "Mô tả sản phẩm trên website (chất liệu, form, màu) được biên soạn trung thực; hình ảnh chụp trong điều kiện ánh sáng chuẩn có thể lệch nhẹ so với thực tế do màn hình thiết bị — không cố ý làm lệch màu sắc.",
          "Thông tin khuyến mãi, giảm giá hiển thị rõ thời gian áp dụng và điều kiện kèm theo.",
        ],
      },
      {
        heading: "Hàng chính hãng & kiểm soát chất lượng",
        paragraphs: [
          "Chúng tôi không kinh doanh hàng nhái thương hiệu. Nếu phát hiện nguồn hàng không đạt, lô hàng sẽ bị ngừng bán và thu hồi theo quy trình nội bộ.",
          "Một số dòng sản phẩm có tem chống hàng giả hoặc mã QR truy xuất — thông tin ghi trên bao bì hoặc thẻ treo.",
        ],
      },
      {
        heading: "Khiếu nại & xử lý",
        paragraphs: [
          "Nếu sản phẩm không đúng mô tả nghiêm trọng (sai mẫu, lỗi rõ ràng), vui lòng liên hệ trong 48 giờ kể từ khi nhận hàng kèm hình ảnh chi tiết.",
          "Chúng tôi đề xuất: đổi cùng mẫu (nếu còn hàng), đổi sang mẫu khác có giá trị tương đương, hoặc hoàn tiền theo chính sách đổi trả sau khi kho xác nhận.",
        ],
      },
    ],
  },
};

export function getPolicyDetailBlock(slug: string): PolicyDetailBlock | undefined {
  return POLICY_DETAIL_BLOCKS[slug];
}
