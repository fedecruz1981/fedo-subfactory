import { useState, useEffect, useCallback } from 'react'
import EntradaURL from './componentes/EntradaURL'
import ColaJobs from './componentes/ColaJobs'
import Configuracion from './componentes/Configuracion'

const CONFIGURACION_DEFAULT = {
  modelo_whisper: 'medium',
  dispositivo: 'cpu',
  motor_traduccion: 'llm',
  llm_proveedor: 'gemini',
  llm_api_key: '',
  llm_modelo: 'gemini-3.6-flash',
  formato_salida: 'srt',
  carpeta_destino: '',
  max_paralelo: 1
}

export default function App () {
  const [jobs, setJobs] = useState([])
  const [config, setConfig] = useState(CONFIGURACION_DEFAULT)
  const [mostrarConfig, setMostrarConfig] = useState(false)

  useEffect(() => {
    if (window.fedoSubfactory) {
      window.fedoSubfactory.onEvento((evento) => {
        if (evento.stage === 'pending_resume') {
          setJobs((prev) => {
            if (prev.find((j) => j.id === evento.job_id)) return prev
            return [...prev, {
              id: evento.job_id,
              url: evento.url || '',
              estado: 'pending_resume',
              progreso: 0,
              mensaje: evento.message || 'Interrumpido',
              logs: [`[resumen] ${evento.message || ''}`],
              ruta_salida: null,
              error: null,
              titulo: evento.titulo || ''
            }]
          })
          return
        }
        setJobs((prev) => prev.map((job) => {
          if (job.id !== evento.job_id) return job
          return {
            ...job,
            estado: evento.stage,
            progreso: evento.progress || job.progreso,
            mensaje: evento.message || job.mensaje,
            logs: [...job.logs, `[${evento.stage}] ${evento.message || ''}`],
            ruta_salida: evento.output_path || job.ruta_salida,
            error: evento.stage === 'error' ? evento.message : null
          }
        }))
      })

      window.fedoSubfactory.enviarComando({ cmd: 'load_pending' })
    }
  }, [])

  const agregarJobs = useCallback((urls) => {
    const nuevosJobs = urls.map((url, i) => ({
      id: `job_${Date.now()}_${i}`,
      url: url.trim(),
      estado: 'en_cola',
      progreso: 0,
      mensaje: 'En cola...',
      logs: [],
      ruta_salida: null,
      error: null
    }))

    setJobs((prev) => [...prev, ...nuevosJobs])

    nuevosJobs.forEach((job) => {
      if (window.fedoSubfactory) {
        window.fedoSubfactory.enviarComando({
          cmd: 'process_job',
          job_id: job.id,
          url: job.url,
          config
        })
      }
    })
  }, [config])

  const cancelarJob = useCallback((jobId) => {
    if (window.fedoSubfactory) {
      window.fedoSubfactory.enviarComando({ cmd: 'cancel_job', job_id: jobId })
    }
    setJobs((prev) => prev.map((job) =>
      job.id === jobId ? { ...job, estado: 'cancelado', mensaje: 'Cancelado por el usuario' } : job
    ))
  }, [])

  const reintentarJob = useCallback((jobId) => {
    const job = jobs.find((j) => j.id === jobId)
    if (!job) return

    setJobs((prev) => prev.map((j) =>
      j.id === jobId ? { ...j, estado: 'en_cola', progreso: 0, mensaje: 'Reintentando...', error: null, logs: [] } : j
    ))

    if (window.fedoSubfactory) {
      window.fedoSubfactory.enviarComando({
        cmd: 'process_job',
        job_id: jobId,
        url: job.url,
        config
      })
    }
  }, [jobs, config])

  const retomarJob = useCallback((jobId) => {
    const job = jobs.find((j) => j.id === jobId)
    if (!job) return

    setJobs((prev) => prev.map((j) =>
      j.id === jobId ? { ...j, estado: 'en_cola', progreso: 0, mensaje: 'Retomando...', error: null } : j
    ))

    if (window.fedoSubfactory) {
      window.fedoSubfactory.enviarComando({
        cmd: 'resume_job',
        job_id: jobId,
        config
      })
    }
  }, [jobs, config])

  const limpiarJobs = useCallback(() => {
    setJobs((prev) => prev.filter((j) => !['error', 'listo', 'done', 'cancelado', 'pending_resume'].includes(j.estado)))
  }, [])

  const jobsActivos = jobs.filter((j) => !['listo', 'error', 'cancelado'].includes(j.estado)).length

  return (
    <div className="h-screen flex flex-col bg-void">
      <header className="flex items-center justify-between px-6 py-4 border-b border-linea">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-magenta animate-pulse" />
          <h1 className="text-xl font-display text-gradient tracking-wider">
            Fábrica de Subtítulos
          </h1>
        </div>

        <div className="flex items-center gap-4">
          {jobsActivos > 0 && (
            <span className="text-xs text-cyan">
              {jobsActivos} activo{jobsActivos !== 1 ? 's' : ''}
            </span>
          )}
          <button
            onClick={() => setMostrarConfig(!mostrarConfig)}
            className="text-sm text-gray-400 hover:text-cyan transition-colors px-3 py-1.5
                       border border-linea rounded-lg hover:border-cyan/30"
          >
            {mostrarConfig ? '✕ Cerrar' : '⚙ Ajustes'}
          </button>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <main className="flex-1 flex flex-col overflow-hidden">
          <EntradaURL onAgregar={agregarJobs} />

          <ColaJobs
            jobs={jobs}
            onCancelar={cancelarJob}
            onReintentar={reintentarJob}
            onRetomar={retomarJob}
            onLimpiar={limpiarJobs}
          />
        </main>

        {mostrarConfig && (
          <Configuracion
            config={config}
            onChange={setConfig}
            onCerrar={() => setMostrarConfig(false)}
          />
        )}
      </div>
    </div>
  )
}
