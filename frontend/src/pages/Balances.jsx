import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../api';

export default function Balances() {
  const { user } = useAuth();
  const [balances, setBalances] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    api.get(`/employees/${user.userId}/balance`)
      .then((res) => setBalances(res.data.balances))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [user]);

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="space-y-4">
          {[1, 2, 3].map((i) => <div key={i} className="skeleton h-24 rounded-xl" />)}
        </div>
      </div>
    );
  }

  const leaveTypes = [
    { key: 'annual', label: 'Annual Leave', total: 20, color: 'blue', desc: 'Planned holidays and vacations' },
    { key: 'sick', label: 'Sick Leave', total: 10, color: 'red', desc: 'Health-related absences' },
    { key: 'unpaid', label: 'Unpaid Leave', total: 30, color: 'gray', desc: 'Leave without pay' },
  ];

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Leave Balances</h1>

      <div className="space-y-4">
        {leaveTypes.map((type) => {
          const remaining = balances?.[type.key] ?? type.total;
          const used = type.total - remaining;
          const percentage = (remaining / type.total) * 100;

          const colorClasses = {
            blue: { bar: 'bg-blue-500', bg: 'bg-blue-50', text: 'text-blue-700', ring: 'ring-blue-100' },
            red: { bar: 'bg-red-500', bg: 'bg-red-50', text: 'text-red-700', ring: 'ring-red-100' },
            gray: { bar: 'bg-gray-400', bg: 'bg-gray-50', text: 'text-gray-600', ring: 'ring-gray-100' },
          };

          const c = colorClasses[type.color];

          return (
            <div key={type.key} className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">{type.label}</h3>
                  <p className="text-sm text-gray-500">{type.desc}</p>
                </div>
                <div className={`${c.bg} ${c.text} px-3 py-1.5 rounded-lg text-center ring-1 ${c.ring}`}>
                  <p className="text-2xl font-bold">{remaining}</p>
                  <p className="text-xs">remaining</p>
                </div>
              </div>

              <div className="w-full bg-gray-100 rounded-full h-3 mb-3">
                <div
                  className={`h-3 rounded-full ${c.bar} transition-all duration-500`}
                  style={{ width: `${percentage}%` }}
                />
              </div>

              <div className="flex justify-between text-sm text-gray-500">
                <span>Used: {used} days</span>
                <span>Total: {type.total} days</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
