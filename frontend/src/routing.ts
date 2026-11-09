export type TabId = "home" | "files" | "assistant" | "work" | "requests" | "notifications" | "people" | "departments" | "roles" | "activity" | "settings";

export interface AppRoute {
  tab: TabId;
  entityId?: string;
  versionId?: string;
}

const decodeSegment = (value?: string) => {
  if (!value) return undefined;
  try { return decodeURIComponent(value); } catch { return undefined; }
};

export const routeFromLocation = (location: Pick<Location, "pathname" | "search">): AppRoute => {
  const path = location.pathname.replace(/\/+$/, "") || "/";
  const segments = path.split("/").filter(Boolean);

  if (segments[0] === "overview") return { tab: "home" };
  if (segments[0] === "documents") {
    return {
      tab: "files",
      entityId: decodeSegment(segments[1]),
      versionId: segments[2] === "versions" ? decodeSegment(segments[3]) : undefined,
    };
  }
  if (segments[0] === "ask") return { tab: "assistant", entityId: decodeSegment(segments[1]) };
  if (segments[0] === "requests") return { tab: "requests", entityId: decodeSegment(segments[1]) };
  if (segments[0] === "notifications") return { tab: "notifications" };
  if (segments[0] === "work") return { tab: "work" };
  if (segments[0] === "admin" && segments[1] === "people") return { tab: "people" };
  if (segments[0] === "admin" && segments[1] === "teams") return { tab: "departments" };
  if (segments[0] === "admin" && segments[1] === "roles") return { tab: "roles" };
  if (segments[0] === "admin" && segments[1] === "audit") return { tab: "activity" };
  if (segments[0] === "admin" && segments[1] === "system") return { tab: "settings" };

  // Compatibility with links issued before path-based routing was introduced.
  const params = new URLSearchParams(location.search);
  const legacyTab = params.get("tab");
  if (legacyTab === "requests") return { tab: "requests", entityId: params.get("requestId") || undefined };
  return { tab: "home" };
};

export const pathForRoute = (route: AppRoute): string => {
  const id = route.entityId ? `/${encodeURIComponent(route.entityId)}` : "";
  switch (route.tab) {
    case "home": return "/overview";
    case "files": return `/documents${id}${route.entityId && route.versionId ? `/versions/${encodeURIComponent(route.versionId)}` : ""}`;
    case "assistant": return `/ask${id}`;
    case "work": return "/work";
    case "requests": return `/requests${id}`;
    case "notifications": return "/notifications";
    case "people": return "/admin/people";
    case "departments": return "/admin/teams";
    case "roles": return "/admin/roles";
    case "activity": return "/admin/audit";
    case "settings": return "/admin/system";
  }
};

export const isRouteAllowed = (route: AppRoute, isAdmin: boolean, permissions: string[]) => {
  if (["departments", "roles", "settings"].includes(route.tab)) return isAdmin;
  if (route.tab === "activity") return isAdmin || permissions.includes("audit:view");
  return true;
};
