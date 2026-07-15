'use client';
import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { analysisAPI, authAPI } from '@/lib/api';
import Link from 'next/link';

interface AnalysisResult {
  analysis_id: number;
  match_score: number;
  matched_keywords: string[];
  missing_keywords: string[];
  strengths: string[];
  improvements: string[];
  summary: string;
}

export default function AnalyzePage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [jd, setJd] = useState('');
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [dragging, setDragging] = useState(false);
  const [coverLetter, setCoverLetter] = useState('');
  const [clLoading, setClLoading] = useState(false);

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
    setCoverLetter('');
    try {
      const { data } = await analysisAPI.analyze(file, jd);
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

  const getCoverLetter = async () => {
    if (!result) return;
    setClLoading(true);
    try {
      const { data } = await analysisAPI.getCoverLetter(result.analysis_id);
      setCoverLetter(data.cover_letter);
    } catch (err: any) {
      setError('Cover letter generation failed');
    } finally {
      setClLoading(false);
    }
  };

  const scoreColor = (score: number) =>
    score >= 75 ? 'text-green-400' : score >= 50 ? 'text-yellow-400' : 'text-red-400';

  const scoreBg = (score: number) =>
    score >= 75 ? 'bg-green-400' : score >= 50 ? 'bg-yellow-400' : 'bg-red-400';

  return (
    <div className="min-h-screen bg-gray-950 p-6">
      <div className="max-w-4xl mx-auto">

        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white">Resume Analyzer</h1>
            <p className="text-gray-500 text-sm mt-1">Upload your resume and paste a job description</p>
          </div>
          <div className="flex gap-3 items-center">
            <Link href="/analyze-rag"
              className="text-violet-400 hover:text-violet-300 text-sm transition-colors">
              Explainable (RAG)
            </Link>
            <Link href="/dashboard"
              className="text-gray-400 hover:text-white text-sm transition-colors">
              Dashboard
            </Link>
            <button
              onClick={() => { authAPI.logout(); router.push('/login'); }}
              className="text-gray-600 hover:text-gray-400 text-sm transition-colors">
              Sign out
            </button>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-4 mb-4">
          <div
            onDrop={onDrop}
            onDragOver={e => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onClick={() => document.getElementById('file-input')?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all
              ${dragging ? 'border-sky-500 bg-sky-950/30' : 'border-gray-800 hover:border-gray-600'}`}>
            <input
              id="file-input"
              type="file"
              accept=".pdf,.docx"
              className="hidden"
              onChange={e => setFile(e.target.files?.[0] || null)}
            />
            <div className="text-4xl mb-3">📄</div>
            {file ? (
              <p className="text-sky-400 font-medium text-sm">{file.name}</p>
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
                       focus:border-sky-600 text-sm"
          />
        </div>

        <button
          onClick={analyze}
          disabled={!file || !jd.trim() || loading}
          className="w-full bg-sky-600 hover:bg-sky-500 disabled:opacity-40
                     text-white font-semibold py-3.5 rounded-xl transition-colors mb-6 text-sm">
          {loading ? 'Analyzing your resume...' : 'Analyze my resume'}
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
                <div className="text-gray-600 text-xs mt-1">match score</div>
                <div className="w-24 h-2 bg-gray-800 rounded-full mt-3">
                  <div
                    className={`h-2 rounded-full ${scoreBg(result.match_score)}`}
                    style={{ width: `${result.match_score}%` }}
                  />
                </div>
              </div>
              <div>
                <h2 className="text-white font-semibold mb-2 text-sm">Overall assessment</h2>
                <p className="text-gray-400 text-sm leading-relaxed">{result.summary}</p>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                <h3 className="text-green-400 font-semibold mb-3 text-sm">
                  Matched keywords
                </h3>
                <div className="flex flex-wrap gap-2">
                  {result.matched_keywords.map(k => (
                    <span key={k} className="bg-green-950 text-green-300 text-xs
                                             px-2.5 py-1 rounded-full border border-green-900">
                      {k}
                    </span>
                  ))}
                </div>
              </div>

              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                <h3 className="text-red-400 font-semibold mb-3 text-sm">
                  Missing keywords
                </h3>
                <div className="flex flex-wrap gap-2">
                  {result.missing_keywords.map(k => (
                    <span key={k} className="bg-red-950 text-red-300 text-xs
                                             px-2.5 py-1 rounded-full border border-red-900">
                      {k}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h3 className="text-sky-400 font-semibold mb-3 text-sm">
                How to improve
              </h3>
              <ul className="space-y-2">
                {result.improvements.map((imp, i) => (
                  <li key={i} className="flex gap-2 text-gray-300 text-sm">
                    <span className="text-sky-600 mt-0.5 shrink-0">→</span>
                    {imp}
                  </li>
                ))}
              </ul>
            </div>

            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h3 className="text-violet-400 font-semibold mb-1 text-sm">
                Cover letter
              </h3>
              <p className="text-gray-600 text-xs mb-4">
                AI-generated based on your resume and this specific job
              </p>
              <button
                onClick={getCoverLetter}
                disabled={clLoading}
                className="bg-violet-600 hover:bg-violet-500 disabled:opacity-50
                           text-white font-medium px-5 py-2.5 rounded-lg text-sm
                           transition-colors">
                {clLoading ? 'Generating...' : 'Generate cover letter'}
              </button>
              {coverLetter && (
                <div className="mt-4 text-gray-300 text-sm leading-relaxed
                                whitespace-pre-wrap bg-gray-800 rounded-lg p-4">
                  {coverLetter}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}