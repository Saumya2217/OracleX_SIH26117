import React from "react";

interface PaginationProps {
  shown: number;
  hasMore: boolean;
  loading: boolean;
  onLoadMore: () => void;
}

export const Pagination: React.FC<PaginationProps> = ({ shown, hasMore, loading, onLoadMore }) => <div className="pagination-bar">
  <span aria-live="polite">{shown} {shown === 1 ? "record" : "records"} shown</span>
  {hasMore && <button type="button" className="btn-secondary" disabled={loading} onClick={onLoadMore}>{loading ? "Loading…" : "Load more"}</button>}
</div>;
