import { useState, useRef, useCallback } from 'react';
import { Upload, X, FileText } from 'lucide-react';
import api from '../api/client';
import toast from 'react-hot-toast';

const ALLOWED = ['pdf', 'docx', 'png', 'jpg', 'jpeg', 'tiff'];

export default function UploadModal({ onClose }) {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const inputRef = useRef(null);
  const dropRef = useRef(null);

  const validate = (fileList) => {
    const valid = [];
    for (const f of fileList) {
      const ext = f.name.split('.').pop()?.toLowerCase();
      if (ALLOWED.includes(ext)) {
        valid.push(f);
      } else {
        toast.error(`Unsupported: ${f.name}`);
      }
    }
    return valid;
  };

  const addFiles = (fileList) => {
    const valid = validate(Array.from(fileList));
    setFiles((prev) => [...prev, ...valid]);
  };

  const removeFile = (idx) => setFiles((prev) => prev.filter((_, i) => i !== idx));

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    dropRef.current?.classList.remove('border-blue-500', 'bg-blue-50', 'dark:bg-blue-900/20');
    addFiles(e.dataTransfer.files);
  }, []);

  const handleDragOver = (e) => {
    e.preventDefault();
    dropRef.current?.classList.add('border-blue-500', 'bg-blue-50', 'dark:bg-blue-900/20');
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    dropRef.current?.classList.remove('border-blue-500', 'bg-blue-50', 'dark:bg-blue-900/20');
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setProgress(0);

    try {
      if (files.length === 1) {
        const fd = new FormData();
        fd.append('file', files[0]);
        await api.post('/documents/upload', fd, {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (e) => setProgress(Math.round((e.loaded / (e.total || 1)) * 100)),
        });
      } else {
        const fd = new FormData();
        files.forEach((f) => fd.append('files', f));
        await api.post('/documents/upload/batch', fd, {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (e) => setProgress(Math.round((e.loaded / (e.total || 1)) * 100)),
        });
      }
      toast.success(`Uploaded ${files.length} file${files.length > 1 ? 's' : ''}`);
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-lg rounded-xl border border-slate-200 bg-white shadow-xl dark:border-slate-700 dark:bg-slate-800">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 dark:border-slate-700">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Upload Documents</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-white">
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          {/* Drop zone */}
          <div
            ref={dropRef}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => inputRef.current?.click()}
            className="flex cursor-pointer flex-col items-center gap-3 rounded-lg border-2 border-dashed border-slate-300 p-8 transition-colors hover:border-blue-500 dark:border-slate-600"
          >
            <Upload size={32} className="text-slate-400" />
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Drag & drop files or <span className="font-medium text-blue-600">browse</span>
            </p>
            <p className="text-xs text-slate-400">PDF, DOCX, PNG, JPG, TIFF</p>
            <input
              ref={inputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.png,.jpg,.jpeg,.tiff"
              className="hidden"
              onChange={(e) => addFiles(e.target.files)}
            />
          </div>

          {/* File list */}
          {files.length > 0 && (
            <div className="max-h-40 space-y-2 overflow-y-auto">
              {files.map((f, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-700/50"
                >
                  <div className="flex items-center gap-2 truncate">
                    <FileText size={16} className="shrink-0 text-slate-400" />
                    <span className="truncate text-sm text-slate-700 dark:text-slate-300">{f.name}</span>
                    <span className="text-xs text-slate-400">{(f.size / 1024).toFixed(0)} KB</span>
                  </div>
                  <button onClick={() => removeFile(i)} className="text-slate-400 hover:text-red-500">
                    <X size={16} />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Progress */}
          {uploading && (
            <div className="h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
              <div
                className="h-full rounded-full bg-blue-600 transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 border-t border-slate-200 px-6 py-4 dark:border-slate-700">
          <button
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700"
          >
            Cancel
          </button>
          <button
            onClick={handleUpload}
            disabled={files.length === 0 || uploading}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {uploading ? `Uploading ${progress}%` : `Upload ${files.length} file${files.length !== 1 ? 's' : ''}`}
          </button>
        </div>
      </div>
    </div>
  );
}
