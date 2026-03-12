'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function DecisionReplayPanel({ simulationId, getToken }) {
  const [lineage, setLineage] = useState(null)
  const [policyEvals, setPolicyEvals] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (simulationId) {
      fetchDecisionData()
    }
  }, [simulationId])

  const fetchDecisionData = async () => {
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
      
      const [lineageRes, evalRes] = await Promise.all([
        axios.get(`${API_BASE}/api/audit/decision-lineage?simulation_id=${simulationId}`, authConfig).catch(() => ({ data: { lineage: [] } })),
        axios.get(`${API_BASE}/api/audit/policy-evaluations?simulation_id=${simulationId}`, authConfig).catch(() => ({ data: { evaluations: [] } }))
      ])
      
      setLineage(lineageRes.data.lineage?.[0] || null)
      setPolicyEvals(evalRes.data.evaluations || [])
    } catch (err) {
      console.error('Failed to fetch decision data:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to fetch decision data')
    } finally {
      setLoading(false)
    }
  }

  if (!simulationId) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Decision Replay</h3>
        <div className="text-center py-8 text-gray-500">
          <p>Select a simulation to view decision replay</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Decision Replay</h3>
        <div className="text-center py-8 text-gray-500">Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Decision Replay</h3>
        <div className="text-center py-8 text-red-500">{error}</div>
      </div>
    )
  }

  if (!lineage) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Decision Replay</h3>
        <div className="text-center py-8 text-gray-500">
          <p>No decision lineage available for this simulation</p>
        </div>
      </div>
    )
  }

  const inputSnapshot = lineage.input_snapshot || {}
  const decisionReasoning = lineage.decision_reasoning || 'No reasoning provided'

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Decision Replay</h3>
        <button
          onClick={fetchDecisionData}
          className="text-sm text-blue-600 hover:text-blue-800"
        >
          Refresh
        </button>
      </div>

      <div className="space-y-4">
        {/* Model & Policy Versions */}
        <div className="grid grid-cols-2 gap-4">
          <div className="p-3 bg-gray-50 rounded">
            <div className="text-xs text-gray-500 mb-1">Model Version</div>
            <div className="text-sm font-semibold text-gray-900">{lineage.model_version || 'N/A'}</div>
          </div>
          <div className="p-3 bg-gray-50 rounded">
            <div className="text-xs text-gray-500 mb-1">Policy Version</div>
            <div className="text-sm font-semibold text-gray-900">{lineage.policy_version || 'N/A'}</div>
          </div>
        </div>

        {/* Decision Reasoning */}
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="text-sm font-semibold text-blue-900 mb-2">Decision Reasoning</div>
          <div className="text-sm text-blue-800">{decisionReasoning}</div>
        </div>

        {/* Input Snapshot */}
        {inputSnapshot && Object.keys(inputSnapshot).length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-2">Input Snapshot</h4>
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="space-y-2 text-sm">
                {inputSnapshot.asset_id && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Asset ID:</span>
                    <span className="font-medium text-gray-900">{inputSnapshot.asset_id}</span>
                  </div>
                )}
                {inputSnapshot.recommendation && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Recommendation:</span>
                    <span className="font-medium text-gray-900">{inputSnapshot.recommendation}</span>
                  </div>
                )}
                {inputSnapshot.expected_roi !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Expected ROI:</span>
                    <span className="font-medium text-gray-900">{inputSnapshot.expected_roi}%</span>
                  </div>
                )}
                {inputSnapshot.confidence !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Confidence:</span>
                    <span className="font-medium text-gray-900">{(inputSnapshot.confidence * 100).toFixed(1)}%</span>
                  </div>
                )}
                {inputSnapshot.risk_score !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Risk Score:</span>
                    <span className="font-medium text-gray-900">
                      {typeof inputSnapshot.risk_score === 'number' 
                        ? `${(inputSnapshot.risk_score * 100).toFixed(1)}%` 
                        : inputSnapshot.risk_score}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Policy Evaluations */}
        {policyEvals.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-2">Policy Evaluations</h4>
            <div className="space-y-2">
              {policyEvals.map((policyEval) => (
                <div 
                  key={policyEval.id} 
                  className={`p-3 rounded-lg border ${
                    policyEval.result === 'PASS' 
                      ? 'bg-green-50 border-green-200' 
                      : 'bg-red-50 border-red-200'
                  }`}
                >
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-gray-900">{policyEval.policy_name}</span>
                    <span className={`px-2 py-1 text-xs font-semibold rounded ${
                      policyEval.result === 'PASS'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {policyEval.result}
                    </span>
                  </div>
                  {policyEval.failure_reason && (
                    <div className="text-xs text-gray-600 mt-1">{policyEval.failure_reason}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Timestamp */}
        <div className="text-xs text-gray-500">
          Decision recorded: {new Date(lineage.timestamp).toLocaleString()}
        </div>
      </div>
    </div>
  )
}
