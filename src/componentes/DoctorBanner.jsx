import { useEffect, useState } from 'react'

const DISMISS_KEY = 'subfactory:doctor:dismissed-v1'

function needsAttention(report) {
  if (!report) return false
  if (report.sidecarState === 'errored') return true
  return report.checks.some((c) => c.required && c.status !== 'ok')
}

function DoctorBanner() {
  const [report, setReport] = useState(null)
  const [dismissed, setDismissed] = useState(() => {
    try { return JSON.parse(localStorage.getItem('subfactory:doctor:dismissed-v1') || '[]') } catch { return [] }
  })

  useEffect(() => {
    let active = true
    let unsubReport = () => {}
    let unsubStatus = () => {}

    window.fedoSubfactory?.getDoctor().then((r) => { if (active) setReport(r) })

    unsubReport = window.fedoSubfactory?.onDoctorReport((r) => { if (active) setReport(r) })
    unsubStatus = window.fedoSubfactory?.onSidecarStatus((s) => {
      if (active && s?.state === 'errored') setReport((prev) => (prev ? { ...prev, sidecarState: 'errored' } : prev))
    })

    return () => { active = false; unsubReport(); unsubStatus() }
  }, [])

  if (!report || !needsAttention(report)) return null

  const problems = [
    ...report.checks.filter((c) => c.required && c.status !== 'ok'),
    ...(report.sidecarState === 'errored' ? [{
      id: 'sidecar', label: 'Sidecar Python', required: true, status: 'missing',
      version: null, message: 'El sidecar de procesamiento no está disponible.',
      hint: 'https://www.python.org/downloads/',
    }] : []),
  ]
  const visible = problems.filter((p) => !dismissed.includes(p.id))
  if (visible.length === 0) return null

  const dismiss = () => {
    const next = [...new Set([...dismissed, ...visible.map((p) => p.id)])]
    setDismissed(next)
    localStorage.setItem('subfactory:doctor:dismissed-v1', JSON.stringify(next))
  }

  return (
    <div role="status" className="border-b border-amber-500/40 bg-amber-500/10 px-6 py-3 text-sm text-amber-100">
      <div className="flex items-start justify-between gap-4 max-w-4xl mx-auto">
        <div className="min-w-0">
          <p className="font-semibold text-amber-200 mb-1">Faltan herramientas para Fábrica de Subtítulos</p>
          <ul className="space-y-1 text-amber-100/90">
            {visible.map((p) => (
              <li key={p.id} className="flex items-start gap-2">
                <span className="font-mono text-amber-300 shrink-0">{p.label}</span>
                <span>{p.message}</span>
                {p.hint && (
                  <a
                    href={p.hint}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline decoration-dotted underline-offset-2 hover:text-amber-50 text-xs"
                  >
                    cómo instalarlo
                  </a>
                )}
              </li>
            ))}
          </ul>
          {report.sidecarState === 'starting' && (
            <p className="mt-1 text-amber-100/70">El sidecar de procesamiento está arrancando…</p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <button
            type="button"
            onClick={() => window.fedoSubfactory?.getDoctor().then(setReport)}
            className="text-xs text-amber-100/80 hover:text-amber-50"
          >
            Reintentar
          </button>
          <button
            type="button"
            onClick={() => {
              const next = [...new Set([...dismissed, ...visible.map((p) => p.id)])]
              setDismissed(next)
              localStorage.setItem('subfactory:doctor:dismissed-v1', JSON.stringify(next))
            }}
            className="text-sm leading-none text-amber-100/60 hover:text-amber-50"
            aria-label="Cerrar aviso"
          >
            ×
          </button>
        </div>
      </div>
    </div>
  )
}

export default DoctorBanner