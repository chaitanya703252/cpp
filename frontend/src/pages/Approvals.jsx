import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { StatusBadge, LeaveTypeBadge } from '../components/StatusBadge';
import { CheckCircle, XCircle } from 'lucide-react';
import api from '../api';

export default function Approvals() {
  const { user } = useAuth();
  const [leaves, setLeaves] = useState([]);
  const [loading, setLoading] = useState(true);
  const [comments, setComments] = useState({});
  const [processing, setProcessing] = useState(null);

  const fetchLeaves = () => {
    setLoading(true);
    api.get('/leaves')
      .then((res) => setLeaves(res.data.leaves || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchLeaves(); }, []);

  const handleAction = async (requestId, status) => {
    if (status === 'rejected' && !comments[requestId]?.trim()) {
      alert('Comments are required when rejecting a request');
      return;
    }
    setProcessing(requestId);
    try {
      await api.put(`/leaves/${requestId}/approve`, {
        status,
        comments: comments[requestId] || '',
      });
      fetchLeaves();
    } catch (err) {
      alert(err.response?.data?.error || `Failed to ${status} request`);
    } finally {
      setProcessing(null);
    }
  };

  if (user?.role !== 'manager') {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <p className="text-gray-500">Only managers can access this page.</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="space-y-4">
          {[1, 2, 3].map((i) => <div key={i} className="skeleton h-32 rounded-xl" />)}
        </div>
      </div>
    );
  }

  const pendingLeaves = leaves.filter((l) => l.status === 'pending');
  const pastLeaves = leaves.filter((l) => l.status !== 'pending');

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Leave Approvals</h1>

      <h2 className="text-lg font-semibold text-gray-800 mb-4">
        Pending Requests ({pendingLeaves.length})
      </h2>

      {pendingLeaves.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center mb-8">
          <p className="text-gray-500">No pending leave requests to review.</p>
        </div>
      ) : (
        <div className="space-y-4 mb-8">
          {pendingLeaves.map((leave) => (
            <div key={leave.requestId} className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <p className="font-medium text-gray-900">{leave.employeeName}</p>
                    <LeaveTypeBadge type={leave.leaveType} />
                    <StatusBadge status={leave.status} />
                  </div>
                  <p className="text-sm text-gray-600">
                    {leave.startDate} to {leave.endDate} ({leave.days} day{leave.days !== 1 ? 's' : ''})
                  </p>
                  <p className="text-sm text-gray-500 mt-1">Reason: {leave.reason}</p>
                </div>
              </div>

              <div className="mt-4 pt-4 border-t border-gray-100">
                <label className="block text-sm font-medium text-gray-700 mb-1">Comments</label>
                <textarea
                  value={comments[leave.requestId] || ''}
                  onChange={(e) => setComments({ ...comments, [leave.requestId]: e.target.value })}
                  rows={2}
                  placeholder="Add comments (required for rejection)"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none mb-3"
                />
                <div className="flex gap-3">
                  <button
                    onClick={() => handleAction(leave.requestId, 'approved')}
                    disabled={processing === leave.requestId}
                    className="flex items-center gap-1.5 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors disabled:opacity-50 cursor-pointer border-none"
                  >
                    <CheckCircle className="w-4 h-4" />
                    Approve
                  </button>
                  <button
                    onClick={() => handleAction(leave.requestId, 'rejected')}
                    disabled={processing === leave.requestId}
                    className="flex items-center gap-1.5 px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition-colors disabled:opacity-50 cursor-pointer border-none"
                  >
                    <XCircle className="w-4 h-4" />
                    Reject
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {pastLeaves.length > 0 && (
        <>
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Past Decisions</h2>
          <div className="space-y-3">
            {pastLeaves.map((leave) => (
              <div key={leave.requestId} className="bg-white rounded-xl border border-gray-200 p-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <p className="text-sm font-medium text-gray-900">{leave.employeeName}</p>
                    <LeaveTypeBadge type={leave.leaveType} />
                    <span className="text-sm text-gray-500">{leave.startDate} - {leave.endDate}</span>
                  </div>
                  <StatusBadge status={leave.status} />
                </div>
                {leave.comments && (
                  <p className="text-xs text-gray-500 mt-2">Comments: {leave.comments}</p>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
