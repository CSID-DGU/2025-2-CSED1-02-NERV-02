import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { overlaysApi } from '../api/overlays'
import type { BlockDisplayMode, OverlayConfigRequest, SecurityLevel } from '../types/overlay'
import { WordListEditor } from '../components/WordListEditor'

type FormState = {
  security_level: SecurityLevel
  block_display_mode: BlockDisplayMode
  placeholder_text: string
  show_score: boolean
  whitelist: string[]
  blacklist: string[]
}

const DEFAULTS: FormState = {
  security_level: 'MEDIUM',
  block_display_mode: 'MASK',
  placeholder_text: '[필터됨]',
  show_score: false,
  whitelist: [],
  blacklist: [],
}

export function SettingsPage() {
  const qc = useQueryClient()
  const [form, setForm] = useState<FormState>(DEFAULTS)
  const [savedAt, setSavedAt] = useState<number | null>(null)

  const { data: existing } = useQuery({
    queryKey: ['overlay-active'],
    queryFn: overlaysApi.active,
  })

  useEffect(() => {
    if (existing) {
      setForm({
        security_level: existing.security_level,
        block_display_mode: existing.block_display_mode,
        placeholder_text: existing.placeholder_text,
        show_score: existing.show_score,
        whitelist: existing.whitelist,
        blacklist: existing.blacklist,
      })
    }
  }, [existing])

  const saveMut = useMutation({
    mutationFn: (req: OverlayConfigRequest) => overlaysApi.updateActive(req),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['overlay-active'] })
      setSavedAt(Date.now())
    },
  })

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    saveMut.mutate({ ...form })
  }

  return (
    <div className="page">
      <header className="header">
        <div>
          <h1>설정</h1>
          <p className="hint" style={{ marginTop: 4 }}>
            필터링 강도 · 채팅 소스 · 사용자 사전을 변경할 수 있습니다.
          </p>
        </div>
        <Link to="/" className="btn">← 메인으로</Link>
      </header>

      <form onSubmit={onSubmit} className="config-form">
        {/* ── 섹션 1: 필터 정책 ── */}
        <section className="settings-section">
          <h2 className="section-title">필터 정책</h2>
          <p className="section-desc">필터링 강도와 차단된 메시지를 어떻게 보여줄지 설정합니다.</p>

          <div className="settings-fields">
            <label>
              <span>보안 강도</span>
              <select
                value={form.security_level}
                onChange={(e) => setForm({ ...form, security_level: e.target.value as SecurityLevel })}
              >
                <option value="LOW">LOW (관대)</option>
                <option value="MEDIUM">MEDIUM (기본)</option>
                <option value="HIGH">HIGH (엄격)</option>
              </select>
            </label>

            <label>
              <span>차단 표시 방식</span>
              <select
                value={form.block_display_mode}
                onChange={(e) => setForm({ ...form, block_display_mode: e.target.value as BlockDisplayMode })}
              >
                <option value="MASK">MASK (별표)</option>
                <option value="HIDE">HIDE (완전 숨김)</option>
                <option value="PLACEHOLDER">PLACEHOLDER (대체 문구)</option>
              </select>
            </label>

            {form.block_display_mode === 'PLACEHOLDER' && (
              <label>
                <span>대체 문구</span>
                <input
                  type="text"
                  value={form.placeholder_text}
                  onChange={(e) => setForm({ ...form, placeholder_text: e.target.value })}
                  maxLength={50}
                />
              </label>
            )}

            <label className="checkbox">
              <input
                type="checkbox"
                checked={form.show_score}
                onChange={(e) => setForm({ ...form, show_score: e.target.checked })}
              />
              <span>위험도 점수 표시</span>
            </label>
          </div>
        </section>

        {/* ── 섹션 2: 사용자 사전 설정 ── */}
        <section className="settings-section">
          <h2 className="section-title">사용자 사전 설정</h2>
          <p className="section-desc">기본 사전 외에 직접 단어를 추가합니다.</p>

          <div className="dict-group">
            <h3 className="dict-subtitle">
              화이트리스트 <span>절대 차단되지 않을 단어</span>
            </h3>
            <WordListEditor
              words={form.whitelist}
              onChange={(words) => setForm({ ...form, whitelist: words })}
              placeholder="예: 시바견"
            />
          </div>

          <div className="dict-group">
            <h3 className="dict-subtitle">
              블랙리스트 <span>무조건 차단할 단어</span>
            </h3>
            <WordListEditor
              words={form.blacklist}
              onChange={(words) => setForm({ ...form, blacklist: words })}
              placeholder="예: 특정닉네임"
            />
          </div>
        </section>

        <div className="form-actions" style={{ alignItems: 'center', gap: 12 }}>
          {savedAt && (
            <span style={{ color: 'var(--color-success-text)', fontSize: 12 }}>
              ✓ 저장됨
            </span>
          )}
          <button type="submit" className="btn btn-primary" disabled={saveMut.isPending}>
            {saveMut.isPending ? '저장 중...' : '저장'}
          </button>
        </div>

        {saveMut.error && (
          <p className="error">에러: {(saveMut.error as Error).message}</p>
        )}
      </form>

    </div>
  )
}
