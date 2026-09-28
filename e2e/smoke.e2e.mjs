// Smoke test de arranque de Fábrica de Subtítulos: comprueba que el proceso
// principal de Electron arranca con la version actual, que la ventana carga el
// build del renderer y que el preload publica su API. Es la red de seguridad
// frente a regressions de API al subir de version de Electron.
//
// El smoke test no invoca el sidecar de Python a proposito: en el CI no estan
// instalados ffmpeg, Whisper ni los modelos, y el arranque de la interfaz no
// debe depender de ellos.

import { test, expect, _electron as electron } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

// Carpeta raiz del proyecto, resuelta desde la ubicacion de este archivo
const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

// Arranca la aplicacion Electron y devuelve el proceso junto a su primera ventana
async function launchApp() {
  // Lanza la app pasando la raiz del proyecto como argumento
  const app = await electron.launch({ args: [projectRoot] })
  // Espera a que aparezca la primera ventana del renderer
  const win = await app.firstWindow()
  // Devuelve el proceso y la ventana ya disponible
  return { app, win }
}

test.describe('Fábrica de Subtítulos', () => {
  test('arranca y monta la interfaz', async () => {
    // Lanza la app y toma la ventana
    const { app, win } = await launchApp()

    try {
      // Espera a que el documento termine de cargar
      await win.waitForLoadState('domcontentloaded')

      // La ventana debe tener el titulo de la app
      await expect(win).toHaveTitle(/Fábrica de Subtítulos/)

      // React debe haber montado algo dentro de #root
      await expect(win.locator('#root')).toBeAttached()
      // La raiz de la app no puede estar vacia
      const rootHtml = await win.locator('#root').innerHTML()
      // Confirma que React renderizo la interfaz
      expect(rootHtml.length).toBeGreaterThan(0)

      // La ventana principal debe existir en el proceso principal
      const windowCount = await app.evaluate(async ({ BrowserWindow }) => {
        // Devuelve cuantas ventanas existen en el proceso principal
        return BrowserWindow.getAllWindows().length
      })
      // Debe existir exactamente una ventana
      expect(windowCount).toBe(1)
    } finally {
      // Cierra siempre la app para no dejar procesos colgados
      await app.close()
    }
  })

  test('expone el puente de IPC del preload', async () => {
    // Lanza la app y toma la ventana
    const { app, win } = await launchApp()

    try {
      // Espera a que el documento termine de cargar
      await win.waitForLoadState('domcontentloaded')

      // El preload debe haber publicado window.fedoSubfactory en el renderer
      const api = await win.evaluate(() => {
        // Devuelve la forma de la API expuesta por el preload
        const puente = window.fedoSubfactory
        // Si no existe, devuelve null para que la asercion falle con clarity
        if (!puente) return null
        // Solo interesan los tipos de las funciones, no su comportamiento
        return {
          enviarComando: typeof puente.enviarComando,
          onEvento: typeof puente.onEvento
        }
      })
      // Confirma que el puente de IPC existe
      expect(api).not.toBeNull()
      // enviarComando debe ser una funcion utilizable
      expect(api.enviarComando).toBe('function')
      // onEvento debe ser una funcion utilizable
      expect(api.onEvento).toBe('function')
    } finally {
      // Cierra siempre la app
      await app.close()
    }
  })

  test('no registra errores de JavaScript al arrancar', async () => {
    // Lanza la app y toma la ventana
    const { app, win } = await launchApp()

    try {
      // Recoge los errores de la pagina que aparezcan tras cargar
      const errores = []
      // Escucha los errores no capturados del renderer
      win.on('pageerror', (err) => errores.push(String(err)))

      // Fuerza una recarga para observar el arranque completo
      await win.reload()
      // Espera a que el documento termine de cargar
      await win.waitForLoadState('domcontentloaded')
      // Margen para que se dispare algun error asincrono tardio
      await win.waitForTimeout(2000)

      // Ningun error de JavaScript debe haber aparecido
      expect(errores).toEqual([])
    } finally {
      // Cierra siempre la app
      await app.close()
    }
  })
})
