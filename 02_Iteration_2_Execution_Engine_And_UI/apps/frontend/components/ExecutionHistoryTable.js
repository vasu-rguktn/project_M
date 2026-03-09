'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function ExecutionHistoryTable({ getToken }) {
  const [executions, setExecutions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const [initialLoad, setInitialLoad] = useState(true)
  const [lastUpdateTime, setLastUpdateTime] = useState(Date.now())

  useEffect(() => {
    fetchExecutions()
    
    // Auto-refresh every 5 seconds to catch new executions
    const interval = setInterval(() => {
      fetchExecutions(false) // Don't show loading on auto-refresh
    }, 5000)
    
    return () => clearInterval(interval)
  }, [])

  const fetchExecutions = async (showLoading = true) => {
    if (!getToken) return
    
    if (showLoading) {
      setLoading(true)
    }
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
        `${API_BASE}/api/executions/autonomous`,
        authConfig
      )
      
      const executionsList = response.data.executions || []
      console.log('Fetched autonomous executions:', executionsList.length, 'items')
      console.log('Autonomous executions data:', executionsList.map(e => ({ 
        id: e.id, 
        decision: e.decision, 
        simulation_id: e.simulation_id,
        executed_at: e.executed_at 
      })))
      
      // Create new array with new object references
      const newExecutions = executionsList.map(e => ({ ...e }))
      
      // Check if data actually changed
      setExecutions(prevExecutions => {
        const prevIds = new Set(prevExecutions.map(e => e.id))
        const newIds = new Set(executionsList.map(e => e.id))
        const hasChanged = prevExecutions.length !== executionsList.length || 
                          ![...newIds].every(id => prevIds.has(id)) ||
                          executionsList.some((e, idx) => {
                            const prev = prevExecutions[idx]
                            return !prev || prev.decision !== e.decision || prev.executed_at !== e.executed_at
                          })
        
        if (hasChanged) {
          console.log('Autonomous executions changed, updating state')
        } else {
          console.log('Autonomous executions unchanged, but updating anyway')
        }
        
        return newExecutions // Always return new array reference
      })
      
      // Update refreshKey and timestamp OUTSIDE setExecutions to ensure re-render
      setRefreshKey(prev => prev + 1)
      setLastUpdateTime(Date.now())
      console.log('Forced re-render with new refreshKey and timestamp')
    } catch (err) {
      console.error('Failed to fetch execution history:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to fetch execution history')
    } finally {
      if (showLoading) {
        setLoading(false)
      }
      if (initialLoad) {
        setInitialLoad(false)
      }
    }
  }

  const getDecisionBadgeClass = (decision) => {
    switch (decision) {
      case 'EXECUTED':
        return 'bg-green-100 text-green-800'
      case 'SKIPPED':
        return 'bg-yellow-100 text-yellow-800'
      case 'BLOCKED':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Autonomous Execution History</h2>
        <div className="text-center py-8">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-2 text-gray-600">Loading execution history...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Autonomous Execution History</h2>
        <div className="bg-red-50 border border-red-200 rounded p-4">
          <p className="text-red-800">Error: {error}</p>
          <button
            onClick={fetchExecutions}
            className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">Autonomous Execution History</h2>
        <button
          onClick={fetchExecutions}
          className="text-sm text-blue-600 hover:text-blue-800 underline"
        >
          Refresh
        </button>
      </div>

      {executions.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p>No autonomous executions recorded yet.</p>
          <p className="text-sm mt-2">Executions will appear here after autonomous execution is enabled and simulations are executed.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Decision
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Simulation ID
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Executed At
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Reason
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200" key={`tbody-${refreshKey}-${lastUpdateTime}`}>
              {executions.map((execution, index) => (
                <tr key={`exec-${execution.id}-${execution.decision}-${execution.executed_at}-${refreshKey}-${lastUpdateTime}-${index}`} className="hover:bg-gray-50">
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getDecisionBadgeClass(execution.decision)}`}>
                      {execution.decision}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900">
                    <span className="font-mono text-xs">{execution.simulation_id.substring(0, 8)}...</span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {new Date(execution.executed_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {execution.failure_reason || execution.reason || 'N/A'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
