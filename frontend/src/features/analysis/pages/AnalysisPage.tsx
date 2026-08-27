import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { ChevronDown, Download, FileText, Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import { apiClient } from '../../../api/client';
import type { Document, FinancialStatement } from '../../../types';
import {
  parseFinancialStatements,
  generateDeterministicKeyFacts,
} from '../utils/financialCalculations';
import { MetricsRow } from '../components/MetricsRow';
import { TrendChart } from '../components/TrendChart';
import {
  BalanceSheetTable,
  RatioTable,
  FinancialStatementsTab,
  RatiosTab,
  ComparisonsTab,
} from '../components/FinancialTables';
import { Highlights } from '../components/Highlights';

type TabType = 'Overview' | 'Financial Statements' | 'Ratios' | 'Trends' | 'Key Facts' | 'Comparisons';

export function AnalysisPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<TabType>('Overview');
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
  const [documentMeta, setDocumentMeta] = useState<Document | null>(null);
  const [financialStatements, setFinancialStatements] = useState<FinancialStatement[]>([]);

  const [isLoadingDocs, setIsLoadingDocs] = useState(true);
  const [isLoadingFinancials, setIsLoadingFinancials] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedPeriod, setSelectedPeriod] = useState<string | undefined>(undefined);
  const [comparePeriod, setComparePeriod] = useState<string | undefined>(undefined);
  const [isDocDropdownOpen, setIsDocDropdownOpen] = useState(false);

  const tabs: TabType[] = [
    'Overview',
    'Financial Statements',
    'Ratios',
    'Trends',
    'Key Facts',
    'Comparisons',
  ];

  // 1. Fetch user documents list
  useEffect(() => {
    setIsLoadingDocs(true);
    apiClient<Document[]>('/api/v1/documents')
      .then((docs) => {
        if (Array.isArray(docs) && docs.length > 0) {
          const activeDocs = docs.filter((d) => !d.isDeleted && d.status !== 'FAILED');
          setDocuments(activeDocs);

          const paramDocId = searchParams.get('documentId');
          const matched = paramDocId ? activeDocs.find((d) => d.id === Number(paramDocId)) : null;

          if (matched) {
            setSelectedDocId(matched.id);
          } else if (activeDocs.length > 0) {
            setSelectedDocId(activeDocs[0].id);
            setSearchParams({ documentId: String(activeDocs[0].id) }, { replace: true });
          }
        } else {
          setDocuments([]);
        }
      })
      .catch((err) => {
        console.error('Failed to fetch documents:', err);
        setError('Unable to load document library.');
      })
      .finally(() => {
        setIsLoadingDocs(false);
      });
  }, []);

  // 2. Fetch selected document metadata and financial statements
  useEffect(() => {
    if (!selectedDocId) return;

    setIsLoadingFinancials(true);
    setError(null);

    Promise.all([
      apiClient<Document>(`/api/v1/documents/${selectedDocId}`),
      apiClient<FinancialStatement[]>(`/api/v1/documents/${selectedDocId}/financial-statements`),
    ])
      .then(([doc, statements]) => {
        setDocumentMeta(doc);
        setFinancialStatements(Array.isArray(statements) ? statements : []);

        // Initialize period selectors if available
        const parsed = parseFinancialStatements(Array.isArray(statements) ? statements : []);
        if (parsed.periods.length > 0) {
          setSelectedPeriod(parsed.periods[0]);
          setComparePeriod(parsed.periods.length > 1 ? parsed.periods[1] : undefined);
        } else {
          setSelectedPeriod(undefined);
          setComparePeriod(undefined);
        }
      })
      .catch((err) => {
        console.error('Failed to load document analysis data:', err);
        setError(err.message || 'Document unavailable or unauthorized.');
        setDocumentMeta(null);
        setFinancialStatements([]);
      })
      .finally(() => {
        setIsLoadingFinancials(false);
      });
  }, [selectedDocId]);

  const handleDocumentChange = (docId: number) => {
    setSelectedDocId(docId);
    setSearchParams({ documentId: String(docId) });
    setIsDocDropdownOpen(false);
  };

  const parsedData = parseFinancialStatements(financialStatements);

  // Export structured financial data as JSON
  const handleExportData = () => {
    if (!documentMeta || !parsedData.hasData) return;
    const exportPayload = {
      documentId: documentMeta.id,
      fileName: documentMeta.fileName,
      documentType: documentMeta.documentType,
      exportedAt: new Date().toISOString(),
      primaryMetrics: parsedData.primaryMetrics,
      ratios: parsedData.ratios,
      periodBreakdown: parsedData.periodMetrics,
      deterministicFacts: generateDeterministicKeyFacts(parsedData),
    };

    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(exportPayload, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `${documentMeta.fileName.replace(/\.[^/.]+$/, '')}_financial_analysis.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  if (isLoadingDocs) {
    return (
      <div className="p-10 max-w-[1400px] mx-auto h-full flex flex-col items-center justify-center gap-3 text-xs text-[#666666] dark:text-[#999999]">
        <Loader2 size={18} className="animate-spin text-penny-accent dark:text-penny-dark-accent" />
        <span>Loading financial workspace...</span>
      </div>
    );
  }

  if (documents.length === 0 && !isLoadingDocs) {
    return (
      <div className="p-10 max-w-[1400px] mx-auto h-full flex flex-col items-center justify-center text-center">
        <FileText size={36} strokeWidth={1} className="text-[#666666] dark:text-[#999999] mb-4" />
        <h2 className="text-base font-medium tracking-tight mb-2">No documents available for analysis</h2>
        <p className="text-xs text-[#666666] dark:text-[#999999] max-w-sm mb-6 leading-relaxed">
          Upload a financial statement PDF in the Documents section to perform deterministic financial analysis.
        </p>
        <button
          type="button"
          onClick={() => navigate('/documents')}
          className="px-4 py-2 text-xs font-medium bg-penny-text text-penny-bg dark:bg-penny-dark-text dark:text-penny-dark-bg hover:opacity-90 transition-opacity cursor-pointer"
        >
          Go to Documents
        </button>
      </div>
    );
  }

  return (
    <div className="p-10 max-w-[1400px] mx-auto h-full overflow-y-auto">
      {/* Header Area */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 mb-10">
        <div>
          <div className="text-[10px] uppercase tracking-widest text-[#666666] dark:text-[#999999] mb-3 flex items-center gap-2">
            <span>Selected Document</span>
            {documentMeta?.status && (
              <span className="font-mono text-[9px] px-1.5 py-0.5 border border-penny-border dark:border-penny-dark-border">
                {documentMeta.status}
              </span>
            )}
          </div>

          {/* Document Switcher Dropdown */}
          <div className="relative inline-block text-left mb-2">
            <button
              type="button"
              onClick={() => setIsDocDropdownOpen(!isDocDropdownOpen)}
              className="flex items-center gap-2 text-3xl font-medium tracking-tight text-penny-text dark:text-penny-dark-text hover:text-penny-accent dark:hover:text-penny-dark-accent transition-colors cursor-pointer group"
            >
              <span className="truncate max-w-xl">
                {documentMeta?.fileName.replace(/\.[^/.]+$/, '') || 'Select Document'}
              </span>
              <ChevronDown size={20} className="shrink-0 group-hover:translate-y-0.5 transition-transform" />
            </button>

            {isDocDropdownOpen && (
              <div className="absolute left-0 top-full mt-2 w-80 bg-penny-surface dark:bg-penny-dark-surface border border-penny-border dark:border-penny-dark-border shadow-xl z-50 py-1">
                <div className="px-3 py-2 text-[10px] uppercase tracking-widest text-[#666666] dark:text-[#999999] border-b border-penny-border dark:border-penny-dark-border font-semibold">
                  Switch Document
                </div>
                {documents.map((doc) => (
                  <button
                    key={doc.id}
                    type="button"
                    onClick={() => handleDocumentChange(doc.id)}
                    className={`w-full text-left px-3.5 py-2.5 text-xs flex items-center justify-between hover:bg-penny-bg dark:hover:bg-penny-dark-bg transition-colors cursor-pointer ${
                      doc.id === selectedDocId ? 'bg-penny-accent/10 text-penny-accent dark:text-penny-dark-accent font-medium' : ''
                    }`}
                  >
                    <span className="truncate">{doc.fileName.replace(/\.[^/.]+$/, '')}</span>
                    <span className="text-[10px] font-mono text-[#666666] dark:text-[#999999]">
                      {doc.fileType}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="text-lg text-[#666666] dark:text-[#999999] mb-2">
            {documentMeta?.documentType || 'Financial Report'}
          </div>

          <div className="flex gap-4 text-xs text-[#666666] dark:text-[#999999]">
            <span>
              {documentMeta?.uploadedAt
                ? `Uploaded ${new Date(documentMeta.uploadedAt).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                  })}`
                : 'Recent'}
            </span>
            <span>•</span>
            <span>USD in millions (extracted)</span>
          </div>
        </div>

        {/* Controls */}
        <div className="flex flex-wrap items-end gap-4">
          {parsedData.periods.length > 0 && (
            <>
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] uppercase tracking-widest text-[#666666] dark:text-[#999999]">
                  Period
                </label>
                <select
                  value={selectedPeriod || ''}
                  onChange={(e) => setSelectedPeriod(e.target.value)}
                  aria-label="Select Period"
                  className="border border-penny-border dark:border-penny-dark-border px-3 py-1.5 text-xs bg-penny-surface dark:bg-penny-dark-surface focus:outline-none cursor-pointer"
                >
                  {parsedData.periods.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>

              {parsedData.periods.length > 1 && (
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] uppercase tracking-widest text-[#666666] dark:text-[#999999]">
                    Compare With
                  </label>
                  <select
                    value={comparePeriod || ''}
                    onChange={(e) => setComparePeriod(e.target.value)}
                    aria-label="Compare With Period"
                    className="border border-penny-border dark:border-penny-dark-border px-3 py-1.5 text-xs bg-penny-surface dark:bg-penny-dark-surface focus:outline-none cursor-pointer"
                  >
                    {parsedData.periods.map((p) => (
                      <option key={p} value={p}>
                        {p}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </>
          )}

          <button
            type="button"
            onClick={handleExportData}
            disabled={!parsedData.hasData}
            className="flex items-center gap-2 border border-penny-text dark:border-penny-dark-text text-penny-text dark:text-penny-dark-text px-4 py-1.5 text-xs font-medium hover:bg-penny-text hover:text-penny-bg dark:hover:bg-penny-dark-text dark:hover:text-penny-dark-bg transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          >
            <Download size={14} /> Export Analysis
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex gap-8 border-b border-penny-border dark:border-penny-dark-border mb-10 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            className={`pb-3 text-xs font-medium transition-colors whitespace-nowrap cursor-pointer ${
              activeTab === tab
                ? 'border-b-2 border-penny-accent dark:border-penny-dark-accent text-penny-text dark:text-penny-dark-text'
                : 'text-[#666666] dark:text-[#999999] hover:text-penny-text dark:hover:text-penny-dark-text'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Error state */}
      {error && (
        <div className="mb-8 p-4 border border-penny-accent/30 bg-penny-accent/5 text-penny-accent dark:text-penny-dark-accent flex items-center justify-between text-xs">
          <div className="flex items-center gap-3">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={() => setSelectedDocId(selectedDocId)}
            className="flex items-center gap-1 font-mono uppercase text-[10px] hover:underline cursor-pointer"
          >
            <RefreshCw size={12} /> Retry
          </button>
        </div>
      )}

      {/* Content Area */}
      {isLoadingFinancials ? (
        <div className="py-20 flex flex-col items-center justify-center gap-3 text-xs text-[#666666] dark:text-[#999999]">
          <Loader2 size={18} className="animate-spin text-penny-accent dark:text-penny-dark-accent" />
          <span>Extracting and computing deterministic metrics...</span>
        </div>
      ) : !parsedData.hasData ? (
        <div className="border border-penny-border dark:border-penny-dark-border bg-penny-surface dark:bg-penny-dark-surface p-12 text-center flex flex-col items-center justify-center">
          <FileText size={32} strokeWidth={1} className="text-[#666666] dark:text-[#999999] mb-3" />
          <h3 className="text-sm font-medium mb-1">No structured financial data available</h3>
          <p className="text-xs text-[#666666] dark:text-[#999999] max-w-md leading-relaxed">
            Financial statements and ratios are extracted automatically when uploading financial PDFs. If this document was recently uploaded, wait until processing reaches READY.
          </p>
        </div>
      ) : (
        <>
          {/* Tab 1: Overview */}
          {activeTab === 'Overview' && (
            <div>
              <MetricsRow
                data={parsedData}
                selectedPeriod={selectedPeriod}
                comparePeriod={comparePeriod}
              />

              <div className="grid grid-cols-1 md:grid-cols-3 gap-10 mb-10">
                <TrendChart
                  data={parsedData}
                  onViewFullTrend={() => setActiveTab('Trends')}
                />
                <BalanceSheetTable
                  data={parsedData}
                  selectedPeriod={selectedPeriod}
                  comparePeriod={comparePeriod}
                  onViewBalanceSheet={() => setActiveTab('Financial Statements')}
                />
                <RatioTable
                  data={parsedData}
                  onViewAllRatios={() => setActiveTab('Ratios')}
                />
              </div>

              <Highlights
                data={parsedData}
                onViewKeyFacts={() => setActiveTab('Key Facts')}
              />
            </div>
          )}

          {/* Tab 2: Financial Statements */}
          {activeTab === 'Financial Statements' && (
            <FinancialStatementsTab
              data={parsedData}
              selectedPeriod={selectedPeriod}
              comparePeriod={comparePeriod}
            />
          )}

          {/* Tab 3: Ratios */}
          {activeTab === 'Ratios' && <RatiosTab data={parsedData} />}

          {/* Tab 4: Trends */}
          {activeTab === 'Trends' && (
            <div className="border border-penny-border dark:border-penny-dark-border bg-penny-surface dark:bg-penny-dark-surface p-8">
              <div className="mb-6 pb-4 border-b border-penny-border dark:border-penny-dark-border">
                <h2 className="text-xl font-medium tracking-tight">Financial Trajectory & Trends</h2>
                <p className="text-xs text-[#666666] dark:text-[#999999] mt-1">
                  Multi-period revenue and income performance across extracted reporting periods.
                </p>
              </div>
              <div className="mb-8">
                <TrendChart data={parsedData} />
              </div>
              <ComparisonsTab
                data={parsedData}
                selectedPeriod={selectedPeriod}
                comparePeriod={comparePeriod}
              />
            </div>
          )}

          {/* Tab 5: Key Facts */}
          {activeTab === 'Key Facts' && (
            <div className="border border-penny-border dark:border-penny-dark-border bg-penny-surface dark:bg-penny-dark-surface p-8">
              <div className="mb-6 pb-4 border-b border-penny-border dark:border-penny-dark-border flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-medium tracking-tight">Deterministic Key Facts</h2>
                  <p className="text-xs text-[#666666] dark:text-[#999999] mt-1">
                    Verifiable observations derived strictly from extracted balance sheet and income statement numbers.
                  </p>
                </div>
                <span className="text-[10px] font-mono text-green-600 dark:text-green-500 uppercase tracking-wider">
                  100% Calculated • Zero Hallucination
                </span>
              </div>

              <div className="flex flex-col divide-y divide-penny-border dark:divide-penny-dark-border">
                {generateDeterministicKeyFacts(parsedData).map((fact, idx) => (
                  <div key={idx} className="py-5">
                    <h3 className="text-sm font-medium text-penny-text dark:text-penny-dark-text mb-1.5">
                      {fact.title}
                    </h3>
                    <p className="text-xs text-[#666666] dark:text-[#999999] leading-relaxed">
                      {fact.desc}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tab 6: Comparisons */}
          {activeTab === 'Comparisons' && (
            <ComparisonsTab
              data={parsedData}
              selectedPeriod={selectedPeriod}
              comparePeriod={comparePeriod}
            />
          )}
        </>
      )}

      {/* Padding at the bottom for scrolling */}
      <div className="h-10"></div>
    </div>
  );
}