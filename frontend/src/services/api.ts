import {
  User, Company, HierarchyNode, DocumentItem, DocumentDetail, DocumentUploadResult,
  IngestionJobItem, AgentResponse, ConversationDetail, ConversationSummary,
  TaskItem, BusinessRequest, BusinessRequestDetail, InternalNotification, RequestReviewer,
  AdaptationProposal, AuditLogItem
} from "../types";
import { queryCache } from "./queryCache";
import { ApiError, apiErrorMessage } from "./apiErrors";
import type { ApiSchema } from "../types/openapi.generated";

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") || "/api";

class ApiService {
  public setScope(companyId: string, userId: string) {
    queryCache.setScope(companyId, userId);
  }

  public invalidateCache() {
    queryCache.invalidate();
  }

  private getToken(): string | null {
    return localStorage.getItem("oraclex_token");
  }

  public setToken(token: string) {
    queryCache.clear();
    localStorage.setItem("oraclex_token", token);
  }

  public clearToken() {
    queryCache.clear();
    localStorage.removeItem("oraclex_token");
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const method = (options.method || "GET").toUpperCase();
    const cacheable = method === "GET" && [
      "/company/profile", "/company/departments", "/company/roles", "/users/", "/workflows/tasks",
    ].includes(endpoint);
    return queryCache.load(endpoint, async (signal) => {
      const token = this.getToken();
      const headers: Record<string, string> = { ...(options.headers as Record<string, string> || {}) };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (!(options.body instanceof FormData) && !headers["Content-Type"]) headers["Content-Type"] = "application/json";

      const resp = await fetch(`${API_BASE}${endpoint}`, { ...options, headers, signal });
      if (!resp.ok) {
        let errorBody: unknown;
        try {
          errorBody = await resp.json();
        } catch { /* response was not JSON */ }
        if (resp.status === 401) this.clearToken();
        throw new ApiError(resp.status, apiErrorMessage(errorBody, resp.status));
      }
      const data = resp.status === 204 ? undefined as T : await resp.json() as T;
      if (method !== "GET") this.invalidateCache();
      return data;
    }, { signal: options.signal ?? undefined, maxAgeMs: cacheable ? 5000 : 0, restartOnInvalidate: method === "GET" });
  }

