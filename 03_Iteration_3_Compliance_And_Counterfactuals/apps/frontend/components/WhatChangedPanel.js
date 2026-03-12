'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function WhatChangedPanel({ proposalId, getToken }) {
  const [diff, setDiff] = useState(null)
  const [narrative, setNarrative] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (proposalId) {
      fetchWhatChanged()
    }
  }, [proposalId])

  const fetchWhatChanged = async () => {
    if (!getToken || !proposalId) return
    
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
      
      const [diffRes, narrativeRes] = await Promise.all([
        axios.get(`${API_BASE}/api/explainability/proposal-diff/${proposalId}`, authConfig).catch(() => ({ data: { has_previous: false } })),
        axios.get(`${API_BASE}/api/explainability/narrative/${proposalId}`, authConfig).catch(() => ({ data: { narrative: null } }))
      ])
      
      setDiff(diffRes.data)
      setNarrative(narrativeRes.data?.narrative || null)
    } catch (err) {
      console.error('Failed to fetch what changed:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to fetch changes')
    } finally {
      setLoading(false)
    }
  }

  if (!proposalId) {
    return null
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">What Changed Since Last Run</h3>
        <div className="text-center py-8 text-gray-500">Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">What Changed Since Last Run</h3>
        <div className="text-center py-8 text-red-500">{error}</div>
      </div>
    )
  }

  if (!diff || !diff.has_previous) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">What Changed Since Last Run</h3>
        <div className="text-center py-8 text-gray-500">
          <p>This is the first analysis for this asset</p>
          <p className="text-sm mt-2">No previous data to compare</p>
        </div>
        {narrative && (
          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="text-sm font-semibold text-blue-900 mb-2">Current Analysis Summary</div>
            <div className="text-sm text-blue-800">{narrative}</div>
          </div>
        )}
      </div>
    )
  }

  const changes = diff.changes || {}
  const current = diff.current_proposal || {}
  const previous = diff.previous_proposal || {}

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">What Changed Since Last Run</h3>
        <button
          onClick={fetchWhatChanged}
          className="text-sm text-blue-600 hover:text-blue-800"
        >
          Refresh
        </button>
      </div>

      {/* Summary */}
      {changes.summary && (
        <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="text-sm font-semibold text-yellow-900 mb-1">Summary of Changes</div>
          <div className="text-sm text-yellow-800">{changes.summary}</div>
        </div>
      )}

      {/* Comparison Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Metric</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Previous</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Current</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Change</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {/* Recommendation */}
            <tr>
              <td className="px-4 py-3 text-sm font-medium text-gray-900">Recommendation</td>
              <td className="px-4 py-3 text-sm text-gray-900">{previous.recommendation || 'N/A'}</td>
              <td className="px-4 py-3 text-sm text-gray-900">{current.recommendation || 'N/A'}</td>
              <td className="px-4 py-3 text-sm">
                {changes.recommendation_changed ? (
                  <span className="px-2 py-1 text-xs font-semibold rounded bg-yellow-100 text-yellow-800">CHANGED</span>
                ) : (
                  <span className="text-gray-500">No change</span>
                )}
              </td>
            </tr>
            
            {/* Confidence */}
            <tr>
              <td className="px-4 py-3 text-sm font-medium text-gray-900">Confidence</td>
              <td className="px-4 py-3 text-sm text-gray-900">
                {previous.confidence_score !== null && previous.confidence_score !== undefined
                  ? `${(previous.confidence_score * 100).toFixed(1)}%`
                  : 'N/A'}
              </td>
              <td className="px-4 py-3 text-sm text-gray-900">
                {current.confidence_score !== null && current.confidence_score !== undefined
                  ? `${(current.confidence_score * 100).toFixed(1)}%`
                  : 'N/A'}
              </td>
              <td className="px-4 py-3 text-sm">
                {changes.confidence_delta !== null && changes.confidence_delta !== undefined && changes.confidence_delta !== 0 ? (
                  <span className={`font-semibold ${changes.confidence_delta > 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {changes.confidence_delta > 0 ? '+' : ''}{(changes.confidence_delta * 100).toFixed(1)}%
                  </span>
                ) : (
                  <span className="text-gray-500">No change</span>
                )}
              </td>
            </tr>
            
            {/* Risk Score */}
            <tr>
              <td className="px-4 py-3 text-sm font-medium text-gray-900">Risk Score</td>
              <td className="px-4 py-3 text-sm text-gray-900">
                {previous.risk_score !== null && previous.risk_score !== undefined && previous.risk_score !== 'Not Available'
                  ? `${(previous.risk_score * 100).toFixed(1)}%`
                  : 'N/A'}
              </td>
              <td className="px-4 py-3 text-sm text-gray-900">
                {current.risk_score !== null && current.risk_score !== undefined && current.risk_score !== 'Not Available'
                  ? `${(current.risk_score * 100).toFixed(1)}%`
                  : 'N/A'}
              </td>
              <td className="px-4 py-3 text-sm">
                {changes.risk_delta !== null && changes.risk_delta !== undefined && changes.risk_delta !== 0 ? (
                  <span className={`font-semibold ${changes.risk_delta < 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {changes.risk_delta > 0 ? '+' : ''}{(changes.risk_delta * 100).toFixed(1)}%
                  </span>
                ) : (
                  <span className="text-gray-500">No change</span>
                )}
              </td>
            </tr>
            
            {/* Expected ROI */}
            <tr>
              <td className="px-4 py-3 text-sm font-medium text-gray-900">Expected ROI</td>
              <td className="px-4 py-3 text-sm text-gray-900">
                {previous.expected_roi !== null && previous.expected_roi !== undefined
                  ? `${previous.expected_roi.toFixed(2)}%`
                  : 'N/A'}
              </td>
              <td className="px-4 py-3 text-sm text-gray-900">
                {current.expected_roi !== null && current.expected_roi !== undefined
                  ? `${current.expected_roi.toFixed(2)}%`
                  : 'N/A'}
              </td>
              <td className="px-4 py-3 text-sm">
                {changes.roi_delta !== null && changes.roi_delta !== undefined && changes.roi_delta !== 0 ? (
                  <span className={`font-semibold ${changes.roi_delta > 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {changes.roi_delta > 0 ? '+' : ''}{changes.roi_delta.toFixed(2)}%
                  </span>
                ) : (
                  <span className="text-gray-500">No change</span>
                )}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Narrative Summary */}
      {narrative && (
        <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="text-sm font-semibold text-blue-900 mb-2">Natural Language Summary</div>
          <div className="text-sm text-blue-800">{narrative}</div>
        </div>
      )}
    </div>
  )
}
