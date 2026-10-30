import { useEffect, useRef } from 'react'
import { observer } from 'mobx-react-lite'
import { chatStore as store } from '../store'
import Message from './Message'

const MessageList = observer(function MessageList() {
  const listRef = useRef(null)
  const count = store.messages.length
  const lastText = store.messages.at(-1)?.text

  useEffect(() => {
    const list = listRef.current
    list.scrollTop = list.scrollHeight
  }, [count, lastText])

  return (
    <div className="messages" ref={listRef}>
      {count === 0 && <div className="empty">Начните диалог: задайте вопрос, попросите найти подматрицу или узнать о продажах.</div>}
      {store.messages.map((m) => (
        <Message key={m.id} message={m} />
      ))}
    </div>
  )
})

export default MessageList