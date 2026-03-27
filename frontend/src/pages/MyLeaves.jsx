import { useState, useEffect } from 'react';
import { StatusBadge, LeaveTypeBadge } from '../components/StatusBadge';
import { Trash2 } from 'lucide-react';
import api from '../api';

export default function MyLeaves() {
  const [leaves, setLeaves] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchLeaves = () => {
    setLoading(true);
    api.get('/leaves')
      .then((res) => setLeaves(res.data.leaves || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchLeaves(); }, []);

  const handleCancel = async (id) => {
    if (!confirm('Are you sure you want to cancel this leave request?')) return;
    try {
      await api.delete(`/leaves/${id}`);
      fetchLeaves();
    } catch (err) {
      alert(err.response?.data?.error || 'Failed to cancel request');
    }
  };

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="space-y-4">
          {[1, 2, 3].map((i) => <div key={i} className="skeleton h-20 rounded-xl" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">My Leave Requests</h1>

      {leaves.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <p className="text-gray-500">No leave requests found. Submit your first request!</p>
        </div>
      ) : (
        <div className="space-y-3">
          {leaves.map((leave) => (
            <div key={leave.requestId} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <LeaveTypeBadge type={leave.leaveType} />
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {leave.startDate} to {leave.endDate}
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5">{leave.days} day(s) - {leave.reason}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={leave.status} />
                  {leave.status === 'pending' && (
                    <button
                      onClick={() => handleCancel(leave.requestId)}
                      className="text-gray-400 hover:text-red-600 transition-colors bg-transparent border-none cursor-pointer"
                      title="Cancel request"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
              {leave.comments && (
                <div className="mt-3 pt-3 border-t border-gray-100">
                  <p className="text-xs text-gray-500">
                    <span className="font-medium">Manager comments:</span> {leave.comments}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
