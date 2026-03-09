'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function PerformanceMetricsPanel({ getToken }) {
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [realizing, setRealizing] = useState(false)

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
        `${API_BASE}/api/outcomes/metrics`,
        authConfig
      )
      
      setMetrics(response.data)
    } catch (err) {
      console.error('Failed to fetch performance metrics:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to fetch metrics')
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
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance Metrics</h3>
        <div className="text-center py-8 text-gray-500">Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance Metrics</h3>
        <div className="text-center py-8 text-red-500">{error}</div>
      </div>
    )
  }

  const handleRealizeOutcomes = async () => {
    if (!getToken || realizing) return
    
    setRealizing(true)
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
      
      const response = await axios.post(
        `${API_BASE}/api/outcomes/realize?min_holding_period_days=0`,
        {},
        authConfig
      )
      
      console.log('Outcome realization result:', response.data)
      
      if (response.data.realized > 0) {
        // Refresh metrics after realization
        setTimeout(() => {
          fetchMetrics()
        }, 1000)
      } else {
        alert(`No outcomes realized. Processed: ${response.data.processed}, Skipped: ${response.data.skipped}, Errors: ${response.data.errors}`)
      }
    } catch (err) {
      console.error('Failed to realize outcomes:', err)
      alert(`Failed to realize outcomes: ${err.response?.data?.detail || err.message}`)
    } finally {
      setRealizing(false)
    }
  }

  if (!metrics || metrics.total_outcomes === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Performance Metrics</h3>
          <button
            onClick={handleRealizeOutcomes}
            disabled={realizing || !getToken}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {realizing ? 'Realizing...' : 'Realize Outcomes'}
          </button>
        </div>
        <div className="text-center py-8 text-gray-500">
          <p>No metrics available yet.</p>
          <p className="text-sm mt-2">Click "Realize Outcomes" to generate outcomes from executed simulations.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Performance Metrics</h3>
        <button
          onClick={fetchMetrics}
          className="text-sm text-blue-600 hover:text-blue-800"
        >
          Refresh
        </button>
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-gray-50 p-4 rounded-lg">
          <div className="text-xs text-gray-500 mb-1">Total Simulations</div>
          <div className="text-2xl font-bold text-gray-900">{metrics.total_simulations}</div>
        </div>
        <div className="bg-gray-50 p-4 rounded-lg">
          <div className="text-xs text-gray-500 mb-1">Total Outcomes</div>
          <div className="text-2xl font-bold text-gray-900">{metrics.total_outcomes}</div>
        </div>
        <div className="bg-gray-50 p-4 rounded-lg">
          <div className="text-xs text-gray-500 mb-1">Success Rate</div>
          <div className="text-2xl font-bold text-green-600">{formatMetric(metrics.success_rate, '%')}</div>
        </div>
        <div className="bg-gray-50 p-4 rounded-lg">
          <div className="text-xs text-gray-500 mb-1">Avg Expected ROI</div>
          <div className="text-2xl font-bold text-blue-600">{formatMetric(metrics.average_expected_roi, '%')}</div>
        </div>
        <div className="bg-gray-50 p-4 rounded-lg">
          <div className="text-xs text-gray-500 mb-1">Avg Actual ROI</div>
          <div className={`text-2xl font-bold ${
            metrics.average_actual_roi >= 0 ? 'text-green-600' : 'text-red-600'
          }`}>
            {formatMetric(metrics.average_actual_roi, '%')}
          </div>
        </div>
        <div className="bg-gray-50 p-4 rounded-lg">
          <div className="text-xs text-gray-500 mb-1">Avg ROI Delta</div>
          <div className={`text-2xl font-bold ${
            metrics.average_roi_delta >= 0 ? 'text-green-600' : 'text-red-600'
          }`}>
            {formatMetric(metrics.average_roi_delta, '%')}
          </div>
        </div>
      </div>

      {metrics.confidence_calibration_error !== null && (
        <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="text-sm font-semibold text-yellow-900 mb-1">Confidence Calibration Error</div>
          <div className="text-lg text-yellow-800">{formatMetric(metrics.confidence_calibration_error)}</div>
          <div className="text-xs text-yellow-600 mt-1">Lower is better (0 = perfect calibration)</div>
        </div>
      )}

      {metrics.risk_underestimation_rate !== null && (
        <div className="mb-4 p-4 bg-orange-50 border border-orange-200 rounded-lg">
          <div className="text-sm font-semibold text-orange-900 mb-1">Risk Underestimation Rate</div>
          <div className="text-lg text-orange-800">{formatMetric(metrics.risk_underestimation_rate, '%')}</div>
          <div className="text-xs text-orange-600 mt-1">Percentage of negative outcomes with low risk scores</div>
        </div>
      )}

      {Object.keys(metrics.region_drift_metrics || {}).length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-gray-900 mb-2">Region-Level Drift</h4>
          <div className="space-y-2">
            {Object.entries(metrics.region_drift_metrics).map(([region, data]) => (
              <div key={region} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                <span className="text-sm font-medium text-gray-700">{region}</span>
                <span className={`text-sm font-semibold ${
                  data.average_drift >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {formatMetric(data.average_drift, '%')} ({data.outcome_count} outcomes)
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {Object.keys(metrics.outcome_distribution || {}).length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-900 mb-2">Outcome Distribution</h4>
          <div className="flex gap-4">
            {Object.entries(metrics.outcome_distribution).map(([status, count]) => (
              <div key={status} className="flex-1 p-3 bg-gray-50 rounded text-center">
                <div className="text-xs text-gray-500 mb-1">{status}</div>
                <div className="text-xl font-bold text-gray-900">{count}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
