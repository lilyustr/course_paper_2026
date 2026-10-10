export function riskColor(operationalRisk) {
  if (operationalRisk === 'SHORTAGE_RISK') return '#dc2626'
  if (operationalRisk === 'OVERFLOW_RISK') return '#f59e0b'
  if (operationalRisk === 'NONE' || operationalRisk === 'NORMAL') return '#16a34a'
  return '#64748b'
}
