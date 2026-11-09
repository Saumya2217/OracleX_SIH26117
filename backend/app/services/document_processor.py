from pathlib import Path
from typing import List, Dict, Any, Tuple
import pymupdf  # fitz
import pandas as pd
from app.config import settings

class DocumentChunkData:
    def __init__(self, content: str, page_number: int = 1, metadata: Dict[str, Any] = None):
        self.content = content
        self.page_number = page_number
        self.metadata = metadata or {}

class DocumentProcessor:
    @staticmethod
    def process_file(file_path: str, file_type: str) -> Tuple[str, List[DocumentChunkData]]:
        """
        Parses document file and returns (summary, chunks).
        Supports PDF, Excel (.xlsx, .xls), CSV, and text/markdown files.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_type_lower = file_type.lower().strip(".")
        if file_type_lower in ["pdf"]:
            return DocumentProcessor._process_pdf(path)
        elif file_type_lower in ["xlsx", "xls"]:
            return DocumentProcessor._process_excel(path)
        elif file_type_lower in ["csv"]:
            return DocumentProcessor._process_csv(path)
        elif file_type_lower in ["txt", "md"]:
            return DocumentProcessor._process_text(path)
        raise ValueError(f"Unsupported parser type: {file_type_lower}")

    @staticmethod
    def _process_pdf(path: Path) -> Tuple[str, List[DocumentChunkData]]:
        doc = pymupdf.open(str(path))
        if doc.needs_pass:
            doc.close()
            raise ValueError("Encrypted PDF files are not supported.")
        if len(doc) > settings.MAX_DOCUMENT_PAGES:
            page_count = len(doc)
            doc.close()
            raise ValueError(
                f"PDF contains {page_count} pages; the configured limit is {settings.MAX_DOCUMENT_PAGES}."
            )
        chunks: List[DocumentChunkData] = []
        full_text_list = []

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_text = page.get_text("text").strip()
            if not page_text:
                continue

            full_text_list.append(page_text)
            
            # Chunk by double newlines or sensible lengths (~500 words)
            paragraphs = [p.strip() for p in page_text.split("\n\n") if len(p.strip()) > 30]
            if not paragraphs:
                paragraphs = [page_text]

            current_chunk = ""
            for p in paragraphs:
                if len(current_chunk) + len(p) < 1500:
                    current_chunk += ("\n\n" + p if current_chunk else p)
                else:
                    chunks.append(DocumentChunkData(
                        content=current_chunk,
                        page_number=page_idx + 1,
                        metadata={"page": page_idx + 1, "filename": path.name}
                    ))
                    current_chunk = p
            if current_chunk:
                chunks.append(DocumentChunkData(
                    content=current_chunk,
                    page_number=page_idx + 1,
                    metadata={"page": page_idx + 1, "filename": path.name}
                ))

        doc.close()
        summary = (full_text_list[0][:400] + "...") if full_text_list else "Empty PDF document"
        return summary, chunks

    @staticmethod
    def _process_excel(path: Path) -> Tuple[str, List[DocumentChunkData]]:
        chunks: List[DocumentChunkData] = []
        excel_file = pd.ExcelFile(str(path))
        sheet_summaries = []

        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            if df.empty:
                continue
            
            # Extract header and statistics
            columns = list(df.columns)
            row_count = len(df)
            if row_count > settings.MAX_TABULAR_ROWS:
                raise ValueError(
                    f"Sheet '{sheet_name}' contains {row_count} rows; the configured limit is "
                    f"{settings.MAX_TABULAR_ROWS}."
                )
            sheet_info = f"Sheet '{sheet_name}': {row_count} rows, Columns: {', '.join(str(c) for c in columns)}"
            sheet_summaries.append(sheet_info)

            # Summarize stats for numeric columns
            numeric_desc = ""
            try:
                desc = df.describe().to_string()
                numeric_desc = f"\nStatistical Summary:\n{desc}\n"
            except Exception:
                pass

            # Chunk the table rows in batches of 10 rows
            for i in range(0, row_count, 10):
                batch = df.iloc[i:i+10]
                batch_text = f"Dataset: {path.name} | Sheet: {sheet_name} | Rows {i+1} to {min(i+10, row_count)}:\n"
                batch_text += batch.to_markdown(index=False)
                if i == 0 and numeric_desc:
                    batch_text += "\n" + numeric_desc

                chunks.append(DocumentChunkData(
                    content=batch_text,
                    page_number=1,
                    metadata={"sheet": sheet_name, "rows": f"{i+1}-{min(i+10, row_count)}", "filename": path.name}
                ))

        summary = f"Excel workbook containing sheets: {', '.join(sheet_summaries)}"
        return summary, chunks

    @staticmethod
    def _process_csv(path: Path) -> Tuple[str, List[DocumentChunkData]]:
        df = pd.read_csv(str(path))
        chunks: List[DocumentChunkData] = []
        columns = list(df.columns)
        row_count = len(df)
        if row_count > settings.MAX_TABULAR_ROWS:
            raise ValueError(
                f"CSV contains {row_count} rows; the configured limit is {settings.MAX_TABULAR_ROWS}."
            )
        summary = f"CSV dataset {path.name} with {row_count} records and columns: {', '.join(str(c) for c in columns)}"

        for i in range(0, row_count, 15):
            batch = df.iloc[i:i+15]
            batch_text = f"CSV: {path.name} | Records {i+1} to {min(i+15, row_count)} of {row_count}:\n"
            batch_text += batch.to_markdown(index=False)
            chunks.append(DocumentChunkData(
                content=batch_text,
                page_number=1,
                metadata={"rows": f"{i+1}-{min(i+15, row_count)}", "filename": path.name}
            ))

        return summary, chunks

    @staticmethod
    def _process_text(path: Path) -> Tuple[str, List[DocumentChunkData]]:
        with open(str(path), "r", encoding="utf-8", errors="strict") as f:
            text = f.read()
        
        chunks = []
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        current = ""
        for p in paragraphs:
            if len(current) + len(p) < 1200:
                current += ("\n\n" + p if current else p)
            else:
                chunks.append(DocumentChunkData(content=current, metadata={"filename": path.name}))
                current = p
        if current:
            chunks.append(DocumentChunkData(content=current, metadata={"filename": path.name}))

        summary = text[:300] + "..." if len(text) > 300 else text
        return summary, chunks
