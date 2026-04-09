export function SubjectBadge({ subject }) {
  const colors = {
    mathematics: 'bg-blue-50 text-blue-700 border border-blue-200',
    physics: 'bg-purple-50 text-purple-700 border border-purple-200',
    chemistry: 'bg-orange-50 text-orange-700 border border-orange-200',
    biology: 'bg-green-50 text-green-700 border border-green-200',
    computer_science: 'bg-indigo-50 text-indigo-700 border border-indigo-200',
    engineering: 'bg-slate-50 text-slate-700 border border-slate-200',
    economics: 'bg-amber-50 text-amber-700 border border-amber-200',
    business: 'bg-teal-50 text-teal-700 border border-teal-200',
    data_science: 'bg-cyan-50 text-cyan-700 border border-cyan-200',
  };

  const label = (subject || '').replace(/_/g, ' ');

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${colors[subject] || 'bg-gray-50 text-gray-700 border border-gray-200'}`}>
      {label}
    </span>
  );
}

export function RoleBadge({ role }) {
  const styles = {
    organizer: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
    member: 'bg-gray-50 text-gray-600 border border-gray-200',
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${styles[role] || 'bg-gray-50 text-gray-700 border border-gray-200'}`}>
      {role}
    </span>
  );
}
