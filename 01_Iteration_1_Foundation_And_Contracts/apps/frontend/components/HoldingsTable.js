import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function HoldingsTable({ holdings, onWatchlistToggle, getToken, watchlist = [], onHoldingsUpdate }) {
  if (!holdings || holdings.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
        No holdings found
      </div>
    )
  }
  
  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">Your Holdings</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Wine
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Region
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Quantity
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Current Value
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                P/L
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                ROI
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Trend
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Watchlist
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {holdings.map((holding) => (
              <tr key={holding.id || holding.asset_id} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900">
                    {holding.asset_name}
                  </div>
                  <div className="text-sm text-gray-500">{holding.vintage}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">{holding.region}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">{holding.quantity}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900">
                    ₹{holding.current_value.toFixed(2)}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className={`text-sm font-medium ${
                    holding.profit_loss >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {holding.profit_loss >= 0 ? '+' : ''}₹{holding.profit_loss.toFixed(2)}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className={`text-sm font-medium ${
                    holding.roi_percent >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {holding.roi_percent >= 0 ? '+' : ''}{holding.roi_percent.toFixed(2)}%
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    holding.trend === 'up' ? 'bg-green-100 text-green-800' :
                    holding.trend === 'down' ? 'bg-red-100 text-red-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {holding.trend === 'up' ? '↑' : holding.trend === 'down' ? '↓' : '→'} {holding.trend}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    holding.status === 'OPEN' ? 'bg-blue-100 text-blue-800' :
                    holding.status === 'PARTIALLY_SOLD' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {holding.status}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {getToken && holding.id && (
                    <HoldingActions 
                      holding={holding}
                      getToken={getToken}
                      onHoldingsUpdate={onHoldingsUpdate}
                    />
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {getToken && (
                    <WatchlistButton 
                      assetId={holding.asset_id}
                      isInWatchlist={watchlist.some(w => w.asset_id === holding.asset_id)}
                      onToggle={onWatchlistToggle}
                      getToken={getToken}
                    />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function HoldingActions({ holding, getToken, onHoldingsUpdate }) {
  const [isSelling, setIsSelling] = useState(false)
  const [showSellModal, setShowSellModal] = useState(false)
  const [sellQuantity, setSellQuantity] = useState('')

  const handleSell = async (quantity = null) => {
    if (isSelling) return
    
    setIsSelling(true)
    try {
      const token = await getToken()
      const authConfig = {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
      
      const response = await axios.post(`${API_BASE}/api/holdings/sell`, {
        holding_id: holding.id,
        quantity: quantity || null
      }, authConfig)
      
      // Show success message
      const qty = quantity || holding.quantity
      alert(`Successfully sold ${qty} unit(s) of ${holding.asset_name}`)
      
      if (onHoldingsUpdate) {
        await onHoldingsUpdate()
      }
      setShowSellModal(false)
      setSellQuantity('')
    } catch (err) {
      console.error('Failed to sell holding:', err)
      alert(err.response?.data?.detail || 'Failed to sell holding. Please try again.')
    } finally {
      setIsSelling(false)
    }
  }

  const handlePartialSell = () => {
    const qty = parseInt(sellQuantity)
    if (!qty || qty <= 0 || qty >= holding.quantity) {
      alert(`Please enter a quantity between 1 and ${holding.quantity - 1}`)
      return
    }
    handleSell(qty)
  }

  if (holding.status === 'SOLD' || holding.status === 'CANCELLED') {
    return <span className="text-xs text-gray-400">No actions</span>
  }

  return (
    <div className="flex items-center gap-2">
      {holding.status === 'OPEN' && (
        <>
          <button
            onClick={() => setShowSellModal(true)}
            className="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 hover:bg-yellow-200 rounded transition-colors"
            title="Partial sell"
          >
            Partial
          </button>
          <button
            onClick={() => {
              if (confirm(`Sell all ${holding.quantity} units of ${holding.asset_name}?`)) {
                handleSell()
              }
            }}
            disabled={isSelling}
            className="px-2 py-1 text-xs bg-red-100 text-red-800 hover:bg-red-200 rounded transition-colors disabled:opacity-50"
            title="Sell all"
          >
            Sell
          </button>
        </>
      )}
      {holding.status === 'PARTIALLY_SOLD' && (
        <button
          onClick={() => {
            if (confirm(`Sell remaining ${holding.quantity} units of ${holding.asset_name}?`)) {
              handleSell()
            }
          }}
          disabled={isSelling}
          className="px-2 py-1 text-xs bg-red-100 text-red-800 hover:bg-red-200 rounded transition-colors disabled:opacity-50"
          title="Sell remaining"
        >
          Sell
        </button>
      )}
      
      {showSellModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Partial Sell</h3>
            <p className="text-sm text-gray-600 mb-4">
              You have {holding.quantity} units of {holding.asset_name}
            </p>
            <input
              type="number"
              min="1"
              max={holding.quantity - 1}
              value={sellQuantity}
              onChange={(e) => setSellQuantity(e.target.value)}
              placeholder="Quantity to sell"
              className="w-full px-3 py-2 border border-gray-300 rounded-md mb-4 text-gray-900 text-base font-normal focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500"
              style={{
                color: '#111827',
                fontSize: '16px',
                lineHeight: '1.5',
                padding: '0.5rem 0.75rem',
                width: '100%',
                boxSizing: 'border-box',
                WebkitAppearance: 'textfield',
                MozAppearance: 'textfield'
              }}
            />
            <div className="flex gap-2">
              <button
                onClick={handlePartialSell}
                disabled={isSelling}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
              >
                {isSelling ? 'Selling...' : 'Sell'}
              </button>
              <button
                onClick={() => {
                  setShowSellModal(false)
                  setSellQuantity('')
                }}
                className="flex-1 px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function WatchlistButton({ assetId, isInWatchlist, onToggle, getToken }) {
  const [isToggling, setIsToggling] = useState(false)
  const [inWatchlist, setInWatchlist] = useState(isInWatchlist)

  useEffect(() => {
    setInWatchlist(isInWatchlist)
  }, [isInWatchlist])

  const handleToggle = async (e) => {
    e.stopPropagation()
    if (isToggling) return
    
    setIsToggling(true)
    const wasInWatchlist = inWatchlist
    
    setInWatchlist(!wasInWatchlist)
    
    try {
      if (onToggle) {
        await onToggle(assetId)
      }
    } catch (err) {
      setInWatchlist(wasInWatchlist)
      console.error('Failed to toggle watchlist:', err)
    } finally {
      setIsToggling(false)
    }
  }

  return (
    <button
      onClick={handleToggle}
      disabled={isToggling}
      className={`px-2 py-1 text-sm rounded transition-colors ${
        inWatchlist
          ? 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200'
          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
      } disabled:opacity-50`}
      title={inWatchlist ? 'Remove from watchlist' : 'Add to watchlist'}
    >
      {inWatchlist ? '⭐' : '☆'}
    </button>
  )
}
