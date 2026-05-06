import React from 'react'
import ReactDOM from 'react-dom/client'
import './styles.css'

const phases = [
  ['MVP 1', 'Backend started', 'FastAPI, index-folder, search, ask, SQLite registry, Chroma and Ollama integration.'],
  ['MVP 2', 'Pending', 'Office extensions, image metadata, filters and desktop UI prototype.'],
  ['MVP 3', 'Pending', 'RAG citations, file watcher and incremental background indexing.'],
  ['Production Local', 'Pending', 'Installer, OCR, logs, backup and offline packaging.'],
]

function App() {
  return (
    <main className="container">
      <section className="hero">
        <span className="badge">Project progress · MVP 1 started</span>
        <h1>Local AI Semantic Search Agent</h1>
        <p className="lead">
          Local-first AI system for semantic search over PDF, Office files, text files,
          image metadata and private document repositories.
        </p>
        <a className="button" href="https://github.com/viggo2040/local-ai-semantic-search">
          View repository
        </a>
      </section>

      <section>
        <h2>Current implementation</h2>
        <div className="grid grid-2">
          <article className="card"><h3>Backend API</h3><p>FastAPI service with health, indexing, search and ask endpoints.</p></article>
          <article className="card"><h3>Indexing</h3><p>Initial support for TXT, Markdown, CSV, PDF and DOCX.</p></article>
          <article className="card"><h3>Vector store</h3><p>Persistent local Chroma collection for document chunks.</p></article>
          <article className="card"><h3>Local AI</h3><p>Ollama integration for embeddings and RAG answer generation.</p></article>
        </div>
      </section>

      <section>
        <h2>Implemented endpoints</h2>
        <pre className="code">{`GET  /health
POST /index-folder
POST /search
POST /ask`}</pre>
      </section>

      <section>
        <h2>Roadmap</h2>
        <div className="grid">
          {phases.map(([phase, status, description]) => (
            <article className="card" key={phase}>
              <h3>{phase} · {status}</h3>
              <p>{description}</p>
            </article>
          ))}
        </div>
      </section>

      <section>
        <h2>Architecture</h2>
        <pre className="code">{`Local files
→ Extractors
→ Chunking
→ Ollama embeddings
→ Chroma vector store
→ Semantic search
→ RAG answer generation`}</pre>
      </section>
    </main>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />)
