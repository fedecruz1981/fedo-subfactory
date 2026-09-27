const PROVEEDORES_LLM = {
  groq: {
    nombre: 'Groq (gratis, rápido)',
    apiKeyUrl: 'console.groq.com/keys',
    modelos: [
      { id: 'llama-3.3-70b-versatile', nombre: 'Llama 3.3 70B — mejor calidad' },
      { id: 'llama-3.1-8b-instant', nombre: 'Llama 3.1 8B — más rápido' },
      { id: 'mixtral-8x7b-32768', nombre: 'Mixtral 8x7B' },
      { id: 'gemma2-9b-it', nombre: 'Gemma 2 9B' },
    ]
  },
  gemini: {
    nombre: 'Google Gemini (gratis)',
    apiKeyUrl: 'aistudio.google.com',
    modelos: [
      { id: 'gemini-3.6-flash', nombre: 'Gemini 3.6 Flash — recomendado' },
      { id: 'gemini-3.5-flash', nombre: 'Gemini 3.5 Flash' },
      { id: 'gemini-3.7-flash', nombre: 'Gemini 3.7 Flash' },
    ]
  },
  openai: {
    nombre: 'OpenAI (pago)',
    apiKeyUrl: 'platform.openai.com/api-keys',
    modelos: [
      { id: 'gpt-4o-mini', nombre: 'GPT-4o Mini — barato' },
      { id: 'gpt-4o', nombre: 'GPT-4o — mejor calidad' },
      { id: 'gpt-3.5-turbo', nombre: 'GPT-3.5 Turbo — más barato' },
    ]
  }
}

export default function Configuracion ({ config, onChange, onCerrar }) {
  const actualizar = (campo, valor) => {
    onChange({ ...config, [campo]: valor })
  }

  const esLLM = config.motor_traduccion === 'llm'
  const proveedor = config.llm_proveedor || 'groq'
  const infoProveedor = PROVEEDORES_LLM[proveedor]
  const modelosDisponibles = infoProveedor?.modelos || []

  return (
    <aside className="w-80 border-l border-linea bg-panel p-6 overflow-y-auto">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-sm font-medium text-gray-300">Configuración</h2>
        <button onClick={onCerrar} className="text-gray-500 hover:text-white text-sm">✕</button>
      </div>

      <div className="space-y-5">
        <div>
          <label className="block text-xs text-gray-400 mb-2">Modelo Whisper</label>
          <select
            value={config.modelo_whisper}
            onChange={(e) => actualizar('modelo_whisper', e.target.value)}
            className="w-full bg-void border border-linea rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-magenta"
          >
            <option value="tiny">tiny (39 MB) — rápido</option>
            <option value="base">base (74 MB)</option>
            <option value="small">small (244 MB)</option>
            <option value="medium">medium (769 MB)</option>
            <option value="large-v3">large-v3 (1.5 GB) — mejor calidad</option>
          </select>
        </div>

        <div>
          <label className="block text-xs text-gray-400 mb-2">Dispositivo</label>
          <select
            value={config.dispositivo}
            onChange={(e) => actualizar('dispositivo', e.target.value)}
            className="w-full bg-void border border-linea rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-magenta"
          >
            <option value="cpu">CPU</option>
            <option value="cuda">GPU (CUDA)</option>
          </select>
        </div>

        <div className="border-t border-linea pt-4">
          <label className="block text-xs text-gray-400 mb-2">Traducción al español</label>
          <select
            value={config.motor_traduccion}
            onChange={(e) => actualizar('motor_traduccion', e.target.value)}
            className="w-full bg-void border border-linea rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-magenta"
          >
            <option value="llm">LLM — mejor contexto</option>
            <option value="google">Google Translate (gratis, online)</option>
            <option value="nllb">NLLB-200 (offline, sin internet)</option>
          </select>
        </div>

        {esLLM && (
          <>
            <div>
              <label className="block text-xs text-gray-400 mb-2">Proveedor LLM</label>
              <select
                value={proveedor}
                onChange={(e) => {
                  actualizar('llm_proveedor', e.target.value)
                  const nuevosModelos = PROVEEDORES_LLM[e.target.value]?.modelos
                  if (nuevosModelos?.length) {
                    actualizar('llm_modelo', nuevosModelos[0].id)
                  }
                }}
                className="w-full bg-void border border-linea rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-magenta"
              >
                <option value="groq">Groq (gratis, sin tarjeta)</option>
                <option value="gemini">Google Gemini (gratis, sin tarjeta)</option>
                <option value="openai">OpenAI (pago)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs text-gray-400 mb-2">Modelo</label>
              <select
                value={config.llm_modelo || modelosDisponibles[0]?.id || ''}
                onChange={(e) => actualizar('llm_modelo', e.target.value)}
                className="w-full bg-void border border-linea rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-magenta"
              >
                {modelosDisponibles.map((m) => (
                  <option key={m.id} value={m.id}>{m.nombre}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs text-gray-400 mb-2">API Key</label>
              <input
                type="password"
                value={config.llm_api_key || ''}
                onChange={(e) => actualizar('llm_api_key', e.target.value)}
                placeholder="Pega tu API key aquí..."
                className="w-full bg-void border border-linea rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-magenta placeholder-gray-600"
              />
              <div className="text-xs text-gray-500 mt-2 space-y-1">
                {proveedor === 'groq' && (
                  <>
                    <p>1. Andá a <span className="text-cyan">console.groq.com/keys</span></p>
                    <p>2. Creá cuenta con tu email (sin tarjeta)</p>
                    <p>3. Click "Create API Key" → copiá la key</p>
                  </>
                )}
                {proveedor === 'gemini' && (
                  <>
                    <p>1. Andá a <span className="text-cyan">aistudio.google.com</span></p>
                    <p>2. Click "Get API Key" → elegí tu cuenta Google</p>
                    <p>3. Click "Create API Key" → copiá la key</p>
                  </>
                )}
                {proveedor === 'openai' && (
                  <>
                    <p>1. Andá a <span className="text-cyan">platform.openai.com/api-keys</span></p>
                    <p>2. Creá cuenta y agregá método de pago</p>
                    <p>3. Click "Create new secret key" → copiá la key</p>
                  </>
                )}
              </div>
            </div>

            <p className="text-xs text-gray-500 bg-void rounded-lg p-2">
              Se agrupan 10 segmentos por lote con contexto del lote anterior para mantener coherencia.
            </p>
          </>
        )}

        <div className="border-t border-linea pt-4">
          <label className="block text-xs text-gray-400 mb-2">Formato de salida</label>
          <select
            value={config.formato_salida}
            onChange={(e) => actualizar('formato_salida', e.target.value)}
            className="w-full bg-void border border-linea rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-magenta"
          >
            <option value="srt">Solo .srt</option>
            <option value="video">Video con subtítulos incrustados</option>
          </select>
        </div>

        <div>
          <label className="block text-xs text-gray-400 mb-2">Carpeta de destino</label>
          <input
            type="text"
            value={config.carpeta_destino}
            onChange={(e) => actualizar('carpeta_destino', e.target.value)}
            placeholder="(usa carpeta temporal por defecto)"
            className="w-full bg-void border border-linea rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-magenta placeholder-gray-600"
          />
        </div>

        <div>
          <label className="block text-xs text-gray-400 mb-2">Trabajos en paralelo</label>
          <input
            type="number"
            min="1"
            max="4"
            value={config.max_paralelo}
            onChange={(e) => actualizar('max_paralelo', parseInt(e.target.value) || 1)}
            className="w-full bg-void border border-linea rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-magenta"
          />
        </div>
      </div>
    </aside>
  )
}
