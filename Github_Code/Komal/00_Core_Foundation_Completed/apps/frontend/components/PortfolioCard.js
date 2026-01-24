export default function PortfolioCard({ title, value, change, changePercent, subtitle }) {
  const isPositive = change >= 0
  const changeColor = change !== undefined ? (isPositive ? 'text-green-600' : 'text-red-600') : ''
  
  return (
    <div className="bg-white p-6 rounded-lg shadow-sm hover:shadow-md transition-all border border-gray-100">
      <div className="text-sm font-medium text-gray-500 mb-1">{title}</div>
      <div className="text-3xl font-bold text-gray-900 mb-2">{value}</div>
      {change !== undefined && (
        <div className="flex items-center gap-2">
          <span className={`text-sm font-semibold ${changeColor}`}>
            {isPositive ? '+' : ''}{change >= 0 ? change.toFixed(2) : Math.abs(change).toFixed(2)}
          </span>
          {changePercent !== undefined && (
            <span className={`text-sm font-medium ${changeColor}`}>
              ({isPositive ? '+' : ''}{changePercent >= 0 ? changePercent.toFixed(2) : Math.abs(changePercent).toFixed(2)}%)
            </span>
          )}
        </div>
      )}
      {subtitle && (
        <div className="text-xs text-gray-400 mt-2">{subtitle}</div>
      )}
    </div>
  )
}

