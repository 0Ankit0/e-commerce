'use client';

import { DocumentList, DocumentUpload } from '@/components/documents';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { FileText, Upload } from 'lucide-react';

export default function DocumentsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
        <p className="text-gray-500">Upload and manage your documents</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Your Documents
              </CardTitle>
            </CardHeader>
            <CardContent>
              <DocumentList />
            </CardContent>
          </Card>
        </div>

        <div>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5" />
                Upload
              </CardTitle>
            </CardHeader>
            <CardContent>
              <DocumentUpload />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
