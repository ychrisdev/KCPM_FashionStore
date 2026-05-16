export function getAddressProvince(address: string | undefined): string {
  if (!address) return "";
  const parts = address.split(",");
  return parts[parts.length - 1]?.trim() || "";
}

export function getEstimatedDeliveryTime(
  provinceName: string,
  startDateStr?: string
): string {
  if (!provinceName) return "";
  
  const hcmPattern = /Hồ Chí Minh/i;
  const southPattern = /(Bình Dương|Đồng Nai|Tây Ninh|Bà Rịa|Vũng Tàu|Bình Phước|Long An|Tiền Giang|Bến Tre|Trà Vinh|Vĩnh Long|Đồng Tháp|An Giang|Kiên Giang|Cần Thơ|Hậu Giang|Sóc Trăng|Bạc Liêu|Cà Mau)/i;

  const baseDate = startDateStr ? new Date(startDateStr) : new Date();
  let minDays = 0;
  let maxDays = 0;

  if (hcmPattern.test(provinceName)) {
    minDays = 1;
    maxDays = 2;
  } else if (southPattern.test(provinceName)) {
    minDays = 2;
    maxDays = 3;
  } else {
    minDays = 3;
    maxDays = 5;
  }

  const minDate = new Date(baseDate);
  minDate.setDate(minDate.getDate() + minDays);
  const maxDate = new Date(baseDate);
  maxDate.setDate(maxDate.getDate() + maxDays);

  const formatDate = (date: Date) => {
    const d = date.getDate().toString().padStart(2, '0');
    const m = (date.getMonth() + 1).toString().padStart(2, '0');
    return `${d}/${m}`;
  };

  return `${formatDate(minDate)} - ${formatDate(maxDate)}`;
}

export function shouldShowDeliveryEstimate(status: string): boolean {
  return ["pending", "shipping", "awaiting_confirmation"].includes(status);
}
