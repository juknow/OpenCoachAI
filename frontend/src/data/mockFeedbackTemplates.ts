import type {
  ExpressionSuggestion,
  QuestionType,
  VocabularySuggestion,
} from '../types/coach.ts'

export interface MockFeedbackTemplate {
  transcript: { first: string; retry: string }
  headline: string
  summary: string
  mainPointLabel: string
  mainPointFeedback: string
  expressions: ExpressionSuggestion[]
  vocabulary: VocabularySuggestion[]
  blocker: { title: string; detail: string }
  reusableStructure: string[]
  retryMission: string[]
  coreSentences: string[]
  nextSentences: string[]
}

const vocabulary = (
  topic: [string, string, string],
  feeling: [string, string, string],
  action: [string, string, string],
): VocabularySuggestion[] => [
  {
    category: 'topic',
    phrase: topic[0],
    meaning: topic[1],
    guidance: '질문의 중심 소재를 더 구체적으로 설명할 때 사용하세요.',
    example: topic[2],
  },
  {
    category: 'feeling',
    phrase: feeling[0],
    meaning: feeling[1],
    guidance: '개인적인 느낌과 반응을 자연스럽게 덧붙일 때 사용하세요.',
    example: feeling[2],
  },
  {
    category: 'action',
    phrase: action[0],
    meaning: action[1],
    guidance: '행동이나 변화를 반복 없이 설명할 때 사용하세요.',
    example: action[2],
  },
]

