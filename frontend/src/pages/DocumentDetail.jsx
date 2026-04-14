import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, RefreshCw, Trash2 } from 'lucide-react';
import api from '../api/client';
import StatusBadge from '../components/StatusBadge';
import toast from 'react-hot-toast';
import { useDocumentUpdates } from '../hooks/useDocumentUpdates';

export default function DocumentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [doc, setDoc] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchDoc = async () => {
    try {
      const { data } = await api.get(`/documents/${id}`);
      setDoc(data);
    } catch {
      toast.error('Document not found');
      navigate('/dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchDoc(); }, [id]);

  useDocumentUpdates((event) => {
    if (event.document_id === id) fetchDoc();
  });

  const reprocess = async () => {
    try {
      await api.post(`/documents/${id}/reprocess`);
      toast.success('Reprocessing started');
      fetchDoc();
    } catch {
      toast.error('Reprocess failed');
    }
  };

  const remove = async () => {
    if (!confirm('Delete this document?')) return;
    try {
      await api.delete(`/documents/${id}`);
      toast.success('Deleted');
      navigate('/dashboard');
    } catch {
      toast.error('Delete failed');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    );
  }

  if (!doc) return null;

  const Section = ({ title, children }) => (
    <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {title}
      </h3>
      {children}
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={() => navigate('/dashboard')}
          className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700"
        >
          <ArrowLeft size={20} />
        </button>
        <h1 className="text-xl font-bold text-slate-900 dark:text-white truncate">
          {doc.original_name}
        </h1>
        <StatusBadge status={doc.status} />
        <div className="ml-auto flex gap-2">
          {doc.status === 'failed' && (
            <button
              onClick={reprocess}
              className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              <RefreshCw size={14} /> Reprocess
            </button>
          )}
          <button
            onClick={remove}
            className="flex items-center gap-1.5 rounded-lg border border-red-200 px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-900/20"
          >
            <Trash2 size={14} /> Delete
          </button>
        </div>
      </div>

      {/* Info grid */}
      <div className="grid gap-4 md:grid-cols-2">
        <Section title="Overview">
          <dl className="space-y-2 text-sm">
            <Row label="Category" value={doc.category?.replace(/_/g, ' ') || '—'} />
            <Row label="Confidence" value={doc.confidence != null ? `${(doc.confidence * 100).toFixed(1)}%` : '—'} />
            <Row label="Pages" value={doc.page_count ?? '—'} />
            <Row label="File size" value={doc.file_size ? `${(doc.file_size / 1024).toFixed(0)} KB` : '—'} />
            <Row label="MIME type" value={doc.mime_type || '—'} />
            <Row label="Processing time" value={doc.processing_time_ms != null ? `${doc.processing_time_ms} ms` : '—'} />
            <Row label="Created" value={new Date(doc.created_at).toLocaleString()} />
            {doc.processed_at && <Row label="Processed" value={new Date(doc.processed_at).toLocaleString()} />}
          </dl>
        </Section>

        <Section title="Summary">
          <p className="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
            {doc.summary || 'No summary available.'}
          </p>
        </Section>

        {doc.error_message && (
          <Section title="Error">
            <p className="text-sm text-red-600 dark:text-red-400">{doc.error_message}</p>
          </Section>
        )}

        {doc.flags?.length > 0 && (
          <Section title="Flags">
            <div className="flex flex-wrap gap-2">
              {doc.flags.map((f, i) => (
                <span key={i} className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-700 dark:bg-amber-900/40 dark:text-amber-400">
                  {f}
                </span>
              ))}
            </div>
          </Section>
        )}
      </div>

      {/* Extracted data */}
      {doc.extracted_data && Object.keys(doc.extracted_data).length > 0 && (
        <Section title="Extracted Data">
          <pre className="max-h-80 overflow-auto rounded-lg bg-slate-50 p-4 text-xs text-slate-700 dark:bg-slate-900 dark:text-slate-300">
            {JSON.stringify(doc.extracted_data, null, 2)}
          </pre>
        </Section>
      )}

      {doc.key_entities && Object.keys(doc.key_entities).length > 0 && (
        <Section title="Key Entities">
          <pre className="max-h-80 overflow-auto rounded-lg bg-slate-50 p-4 text-xs text-slate-700 dark:bg-slate-900 dark:text-slate-300">
            {JSON.stringify(doc.key_entities, null, 2)}
          </pre>
        </Section>
      )}
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex justify-between">
      <dt className="text-slate-500 dark:text-slate-400">{label}</dt>
      <dd className="font-medium text-slate-900 dark:text-white capitalize">{value}</dd>
    </div>
  );
}
