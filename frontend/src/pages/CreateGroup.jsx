import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen } from 'lucide-react';
import api from '../api';

const SUBJECTS = [
  'mathematics', 'physics', 'chemistry', 'biology', 'computer_science',
  'english', 'history', 'economics', 'psychology', 'engineering',
  'business', 'statistics', 'data_science', 'law', 'medicine',
];

export default function CreateGroup() {
  const [form, setForm] = useState({ name: '', subject: '', description: '', maxMembers: 8 });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await api.post('/groups', { ...form, maxMembers: parseInt(form.maxMembers) });
      navigate(`/groups/${res.data.group.id}`);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to create group');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <div className="flex items-center gap-2 mb-6">
        <BookOpen className="w-6 h-6 text-emerald-600" />
        <h1 className="text-2xl font-bold text-gray-900">Create Study Group</h1>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-8">
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Group Name</label>
            <input
              type="text"
              name="name"
              value={form.name}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
              placeholder="e.g., Calculus Study Group"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Subject</label>
            <select
              name="subject"
              value={form.subject}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent bg-white"
            >
              <option value="">Select a subject</option>
              {SUBJECTS.map((s) => (
                <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              name="description"
              value={form.description}
              onChange={handleChange}
              required
              rows={4}
              minLength={10}
              placeholder="Describe what your study group will focus on (minimum 10 characters)"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent resize-none"
            />
            <p className="mt-1 text-xs text-gray-400">{form.description.length}/10 minimum characters</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Max Members</label>
            <input
              type="number"
              name="maxMembers"
              value={form.maxMembers}
              onChange={handleChange}
              min={2}
              max={20}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
            />
            <p className="mt-1 text-xs text-gray-400">Between 2 and 20 members</p>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-emerald-600 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors disabled:opacity-50 cursor-pointer border-none"
          >
            {loading ? 'Creating...' : 'Create Study Group'}
          </button>
        </form>
      </div>
    </div>
  );
}
