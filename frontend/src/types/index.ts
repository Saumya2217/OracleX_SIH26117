import type { ApiSchema } from "./openapi.generated";

// API response types have one source of truth: the generated FastAPI schemas.
export type User = ApiSchema<"UserResponse">;
export type Company = ApiSchema<"CompanyResponse">;
export type HierarchyNode = ApiSchema<"HierarchyNode">;
export type DocumentItem = ApiSchema<"DocumentResponse">;
export type DocumentVersionItem = ApiSchema<"DocumentVersionResponse">;
export type IngestionJobItem = ApiSchema<"IngestionJobResponse">;
export type DocumentUploadResult = ApiSchema<"DocumentUploadResponse">;
export type DocumentDetail = ApiSchema<"DocumentDetailResponse">;
export type AgentCitation = ApiSchema<"AgentCitation">;
export type AgentResponse = ApiSchema<"AgentQueryResponse">;
export type PersistedAgentRun = ApiSchema<"PersistedAgentRunResponse">;
export type ConversationMessage = ApiSchema<"ConversationMessageResponse">;
export type ConversationSummary = ApiSchema<"ConversationSummaryResponse">;
export type ConversationDetail = ApiSchema<"ConversationDetailResponse">;
export type TaskItem = ApiSchema<"TaskResponse">;
export type BusinessRequestVersion = ApiSchema<"BusinessRequestVersionResponse">;
export type BusinessRequestEvent = ApiSchema<"BusinessRequestEventResponse">;
export type BusinessRequest = ApiSchema<"BusinessRequestResponse">;
export type BusinessRequestDetail = ApiSchema<"BusinessRequestDetailResponse">;
export type InternalNotification = ApiSchema<"InternalNotificationResponse">;
export type RequestReviewer = ApiSchema<"RequestReviewerResponse">;
export type AdaptationProposal = ApiSchema<"AdaptationProposalResponse">;
export type AuditLogItem = ApiSchema<"AuditLogResponse">;

export type BusinessRequestType = BusinessRequest["request_type"];
export type BusinessRequestStatus = BusinessRequest["status"];
