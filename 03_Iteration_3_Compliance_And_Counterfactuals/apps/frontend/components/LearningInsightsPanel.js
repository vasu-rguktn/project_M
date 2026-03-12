'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function LearningInsightsPanel({ getToken }) {
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchMetrics()
  }, [])

  const fetchMetrics = async () => {
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
        `${API_BASE}/api/learning/metrics`,
        authConfig
      )
      
      setMetrics(response.data)
    } catch (err) {
      console.error('Failed to fetch learning metrics:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to fetch metrics')
    } finally {
      setLoading(false)
    }
  }

  const formatMetric = (value, suffix = '') => {
    if (value === null || value === undefined) return 'N/A'
    if (typeof value === 'number') {
      return `${value.toFixed(3)}${suffix}`
    }
    return value
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Learning Insights</h3>
        <div className="text-center py-8 text-gray-500">Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Learning Insights</h3>
        <div className="text-center py-8 text-red-500">{error}</div>
      </div>
    )
  }

  if (!metrics || (metrics.strategy_performance?.length === 0 && metrics.confidence_calibration?.length === 0)) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Learning Insights</h3>
        <div className="text-center py-8 text-gray-500">
          <p>No learning data available yet.</p>
          <p className="text-sm mt-2">Learning insights will appear after outcomes are recorded and analyzed.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Learning Insights</h3>
        <button
          onClick={fetchMetrics}
          className="text-sm text-blue-600 hover:text-blue-800"
        >
          Refresh
        </button>
      </div>

      <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
        <p className="text-xs text-blue-800">
          <strong>Note:</strong> These metrics are observational only. They do not modify AI behavior or decision logic.
        </p>
      </div>

      {metrics.overall_calibration_error !== null && (
        <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="text-sm font-semibold text-yellow-900 mb-1">Overall Calibration Error</div>
          <div className="text-lg text-yellow-800">{formatMetric(metrics.overall_calibration_error)}</div>
          <div className="text-xs text-yellow-600 mt-1">Lower is better (0 = perfect calibration)</div>
        </div>
      )}

      {metrics.confidence_calibration && metrics.confidence_calibration.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-gray-900 mb-2">Confidence Calibration</h4>
          <div className="space-y-2">
            {metrics.confidence_calibration.map((cal, idx) => (
              <div key={idx} className="p-3 bg-gray-50 rounded">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm font-medium text-gray-700">{cal.model_component}</span>
                  <span className="text-xs text-gray-500">{cal.sample_size} samples</span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div>
                    <span className="text-gray-500">Predicted:</span>
                    <span className="ml-1 font-semibold">{formatMetric(cal.predicted_confidence)}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Observed:</span>
                    <span className="ml-1 font-semibold">{formatMetric(cal.observed_success_rate)}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Delta:</span>
                    <span className={`ml-1 font-semibold ${
                      cal.calibration_delta < 0.1 ? 'text-green-600' : cal.calibration_delta < 0.2 ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      {formatMetric(cal.calibration_delta)}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {metrics.strategy_performance && metrics.strategy_performance.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-900 mb-2">Strategy Performance</h4>
          <div className="space-y-2">
            {metrics.strategy_performance.map((strategy, idx) => (
              <div key={idx} className="p-3 bg-gray-50 rounded">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm font-medium text-gray-700">{strategy.strategy_name || strategy.region}</span>
                  <span className="text-xs text-gray-500">{strategy.sample_size} outcomes</span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div>
                    <span className="text-gray-500">Expected ROI:</span>
                    <span className="ml-1 font-semibold">{formatMetric(strategy.avg_expected_roi, '%')}</span>
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
                    <span className="text-gray-500">Error:</span>
                    <span className={`ml-1 font-semibold ${
                      strategy.confidence_error < 5 ? 'text-green-600' : strategy.confidence_error < 10 ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      {formatMetric(strategy.confidence_error, '%')}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
