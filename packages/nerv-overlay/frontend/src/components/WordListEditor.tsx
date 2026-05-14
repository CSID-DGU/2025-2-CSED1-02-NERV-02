import { useState } from 'react'

interface Props {
  words: string[]
  onChange: (words: string[]) => void
  placeholder?: string
}

export function WordListEditor({ words, onChange, placeholder }: Props) {
  const [input, setInput] = useState('')

  const add = () => {
    const w = input.trim()
    if (!w || words.includes(w)) return
    onChange([...words, w])
    setInput('')
  }

  const remove = (w: string) => {
    onChange(words.filter((x) => x !== w))
  }

  return (
    <div className="word-list-editor">
      <div className="word-input-row">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              add()
            }
          }}
          placeholder={placeholder ?? '단어 입력 후 Enter'}
          maxLength={100}
        />
        <button type="button" onClick={add} className="btn">
          추가
        </button>
      </div>

      {words.length > 0 ? (
        <ul className="word-chips">
          {words.map((w) => (
            <li key={w} className="chip">
              <span>{w}</span>
              <button
                type="button"
                onClick={() => remove(w)}
                aria-label={`${w} 삭제`}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="empty-list">등록된 단어 없음</p>
      )}
    </div>
  )
}
