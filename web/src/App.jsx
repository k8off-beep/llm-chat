import { observer } from 'mobx-react-lite'
import { chatStore as store } from './store'

const App = observer(function App() {
  return (
    <main>
      <h1>LLM-чат</h1>
      {store.messages.map((m) => (
        <pre key={m.id}>
          {m.role}: {m.text} [{m.status}] {m.error}
        </pre>
      ))}
      <p>Состояние: {store.phase} {store.toolName}</p>
      <textarea value={store.draft} onChange={(e) => store.setDraft(e.target.value)} />
      <button onClick={store.send} disabled={!store.canSend}>Отправить</button>
      <button onClick={store.stop} disabled={!store.isRunning}>Остановить</button>
      <button onClick={store.startFix} disabled={!store.canFix}>Исправить и отправить</button>
      <button onClick={store.clear}>Очистить чат</button>
    </main>
  )
})

export default App