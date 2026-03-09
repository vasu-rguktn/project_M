'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function ExecutionStepsPanel({ simulationId, getToken }) {
  const [steps, setSteps] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [executing, setExecuting] = useState(false)
  const [resetting, setResetting] = useState(null) // Track which step is being reset

  useEffect(() => {
    if (simulationId) {
      fetchExecutionSteps()
    }
  }, [simulationId])

  const fetchExecutionSteps = async () => {
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
        `${API_BASE}/api/executions/${simulationId}/steps`,
        authConfig
      )
      
      setSteps(response.data.steps || [])
    } catch (err) {
      console.error('Failed to fetch execution steps:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to fetch execution steps')
    } finally {
      setLoading(false)
    }
  }

  const handleExecuteStep = async () => {
    if (!getToken || !simulationId || executing) return
    
    setExecuting(true)
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
        `${API_BASE}/api/executions/${simulationId}/execute-step`,
        {},
        authConfig
      )
      
      if (response.data.step) {
        // Refresh steps after execution
        setTimeout(() => {
          fetchExecutionSteps()
        }, 500)
      }
    } catch (err) {
      console.error('Failed to execute step:', err)
      alert(`Failed to execute step: ${err.response?.data?.detail || err.message}`)
    } finally {
      setExecuting(false)
    }
  }

  const handleRetryFailedStep = async (stepId) => {
    if (!getToken || !stepId || resetting === stepId) return
    
    setResetting(stepId)
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
        `${API_BASE}/api/executions/steps/${stepId}/reset`,
        {},
        authConfig
      )
      
      if (response.data.step) {
        // Refresh steps after reset
        setTimeout(() => {
          fetchExecutionSteps()
        }, 500)
        alert('Failed step reset to PENDING. You can now retry it.')
      }
    } catch (err) {
      console.error('Failed to reset step:', err)
      alert(`Failed to reset step: ${err.response?.data?.detail || err.message}`)
    } finally {
      setResetting(null)
    }
  }

  const getStepStatusColor = (status) => {
    switch (status) {
      case 'SUCCESS':
        return 'bg-green-100 text-green-800 border-green-300'
      case 'FAILED':
        return 'bg-red-100 text-red-800 border-red-300'
      case 'IN_PROGRESS':
        return 'bg-blue-100 text-blue-800 border-blue-300'
      case 'COMPENSATED':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300'
      case 'PENDING':
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300'
    }
  }

  const getStepStatusIcon = (status) => {
    switch (status) {
      case 'SUCCESS':
        return '✓'
      case 'FAILED':
        return '✗'
      case 'IN_PROGRESS':
        return '⟳'
      case 'COMPENSATED':
        return '↻'
      case 'PENDING':
      default:
        return '○'
    }
  }

  if (!simulationId) {
    return (
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Execution Steps</h3>
        <div className="text-center py-8 text-gray-500">
          <p>No simulation ID provided</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Execution Steps</h3>
        <div className="text-center py-8 text-gray-500">Loading execution steps...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Execution Steps</h3>
        <div className="text-center py-8 text-red-500">{error}</div>
        <button
          onClick={fetchExecutionSteps}
          className="mt-4 px-4 py-2 text-sm text-blue-600 hover:text-blue-800"
        >
          Retry
        </button>
      </div>
    )
  }

  if (steps.length === 0) {
    return (
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Execution Steps</h3>
        <div className="text-center py-8 text-gray-500">
          <p>No execution steps found for this simulation.</p>
          <p className="text-sm mt-2">Steps will be created when simulation is executed.</p>
        </div>
      </div>
    )
  }

  const pendingSteps = steps.filter(s => s.status === 'PENDING')
  const hasPendingSteps = pendingSteps.length > 0

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Execution Steps</h3>
        <div className="flex gap-2">
          {hasPendingSteps && (
            <button
              onClick={handleExecuteStep}
              disabled={executing}
              className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {executing ? 'Executing...' : 'Execute Next Step'}
            </button>
          )}
          <button
            onClick={fetchExecutionSteps}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="space-y-3">
        {steps.map((step, index) => (
          <div
            key={step.id || index}
            className={`p-4 rounded-lg border-2 ${getStepStatusColor(step.status)}`}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3 flex-1">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-white border-2 border-current flex items-center justify-center text-sm font-bold">
                  {step.step_order || index + 1}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-base font-semibold">{step.step_name}</span>
                    <span className={`px-2 py-0.5 text-xs font-semibold rounded ${getStepStatusColor(step.status)}`}>
                      {getStepStatusIcon(step.status)} {step.status}
                    </span>
                  </div>
                  
                  {step.step_data && typeof step.step_data === 'object' && (
                    <div className="text-sm text-gray-700 mt-2">
                      {step.step_data.message && (
                        <p className="mb-1">{step.step_data.message}</p>
                      )}
                      {step.step_data.tracking_number && (
                        <p className="text-xs">Tracking: {step.step_data.tracking_number}</p>
                      )}
                      {step.step_data.facility_id && (
                        <p className="text-xs">Facility: {step.step_data.facility_id}</p>
                      )}
                    </div>
                  )}
                  
                  {step.failure_reason && (
                    <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-800">
                      <strong>Failure Reason:</strong> {step.failure_reason}
                      {step.status === 'FAILED' && (
                        <button
                          onClick={() => handleRetryFailedStep(step.id)}
                          disabled={resetting === step.id}
                          className="ml-3 px-2 py-1 text-xs font-medium text-white bg-red-600 rounded hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                        >
                          {resetting === step.id ? 'Resetting...' : 'Retry Step'}
                        </button>
                      )}
                    </div>
                  )}
                  
                  {step.compensation_status && step.compensation_status !== 'NONE' && (
                    <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-800">
                      <strong>Compensation:</strong> {step.compensation_status}
                    </div>
                  )}
                  
                  <div className="flex gap-4 mt-2 text-xs text-gray-600">
                    {step.started_at && (
                      <span>Started: {new Date(step.started_at).toLocaleString()}</span>
                    )}
                    {step.completed_at && (
                      <span>Completed: {new Date(step.completed_at).toLocaleString()}</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {hasPendingSteps && (
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded text-sm text-blue-800">
          <strong>Note:</strong> {pendingSteps.length} step(s) pending execution. Click "Execute Next Step" to proceed.
        </div>
      )}
    </div>
  )
}
