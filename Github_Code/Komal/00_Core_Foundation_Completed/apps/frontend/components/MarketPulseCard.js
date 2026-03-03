export default function MarketPulseCard({ region, change }) {
  const isPositive = change >= 0
  const colorClass = isPositive ? 'text-green-600' : 'text-red-600'
  const bgClass = isPositive ? 'bg-green-50' : 'bg-red-50'
  const icon = isPositive ? '↑' : '↓'
  
  return (
    <div className={`${bgClass} p-4 rounded-lg shadow-sm hover:shadow-md transition-shadow border border-gray-100`}>
      <div className="text-sm font-medium text-gray-600 mb-1">{region}</div>
      <div className={`text-2xl font-bold ${colorClass} flex items-center gap-2`}>
        <span>{icon}</span>
        <span>{Math.abs(change).toFixed(2)}%</span>
      </div>
    </div>
  )
}

