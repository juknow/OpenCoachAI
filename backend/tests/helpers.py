from app.schemas.evaluation import EvaluationModelOutput


def evaluation_output() -> EvaluationModelOutput:
    dimension = {"score": 3, "reason": "전사문에서 과업 수행 근거가 확인됩니다."}
    sentences = [f"This is a clear practice sentence number {index}." for index in range(1, 13)]
    next_sentences = [
        f"This is a more developed practice sentence number {index}." for index in range(1, 14)
    ]
    return EvaluationModelOutput.model_validate(
        {
            "mostLikelyLevel": "IM2",
            "confidence": "medium",
            "confidenceReason": "한 문항과 제한된 지표를 사용한 연습용 추정입니다.",
            "summaryKorean": "핵심 내용은 전달되며 구체성을 더하면 좋습니다.",
            "dimensions": {
                "taskCompletion": dimension,
                "contentSpecificity": dimension,
                "discourseOrganization": dimension,
                "timeFrameControl": dimension,
                "grammarControl": dimension,
                "vocabularyRange": dimension,
                "fluencyComprehensibility": dimension,
            },
            "conversationalDelivery": {
                "fluency": dimension,
                "accuracy": dimension,
                "naturalness": dimension,
                "mainPoint": {
                    "status": "clear_early",
                    "first20SecondsEstimate": "I like this park because it is quiet.",
                    "feedbackKorean": "초반에 중심 내용을 제시했습니다.",
                },
                "feelingLanguage": {
                    "expressions": ["I really enjoy it"],
                    "feedbackKorean": "감정 표현이 의미를 보탭니다.",
                },
                "discourseMarkers": {
                    "functional": ["Honestly"],
                    "disruptive": [],
                    "feedbackKorean": "연결 표현을 제한적으로 사용했습니다.",
                },
            },
            "naturalPhraseSuggestions": [
                {
                    "contextKorean": "장소의 분위기 소개",
                    "phraseEnglish": "It has a laid-back atmosphere.",
                    "usageKorean": "편안한 분위기를 자연스럽게 설명합니다.",
                },
                {
                    "contextKorean": "개인적인 반응",
                    "phraseEnglish": "It helps me clear my head.",
                    "usageKorean": "장소가 주는 효과를 말합니다.",
                },
            ],
            "recommendedVocabulary": [
                {
                    "category": "topic",
                    "wordOrPhraseEnglish": "walking trail",
                    "meaningKorean": "산책로",
                    "whyRecommendedKorean": "공원의 구체적인 특징을 말할 수 있습니다.",
                    "exampleSentenceEnglish": "The walking trail goes around the lake.",
                },
                {
                    "category": "feeling",
                    "wordOrPhraseEnglish": "feel refreshed",
                    "meaningKorean": "상쾌해지다",
                    "whyRecommendedKorean": "방문 후 감정을 설명할 수 있습니다.",
                    "exampleSentenceEnglish": "I feel refreshed after a short walk.",
                },
                {
                    "category": "action",
                    "wordOrPhraseEnglish": "take a stroll",
                    "meaningKorean": "산책하다",
                    "whyRecommendedKorean": "공원에서 하는 행동에 적합합니다.",
                    "exampleSentenceEnglish": "I usually take a stroll in the evening.",
                },
            ],
            "strengths": [
                {
                    "title": "명확한 주제",
                    "explanationKorean": "좋아하는 장소를 분명히 소개했습니다.",
                    "evidenceFromTranscript": "I like this park",
                }
            ],
            "limitations": [
                {
                    "title": "구체성 부족",
                    "explanationKorean": "세부 활동을 더 설명할 수 있습니다.",
                    "evidenceFromTranscript": "It is nice",
                }
            ],
            "primaryLevelBlocker": {
                "title": "세부 근거",
                "explanationKorean": "구체적인 경험과 이유가 부족합니다.",
                "evidenceFromTranscript": "I go there sometimes",
            },
            "corrections": [
                {
                    "original": "I go there yesterday.",
                    "corrected": "I went there yesterday.",
                    "explanationKorean": "과거 시제를 사용합니다.",
                }
            ],
            "retryMission": [
                "중심 내용 먼저 말하기",
                "구체적인 활동 추가하기",
                "느낌으로 마무리하기",
            ],
            "recommendedNextQuestionType": "past_experience",
            "minimalCorrectionSentences": sentences[:10],
            "nextLevelSentences": next_sentences,
        }
    )


def evaluation_request() -> dict[str, object]:
    return {
        "profile": {
            "targetLevel": "IH",
            "currentLevel": "IM2",
            "occupation": "student",
            "residence": "family",
            "interests": ["parks"],
            "difficulty": "medium",
        },
        "question": {
            "id": "description-01",
            "type": "description",
            "topic": "park",
            "difficulty": "medium",
            "question": "Describe a park you like.",
            "koreanTranslation": "좋아하는 공원을 설명해 주세요.",
            "requiredElements": ["Describe a park you like."],
            "relatedTopics": ["park"],
        },
        "attemptNumber": 1,
        "transcript": "Um, I like this park because it is quiet. It is nice.",
        "speechMetrics": {
            "durationSeconds": 30,
            "wordCount": 12,
            "wordsPerMinute": 24,
            "fillerWords": [{"word": "um", "count": 1}],
            "repeatedPhrases": [],
            "functionalDiscourseMarkers": [],
            "fillerRatePer100Words": 8.3,
            "opening20SecondEstimate": "Um, I like this park because it is quiet.",
            "acoustic": {
                "initialResponseDelaySeconds": 0.5,
                "hesitationPauseCount": 1,
                "longPauseCount": 0,
                "silenceRatio": 20,
                "energyVariationIndex": 40,
                "confidence": "medium",
            },
        },
        "previousAttempt": None,
    }
