'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function StrategyPerformancePanel({ getToken }) {
  const [strategies, setStrategies] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchStrategyPerformance()
  }, [])

  const fetchStrategyPerformance = async () => {
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
      
      const response = await axios.get(
        `${API_BASE}/api/strategies/performance`,
        authConfig
      )
      
      setStrategies(response.data.strategies || [])
    } catch (err) {
      console.error('Failed to fetch strategy performance:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to fetch strategy performance')
    } finally {
      setLoading(false)
    }
  }

  const formatMetric = (value, suffix = '') => {
    if (value === null || value === undefined) return 'N/A'
    if (typeof value === 'number') {
      return `${value.toFixed(2)}${suffix}`
    }
    return value
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Strategy Performance</h3>
        <div className="text-center py-8 text-gray-500">Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Strategy Performance</h3>
        <div className="text-center py-8 text-red-500">{error}</div>
      </div>
    )
  }

  if (strategies.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Strategy Performance</h3>
        <div className="text-center py-8 text-gray-500">
          <p>No strategy performance data available yet.</p>
          <p className="text-sm mt-2">Performance metrics will appear after outcomes are recorded for strategies.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Strategy Performance</h3>
        <button
          onClick={fetchStrategyPerformance}
          className="text-sm text-blue-600 hover:text-blue-800"
        >
          Refresh
        </button>
      </div>
      
      <div className="space-y-4">
        {strategies.map((strategy) => (
          <div key={strategy.strategy_id} className="p-4 bg-gray-50 rounded-lg">
            <div className="flex justify-between items-center mb-2">
              <h4 className="text-sm font-semibold text-gray-900">{strategy.strategy_name}</h4>
              <span className="text-xs text-gray-500">{strategy.total_trades} trades</span>
            </div>
            {strategy.strategy_description && (
              <p className="text-xs text-gray-600 mb-3">{strategy.strategy_description}</p>
            )}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
              <div>
                <span className="text-gray-500">Success Rate:</span>
                <span className="ml-1 font-semibold">{formatMetric(strategy.success_rate, '%')}</span>
              </div>
              <div>
                <span className="text-gray-500">Expected ROI:</span>
                <span className="ml-1 font-semibold text-blue-600">{formatMetric(strategy.avg_expected_roi, '%')}</span>
              </div>
              <div>
                <span className="text-gray-500">Actual ROI:</span>
                <span className={`ml-1 font-semibold ${
                  strategy.avg_actual_roi >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {formatMetric(strategy.avg_actual_roi, '%')}
                </span>
              </div>
              <div>
                <span className="text-gray-500">Calibration Error:</span>
                <span className={`ml-1 font-semibold ${
                  strategy.calibration_error < 5 ? 'text-green-600' : strategy.calibration_error < 10 ? 'text-yellow-600' : 'text-red-600'
                }`}>
                  {formatMetric(strategy.calibration_error, '%')}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
