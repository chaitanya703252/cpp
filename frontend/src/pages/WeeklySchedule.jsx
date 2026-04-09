import { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, MapPin, Wifi } from 'lucide-react';
import { Link } from 'react-router-dom';
import api from '../api';

export default function WeeklySchedule() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [weekStart, setWeekStart] = useState(() => {
    const now = new Date();
    const day = now.getDay();
    const diff = now.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(now.setDate(diff));
  });

  useEffect(() => {
    api.get('/my-groups')
      .then(async (res) => {
        const groups = res.data.groups || [];
        const allSessions = [];

        for (const g of groups) {
          try {
            const sRes = await api.get(`/groups/${g.id}/sessions`);
            const gSessions = (sRes.data.sessions || []).map((s) => ({ ...s, groupName: g.name }));
            allSessions.push(...gSessions);
          } catch { /* skip */ }
        }

        setSessions(allSessions);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  const getWeekDates = () => {
    const dates = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(weekStart);
      d.setDate(d.getDate() + i);
      dates.push(d);
    }
    return dates;
  };

  const weekDates = getWeekDates();

  const formatDate = (d) => d.toISOString().split('T')[0];

  const getSessionsForDate = (date) => {
    const dateStr = formatDate(date);
    return sessions
      .filter((s) => s.date === dateStr)
      .sort((a, b) => (a.startTime || '').localeCompare(b.startTime || ''));
  };

  const prevWeek = () => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() - 7);
    setWeekStart(d);
  };

  const nextWeek = () => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + 7);
    setWeekStart(d);
  };

  const isToday = (d) => formatDate(d) === formatDate(new Date());

  const monthYear = weekDates[0].toLocaleString('default', { month: 'long', year: 'numeric' });

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="skeleton h-96 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Weekly Schedule</h1>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <button
            onClick={prevWeek}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors bg-transparent border-none cursor-pointer"
          >
            <ChevronLeft className="w-5 h-5 text-gray-600" />
          </button>
          <h2 className="text-lg font-semibold text-gray-900">{monthYear}</h2>
          <button
            onClick={nextWeek}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors bg-transparent border-none cursor-pointer"
          >
            <ChevronRight className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        <div className="grid grid-cols-7 min-h-[400px]">
          {weekDates.map((date, i) => {
            const daySessions = getSessionsForDate(date);
            const today = isToday(date);

            return (
              <div
                key={i}
                className={`border-r border-gray-100 last:border-r-0 ${
                  i >= 5 ? 'bg-gray-50' : ''
                }`}
              >
                <div className={`p-3 text-center border-b border-gray-100 ${
                  today ? 'bg-emerald-50' : ''
                }`}>
                  <p className="text-xs text-gray-500">{dayNames[i]}</p>
                  <p className={`text-lg font-semibold ${
                    today ? 'text-emerald-600' : 'text-gray-900'
                  }`}>
                    {date.getDate()}
                  </p>
                </div>

                <div className="p-2 space-y-2">
                  {daySessions.map((s) => (
                    <Link
                      key={s.id}
                      to={`/groups/${s.groupId}`}
                      className="block p-2 rounded-lg bg-emerald-50 border border-emerald-100 hover:bg-emerald-100 transition-colors no-underline"
                    >
                      <p className="text-xs font-medium text-emerald-800 truncate">{s.title}</p>
                      <p className="text-[10px] text-emerald-600 mt-0.5">
                        {s.startTime}-{s.endTime}
                      </p>
                      <div className="flex items-center gap-1 mt-0.5">
                        {s.isOnline ? (
                          <Wifi className="w-2.5 h-2.5 text-emerald-500" />
                        ) : (
                          <MapPin className="w-2.5 h-2.5 text-gray-400" />
                        )}
                        <p className="text-[10px] text-gray-500 truncate">
                          {s.groupName}
                        </p>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
