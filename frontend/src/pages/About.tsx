import "../styles/pages/About.css";

const features = [
  {
    icon: '◈',
    title: 'Chất Lượng Cao',
    desc: 'Mỗi sản phẩm được chọn lọc kỹ lưỡng từ các nhà sản xuất uy tín, sử dụng nguyên liệu cao cấp và tay nghề thượng hạng.',
  },
  {
    icon: '◎',
    title: 'Giao Hàng Nhanh',
    desc: 'Miễn phí giao hàng nhanh cho đơn từ 500.000đ. Đơn hàng được giao trong vòng 2–3 ngày làm việc.',
  },
  {
    icon: '◇',
    title: 'Giá Tốt Nhất',
    desc: 'Chúng tôi làm việc trực tiếp với nhà sản xuất để mang đến chất lượng tốt nhất với mức giá cạnh tranh nhất.',
  },
];

export default function About() {
  return (
    <>
      <section className="hero">
        <div className="container">
          <div className="heroInner">

            <div className="heroText">
              <span className="tag">Thành lập 2026</span>

              <h1 className="heroTitle">
                Về Thương Hiệu Của Chúng Tôi
              </h1>

              <p className="heroSubtitle">
                Chúng tôi tin rằng thời trang không chỉ là trang phục —
                đó là cách thể hiện bản thân, là tuyên ngôn giá trị
                và là cầu nối giữa các nền văn hóa.
              </p>
            </div>

            <div className="heroImageGrid">
              <img
                src="https://bizweb.dktcdn.net/100/369/010/products/dico-x-rls9722-copy-compressed-08238205-d381-4655-aeb2-bd936234211d.jpg?v=1766811407193"
                alt="Thương hiệu thời trang"
                className="heroImg1"
              />

              <img
                src="https://bd-media-production.hcm.ss.bfcplatform.vn/upload_media/31-03-26/1774951057042_429375.png"
                alt="Bộ sưu tập thời trang"
                className="heroImg2"
              />
            </div>

          </div>
        </div>
      </section>

      <section className="storySection">
        <div className="container">
          <div className="storyGrid">

            <div className="storyImageWrapper">
              <img
                src="https://bizweb.dktcdn.net/100/369/010/files/002.jpg?v=1676537144959"
                alt="Câu chuyện của chúng tôi"
                className="storyImage"
              />
              <div className="storyImageAccent"></div>
            </div>

            <div className="storyContent">
              <span className="sectionTag">Câu Chuyện Của Chúng Tôi</span>

              <h2 className="storyTitle">
                Kiến Tạo Phong Cách,<br />Xây Dựng Tự Tin
              </h2>

              <p className="storyText">
                Được thành lập năm 2026 tại trung tâm TP. Hồ Chí Minh,
                FashionStore ra đời từ một ý tưởng đơn giản:
                mọi người đều xứng đáng được mặc những bộ trang phục đẹp,
                chất lượng mà không phải đánh đổi giá trị hay ngân sách của mình.
              </p>

              <p className="storyText">
                Đội ngũ nhà thiết kế và biên tập viên đầy nhiệt huyết
                của chúng tôi không ngừng tìm kiếm những chất liệu tốt nhất
                và những phong cách sáng tạo nhất.
              </p>

              <p className="storyText">
                Ngày nay, chúng tôi phục vụ hơn 50.000 khách hàng
                trên khắp Việt Nam và vẫn đang không ngừng phát triển.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="featuresSection">
        <div className="container">

          <div className="featureHeader">
            <span className="sectionTag">Tại Sao Chọn Chúng Tôi</span>
            <h2 className="sectionTitle">Cam Kết Của Chúng Tôi</h2>
            <p className="sectionSubtitle">
              Tất cả những gì chúng tôi làm đều hướng đến bạn
            </p>
          </div>

          <div className="featuresGrid">

            {features.map(({ icon, title, desc }) => (
              <div key={title} className="featureCard">
                <div className="featureIcon">{icon}</div>
                <h3 className="featureTitle">{title}</h3>
                <p className="featureDesc">{desc}</p>
              </div>
            ))}

          </div>
        </div>
      </section>
    </>
  );
}