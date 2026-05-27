type TelemetryProperties = Record<string, boolean | number | string | null | undefined>

export function trackTelemetry(eventName: string, properties: TelemetryProperties = {}): void {
  if (typeof window === 'undefined') return
  window.dispatchEvent(
    new CustomEvent('campus-rag:telemetry', {
      detail: { eventName, properties },
    }),
  )
}

export function trackHelpdeskAgentEvent(
  eventName: string,
  properties: TelemetryProperties = {},
): void {
  trackTelemetry(`helpdesk_agent_${eventName}`, properties)
}
