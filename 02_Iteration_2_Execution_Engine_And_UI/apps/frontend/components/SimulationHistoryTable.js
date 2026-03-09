'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'
import ApprovalDialog from './ApprovalDialog'
import SimulationDetailModal from './SimulationDetailModal'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function SimulationHistoryTable({ getToken, onSimulationUpdate }) {
  const [simulations, setSimulations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedSimulation, setSelectedSimulation] = useState(null)
  const [showApprovalDialog, setShowApprovalDialog] = useState(false)
  const [showDetailModal, setShowDetailModal] = useState(false)
  const [detailSimulation, setDetailSimulation] = useState(null)
  const [executing, setExecuting] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0) // Force re-render key

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
      
      console.log('Fetched simulations response:', response.data)
      const simulationsList = response.data.simulations || []
      console.log('Setting simulations:', simulationsList.length, 'items')
      console.log('Simulations data:', simulationsList.map(s => ({ id: s.id, status: s.status, asset_name: s.asset_name })))
      
      // Force update by creating new array reference
      setSimulations([...simulationsList])
      setRefreshKey(prev => prev + 1) // Force re-render
      
      // Double-check: Log after state update
      setTimeout(() => {
        console.log('State after update - simulations count:', simulationsList.length)
      }, 100)
    } catch (err) {
      console.error('Failed to fetch simulations:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to fetch simulations')
    } finally {
      setLoading(false)
    }
  }

  const handleApproveClick = (simulation) => {
    if (simulation.status === 'PENDING_APPROVAL') {
      setSelectedSimulation(simulation)
      setShowApprovalDialog(true)
    }
  }

  const handleApproved = (updatedSimulation) => {
    console.log('Handling approved simulation:', updatedSimulation.id, 'Status:', updatedSimulation.status)
    setSimulations(prevSimulations => {
      const updated = prevSimulations.map(s => 
        s.id === updatedSimulation.id ? { ...updatedSimulation } : { ...s }
      )
      console.log('Updated simulations after approval:', updated.length, 'items')
      setRefreshKey(prev => prev + 1) // Force re-render
      return [...updated] // Force new array reference
    })
    setShowApprovalDialog(false)
    setSelectedSimulation(null)
    if (onSimulationUpdate) {
      onSimulationUpdate(updatedSimulation)
    }
    // Refresh after a delay to ensure consistency
    setTimeout(() => {
      fetchSimulations()
    }, 300)
  }

  const handleRejected = (updatedSimulation) => {
    console.log('Handling rejected simulation:', updatedSimulation.id, 'Status:', updatedSimulation.status)
    setSimulations(prevSimulations => {
      const updated = prevSimulations.map(s => 
        s.id === updatedSimulation.id ? { ...updatedSimulation } : { ...s }
      )
      console.log('Updated simulations after rejection:', updated.length, 'items')
      setRefreshKey(prev => prev + 1) // Force re-render
      return [...updated] // Force new array reference
    })
    setShowApprovalDialog(false)
    setSelectedSimulation(null)
    if (onSimulationUpdate) {
      onSimulationUpdate(updatedSimulation)
    }
    // Refresh after a delay to ensure consistency
    setTimeout(() => {
      fetchSimulations()
    }, 300)
  }

  const handleViewDetails = (simulation) => {
    console.log('[SimulationHistoryTable] Opening detail modal for simulation:', simulation)
    if (!simulation || !simulation.id) {
      console.error('[SimulationHistoryTable] Invalid simulation object:', simulation)
      alert('Error: Invalid simulation data. Please refresh and try again.')
      return
    }
    setDetailSimulation(simulation)
    setShowDetailModal(true)
  }

  const handleExecute = async (simulation) => {
    if (!getToken || executing) return
    
    if (!confirm(`Are you sure you want to execute this simulation? This will trigger the execution steps.`)) {
      return
    }
    
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
        `${API_BASE}/api/simulations/${simulation.id}/execute`,
        {},
        authConfig
      )
      
      console.log('Execution response:', response.data)
      
      // Update local state immediately with the response
      if (response.data) {
        const updatedSimulation = response.data
        console.log('Updating simulation:', updatedSimulation.id, 'Status:', updatedSimulation.status)
        setSimulations(prevSimulations => {
          const updated = prevSimulations.map(s => 
            s.id === updatedSimulation.id ? { ...updatedSimulation } : { ...s }
          )
          console.log('Updated simulations list:', updated.length, 'items')
          console.log('Updated simulation status in list:', updated.find(s => s.id === updatedSimulation.id)?.status)
          setRefreshKey(prev => prev + 1) // Force re-render
          return [...updated] // Force new array reference
        })
      }
      
      // Refresh simulations after a short delay to ensure backend has committed
      setTimeout(() => {
        console.log('Refreshing simulations list...')
        fetchSimulations()
      }, 500)
      
      // Show success message
      alert('Simulation executed successfully! Execution steps have been initialized and executed.')
    } catch (err) {
      console.error('Failed to execute simulation:', err)
      
      // Extract error message
      let errorMessage = err.response?.data?.detail || err.message || 'Failed to execute simulation'
      
      // Check if it's a gate blocking error
      if (errorMessage.includes('Execution gates blocked') || errorMessage.includes('KYC') || errorMessage.includes('AML') || errorMessage.includes('Tax')) {
        errorMessage = `Execution Blocked: ${errorMessage}\n\nPlease check the "Execution Gates" tab in the simulation details to see which gates failed.`
      }
      
      alert(errorMessage)
    } finally {
      setExecuting(false)
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'PENDING_APPROVAL':
        return 'bg-yellow-100 text-yellow-800'
      case 'APPROVED':
        return 'bg-blue-100 text-blue-800'
      case 'REJECTED':
        return 'bg-red-100 text-red-800'
      case 'EXECUTED':
        return 'bg-green-100 text-green-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Simulation History</h3>
        <div className="text-center py-8 text-gray-500">Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Simulation History</h3>
        <div className="text-center py-8 text-red-500">{error}</div>
      </div>
    )
  }

  if (simulations.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Simulation History</h3>
        <div className="text-center py-8 text-gray-500">
          <p>No simulations yet.</p>
          <p className="text-sm mt-2">Create a simulation from an AI recommendation to get started.</p>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Simulation History</h3>
          <button
            onClick={fetchSimulations}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            Refresh
          </button>
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Asset
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Action
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Quantity
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Created
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {simulations.map((sim) => (
                <tr key={`${sim.id}-${sim.status}-${refreshKey}`} className="hover:bg-gray-50">
                  <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                    {sim.asset_name || sim.asset_id}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                    {sim.action}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                    {sim.quantity}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(sim.status)}`}>
                      {sim.status.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                    {new Date(sim.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-sm">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleViewDetails(sim)}
                        className="text-blue-600 hover:text-blue-800 font-medium"
                      >
                        View Details
                      </button>
                      {sim.status === 'PENDING_APPROVAL' && (
                        <button
                          onClick={() => handleApproveClick(sim)}
                          className="text-green-600 hover:text-green-800 font-medium"
                        >
                          Review
                        </button>
                      )}
                      {sim.status === 'APPROVED' && (
                        <button
                          onClick={() => handleExecute(sim)}
                          disabled={executing}
                          className="text-purple-600 hover:text-purple-800 font-medium disabled:text-gray-400 disabled:cursor-not-allowed"
                        >
                          {executing ? 'Executing...' : 'Execute'}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showApprovalDialog && selectedSimulation && (
        <ApprovalDialog
          simulation={selectedSimulation}
          isOpen={showApprovalDialog}
          onClose={() => {
            setShowApprovalDialog(false)
            setSelectedSimulation(null)
          }}
          getToken={getToken}
          onApproved={handleApproved}
          onRejected={handleRejected}
        />
      )}

      {showDetailModal && detailSimulation && (
        <SimulationDetailModal
          simulation={detailSimulation}
          isOpen={showDetailModal}
          onClose={() => {
            setShowDetailModal(false)
            setDetailSimulation(null)
            // Refresh simulations after closing modal to get latest status
            setTimeout(() => {
              fetchSimulations()
            }, 300)
          }}
          getToken={getToken}
        />
      )}
    </>
  )
}
