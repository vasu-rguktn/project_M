'use client'

export default function ExecutionTimeline({ simulation }) {
  if (!simulation?.simulation_result?.execution_steps) {
    return null
  }

  const steps = simulation.simulation_result.execution_steps
  const status = simulation.status

  const getStepStatus = (step) => {
    if (status === 'EXECUTED') {
      return step.status === 'COMPLETED' ? 'completed' : 'pending'
    } else if (status === 'APPROVED') {
      return 'pending'
    } else {
      return 'pending'
    }
  }

  return (
    <div className="mt-4">
      <h4 className="text-sm font-semibold text-gray-900 mb-3">Execution Timeline</h4>
      <div className="space-y-3">
        {steps.map((step, index) => {
          const stepStatus = getStepStatus(step)
          return (
            <div key={index} className="flex items-start gap-3">
              <div className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold ${
                stepStatus === 'completed' 
                  ? 'bg-green-500 text-white' 
                  : stepStatus === 'pending'
                  ? 'bg-gray-300 text-gray-600'
                  : 'bg-yellow-500 text-white'
              }`}>
                {stepStatus === 'completed' ? '✓' : index + 1}
              </div>
              <div className="flex-1">
                <div className={`text-sm font-medium ${
                  stepStatus === 'completed' ? 'text-gray-900' : 'text-gray-600'
                }`}>
                  {step.description}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  Step {step.step}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