export const MOCK_FEEDBACK_TEMPLATES: Record<QuestionType, MockFeedbackTemplate> = {
  description: {
    transcript: {
      first: "Um, I want to talk about {topic}. It's, uh, a place I know pretty well. It is nice and there are many things. I go there sometimes because I like it. The place is comfortable, but I don't know how to explain everything.",
      retry: "I'd like to describe {topic}. It has a welcoming atmosphere and several useful features. First, the layout is easy to understand. Also, there are a few details that make the place memorable. I usually spend time there with friends, and I feel relaxed whenever I visit.",
    },
    headline: '핵심 장소를 제시했지만, 위치·모습·개인적인 이유를 더 선명하게 연결하면 답변이 한 단계 좋아집니다.',
    summary: '주제는 이해되지만 비슷한 형용사가 반복되어 장면이 구체적으로 그려지지 않습니다.',
    mainPointLabel: '중심 장소는 제시됨',
    mainPointFeedback: '첫 문장에 장소와 전체 인상을 함께 말한 뒤, 보이는 특징 두 가지를 바로 붙여 보세요.',
    expressions: [
      { situation: '전체 인상을 먼저 말할 때', expression: 'What stands out most is the welcoming atmosphere.', guidance: '묘사의 방향을 첫 문장에서 분명히 잡아 줍니다.' },
      { situation: '세부 특징을 연결할 때', expression: 'Another thing I really like is how easy it is to get around.', guidance: '두 번째 특징과 개인적인 이유를 자연스럽게 묶습니다.' },
    ],
    vocabulary: vocabulary(
      ['well-designed layout', '잘 설계된 배치', '{topic} has a well-designed layout.'],
      ['welcoming atmosphere', '편안하게 맞아 주는 분위기', 'The welcoming atmosphere makes people feel at ease.'],
      ['spend time at my own pace', '내 속도대로 시간을 보내다', 'I can spend time there at my own pace.'],
    ),
    blocker: { title: '구체적인 감각 정보 부족', detail: 'nice, good 같은 일반적인 표현 대신 보이는 모습과 실제 행동을 붙여야 합니다.' },
    reusableStructure: ['한 문장 Main Point', '보이는 특징 두세 가지', '개인적인 이유와 느낌'],
    retryMission: ['첫 문장에 장소와 전체 인상을 함께 말하세요.', '위치·시설·분위기 중 두 가지를 구체화하세요.', '마지막에 내가 이곳을 좋아하는 이유를 말하세요.'],
    coreSentences: [
      'I would like to describe {topic}.', 'It is one of the places I know best.', 'The area is easy to find and convenient to visit.', 'Inside, the layout is simple and well organized.', 'There are several useful facilities for visitors.', 'The atmosphere is usually calm and welcoming.', 'I often go there when I need a comfortable break.', 'I especially like the small details in the space.', 'They make the place feel more personal and memorable.', 'That is why {topic} is special to me.',
    ],
    nextSentences: [
      'I would like to tell you about {topic}, which is one of my favorite places.', 'The first thing people notice is its welcoming atmosphere.', 'The space has a well-designed layout, so it is easy to move around.', 'There are useful facilities in every part of the place.', 'The lighting and colors make the interior feel comfortable.', 'It can become lively, but it rarely feels confusing.', 'I normally visit when I want to take a break from my routine.', 'Sometimes I meet friends there, and sometimes I go alone.', 'Either way, I can spend time at my own pace.', 'I also appreciate how clean and well maintained it is.', 'Those practical details make every visit enjoyable.', 'For these reasons, I would gladly recommend {topic} to other people.',
    ],
  },
  routine: {
    transcript: {
      first: 'Well, my routine for {topic} is pretty simple. First, I get ready and, um, I check what I need. Then I do it for a while. Sometimes I take a break, and after that I finish everything. I usually feel good when it is done.',
      retry: 'My routine for {topic} follows a clear order. I prepare what I need first, and then I focus on the main task. I usually take one short break so I can keep my energy. After I finish, I check the result and get ready for the next day.',
    },
    headline: '행동 순서는 보이지만 빈도, 시간대와 이유를 더하면 일상적인 답변이 훨씬 자연스러워집니다.',
    summary: 'first와 then은 사용했지만 각 행동이 언제, 얼마나 자주 일어나는지 충분히 설명하지 않았습니다.',
    mainPointLabel: '기본 순서는 제시됨',
    mainPointFeedback: '보통 시작하는 시간과 가장 중요한 행동을 첫 20초 안에 말해 보세요.',
    expressions: [
      { situation: '평소 빈도를 말할 때', expression: 'Most of the time, I stick to the same routine.', guidance: '반복되는 습관임을 자연스럽게 알려 줍니다.' },
      { situation: '예외를 덧붙일 때', expression: 'If I am short on time, I simplify a few steps.', guidance: '일과가 달라지는 조건을 설명할 수 있습니다.' },
    ],
    vocabulary: vocabulary(
      ['daily routine', '일상적인 습관', 'This daily routine helps me stay organized.'],
      ['feel productive', '생산적이라고 느끼다', 'I feel productive after I finish everything.'],
      ['stick to a schedule', '일정을 지키다', 'I try to stick to a schedule during the week.'],
    ),
    blocker: { title: '시간과 빈도 정보 부족', detail: '행동 목록만 나열하지 말고 언제, 얼마나 자주, 왜 하는지 연결해야 합니다.' },
    reusableStructure: ['시작 시간과 빈도', '행동 순서와 연결어', '예외 상황과 효과'],
    retryMission: ['usually와 시간 표현을 첫 문장에 넣으세요.', 'first, after that, finally로 세 단계를 연결하세요.', '이 습관이 나에게 주는 효과를 마지막에 말하세요.'],
    coreSentences: [
      'I usually follow the same routine for {topic}.', 'I start by preparing everything I need.', 'First, I check my schedule and set a simple goal.', 'Then I focus on the most important task.', 'I normally work without distractions for a while.', 'After that, I take a short break.', 'The break helps me recover my energy.', 'Finally, I check what I have completed.', 'This routine keeps me organized during the day.', 'It also helps me feel productive.',
    ],
    nextSentences: [
      'Most of the time, I stick to a regular routine for {topic}.', 'I begin at a similar time because consistency helps me focus.', 'Before I start, I prepare the tools and information I need.', 'First, I deal with the task that requires the most attention.', 'Then I move on to smaller and easier steps.', 'I take a short break before I become too tired.', 'During the break, I stretch or get something to drink.', 'After that, I return with better concentration.', 'If I am short on time, I simplify a few steps.', 'However, I always try to finish the most important part.', 'At the end, I review the result and plan the next day.', 'This routine gives my day a clear and comfortable rhythm.',
    ],
  },
  past_experience: {
    transcript: {
      first: 'Uh, I remember an experience about {topic}. It happened a while ago when I was with someone. At first, everything was normal, but then something unexpected happened. I was surprised and, um, we tried to handle it. In the end, it was okay and I still remember it.',
      retry: 'One memorable experience involving {topic} happened last year. I was with a close friend when an unexpected problem changed our plan. At first we were worried, but we discussed our options and acted quickly. In the end, the situation worked out, and I learned to stay calm.',
    },
    headline: '사건의 시작과 결과는 있지만, 결정적인 순간과 감정 변화를 더 구체적으로 보여 줄 필요가 있습니다.',
    summary: '과거 시제는 사용했지만 누가 무엇을 했는지와 사건의 원인·결과 연결이 약합니다.',
    mainPointLabel: '사건의 방향은 제시됨',
    mainPointFeedback: '언제, 누구와 있었는지 말한 뒤 가장 중요한 사건을 구체적인 동사로 설명하세요.',
    expressions: [
      { situation: '예상 밖의 전환을 말할 때', expression: 'Just when we thought everything was going smoothly, things changed.', guidance: '사건의 전환점을 자연스럽게 강조합니다.' },
      { situation: '경험의 의미를 마무리할 때', expression: 'Looking back, it taught me to stay calm under pressure.', guidance: '과거 경험과 현재의 교훈을 연결합니다.' },
    ],
    vocabulary: vocabulary(
      ['turning point', '전환점', 'That moment became the turning point of the experience.'],
      ['feel relieved', '안도감을 느끼다', 'I felt relieved when the problem was solved.'],
      ['deal with the situation', '상황에 대처하다', 'We worked together to deal with the situation.'],
    ),
    blocker: { title: '사건의 결정적 장면 부족', detail: '무슨 일이 있었는지를 일반적으로 말하지 말고 행동과 결과를 시간 순서로 제시해야 합니다.' },
    reusableStructure: ['배경과 등장인물', '예상 밖의 사건과 대응', '결과·감정·교훈'],
    retryMission: ['when, where, who를 첫 두 문장에 넣으세요.', '결정적인 사건을 구체적인 동사로 설명하세요.', '마지막에 감정 변화나 교훈을 덧붙이세요.'],
    coreSentences: [
      'I remember a special experience involving {topic}.', 'It happened last year when I was with a close friend.', 'At first, everything went according to plan.', 'Then an unexpected problem suddenly came up.', 'We were surprised and did not know what to do.', 'After a short discussion, we chose a simple solution.', 'We worked together to deal with the situation.', 'Fortunately, the problem was solved before it got worse.', 'I felt relieved and proud of our decision.', 'The experience taught me to stay calm.',
    ],
    nextSentences: [
      'One of my most memorable experiences involving {topic} happened last year.', 'I had planned the day carefully with a close friend.', 'At the beginning, everything seemed to be going smoothly.', 'Just when we relaxed, an unexpected problem changed the situation.', 'For a moment, both of us felt confused and worried.', 'Instead of panicking, we stopped and discussed our options.', 'We divided the tasks and dealt with the most urgent issue first.', 'A stranger also gave us useful advice at the right time.', 'Thanks to that help, we found a practical solution.', 'When everything was finally settled, I felt extremely relieved.', 'Looking back, the event brought my friend and me closer together.', 'It also taught me to stay calm and communicate clearly under pressure.',
    ],
  },
  comparison: {
    transcript: {
      first: 'I want to compare the past and present of {topic}. Before, it was different and maybe simpler. Now there are more options, and it is more convenient. Um, both have good points, but I think the current one is better for me.',
      retry: 'There are clear differences between the past and present of {topic}. In the past, people had fewer choices but followed a simpler process. Today, technology makes things faster and more convenient. Although the old way felt familiar, I prefer the current one because it saves time.',
    },
    headline: '차이는 제시했지만, 두 시점의 구체적인 예와 변화의 원인을 한 쌍씩 연결하면 더 설득력 있습니다.',
    summary: 'better와 convenient에 의존해 비교 기준이 충분히 구체적이지 않습니다.',
    mainPointLabel: '선호와 방향은 제시됨',
    mainPointFeedback: '비교 기준을 두 가지로 먼저 정하고 과거와 현재의 예를 같은 순서로 제시하세요.',
    expressions: [
      { situation: '가장 큰 변화를 말할 때', expression: 'The biggest difference is how much more convenient it has become.', guidance: '핵심 비교 기준을 명확히 제시합니다.' },
      { situation: '양쪽 장점을 인정할 때', expression: 'While the old way had its charm, the current one suits my lifestyle better.', guidance: '균형 잡힌 비교 뒤 선호를 말할 수 있습니다.' },
    ],
    vocabulary: vocabulary(
      ['noticeable change', '눈에 띄는 변화', 'There has been a noticeable change in {topic}.'],
      ['feel familiar', '익숙하게 느껴지다', 'The old way still feels familiar to many people.'],
      ['adapt to new needs', '새로운 요구에 적응하다', 'The current system can adapt to new needs.'],
    ),
    blocker: { title: '비교 기준이 추상적임', detail: 'good, better 대신 비용·시간·편리함 같은 동일한 기준으로 양쪽을 비교해야 합니다.' },
    reusableStructure: ['비교 대상과 핵심 차이', '동일 기준의 과거·현재 예', '변화 원인과 개인 선호'],
    retryMission: ['가장 큰 차이를 첫 문장에 말하세요.', '과거와 현재의 구체적인 예를 하나씩 붙이세요.', '변화의 이유와 내 선호를 because로 연결하세요.'],
    coreSentences: [
      'There are several differences in {topic} between the past and today.', 'In the past, people had fewer choices.', 'The process was often slower and less convenient.', 'However, the old way felt simple and familiar.', 'Today, there are more services and useful tools.', 'Technology has made the process much faster.', 'People can also choose what fits their needs.', 'The biggest improvement is the amount of time people save.', 'Although both versions have advantages, I prefer the current one.', 'It is more convenient for my daily life.',
    ],
    nextSentences: [
      'The way people experience {topic} has changed noticeably over time.', 'In the past, choices were limited and information was harder to find.', 'As a result, people spent more time preparing and waiting.', 'Still, the old process was familiar and sometimes felt more personal.', 'Today, technology provides far more options.', 'Most tasks can be completed quickly with a phone or computer.', 'Modern services can also adapt to different needs.', 'The biggest difference is how convenient the entire process has become.', 'On the other hand, too many choices can occasionally feel overwhelming.', 'For that reason, the older approach still has some charm.', 'Even so, the current system suits my lifestyle better.', 'It saves time while giving me the flexibility I need.',
    ],
  },
  role_play: {
    transcript: {
      first: 'Hello, I am calling about {topic}. Um, I have a few questions. First, can you tell me the price? Also, what time is available? And, uh, is there anything I should bring? Okay, thank you.',
      retry: 'Hello, I am calling to get information about {topic}. Could you tell me which options are available and how much they cost? I would also like to know the schedule and cancellation policy. Finally, is there anything I need to prepare in advance?',
    },
    headline: '기본 질문은 만들었지만, 상황 설명과 후속 질문을 더하면 실제 통화처럼 자연스러워집니다.',
    summary: '질문 수는 충분하지만 맥락 없이 이어져 상대방이 필요한 정보를 파악하기 어렵습니다.',
    mainPointLabel: '통화 목적은 제시됨',
    mainPointFeedback: '인사 후 전화한 이유를 한 문장으로 말하고 세부 질문을 중요도 순으로 배치하세요.',
    expressions: [
      { situation: '통화 목적을 밝힐 때', expression: 'I am calling to get a little more information before I decide.', guidance: '질문 전에 자연스럽게 맥락을 제공합니다.' },
      { situation: '추가 조건을 확인할 때', expression: 'Is there anything else I should know in advance?', guidance: '빠뜨린 정보를 마지막에 확인할 수 있습니다.' },
    ],
    vocabulary: vocabulary(
      ['available option', '이용 가능한 선택지', 'Could you explain each available option?'],
      ['feel certain', '확신이 들다', 'That information would help me feel certain about my choice.'],
      ['make a reservation', '예약하다', 'I would like to make a reservation for Saturday.'],
    ),
    blocker: { title: '상황 설명과 후속 질문 부족', detail: '질문을 나열하기 전에 목적을 밝히고 답변에 따라 이어지는 질문을 만들어야 합니다.' },
    reusableStructure: ['인사와 통화 목적', '핵심 질문 세 가지', '조건 재확인과 감사'],
    retryMission: ['첫 문장에 전화한 이유를 말하세요.', '가격·시간·조건을 완전한 질문으로 만드세요.', '마지막에 내용을 재확인하고 감사 인사를 하세요.'],
    coreSentences: [
      'Hello, I am calling about {topic}.', 'I would like to get some information before I decide.', 'First, could you tell me which options are available?', 'I would also like to know how much they cost.', 'What times are available this week?', 'Is there a deadline for making a reservation?', 'Could you explain the cancellation policy as well?', 'Is there anything I need to bring or prepare?', 'That answers all of my questions.', 'Thank you very much for your help.',
    ],
    nextSentences: [
      'Hello, I am calling to get a little more information about {topic}.', 'I am interested, but I would like to compare the available options first.', 'Could you explain the main difference between the options?', 'I would also appreciate a clear breakdown of the total cost.', 'Are there any additional fees that I should expect?', 'Next, could you tell me which times are still available?', 'I may need to change my schedule, so what is the cancellation policy?', 'Is it possible to make a change online or by phone?', 'I would also like to know what I need to prepare in advance.', 'Let me confirm that I understood the information correctly.', 'That sounds like the best option for my situation.', 'Thank you for answering all of my questions so clearly.',
    ],
  },
  problem_solution: {
    transcript: {
      first: 'There is a problem with {topic}. It is inconvenient and many people are unhappy. Um, I think we should talk to someone and find another way. Maybe we can change the schedule or use a different place. That could solve the problem.',
      retry: 'The main problem with {topic} is that it disrupts people’s plans and creates extra stress. First, we should provide clear information and a temporary alternative. Then the people responsible should address the cause and prevent it from happening again.',
    },
    headline: '문제와 대안은 제시했지만, 원인·영향·즉각적 해결·장기적 해결을 구분하면 답변이 더 완성됩니다.',
    summary: '해결책이 일반적이어서 누가 언제 무엇을 해야 하는지 구체성이 부족합니다.',
    mainPointLabel: '문제와 해결 방향은 제시됨',
    mainPointFeedback: '가장 큰 영향을 먼저 말한 뒤 즉시 할 일과 재발 방지책을 분리하세요.',
    expressions: [
      { situation: '핵심 원인을 짚을 때', expression: 'The root of the problem is a lack of clear planning and communication.', guidance: '문제의 표면이 아니라 원인을 설명합니다.' },
      { situation: '단계적 해결을 제안할 때', expression: 'In the short term we should act quickly, while the long-term goal is prevention.', guidance: '즉각적 대안과 장기 대책을 구분합니다.' },
    ],
    vocabulary: vocabulary(
      ['root cause', '근본 원인', 'We need to identify the root cause first.'],
      ['feel frustrated', '답답함을 느끼다', 'People feel frustrated when they receive no explanation.'],
      ['prevent the issue from recurring', '문제의 재발을 막다', 'A clear process can prevent the issue from recurring.'],
    ),
    blocker: { title: '실행 주체와 단계 부족', detail: '누가 어떤 조치를 언제 할지와 임시 대안·장기 대책을 분명히 해야 합니다.' },
    reusableStructure: ['문제와 가장 큰 영향', '즉각적인 현실적 조치', '근본 원인과 재발 방지'],
    retryMission: ['문제의 원인과 영향을 한 문장씩 말하세요.', '당장 가능한 해결책을 구체적인 행동으로 제안하세요.', '장기적인 재발 방지책으로 마무리하세요.'],
    coreSentences: [
      'There is a serious problem involving {topic}.', 'It is disrupting plans and causing unnecessary stress.', 'The first step is to explain the situation clearly.', 'People need accurate information as soon as possible.', 'A temporary alternative should also be provided.', 'This would reduce the immediate inconvenience.', 'Next, the people responsible should find the root cause.', 'They should create a clear process for similar situations.', 'That process can prevent the issue from recurring.', 'A combination of quick action and prevention is the best solution.',
    ],
    nextSentences: [
      'The main problem involving {topic} is the lack of preparation and clear communication.', 'Because people do not know what is happening, they feel frustrated and lose time.', 'The most urgent step is to share accurate information immediately.', 'A temporary alternative should be offered to the people most affected.', 'This short-term response would reduce confusion and inconvenience.', 'At the same time, the organization should identify the root cause.', 'It should speak with the people involved and review the current process.', 'Based on that review, responsibilities and deadlines need to be clarified.', 'A backup plan should also be prepared in advance.', 'Regular updates would help rebuild trust.', 'These measures could prevent the issue from recurring.', 'In my view, fast communication and long-term prevention must work together.',
    ],
  },
}

