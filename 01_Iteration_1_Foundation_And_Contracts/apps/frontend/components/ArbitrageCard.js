'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function ArbitrageCard({ opportunity, onWatchlistToggle, getToken, isInWatchlist = false }) {
  return (
    <div className="bg-gradient-to-br from-blue-50 to-indigo-50 p-5 rounded-lg shadow-sm hover:shadow-md transition-all border border-blue-100">
      <div className="flex justify-between items-start mb-3">
        <div className="flex-1">
          <h4 className="font-semibold text-gray-900 mb-1">{opportunity.asset_name}</h4>
          <p className="text-sm text-gray-600">{opportunity.vintage}</p>
        </div>
        <div className="flex items-center gap-2">
          {getToken && (
            <WatchlistButton 
              assetId={opportunity.asset_id}
              isInWatchlist={isInWatchlist}
              onToggle={onWatchlistToggle}
              getToken={getToken}
            />
          )}
          <div className="bg-blue-100 text-blue-800 text-xs font-semibold px-2 py-1 rounded">
            {Math.round(opportunity.confidence * 100)}% conf
          </div>
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-3 mb-3 text-sm">
        <div>
          <div className="text-gray-500 text-xs">Buy</div>
          <div className="font-medium">{opportunity.buy_region}</div>
          <div className="text-gray-700">₹{opportunity.buy_price.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-gray-500 text-xs">Sell</div>
          <div className="font-medium">{opportunity.sell_region}</div>
          <div className="text-gray-700">₹{opportunity.sell_price.toFixed(2)}</div>
        </div>
      </div>
      
      <div className="flex justify-between items-center pt-3 border-t border-blue-200">
        <div>
          <div className="text-xs text-gray-500">Expected Profit</div>
          <div className="text-lg font-bold text-green-600">
            ₹{opportunity.expected_profit.toFixed(2)}
          </div>
        </div>
        <div className="text-xs text-gray-500">
          {opportunity.volume_available} available
        </div>
      </div>
      
      {getToken && (
        <div className="mt-3 pt-3 border-t border-blue-200">
          <SimulateBuyButton 
            opportunity={opportunity}
            getToken={getToken}
            onBuySuccess={opportunity.onBuySuccess}
          />
        </div>
      )}
    </div>
  )
}

function SimulateBuyButton({ opportunity, getToken, onBuySuccess }) {
  const [isBuying, setIsBuying] = useState(false)
  const [showBuyModal, setShowBuyModal] = useState(false)
  const [quantity, setQuantity] = useState('1')

  const handleBuy = async () => {
    if (isBuying) return
    
    const qty = parseInt(quantity)
    if (!qty || qty <= 0 || qty > opportunity.volume_available) {
      alert(`Please enter a quantity between 1 and ${opportunity.volume_available}`)
      return
    }
    
    setIsBuying(true)
    try {
      const token = await getToken()
      const authConfig = {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
      
      await axios.post(`${API_BASE}/api/holdings/buy`, {
        asset_id: opportunity.asset_id,
        quantity: qty,
        buy_price: opportunity.buy_price,
        source: 'ARBITRAGE_SIMULATION'
      }, authConfig)
      
      if (onBuySuccess) {
        await onBuySuccess()
      }
      setShowBuyModal(false)
      setQuantity('1')
      alert(`Successfully simulated buy of ${qty} unit(s) of ${opportunity.asset_name}`)
    } catch (err) {
      console.error('Failed to buy holding:', err)
      alert(err.response?.data?.detail || 'Failed to simulate buy. Please try again.')
    } finally {
      setIsBuying(false)
    }
  }

  return (
    <>
      <button
        onClick={() => setShowBuyModal(true)}
        className="w-full px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors text-sm font-medium"
      >
        Simulate Buy
      </button>
      
      {showBuyModal && (
        <div className="fixed inset-0 backdrop-blur-[2px] bg-black/20 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold text-gray-900">Simulate Buy</h2>
                <button
                  onClick={() => {
                    setShowBuyModal(false)
                    setQuantity('1')
                  }}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {opportunity.asset_name} ({opportunity.vintage})
                </h3>
                <p className="text-sm text-gray-600 mb-4">
                  Buy at ₹{opportunity.buy_price.toFixed(2)} from {opportunity.buy_region}
                </p>
                <p className="text-xs text-gray-500 mb-4">
                  Available: {opportunity.volume_available} units
                </p>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Quantity
                </label>
                <input
                  type="number"
                  min="1"
                  max={opportunity.volume_available}
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 text-gray-900"
                />
              </div>

              <div className="flex justify-end gap-3">
                <button
                  onClick={() => {
                    setShowBuyModal(false)
                    setQuantity('1')
                  }}
                  className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                  disabled={isBuying}
                >
                  Cancel
                </button>
                <button
                  onClick={handleBuy}
                  disabled={isBuying}
                  className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
                >
                  {isBuying ? 'Buying...' : 'Buy'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

function WatchlistButton({ assetId, isInWatchlist, onToggle, getToken }) {
  const [isToggling, setIsToggling] = useState(false)
  const [inWatchlist, setInWatchlist] = useState(isInWatchlist)

  // Update local state when prop changes - this ensures star updates when watchlist changes
  useEffect(() => {
    setInWatchlist(isInWatchlist)
  }, [isInWatchlist])

  const handleToggle = async (e) => {
    e.stopPropagation()
    if (isToggling) return
    
    setIsToggling(true)
    const wasInWatchlist = inWatchlist
    
    // Optimistic update
    setInWatchlist(!wasInWatchlist)
    
    try {
      // Call the parent's toggle handler which handles API call and refresh
      if (onToggle) {
        await onToggle(assetId)
      }
    } catch (err) {
      // Revert on error
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
      className={`px-2 py-1 text-lg rounded transition-colors ${
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

