'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function CapitalSummaryPanel({ getToken }) {
  const [capital, setCapital] = useState(null)
  const [exposure, setExposure] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchCapitalData()
  }, [])

  const fetchCapitalData = async () => {
    if (!getToken) return
    
    setLoading(true)
    setError(null)
    
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
      
      const [capitalRes, exposureRes] = await Promise.all([
        axios.get(`${API_BASE}/api/portfolio/capital`, authConfig),
        axios.get(`${API_BASE}/api/portfolio/exposure`, authConfig)
      ])
      
      setCapital(capitalRes.data)
      setExposure(exposureRes.data)
    } catch (err) {
      console.error('Failed to fetch capital data:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to fetch capital data')
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value) => {
    if (value === null || value === undefined) return 'N/A'
    return `₹${value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }

  const formatPercent = (value) => {
    if (value === null || value === undefined) return 'N/A'
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Portfolio Capital</h3>
        <div className="text-center py-8 text-gray-500">Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Portfolio Capital</h3>
        <div className="text-center py-8 text-red-500">{error}</div>
      </div>
    )
  }

  if (!capital) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Portfolio Capital</h3>
        <div className="text-center py-8 text-gray-500">No capital data available</div>
      </div>
    )
  }

  const availablePercent = capital.total_capital > 0 
    ? (capital.available_capital / capital.total_capital) * 100 
    : 0

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Portfolio Capital</h3>
        <button
          onClick={fetchCapitalData}
          className="text-sm text-blue-600 hover:text-blue-800"
        >
          Refresh
        </button>
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-blue-50 p-4 rounded-lg">
          <div className="text-xs text-gray-500 mb-1">Total Capital</div>
          <div className="text-2xl font-bold text-blue-900">{formatCurrency(capital.total_capital)}</div>
        </div>
        <div className="bg-green-50 p-4 rounded-lg">
          <div className="text-xs text-gray-500 mb-1">Available</div>
          <div className="text-2xl font-bold text-green-700">{formatCurrency(capital.available_capital)}</div>
          <div className="text-xs text-gray-500 mt-1">{availablePercent.toFixed(1)}% available</div>
        </div>
        <div className="bg-yellow-50 p-4 rounded-lg">
          <div className="text-xs text-gray-500 mb-1">Locked</div>
          <div className="text-2xl font-bold text-yellow-700">{formatCurrency(capital.locked_capital)}</div>
        </div>
        <div className={`p-4 rounded-lg ${capital.realized_pnl >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
          <div className="text-xs text-gray-500 mb-1">Realized P&L</div>
          <div className={`text-2xl font-bold ${capital.realized_pnl >= 0 ? 'text-green-700' : 'text-red-700'}`}>
            {formatCurrency(capital.realized_pnl)}
          </div>
        </div>
        <div className={`p-4 rounded-lg ${capital.unrealized_pnl >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
          <div className="text-xs text-gray-500 mb-1">Unrealized P&L</div>
          <div className={`text-2xl font-bold ${capital.unrealized_pnl >= 0 ? 'text-green-700' : 'text-red-700'}`}>
            {formatCurrency(capital.unrealized_pnl)}
          </div>
        </div>
        <div className="bg-gray-50 p-4 rounded-lg">
          <div className="text-xs text-gray-500 mb-1">Total Exposure</div>
          <div className="text-2xl font-bold text-gray-900">
            {exposure ? formatCurrency(exposure.total_exposure) : 'N/A'}
          </div>
        </div>
      </div>

      {exposure && (
        <div className="space-y-4">
          {Object.keys(exposure.by_region || {}).length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-2">Exposure by Region</h4>
              <div className="space-y-2">
                {Object.entries(exposure.by_region).map(([region, value]) => (
                  <div key={region} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                    <span className="text-sm font-medium text-gray-700">{region}</span>
                    <span className="text-sm font-semibold text-gray-900">{formatCurrency(value)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
