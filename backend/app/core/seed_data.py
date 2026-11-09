import os
import hashlib
from pathlib import Path
from sqlalchemy.orm import Session
from app.config import settings
from app.models.company import Company, Department, Role, User
from app.models.knowledge import Document, DocumentChunk, DocumentVersion, IngestionJob, OutboxEvent, utcnow
from app.models.workflow import Workflow, Task, ApprovalRequest
from app.models.adaptation import AdaptationProposal
from app.models.audit import AuditLog
from app.models.assistant import AgentRunCitation, AgentRun, ConversationMessage, Conversation
from app.models.request import InternalNotification, BusinessRequestEvent, BusinessRequestVersion, BusinessRequest
from app.core.security import hash_password
from app.core.permissions import DEFAULT_ROLE_PERMISSIONS, ClearanceLevel, PermissionScope
from app.services.vector_store import vector_store_service
from app.services.document_processor import DocumentProcessor

def seed_database(db: Session, force_reseed: bool = False) -> Company:
    """
    Seeds rich, realistic enterprise structure for OracleX:
    Company: NovaWorks Enterprise Solutions
    Departments: Executive Board, Operations, Creative & Product, Finance & Strategy
    Team Members: Soumya Jain, Ashutosh Tandel, Hetvi Devalekar, Arya Khetalpa, Jignasa Loke, Krish Nisar
    """
    existing_company = db.query(Company).first()
    if existing_company:
        if not force_reseed and "NovaWorks" in existing_company.name:
            return existing_company
        # If force_reseed or older seed exists (e.g. Apex Precision), clean up and reseed
        db.query(AuditLog).delete()
        db.query(AgentRunCitation).delete()
        db.query(AgentRun).delete()
        db.query(ConversationMessage).delete()
        db.query(Conversation).delete()
        db.query(InternalNotification).delete()
        db.query(BusinessRequestEvent).delete()
        db.query(BusinessRequestVersion).delete()
        db.query(BusinessRequest).delete()
        db.query(ApprovalRequest).delete()
        db.query(Task).delete()
        db.query(Workflow).delete()
        db.query(AdaptationProposal).delete()
        db.query(OutboxEvent).delete()
        db.query(IngestionJob).delete()
        db.query(DocumentChunk).delete()
        db.query(DocumentVersion).delete()
        db.query(Document).delete()
        db.query(User).delete()
        db.query(Role).delete()
        db.query(Department).delete()
        db.query(Company).delete()
        db.commit()

        try:
            vector_store_service.client.delete_collection("oraclex_company_knowledge")
            vector_store_service.collection = vector_store_service.client.get_or_create_collection(
                name="oraclex_company_knowledge",
                embedding_function=vector_store_service.embedding_fn
            )
        except Exception:
            pass


    # 1. Create Company: NovaWorks Enterprise Solutions
    company = Company(
        name="NovaWorks Enterprise Solutions",
        industry="Enterprise Operations & Digital Solutions",
        description="Collaborative enterprise operations, product design, and strategic business intelligence workspace.",
        mission_statement="Delivering sovereign, secure, and intelligent workplace operations across creative, operational, and financial teams.",
        compliance_standards=["ISO 9001:2015", "SOC 2 Type II", "GDPR Enterprise Privacy", "Internal Governance Framework"],
        settings={"timezone": "UTC", "clearance_mode": "STRICT_FOUR_TIER", "default_model": "llama3.2"}
    )
    db.add(company)
    db.commit()
    db.refresh(company)

    # 2. Departments
    dept_exec = Department(
        company_id=company.id,
        name="Executive Board & Leadership",
        code="EXEC",
        description="Strategic governance, organization-wide policy, capital allocation, and executive oversight."
    )
    dept_ops = Department(
        company_id=company.id,
        name="Operations & Logistics",
        code="OPS",
        description="Client fulfillment, workflow automation, operational quality, and logistics coordination."
    )
    dept_creat = Department(
        company_id=company.id,
        name="Creative & Product Design",
        code="CREAT",
        description="Product strategy, UX/UI architecture, creative design systems, and digital assets."
    )
    dept_fin = Department(
        company_id=company.id,
        name="Finance & Strategic Planning",
        code="FIN",
        description="Budgeting, financial forecasting, audit compliance, and investor relations."
    )

    depts = [dept_exec, dept_ops, dept_creat, dept_fin]
    db.add_all(depts)
    db.commit()
    for d in depts:
        db.refresh(d)

    # 3. Roles
    role_admin = Role(
        company_id=company.id,
        name="Director & Executive Administrator",
        code="ADMIN",
        description="Full enterprise administration, organization governance, and Level 4 Restricted clearance.",
        permissions=DEFAULT_ROLE_PERMISSIONS["ADMIN"],
        clearance_level=ClearanceLevel.RESTRICTED
    )
    role_manager = Role(
        company_id=company.id,
        name="Department Manager & Lead",
        code="MANAGER",
        description="Department leadership, task delegation, team workflow supervision, and Level 3 Confidential clearance.",
        permissions=DEFAULT_ROLE_PERMISSIONS["MANAGER"],
        clearance_level=ClearanceLevel.CONFIDENTIAL
    )
    role_specialist = Role(
        company_id=company.id,
        name="Senior Specialist",
        code="TECHNICIAN",
        description="Core contributor executing specialized projects, workflows, and Level 2 Internal clearance.",
        permissions=DEFAULT_ROLE_PERMISSIONS["TECHNICIAN"],
        clearance_level=ClearanceLevel.INTERNAL
    )
    role_employee = Role(
        company_id=company.id,
        name="Team Associate",
        code="EMPLOYEE",
        description="Standard team associate adhering to standard organizational procedures and project tasks.",
        permissions=DEFAULT_ROLE_PERMISSIONS["EMPLOYEE"],
        clearance_level=ClearanceLevel.PUBLIC
    )

    roles = [role_admin, role_manager, role_specialist, role_employee]
    db.add_all(roles)
    db.commit()
    for r in roles:
        db.refresh(r)

    # 4. Users (The 6 Real Team Members - ordinary DB records)
    # User 1: Saumy Jain (Admin / Operations Director, Level 4)
    saumy = User(
        company_id=company.id,
        department_id=dept_ops.id,
        role_id=role_admin.id,
        email="saumy@novaworks.com",
        full_name="Saumy Jain",
        job_title="Operations Director & Executive Admin",
        employee_code="NW-001",
        hashed_password=hash_password("password123"),
        clearance_level=ClearanceLevel.RESTRICTED,
        is_admin=True
    )
    db.add(saumy)
    db.commit()
    db.refresh(saumy)

    # User 2: Ashutosh Tandel (Manager / Creative & Product Lead, Level 3)
    ashutosh = User(
        company_id=company.id,
        department_id=dept_creat.id,
        role_id=role_manager.id,
        reports_to_id=saumy.id,
        email="ashutosh@novaworks.com",
        full_name="Ashutosh Tandel",
        job_title="Creative & Product Lead",
        employee_code="NW-002",
        hashed_password=hash_password("password123"),
        clearance_level=ClearanceLevel.CONFIDENTIAL,
        is_admin=False
    )

    # User 3: Hetvi Devlekar (Manager / Finance & Strategy Lead, Level 3)
    hetvi = User(
        company_id=company.id,
        department_id=dept_fin.id,
        role_id=role_manager.id,
        reports_to_id=saumy.id,
        email="hetvi@novaworks.com",
        full_name="Hetvi Devlekar",
        job_title="Finance & Operations Lead",
        employee_code="NW-003",
        hashed_password=hash_password("password123"),
        clearance_level=ClearanceLevel.CONFIDENTIAL,
        is_admin=False
    )
    db.add_all([ashutosh, hetvi])
    db.commit()
    db.refresh(ashutosh)
    db.refresh(hetvi)

    # User 4: Arya Khetalpar (Employee / Creative Specialist, Level 2)
    arya = User(
        company_id=company.id,
        department_id=dept_creat.id,
        role_id=role_specialist.id,
        reports_to_id=ashutosh.id,
        email="arya@novaworks.com",
        full_name="Arya Khetalpar",
        job_title="Creative Specialist",
        employee_code="NW-004",
        hashed_password=hash_password("password123"),
        clearance_level=ClearanceLevel.INTERNAL,
        is_admin=False
    )

    # User 5: Jidnyasa Loke (Employee / Operations Associate, Level 2)
    jidnyasa = User(
        company_id=company.id,
        department_id=dept_ops.id,
        role_id=role_specialist.id,
        reports_to_id=saumy.id,
        email="jidnyasa@novaworks.com",
        full_name="Jidnyasa Loke",
        job_title="Operations Associate",
        employee_code="NW-005",
        hashed_password=hash_password("password123"),
        clearance_level=ClearanceLevel.INTERNAL,
        is_admin=False
    )

    # User 6: Krish Jain (Employee / Junior Associate, Level 1)
    krish = User(
        company_id=company.id,
        department_id=dept_fin.id,
        role_id=role_employee.id,
        reports_to_id=hetvi.id,
        email="krish@novaworks.com",
        full_name="Krish Jain",
        job_title="Junior Financial Associate",
        employee_code="NW-006",
        hashed_password=hash_password("password123"),
        clearance_level=ClearanceLevel.PUBLIC,
        is_admin=False
    )
    db.add_all([arya, jidnyasa, krish])
    db.commit()
    db.refresh(arya)
    db.refresh(jidnyasa)
    db.refresh(krish)

    # 5. Documents & Knowledge Base
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Document 1: Company Handbook & Leave Policy (PUBLIC - Level 1)
    doc1_content = """NOVAWORKS ENTERPRISE SOLUTIONS - OFFICIAL EMPLOYEE HANDBOOK
DOCUMENT REF: NW-HR-001 | REVISION: 2026.1 | CLASSIFICATION: PUBLIC (LEVEL 1)
TITLE: Company Handbook, Working Guidelines & Comprehensive Leave Policy

1. PURPOSE & ORGANIZATIONAL ETHOS
NovaWorks provides a collaborative, transparent, and sovereign workspace. This handbook outlines everyday standards, working hours, benefits, and conduct expectations for all team members across all departments.

2. WORKING HOURS & HYBRID COLLABORATION
• Standard Office Hours: 9:00 AM to 6:00 PM (Monday through Friday).
• Core Collaboration Hours: 10:00 AM to 4:00 PM. Team members should be reachable for cross-department standups and syncs.
• Remote Flexibility: Up to 2 remote working days per week with manager coordination.

3. ANNUAL LEAVE & TIME-OFF ENTITLEMENTS
• Annual Vacation Leave: 20 paid vacation days per calendar year, accrued monthly.
• Sick & Medical Leave: 10 days fully paid per year. No medical certificate required for absences under 2 consecutive days.
• Parental & Personal Emergency Leave: Standard 12 weeks paid parental leave for primary caregivers; 5 personal emergency days.
• Leave Request Procedure: Submit via the internal portal at least 3 business days prior to scheduled time off.

4. CODE OF CONDUCT & DATA SOVEREIGNTY
• All corporate communications, designs, and financial documents must remain within sovereign company infrastructure.
• External AI tools, public LLMs, and unauthorized cloud sync services are strictly prohibited for internal assets."""
    
    doc1_path = upload_dir / "Company_Handbook_and_Leave_Policy.txt"
    with open(doc1_path, "w", encoding="utf-8") as f:
        f.write(doc1_content)

    doc1 = Document(
        company_id=company.id,
        department_id=dept_ops.id,
        uploaded_by_id=saumy.id,
        title="Company Handbook & Leave Policy (HR-001)",
        filename="Company_Handbook_and_Leave_Policy.txt",
        file_type="txt",
        file_path=str(doc1_path),
        file_size=len(doc1_content),
        clearance_level=ClearanceLevel.PUBLIC,
        is_company_wide=True,
        tags=["HR", "Handbook", "LeavePolicy", "Public", "Guidelines"],
        summary="Official NovaWorks handbook outlining standard 9 AM-6 PM hours, 20 annual leave days, sick leave, and code of conduct.",
        chunk_count=1,
        status="INDEXED"
    )
    db.add(doc1)
    db.commit()
    db.refresh(doc1)

    # Document 2: Product Launch Roadmap Q4 (INTERNAL - Level 2)
    doc2_content = """NOVAWORKS ENTERPRISE SOLUTIONS - CREATIVE & PRODUCT SPECIFICATION
DOCUMENT REF: PRD-Q4-2026 | REVISION: 1.4 | CLASSIFICATION: INTERNAL (LEVEL 2)
TITLE: Q4 Product Launch Roadmap, UI Architecture & Design System Deliverables

1. PRODUCT OVERVIEW
NovaWorks Product Studio is driving the Q4 platform release with revamped client workspaces, unified design tokens, and sovereign AI workflow automation.

2. MILESTONE SCHEDULE & SPRINT TARGETS
• Sprint 21 (Weeks 1-2): Completion of Design System v2.4 (dark obsidian theme, typography tokens, unified iconography).
• Sprint 22 (Weeks 3-4): Client Onboarding Flow Refactor, reducing setup friction by 40%.
• Sprint 23 (Weeks 5-6): Beta release of Team Activity Analytics and cross-department project boards.
• Launch Target: November 15, 2026 for general enterprise availability.

3. ROLES & ACCOUNTABILITY
• Creative Lead (Ashutosh Tandel): Overall product experience, aesthetic governance, and executive sign-off.
• Creative Specialist (Arya Khetalpa): Component library development, responsive layout QA, and marketing collateral."""

    doc2_path = upload_dir / "Product_Launch_Roadmap_Q4.txt"
    with open(doc2_path, "w", encoding="utf-8") as f:
        f.write(doc2_content)

    doc2 = Document(
        company_id=company.id,
        department_id=dept_creat.id,
        uploaded_by_id=ashutosh.id,
        title="Product Launch Roadmap (Q4 2026)",
        filename="Product_Launch_Roadmap_Q4.txt",
        file_type="txt",
        file_path=str(doc2_path),
        file_size=len(doc2_content),
        clearance_level=ClearanceLevel.INTERNAL,
        is_company_wide=False,
        tags=["Product", "Roadmap", "Creative", "Q4", "Milestones"],
        summary="Product design roadmap detailing Sprint 21-23 release schedules, Design System v2.4, and November 15 release target.",
        chunk_count=1,
        status="INDEXED"
    )
    db.add(doc2)
    db.commit()
    db.refresh(doc2)

    # Document 3: Client Operations Standard Procedure (INTERNAL - Level 2)
    doc3_content = """NOVAWORKS ENTERPRISE SOLUTIONS - OPERATIONS STANDARD OPERATING PROCEDURE
DOCUMENT REF: SOP-OPS-202 | REVISION: 3.1 | CLASSIFICATION: INTERNAL (LEVEL 2)
TITLE: Client Operations Fulfillment & Service Level Agreement (SLA) Protocol

1. SCOPE & FULFILLMENT MATRIX
This SOP governs client onboarding, ticket escalation, and operational quality control managed by the Operations team.

2. SERVICE LEVEL AGREEMENT (SLA) TARGETS
• Critical Incidents (Sev-1): Initial response within 15 minutes; containment within 2 hours.
• Standard Requests (Sev-2): Initial response within 2 hours; resolution within 24 hours.
• General Inquiries (Sev-3): Initial response within 1 business day.
• Platform Uptime Guarantee: 99.9% monthly availability for all client workspaces.

3. ESCALATION & APPROVAL PATHWAYS
• First Responder: Operations Associate (Jignasa Loke).
• Escalation Point: Operations Director (Soumya Jain) for Sev-1 incidents or contract SLA waivers.
• Weekly review: Every Monday at 10:00 AM to analyze ticket resolution trends and operational bottlenecks."""

    doc3_path = upload_dir / "Client_Operations_Standard_Procedure.txt"
    with open(doc3_path, "w", encoding="utf-8") as f:
        f.write(doc3_content)

    doc3 = Document(
        company_id=company.id,
        department_id=dept_ops.id,
        uploaded_by_id=saumy.id,
        title="Client Operations Standard Procedure (SOP-OPS-202)",
        filename="Client_Operations_Standard_Procedure.txt",
        file_type="txt",
        file_path=str(doc3_path),
        file_size=len(doc3_content),
        clearance_level=ClearanceLevel.INTERNAL,
        is_company_wide=False,
        tags=["Operations", "SOP", "SLA", "ClientServices", "Fulfillment"],
        summary="Operations standard operating procedure defining Sev-1 to Sev-3 SLAs, 99.9% uptime, and escalation matrix.",
        chunk_count=1,
        status="INDEXED"
    )
    db.add(doc3)
    db.commit()
    db.refresh(doc3)

    # Document 4: Confidential Strategic Budget 2026 (CONFIDENTIAL - Level 3)
    doc4_content = """NOVAWORKS ENTERPRISE SOLUTIONS - FINANCE & STRATEGY COMMITTEE
DOCUMENT REF: FIN-CONFIDENTIAL-2026 | CLASSIFICATION: CONFIDENTIAL (LEVEL 3)
TITLE: Annual Operating Budget Allocation & Strategic Expenditure Plan

CONFIDENTIALITY NOTICE:
Contains proprietary financial projections and department expenditure quotas. Restricted to Level 3 and Level 4 personnel.

1. ANNUAL OPERATING BUDGET OVERVIEW ($1,450,000 TOTAL)
• Creative & Product Engineering: $420,000 (UI/UX research, tooling, software licenses).
• Operations & Client Delivery: $480,000 (infrastructure, logistics, vendor support).
• Finance & Strategic Planning: $320,000 (audits, legal compliance, financial advisory).
• Executive Reserve & Contingency Fund: $230,000 (retained for rapid strategic opportunities).

2. EXPENDITURE POLICIES & APPROVAL THRESHOLDS
• Expenditures under $2,500: Department Manager approval required (Ashutosh / Hetvi).
• Expenditures exceeding $10,000: Formal dual sign-off from Finance Lead and Operations Director (Soumya Jain)."""

    doc4_path = upload_dir / "Confidential_Strategic_Budget_2026.txt"
    with open(doc4_path, "w", encoding="utf-8") as f:
        f.write(doc4_content)

    doc4 = Document(
        company_id=company.id,
        department_id=dept_fin.id,
        uploaded_by_id=hetvi.id,
        title="Confidential Strategic Budget 2026 (FIN-CONFIDENTIAL)",
        filename="Confidential_Strategic_Budget_2026.txt",
        file_type="txt",
        file_path=str(doc4_path),
        file_size=len(doc4_content),
        clearance_level=ClearanceLevel.CONFIDENTIAL,
        is_company_wide=False,
        tags=["Finance", "Budget", "Confidential", "Strategy", "Allocations"],
        summary="Confidential 2026 operating budget allocations totaling $1,450,000 and expenditure approval thresholds.",
        chunk_count=1,
        status="INDEXED"
    )
    db.add(doc4)
    db.commit()
    db.refresh(doc4)

    # Document 5: Executive Board Expansion Plan (RESTRICTED - Level 4)
    doc5_content = """NOVAWORKS ENTERPRISE SOLUTIONS - EXECUTIVE BOARD CONFIDENTIAL
DOCUMENT REF: EXEC-CONFIDENTIAL-RESTRICTED | LEVEL 4 RESTRICTED
TITLE: Strategic Corporate Expansion, Executive Compensation & M&A Governance

RESTRICTED ACCESS WARNING:
Access is strictly restricted to Level 4 clearance. Any unauthorized query triggers security audit alarms.

1. EXECUTIVE COMPENSATION & INCENTIVE POOL
• The annual executive compensation bonus pool is capped at $280,000, tied to enterprise ARR milestones and zero compliance violations.
• Board meeting minutes and voting resolutions are archived under encrypted corporate charter EXEC-2026-B.

2. STRATEGIC EXPANSION & ACQUISITIONS (M&A)
• Evaluation of Project Horizon: Potential acquisition of automated workflow design studio for $1.8M.
• Sovereign Infrastructure: Full migration to on-premise hardware cluster in Q1 2027 to eliminate cloud dependency."""

    doc5_path = upload_dir / "Executive_Board_Expansion_Plan.txt"
    with open(doc5_path, "w", encoding="utf-8") as f:
        f.write(doc5_content)

    doc5 = Document(
        company_id=company.id,
        department_id=dept_exec.id,
        uploaded_by_id=saumy.id,
        title="Executive Board Expansion & Compensation Plan (RESTRICTED)",
        filename="Executive_Board_Expansion_Plan.txt",
        file_type="txt",
        file_path=str(doc5_path),
        file_size=len(doc5_content),
        clearance_level=ClearanceLevel.RESTRICTED,
        is_company_wide=False,
        tags=["Executive", "Restricted", "Compensation", "Expansion", "BoardMinutes"],
        summary="Level 4 Restricted executive compensation, board minutes, and strategic corporate acquisition plans.",
        chunk_count=1,
        status="INDEXED"
    )
    db.add(doc5)
    db.commit()
    db.refresh(doc5)

    # Document 6: Backward Compatibility Document for Technical Tolerances (Level 2)
    doc6_content = """NOVAWORKS HARDWARE SPECIFICATIONS - ENGINEERING STANDARD
DOCUMENT REF: SOP-ENG-042 | REVISION: 4.2 | CLASSIFICATION: INTERNAL (LEVEL 2)
TITLE: High-Precision Component Tolerances & Quality Specifications

1. TECHNICAL TOLERANCE SPECIFICATIONS
• Standard precision engineering tolerance: ±0.005 mm nominal limit.
• Quality yield threshold: 98.4% target conformance.
• Any variance exceeding ±0.007 mm mandates immediate station hold and engineering review."""

    doc6_path = upload_dir / "SOP-ENG-042_Precision_Tolerances.txt"
    with open(doc6_path, "w", encoding="utf-8") as f:
        f.write(doc6_content)

    doc6 = Document(
        company_id=company.id,
        department_id=dept_ops.id,
        uploaded_by_id=saumy.id,
        title="SOP-ENG-042: High-Precision Component Tolerances",
        filename="SOP-ENG-042_Precision_Tolerances.txt",
        file_type="txt",
        file_path=str(doc6_path),
        file_size=len(doc6_content),
        clearance_level=ClearanceLevel.INTERNAL,
        is_company_wide=True,
        tags=["SOP", "Engineering", "Tolerances", "Quality"],
        summary="Technical component tolerance specifications (±0.005 mm) and quality inspection metrics.",
        chunk_count=1,
        status="INDEXED"
    )
    db.add(doc6)
    db.commit()
    db.refresh(doc6)

    # Create immutable version records and index the active version.
    try:
        for doc_obj, fpath in [(doc1, doc1_path), (doc2, doc2_path), (doc3, doc3_path), (doc4, doc4_path), (doc5, doc5_path), (doc6, doc6_path)]:
            s, chs = DocumentProcessor.process_file(str(fpath), "txt")
            digest = hashlib.sha256(Path(fpath).read_bytes()).hexdigest()
            version = DocumentVersion(
                document_id=doc_obj.id,
                created_by_id=doc_obj.uploaded_by_id,
                version_number=1,
                original_filename=doc_obj.filename,
                media_type="text/plain",
                file_size=doc_obj.file_size,
                content_sha256=digest,
                storage_key=str(fpath),
                parser_version="seed-v2",
                embedding_model=vector_store_service.EMBEDDING_MODEL,
                embedding_dimensions=vector_store_service.EMBEDDING_DIMENSIONS,
                status="READY",
                summary=s,
                chunk_count=len(chs),
                extraction_metadata={"format": "txt", "complete": True, "chunk_count": len(chs)},
                ready_at=utcnow(),
            )
            db.add(version)
            db.flush()
            for index, chunk in enumerate(chs):
                db.add(DocumentChunk(
                    document_id=doc_obj.id,
                    version_id=version.id,
                    chunk_index=index,
                    content=chunk.content,
                    page_number=chunk.page_number,
                    metadata_json=dict(chunk.metadata),
                    vector_id=f"{version.id}_chunk_{index}",
                ))
            doc_obj.current_version_id = version.id
            doc_obj.version_count = 1
            doc_obj.content_sha256 = digest
            doc_obj.summary = s
            doc_obj.chunk_count = len(chs)
            vector_store_service.index_chunks(
                document_id=doc_obj.id,
                company_id=company.id,
                clearance_level=doc_obj.clearance_level,
                department_id=doc_obj.department_id,
                is_company_wide=doc_obj.is_company_wide,
                chunks=chs,
                doc_title=doc_obj.title,
                version_id=version.id,
            )
        db.commit()
    except Exception as e:
        print(f"[Seed] Note: ChromaDB indexing warning: {e}")

    # 6. Workflows
    wf1 = Workflow(
        company_id=company.id,
        department_id=dept_ops.id,
        title="Client SLA & Service Incident Escalation",
        code="WF-OPS-01",
        description="Structured review pathway when client operational metrics deviate from agreed SLA thresholds.",
        category="OPERATIONS",
        steps=[
            {"step": 1, "name": "Incident Logging & Initial Triage", "role": "EMPLOYEE"},
            {"step": 2, "name": "Technical & Operational Impact Review", "role": "SPECIALIST"},
            {"step": 3, "name": "Corrective Action Plan Approval", "role": "MANAGER"},
            {"step": 4, "name": "Executive Notification & Closure", "role": "ADMIN"}
        ],
        requires_approval=True,
        approval_role_code="MANAGER",
        status="ACTIVE"
    )
    wf2 = Workflow(
        company_id=company.id,
        department_id=dept_fin.id,
        title="Department Budget Reallocation Request",
        code="WF-FIN-02",
        description="Formal approval procedure for transferring allocated funds between operational accounts.",
        category="FINANCE",
        steps=[
            {"step": 1, "name": "Variance Identification & Justification", "role": "EMPLOYEE"},
            {"step": 2, "name": "Financial Ledger Audit", "role": "MANAGER"},
            {"step": 3, "name": "Executive Board Authorization", "role": "ADMIN"}
        ],
        requires_approval=True,
        approval_role_code="ADMIN",
        status="ACTIVE"
    )
    db.add_all([wf1, wf2])
    db.commit()

    # 7. Operational Tasks
    task1 = Task(
        company_id=company.id,
        department_id=dept_creat.id,
        assigned_to_id=arya.id,
        created_by_id=ashutosh.id,
        title="Finalize Q4 Dark Obsidian Design System Tokens",
        description="Export standardized color variables, typography scales, and button states for the client workspace revamp.",
        project_name="Platform UI Modernization",
        status="IN_PROGRESS",
        priority="HIGH"
    )
    task2 = Task(
        company_id=company.id,
        department_id=dept_ops.id,
        assigned_to_id=jidnyasa.id,
        created_by_id=saumy.id,
        title="Conduct Monthly Client SLA Compliance Audit",
        description="Audit resolution tickets across all tier-1 enterprise accounts and verify 99.9% uptime compliance.",
        project_name="Service Operations 2026",
        status="TODO",
        priority="HIGH"
    )
    task3 = Task(
        company_id=company.id,
        department_id=dept_fin.id,
        assigned_to_id=krish.id,
        created_by_id=hetvi.id,
        title="Compile Q3 Budget Variance & Spend Summary",
        description="Consolidate departmental software tool subscriptions and flag any variances exceeding 5%.",
        project_name="Fiscal Year Audits",
        status="IN_PROGRESS",
        priority="MEDIUM"
    )
    task4 = Task(
        company_id=company.id,
        department_id=dept_ops.id,
        assigned_to_id=saumy.id,
        created_by_id=saumy.id,
        title="Review Enterprise Data Sovereignty & ISO Audit Readiness",
        description="Validate that all document embeddings and audit logs remain strictly within local on-premise storage.",
        project_name="Governance & Compliance",
        status="COMPLETED",
        priority="HIGH"
    )
    db.add_all([task1, task2, task3, task4])
    db.commit()

    # 8. Adaptation Proposals
    prop1 = AdaptationProposal(
        company_id=company.id,
        title="Automated Client Onboarding Checklist Triggers",
        category="WORKFLOW_OPTIMIZATION",
        description="AI detected recurring 48-hour delays during manual client onboarding verification in Operations.",
        detected_pattern="Telemetry indicates team members wait on average 2.3 days for initial credential verification.",
        proposed_adaptation="Trigger automated workspace provisioning upon signed contract upload, reducing setup time by 75%.",
        projected_benefit="Saves approximately 6 operational hours per client onboarding while ensuring 100% audit logging.",
        confidence_score=94,
        status="PROPOSED"
    )
    prop2 = AdaptationProposal(
        company_id=company.id,
        title="Design Asset Review Fast-Track for Minor Revisions",
        category="BOTTLENECK",
        description="Minor UI icon and typography token updates experience average hold time of 36 hours awaiting Lead sign-off.",
        detected_pattern="95% of routine token modifications are approved without changes during final review.",
        proposed_adaptation="Empower Creative Specialists to merge low-risk design tokens automatically with post-merge notification to Lead.",
        projected_benefit="Reduces design system sprint bottleneck from 36 hours to under 30 minutes.",
        confidence_score=89,
        status="PROPOSED"
    )
    db.add_all([prop1, prop2])
    db.commit()

    return company
