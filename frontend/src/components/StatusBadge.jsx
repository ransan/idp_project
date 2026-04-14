const colors = {
  uploaded: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300',
  parsing: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400',
  processing: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400',
  completed: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400',
  failed: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400',
};

export default function StatusBadge({ status }) {
  const cls = colors[status] || colors.uploaded;
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${cls}`}>
      {status}
    </span>
  );
}
