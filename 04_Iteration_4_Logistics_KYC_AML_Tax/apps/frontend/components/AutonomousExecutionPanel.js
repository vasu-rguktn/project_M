'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function AutonomousExecutionPanel({ getToken }) {
  const [simulations, setSimulations] = useState([])
  const [pendingSimulations, setPendingSimulations] = useState([])
  const [executing, setExecuting] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  useEffect(() => {
    fetchSimulations()
  }, [])

  const fetchSimulations = async () => {
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
        `${API_BASE}/api/simulations`,
        authConfig
      )
      
      const allSims = response.data.simulations || []
      setSimulations(allSims)
      // Filter approved simulations that haven't been executed
      const approved = allSims.filter(sim => sim.status === 'APPROVED')
      setPendingSimulations(approved)
    } catch (err) {
      console.error('Failed to fetch simulations:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to fetch simulations')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // Update pending simulations when simulations change
    const approved = simulations.filter(sim => sim.status === 'APPROVED')
    setPendingSimulations(approved)
  }, [simulations])

  const handleExecute = async (simulationId) => {
    if (!getToken) return
    
    setExecuting(true)
    setError(null)
    setSuccess(null)
    
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
        `${API_BASE}/api/executions/run-autonomous`,
        { simulation_id: simulationId },
        authConfig
      )
      
      setSuccess(`Execution ${response.data.decision}: ${response.data.reason}`)
      
      // Refresh simulations after a delay
      setTimeout(() => {
        fetchSimulations()
        setSuccess(null)
      }, 2000)
    } catch (err) {
      console.error('Failed to execute autonomously:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to execute autonomously')
    } finally {
      setExecuting(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Autonomous Execution</h3>
        <div className="text-center py-8">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-2 text-gray-600">Loading simulations...</p>
        </div>
      </div>
    )
  }

  if (pendingSimulations.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Autonomous Execution</h3>
          <button
            onClick={fetchSimulations}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            Refresh
          </button>
        </div>
        <div className="text-center py-8 text-gray-500">
          <p>No approved simulations available for autonomous execution.</p>
          <p className="text-sm mt-2">Approve a simulation first, then it will appear here.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Autonomous Execution</h3>
        <button
          onClick={fetchSimulations}
          className="text-sm text-blue-600 hover:text-blue-800"
        >
          Refresh
        </button>
      </div>
      
      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded p-4">
          <p className="text-red-800">{error}</p>
        </div>
      )}
      
      {success && (
        <div className="mb-4 bg-green-50 border border-green-200 rounded p-4">
          <p className="text-green-800">{success}</p>
        </div>
      )}

      <div className="space-y-4">
        {pendingSimulations.map((simulation) => (
          <div
            key={simulation.id}
            className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50"
          >
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <h3 className="font-semibold text-gray-900">
                  {simulation.asset_id || 'Unknown Asset'}
                </h3>
                <div className="mt-2 text-sm text-gray-600">
                  <p>
                    <span className="font-medium">Action:</span> {simulation.action}
                  </p>
                  <p>
                    <span className="font-medium">Quantity:</span> {simulation.quantity}
                  </p>
                  {simulation.confidence && (
                    <p>
                      <span className="font-medium">Confidence:</span>{' '}
                      {(simulation.confidence * 100).toFixed(1)}%
                    </p>
                  )}
                  {simulation.risk_score && (
                    <p>
                      <span className="font-medium">Risk Score:</span>{' '}
                      {(simulation.risk_score * 100).toFixed(1)}%
                    </p>
                  )}
                  {simulation.expected_roi && (
                    <p>
                      <span className="font-medium">Expected ROI:</span>{' '}
                      {simulation.expected_roi.toFixed(2)}%
                    </p>
                  )}
                </div>
              </div>
              <button
                onClick={() => handleExecute(simulation.id)}
                disabled={executing}
                className="ml-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {executing ? 'Executing...' : 'Execute Autonomously'}
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded">
        <p className="text-sm text-yellow-800">
          <strong>Note:</strong> Autonomous execution will only proceed if all policy checks pass:
          confidence &gt;= 85%, risk &lt;= 30%, daily limits not exceeded, and kill switch is inactive.
        </p>
      </div>
    </div>
  )
}
