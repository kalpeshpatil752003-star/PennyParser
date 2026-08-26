import { useState } from 'react';
import { UploadDocument } from '../components/UploadDocument';
import { DocumentList } from '../components/DocumentList';

export function DocumentsPage() {
  const [refreshKey, setRefreshKey] = useState(0);

  const handleUploadSuccess = () => {
    setRefreshKey((prev) => prev + 1);
  };

  return (
    <div className="max-w-4xl mx-auto p-12 h-full flex flex-col">
      {/* Page Header */}
      <div className="mb-12">
        <h1 className="text-3xl font-medium tracking-tight">Documents</h1>
      </div>

      {/* Upload Zone */}
      <UploadDocument onUploadSuccess={handleUploadSuccess} />

      {/* Document Library */}
      <DocumentList refreshKey={refreshKey} />
    </div>
  );
}