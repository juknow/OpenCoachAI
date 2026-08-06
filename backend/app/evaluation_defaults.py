from app.schemas.common import PracticeLevel, QuestionType
from app.schemas.evaluation import EstimatedRange, ReusableStructureStep

LEVELS = list(PracticeLevel)


def estimated_range_for(level: PracticeLevel) -> EstimatedRange:
    index = LEVELS.index(level)
    return EstimatedRange(
        lower=LEVELS[max(0, index - 1)],
        upper=LEVELS[min(len(LEVELS) - 1, index + 1)],
    )


STRUCTURES: dict[QuestionType, list[tuple[str, str]]] = {
    QuestionType.DESCRIPTION: [
        ("핵심 소개", "대상을 한 문장으로 분명하게 소개합니다."),
        ("구체적 특징", "보이는 특징과 분위기를 구체적으로 설명합니다."),
        ("개인적 의미", "좋아하는 이유나 개인적인 반응으로 마무리합니다."),
    ],
    QuestionType.ROUTINE: [
        ("일과 개요", "언제 무엇을 하는지 먼저 요약합니다."),
        ("순서와 빈도", "행동의 순서와 빈도를 구체적으로 말합니다."),
        ("이유와 느낌", "그 습관의 이유와 효과를 덧붙입니다."),
    ],
    QuestionType.PAST_EXPERIENCE: [
        ("배경", "언제 어디서 누구와 있었는지 밝힙니다."),
        ("사건 전개", "핵심 사건을 시간 순서대로 설명합니다."),
        ("결과와 반응", "결과, 감정, 배운 점으로 마무리합니다."),
    ],
    QuestionType.COMPARISON_CHANGE: [
        ("비교 대상", "비교할 두 대상이나 과거와 현재를 소개합니다."),
        ("핵심 차이", "구체적인 차이를 근거와 함께 설명합니다."),
        ("평가", "더 선호하는 쪽과 이유를 분명하게 말합니다."),
    ],
    QuestionType.ROLE_PLAY: [
        ("상황 확인", "역할과 필요한 목적을 자연스럽게 밝힙니다."),
        ("필수 질문", "요청된 정보를 빠짐없이 질문하거나 전달합니다."),
        ("마무리", "확인, 감사, 다음 행동으로 대화를 끝냅니다."),
    ],
    QuestionType.PROBLEM_SOLUTION: [
        ("문제 설명", "발생한 문제와 영향을 분명하게 설명합니다."),
        ("해결책 제시", "실행 가능한 해결책을 하나 이상 제안합니다."),
        ("결과 확인", "원하는 결과와 후속 행동을 확인합니다."),
    ],
}


def reusable_structure_for(question_type: QuestionType) -> list[ReusableStructureStep]:
    return [
        ReusableStructureStep(step=index, title_korean=title, explanation_korean=explanation)
        for index, (title, explanation) in enumerate(STRUCTURES[question_type], start=1)
    ]


SAFETY_NOTICE = (
    "이 결과는 한 문항의 전사문과 제한된 브라우저 음성 지표를 바탕으로 한 "
    "연습용 예상치이며 공식 OPIc 점수가 아닙니다."
)
