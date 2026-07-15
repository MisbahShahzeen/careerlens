'use client';
import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { analysisAPI, authAPI } from '@/lib/api';
import Link from 'next/link';

interface RequirementScore {
  requirement: string;
  score: number;
  explanation: string;
  evidence: string | null;
  similarity: number;
  has_strong_evidence: boolean;
}

interface RagResult {
  analysis_id: number;
  match_score: number;
  requirement_scores: RequirementScore[];
  matched_keywords: string[];
  missing_keywords: string[];
  summary: string;
}

export default function AnalyzeRagPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [jd, setJd] = useState('');
  const [result, setResult] = useState<RagResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [dragging, setDragging] = useState(false);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped?.name.match(/\.(pdf|docx)$/i)) setFile(dropped);
  }, []);

  const analyze = async () => {
    if (!file || !jd.trim()) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const { data } = await analysisAPI.analyzeRag(file, jd);
      setResult(data);
    } catch (err: any) {
      if (err.response?.status === 401) {
        router.push('/login');
      } else {
        setError(err.response?.data?.detail || 'Analysis failed');
      }
    } finally {
      setLoading(false);
    }
  };

  const scoreColor = (score: number) =>
    score >= 70 ? 'text-green-400' : score >= 40 ? 'text-yellow-400' : 'text-red-400';

  const scoreBg = (score: number) =>
    score >= 70 ? 'bg-green-500' : score >= 40 ? 'bg-yellow-500' : 'bg-red-500';

  return (
    <div className="min-h-screen bg-gray-950 p-6">
      <div className="max-w-4xl mx-auto">

        <div className="flex justify-between items-center mb-2">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-white">Explainable Analysis</h1>
              <span className="bg-violet-950 text-violet-300 text-xs px-2 py-0.5 rounded-full border border-violet-800">
                RAG
              </span>
            </div>
            <p className="text-gray-500 text-sm mt-1">
              Semantic retrieval matches each job requirement to evidence in your resume
            </p>
          </div>
          <div className="flex gap-3 items-center">
            <Link href="/analyze" className="text-gray-400 hover:text-white text-sm">
              Standard analysis
            </Link>
            <Link href="/dashboard" className="text-gray-400 hover:text-white text-sm">
              Dashboard
            </Link>
            <button
              onClick={() => { authAPI.logout(); router.push('/login'); }}
              className="text-gray-600 hover:text-gray-400 text-sm">
              Sign out
            </button>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-4 mb-4 mt-6">
          <div
            onDrop={onDrop}
            onDragOver={e => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onClick={() => document.getElementById('file-input')?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all
              ${dragging ? 'border-violet-500 bg-violet-950/30' : 'border-gray-800 hover:border-gray-600'}`}>
            <input
              id="file-input"
              type="file"
              accept=".pdf,.docx"
              className="hidden"
              onChange={e => setFile(e.target.files?.[0] || null)}
            />
            <div className="text-4xl mb-3">📄</div>
            {file ? (
              <p className="text-violet-400 font-medium text-sm">{file.name}</p>
            ) : (
              <>
                <p className="text-gray-500 text-sm">Drop your resume here</p>
                <p className="text-gray-700 text-xs mt-1">PDF or DOCX</p>
              </>
            )}
          </div>

          <textarea
            value={jd}
            onChange={e => setJd(e.target.value)}
            placeholder="Paste the job description here..."
            rows={8}
            className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-gray-300
                       placeholder-gray-600 resize-none focus:outline-none
                       focus:border-violet-600 text-sm"
          />
        </div>

        <button
          onClick={analyze}
          disabled={!file || !jd.trim() || loading}
          className="w-full bg-violet-600 hover:bg-violet-500 disabled:opacity-40
                     text-white font-semibold py-3.5 rounded-xl transition-colors mb-6 text-sm">
          {loading ? 'Retrieving evidence and scoring each requirement...' : 'Analyze with RAG'}
        </button>

        {error && (
          <div className="text-red-400 text-sm bg-red-950 border border-red-900 rounded-xl p-4 mb-4">
            {error}
          </div>
        )}

        {result && (
          <div className="space-y-4">

            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 flex flex-col md:flex-row gap-6 items-start">
              <div className="flex flex-col items-center">
                <div className={`text-5xl font-bold ${scoreColor(result.match_score)}`}>
                  {result.match_score}
                </div>
                <div className="text-gray-600 text-xs mt-1">overall match</div>
              </div>
              <div>
                <h2 className="text-white font-semibold mb-2 text-sm">Summary</h2>
                <p className="text-gray-400 text-sm leading-relaxed">{result.summary}</p>
              </div>
            </div>

            <div>
              <h3 className="text-white font-semibold text-sm mb-3">
                Requirement-by-requirement breakdown
              </h3>
              <div className="space-y-3">
                {result.requirement_scores.map((req, i) => (
                  <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                    <div className="flex justify-between items-start gap-4 mb-3">
                      <p className="text-gray-200 text-sm font-medium flex-1">
                        {req.requirement}
                      </p>
                      <div className="text-right shrink-0">
                        <div className={`text-2xl font-bold ${scoreColor(req.score)}`}>
                          {req.score}
                        </div>
                      </div>
                    </div>

                    <div className="w-full h-1.5 bg-gray-800 rounded-full mb-3">
                      <div
                        className={`h-1.5 rounded-full ${scoreBg(req.score)}`}
                        style={{ width: `${req.score}%` }}
                      />
                    </div>

                    <p className="text-gray-400 text-xs mb-3 leading-relaxed">
                      {req.explanation}
                    </p>

                    {req.evidence && (
                      <div className="bg-gray-950 border border-gray-800 rounded-lg p-3">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-gray-600 text-xs uppercase tracking-wide">
                            Evidence from resume
                          </span>
                          <span className={`text-xs px-2 py-0.5 rounded-full border
                            ${req.has_strong_evidence
                              ? 'bg-green-950 text-green-400 border-green-900'
                              : 'bg-yellow-950 text-yellow-500 border-yellow-900'}`}>
                            {req.has_strong_evidence ? 'strong' : 'weak'} · {(req.similarity * 100).toFixed(0)}% match
                          </span>
                        </div>
                        <p className="text-gray-400 text-xs leading-relaxed">
                          {req.evidence}
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}