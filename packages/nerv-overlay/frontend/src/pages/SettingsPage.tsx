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
  use_ai_filter: boolean
  whitelist: string[]
  blacklist: string[]
}

const DEFAULTS: FormState = {
  security_level: 'MEDIUM',
  block_display_mode: 'MASK',
  placeholder_text: '[필터됨]',
  show_score: false,
  use_ai_filter: true,
  whitelist: [],
  blacklist: [],
}

// 2차 AI 카테고리 모듈 (UI 전용 — 현재 백엔드 미연동)
const AI_MODULES: { key: string; label: string }[] = [
  { key: 'basic', label: '욕설' },
  { key: 'sexual', label: '성적' },
  { key: 'spam', label: '스팸' },
  { key: 'politics', label: '정치' },
  { key: 'pii', label: '개인정보' },
  { key: 'criticism', label: '비판' },
  { key: 'family', label: '가족' },
]

export function SettingsPage() {
  const qc = useQueryClient()
  const [form, setForm] = useState<FormState>(DEFAULTS)
  const [savedAt, setSavedAt] = useState<number | null>(null)
  // 모듈별 ON/OFF — UI 전용 (기본 전체 ON). 백엔드 저장은 아직 연동 안 함.
  const [enabledModules, setEnabledModules] = useState<string[]>(AI_MODULES.map((m) => m.key))
  const toggleModule = (key: string) =>
    setEnabledModules((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key],
    )

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
        use_ai_filter: existing.use_ai_filter,
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

          <div className="dict-group">
            <h3 className="dict-subtitle">
              AI 모듈 (2차 필터링) <span>사전 매칭으로 잡히지 않는 표현을 학습된 모델로 추가 탐지</span>
            </h3>
            <div className="ai-toggle-row">
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={form.use_ai_filter}
                  onChange={(e) => setForm({ ...form, use_ai_filter: e.target.checked })}
                />
                <span className="toggle-track" aria-hidden />
                <span className="toggle-label">
                  {form.use_ai_filter ? 'AI 필터 사용' : 'AI 필터 끔'}
                </span>
              </label>
              <p className="hint" style={{ margin: 0, fontSize: 11 }}>
                {form.use_ai_filter
                  ? '욕설·성적·스팸·정치·개인정보·비판·가족 7개 카테고리 분류기로 2차 검사합니다. 1차에서 이미 차단된 경우 호출하지 않습니다.'
                  : '2차 AI 모델을 건너뜁니다. 1차(사전+형태소) 필터만 동작합니다.'}
              </p>
            </div>

            {form.use_ai_filter && (
              <div className="ai-module-toggles" style={{ marginTop: 12 }}>
                <p className="hint" style={{ margin: '0 0 8px', fontSize: 11 }}>
                  검사할 카테고리를 선택하세요. 클릭하여 ON/OFF
                  <span style={{ marginLeft: 6, opacity: 0.7 }}>
                    ({enabledModules.length}/{AI_MODULES.length} 사용 중)
                  </span>
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {AI_MODULES.map((m) => {
                    const on = enabledModules.includes(m.key)
                    return (
                      <button
                        key={m.key}
                        type="button"
                        onClick={() => toggleModule(m.key)}
                        aria-pressed={on}
                        title={on ? `${m.label} 켜짐 (클릭하여 끄기)` : `${m.label} 꺼짐 (클릭하여 켜기)`}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 6,
                          padding: '6px 12px',
                          fontSize: 12,
                          lineHeight: 1,
                          borderRadius: 999,
                          cursor: 'pointer',
                          transition: 'all .12s ease',
                          border: on
                            ? '1px solid var(--color-accent, #6c7bff)'
                            : '1px solid var(--color-border, #3a3a44)',
                          background: on ? 'var(--color-accent, #6c7bff)' : 'transparent',
                          color: on ? '#fff' : 'var(--color-text-muted, #9a9aa6)',
                          opacity: on ? 1 : 0.65,
                        }}
                      >
                        <span aria-hidden style={{ fontSize: 9 }}>{on ? '●' : '○'}</span>
                        {m.label}
                      </button>
                    )
                  })}
                </div>
              </div>
            )}
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
