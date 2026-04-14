import { useEffect, useState, useCallback } from 'react';
import api from '../api/client';
import StatsCards from '../components/StatsCards';
import DocumentTable from '../components/DocumentTable';
import { useDocumentUpdates } from '../hooks/useDocumentUpdates';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [docs, setDocs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ status: null, category: null });
  const size = 20;

  const fetchStats = useCallback(async () => {
    try {
      const { data } = await api.get('/stats');
      setStats(data);
    } catch { /* ignore */ }
  }, []);

  const fetchDocs = useCallback(async () => {
    try {
      const params = { page, size };
      if (filters.status) params.status = filters.status;
      if (filters.category) params.category = filters.category;
      const { data } = await api.get('/documents/', { params });
      setDocs(data.documents);
      setTotal(data.total);
    } catch { /* ignore */ }
  }, [page, filters, size]);

  const refresh = useCallback(() => {
    fetchStats();
    fetchDocs();
  }, [fetchStats, fetchDocs]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Real-time updates via WebSocket
  useDocumentUpdates(() => {
    refresh();
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Dashboard</h1>
      <StatsCards stats={stats} />
      <DocumentTable
        documents={docs}
        total={total}
        page={page}
        size={size}
        onPageChange={setPage}
        onRefresh={refresh}
        filters={filters}
        onFilterChange={(f) => { setFilters(f); setPage(1); }}
      />
    </div>
  );
}
