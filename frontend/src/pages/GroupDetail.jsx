import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Users, CalendarDays, Clock, MapPin, Wifi, Plus, Trash2 } from 'lucide-react';
import { SubjectBadge, RoleBadge } from '../components/StatusBadge';
import api from '../api';

export default function GroupDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showSessionForm, setShowSessionForm] = useState(false);
  const [sessionForm, setSessionForm] = useState({
    title: '', date: '', startTime: '', endTime: '', location: '', isOnline: false, notes: '',
  });
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const fetchGroup = () => {
    setLoading(true);
    api.get(`/groups/${id}`)
      .then((res) => setData(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchGroup(); }, [id]);

  const handleJoin = async () => {
    setActionLoading(true);
    try {
      await api.post(`/groups/${id}/join`);
      fetchGroup();
    } catch (err) {
      alert(err.response?.data?.error || 'Failed to join group');
    } finally {
      setActionLoading(false);
    }
  };

  const handleLeave = async () => {
    if (!confirm('Are you sure you want to leave this group?')) return;
    setActionLoading(true);
    try {
      await api.delete(`/groups/${id}/leave`);
      fetchGroup();
    } catch (err) {
      alert(err.response?.data?.error || 'Failed to leave group');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreateSession = async (e) => {
    e.preventDefault();
    setError('');
    setActionLoading(true);
    try {
      await api.post(`/groups/${id}/sessions`, sessionForm);
      setShowSessionForm(false);
      setSessionForm({ title: '', date: '', startTime: '', endTime: '', location: '', isOnline: false, notes: '' });
      fetchGroup();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to create session');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteSession = async (sessionId) => {
    if (!confirm('Delete this session?')) return;
    try {
      await api.delete(`/groups/${id}/sessions/${sessionId}`);
      fetchGroup();
    } catch (err) {
      alert(err.response?.data?.error || 'Failed to delete session');
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="skeleton h-48 rounded-xl mb-6" />
        <div className="skeleton h-64 rounded-xl" />
      </div>
    );
  }

  if (!data) return null;

  const { group, members, sessions, isMember, userRole } = data;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <h1 className="text-2xl font-bold text-gray-900">{group.name}</h1>
              <SubjectBadge subject={group.subject} />
            </div>
            <p className="text-gray-600">{group.description}</p>
            <p className="text-sm text-gray-400 mt-2">Created by {group.creatorName}</p>
          </div>

          <div className="shrink-0">
            {!isMember ? (
              <button
                onClick={handleJoin}
                disabled={actionLoading}
                className="px-5 py-2.5 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors disabled:opacity-50 cursor-pointer border-none"
              >
                Join Group
              </button>
            ) : userRole !== 'organizer' ? (
              <button
                onClick={handleLeave}
                disabled={actionLoading}
                className="px-5 py-2.5 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-red-50 hover:text-red-600 transition-colors disabled:opacity-50 cursor-pointer border border-gray-200"
              >
                Leave Group
              </button>
            ) : null}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <CalendarDays className="w-5 h-5 text-emerald-600" />
                <h2 className="text-lg font-semibold text-gray-900">Upcoming Sessions</h2>
              </div>
              {isMember && (
                <button
                  onClick={() => setShowSessionForm(!showSessionForm)}
                  className="flex items-center gap-1 px-3 py-1.5 bg-emerald-50 text-emerald-700 rounded-lg text-sm font-medium hover:bg-emerald-100 transition-colors cursor-pointer border border-emerald-200"
                >
                  <Plus className="w-4 h-4" />
                  Schedule
                </button>
              )}
            </div>

            {showSessionForm && (
              <form onSubmit={handleCreateSession} className="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
                {error && (
                  <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>
                )}
                <div className="grid grid-cols-2 gap-3 mb-3">
                  <div className="col-span-2">
                    <input
                      type="text"
                      value={sessionForm.title}
                      onChange={(e) => setSessionForm({ ...sessionForm, title: e.target.value })}
                      placeholder="Session title"
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                    />
                  </div>
                  <input
                    type="date"
                    value={sessionForm.date}
                    onChange={(e) => setSessionForm({ ...sessionForm, date: e.target.value })}
                    required
                    className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                  />
                  <div className="flex gap-2">
                    <input
                      type="time"
                      value={sessionForm.startTime}
                      onChange={(e) => setSessionForm({ ...sessionForm, startTime: e.target.value })}
                      required
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                    />
                    <input
                      type="time"
                      value={sessionForm.endTime}
                      onChange={(e) => setSessionForm({ ...sessionForm, endTime: e.target.value })}
                      required
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                    />
                  </div>
                  <input
                    type="text"
                    value={sessionForm.location}
                    onChange={(e) => setSessionForm({ ...sessionForm, location: e.target.value })}
                    placeholder="Location (e.g., Library Room 201)"
                    className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                  />
                  <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={sessionForm.isOnline}
                      onChange={(e) => setSessionForm({ ...sessionForm, isOnline: e.target.checked })}
                      className="w-4 h-4 text-emerald-600 rounded"
                    />
                    Online session
                  </label>
                  <textarea
                    value={sessionForm.notes}
                    onChange={(e) => setSessionForm({ ...sessionForm, notes: e.target.value })}
                    placeholder="Notes (optional)"
                    rows={2}
                    className="col-span-2 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent resize-none"
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    type="submit"
                    disabled={actionLoading}
                    className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors disabled:opacity-50 cursor-pointer border-none"
                  >
                    {actionLoading ? 'Creating...' : 'Create Session'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowSessionForm(false)}
                    className="px-4 py-2 bg-white text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors cursor-pointer border border-gray-200"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}

            {sessions?.length > 0 ? (
              <div className="space-y-3">
                {sessions.map((s) => (
                  <div key={s.id} className="p-4 rounded-lg border border-gray-100">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{s.title}</p>
                        <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                          <span className="flex items-center gap-1">
                            <CalendarDays className="w-3.5 h-3.5" />
                            {s.date}
                          </span>
                          <span className="flex items-center gap-1">
                            <Clock className="w-3.5 h-3.5" />
                            {s.startTime} - {s.endTime}
                          </span>
                          <span className="flex items-center gap-1">
                            {s.isOnline ? <Wifi className="w-3.5 h-3.5 text-emerald-500" /> : <MapPin className="w-3.5 h-3.5" />}
                            {s.isOnline ? 'Online' : s.location || 'TBD'}
                          </span>
                        </div>
                        {s.notes && <p className="text-xs text-gray-400 mt-1">{s.notes}</p>}
                      </div>
                      {(userRole === 'organizer' || s.createdBy === user?.userId) && (
                        <button
                          onClick={() => handleDeleteSession(s.id)}
                          className="text-gray-400 hover:text-red-600 transition-colors bg-transparent border-none cursor-pointer"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">No upcoming sessions scheduled</p>
            )}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Users className="w-5 h-5 text-emerald-600" />
            <h2 className="text-lg font-semibold text-gray-900">Members ({members?.length || 0})</h2>
          </div>

          <div className="space-y-3">
            {members?.map((m) => (
              <div key={m.userId} className="flex items-center justify-between">
                <span className="text-sm text-gray-900">{m.username}</span>
                <RoleBadge role={m.role} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
