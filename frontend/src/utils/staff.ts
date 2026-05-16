/** Role từ backend Profile — khách hàng không vào được /admin */
const STAFF_ROLES = ['staff', 'admin'] as const;

export function isStaffRole(role: string | null | undefined): boolean {
  return role != null && STAFF_ROLES.includes(role as (typeof STAFF_ROLES)[number]);
}
