'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function ExecutionGatesPanel({ simulationId, getToken }) {
  const [gates, setGates] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (simulationId) {
      fetchExecutionGates()
    }
  }, [simulationId])

  const fetchExecutionGates = async () => {
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
        `${API_BASE}/api/executions/${simulationId}/gates`,
        authConfig
      )
      
      setGates(response.data.gates || [])
    } catch (err) {
      console.error('Failed to fetch execution gates:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to fetch execution gates')
    } finally {
      setLoading(false)
    }
  }

  const getGateStatusColor = (status) => {
    switch (status) {
      case 'PASSED':
        return 'bg-green-100 text-green-800 border-green-300'
      case 'BLOCKED':
        return 'bg-red-100 text-red-800 border-red-300'
      case 'PENDING':
      default:
        return 'bg-yellow-100 text-yellow-800 border-yellow-300'
    }
  }

  const getGateStatusIcon = (status) => {
    switch (status) {
      case 'PASSED':
        return '✓'
      case 'BLOCKED':
        return '✗'
      case 'PENDING':
      default:
        return '○'
    }
  }

  const getGateTypeLabel = (type) => {
    switch (type) {
      case 'KYC':
        return 'KYC Verification'
      case 'AML':
        return 'AML Risk Check'
      case 'TAX':
        return 'Tax Obligation'
      case 'COMPLIANCE':
        return 'Compliance Check'
      default:
        return type
    }
  }

  if (!simulationId) {
    return (
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Execution Gates</h3>
        <div className="text-center py-8 text-gray-500">
          <p>No simulation ID provided</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Execution Gates</h3>
        <div className="text-center py-8 text-gray-500">Loading execution gates...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Execution Gates</h3>
        <div className="text-center py-8 text-gray-500">{error}</div>
        <button
          onClick={fetchExecutionGates}
          className="mt-4 px-4 py-2 text-sm text-blue-600 hover:text-blue-800"
        >
          Retry
        </button>
      </div>
    )
  }

  if (gates.length === 0) {
    return (
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Execution Gates</h3>
        <div className="text-center py-8 text-gray-500">
          <p>No execution gates evaluated yet.</p>
          <p className="text-sm mt-2">Gates will be evaluated before simulation execution.</p>
        </div>
      </div>
    )
  }

  const overallStatus = gates.every(g => g.gate_status === 'PASSED') 
    ? 'PASSED' 
    : gates.some(g => g.gate_status === 'BLOCKED')
    ? 'BLOCKED'
    : 'PENDING'

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Execution Gates</h3>
        <button
          onClick={fetchExecutionGates}
          className="text-sm text-blue-600 hover:text-blue-800"
        >
          Refresh
        </button>
      </div>

      <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-blue-800">
          <strong>What are Execution Gates?</strong> These are pre-execution checks (KYC, AML, Tax) 
          that must pass before a simulation can be executed. All gates must be PASSED for execution to proceed.
        </p>
      </div>

      {/* Overall Status */}
      <div className={`mb-6 p-4 rounded-lg border-2 ${getGateStatusColor(overallStatus)}`}>
        <div className="flex items-center gap-2">
          <span className="text-2xl">{getGateStatusIcon(overallStatus)}</span>
          <span className="text-lg font-bold">Overall Gate Status: {overallStatus}</span>
        </div>
        {overallStatus === 'BLOCKED' && (
          <p className="text-sm mt-2">
            Execution is blocked. One or more gates have failed. See details below.
          </p>
        )}
        {overallStatus === 'PASSED' && (
          <p className="text-sm mt-2">
            All gates have passed. Execution is allowed to proceed.
          </p>
        )}
      </div>

      {/* Individual Gates */}
      <div className="space-y-3">
        {gates.map((gate, index) => (
          <div
            key={gate.id || index}
            className={`p-4 rounded-lg border-2 ${getGateStatusColor(gate.gate_status)}`}
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-base font-semibold">{getGateTypeLabel(gate.gate_type)}</span>
                <span className={`px-2 py-0.5 text-xs font-semibold rounded ${getGateStatusColor(gate.gate_status)}`}>
                  {getGateStatusIcon(gate.gate_status)} {gate.gate_status}
                </span>
              </div>
            </div>
            
            {gate.block_reason && (
              <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-800">
                <strong>Block Reason:</strong> {gate.block_reason}
              </div>
            )}
            
            {gate.evaluated_at && (
              <div className="mt-2 text-xs text-gray-600">
                Evaluated: {new Date(gate.evaluated_at).toLocaleString()}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Gate Descriptions */}
      <div className="mt-6 p-4 bg-gray-50 rounded-lg">
        <h4 className="text-sm font-semibold text-gray-900 mb-2">Gate Descriptions</h4>
        <div className="text-xs text-gray-700 space-y-1">
          <p><strong>KYC (Know Your Customer):</strong> Verifies user identity and verification status.</p>
          <p><strong>AML (Anti-Money Laundering):</strong> Checks for money laundering risk flags.</p>
          <p><strong>Tax:</strong> Calculates and validates tax obligations for the trade.</p>
          <p><strong>Compliance:</strong> Ensures trade complies with regulatory rules.</p>
        </div>
      </div>
    </div>
  )
}
