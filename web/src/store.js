import { makeAutoObservable } from 'mobx'
import { readSse } from './sse'

let nextId = 1

class ChatStore {
  messages = []
  draft = ''
  conversationId = null
  runId = null
  phase = 'idle' // idle | waiting | generating | tool
  toolName = null
  canFix = false
  controller = null

  constructor() {
    makeAutoObservable(this, { controller: false }, { autoBind: true })
  }

  get isRunning() {
    return this.phase !== 'idle'
  }

  get canSend() {
    return !this.isRunning && this.draft.trim() !== ''
  }

  setDraft(text) {
    this.draft = text
  }

  async send() {
    if (!this.canSend) return
    const text = this.draft.trim()
    this.draft = ''
    this.canFix = false

    this.messages.push({ id: nextId++, role: 'user', text })
    this.messages.push({ id: nextId++, role: 'assistant', text: '', status: 'streaming', error: null })
    const answer = this.messages[this.messages.length - 1]

    this.phase = 'waiting'
    this.runId = null
    const controller = new AbortController()
    this.controller = controller

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, conversation_id: this.conversationId }),
        signal: controller.signal,
      })
      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new Error(body.detail || `Ошибка сервера: ${response.status}`)
      }
      await readSse(response, (event, data) => this.handleEvent(controller, answer, event, data))

      if (controller === this.controller) {
        this.fail(answer, 'Соединение с сервером прервалось.')
      }
    } catch (err) {
      if (controller !== this.controller) return
      if (err.name === 'AbortError') {
        answer.status = 'cancelled'
        this.canFix = true
        this.finish()
      } else {
        this.fail(answer, err.message || 'Нет связи с сервером.')
      }
    }
  }

  handleEvent(controller, answer, event, data) {
    if (controller !== this.controller) return // событие от старого запроса

    if (event === 'start') {
      this.runId = data.run_id
      this.conversationId = data.conversation_id
      return
    }
    if (data.run_id !== this.runId) return

    if (event === 'delta') {
      answer.text += data.text
      this.phase = 'generating'
    } else if (event === 'tool') {
      if (data.status === 'running') {
        this.phase = 'tool'
        this.toolName = data.name
      } else {
        this.phase = 'waiting'
        this.toolName = null
      }
    } else if (event === 'done') {
      answer.status = 'done'
      this.finish()
    } else if (event === 'cancelled') {
      answer.status = 'cancelled'
      this.canFix = true
      this.finish()
    } else if (event === 'error') {
      this.fail(answer, data.message)
    }
  }

  fail(answer, message) {
    answer.status = 'error'
    answer.error = message
    this.canFix = true
    this.finish()
  }

  finish() {
    this.phase = 'idle'
    this.toolName = null
    this.runId = null
    this.controller = null
  }

  async stop() {
    if (!this.isRunning) return
    if (this.runId) {
      await fetch(`/api/runs/${this.runId}/cancel`, { method: 'POST' }).catch(() => {})
    } else {
      this.controller?.abort()
    }
  }

  startFix() {
    if (!this.canFix || this.messages.length < 2) return
    const lastUser = this.messages[this.messages.length - 2]
    this.draft = lastUser.text
    this.messages.splice(-2, 2)
    this.canFix = false
  }

  clear() {
    if (this.runId) {
      fetch(`/api/runs/${this.runId}/cancel`, { method: 'POST' }).catch(() => {})
    }
    const controller = this.controller
    this.controller = null
    controller?.abort()

    this.messages = []
    this.draft = ''
    this.conversationId = null
    this.runId = null
    this.phase = 'idle'
    this.toolName = null
    this.canFix = false
  }
}

export const chatStore = new ChatStore()