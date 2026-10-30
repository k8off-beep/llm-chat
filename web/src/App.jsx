import Composer from './components/Composer'
import MessageList from './components/MessageList'
import StatusBar from './components/StatusBar'

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>LLM-чат</h1>
      </header>
      <MessageList />
      <StatusBar />
      <Composer />
    </div>
  )
}