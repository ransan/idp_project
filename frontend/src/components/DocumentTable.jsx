import { useNavigate } from 'react-router-dom';
import { RefreshCw, Trash2, ChevronLeft, ChevronRight } from 'lucide-react';
import StatusBadge from './StatusBadge';
import api from '../api/client';
import toast from 'react-hot-toast';

export default function DocumentTable({
  documents,
  total,
  page,
  size,
  onPageChange,
  onRefresh,
  filters,
  onFilterChange,
}) {
  const navigate = useNavigate();
  const totalPages = Math.max(1, Math.ceil(total / size));

  const reprocess = async (e, id) => {
    e.stopPropagation();
    try {
      await api.post(`/documents/${id}/reprocess`);
      toast.success('Reprocessing started');
      onRefresh();
    } catch {
      toast.error('Reprocess failed');
    }
  };

  const remove = async (e, id) => {
    e.stopPropagation();
    if (!confirm('Delete this document?')) return;
    try {
      await api.delete(`/documents/${id}`);
      toast.success('Deleted');
      onRefresh();
    } catch {
      toast.error('Delete failed');
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 border-b border-slate-200 px-5 py-3 dark:border-slate-700">
        <select
          value={filters.status || ''}
          onChange={(e) => onFilterChange({ ...filters, status: e.target.value || null })}
          className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-white"
        >
          <option value="">All Statuses</option>
          <option value="uploaded">Uploaded</option>
          <option value="parsing">Parsing</option>
          <option value="processing">Processing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
        <select
          value={filters.category || ''}
          onChange={(e) => onFilterChange({ ...filters, category: e.target.value || null })}
          className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-white"
        >
          <option value="">All Categories</option>
          <option value="invoice">Invoice</option>
          <option value="contract">Contract</option>
          <option value="report">Report</option>
          <option value="legal_brief">Legal Brief</option>
          <option value="financial_statement">Financial Statement</option>
          <option value="shipping_manifest">Shipping Manifest</option>
          <option value="unknown">Unknown</option>
        </select>
        <span className="ml-auto text-xs text-slate-500 dark:text-slate-400">
          {total} document{total !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-700">
              <th className="px-5 py-3 font-medium text-slate-500 dark:text-slate-400">Name</th>
              <th className="px-5 py-3 font-medium text-slate-500 dark:text-slate-400">Status</th>
              <th className="hidden px-5 py-3 font-medium text-slate-500 dark:text-slate-400 md:table-cell">Category</th>
              <th className="hidden px-5 py-3 font-medium text-slate-500 dark:text-slate-400 md:table-cell">Confidence</th>
              <th className="hidden px-5 py-3 font-medium text-slate-500 dark:text-slate-400 lg:table-cell">Date</th>
              <th className="px-5 py-3 font-medium text-slate-500 dark:text-slate-400">Actions</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => (
              <tr
                key={doc.id}
                onClick={() => navigate(`/documents/${doc.id}`)}
                className="cursor-pointer border-b border-slate-100 hover:bg-slate-50 dark:border-slate-700/50 dark:hover:bg-slate-700/30"
              >
                <td className="max-w-[200px] truncate px-5 py-3 font-medium text-slate-900 dark:text-white">
                  {doc.original_name}
                </td>
                <td className="px-5 py-3">
                  <StatusBadge status={doc.status} />
                </td>
                <td className="hidden px-5 py-3 capitalize text-slate-600 dark:text-slate-300 md:table-cell">
                  {doc.category?.replace(/_/g, ' ') || '—'}
                </td>
                <td className="hidden px-5 py-3 text-slate-600 dark:text-slate-300 md:table-cell">
                  {doc.confidence != null ? `${(doc.confidence * 100).toFixed(0)}%` : '—'}
                </td>
                <td className="hidden px-5 py-3 text-slate-500 dark:text-slate-400 lg:table-cell">
                  {new Date(doc.created_at).toLocaleDateString()}
                </td>
                <td className="px-5 py-3">
                  <div className="flex items-center gap-1">
                    {doc.status === 'failed' && (
                      <button
                        onClick={(e) => reprocess(e, doc.id)}
                        className="rounded p-1.5 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30"
                        title="Reprocess"
                      >
                        <RefreshCw size={15} />
                      </button>
                    )}
                    <button
                      onClick={(e) => remove(e, doc.id)}
                      className="rounded p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30"
                      title="Delete"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {documents.length === 0 && (
              <tr>
                <td colSpan={6} className="px-5 py-12 text-center text-slate-400">
                  No documents found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-slate-200 px-5 py-3 dark:border-slate-700">
          <span className="text-xs text-slate-500 dark:text-slate-400">
            Page {page} of {totalPages}
          </span>
          <div className="flex gap-1">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              className="rounded p-1.5 text-slate-500 hover:bg-slate-100 disabled:opacity-30 dark:text-slate-400 dark:hover:bg-slate-700"
            >
              <ChevronLeft size={16} />
            </button>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
              className="rounded p-1.5 text-slate-500 hover:bg-slate-100 disabled:opacity-30 dark:text-slate-400 dark:hover:bg-slate-700"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
