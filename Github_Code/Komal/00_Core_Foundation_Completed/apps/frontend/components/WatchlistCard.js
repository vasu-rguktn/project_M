import { useState } from 'react'
import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function WatchlistCard({ watchlist, onRemove, getToken }) {
  const [removing, setRemoving] = useState({})

  const handleRemove = async (assetId) => {
    if (removing[assetId] || !getToken) return
    
    setRemoving({ ...removing, [assetId]: true })
    
    try {
      const token = await getToken()
      
      if (!token || !token.trim()) {
        throw new Error('No authentication token available')
      }
      
      const authConfig = {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
      
      await axios.delete(`${API_BASE}/api/watchlist/remove`, {
        ...authConfig,
        data: { asset_id: assetId }
      })
      
      onRemove(assetId)
    } catch (err) {
      if (err.response?.status === 401) {
        console.warn('Authentication failed when removing from watchlist')
        alert('Authentication failed. Please refresh the page and try again.')
      } else {
        console.error('Failed to remove from watchlist:', err)
        alert('Failed to remove from watchlist. Please try again.')
      }
    } finally {
      setRemoving({ ...removing, [assetId]: false })
    }
  }

  if (!watchlist || watchlist.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-100">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">My Watchlist</h3>
        <div className="text-center py-8 text-gray-500">
          <p>Your watchlist is empty.</p>
          <p className="text-sm mt-2">Add assets from arbitrage opportunities or your holdings to track them.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-100">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">My Watchlist ({watchlist.length})</h3>
      <div className="space-y-3">
        {watchlist.map((item) => (
          <div
            key={item.watchlist_id}
            className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h4 className="font-medium text-gray-900">{item.asset_name}</h4>
                {item.vintage && (
                  <span className="text-sm text-gray-500">({item.vintage})</span>
                )}
              </div>
              <div className="flex items-center gap-4 mt-1 text-sm text-gray-600">
                <span>{item.region}</span>
                <span className="font-medium text-gray-900">
                  ₹{item.current_price?.toFixed(2) || item.base_price?.toFixed(2) || '0.00'}
                </span>
                <span className={`px-2 py-1 rounded text-xs ${
                  item.trend === 'up' ? 'bg-green-100 text-green-800' :
                  item.trend === 'down' ? 'bg-red-100 text-red-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {item.trend || 'stable'}
                </span>
              </div>
            </div>
            <button
              onClick={() => handleRemove(item.asset_id)}
              disabled={removing[item.asset_id]}
              className="ml-4 px-3 py-1.5 text-sm text-red-600 hover:text-red-700 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
            >
              {removing[item.asset_id] ? 'Removing...' : 'Remove'}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

