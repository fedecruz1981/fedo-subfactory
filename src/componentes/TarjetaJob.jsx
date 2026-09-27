import { useState } from 'react'

const CONFIG_ESTADO = {
  en_cola:       { color: 'text-gray-400',   bg: 'bg-gray-400/10',   label: 'En cola',         icono: '◌' },
  descargando:   { color: 'text-cyan',       bg: 'bg-cyan/10',       label: 'Descargando',     icono: '⬇' },
  downloading:   { color: 'text-cyan',       bg: 'bg-cyan/10',       label: 'Descargando',     icono: '⬇' },
  transcribing:  { color: 'text-amber',      bg: 'bg-amber/10',      label: 'Transcribiendo',  icono: '🎙' },
  transcribiendo:{ color: 'text-amber',      bg: 'bg-amber/10',      label: 'Transcribiendo',  icono: '🎙' },
  translating:   { color: 'text-magenta',    bg: 'bg-magenta/10',    label: 'Traduciendo',     icono: '🌐' },
  traduciendo:   { color: 'text-magenta',    bg: 'bg-magenta/10',    label: 'Traduciendo',     icono: '🌐' },
  renderizando:  { color: 'text-cyan',       bg: 'bg-cyan/10',       label: 'Renderizando',    icono: '🎬' },
  resuming:      { color: 'text-amber',      bg: 'bg-amber/10',      label: 'Retomando...',    icono: '↻' },
  pending_resume:{ color: 'text-amber',      bg: 'bg-amber/10',      label: 'Interrumpido',    icono: '↻' },
  done:          { color: 'text-green-400',  bg: 'bg-green-400/10',  label: 'Listo',           icono: '✓' },
  listo:         { color: 'text-green-400',  bg: 'bg-green-400/10',  label: 'Listo',           icono: '✓' },
  error:         { color: 'text-red-400',    bg: 'bg-red-400/10',    label: 'Error',           icono: '✕' },
  cancelado:     { color: 'text-gray-500',   bg: 'bg-gray-500/10',   label: 'Cancelado',       icono: '—' },
}

export default function TarjetaJob ({ job, onCancelar, onReintentar, onRetomar }) {
  const [mostrarLogs, setMostrarLogs] = useState(false)
  const cfg = CONFIG_ESTADO[job.estado] || CONFIG_ESTADO.en_cola
  const activo = !['listo', 'done', 'error', 'cancelado', 'pending_resume'].includes(job.estado)

  return (
    <div className={`bg-panel border rounded-lg p-4 transition-all duration-300 glow-hover
                     ${job.estado === 'error' ? 'border-red-400/30' : 'border-linea'}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.color} ${cfg.bg}`}>
              {cfg.icono} {cfg.label}
            </span>
            {activo && <div className="spinner" />}
          </div>

          <p className="text-sm text-gray-300 truncate" title={job.url}>
            {job.url}
          </p>

          {job.mensaje && !job.error && (
            <p className="text-xs text-gray-500 mt-1">{job.mensaje}</p>
          )}

          {activo && job.progreso > 0 && (
            <div className="mt-3">
              <div className="progress-bar w-full bg-void h-1.5">
                <div
                  className="h-1.5 rounded-full transition-all duration-500 ease-out"
                  style={{
                    width: `${Math.min(100, job.progreso)}%`,
                    background: 'linear-gradient(90deg, #23E6C9, #FF2F6E)'
                  }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-1">{Math.round(job.progreso)}%</p>
            </div>
          )}

          {job.error && (
            <p className="text-xs text-red-400 mt-2 bg-red-400/5 px-2 py-1 rounded">
              {job.error}
            </p>
          )}

          {job.ruta_salida && (
            <p className="text-xs text-green-400 mt-2 truncate" title={job.ruta_salida}>
              📁 {job.ruta_salida}
            </p>
          )}
        </div>

        <div className="flex gap-2 shrink-0">
          {job.estado === 'error' && (
            <button
              onClick={() => onReintentar(job.id)}
              className="text-xs text-amber hover:text-amber/80 transition-colors px-2 py-1
                         border border-amber/20 rounded hover:border-amber/40"
            >
              Reintentar
            </button>
          )}
          {job.estado === 'pending_resume' && (
            <button
              onClick={() => onRetomar(job.id)}
              className="text-xs text-green-400 hover:text-green-400/80 transition-colors px-2 py-1
                         border border-green-400/20 rounded hover:border-green-400/40"
            >
              Retomar
            </button>
          )}
          {activo && (
            <button
              onClick={() => onCancelar(job.id)}
              className="text-xs text-gray-500 hover:text-magenta transition-colors px-2 py-1
                         border border-linea rounded hover:border-magenta/30"
            >
              Cancelar
            </button>
          )}
          <button
            onClick={() => setMostrarLogs(!mostrarLogs)}
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors px-2 py-1"
          >
            {mostrarLogs ? '▾' : '▸'} Logs
          </button>
        </div>
      </div>

      {mostrarLogs && job.logs.length > 0 && (
        <div className="mt-3 bg-void rounded-lg p-3 max-h-40 overflow-y-auto border border-linea">
          {job.logs.map((log, i) => (
            <p key={i} className="text-xs text-gray-400 font-mono leading-relaxed">{log}</p>
          ))}
        </div>
      )}
    </div>
  )
}
