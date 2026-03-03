import { useEffect, useState } from 'react';
import Head from 'next/head';
import { dashboardApi, Stats, AlertLevel, Platform, Narratif, TimelinePoint, TopAccount } from '../lib/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, Legend, PieChart, Pie, Cell } from 'recharts';

const ALERT_COLORS: Record<string, string> = {
  CALME: 'bg-green-500',
  VIGILANCE: 'bg-yellow-500',
  TENSION: 'bg-orange-500',
  CRISE: 'bg-red-600',
};

const SENTIMENT_COLORS = {
  positif: '#22c55e',
  negatif: '#ef4444',
  neutre: '#94a3b8',
  crise: '#7c3aed',
};

const PLATFORM_COLORS = ['#3b82f6', '#8b5cf6', '#06b6d4', '#f59e0b', '#10b981', '#f43f5e', '#6366f1'];

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [alertLevel, setAlertLevel] = useState<AlertLevel | null>(null);
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [narratifs, setNaratifs] = useState<Narratif[]>([]);
  const [timeline, setTimeline] = useState<TimelinePoint[]>([]);
  const [topAccounts, setTopAccounts] = useState<TopAccount[]>([]);
  const [hours, setHours] = useState(24);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const fetchData = async () => {
    try {
      const [statsRes, alertRes, platformsRes, naratifRes, timelineRes, accountsRes] = await Promise.all([
        dashboardApi.getStats(hours),
        dashboardApi.getAlertLevel(),
        dashboardApi.getPlatforms(hours),
        dashboardApi.getNaratifs(hours),
        dashboardApi.getTimeline(hours),
        dashboardApi.getTopAccounts(hours),
      ]);
      setStats(statsRes.data);
      setAlertLevel(alertRes.data);
      setPlatforms(platformsRes.data);
      setNaratifs(naratifRes.data);
      setTimeline(timelineRes.data);
      setTopAccounts(accountsRes.data);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5 * 60 * 1000); // refresh every 5 min
    return () => clearInterval(interval);
  }, [hours]);

  const alertColor = alertLevel ? ALERT_COLORS[alertLevel.level] : 'bg-gray-400';

  return (
    <>
      <Head>
        <title>RW Social Monitor - Meteo Numerique Wadagni 2026</title>
        <meta name="description" content="Monitoring des reseaux sociaux pour la campagne Wadagni 2026" />
      </Head>

      <div className="min-h-screen bg-gray-950 text-white">
        {/* Header */}
        <header className="bg-gray-900 border-b border-gray-800 px-6 py-4">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center font-bold text-lg">RW</div>
              <div>
                <h1 className="text-xl font-bold">RW Social Monitor</h1>
                <p className="text-xs text-gray-400">Meteo Numerique - Campagne Wadagni 2026</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <select
                value={hours}
                onChange={(e) => setHours(Number(e.target.value))}
                className="bg-gray-800 border border-gray-700 rounded px-3 py-1 text-sm"
              >
                <option value={6}>6 heures</option>
                <option value={24}>24 heures</option>
                <option value={48}>48 heures</option>
                <option value={168}>7 jours</option>
              </select>
              <span className="text-xs text-gray-500">Mis a jour: {lastUpdate.toLocaleTimeString('fr-FR')}</span>
              {alertLevel && (
                <span className={`${alertColor} px-3 py-1 rounded-full text-sm font-bold`}>
                  {alertLevel.level}
                </span>
              )}
            </div>
          </div>
        </header>

        <main className="max-w-7xl mx-auto px-6 py-6">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            </div>
          ) : (
            <>
              {/* KPI Row */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                  <p className="text-gray-400 text-sm">Total Mentions</p>
                  <p className="text-3xl font-bold mt-1">{stats?.total ?? 0}</p>
                  <p className="text-xs text-gray-500 mt-1">{hours}h</p>
                </div>
                <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                  <p className="text-gray-400 text-sm">Positif</p>
                  <p className="text-3xl font-bold text-green-400 mt-1">{stats?.positive_pct?.toFixed(1) ?? 0}%</p>
                  <p className="text-xs text-gray-500 mt-1">{stats?.positive ?? 0} mentions</p>
                </div>
                <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                  <p className="text-gray-400 text-sm">Negatif</p>
                  <p className="text-3xl font-bold text-red-400 mt-1">{stats?.negative_pct?.toFixed(1) ?? 0}%</p>
                  <p className="text-xs text-gray-500 mt-1">{stats?.negative ?? 0} mentions</p>
                </div>
                <div className="bg-gray-900 rounded-xl p-4 border border-red-900">
                  <p className="text-gray-400 text-sm">Alertes Crise</p>
                  <p className="text-3xl font-bold text-purple-400 mt-1">{stats?.crisis ?? 0}</p>
                  <p className="text-xs text-gray-500 mt-1">contenus critiques</p>
                </div>
              </div>

              {/* Timeline Chart */}
              <div className="bg-gray-900 rounded-xl p-5 border border-gray-800 mb-6">
                <h2 className="text-lg font-semibold mb-4">Evolution des mentions</h2>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={timeline}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="hour" tick={{ fill: '#9ca3af', fontSize: 11 }} tickFormatter={(v) => v.slice(11, 16)} />
                    <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} />
                    <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none' }} />
                    <Legend />
                    <Line type="monotone" dataKey="positif" stroke={SENTIMENT_COLORS.positif} strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="negatif" stroke={SENTIMENT_COLORS.negatif} strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="neutre" stroke={SENTIMENT_COLORS.neutre} strokeWidth={1} dot={false} />
                    <Line type="monotone" dataKey="crise" stroke={SENTIMENT_COLORS.crise} strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Row: Platforms + Narratifs */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                {/* Platforms */}
                <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
                  <h2 className="text-lg font-semibold mb-4">Volume par plateforme</h2>
                  {platforms.length === 0 ? (
                    <p className="text-gray-500 text-sm">Aucune donnee</p>
                  ) : (
                    <ResponsiveContainer width="100%" height={200}>
                      <PieChart>
                        <Pie data={platforms} dataKey="count" nameKey="platform" cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                          {platforms.map((_, i) => <Cell key={i} fill={PLATFORM_COLORS[i % PLATFORM_COLORS.length]} />)}
                        </Pie>
                        <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none' }} />
                      </PieChart>
                    </ResponsiveContainer>
                  )}
                </div>

                {/* Top Narratifs */}
                <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
                  <h2 className="text-lg font-semibold mb-4">Top Narratifs</h2>
                  {narratifs.length === 0 ? (
                    <p className="text-gray-500 text-sm">Aucun narratif detecte</p>
                  ) : (
                    <div className="space-y-2">
                      {narratifs.slice(0, 8).map((n, i) => (
                        <div key={i} className="flex items-center space-x-2">
                          <div className="flex-1 bg-gray-800 rounded-full h-6 overflow-hidden">
                            <div
                              className="bg-blue-600 h-full flex items-center px-2 text-xs"
                              style={{ width: `${(n.count / narratifs[0].count) * 100}%` }}
                            >
                              {n.narratif}
                            </div>
                          </div>
                          <span className="text-xs text-gray-400 w-8 text-right">{n.count}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Top Accounts */}
              <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
                <h2 className="text-lg font-semibold mb-4">Comptes moteurs</h2>
                {topAccounts.length === 0 ? (
                  <p className="text-gray-500 text-sm">Aucune donnee</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-gray-400 border-b border-gray-800">
                          <th className="text-left py-2">Auteur</th>
                          <th className="text-left py-2">Plateforme</th>
                          <th className="text-right py-2">Mentions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {topAccounts.map((a, i) => (
                          <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                            <td className="py-2">{a.author}</td>
                            <td className="py-2">
                              <span className="bg-blue-900/50 text-blue-300 px-2 py-0.5 rounded text-xs">{a.platform}</span>
                            </td>
                            <td className="py-2 text-right font-medium">{a.count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          )}
        </main>
      </div>
    </>
  );
}
