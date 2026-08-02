import { useState } from 'react'
import type { Difficulty, PracticeProfile } from '../types/coach.ts'

const interestOptions = [
  ['movie', '영화'], ['music', '음악'], ['game', '게임'], ['park', '공원'],
  ['exercise', '운동'], ['cafe', '카페'], ['domestic-travel', '국내여행'],
  ['overseas-travel', '해외여행'], ['staycation', '집에서 보내는 휴가'],
]

interface ProfileSetupPageProps {
  initialProfile: PracticeProfile | null
  onBack: () => void
  onSave: (profile: PracticeProfile) => void
}

export function ProfileSetupPage({ initialProfile, onBack, onSave }: ProfileSetupPageProps) {
  const [profile, setProfile] = useState<PracticeProfile>(
    initialProfile ?? {
      targetLevel: 'IH',
      currentLevel: 'unknown',
      identity: 'student',
      residence: 'family',
      interests: ['park', 'overseas-travel'],
      difficulty: 'medium',
    },
  )

  const toggleInterest = (value: string) => {
    setProfile((current) => ({
      ...current,
      interests: current.interests.includes(value)
        ? current.interests.filter((interest) => interest !== value)
        : [...current.interests, value],
    }))
  }

  return (
    <main className="profile-page page-shell">
      <button className="back-button" type="button" onClick={onBack}>← 이전</button>
      <header className="page-intro centered">
        <span className="eyebrow">STEP 1</span>
        <h1>연습 프로필을 설정해 주세요</h1>
        <p>목표와 관심 주제에 맞는 문제를 추천하는 데 사용해요. 언제든 바꿀 수 있습니다.</p>
      </header>

      <form className="profile-card" onSubmit={(event) => { event.preventDefault(); onSave(profile) }}>
        <div className="profile-grid">
          <label>목표 등급
            <select value={profile.targetLevel} onChange={(event) => setProfile({ ...profile, targetLevel: event.target.value as PracticeProfile['targetLevel'] })}>
              <option>IM2</option><option>IM3</option><option>IH</option><option>AL</option>
            </select>
          </label>
          <label>현재 예상 등급
            <select value={profile.currentLevel} onChange={(event) => setProfile({ ...profile, currentLevel: event.target.value as PracticeProfile['currentLevel'] })}>
              <option value="unknown">모름</option><option>IM1</option><option>IM2</option><option>IM3</option><option>IH</option>
            </select>
          </label>
          <label>신분
            <select value={profile.identity} onChange={(event) => setProfile({ ...profile, identity: event.target.value as PracticeProfile['identity'] })}>
              <option value="student">학생</option><option value="worker">직장인</option><option value="job_seeker">취업 준비생</option>
            </select>
          </label>
          <label>거주 형태
            <select value={profile.residence} onChange={(event) => setProfile({ ...profile, residence: event.target.value as PracticeProfile['residence'] })}>
              <option value="family">가족과 거주</option><option value="alone">혼자 거주</option><option value="dormitory">기숙사</option><option value="other">기타</option>
            </select>
          </label>
        </div>

        <fieldset className="choice-group">
          <legend>관심 주제 <small>여러 개 선택할 수 있어요</small></legend>
          <div className="choice-chips">
            {interestOptions.map(([value, label]) => (
              <button key={value} className={profile.interests.includes(value) ? 'selected' : ''} type="button" onClick={() => toggleInterest(value)}>
                {profile.interests.includes(value) && <span>✓</span>} {label}
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset className="choice-group">
          <legend>연습 난이도</legend>
          <div className="difficulty-selector">
            {([['easy', '쉬움'], ['medium', '보통'], ['hard', '어려움']] as Array<[Difficulty, string]>).map(([value, label]) => (
              <button key={value} className={profile.difficulty === value ? 'selected' : ''} type="button" onClick={() => setProfile({ ...profile, difficulty: value })}>{label}</button>
            ))}
          </div>
        </fieldset>

        <button className="button primary profile-submit" type="submit" disabled={profile.interests.length === 0}>
          프로필 저장하고 시작하기 →
        </button>
      </form>
    </main>
  )
}

