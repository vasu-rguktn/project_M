import { useState } from 'react'
import axios from 'axios'
import SimulationModal from './SimulationModal'
import ConfidenceStabilityIndicator from './ConfidenceStabilityIndicator'
import StrategyReliabilityBadge from './StrategyReliabilityBadge'
import WhatChangedPanel from './WhatChangedPanel'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000'

export default function AdvisorCard({ proposal, getToken, onAction }) {
  const [expanded, setExpanded] = useState(false)
  const [loading, setLoading] = useState(false)
  const [fetchingDetail, setFetchingDetail] = useState(false)
  const [detailedProposal, setDetailedProposal] = useState(null)
  const [fetchError, setFetchError] = useState(null)
  const [showSimulationModal, setShowSimulationModal] = useState(false)
  const [narrative, setNarrative] = useState(null)
  const [showWhatChanged, setShowWhatChanged] = useState(false)
  
  const getRecommendationColor = (rec) => {
    switch (rec) {
      case 'BUY':
        return 'text-green-600 bg-green-50'
      case 'SELL':
        return 'text-red-600 bg-red-50'
      case 'HOLD':
        return 'text-yellow-600 bg-yellow-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }
  
  const getConfidenceColor = (score) => {
    if (score >= 0.8) return 'text-green-600'
    if (score >= 0.6) return 'text-yellow-600'
    return 'text-red-600'
  }
  
  const handleSimulateBuy = () => {
    // Phase 11: Open simulation modal instead of directly buying
    setShowSimulationModal(true)
  }

  const handleSimulationCreated = (simulation) => {
    console.log('Simulation created:', simulation)
    if (onAction) {
      onAction('simulation_created', simulation)
    }
    // Modal will close itself after creation
  }

  const fetchNarrative = async () => {
    if (!getToken || !proposal?.proposal_id) return
    
    try {
      const token = await getToken()
      if (!token || !token.trim()) return
      
      const authConfig = {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
      
      const response = await axios.get(
        `${API_BASE}/api/explainability/narrative/${proposal.proposal_id}`,
        authConfig
      )
      
      setNarrative(response.data?.narrative || null)
    } catch (err) {
      console.error('Failed to fetch narrative:', err)
      // Don't set error state, just log it
    }
  }
  
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h4 className="text-lg font-semibold text-gray-900">
              {proposal.asset_name}
            </h4>
            {proposal.vintage && (
              <span className="text-sm text-gray-500">({proposal.vintage})</span>
            )}
            <span className={`px-2 py-1 rounded text-xs font-medium ${getRecommendationColor(proposal.recommendation)}`}>
              {proposal.recommendation}
            </span>
          </div>
          <p className="text-sm text-gray-600 mb-2">{proposal.region}</p>
          <p className="text-sm text-gray-700 mb-2">{proposal.rationale}</p>
          {proposal.evidence && proposal.evidence.length > 0 && proposal.evidence[0].model_explanation && (
            <div className="text-xs text-gray-600 bg-gray-50 p-2 rounded mt-2">
              <strong>AI Explanation:</strong> {proposal.evidence[0].model_explanation.substring(0, 200)}
              {proposal.evidence[0].model_explanation.length > 200 && '...'}
            </div>
          )}
        </div>
      </div>
      
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div>
          <div className="flex items-center gap-1">
            <div className="text-xs text-gray-500 mb-1">Confidence</div>
            <div className="group relative">
              <span className="text-xs text-gray-400 cursor-help">ℹ️</span>
              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-48 p-2 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 pointer-events-none z-10">
                Confidence score indicates how certain the AI is about this recommendation. Higher confidence means more reliable predictions.
              </div>
            </div>
          </div>
          <div className={`text-lg font-semibold ${getConfidenceColor(proposal.confidence_score)}`}>
            {(proposal.confidence_score * 100).toFixed(0)}%
          </div>
          <ConfidenceStabilityIndicator getToken={getToken} />
        </div>
        {proposal.expected_roi !== null && (
          <div>
            <div className="flex items-center gap-1">
              <div className="text-xs text-gray-500 mb-1">Expected ROI</div>
              <div className="group relative">
                <span className="text-xs text-gray-400 cursor-help">ℹ️</span>
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-48 p-2 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 pointer-events-none z-10">
                  Expected Return on Investment (ROI) is the predicted percentage gain or loss from this trade. This is an estimate, not a guarantee.
                </div>
              </div>
            </div>
            <div className={`text-lg font-semibold ${proposal.expected_roi >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {proposal.expected_roi >= 0 ? '+' : ''}{proposal.expected_roi.toFixed(1)}%
            </div>
          </div>
        )}
        {(() => {
          // Use detailed proposal risk_score if available, otherwise use basic proposal
          const displayProposal = detailedProposal || proposal
          const riskScore = displayProposal.risk_score
          const isValidRiskScore = riskScore !== null && riskScore !== undefined && 
                                   !isNaN(riskScore) && typeof riskScore === 'number' &&
                                   riskScore >= 0 && riskScore <= 1
          
          console.log(`[AdvisorCard] Risk Score Check for proposal ${proposal.proposal_id}:`, {
            riskScore,
            isValidRiskScore,
            type: typeof riskScore,
            isNaN: isNaN(riskScore),
            hasDetailedProposal: !!detailedProposal,
            basicProposalRiskScore: proposal.risk_score
          })
          
          if (isValidRiskScore) {
            return (
              <div>
                <div className="flex items-center gap-1">
                  <div className="text-xs text-gray-500 mb-1">Risk Score</div>
                  <div className="group relative">
                    <span className="text-xs text-gray-400 cursor-help">ℹ️</span>
                    <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-48 p-2 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 pointer-events-none z-10">
                      Risk score measures the potential for loss. Lower scores indicate safer investments. Scores above 70% are considered high risk.
                    </div>
                  </div>
                </div>
                <div className={`text-lg font-semibold ${riskScore < 0.5 ? 'text-green-600' : riskScore < 0.7 ? 'text-yellow-600' : 'text-red-600'}`}>
                  {(riskScore * 100).toFixed(0)}%
                </div>
              </div>
            )
          }
          return null
        })()}
      </div>
      
      {proposal.compliance_status && (
        <div className={`mb-4 p-2 rounded text-xs ${
          proposal.compliance_status === 'PASS' 
            ? 'bg-green-50 text-green-700' 
            : 'bg-red-50 text-red-700'
        }`}>
          <strong>Compliance:</strong> {proposal.compliance_status}
          {proposal.compliance_reason && ` - ${proposal.compliance_reason}`}
        </div>
      )}
      
      <div className="flex items-center gap-2">
        {(proposal.recommendation === 'BUY' || proposal.recommendation === 'SELL' || proposal.recommendation === 'ARBITRAGE_BUY' || proposal.recommendation === 'ARBITRAGE_SELL') && (
          <button
            onClick={handleSimulateBuy}
            disabled={loading}
            className={`px-4 py-2 text-white rounded hover:opacity-90 disabled:opacity-50 text-sm font-medium ${
              proposal.recommendation === 'BUY' || proposal.recommendation === 'ARBITRAGE_BUY' 
                ? 'bg-blue-600 hover:bg-blue-700' 
                : 'bg-red-600 hover:bg-red-700'
            }`}
          >
            {loading ? 'Processing...' : `Simulate ${proposal.recommendation === 'BUY' || proposal.recommendation === 'ARBITRAGE_BUY' ? 'Buy' : 'Sell'}`}
          </button>
        )}
        <button
          onClick={async () => {
            if (!expanded && !detailedProposal && !fetchingDetail) {
              // Fetch detailed proposal when expanding for first time
              setFetchingDetail(true)
              setFetchError(null)
              try {
                const token = await getToken()
                if (!token) {
                  throw new Error('No authentication token')
                }
                const authConfig = {
                  headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                  }
                }
                console.log(`[AdvisorCard] Fetching detail for proposal ${proposal.proposal_id}`)
                console.log(`[AdvisorCard] Current proposal data:`, {
                  proposal_id: proposal.proposal_id,
                  hasStructuredExplanation: !!proposal.structured_explanation,
                  hasRiskScore: proposal.risk_score !== null && proposal.risk_score !== undefined,
                  riskScore: proposal.risk_score,
                  evidenceCount: proposal.evidence?.length || 0
                })
                
                const detailRes = await axios.get(`${API_BASE}/api/agent/proposals/${proposal.proposal_id}`, authConfig)
                
                console.log(`[AdvisorCard] Received proposal detail from API:`, {
                  proposal_id: detailRes.data.proposal_id,
                  hasStructuredExplanation: !!detailRes.data.structured_explanation,
                  structuredExplanationKeys: detailRes.data.structured_explanation ? Object.keys(detailRes.data.structured_explanation) : [],
                  factorsCount: detailRes.data.structured_explanation?.factors?.length || 0,
                  hasRiskAnalysis: !!detailRes.data.structured_explanation?.risk_analysis,
                  hasRiskScore: detailRes.data.risk_score !== null && detailRes.data.risk_score !== undefined,
                  riskScore: detailRes.data.risk_score,
                  riskScoreType: typeof detailRes.data.risk_score,
                  evidenceCount: detailRes.data.evidence?.length || 0,
                  evidenceTypes: detailRes.data.evidence?.map(e => e.evidence_type) || []
                })
                
                if (!detailRes.data.structured_explanation) {
                  console.warn(`[AdvisorCard] WARNING: No structured_explanation in API response for proposal ${proposal.proposal_id}`)
                  console.warn(`[AdvisorCard] Available evidence types:`, detailRes.data.evidence?.map(e => e.evidence_type) || [])
                }
                
                setDetailedProposal(detailRes.data)
                setExpanded(true)
              } catch (err) {
                console.error(`[AdvisorCard] Error fetching proposal detail:`, err)
                setFetchError(err.response?.data?.detail || err.message || 'Failed to fetch proposal details')
                // Still expand to show error message
                setExpanded(true)
              } finally {
                setFetchingDetail(false)
              }
            } else {
              setExpanded(!expanded)
            }
          }}
          disabled={fetchingDetail}
          className="px-4 py-2 text-gray-600 border border-gray-300 rounded hover:bg-gray-50 text-sm disabled:opacity-50"
        >
          {fetchingDetail ? 'Loading...' : expanded ? 'Hide' : 'Show'} Details
        </button>
        {expanded && (
          <button
            onClick={() => {
              setShowWhatChanged(!showWhatChanged)
              if (!showWhatChanged && !narrative) {
                fetchNarrative()
              }
            }}
            className="px-4 py-2 text-sm text-blue-600 bg-blue-50 rounded hover:bg-blue-100"
          >
            {showWhatChanged ? 'Hide Changes' : 'What Changed?'}
          </button>
        )}
      </div>
      
      {expanded && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <h5 className="text-sm font-semibold text-gray-900 mb-3">Explainability</h5>
          
          {/* Error Display */}
          {fetchError && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm">
              <div className="font-medium text-red-900 mb-1">Error Loading Details</div>
              <div className="text-red-700">{fetchError}</div>
              <div className="text-xs text-red-600 mt-2">Proposal ID: {proposal.proposal_id}</div>
            </div>
          )}
          
          {/* Use detailed proposal if available, otherwise fallback to basic proposal */}
          {(() => {
            const displayProposal = detailedProposal || proposal
            console.log(`[AdvisorCard] Rendering explainability for proposal ${proposal.proposal_id}:`, {
              hasStructuredExplanation: !!displayProposal.structured_explanation,
              structuredExplanation: displayProposal.structured_explanation,
              hasEvidence: displayProposal.evidence && displayProposal.evidence.length > 0,
              evidenceCount: displayProposal.evidence?.length || 0
            })
            
            return (
              <>
                {/* Phase 10: Structured Explanation */}
                {displayProposal.structured_explanation ? (
                  <div className="space-y-4">
                    {/* Summary */}
                    {displayProposal.structured_explanation.summary && (
                      <div className="p-3 bg-blue-50 rounded text-sm">
                        <div className="font-medium text-gray-900 mb-1">Summary</div>
                        <p className="text-gray-700">{displayProposal.structured_explanation.summary}</p>
                      </div>
                    )}
                    
                    {/* Factors */}
                    {displayProposal.structured_explanation.factors && displayProposal.structured_explanation.factors.length > 0 && (
                      <div>
                        <div className="font-medium text-gray-900 mb-2 text-sm">Key Factors</div>
                        <div className="space-y-2">
                          {displayProposal.structured_explanation.factors.map((factor, idx) => (
                            <div key={idx} className="p-2 bg-gray-50 rounded text-xs">
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-medium text-gray-900">{factor.name}</span>
                                <span className={`px-2 py-0.5 rounded text-xs ${
                                  factor.impact === 'positive' ? 'bg-green-100 text-green-700' :
                                  factor.impact === 'negative' ? 'bg-red-100 text-red-700' :
                                  'bg-gray-100 text-gray-700'
                                }`}>
                                  {factor.impact}
                                </span>
                              </div>
                              <div className="text-gray-600 mb-1">{factor.evidence}</div>
                              <div className="text-xs text-gray-500">
                                Weight: {(factor.weight * 100).toFixed(0)}%
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {/* Risk Analysis */}
                    {displayProposal.structured_explanation.risk_analysis && (
                      <div>
                        <div className="font-medium text-gray-900 mb-2 text-sm">Risk Analysis</div>
                        <div className="grid grid-cols-3 gap-2 text-xs">
                          <div className="p-2 bg-gray-50 rounded">
                            <div className="text-gray-500 mb-1">Liquidity</div>
                            <div className={`font-medium ${
                              displayProposal.structured_explanation.risk_analysis.liquidity === 'low' ? 'text-green-600' :
                              displayProposal.structured_explanation.risk_analysis.liquidity === 'medium' ? 'text-yellow-600' :
                              'text-red-600'
                            }`}>
                              {displayProposal.structured_explanation.risk_analysis.liquidity}
                            </div>
                          </div>
                          <div className="p-2 bg-gray-50 rounded">
                            <div className="text-gray-500 mb-1">Volatility</div>
                            <div className={`font-medium ${
                              displayProposal.structured_explanation.risk_analysis.volatility === 'low' ? 'text-green-600' :
                              displayProposal.structured_explanation.risk_analysis.volatility === 'medium' ? 'text-yellow-600' :
                              'text-red-600'
                            }`}>
                              {displayProposal.structured_explanation.risk_analysis.volatility}
                            </div>
                          </div>
                          <div className="p-2 bg-gray-50 rounded">
                            <div className="text-gray-500 mb-1">Market Stability</div>
                            <div className={`font-medium ${
                              displayProposal.structured_explanation.risk_analysis.market_stability === 'high' ? 'text-green-600' :
                              displayProposal.structured_explanation.risk_analysis.market_stability === 'medium' ? 'text-yellow-600' :
                              'text-red-600'
                            }`}>
                              {displayProposal.structured_explanation.risk_analysis.market_stability}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {/* Uncertainties */}
                    {displayProposal.structured_explanation.uncertainties && displayProposal.structured_explanation.uncertainties.length > 0 && (
                      <div>
                        <div className="font-medium text-gray-900 mb-2 text-sm">Uncertainties & Limitations</div>
                        <div className="space-y-1">
                          {displayProposal.structured_explanation.uncertainties.map((uncertainty, idx) => (
                            <div key={idx} className="p-2 bg-yellow-50 rounded text-xs text-yellow-800">
                              ⚠️ {uncertainty}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  /* Phase 9 Fallback: Legacy evidence display */
                  displayProposal.evidence && displayProposal.evidence.length > 0 ? (
                    <div className="space-y-3">
                      {displayProposal.evidence.map((ev, idx) => (
                        <div key={idx} className="mb-3 p-3 bg-gray-50 rounded text-sm">
                          <div className="font-medium text-gray-700 mb-1">{ev.evidence_type}</div>
                          {ev.model_explanation && (
                            <p className="text-gray-600 mb-2">{ev.model_explanation}</p>
                          )}
                          {ev.feature_contributions && Object.keys(ev.feature_contributions).length > 0 && (
                            <div className="mt-2">
                              <div className="text-xs text-gray-500 mb-1">Feature Contributions:</div>
                              <div className="space-y-1">
                                {Object.entries(ev.feature_contributions).map(([feature, value]) => (
                                  <div key={feature} className="flex justify-between text-xs">
                                    <span className="text-gray-600">{feature}:</span>
                                    <span className="font-medium">{(value * 100).toFixed(1)}%</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    /* No explanation available */
                    <div className="p-4 bg-yellow-50 border border-yellow-200 rounded text-sm">
                      <div className="font-medium text-yellow-900 mb-2">⚠️ Explanation Not Available</div>
                      <div className="text-yellow-800 text-xs space-y-1">
                        <p>No structured explanation found for this proposal.</p>
                        <p>Proposal ID: {proposal.proposal_id}</p>
                        {proposal.run_id && <p>Run ID: {proposal.run_id}</p>}
                        <p className="mt-2">This may indicate:</p>
                        <ul className="list-disc list-inside ml-2">
                          <li>Proposal was created before Phase 10 explainability was implemented</li>
                          <li>Structured explanation failed to save during agent execution</li>
                          <li>Database query did not retrieve the explanation evidence</li>
                        </ul>
                      </div>
                    </div>
                  )
                )}
                
                {/* Phase 24: What Changed Panel */}
                {showWhatChanged && (
                  <div className="mt-4">
                    <WhatChangedPanel proposalId={proposal.proposal_id} getToken={getToken} />
                  </div>
                )}
                
                {/* Phase 24: Narrative Summary */}
                {narrative && (
                  <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <div className="text-sm font-semibold text-blue-900 mb-2">Natural Language Summary</div>
                    <div className="text-sm text-blue-800">{narrative}</div>
                  </div>
                )}
              </>
            )
          })()}
        </div>
      )}

      {/* Phase 11: Simulation Modal */}
      <SimulationModal
        proposal={proposal}
        isOpen={showSimulationModal}
        onClose={() => setShowSimulationModal(false)}
        getToken={getToken}
        onSimulationCreated={handleSimulationCreated}
      />
    </div>
  )
}

