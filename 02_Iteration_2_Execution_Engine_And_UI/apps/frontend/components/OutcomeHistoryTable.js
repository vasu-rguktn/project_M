'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function OutcomeHistoryTable({ getToken }) {
  const [outcomes, setOutcomes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [realizing, setRealizing] = useState(false)

  useEffect(() => {
    fetchOutcomes()
  }, [])

  const fetchOutcomes = async () => {
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
      
      // Try realized outcomes first (Phase 17), fallback to execution outcomes (Phase 12)
      let outcomes = []
      
      // Attempt to fetch realized outcomes
      try {
        const realizedResponse = await axios.get(
          `${API_BASE}/api/outcomes/realized`,
          authConfig
        )
        outcomes = realizedResponse.data.outcomes || []
      } catch (err) {
        // Fallback to execution outcomes if realized endpoint doesn't exist
        console.log('Realized outcomes not available, trying execution outcomes...')
        
        const response = await axios.get(
          `${API_BASE}/api/outcomes`,
          authConfig
        )
        outcomes = response.data.outcomes || []
      }
      
      setOutcomes(outcomes)
    } catch (err) {
      console.error('Failed to fetch outcomes:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to fetch outcomes')
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'SUCCESS':
        return 'bg-green-100 text-green-800'
      case 'NEUTRAL':
        return 'bg-gray-100 text-gray-800'
      case 'NEGATIVE':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const formatROI = (roi) => {
    if (roi === null || roi === undefined) return 'N/A'
    return `${roi >= 0 ? '+' : ''}${roi.toFixed(2)}%`
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
        // Refresh outcomes after realization
        setTimeout(() => {
          fetchOutcomes()
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

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Outcome History</h3>
        <div className="text-center py-8 text-gray-500">Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Outcome History</h3>
        <div className="text-center py-8 text-red-500">{error}</div>
      </div>
    )
  }

  if (outcomes.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Outcome History</h3>
          <button
            onClick={handleRealizeOutcomes}
            disabled={realizing || !getToken}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {realizing ? 'Realizing...' : 'Realize Outcomes'}
          </button>
        </div>
        <div className="text-center py-8 text-gray-500">
          <p>No outcomes recorded yet.</p>
          <p className="text-sm mt-2">Click "Realize Outcomes" to generate outcomes from executed simulations.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Outcome History</h3>
        <div className="flex gap-2">
          <button
            onClick={handleRealizeOutcomes}
            disabled={realizing || !getToken}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {realizing ? 'Realizing...' : 'Realize Outcomes'}
          </button>
          <button
            onClick={fetchOutcomes}
            className="px-4 py-2 text-sm font-medium text-blue-600 hover:text-blue-800 border border-blue-600 rounded-md"
          >
            Refresh
          </button>
        </div>
      </div>
      
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Asset
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Expected ROI
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actual ROI
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Delta
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Recorded
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {outcomes.map((outcome) => (
              <tr key={outcome.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                  {outcome.asset_name || outcome.asset_id}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                  {formatROI(outcome.expected_roi)}
                </td>
                <td className={`px-4 py-3 whitespace-nowrap text-sm font-semibold ${
                  outcome.actual_roi >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {formatROI(outcome.actual_roi)}
                </td>
                <td className={`px-4 py-3 whitespace-nowrap text-sm font-semibold ${
                  outcome.roi_delta >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {formatROI(outcome.roi_delta)}
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(outcome.outcome_status)}`}>
                    {outcome.outcome_status}
                  </span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                  {new Date(outcome.recorded_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
