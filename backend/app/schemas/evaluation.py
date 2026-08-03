from typing import Annotated, Literal

from pydantic import Field, field_validator

from app.schemas.common import (
    ApiModel,
    Confidence,
    PracticeLevel,
    QuestionType,
    ResponseMetadata,
)

Difficulty = Literal["easy", "medium", "hard"]


class UserProfile(ApiModel):
    target_level: Literal["IM2", "IM3", "IH", "AL"]
    current_level: Literal["unknown", "IM1", "IM2", "IM3", "IH"]
    occupation: Literal["student", "worker", "unemployed"]
    residence: Literal["family", "alone", "dorm", "other"]
    interests: list[str] = Field(max_length=9)
    difficulty: Difficulty


class PracticeQuestion(ApiModel):
    id: str
    type: QuestionType
    topic: str
    difficulty: Difficulty
    question: str
    korean_translation: str
    required_elements: list[str] = Field(min_length=1, max_length=8)
    related_topics: list[str] = Field(max_length=8)


class WordCount(ApiModel):
    word: str
    count: int = Field(ge=1)


class AcousticMetrics(ApiModel):
    initial_response_delay_seconds: float = Field(ge=0, le=120)
    hesitation_pause_count: int = Field(ge=0)
    long_pause_count: int = Field(ge=0)
    silence_ratio: float = Field(ge=0, le=100)
    energy_variation_index: float = Field(ge=0, le=100)
    confidence: Literal["low", "medium"]


class SpeechMetrics(ApiModel):
    duration_seconds: float = Field(gt=0, le=120.5)
    word_count: int = Field(ge=0)
    words_per_minute: int = Field(ge=0, le=500)
    filler_words: list[WordCount] = Field(max_length=12)
    repeated_phrases: list[str] = Field(max_length=5)
    functional_discourse_markers: list[WordCount] = Field(max_length=12)
    filler_rate_per_100_words: float = Field(ge=0, le=100)
    opening_20_second_estimate: str = Field(max_length=3000)
    acoustic: AcousticMetrics


class DimensionScoreSet(ApiModel):
    task_completion: int = Field(ge=0, le=4)
    content_specificity: int = Field(ge=0, le=4)
    discourse_organization: int = Field(ge=0, le=4)
    time_frame_control: int = Field(ge=0, le=4)
    grammar_control: int = Field(ge=0, le=4)
    vocabulary_range: int = Field(ge=0, le=4)
    fluency_comprehensibility: int = Field(ge=0, le=4)


class PreviousAttempt(ApiModel):
    level: PracticeLevel
    dimension_scores: DimensionScoreSet
    primary_blocker: str
    retry_mission: list[str] = Field(min_length=3, max_length=3)


