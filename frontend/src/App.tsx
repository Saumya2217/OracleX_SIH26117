import React, { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { BusinessRequest, Company, DocumentItem, TaskItem, User } from "./types";
import { api } from "./services/api";
import { AppRoute, isRouteAllowed, pathForRoute, routeFromLocation, TabId } from "./routing";
import { Header } from "./components/Header";
import { Sidebar } from "./components/Sidebar";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { OverviewPage } from "./pages/OverviewPage";
import { PeoplePage } from "./pages/PeoplePage";
import { DepartmentsPage } from "./pages/DepartmentsPage";
import { RolesPage } from "./pages/RolesPage";
import { WorkPage } from "./pages/WorkPage";
import { FilesPage } from "./pages/FilesPage";
import { AIAssistantPage } from "./pages/AIAssistantPage";
import { ApprovalsPage } from "./pages/ApprovalsPage";
import { ActivityPage } from "./pages/ActivityPage";
import { SettingsPage } from "./pages/SettingsPage";
import { NotificationsPage } from "./pages/NotificationsPage";
import { requestDrafts, requestDraftScope } from "./services/requestDrafts";
import { ModalSurface } from "./components/ui/ModalSurface";

type WorkspaceDataErrors = Partial<Record<"company" | "tasks" | "requests" | "documents", string>>;

const fetchWorkspaceData = async (user: User, signal: AbortSignal) => {
  const canReview = user.is_admin || user.role?.permissions?.includes("workflow:approve");
  const [company, tasks, requests, documents] = await Promise.allSettled([
    api.getCompanyProfile(signal), api.getTasks(signal), api.getRequests(canReview ? "review" : "mine", undefined, signal), api.getDocuments(false, signal),
  ]);
  const errors: WorkspaceDataErrors = {};
  if (company.status === "rejected") errors.company = "Company profile could not be loaded.";
  if (tasks.status === "rejected") errors.tasks = "Work summary could not be loaded.";
  if (requests.status === "rejected") errors.requests = "Request summary could not be loaded.";
  if (documents.status === "rejected") errors.documents = "Document summary could not be loaded.";
  return {
    company: company.status === "fulfilled" ? company.value : null,
    tasks: tasks.status === "fulfilled" ? tasks.value : [],
    requests: requests.status === "fulfilled" ? requests.value : [],
    documents: documents.status === "fulfilled" ? documents.value : [],
    errors,
  };
};

export const App: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [company, setCompany] = useState<Company | null>(null);
  const [route, setRoute] = useState<AppRoute>(() => routeFromLocation(window.location));
  const [initialAssistantPrompt, setInitialAssistantPrompt] = useState("");
  const [isInitializing, setIsInitializing] = useState(true);
  const [authView, setAuthView] = useState<"login" | "register">("login");
  const [mobileNavigationOpen, setMobileNavigationOpen] = useState(false);
  const [confirmSignOut, setConfirmSignOut] = useState(false);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [requests, setRequests] = useState<BusinessRequest[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [dataErrors, setDataErrors] = useState<WorkspaceDataErrors>({});
  const [dataLoaded, setDataLoaded] = useState(false);
  const dataController = useRef<AbortController | null>(null);
  useSyncExternalStore(requestDrafts.subscribe, requestDrafts.getSnapshot);
  const pendingRequestCount = currentUser ? requestDrafts.list(requestDraftScope(currentUser)).length : 0;
  useEffect(() => {
    const warnOnUnload = (event: BeforeUnloadEvent) => {
      if (!currentUser || requestDrafts.list(requestDraftScope(currentUser)).length === 0) return;
      event.preventDefault(); event.returnValue = "";
    };
    window.addEventListener("beforeunload", warnOnUnload);
    return () => window.removeEventListener("beforeunload", warnOnUnload);
  }, [currentUser]);

  const loadData = async (userOverride?: User | null) => {
    const activeUser = userOverride === undefined ? currentUser : userOverride;
    if (!activeUser) return;
    dataController.current?.abort();
    const controller = new AbortController();
    dataController.current = controller;
    api.invalidateCache();
    setDataLoaded(false);
    const snapshot = await fetchWorkspaceData(activeUser, controller.signal);
    if (controller.signal.aborted) return;
    setCompany(snapshot.company); setTasks(snapshot.tasks); setRequests(snapshot.requests); setDocuments(snapshot.documents);
    setDataErrors(snapshot.errors); setDataLoaded(true);
    if (dataController.current === controller) dataController.current = null;
  };

  const replaceRoute = (next: AppRoute) => {
    window.history.replaceState({}, "", pathForRoute(next));
    setRoute(next);
  };
  const pushRoute = (next: AppRoute) => {
    const nextPath = pathForRoute(next);
    if (`${window.location.pathname}${window.location.search}` !== nextPath) window.history.pushState({}, "", nextPath);
    setRoute(next);
  };
  const navigate = (tab: string, initialPrompt?: string, entityId?: string) => {
    const next: AppRoute = { tab: tab as TabId, entityId };
    if (currentUser && !isRouteAllowed(next, currentUser.is_admin === true, currentUser.role?.permissions || [])) {
      pushRoute({ tab: "home" });
    } else {
      pushRoute(next);
    }
    setInitialAssistantPrompt(tab === "assistant" ? initialPrompt || "" : "");
    setMobileNavigationOpen(false);
    if (next.tab === "home" && currentUser) void loadData();
  };

  useEffect(() => {
    const onPopState = () => {
      const requested = routeFromLocation(window.location);
      if (currentUser && !isRouteAllowed(requested, currentUser.is_admin === true, currentUser.role?.permissions || [])) {
        window.history.replaceState({}, "", pathForRoute({ tab: "home" }));
        setRoute({ tab: "home" });
      } else setRoute(requested);
      setInitialAssistantPrompt("");
      setMobileNavigationOpen(false);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [currentUser]);

  useEffect(() => {
    if (!currentUser || isInitializing) return;
    const frame = window.requestAnimationFrame(() => {
      const heading = document.querySelector<HTMLElement>("#main-content h1");
      if (!heading) return;
      heading.tabIndex = -1;
      heading.focus({ preventScroll: true });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [route.tab, currentUser, isInitializing]);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    api.getMe(controller.signal).catch(() => null).then(async (user) => {
      if (!active || !user) return;
      api.setScope(user.company_id, user.id);
      setCurrentUser(user);
      const requested = routeFromLocation(window.location);
      if (!isRouteAllowed(requested, user.is_admin === true, user.role?.permissions || [])) replaceRoute({ tab: "home" });
      const snapshot = await fetchWorkspaceData(user, controller.signal);
      if (active && !controller.signal.aborted) {
        setCompany(snapshot.company); setTasks(snapshot.tasks); setRequests(snapshot.requests); setDocuments(snapshot.documents);
        setDataErrors(snapshot.errors); setDataLoaded(true);
      }
    }).catch((error) => console.error("Init error:", error)).finally(() => active && setIsInitializing(false));
    return () => { active = false; controller.abort(); };
  }, []);

  const handleLoginSuccess = async (user: User) => {
    api.setScope(user.company_id, user.id);
    setCurrentUser(user);
    const requested = routeFromLocation(window.location);
    if (!isRouteAllowed(requested, user.is_admin === true, user.role?.permissions || [])) replaceRoute({ tab: "home" });
    else if (window.location.pathname === "/") replaceRoute({ tab: "home" });
    await loadData(user);
  };
  const finishLogout = () => {
    if (currentUser) {
      const scope = requestDraftScope(currentUser);
      requestDrafts.clear(scope);
    }
    dataController.current?.abort();
    dataController.current = null;
    api.clearToken(); setCurrentUser(null); setCompany(null); setTasks([]); setRequests([]); setDocuments([]);
    setDataErrors({}); setDataLoaded(false);
    setInitialAssistantPrompt(""); setMobileNavigationOpen(false); setAuthView("login"); setConfirmSignOut(false);
  };
  const handleLogout = () => {
    if (pendingRequestCount) setConfirmSignOut(true);
    else finishLogout();
  };

  if (isInitializing) return <div className="app-loading"><span className="pulse-indicator" /> Loading workspace…</div>;
  if (!currentUser) return authView === "register"
    ? <RegisterPage onRegisterSuccess={handleLoginSuccess} onNavigateToLogin={() => setAuthView("login")} />
    : <LoginPage onLoginSuccess={handleLoginSuccess} onNavigateToRegister={() => setAuthView("register")} />;

  const pendingCount = requests.filter((item) => item.status === "SUBMITTED" || item.status === "ASSIGNED").length;
  const safeRoute = isRouteAllowed(route, currentUser.is_admin === true, currentUser.role?.permissions || []) ? route : { tab: "home" as const };

  return <div className="app-container">
    <a className="skip-link" href="#main-content">Skip to main content</a>
    <Sidebar currentUser={currentUser} currentTab={safeRoute.tab} onSelectTab={(tab) => navigate(tab)} pendingApprovalsCount={pendingCount} isOpen={mobileNavigationOpen} onClose={() => setMobileNavigationOpen(false)} />
    <div className="main-content">
      <Header currentUser={currentUser} company={company} currentTabName={safeRoute.tab} onLogout={handleLogout} navigationOpen={mobileNavigationOpen} onToggleNavigation={() => setMobileNavigationOpen((open) => !open)} pendingRequestCount={pendingRequestCount} onResumeRequests={() => navigate("requests")} />
      <main className="content-viewport" id="main-content" tabIndex={-1}>
        {safeRoute.tab === "home" && <OverviewPage currentUser={currentUser} company={company} tasks={tasks} requests={requests} documents={documents} dataErrors={dataErrors} dataLoaded={dataLoaded} onRefresh={() => void loadData()} onNavigate={navigate} />}
        {safeRoute.tab === "people" && <PeoplePage currentUser={currentUser} />}
        {safeRoute.tab === "departments" && <DepartmentsPage currentUser={currentUser} />}
        {safeRoute.tab === "roles" && <RolesPage />}
        {safeRoute.tab === "work" && <WorkPage currentUser={currentUser} />}
        {safeRoute.tab === "files" && <FilesPage user={currentUser} initialDocumentId={safeRoute.entityId} initialVersionId={safeRoute.versionId} onDocumentChange={(id, versionId) => pushRoute({ tab: "files", entityId: id, versionId })} />}
        {safeRoute.tab === "assistant" && <AIAssistantPage key={`ask-${safeRoute.entityId || "new"}`} user={currentUser} initialPrompt={initialAssistantPrompt} initialConversationId={safeRoute.entityId} onConversationChange={(id) => pushRoute({ tab: "assistant", entityId: id })} onNavigateToRequests={(requestId) => navigate("requests", undefined, requestId)} />}
        {safeRoute.tab === "requests" && <ApprovalsPage currentUser={currentUser} initialRequestId={safeRoute.entityId} onRequestChange={(id) => pushRoute({ tab: "requests", entityId: id })} onRefreshData={() => void loadData()} />}
        {safeRoute.tab === "notifications" && <NotificationsPage onOpenRequest={(id) => navigate("requests", undefined, id)} />}
        {safeRoute.tab === "activity" && <ActivityPage currentUser={currentUser} />}
        {safeRoute.tab === "settings" && <SettingsPage />}
      </main>
    </div>
    {confirmSignOut && <ModalSurface labelledBy="sign-out-title" onClose={() => setConfirmSignOut(false)}>
      <div className="sign-out-confirmation">
        <h2 id="sign-out-title">Unsaved request text</h2>
        <p>Signing out will discard {pendingRequestCount} unsaved request {pendingRequestCount === 1 ? "entry" : "entries"}. Saved company records will be kept.</p>
        <div className="request-actions">
          <button className="btn-secondary" onClick={() => setConfirmSignOut(false)}>Keep working</button>
          <button className="btn-primary" onClick={finishLogout}>Discard text and sign out</button>
        </div>
      </div>
    </ModalSurface>}
  </div>;
};

export default App;
