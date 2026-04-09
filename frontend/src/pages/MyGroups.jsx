import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Users } from 'lucide-react';
import { SubjectBadge, RoleBadge } from '../components/StatusBadge';
import api from '../api';

export default function MyGroups() {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/my-groups')
      .then((res) => setGroups(res.data.groups || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

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
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">My Study Groups</h1>
        <Link
          to="/create-group"
          className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors no-underline"
        >
          Create Group
        </Link>
      </div>

      {groups.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <p className="text-gray-500">You haven't joined any study groups yet.</p>
          <Link to="/browse" className="text-emerald-600 hover:text-emerald-700 text-sm font-medium no-underline">
            Browse groups
          </Link>
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
                    <RoleBadge role={group.myRole} />
                  </div>
                  <p className="text-sm text-gray-500 line-clamp-1">{group.description}</p>
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
