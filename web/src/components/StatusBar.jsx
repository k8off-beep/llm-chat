import { observer } from 'mobx-react-lite'
import { chatStore as store } from '../store'

const PHASE_TEXT = {
  waiting: 'Ожидание ответа модели…',
  generating: 'Модель генерирует ответ…',
}

const StatusBar = observer(function StatusBar() {
  const text =
    store.phase === 'tool'
      ? `Выполняется инструмент ${store.toolName}…`
      : PHASE_TEXT[store.phase] || ''

  return <div className="status">{text}</div>
})

export default StatusBar