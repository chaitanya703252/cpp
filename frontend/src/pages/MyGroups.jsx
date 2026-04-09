import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Users, Pencil, Trash2, X, Check } from 'lucide-react';
import { SubjectBadge, RoleBadge } from '../components/StatusBadge';
import api from '../api';

export default function MyGroups() {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({ name: '', description: '' });
  const navigate = useNavigate();

  const fetchGroups = () => {
    setLoading(true);
    api.get('/my-groups')
      .then((res) => setGroups(res.data.groups || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchGroups(); }, []);

  const handleDelete = async (e, groupId, groupName) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm(`Delete "${groupName}"? This will remove all members and sessions.`)) return;
    try {
      await api.delete(`/groups/${groupId}`);
      fetchGroups();
    } catch (err) {
      alert(err.response?.data?.error || 'Failed to delete group');
    }
  };

  const handleEditStart = (e, group) => {
    e.preventDefault();
    e.stopPropagation();
    setEditingId(group.id);
    setEditForm({ name: group.name, description: group.description });
  };

  const handleEditSave = async (e, groupId) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await api.put(`/groups/${groupId}`, editForm);
      setEditingId(null);
      fetchGroups();
    } catch (err) {
      alert(err.response?.data?.error || 'Failed to update group');
    }
  };

  const handleEditCancel = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setEditingId(null);
  };

  const handleLeave = async (e, groupId) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm('Leave this group?')) return;
    try {
      await api.delete(`/groups/${groupId}/leave`);
      fetchGroups();
    } catch (err) {
      alert(err.response?.data?.error || 'Failed to leave group');
    }
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
            <div
              key={group.id}
              className="bg-white rounded-xl border border-gray-200 p-5 hover:border-emerald-200 hover:shadow-sm transition-all"
            >
              {editingId === group.id ? (
                <div className="space-y-3" onClick={(e) => e.stopPropagation()}>
                  <input
                    type="text"
                    value={editForm.name}
                    onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                    placeholder="Group name"
                  />
                  <textarea
                    value={editForm.description}
                    onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                    rows={2}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent resize-none"
                    placeholder="Description"
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={(e) => handleEditSave(e, group.id)}
                      className="flex items-center gap-1 px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors cursor-pointer border-none"
                    >
                      <Check className="w-4 h-4" /> Save
                    </button>
                    <button
                      onClick={handleEditCancel}
                      className="flex items-center gap-1 px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 transition-colors cursor-pointer border border-gray-200"
                    >
                      <X className="w-4 h-4" /> Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <Link to={`/groups/${group.id}`} className="flex-1 no-underline">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="text-base font-semibold text-gray-900">{group.name}</p>
                      <SubjectBadge subject={group.subject} />
                      <RoleBadge role={group.myRole} />
                    </div>
                    <p className="text-sm text-gray-500 line-clamp-1">{group.description}</p>
                  </Link>
                  <div className="flex items-center gap-3 shrink-0">
                    <div className="flex items-center gap-1.5 text-sm text-gray-500">
                      <Users className="w-4 h-4" />
                      <span>{group.memberCount}/{group.maxMembers}</span>
                    </div>
                    {group.myRole === 'organizer' ? (
                      <div className="flex items-center gap-1">
                        <button
                          onClick={(e) => handleEditStart(e, group)}
                          className="p-1.5 text-gray-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors bg-transparent border-none cursor-pointer"
                          title="Edit group"
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button
                          onClick={(e) => handleDelete(e, group.id, group.name)}
                          className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors bg-transparent border-none cursor-pointer"
                          title="Delete group"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={(e) => handleLeave(e, group.id)}
                        className="px-3 py-1.5 text-xs text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors bg-transparent border border-gray-200 cursor-pointer"
                        title="Leave group"
                      >
                        Leave
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
