import type { User } from "../types";

export function hasPermission(user: User | null, scope: string): boolean {
  return Boolean(user && user.is_active !== false && (user.is_admin || user.role?.permissions?.includes(scope)));
}
