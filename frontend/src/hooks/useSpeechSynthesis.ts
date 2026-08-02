import { useCallback, useEffect, useState } from 'react'

export const useSpeechSynthesis = () => {
  const [speaking, setSpeaking] = useState(false)

  const cancel = useCallback(() => {
    window.speechSynthesis?.cancel()
    setSpeaking(false)
  }, [])

  const speak = useCallback(
    (text: string) => {
      if (!window.speechSynthesis) return
      cancel()
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = 'en-US'
      utterance.rate = 0.92
      utterance.onstart = () => setSpeaking(true)
      utterance.onend = () => setSpeaking(false)
      utterance.onerror = () => setSpeaking(false)
      window.speechSynthesis.speak(utterance)
    },
    [cancel],
  )

  useEffect(() => cancel, [cancel])

  return { speak, cancel, speaking }
}

