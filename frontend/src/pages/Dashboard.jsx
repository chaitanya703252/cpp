import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Link } from 'react-router-dom';
import { BookOpen, Clock, Users, CalendarDays, MapPin, Wifi } from 'lucide-react';
import { SubjectBadge } from '../components/StatusBadge';
import api from '../api';

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/dashboard')
      .then((res) => setData(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="skeleton h-28 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Welcome back, {user?.username}</h1>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-2 mb-2">
            <Users className="w-5 h-5 text-emerald-500" />
            <p className="text-sm text-gray-500">My Groups</p>
          </div>
          <p className="text-3xl font-bold text-gray-900">{data.totalGroups}</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-2 mb-2">
            <BookOpen className="w-5 h-5 text-blue-500" />
            <p className="text-sm text-gray-500">Organized</p>
          </div>
          <p className="text-3xl font-bold text-gray-900">{data.organizedGroups}</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-2 mb-2">
            <CalendarDays className="w-5 h-5 text-amber-500" />
            <p className="text-sm text-gray-500">Today's Sessions</p>
          </div>
          <p className="text-3xl font-bold text-gray-900">{data.todaySessions}</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-5 h-5 text-purple-500" />
            <p className="text-sm text-gray-500">Upcoming Sessions</p>
          </div>
          <p className="text-3xl font-bold text-gray-900">{data.totalUpcomingSessions}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Upcoming Sessions</h2>
            <Link to="/schedule" className="text-sm text-emerald-600 hover:text-emerald-700 no-underline">
              View all
            </Link>
          </div>

          {data.upcomingSessions?.length > 0 ? (
            <div className="space-y-3">
              {data.upcomingSessions.map((session) => (
                <Link
                  key={session.id}
                  to={`/groups/${session.groupId}`}
                  className="flex items-center justify-between p-3 rounded-lg border border-gray-100 hover:bg-gray-50 transition-colors no-underline"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-900">{session.title}</p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {session.groupName} &middot; {session.date}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <span>{session.startTime} - {session.endTime}</span>
                    {session.isOnline ? (
                      <Wifi className="w-3.5 h-3.5 text-emerald-500" />
                    ) : (
                      <MapPin className="w-3.5 h-3.5 text-gray-400" />
                    )}
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500">No upcoming sessions. Join a group to get started!</p>
          )}
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Popular Subjects</h2>
            <Link to="/browse" className="text-sm text-emerald-600 hover:text-emerald-700 no-underline">
              Browse
            </Link>
          </div>

          {data.popularSubjects?.length > 0 ? (
            <div className="space-y-3">
              {data.popularSubjects.map((item) => (
                <div key={item.subject} className="flex items-center justify-between">
                  <SubjectBadge subject={item.subject} />
                  <span className="text-sm text-gray-500">{item.count} group{item.count !== 1 ? 's' : ''}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500">No groups created yet</p>
          )}
        </div>
      </div>
    </div>
  );
}
