'use client'

import { useState } from 'react'
import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function SimulationModal({ 
  proposal, 
  isOpen, 
  onClose, 
  getToken, 
  onSimulationCreated 
}) {
  const [quantity, setQuantity] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [simulation, setSimulation] = useState(null)

  if (!isOpen) return null

  const handleCreateSimulation = async () => {
    if (!getToken || !proposal?.proposal_id) return
    
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
      
      const response = await axios.post(
        `${API_BASE}/api/simulations/create`,
        {
          proposal_id: proposal.proposal_id,
          quantity: quantity
        },
        authConfig
      )
      
      const createdSimulation = response.data
      setSimulation(createdSimulation)
      
      if (onSimulationCreated) {
        onSimulationCreated(createdSimulation)
      }
      
      // Show success message
      console.log('✅ Simulation created successfully:', createdSimulation.id)
    } catch (err) {
      console.error('Failed to create simulation:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to create simulation')
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    setSimulation(null)
    setError(null)
    setQuantity(1)
    onClose()
  }

  return (
    <div className="fixed inset-0 backdrop-blur-[2px] bg-black/20 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-bold text-gray-900">Create Simulation</h2>
            <button
              onClick={handleClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {!simulation ? (
            <>
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">{proposal?.asset_name}</h3>
                <p className="text-sm text-gray-600 mb-4">{proposal?.rationale}</p>
                
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <div className="text-xs text-gray-500 mb-1">Recommendation</div>
                    <div className={`text-lg font-semibold ${
                      proposal?.recommendation === 'BUY' || proposal?.recommendation === 'ARBITRAGE_BUY' 
                        ? 'text-green-600' 
                        : proposal?.recommendation === 'SELL' || proposal?.recommendation === 'ARBITRAGE_SELL'
                        ? 'text-red-600'
                        : 'text-yellow-600'
                    }`}>
                      {proposal?.recommendation}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-1">Confidence</div>
                    <div className="text-lg font-semibold">{(proposal?.confidence_score * 100).toFixed(0)}%</div>
                  </div>
                  {proposal?.expected_roi !== null && (
                    <div>
                      <div className="text-xs text-gray-500 mb-1">Expected ROI</div>
                      <div className={`text-lg font-semibold ${proposal.expected_roi >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {proposal.expected_roi >= 0 ? '+' : ''}{proposal.expected_roi.toFixed(1)}%
                      </div>
                    </div>
                  )}
                  {proposal?.risk_score !== null && proposal?.risk_score !== undefined && (
                    <div>
                      <div className="text-xs text-gray-500 mb-1">Risk Score</div>
                      <div className={`text-lg font-semibold ${
                        proposal.risk_score < 0.5 ? 'text-green-600' : proposal.risk_score < 0.7 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {(proposal.risk_score * 100).toFixed(0)}%
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Quantity
                </label>
                <input
                  type="number"
                  min="1"
                  value={quantity}
                  onChange={(e) => {
                    const value = e.target.value;
                    if (value === '' || value === '-') {
                      setQuantity('');
                    } else {
                      const numValue = parseInt(value, 10);
                      if (!isNaN(numValue) && numValue >= 1) {
                        setQuantity(numValue);
                      }
                    }
                  }}
                  onBlur={(e) => {
                    if (e.target.value === '' || parseInt(e.target.value, 10) < 1) {
                      setQuantity(1);
                    }
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
                />
              </div>

              {error && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
                  {error}
                </div>
              )}

              <div className="flex justify-end gap-3">
                <button
                  onClick={handleClose}
                  className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                  disabled={loading}
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateSimulation}
                  disabled={loading || quantity < 1}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  {loading ? 'Creating...' : 'Create Simulation'}
                </button>
              </div>
            </>
          ) : (
            <div>
              <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-md">
                <h3 className="text-lg font-semibold text-green-900 mb-2">✅ Simulation Created Successfully</h3>
                <p className="text-sm text-green-700 mb-2">
                  Your simulation has been created and is now <strong>pending your approval</strong>.
                </p>
                <p className="text-xs text-green-600">
                  Go to the "Simulation History" section below to review and approve/reject this simulation.
                </p>
              </div>

              <div className="mb-4">
                <div className="text-sm font-semibold text-gray-700 mb-2">Simulation Details:</div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Action:</span>
                    <span className="font-semibold">{simulation.action}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Quantity:</span>
                    <span className="font-semibold">{simulation.quantity}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Status:</span>
                    <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs font-semibold">
                      {simulation.status.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 mt-2 pt-2 border-t">
                    ID: <span className="font-mono">{simulation.id.substring(0, 8)}...</span>
                  </div>
                </div>
              </div>

              {simulation.simulation_result && (
                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-gray-900 mb-2">Projected Impact</h4>
                  <div className="space-y-2">
                    {simulation.simulation_result.projected_roi !== null && (
                      <div className="text-sm">
                        <span className="text-gray-600">Projected ROI: </span>
                        <span className="font-semibold">{simulation.simulation_result.projected_roi.toFixed(2)}%</span>
                      </div>
                    )}
                    {simulation.simulation_result.warnings && simulation.simulation_result.warnings.length > 0 && (
                      <div className="p-2 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-800">
                        <div className="font-semibold mb-1">Warnings:</div>
                        <ul className="list-disc list-inside">
                          {simulation.simulation_result.warnings.map((warning, idx) => (
                            <li key={idx}>{warning}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}

              <div className="flex justify-end">
                <button
                  onClick={handleClose}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  Close
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