  // Auth
  async login(email: string, password: string): Promise<ApiSchema<"TokenResponse">> {
    const data = await this.request<ApiSchema<"TokenResponse">>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    });
    this.setToken(data.access_token);
    this.setScope(data.user.company_id, data.user.id);
    return data;
  }

  async registerCompany(payload: {
    company_name: string;
    industry: string;
    domain: string;
    admin_name: string;
    admin_email: string;
    password: string;
    setup_token: string;
  }): Promise<ApiSchema<"TokenResponse">> {
    const data = await this.request<ApiSchema<"TokenResponse">>("/auth/register-company", {
      method: "POST",
      headers: { "X-Setup-Token": payload.setup_token },
      body: JSON.stringify({
        company_name: payload.company_name,
        industry: payload.industry,
        domain: payload.domain,
        admin_name: payload.admin_name,
        admin_email: payload.admin_email,
        password: payload.password
      })
    });
    this.setToken(data.access_token);
    this.setScope(data.user.company_id, data.user.id);
    return data;
  }

  async getMe(signal?: AbortSignal): Promise<User> {
    return this.request<User>("/auth/me", { signal });
  }

  async getBootstrapStatus(): Promise<ApiSchema<"BootstrapStatusResponse">> {
    return this.request<ApiSchema<"BootstrapStatusResponse">>("/auth/bootstrap-status");
  }

  // Company
  async getCompanyProfile(signal?: AbortSignal): Promise<Company> {
    return this.request<Company>("/company/profile", { signal });
  }

  async getOrgHierarchy(): Promise<HierarchyNode> {
    return this.request<HierarchyNode>("/company/hierarchy");
  }

  async getDepartments(signal?: AbortSignal): Promise<ApiSchema<"DepartmentResponse">[]> {
    return this.request<ApiSchema<"DepartmentResponse">[]>("/company/departments", { signal });
  }

  async createDepartment(dept: { name: string; code: string; description?: string }): Promise<ApiSchema<"DepartmentResponse">> {
    return this.request<ApiSchema<"DepartmentResponse">>("/company/departments", {
      method: "POST",
      body: JSON.stringify(dept)
    });
  }

  async updateDepartment(id: string, updates: { name?: string; code?: string; description?: string }): Promise<ApiSchema<"DepartmentResponse">> {
    return this.request<ApiSchema<"DepartmentResponse">>(`/company/departments/${id}`, {
      method: "PUT",
      body: JSON.stringify(updates)
    });
  }

  async deleteDepartment(id: string): Promise<ApiSchema<"DepartmentDeleteResponse">> {
    return this.request<ApiSchema<"DepartmentDeleteResponse">>(`/company/departments/${id}`, {
      method: "DELETE"
    });
  }

  async getRoles(signal?: AbortSignal): Promise<ApiSchema<"RoleResponse">[]> {
    return this.request<ApiSchema<"RoleResponse">[]>("/company/roles", { signal });
  }

  // Knowledge
  async getDocuments(includeArchived = false, signal?: AbortSignal): Promise<DocumentItem[]> {
    return this.request<DocumentItem[]>(`/knowledge/documents?include_archived=${includeArchived}`, { signal });
  }

  async getDocumentChunks(docId: string, signal?: AbortSignal): Promise<ApiSchema<"DocumentChunkResponse">[]> {
    return this.request<ApiSchema<"DocumentChunkResponse">[]>(`/knowledge/documents/${docId}/chunks`, { signal });
  }

  async downloadDocumentVersion(docId: string, versionId: string, filename: string): Promise<void> {
    const token = this.getToken();
    const response = await fetch(`${API_BASE}/knowledge/documents/${docId}/versions/${versionId}/source`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) {
      let errorBody: unknown;
      try { errorBody = await response.json(); } catch { /* response was not JSON */ }
      if (response.status === 401) this.clearToken();
      throw new ApiError(response.status, apiErrorMessage(errorBody, response.status));
    }
    const url = URL.createObjectURL(await response.blob());
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  async searchKnowledge(query: string, limit: number = 5): Promise<ApiSchema<"VectorSearchResultItem">[]> {
    return this.request<ApiSchema<"VectorSearchResultItem">[]>("/knowledge/search", {
      method: "POST",
      body: JSON.stringify({ query, limit })
    });
  }

  async uploadDocument(formData: FormData): Promise<DocumentUploadResult> {
    return this.request<DocumentUploadResult>("/knowledge/upload", {
      method: "POST",
      body: formData
    });
  }

  async uploadDocumentVersion(docId: string, file: File): Promise<DocumentUploadResult> {
    const formData = new FormData();
    formData.append("file", file);
    return this.request<DocumentUploadResult>(`/knowledge/documents/${docId}/versions`, {
      method: "POST",
      body: formData
    });
  }

  async getIngestionJob(jobId: string): Promise<IngestionJobItem> {
    return this.request<IngestionJobItem>(`/knowledge/jobs/${jobId}`);
  }

  async retryIngestionJob(jobId: string): Promise<IngestionJobItem> {
    return this.request<IngestionJobItem>(`/knowledge/jobs/${jobId}/retry`, { method: "POST" });
  }

  async archiveDocument(docId: string): Promise<DocumentItem> {
    return this.request<DocumentItem>(`/knowledge/documents/${docId}/archive`, { method: "POST" });
  }

  async restoreDocument(docId: string): Promise<DocumentItem> {
    return this.request<DocumentItem>(`/knowledge/documents/${docId}/restore`, { method: "POST" });
  }

  async deleteDocument(docId: string): Promise<{ status: string; id: string }> {
    return this.request<{ status: string; id: string }>(`/knowledge/documents/${docId}`, {
      method: "DELETE"
    });
  }

  // Agents
  async queryAgent(message: string, conversationId?: string, imageBase64?: string): Promise<AgentResponse> {
    return this.request<AgentResponse>("/agents/query", {
      method: "POST",
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
        image_base64: imageBase64
      })
    });
  }

  async getAiHealth(signal?: AbortSignal): Promise<ApiSchema<"AgentHealthResponse">> {
    return this.request<ApiSchema<"AgentHealthResponse">>("/agents/health", { signal });
  }

  async submitFeedback(queryText: string, agentResponse: string, rating: number, correction?: string): Promise<ApiSchema<"FeedbackSubmitResponse">> {
    return this.request<ApiSchema<"FeedbackSubmitResponse">>("/agents/feedback", {
      method: "POST",
      body: JSON.stringify({
        query_text: queryText,
        agent_response: agentResponse,
        rating,
        correction
      })
    });
  }

  async getConversations(includeArchived = false, signal?: AbortSignal): Promise<ConversationSummary[]> {
    return this.request<ConversationSummary[]>(`/conversations?include_archived=${includeArchived}`, { signal });
  }

  async getConversation(id: string, signal?: AbortSignal): Promise<ConversationDetail> {
    return this.request<ConversationDetail>(`/conversations/${id}`, { signal });
  }

  async updateConversation(id: string, updates: { title?: string; status?: "ACTIVE" | "ARCHIVED" }): Promise<ConversationSummary> {
    return this.request<ConversationSummary>(`/conversations/${id}`, {
      method: "PATCH",
      body: JSON.stringify(updates)
    });
  }

  // Workflows & Tasks
  async getWorkflows(): Promise<ApiSchema<"WorkflowResponse">[]> {
    return this.request<ApiSchema<"WorkflowResponse">[]>("/workflows/");
  }

  async getTasks(signal?: AbortSignal): Promise<TaskItem[]> {
    return this.request<TaskItem[]>("/workflows/tasks", { signal });
  }

  async createTask(task: ApiSchema<"TaskCreate">): Promise<TaskItem> {
    return this.request<TaskItem>("/workflows/tasks", {
      method: "POST",
      body: JSON.stringify(task)
    });
  }

  async updateTask(id: string, updates: ApiSchema<"TaskUpdate">): Promise<TaskItem> {
    return this.request<TaskItem>(`/workflows/tasks/${id}`, {
      method: "PATCH",
      body: JSON.stringify(updates)
    });
  }

  async getRequests(view: "mine" | "review" = "mine", statusFilter?: string, signal?: AbortSignal): Promise<BusinessRequest[]> {
    const params = new URLSearchParams({ view });
    if (statusFilter) params.set("status_filter", statusFilter);
    return this.request<BusinessRequest[]>(`/requests?${params.toString()}`, { signal });
  }

  async getRequestReviewers(requestId?: string, signal?: AbortSignal): Promise<RequestReviewer[]> {
    const params = new URLSearchParams();
    if (requestId) params.set("request_id", requestId);
    return this.request<RequestReviewer[]>(`/requests/reviewers/eligible?${params}`, { signal });
  }

  async getRequest(id: string, signal?: AbortSignal): Promise<BusinessRequestDetail> {
    return this.request<BusinessRequestDetail>(`/requests/${id}`, { signal });
  }

  async createRequest(payload: ApiSchema<"BusinessRequestCreate">): Promise<BusinessRequestDetail> {
    return this.request<BusinessRequestDetail>("/requests", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  async updateRequest(id: string, payload: ApiSchema<"BusinessRequestUpdate">): Promise<BusinessRequestDetail> {
    return this.request<BusinessRequestDetail>(`/requests/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    });
  }

  async submitRequest(id: string, expectedLockVersion: number): Promise<BusinessRequestDetail> {
    return this.request<BusinessRequestDetail>(`/requests/${id}/submit`, {
      method: "POST",
      body: JSON.stringify({ expected_lock_version: expectedLockVersion })
    });
  }

  async assignRequest(id: string, reviewerId: string, expectedLockVersion: number): Promise<BusinessRequestDetail> {
    return this.request<BusinessRequestDetail>(`/requests/${id}/assign`, {
      method: "POST",
      body: JSON.stringify({ reviewer_id: reviewerId, expected_lock_version: expectedLockVersion })
    });
  }

  async decideRequest(id: string, decision: "APPROVED" | "REJECTED", reason: string, submittedVersionId: string, expectedLockVersion: number): Promise<BusinessRequestDetail> {
    return this.request<BusinessRequestDetail>(`/requests/${id}/decision`, {
      method: "POST",
      body: JSON.stringify({ decision, reason, submitted_version_id: submittedVersionId, expected_lock_version: expectedLockVersion })
    });
  }

  async fulfillRequest(id: string, notes: string, expectedLockVersion: number): Promise<BusinessRequestDetail> {
    return this.request<BusinessRequestDetail>(`/requests/${id}/fulfill`, {
      method: "POST",
      body: JSON.stringify({ notes, expected_lock_version: expectedLockVersion })
    });
  }

  async cancelRequest(id: string, reason: string, expectedLockVersion: number): Promise<BusinessRequestDetail> {
    return this.request<BusinessRequestDetail>(`/requests/${id}/cancel`, {
      method: "POST",
      body: JSON.stringify({ reason, expected_lock_version: expectedLockVersion })
    });
  }

  async getNotifications(unreadOnly = false, signal?: AbortSignal, before?: { created_at: string; id: string }, limit = 25): Promise<InternalNotification[]> {
    const params = new URLSearchParams({ unread_only: String(unreadOnly), limit: String(limit) });
    if (before) { params.set("before_created_at", before.created_at); params.set("before_id", before.id); }
    return this.request<InternalNotification[]>(`/requests/notifications/inbox?${params}`, { signal });
  }

  async markNotificationRead(id: string, signal?: AbortSignal): Promise<InternalNotification> {
    return this.request<InternalNotification>(`/requests/notifications/${id}/read`, { method: "POST", signal });
  }

  // Adaptation (Levels 3 & 4)
  async getProposals(): Promise<AdaptationProposal[]> {
    return this.request<AdaptationProposal[]>("/adaptation/proposals");
  }

  async reviewProposal(id: string, status: "ACCEPTED" | "REJECTED", reviewNotes?: string): Promise<AdaptationProposal> {
    return this.request<AdaptationProposal>(`/adaptation/proposals/${id}/review`, {
      method: "POST",
      body: JSON.stringify({ status, review_notes: reviewNotes })
    });
  }

  // Users & Personnel
  async getUsers(signal?: AbortSignal): Promise<User[]> {
    return this.request<User[]>("/users/", { signal });
  }

  async createUser(user: ApiSchema<"UserCreateRequest">): Promise<User> {
    return this.request<User>("/users/", {
      method: "POST",
      body: JSON.stringify(user)
    });
  }

  async updateUser(id: string, updates: ApiSchema<"UserUpdateRequest">): Promise<User> {
    return this.request<User>(`/users/${id}`, {
      method: "PUT",
      body: JSON.stringify(updates)
    });
  }

  async toggleUserStatus(id: string): Promise<User> {
    return this.request<User>(`/users/${id}/status`, {
      method: "PATCH"
    });
  }

  async deleteUser(id: string): Promise<void> {
    return this.request<void>(`/users/${id}`, {
      method: "DELETE"
    });
  }

  async getDocumentDetail(id: string, signal?: AbortSignal): Promise<DocumentDetail> {
    return this.request<DocumentDetail>(`/knowledge/documents/${id}/detail`, { signal });
  }

  // Audit
  async getAuditLogs(action?: string, status?: string, signal?: AbortSignal, before?: { timestamp: string; id: string }, limit = 25): Promise<AuditLogItem[]> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (action?.trim()) params.set("action", action.trim());
    if (status) params.set("status", status);
    if (before) { params.set("before_timestamp", before.timestamp); params.set("before_id", before.id); }
    return this.request<AuditLogItem[]>(`/audit/logs?${params.toString()}`, { signal });
  }

  async verifyAuditIntegrity(): Promise<ApiSchema<"AuditIntegrityResponse">> {
    return this.request<ApiSchema<"AuditIntegrityResponse">>("/audit/verify-integrity");
  }
}

export const api = new ApiService();
