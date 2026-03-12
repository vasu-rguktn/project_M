'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function CounterfactualPanel({ simulationId, getToken }) {
  const [counterfactual, setCounterfactual] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (simulationId) {
      fetchCounterfactual()
    }
  }, [simulationId])

  const fetchCounterfactual = async () => {
    if (!getToken || !simulationId) return
    
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
        `${API_BASE}/api/counterfactual/${simulationId}`,
        authConfig
      )
      
      setCounterfactual(response.data)
    } catch (err) {
      // 404 is expected when counterfactual hasn't been computed yet - don't log as error
      if (err.response?.status === 404) {
        setError(null) // Clear error, show empty state message instead
        setCounterfactual(null)
      } else {
        console.error('Failed to fetch counterfactual:', err)
        setError(err.response?.data?.detail || err.message || 'Failed to fetch counterfactual outcome')
      }
    } finally {
      setLoading(false)
    }
  }

  if (!simulationId) {
    return (
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Counterfactual Analysis</h3>
        <div className="text-center py-8 text-gray-500">
          <p>No simulation ID provided</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Counterfactual Analysis</h3>
        <div className="text-center py-8 text-gray-500">Loading counterfactual analysis...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Counterfactual Analysis</h3>
        <div className="text-center py-8 text-gray-500">{error}</div>
        <button
          onClick={fetchCounterfactual}
          className="mt-4 px-4 py-2 text-sm text-blue-600 hover:text-blue-800"
        >
          Retry
        </button>
      </div>
    )
  }

  if (!counterfactual) {
    return (
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Counterfactual Analysis</h3>
        <div className="text-center py-8 text-gray-500">
          <p>No counterfactual analysis available yet.</p>
          <p className="text-sm mt-2">Counterfactual will be computed after outcome is realized.</p>
        </div>
      </div>
    )
  }

  const formatValue = (value) => {
    if (value === null || value === undefined) return 'N/A'
    if (typeof value === 'number') {
      return value.toFixed(2)
    }
    return value
  }

  const formatPercent = (value) => {
    if (value === null || value === undefined) return 'N/A'
    if (typeof value === 'number') {
      return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
    }
    return value
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Counterfactual Analysis</h3>
        <button
          onClick={fetchCounterfactual}
          className="text-sm text-blue-600 hover:text-blue-800"
        >
          Refresh
        </button>
      </div>

      <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-blue-800">
          <strong>What is Counterfactual Analysis?</strong> This compares what actually happened 
          with what would have happened if no action was taken. It helps evaluate the true impact 
          of your decision.
        </p>
      </div>

      {/* Comparison Table */}
      <div className="overflow-x-auto mb-6">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Metric</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">No Action (Baseline)</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actual Outcome</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Delta (Difference)</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {/* ROI Comparison */}
            <tr>
              <td className="px-4 py-3 text-sm font-medium text-gray-900">Expected ROI</td>
              <td className="px-4 py-3 text-sm text-gray-900">
                {formatPercent(counterfactual.no_action_roi)}%
              </td>
              <td className="px-4 py-3 text-sm text-gray-900">
                {formatPercent(counterfactual.actual_roi)}%
              </td>
              <td className="px-4 py-3 text-sm">
                <span className={`font-semibold ${
                  counterfactual.roi_delta > 0 ? 'text-green-600' : 
                  counterfactual.roi_delta < 0 ? 'text-red-600' : 'text-gray-600'
                }`}>
                  {formatPercent(counterfactual.roi_delta)}
                </span>
              </td>
            </tr>
            
            {/* Risk Comparison */}
            <tr>
              <td className="px-4 py-3 text-sm font-medium text-gray-900">Risk Score</td>
              <td className="px-4 py-3 text-sm text-gray-900">
                {formatPercent(counterfactual.no_action_risk_score)}%
              </td>
              <td className="px-4 py-3 text-sm text-gray-900">
                {formatPercent(counterfactual.actual_risk_score)}%
              </td>
              <td className="px-4 py-3 text-sm">
                <span className={`font-semibold ${
                  counterfactual.risk_delta < 0 ? 'text-green-600' : 
                  counterfactual.risk_delta > 0 ? 'text-red-600' : 'text-gray-600'
                }`}>
                  {formatPercent(counterfactual.risk_delta)}
                </span>
                <span className="text-xs text-gray-500 ml-1">
                  ({counterfactual.risk_delta < 0 ? 'Lower risk' : counterfactual.risk_delta > 0 ? 'Higher risk' : 'Same risk'})
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Opportunity Cost */}
      {counterfactual.opportunity_cost !== null && counterfactual.opportunity_cost !== undefined && (
        <div className={`p-4 rounded-lg border-2 ${
          counterfactual.opportunity_cost > 0
            ? 'bg-red-50 border-red-200'
            : 'bg-green-50 border-green-200'
        }`}>
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-1">Opportunity Cost</h4>
              <p className="text-xs text-gray-600">
                {counterfactual.opportunity_cost > 0
                  ? 'Potential loss from not taking action'
                  : 'No opportunity cost (action was beneficial)'}
              </p>
            </div>
            <div className={`text-lg font-bold ${
              counterfactual.opportunity_cost > 0 ? 'text-red-600' : 'text-green-600'
            }`}>
              {counterfactual.opportunity_cost > 0 ? '+' : ''}{formatValue(counterfactual.opportunity_cost)}%
            </div>
          </div>
        </div>
      )}

      {/* Summary */}
      <div className="mt-4 p-4 bg-gray-50 rounded-lg">
        <h4 className="text-sm font-semibold text-gray-900 mb-2">Analysis Summary</h4>
        <div className="text-sm text-gray-700 space-y-1">
          {counterfactual.roi_delta > 0 && (
            <p>
              ✓ <strong>Positive Impact:</strong> Taking action resulted in {formatPercent(counterfactual.roi_delta)} 
              higher ROI compared to no action.
            </p>
          )}
          {counterfactual.roi_delta < 0 && (
            <p>
              ⚠ <strong>Negative Impact:</strong> Taking action resulted in {formatPercent(Math.abs(counterfactual.roi_delta))} 
              lower ROI compared to no action.
            </p>
          )}
          {counterfactual.roi_delta === 0 && (
            <p>
              ➡ <strong>Neutral Impact:</strong> Taking action had no significant impact on ROI.
            </p>
          )}
          {counterfactual.risk_delta !== null && counterfactual.risk_delta !== undefined && (
            <p className="mt-2">
              {counterfactual.risk_delta < 0 
                ? '✓ Risk was reduced by taking action.'
                : counterfactual.risk_delta > 0
                ? '⚠ Risk increased by taking action.'
                : '➡ Risk remained unchanged.'}
            </p>
          )}
        </div>
      </div>

      {counterfactual.computed_at && (
        <div className="mt-4 text-xs text-gray-500">
          Computed: {new Date(counterfactual.computed_at).toLocaleString()}
        </div>
      )}
    </div>
  )
}
