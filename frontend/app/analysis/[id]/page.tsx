'use client';
import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { analysisAPI, authAPI } from '@/lib/api';
import Link from 'next/link';

interface AnalysisDetail {
  analysis_id: number;
  resume_filename: string;
  job_description: string;
  match_score: number;
  matched_keywords: string[];
  missing_keywords: string[];
  strengths: string[];
  improvements: string[];
  cover_letter: string | null;
  created_at: string;
}

export default function AnalysisDetailPage() {
  const router = useRouter();
  const params = useParams();
  const analysisId = Number(params.id);

  const [data, setData] = useState<AnalysisDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [clLoading, setClLoading] = useState(false);

  useEffect(() => {
    const fetchAnalysis = async () => {
      try {
        const res = await analysisAPI.getAnalysis(analysisId);
        setData(res.data);
      } catch (err: any) {
        if (err.response?.status === 401) {
          router.push('/login');
        } else if (err.response?.status === 404) {
          setError('Analysis not found');
        } else {
          setError('Could not load analysis');
        }
      } finally {
        setLoading(false);
      }
    };
    fetchAnalysis();
  }, [analysisId]);

  const generateCoverLetter = async () => {
    if (!data) return;
    setClLoading(true);
    try {
      const res = await analysisAPI.getCoverLetter(data.analysis_id);
      setData({ ...data, cover_letter: res.data.cover_letter });
    } catch {
      setError('Cover letter generation failed');
    } finally {
      setClLoading(false);
    }
  };

  const scoreColor = (score: number) =>
    score >= 75 ? 'text-green-400' : score >= 50 ? 'text-yellow-400' : 'text-red-400';

  const scoreBg = (score: number) =>
    score >= 75 ? 'bg-green-400' : score >= 50 ? 'bg-yellow-400' : 'bg-red-400';

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <p className="text-gray-600 text-sm">Loading...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center gap-4">
        <p className="text-red-400 text-sm">{error || 'Something went wrong'}</p>
        <Link href="/dashboard"
          className="text-sky-400 hover:text-sky-300 text-sm">
          ← Back to dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <Link href="/dashboard"
              className="text-gray-500 hover:text-gray-300 text-xs transition-colors">
              ← Back to dashboard
            </Link>
            <h1 className="text-2xl font-bold text-white mt-2">{data.resume_filename}</h1>
            <p className="text-gray-600 text-xs mt-1">
              {new Date(data.created_at).toLocaleDateString('en-US', {
                month: 'long', day: 'numeric', year: 'numeric',
              })}
            </p>
          </div>
          <button
            onClick={() => { authAPI.logout(); router.push('/login'); }}
            className="text-gray-600 hover:text-gray-400 text-sm transition-colors">
            Sign out
          </button>
        </div>

        <div className="space-y-4">
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6
                          flex flex-col md:flex-row gap-6 items-start">
            <div className="flex flex-col items-center">
              <div className={`text-5xl font-bold ${scoreColor(data.match_score)}`}>
                {data.match_score}
              </div>
              <div className="text-gray-600 text-xs mt-1">match score</div>
              <div className="w-24 h-2 bg-gray-800 rounded-full mt-3">
                <div className={`h-2 rounded-full ${scoreBg(data.match_score)}`}
                  style={{ width: `${data.match_score}%` }} />
              </div>
            </div>
            <div>
              <h2 className="text-white font-semibold mb-2 text-sm">Job description</h2>
              <p className="text-gray-400 text-sm leading-relaxed line-clamp-4">
                {data.job_description}
              </p>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h3 className="text-green-400 font-semibold mb-3 text-sm">Matched keywords</h3>
              <div className="flex flex-wrap gap-2">
                {data.matched_keywords.map(k => (
                  <span key={k} className="bg-green-950 text-green-300 text-xs
                                           px-2.5 py-1 rounded-full border border-green-900">
                    {k}
                  </span>
                ))}
              </div>
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h3 className="text-red-400 font-semibold mb-3 text-sm">Missing keywords</h3>
              <div className="flex flex-wrap gap-2">
                {data.missing_keywords.map(k => (
                  <span key={k} className="bg-red-950 text-red-300 text-xs
                                           px-2.5 py-1 rounded-full border border-red-900">
                    {k}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {data.strengths.length > 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h3 className="text-emerald-400 font-semibold mb-3 text-sm">Strengths</h3>
              <ul className="space-y-2">
                {data.strengths.map((s, i) => (
                  <li key={i} className="flex gap-2 text-gray-300 text-sm">
                    <span className="text-emerald-600 mt-0.5 shrink-0">✓</span>{s}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h3 className="text-sky-400 font-semibold mb-3 text-sm">How to improve</h3>
            <ul className="space-y-2">
              {data.improvements.map((imp, i) => (
                <li key={i} className="flex gap-2 text-gray-300 text-sm">
                  <span className="text-sky-600 mt-0.5 shrink-0">→</span>{imp}
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h3 className="text-violet-400 font-semibold mb-1 text-sm">Cover letter</h3>
            <p className="text-gray-600 text-xs mb-4">
              AI-generated based on your resume and this specific job
            </p>
            {data.cover_letter ? (
              <div className="text-gray-300 text-sm leading-relaxed
                              whitespace-pre-wrap bg-gray-800 rounded-lg p-4">
                {data.cover_letter}
              </div>
            ) : (
              <button onClick={generateCoverLetter} disabled={clLoading}
                className="bg-violet-600 hover:bg-violet-500 disabled:opacity-50
                           text-white font-medium px-5 py-2.5 rounded-lg text-sm
                           transition-colors">
                {clLoading ? 'Generating...' : 'Generate cover letter'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}