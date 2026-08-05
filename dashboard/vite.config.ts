import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

// Serve each city's graph straight from the repo's single source of truth
// (data/<city>/graph.json) so the dashboard never carries a stale copy. The
// engine data dir lives one level above the dashboard, so a normal public/
// file won't reach it.
const cityGraphsPlugin: Plugin = {
  name: 'city-graphs',
  configureServer(server) {
    server.middlewares.use('/graphs', (req, res, next) => {
      const m = req.url?.match(/^\/([a-zA-Z0-9_-]+)\/graph\.json$/)
      if (!m) return next()
      const file = path.join(repoRoot, 'data', m[1], 'graph.json')
      if (!fs.existsSync(file)) {
        res.statusCode = 404
        res.end('Not found')
        return
      }
      res.setHeader('Content-Type', 'application/json')
      fs.createReadStream(file).pipe(res)
    })
  },
}

export default defineConfig({
  plugins: [cityGraphsPlugin, react()],
  server: {
    fs: { allow: [repoRoot] },
  },
})
