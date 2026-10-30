import { observer } from 'mobx-react-lite'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkBreaks from "remark-breaks"

function Link({ href, children }) {
  return (
    <a href={href} target="_blank" rel="noreferrer">
      {children}
    </a>
  )
}

const Message = observer(function Message({ message }) {
  if (message.role === 'user') {
    return <div className="message user">{message.text}</div>
  }

  return (
    <div className="message assistant">
      {message.text ? (
        <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} components={{ a: Link }}>
          {message.text}
        </ReactMarkdown>
      ) : (
        message.status === 'streaming' && <span className="typing">…</span>
      )}
      {message.status === 'cancelled' && <div className="message-note">Остановлено</div>}
      {message.status === 'error' && <div className="message-note error">Ошибка: {message.error}</div>}
    </div>
  )
})

export default Message