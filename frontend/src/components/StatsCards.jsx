import { FileText, CheckCircle, Clock, AlertTriangle } from 'lucide-react';

const iconMap = {
  total: { icon: FileText, color: 'bg-blue-100 text-blue-600 dark:bg-blue-900/40 dark:text-blue-400' },
  completed: { icon: CheckCircle, color: 'bg-green-100 text-green-600 dark:bg-green-900/40 dark:text-green-400' },
  processing: { icon: Clock, color: 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900/40 dark:text-yellow-400' },
  failed: { icon: AlertTriangle, color: 'bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-400' },
};

export default function StatsCards({ stats }) {
  if (!stats) return null;

  const statusMap = {};
  (stats.by_status || []).forEach((s) => {
    statusMap[s.status] = s.count;
  });

  const cards = [
    { key: 'total', label: 'Total Documents', value: stats.total_documents },
    { key: 'completed', label: 'Completed', value: statusMap.completed || 0 },
    { key: 'processing', label: 'Processing', value: (statusMap.parsing || 0) + (statusMap.processing || 0) },
    { key: 'failed', label: 'Failed', value: statusMap.failed || 0 },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((c) => {
        const { icon: Icon, color } = iconMap[c.key];
        return (
          <div
            key={c.key}
            className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500 dark:text-slate-400">{c.label}</p>
                <p className="mt-1 text-2xl font-bold text-slate-900 dark:text-white">
                  {c.value}
                </p>
              </div>
              <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${color}`}>
                <Icon size={20} />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
