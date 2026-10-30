import { useRef } from 'react'
import { observer } from 'mobx-react-lite'
import { chatStore as store } from '../store'

const Composer = observer(function Composer() {
  const inputRef = useRef(null)

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      store.send()
    }
  }

  function handleFix() {
    store.startFix()
    inputRef.current.focus()
  }

  return (
    <div className="composer">
      <textarea
        ref={inputRef}
        value={store.draft}
        onChange={(e) => store.setDraft(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Сообщение… (Enter — отправить, Shift+Enter — новая строка)"
      />
      <div className="buttons">
        <button className="primary" onClick={store.send} disabled={!store.canSend}>
          Отправить
        </button>
        <button onClick={store.stop} disabled={!store.isRunning}>
          Остановить
        </button>
        <button onClick={handleFix} disabled={!store.canFix}>
          Исправить и отправить
        </button>
        <button className="clear" onClick={store.clear}>
          Очистить чат
        </button>
      </div>
    </div>
  )
})

export default Composer