from app.schemas.evaluation import CompactEvaluationOutput


def evaluation_output() -> CompactEvaluationOutput:
    dimension = {"score": 3, "feedback": "전사문에서 과업 수행 근거가 확인됩니다."}
    base_answer = [
        "I would like to talk about a peaceful park located near my home.",
        "I usually visit this park on weekends when I need some fresh air.",
        "The park has a wide walking trail that circles a small lake.",
        "There are many tall trees, so the whole area feels cool and quiet.",
        "My favorite spot is a wooden bench beside the clean walking path.",
        "I often sit there for a while and watch families enjoying their time.",
        "Sometimes I take a slow walk while listening to music through my earphones.",
        "The calm atmosphere helps me forget stress from school and daily routines.",
        "I especially enjoy the park in the evening because the sunset looks beautiful.",
        "For these reasons, this nearby park is one of my favorite places.",
    ]
    higher_answer = [
        "One of my favorite places is a peaceful neighborhood park near my home.",
        "I first discovered it several years ago while exploring the area with friends.",
        "Since then, I have visited whenever I need a quiet break from work.",
        "A broad walking trail surrounds a small lake in the center of the park.",
        "Tall trees line the path and provide plenty of shade during warm afternoons.",
        "My favorite area is a wooden bench beside a garden filled with flowers.",
        "From there, I can watch families, runners, and people walking their dogs.",
        "I normally take a slow stroll before sitting down and listening to music.",
        "That simple routine helps me clear my head and feel completely refreshed.",
        "The park becomes even more attractive in the evening when the sun sets.",
        "The orange light reflects on the lake and creates a warm atmosphere.",
        "Although it is not a famous destination, it feels meaningful and comfortable.",
        "That is why I continue to choose this park whenever I need rest.",
    ]
    return CompactEvaluationOutput.model_validate(
        {
            "level": "IM2",
            "confidence": "medium",
            "confidenceWhy": "문항과 제한된 지표를 사용한 연습용 추정입니다.",
            "summary": "핵심 내용은 전달되며 구체성과 연결성을 더하면 좋습니다.",
            "dims": {
                "task": dimension,
                "content": dimension,
                "organization": dimension,
                "timeFrames": dimension,
                "grammar": dimension,
                "vocabulary": dimension,
                "fluency": dimension,
            },
            "delivery": {
                "fluency": dimension,
                "accuracy": dimension,
                "naturalness": dimension,
                "mainPoint": {
                    "status": "clear_early",
                    "feedback": "초반에 중심 내용을 제시했습니다.",
                },
                "feelings": ["I really enjoy it"],
                "markers": {"functional": ["Honestly"], "disruptive": []},
            },
            "phrases": [
                {
                    "context": "장소의 분위기 소개",
                    "phrase": "It has a laid-back atmosphere.",
                    "usage": "편안한 분위기를 자연스럽게 설명합니다.",
                },
                {
                    "context": "개인적인 반응",
                    "phrase": "It helps me clear my head.",
                    "usage": "장소가 주는 효과를 말합니다.",
                },
            ],
            "vocab": [
                {
                    "category": "topic",
                    "phrase": "walking trail",
                    "meaning": "산책로",
                    "why": "공원의 구체적인 특징을 말할 수 있습니다.",
                    "example": "The walking trail goes around the lake.",
                },
                {
                    "category": "feeling",
                    "phrase": "feel refreshed",
                    "meaning": "상쾌해지다",
                    "why": "방문 후 감정을 설명할 수 있습니다.",
                    "example": "I feel refreshed after a short walk.",
                },
                {
                    "category": "action",
                    "phrase": "take a stroll",
                    "meaning": "산책하다",
                    "why": "공원에서 하는 행동에 적합합니다.",
                    "example": "I usually take a stroll in the evening.",
                },
            ],
            "strengths": [
                {
                    "title": "명확한 주제",
                    "explanation": "좋아하는 장소를 분명히 소개했습니다.",
                    "evidence": "I like this park",
                }
            ],
            "blocker": {
                "title": "세부 근거",
                "explanation": "구체적인 경험과 이유가 부족합니다.",
                "evidence": "I go there sometimes",
            },
            "corrections": [
                {
                    "original": "I go there yesterday.",
                    "corrected": "I went there yesterday.",
                    "explanation": "과거 시제를 사용합니다.",
                }
            ],
            "missions": [
                "중심 내용을 먼저 말하기",
                "구체적인 행동 추가하기",
                "이유로 마무리하기",
            ],
            "nextQuestionType": "past_experience",
            "baseAnswer": base_answer,
            "higherAnswer": higher_answer,
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
