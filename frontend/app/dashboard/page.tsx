'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { analysisAPI, authAPI } from '@/lib/api';
import Link from 'next/link';

interface HistoryItem {
  id: number;
  resume_filename: string;
  match_score: number;
  created_at: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const { data } = await analysisAPI.getHistory();
        setHistory(data);
      } catch (err: any) {
        if (err.response?.status === 401) {
          router.push('/login');
        }
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, []);

  const scoreColor = (score: number) =>
    score >= 75 ? 'text-green-400' : score >= 50 ? 'text-yellow-400' : 'text-red-400';

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <div className="min-h-screen bg-gray-950 p-6">
      <div className="max-w-3xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white">Dashboard</h1>
            <p className="text-gray-500 text-sm mt-1">Your analysis history</p>
          </div>
          <div className="flex gap-3">
            <Link href="/analyze"
              className="bg-sky-600 hover:bg-sky-500 text-white text-sm
                         font-medium px-4 py-2 rounded-lg transition-colors">
              New analysis
            </Link>
            <button
              onClick={() => { authAPI.logout(); router.push('/login'); }}
              className="text-gray-600 hover:text-gray-400 text-sm transition-colors">
              Sign out
            </button>
          </div>
        </div>

        {loading ? (
          <div className="text-gray-600 text-sm text-center py-12">
            Loading...
          </div>
        ) : history.length === 0 ? (
          <div className="text-center py-16">
            <div className="text-4xl mb-4">📄</div>
            <p className="text-gray-500 text-sm mb-4">No analyses yet</p>
            <Link href="/analyze"
              className="bg-sky-600 hover:bg-sky-500 text-white text-sm
                         font-medium px-5 py-2.5 rounded-lg transition-colors">
              Analyze your first resume
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {history.map(item => (
  <Link key={item.id} href={`/analysis/${item.id}`}
    className="bg-gray-900 border border-gray-800 rounded-xl p-5
              flex items-center justify-between hover:border-gray-700
              transition-colors cursor-pointer">
    <div className="flex items-center gap-4">
      <div className="text-2xl">📄</div>
      <div>
        <p className="text-white text-sm font-medium">
          {item.resume_filename}
        </p>
        <p className="text-gray-600 text-xs mt-0.5">
          {formatDate(item.created_at)}
        </p>
      </div>
    </div>
    <div className="text-right">
      <div className={`text-2xl font-bold ${scoreColor(item.match_score)}`}>
        {item.match_score}
      </div>
      <div className="text-gray-600 text-xs">match score</div>
    </div>
  </Link>
))}
          </div>
        )}
      </div>
    </div>
  );
}