class EvaluationRequest(ApiModel):
    profile: UserProfile
    question: PracticeQuestion
    attempt_number: Literal[1, 2]
    transcript: str = Field(min_length=1, max_length=12_000)
    speech_metrics: SpeechMetrics
    previous_attempt: PreviousAttempt | None = None

    @field_validator("transcript")
    @classmethod
    def transcript_must_contain_speech(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("transcript must not be blank")
        return value


class DimensionEvaluation(ApiModel):
    score: int = Field(ge=0, le=4)
    reason: str = Field(min_length=1, max_length=500)


class DimensionEvaluations(ApiModel):
    task_completion: DimensionEvaluation
    content_specificity: DimensionEvaluation
    discourse_organization: DimensionEvaluation
    time_frame_control: DimensionEvaluation
    grammar_control: DimensionEvaluation
    vocabulary_range: DimensionEvaluation
    fluency_comprehensibility: DimensionEvaluation


class MainPointEvaluation(ApiModel):
    status: Literal["clear_early", "late", "missing", "uncertain"]
    first_20_seconds_estimate: str = Field(max_length=3000)
    feedback_korean: str = Field(min_length=1, max_length=500)


class FeelingLanguageEvaluation(ApiModel):
    expressions: list[str] = Field(max_length=4)
    feedback_korean: str = Field(min_length=1, max_length=500)


class DiscourseMarkersEvaluation(ApiModel):
    functional: list[str] = Field(max_length=4)
    disruptive: list[str] = Field(max_length=4)
    feedback_korean: str = Field(min_length=1, max_length=500)


class ConversationalDelivery(ApiModel):
    fluency: DimensionEvaluation
    accuracy: DimensionEvaluation
    naturalness: DimensionEvaluation
    main_point: MainPointEvaluation
    feeling_language: FeelingLanguageEvaluation
    discourse_markers: DiscourseMarkersEvaluation


class NaturalPhraseSuggestion(ApiModel):
    context_korean: str
    phrase_english: str
    usage_korean: str


class RecommendedVocabulary(ApiModel):
    category: Literal["topic", "feeling", "action", "connector"]
    word_or_phrase_english: str
    meaning_korean: str
    why_recommended_korean: str
    example_sentence_english: str


class Evidence(ApiModel):
    title: str
    explanation_korean: str
    evidence_from_transcript: str


class Correction(ApiModel):
    original: str
    corrected: str
    explanation_korean: str


ShortKorean = Annotated[str, Field(min_length=1, max_length=180)]
SummaryKorean = Annotated[str, Field(min_length=1, max_length=260)]
ShortEnglish = Annotated[str, Field(min_length=1, max_length=240)]
TagText = Annotated[str, Field(min_length=1, max_length=80)]


class CompactDimension(ApiModel):
    score: int = Field(ge=0, le=4)
    feedback: ShortKorean


class CompactDimensions(ApiModel):
    task: CompactDimension
    content: CompactDimension
    organization: CompactDimension
    time_frames: CompactDimension
    grammar: CompactDimension
    vocabulary: CompactDimension
    fluency: CompactDimension


class CompactMainPoint(ApiModel):
    status: Literal["clear_early", "late", "missing", "uncertain"]
    feedback: ShortKorean


class CompactMarkers(ApiModel):
    functional: list[TagText] = Field(max_length=4)
    disruptive: list[TagText] = Field(max_length=4)


class CompactDelivery(ApiModel):
    fluency: CompactDimension
    accuracy: CompactDimension
    naturalness: CompactDimension
    main_point: CompactMainPoint
    feelings: list[TagText] = Field(max_length=4)
    markers: CompactMarkers


class CompactPhrase(ApiModel):
    context: Annotated[str, Field(min_length=1, max_length=100)]
    phrase: Annotated[str, Field(min_length=1, max_length=120)]
    usage: ShortKorean


class CompactVocabulary(ApiModel):
    category: Literal["topic", "feeling", "action", "connector"]
    phrase: Annotated[str, Field(min_length=1, max_length=100)]
    meaning: Annotated[str, Field(min_length=1, max_length=80)]
    why: ShortKorean
    example: ShortEnglish


class CompactEvidence(ApiModel):
    title: Annotated[str, Field(min_length=1, max_length=80)]
    explanation: ShortKorean
    evidence: Annotated[str, Field(min_length=1, max_length=180)]


class CompactCorrection(ApiModel):
    original: ShortEnglish
    corrected: ShortEnglish
    explanation: ShortKorean


class CompactEvaluationCore(ApiModel):
    level: PracticeLevel
    confidence: Confidence
    confidence_why: ShortKorean
    summary: SummaryKorean
    dims: CompactDimensions
    delivery: CompactDelivery
    phrases: list[CompactPhrase] = Field(min_length=2, max_length=2)
    vocab: list[CompactVocabulary] = Field(min_length=3, max_length=3)
    strengths: list[CompactEvidence] = Field(max_length=3)
    blocker: CompactEvidence
    corrections: list[CompactCorrection] = Field(max_length=5)
    missions: list[ShortKorean] = Field(min_length=3, max_length=3)


class CompactEvaluationV2Output(CompactEvaluationCore):
    base_answer: list[ShortEnglish] = Field(min_length=10, max_length=12)


class CompactEvaluationOutput(CompactEvaluationCore):
    next_question_type: QuestionType
    base_answer: list[ShortEnglish] = Field(min_length=10, max_length=12)
    higher_answer: list[ShortEnglish] = Field(min_length=12, max_length=15)


class CompactHigherAnswerOutput(ApiModel):
    sentences: list[ShortEnglish] = Field(min_length=12, max_length=15)


class EvaluationModelOutput(ApiModel):
    most_likely_level: PracticeLevel
    confidence: Confidence
    confidence_reason: str
    summary_korean: str
    dimensions: DimensionEvaluations
    conversational_delivery: ConversationalDelivery
    natural_phrase_suggestions: list[NaturalPhraseSuggestion] = Field(min_length=2, max_length=2)
    recommended_vocabulary: list[RecommendedVocabulary] = Field(min_length=3, max_length=3)
    strengths: list[Evidence] = Field(max_length=3)
    limitations: list[Evidence] = Field(max_length=3)
    primary_level_blocker: Evidence
    corrections: list[Correction] = Field(max_length=5)
    retry_mission: list[str] = Field(min_length=3, max_length=3)
    recommended_next_question_type: QuestionType
    minimal_correction_sentences: list[str] = Field(min_length=10, max_length=12)
    next_level_sentences: list[str] = Field(min_length=12, max_length=15)


class EstimatedRange(ApiModel):
    lower: PracticeLevel
    upper: PracticeLevel


class ReusableStructureStep(ApiModel):
    step: int = Field(ge=1)
    title_korean: str
    explanation_korean: str


class EvaluationResult(EvaluationModelOutput):
    estimated_range: EstimatedRange
    reusable_structure: list[ReusableStructureStep]
    safety_notice_korean: str


class EvaluationResponse(ApiModel):
    evaluation: EvaluationResult
    metadata: ResponseMetadata


class EvaluationV2MainPoint(ApiModel):
    status: Literal["clear_early", "late", "missing", "uncertain"]
    feedback_korean: str = Field(min_length=1, max_length=500)


class EvaluationV2Delivery(ApiModel):
    fluency: DimensionEvaluation
    accuracy: DimensionEvaluation
    naturalness: DimensionEvaluation
    main_point: EvaluationV2MainPoint
    feeling_expressions: list[str] = Field(max_length=4)
    functional_markers: list[str] = Field(max_length=4)
    disruptive_markers: list[str] = Field(max_length=4)


class ImprovementAnswerResult(ApiModel):
    variant: Literal["core", "next"]
    sentences: list[ShortEnglish] = Field(min_length=10, max_length=15)
    sentence_count: int = Field(ge=10, le=15)
    word_count: int = Field(ge=1)


class EvaluationV2Result(ApiModel):
    most_likely_level: PracticeLevel
    estimated_range: EstimatedRange
    confidence: Confidence
    confidence_reason: str
    summary_korean: str
    dimensions: DimensionEvaluations
    conversational_delivery: EvaluationV2Delivery
    natural_phrase_suggestions: list[NaturalPhraseSuggestion] = Field(
        min_length=2, max_length=2
    )
    recommended_vocabulary: list[RecommendedVocabulary] = Field(min_length=3, max_length=3)
    strengths: list[Evidence] = Field(max_length=3)
    primary_level_blocker: Evidence
    corrections: list[Correction] = Field(max_length=5)
    retry_mission: list[str] = Field(min_length=3, max_length=3)
    base_answer: ImprovementAnswerResult
    reusable_structure: list[ReusableStructureStep]
    safety_notice_korean: str


class EvaluationV2Response(ApiModel):
    evaluation: EvaluationV2Result
    metadata: ResponseMetadata


class HigherAnswerProfile(ApiModel):
    target_level: Literal["IM2", "IM3", "IH", "AL"]
    current_level: Literal["unknown", "IM1", "IM2", "IM3", "IH"]


class HigherAnswerQuestion(ApiModel):
    type: QuestionType
    topic: str = Field(min_length=1, max_length=200)
    question: str = Field(min_length=1, max_length=2_000)


class HigherAnswerRequest(ApiModel):
    profile: HigherAnswerProfile
    question: HigherAnswerQuestion
    transcript: str = Field(min_length=1, max_length=12_000)
    most_likely_level: PracticeLevel
    base_answer: list[ShortEnglish] = Field(min_length=10, max_length=12)

    @field_validator("transcript")
    @classmethod
    def higher_transcript_must_contain_speech(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("transcript must not be blank")
        return value


class HigherAnswerResponse(ApiModel):
    answer: ImprovementAnswerResult
    metadata: ResponseMetadata
