export function StatusBadge({ status }) {
  const styles = {
    pending: 'bg-amber-50 text-amber-700 border border-amber-200',
    approved: 'bg-green-50 text-green-700 border border-green-200',
    rejected: 'bg-red-50 text-red-700 border border-red-200',
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${styles[status] || 'bg-gray-50 text-gray-700 border border-gray-200'}`}>
      {status}
    </span>
  );
}

export function LeaveTypeBadge({ type }) {
  const styles = {
    annual: 'bg-blue-50 text-blue-700 border border-blue-200',
    sick: 'bg-red-50 text-red-700 border border-red-200',
    unpaid: 'bg-gray-50 text-gray-600 border border-gray-200',
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${styles[type] || 'bg-gray-50 text-gray-700 border border-gray-200'}`}>
      {type}
    </span>
  );
}
