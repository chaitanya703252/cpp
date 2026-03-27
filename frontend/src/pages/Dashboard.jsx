import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { CalendarDays, Clock, CheckCircle, XCircle, Users } from 'lucide-react';
import { StatusBadge, LeaveTypeBadge } from '../components/StatusBadge';
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
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-32 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (!data) return null;

  if (user.role === 'employee') return <EmployeeDashboard data={data} />;
  return <ManagerDashboard data={data} />;
}

function EmployeeDashboard({ data }) {
  const balances = data.balances || {};

  const balanceCards = [
    { label: 'Annual Leave', total: 20, remaining: balances.annual ?? 20, color: 'blue' },
    { label: 'Sick Leave', total: 10, remaining: balances.sick ?? 10, color: 'red' },
    { label: 'Unpaid Leave', total: 30, remaining: balances.unpaid ?? 30, color: 'gray' },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Welcome back, {data.name}</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {balanceCards.map((card) => (
          <div key={card.label} className="bg-white rounded-xl border border-gray-200 p-6">
            <p className="text-sm text-gray-500 mb-1">{card.label}</p>
            <p className="text-3xl font-bold text-gray-900">{card.remaining}</p>
            <p className="text-sm text-gray-400 mt-1">of {card.total} days remaining</p>
            <div className="mt-3 w-full bg-gray-100 rounded-full h-2">
              <div
                className={`h-2 rounded-full ${
                  card.color === 'blue' ? 'bg-blue-500' : card.color === 'red' ? 'bg-red-500' : 'bg-gray-400'
                }`}
                style={{ width: `${(card.remaining / card.total) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="w-5 h-5 text-amber-500" />
            <h2 className="text-lg font-semibold text-gray-900">Pending Requests</h2>
            <span className="ml-auto bg-amber-50 text-amber-700 px-2.5 py-0.5 rounded-full text-sm font-medium">
              {data.pendingRequests}
            </span>
          </div>
          <p className="text-sm text-gray-500">
            {data.pendingRequests === 0
              ? 'No pending requests'
              : `You have ${data.pendingRequests} request(s) awaiting approval`}
          </p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-2 mb-4">
            <CalendarDays className="w-5 h-5 text-blue-500" />
            <h2 className="text-lg font-semibold text-gray-900">Upcoming Leaves</h2>
          </div>
          {data.upcomingLeaves?.length > 0 ? (
            <div className="space-y-3">
              {data.upcomingLeaves.map((leave) => (
                <div key={leave.requestId} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <LeaveTypeBadge type={leave.leaveType} />
                    <span className="text-gray-700">{leave.startDate} - {leave.endDate}</span>
                  </div>
                  <StatusBadge status={leave.status} />
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500">No upcoming leaves scheduled</p>
          )}
        </div>
      </div>
    </div>
  );
}

function ManagerDashboard({ data }) {
  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Manager Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-5 h-5 text-amber-500" />
            <p className="text-sm text-gray-500">Pending Approvals</p>
          </div>
          <p className="text-3xl font-bold text-gray-900">{data.pendingApprovals}</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-2 mb-2">
            <Users className="w-5 h-5 text-blue-500" />
            <p className="text-sm text-gray-500">On Leave Today</p>
          </div>
          <p className="text-3xl font-bold text-gray-900">{data.teamOnLeaveToday?.length || 0}</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="w-5 h-5 text-green-500" />
            <p className="text-sm text-gray-500">Approved</p>
          </div>
          <p className="text-3xl font-bold text-gray-900">{data.leaveStats?.approved || 0}</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-2 mb-2">
            <XCircle className="w-5 h-5 text-red-500" />
            <p className="text-sm text-gray-500">Rejected</p>
          </div>
          <p className="text-3xl font-bold text-gray-900">{data.leaveStats?.rejected || 0}</p>
        </div>
      </div>

      {data.teamOnLeaveToday?.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Team on Leave Today</h2>
          <div className="space-y-3">
            {data.teamOnLeaveToday.map((person, i) => (
              <div key={i} className="flex items-center justify-between text-sm border-b border-gray-100 pb-2 last:border-0">
                <span className="font-medium text-gray-900">{person.employeeName}</span>
                <div className="flex items-center gap-2">
                  <LeaveTypeBadge type={person.leaveType} />
                  <span className="text-gray-400">until {person.endDate}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
