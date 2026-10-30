import { useEffect, useState } from 'react'

export default function App() {
  const [ping, setPing] = useState('...')

  useEffect(() => {
    fetch('/api/ping')
      .then((response) => response.json())
      .then((data) => setPing(data.answer))
      .catch(() => setPing('агент недоступен'))
  }, [])

  return (
    <main>
      <h1>LLM-чат</h1>
      <p>Агент отвечает: {ping}</p>
    </main>
  )
}