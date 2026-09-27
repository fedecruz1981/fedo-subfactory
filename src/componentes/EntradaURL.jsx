import { useState } from 'react'

export default function EntradaURL ({ onAgregar }) {
  const [texto, setTexto] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    const urls = texto.split('\n').filter((u) => u.trim())
    if (urls.length === 0) return
    onAgregar(urls)
    setTexto('')
  }

  return (
    <form onSubmit={handleSubmit} className="px-6 py-4 border-b border-linea">
      <div className="flex gap-3">
        <textarea
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="Pega uno o varios links de video (uno por línea)..."
          className="flex-1 bg-panel border border-linea rounded-lg px-4 py-3 text-sm
                     focus:outline-none focus:border-magenta resize-none h-20
                     placeholder-gray-500"
        />
        <button
          type="submit"
          disabled={!texto.trim()}
          className="px-6 py-3 bg-magenta hover:bg-magenta/80 disabled:opacity-30
                     disabled:cursor-not-allowed rounded-lg font-medium text-sm
                     transition-colors"
        >
          Agregar
        </button>
      </div>
    </form>
  )
}
