import { useEffect, useState } from 'react';
import { Webhook, Save, Trash2, Check } from 'lucide-react';
import api from '../api/client';
import toast from 'react-hot-toast';

export default function Settings() {
  const [url, setUrl] = useState('');
  const [current, setCurrent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get('/webhooks/');
        setCurrent(data);
        setUrl(data.url);
      } catch {
        // No webhook configured
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const { data } = await api.post('/webhooks/configure', { url });
      setCurrent(data);
      toast.success('Webhook saved');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!confirm('Remove webhook?')) return;
    try {
      await api.delete('/webhooks/');
      setCurrent(null);
      setUrl('');
      toast.success('Webhook removed');
    } catch {
      toast.error('Failed to remove');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Settings</h1>

      {/* Webhook Config */}
      <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
        <div className="flex items-center gap-3 border-b border-slate-200 px-6 py-4 dark:border-slate-700">
          <Webhook size={20} className="text-blue-600" />
          <h2 className="text-base font-semibold text-slate-900 dark:text-white">Webhook</h2>
          {current?.is_active && (
            <span className="ml-auto flex items-center gap-1 text-xs font-medium text-green-600">
              <Check size={14} /> Active
            </span>
          )}
        </div>

        <form onSubmit={save} className="p-6 space-y-4">
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Receive HTTP POST notifications when document processing completes or fails.
          </p>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Webhook URL
            </label>
            <input
              type="url"
              required
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com/webhook"
              className="w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
            />
          </div>

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
            >
              <Save size={14} />
              {saving ? 'Saving…' : 'Save'}
            </button>
            {current && (
              <button
                type="button"
                onClick={remove}
                className="flex items-center gap-2 rounded-lg border border-red-200 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-900/20"
              >
                <Trash2 size={14} />
                Remove
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
