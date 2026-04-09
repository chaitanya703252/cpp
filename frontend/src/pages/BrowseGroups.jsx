import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Search, Users } from 'lucide-react';
import { SubjectBadge } from '../components/StatusBadge';
import api from '../api';

const SUBJECTS = [
  '', 'mathematics', 'physics', 'chemistry', 'biology', 'computer_science',
  'english', 'history', 'economics', 'psychology', 'engineering',
  'business', 'statistics', 'data_science', 'law', 'medicine',
];

export default function BrowseGroups() {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [subjectFilter, setSubjectFilter] = useState('');

  const fetchGroups = () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (subjectFilter) params.set('subject', subjectFilter);
    if (search) params.set('search', search);
    api.get(`/groups?${params.toString()}`)
      .then((res) => setGroups(res.data.groups || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchGroups(); }, [subjectFilter]);

  const handleSearch = (e) => {
    e.preventDefault();
    fetchGroups();
  };

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="space-y-4">
          {[1, 2, 3].map((i) => <div key={i} className="skeleton h-24 rounded-xl" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Browse Study Groups</h1>

      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <form onSubmit={handleSearch} className="flex-1 flex gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search groups..."
              className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors cursor-pointer border-none"
          >
            Search
          </button>
        </form>

        <select
          value={subjectFilter}
          onChange={(e) => setSubjectFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent bg-white"
        >
          <option value="">All Subjects</option>
          {SUBJECTS.filter(Boolean).map((s) => (
            <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
          ))}
        </select>
      </div>

      {groups.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <p className="text-gray-500">No study groups found. Try a different search or create one!</p>
        </div>
      ) : (
        <div className="space-y-3">
          {groups.map((group) => (
            <Link
              key={group.id}
              to={`/groups/${group.id}`}
              className="block bg-white rounded-xl border border-gray-200 p-5 hover:border-emerald-200 hover:shadow-sm transition-all no-underline"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <p className="text-base font-semibold text-gray-900">{group.name}</p>
                    <SubjectBadge subject={group.subject} />
                  </div>
                  <p className="text-sm text-gray-500 line-clamp-1">{group.description}</p>
                  <p className="text-xs text-gray-400 mt-1">Created by {group.creatorName}</p>
                </div>
                <div className="flex items-center gap-1.5 text-sm text-gray-500 shrink-0">
                  <Users className="w-4 h-4" />
                  <span>{group.memberCount}/{group.maxMembers}</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
