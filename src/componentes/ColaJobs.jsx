import TarjetaJob from './TarjetaJob'

export default function ColaJobs ({ jobs, onCancelar, onReintentar, onRetomar, onLimpiar }) {
  if (jobs.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-500">
        <div className="text-center">
          <p className="text-lg mb-2">Sin trabajos en cola</p>
          <p className="text-sm">Pega links de video arriba para comenzar</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-3">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-sm text-gray-400">
          {jobs.length} trabajo{jobs.length !== 1 ? 's' : ''} en cola
        </h2>
        <button
          onClick={onLimpiar}
          className="text-xs text-gray-500 hover:text-magenta transition-colors"
        >
          Limpiar completados
        </button>
      </div>

      {jobs.map((job) => (
        <TarjetaJob
          key={job.id}
          job={job}
          onCancelar={onCancelar}
          onReintentar={onReintentar}
          onRetomar={onRetomar}
        />
      ))}
    </div>
  )
}
