'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function ComplianceEvaluationPanel({ simulationId, getToken }) {
  const [evaluation, setEvaluation] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (simulationId) {
      fetchComplianceEvaluation()
    }
  }, [simulationId])

  const fetchComplianceEvaluation = async () => {
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
        `${API_BASE}/api/compliance/${simulationId}/evaluation`,
        authConfig
      )
      
      setEvaluation(response.data)
    } catch (err) {
      // 404 is expected when evaluation hasn't been created yet - don't log as error
      if (err.response?.status === 404) {
        setError(null) // Clear error, show empty state message instead
        setEvaluation(null)
      } else {
        console.error('Failed to fetch compliance evaluation:', err)
        setError(err.response?.data?.detail || err.message || 'Failed to fetch compliance evaluation')
      }
    } finally {
      setLoading(false)
    }
  }

  const getResultColor = (result) => {
    switch (result) {
      case 'PASS':
        return 'bg-green-100 text-green-800 border-green-300'
      case 'FAIL':
        return 'bg-red-100 text-red-800 border-red-300'
      case 'CONDITIONAL':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300'
    }
  }

  const getResultIcon = (result) => {
    switch (result) {
      case 'PASS':
        return '✓'
      case 'FAIL':
        return '✗'
      case 'CONDITIONAL':
        return '⚠'
      default:
        return '○'
    }
  }

  if (!simulationId) {
    return (
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Compliance Evaluation</h3>
        <div className="text-center py-8 text-gray-500">
          <p>No simulation ID provided</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Compliance Evaluation</h3>
        <div className="text-center py-8 text-gray-500">Loading compliance evaluation...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Compliance Evaluation</h3>
        <div className="text-center py-8 text-gray-500">{error}</div>
        <button
          onClick={fetchComplianceEvaluation}
          className="mt-4 px-4 py-2 text-sm text-blue-600 hover:text-blue-800"
        >
          Retry
        </button>
      </div>
    )
  }

  if (!evaluation) {
    return (
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Compliance Evaluation</h3>
        <div className="text-center py-8 text-gray-500">
          <p>No compliance evaluation available yet.</p>
          <p className="text-sm mt-2">Evaluation will be performed when simulation is approved.</p>
        </div>
      </div>
    )
  }

  const overallResult = evaluation.overall_result || 'PENDING'
  const evaluations = evaluation.evaluations || []
  const documentRequirements = evaluation.document_requirements || []

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Compliance Evaluation</h3>
        <button
          onClick={fetchComplianceEvaluation}
          className="text-sm text-blue-600 hover:text-blue-800"
        >
          Refresh
        </button>
      </div>

      {/* Overall Result */}
      <div className={`mb-6 p-4 rounded-lg border-2 ${getResultColor(overallResult)}`}>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-2xl">{getResultIcon(overallResult)}</span>
          <span className="text-lg font-bold">Overall Result: {overallResult}</span>
        </div>
        {evaluation.explanation && (
          <p className="text-sm mt-2">{evaluation.explanation}</p>
        )}
      </div>

      {/* Rule Evaluations */}
      {evaluations.length > 0 && (
        <div className="mb-6">
          <h4 className="text-sm font-semibold text-gray-900 mb-3">Rule Evaluations</h4>
          <div className="space-y-2">
            {evaluations.map((evalItem, index) => (
              <div
                key={evalItem.rule_id || index}
                className={`p-3 rounded-lg border ${getResultColor(evalItem.result)}`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium">{evalItem.rule_name}</span>
                  <span className={`px-2 py-0.5 text-xs font-semibold rounded ${getResultColor(evalItem.result)}`}>
                    {getResultIcon(evalItem.result)} {evalItem.result}
                  </span>
                </div>
                {evalItem.explanation && (
                  <p className="text-xs text-gray-700 mt-1">{evalItem.explanation}</p>
                )}
                {evalItem.failure_reason && (
                  <p className="text-xs text-red-700 mt-1">
                    <strong>Failure:</strong> {evalItem.failure_reason}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Document Requirements */}
      {documentRequirements.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-900 mb-3">Document Requirements</h4>
          <div className="space-y-2">
            {documentRequirements.map((doc, index) => (
              <div
                key={doc.id || index}
                className={`p-3 rounded-lg border ${
                  doc.provided
                    ? 'bg-green-50 border-green-200'
                    : 'bg-yellow-50 border-yellow-200'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium text-gray-900">{doc.document_name}</span>
                    <span className="text-xs text-gray-600 ml-2">({doc.document_type})</span>
                  </div>
                  <span className={`px-2 py-0.5 text-xs font-semibold rounded ${
                    doc.provided
                      ? 'bg-green-100 text-green-800'
                      : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {doc.provided ? '✓ Provided' : '⚠ Required'}
                  </span>
                </div>
                {doc.provided_at && (
                  <p className="text-xs text-gray-600 mt-1">
                    Provided: {new Date(doc.provided_at).toLocaleString()}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {evaluations.length === 0 && documentRequirements.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p>No detailed compliance information available.</p>
        </div>
      )}
    </div>
  )
}
