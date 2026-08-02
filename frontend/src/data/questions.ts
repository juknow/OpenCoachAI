import type { Difficulty, Question, QuestionType } from '../types/coach.ts'

interface QuestionSeed {
  difficulty: Difficulty
  topic: string
  prompt: string
  translation: string
}

const q = (
  difficulty: Difficulty,
  topic: string,
  prompt: string,
  translation: string,
): QuestionSeed => ({ difficulty, topic, prompt, translation })

const descriptionQuestions: QuestionSeed[] = [
  q('easy', 'home', 'Describe the home where you live. What does it look like, and what is your favorite part of it?', '현재 살고 있는 집을 묘사해 주세요. 집은 어떻게 생겼으며 가장 좋아하는 공간은 어디인가요?'),
  q('easy', 'bedroom', 'Describe your bedroom in detail. What furniture and personal items can you see there?', '침실을 자세히 묘사해 주세요. 어떤 가구와 개인 물건이 있나요?'),
  q('easy', 'neighborhood', 'Describe your neighborhood. What places are nearby, and what is the atmosphere like?', '동네를 묘사해 주세요. 주변에 어떤 장소가 있고 분위기는 어떤가요?'),
  q('easy', 'park', 'Describe a park you often visit. What can people see and do there?', '자주 방문하는 공원을 묘사해 주세요. 그곳에서 무엇을 보고 할 수 있나요?'),
  q('easy', 'cafe', 'Describe a cafe you like. What does it look like inside, and what makes it comfortable?', '좋아하는 카페를 묘사해 주세요. 내부는 어떻게 생겼고 무엇이 편안하게 느껴지게 하나요?'),
  q('easy', 'beach', 'Describe a beach you know. What does the area look, sound, and feel like?', '알고 있는 해변을 묘사해 주세요. 그곳의 모습과 소리, 느낌은 어떤가요?'),
  q('easy', 'library', 'Describe a library you use. What facilities does it have, and where do you usually sit?', '이용하는 도서관을 묘사해 주세요. 어떤 시설이 있고 보통 어디에 앉나요?'),
  q('easy', 'movie theater', 'Describe a movie theater you often use. What are the facilities like?', '자주 이용하는 영화관을 묘사해 주세요. 시설은 어떤가요?'),
  q('easy', 'favorite object', 'Describe an object you use every day. What does it look like, and why is it important to you?', '매일 사용하는 물건을 묘사해 주세요. 어떻게 생겼으며 왜 중요한가요?'),
  q('medium', 'restaurant', 'Describe a restaurant you would recommend. Explain its location, interior, menu, and atmosphere.', '추천하고 싶은 식당의 위치, 내부, 메뉴와 분위기를 설명해 주세요.'),
  q('medium', 'city landmark', 'Describe a landmark in your city. What makes it visually memorable and worth visiting?', '도시의 대표 장소를 묘사해 주세요. 무엇이 시각적으로 인상적이고 방문할 가치가 있게 하나요?'),
  q('medium', 'vacation destination', 'Describe a vacation destination you would recommend. What can visitors see, eat, and do there?', '추천하고 싶은 여행지를 묘사해 주세요. 방문객은 무엇을 보고 먹고 할 수 있나요?'),
  q('medium', 'hotel', 'Describe a hotel or other accommodation you remember well. What made the place stand out?', '기억에 남는 호텔이나 숙소를 묘사해 주세요. 무엇이 그곳을 특별하게 만들었나요?'),
  q('medium', 'shopping mall', 'Describe a shopping mall you visit. How is it organized, and which area do you like most?', '방문하는 쇼핑몰을 묘사해 주세요. 공간은 어떻게 구성되어 있고 어느 구역을 가장 좋아하나요?'),
  q('medium', 'gym', 'Describe a gym or exercise facility you know. What equipment and services are available?', '알고 있는 헬스장이나 운동 시설을 묘사해 주세요. 어떤 장비와 서비스가 있나요?'),
  q('medium', 'campus', 'Describe a school or university campus you know well. Explain its layout and busiest places.', '잘 아는 학교나 대학 캠퍼스의 배치와 가장 붐비는 장소를 설명해 주세요.'),
  q('medium', 'station', 'Describe a subway or train station you often use. What makes it convenient or inconvenient?', '자주 이용하는 지하철역이나 기차역을 묘사해 주세요. 무엇이 편리하거나 불편하게 하나요?'),
  q('hard', 'changing neighborhood', 'Give a detailed description of how your neighborhood looks today, including signs of recent development.', '최근 개발의 흔적을 포함해 현재 동네의 모습을 자세히 묘사해 주세요.'),
  q('hard', 'memorable architecture', 'Describe a building with memorable architecture. Explain how its exterior and interior create a particular impression.', '인상적인 건축물을 묘사하고 외관과 내부가 어떤 느낌을 만드는지 설명해 주세요.'),
  q('hard', 'seasonal place', 'Describe a place that looks very different depending on the season. Use specific sensory details.', '계절에 따라 모습이 크게 달라지는 장소를 구체적인 감각 표현으로 묘사해 주세요.'),
  q('hard', 'crowded public space', 'Describe a crowded public place at its busiest time. Explain the movement, sounds, and overall mood.', '가장 붐비는 시간의 공공장소를 움직임, 소리와 전체 분위기를 중심으로 묘사해 주세요.'),
  q('hard', 'quiet retreat', 'Describe a place where you go to escape noise and stress. Explain what creates its calm atmosphere.', '소음과 스트레스를 피하러 가는 장소와 차분한 분위기를 만드는 요소를 묘사해 주세요.'),
  q('hard', 'local market', 'Describe a traditional or local market in detail. What do vendors sell, and how do people interact there?', '전통 시장이나 지역 시장을 자세히 묘사해 주세요. 상인들은 무엇을 팔고 사람들은 어떻게 교류하나요?'),
  q('hard', 'event venue', 'Describe a venue prepared for a major event. Explain the seating, lighting, facilities, and crowd atmosphere.', '큰 행사를 위해 준비된 장소의 좌석, 조명, 시설과 관중 분위기를 묘사해 주세요.'),
  q('hard', 'ideal room', 'Describe your ideal room or workspace. Explain how each design choice would support your daily life.', '이상적인 방이나 작업 공간을 묘사하고 각 디자인 선택이 일상에 어떻게 도움이 되는지 설명해 주세요.'),
]

const routineQuestions: QuestionSeed[] = [
  q('easy', 'weekday morning', 'Walk me through your usual weekday morning from the moment you wake up.', '잠에서 깬 순간부터 평일 아침 일과를 순서대로 말해 주세요.'),
  q('easy', 'weekend', 'What do you usually do on weekends? Describe your typical schedule.', '주말에 보통 무엇을 하나요? 전형적인 일정을 설명해 주세요.'),
  q('easy', 'meal preparation', 'Describe how you usually prepare and eat a meal at home.', '집에서 보통 식사를 준비하고 먹는 과정을 설명해 주세요.'),
  q('easy', 'commute', 'Describe your usual trip to school or work. What transportation do you use?', '학교나 직장에 가는 평소 이동 과정과 교통수단을 설명해 주세요.'),
  q('easy', 'exercise', 'Tell me about your regular exercise routine. Where, when, and how often do you exercise?', '규칙적인 운동 습관을 말해 주세요. 어디서 언제 얼마나 자주 운동하나요?'),
  q('easy', 'housework', 'What household chores do you regularly do, and in what order?', '정기적으로 하는 집안일과 그 순서를 말해 주세요.'),
  q('easy', 'music listening', 'Describe when and how you usually listen to music during the day.', '하루 중 언제 어떤 방식으로 음악을 듣는지 설명해 주세요.'),
  q('easy', 'cafe visit', 'What do you normally do when you visit a cafe?', '카페에 방문하면 보통 무엇을 하는지 말해 주세요.'),
  q('easy', 'bedtime', 'Describe your usual routine before going to bed.', '잠자리에 들기 전의 평소 일과를 설명해 주세요.'),
  q('medium', 'busy weekday', 'Describe how you organize a particularly busy weekday and keep track of your tasks.', '특히 바쁜 평일에 일정을 구성하고 할 일을 관리하는 방법을 설명해 주세요.'),
  q('medium', 'movie watching', 'Explain your usual process for choosing, watching, and discussing a movie.', '영화를 선택하고 보고 이야기하는 평소 과정을 설명해 주세요.'),
  q('medium', 'trip planning', 'Describe how you normally plan a trip, from choosing a destination to packing.', '목적지 선택부터 짐 싸기까지 평소 여행 계획 과정을 설명해 주세요.'),
  q('medium', 'online shopping', 'Walk me through how you usually shop online and decide what to buy.', '온라인 쇼핑을 하고 구매할 물건을 결정하는 과정을 설명해 주세요.'),
  q('medium', 'study session', 'Describe a productive study session. How do you prepare, focus, and take breaks?', '생산적인 공부 시간에 준비하고 집중하며 쉬는 방법을 설명해 주세요.'),
  q('medium', 'social plans', 'How do you usually make plans with friends and decide where to meet?', '친구들과 약속을 잡고 만날 장소를 결정하는 방식을 설명해 주세요.'),
  q('medium', 'health management', 'Describe the routines you follow to stay healthy during a normal week.', '평범한 한 주 동안 건강을 유지하기 위해 따르는 습관을 설명해 주세요.'),
  q('medium', 'phone use', 'Describe how your phone fits into your daily routine, from morning to night.', '아침부터 밤까지 휴대전화가 일상에서 어떻게 사용되는지 설명해 주세요.'),
  q('hard', 'changing schedule', 'Explain how your daily routine changes when an unexpected task is added to your schedule.', '예상치 못한 일이 일정에 추가될 때 일과가 어떻게 바뀌는지 설명해 주세요.'),
  q('hard', 'work-life balance', 'Describe the routine you use to balance responsibilities, rest, and personal interests.', '책임, 휴식과 개인 관심사의 균형을 맞추는 일과를 설명해 주세요.'),
  q('hard', 'long journey', 'Walk me through everything you normally do before, during, and after a long journey.', '장거리 이동 전, 도중과 후에 보통 하는 모든 일을 순서대로 설명해 주세요.'),
  q('hard', 'hosting guests', 'Describe your routine for preparing your home, food, and schedule when guests are coming.', '손님이 올 때 집, 음식과 일정을 준비하는 과정을 설명해 주세요.'),
  q('hard', 'digital break', 'Explain how you spend a day when you intentionally avoid phones and computers.', '휴대전화와 컴퓨터를 의도적으로 사용하지 않는 날을 어떻게 보내는지 설명해 주세요.'),
  q('hard', 'project routine', 'Describe how you manage a multi-week project from the first plan to the final review.', '몇 주간 진행되는 프로젝트를 첫 계획부터 최종 검토까지 관리하는 방식을 설명해 주세요.'),
  q('hard', 'seasonal routine', 'Explain how your daily habits change between the hottest and coldest parts of the year.', '가장 더운 시기와 가장 추운 시기에 일상 습관이 어떻게 달라지는지 설명해 주세요.'),
  q('hard', 'recovery day', 'Describe the routine you follow when you are exhausted and need to recover efficiently.', '매우 피곤해 효율적으로 회복해야 할 때 따르는 일과를 설명해 주세요.'),
]

const pastExperienceQuestions: QuestionSeed[] = [
  q('easy', 'memorable meal', 'Tell me about a memorable meal you had. Where were you, and what made it special?', '기억에 남는 식사 경험을 말해 주세요. 어디에 있었고 무엇이 특별했나요?'),
  q('easy', 'first movie', 'Tell me about a movie you remember seeing for the first time.', '처음 보았을 때가 기억나는 영화에 대해 말해 주세요.'),
  q('easy', 'park visit', 'Describe a memorable visit to a park. Who were you with, and what happened?', '기억에 남는 공원 방문을 말해 주세요. 누구와 있었고 무슨 일이 있었나요?'),
  q('easy', 'birthday', 'Tell me about a birthday celebration you remember well.', '기억에 남는 생일 축하 경험을 말해 주세요.'),
  q('easy', 'shopping experience', 'Tell me about a time you bought something you really liked.', '정말 마음에 드는 물건을 샀던 경험을 말해 주세요.'),
  q('easy', 'concert', 'Describe a concert or live performance you attended.', '참석했던 콘서트나 라이브 공연을 설명해 주세요.'),
  q('easy', 'family trip', 'Tell me about a trip you took with your family.', '가족과 함께 갔던 여행에 대해 말해 주세요.'),
  q('easy', 'new hobby', 'Tell me about the first time you tried a new hobby.', '새로운 취미를 처음 시도했던 경험을 말해 주세요.'),
  q('easy', 'unexpected weather', 'Describe a time when unexpected weather changed your plans.', '예상치 못한 날씨 때문에 계획이 바뀐 경험을 설명해 주세요.'),
  q('medium', 'memorable journey', 'Tell a story about a journey that did not go as planned. What happened in the end?', '계획대로 되지 않았던 여행 이야기를 하고 결국 어떻게 되었는지 말해 주세요.'),
  q('medium', 'helping someone', 'Describe a time when you helped someone solve a problem.', '누군가의 문제 해결을 도왔던 경험을 설명해 주세요.'),
  q('medium', 'special restaurant', 'Tell me about a restaurant experience that exceeded or disappointed your expectations.', '기대 이상이거나 실망스러웠던 식당 경험을 말해 주세요.'),
  q('medium', 'lost item', 'Tell me about a time you lost an important item and what you did next.', '중요한 물건을 잃어버렸던 경험과 이후에 한 일을 말해 주세요.'),
  q('medium', 'achievement', 'Describe a personal achievement you worked hard for.', '열심히 노력해 이룬 개인적인 성취를 설명해 주세요.'),
  q('medium', 'meeting someone', 'Tell me about a memorable first meeting with someone.', '누군가와의 기억에 남는 첫 만남을 말해 주세요.'),
  q('medium', 'technology problem', 'Describe a time when a device or app failed at an inconvenient moment.', '불편한 순간에 기기나 앱이 작동하지 않았던 경험을 설명해 주세요.'),
  q('medium', 'public event', 'Tell me about a festival, sports game, or public event you attended.', '참석했던 축제, 스포츠 경기 또는 공개 행사에 대해 말해 주세요.'),
  q('hard', 'difficult decision', 'Tell me about a difficult decision you made. Explain the events leading up to it and the result.', '어려운 결정을 내렸던 경험을 그 과정과 결과를 포함해 말해 주세요.'),
  q('hard', 'major change', 'Describe an experience that significantly changed one of your habits or opinions.', '습관이나 생각을 크게 바꾼 경험을 설명해 주세요.'),
  q('hard', 'team conflict', 'Tell me about a conflict in a team and how the people involved resolved it.', '팀 내 갈등과 관련된 사람들이 이를 해결한 과정을 말해 주세요.'),
  q('hard', 'travel emergency', 'Tell a detailed story about an emergency or serious problem during a trip.', '여행 중 발생한 긴급 상황이나 심각한 문제를 자세히 이야기해 주세요.'),
  q('hard', 'failed plan', 'Describe a plan that failed despite careful preparation. What did you learn?', '철저히 준비했지만 실패한 계획과 그 경험에서 배운 점을 설명해 주세요.'),
  q('hard', 'meaningful conversation', 'Tell me about a conversation that stayed with you for a long time and explain why.', '오랫동안 기억에 남은 대화와 그 이유를 말해 주세요.'),
  q('hard', 'community experience', 'Describe an experience that made you feel connected to your community.', '지역 공동체와 연결되어 있다고 느끼게 한 경험을 설명해 주세요.'),
  q('hard', 'surprising outcome', 'Tell a story that began normally but ended in a completely unexpected way.', '평범하게 시작했지만 전혀 예상하지 못한 방식으로 끝난 이야기를 해 주세요.'),
]

const comparisonQuestions: QuestionSeed[] = [
  q('easy', 'home then and now', 'Compare the home you lived in before with the home you live in now.', '예전에 살던 집과 지금 사는 집을 비교해 주세요.'),
  q('easy', 'weekday and weekend', 'Compare your typical weekday with your typical weekend.', '평소 평일과 주말을 비교해 주세요.'),
  q('easy', 'movies at home and theaters', 'Compare watching movies at home with watching them at a theater.', '집에서 영화를 보는 것과 영화관에서 보는 것을 비교해 주세요.'),
  q('easy', 'city and countryside', 'Compare living in a large city with living in the countryside.', '대도시 생활과 시골 생활을 비교해 주세요.'),
  q('easy', 'online and offline shopping', 'Compare shopping online with shopping in a physical store.', '온라인 쇼핑과 매장 쇼핑을 비교해 주세요.'),
  q('easy', 'summer and winter', 'Compare how you spend your free time in summer and winter.', '여름과 겨울에 여가 시간을 보내는 방식을 비교해 주세요.'),
  q('easy', 'two cafes', 'Compare two cafes you know. Which one do you prefer?', '알고 있는 두 카페를 비교하고 어느 곳을 더 좋아하는지 말해 주세요.'),
  q('easy', 'public and private transport', 'Compare public transportation with traveling by car.', '대중교통 이용과 자동차 이동을 비교해 주세요.'),
  q('easy', 'old and new phone', 'Compare your current phone with a phone you used in the past.', '현재 휴대전화와 예전에 사용하던 휴대전화를 비교해 주세요.'),
  q('medium', 'neighborhood change', 'Explain how your neighborhood has changed over the past several years.', '지난 몇 년 동안 동네가 어떻게 변했는지 설명해 주세요.'),
  q('medium', 'travel planning change', 'Compare how you planned trips in the past with how you plan them now.', '과거와 현재의 여행 계획 방식을 비교해 주세요.'),
  q('medium', 'exercise habits', 'Compare your current exercise habits with your habits a few years ago.', '현재 운동 습관과 몇 년 전의 습관을 비교해 주세요.'),
  q('medium', 'communication', 'Explain how the way people communicate has changed because of mobile technology.', '모바일 기술 때문에 사람들의 소통 방식이 어떻게 변했는지 설명해 주세요.'),
  q('medium', 'two destinations', 'Compare two travel destinations you have visited and recommend one.', '방문한 두 여행지를 비교하고 한 곳을 추천해 주세요.'),
  q('medium', 'work and study', 'Compare working on a professional task with studying for an exam.', '업무 과제를 수행하는 것과 시험공부를 하는 것을 비교해 주세요.'),
  q('medium', 'home cooking and dining out', 'Compare cooking at home with eating at restaurants in terms of cost, time, and enjoyment.', '비용, 시간과 즐거움 측면에서 집밥과 외식을 비교해 주세요.'),
  q('medium', 'past and current hobbies', 'Compare a hobby you enjoyed as a child with one you enjoy now.', '어릴 때 즐겼던 취미와 현재 즐기는 취미를 비교해 주세요.'),
  q('hard', 'changing entertainment', 'Explain how entertainment choices have changed over the last decade and what caused the change.', '지난 10년간 여가 선택이 어떻게 변했고 무엇이 변화를 일으켰는지 설명해 주세요.'),
  q('hard', 'traditional and remote work', 'Compare traditional office work with remote work, including their long-term effects.', '전통적인 사무실 근무와 원격 근무를 장기적인 영향까지 포함해 비교해 주세요.'),
  q('hard', 'tourism impact', 'Compare a popular destination before and after it became crowded with tourists.', '관광객이 몰리기 전과 후의 인기 여행지를 비교해 주세요.'),
  q('hard', 'learning methods', 'Compare learning from a teacher in person with learning through digital platforms.', '교사에게 직접 배우는 것과 디지털 플랫폼으로 배우는 것을 비교해 주세요.'),
  q('hard', 'consumer priorities', 'Explain how your priorities when buying products have changed and why.', '제품 구매 시 우선순위가 어떻게 변했고 그 이유가 무엇인지 설명해 주세요.'),
  q('hard', 'community spaces', 'Compare the role of public spaces in your community in the past and today.', '과거와 오늘날 지역사회 공공장소의 역할을 비교해 주세요.'),
  q('hard', 'environmental awareness', 'Compare people’s environmental awareness now with their awareness in the past.', '현재 사람들의 환경 인식을 과거와 비교해 주세요.'),
  q('hard', 'independent and group travel', 'Compare traveling alone with traveling in a group, including unexpected challenges.', '혼자 여행하는 것과 단체 여행을 예상치 못한 어려움까지 포함해 비교해 주세요.'),
]

const rolePlayQuestions: QuestionSeed[] = [
  q('easy', 'movie tickets', 'Call a movie theater and ask three or four questions about tickets, showtimes, and seating.', '영화관에 전화해 표, 상영 시간과 좌석에 대해 서너 가지 질문을 해 보세요.'),
  q('easy', 'restaurant reservation', 'Call a restaurant and ask three or four questions before making a reservation.', '식당에 전화해 예약 전에 서너 가지 질문을 해 보세요.'),
  q('easy', 'gym membership', 'Visit a gym and ask the staff three or four questions about membership and facilities.', '헬스장을 방문해 회원권과 시설에 대해 직원에게 서너 가지 질문을 해 보세요.'),
  q('easy', 'hotel room', 'Call a hotel and ask three or four questions about rooms, price, and check-in.', '호텔에 전화해 객실, 가격과 체크인에 대해 서너 가지 질문을 해 보세요.'),
  q('easy', 'concert information', 'Call a concert venue and ask for the information you need before attending.', '공연장에 전화해 참석 전에 필요한 정보를 질문해 보세요.'),
  q('easy', 'language class', 'Call a language school and ask three or four questions about a class.', '어학원에 전화해 수업에 대해 서너 가지 질문을 해 보세요.'),
  q('easy', 'rental car', 'Talk to a rental car employee and ask about available cars, cost, and rules.', '렌터카 직원에게 이용 가능한 차량, 비용과 규칙을 질문해 보세요.'),
  q('easy', 'cafe order', 'Order drinks and food at a cafe and ask about two menu items.', '카페에서 음료와 음식을 주문하고 메뉴 두 가지에 대해 질문해 보세요.'),
  q('easy', 'museum visit', 'Call a museum and ask about hours, admission, and current exhibitions.', '박물관에 전화해 운영 시간, 입장료와 현재 전시를 질문해 보세요.'),
  q('medium', 'change reservation', 'Call a restaurant because you need to change a reservation. Explain the situation and suggest two alternatives.', '식당에 전화해 예약 변경 이유를 설명하고 두 가지 대안을 제시해 보세요.'),
  q('medium', 'invite a friend', 'Call a friend, invite them to a weekend activity, and answer their questions about the plan.', '친구에게 전화해 주말 활동에 초대하고 계획에 관한 질문에 답해 보세요.'),
  q('medium', 'return a product', 'Talk to a store employee about returning a product. Explain the reason and ask about your options.', '매장 직원에게 제품 반품 이유를 설명하고 가능한 방법을 질문해 보세요.'),
  q('medium', 'missed appointment', 'Call a clinic after missing an appointment. Apologize, explain, and arrange a new time.', '예약을 놓친 뒤 병원에 전화해 사과하고 설명한 후 새 시간을 정해 보세요.'),
  q('medium', 'travel advice', 'A friend is visiting your city. Recommend a place and answer questions about transportation and cost.', '친구가 당신의 도시를 방문합니다. 장소를 추천하고 교통과 비용 질문에 답해 보세요.'),
  q('medium', 'broken hotel facility', 'Call the hotel front desk about a broken facility in your room and request a solution.', '객실 내 고장 난 시설에 대해 프런트에 전화하고 해결을 요청해 보세요.'),
  q('medium', 'class schedule conflict', 'Talk to an instructor about a schedule conflict and propose two ways to handle it.', '강사에게 일정 충돌을 설명하고 해결 방법 두 가지를 제안해 보세요.'),
  q('medium', 'lost property inquiry', 'Call a public facility about a lost item. Describe it and ask what you should do next.', '공공시설에 전화해 잃어버린 물건을 묘사하고 다음에 할 일을 질문해 보세요.'),
  q('hard', 'canceled flight', 'Speak with an airline employee after a flight cancellation. Explain your needs, ask detailed questions, and negotiate an alternative.', '항공편 취소 후 직원에게 필요한 사항을 설명하고 자세히 질문하며 대안을 협의해 보세요.'),
  q('hard', 'event complaint', 'Call an event organizer about a serious problem you experienced. Explain the impact and request a fair response.', '행사 주최자에게 심각한 문제와 그 영향을 설명하고 적절한 조치를 요청해 보세요.'),
  q('hard', 'apartment negotiation', 'Talk to a landlord about a repair and scheduling problem. Ask questions and negotiate a practical plan.', '집주인에게 수리와 일정 문제를 말하고 질문한 뒤 현실적인 계획을 협의해 보세요.'),
  q('hard', 'group trip change', 'Tell your travel group that the original plan is impossible. Explain why and persuade them to choose a new plan.', '여행 모임에 기존 계획이 불가능한 이유를 설명하고 새 계획을 선택하도록 설득해 보세요.'),
  q('hard', 'incorrect bill', 'Discuss an incorrect bill with a service representative. Clarify the details and request specific corrections.', '서비스 직원과 잘못된 청구서를 논의하고 세부 내용을 확인해 구체적인 수정을 요청해 보세요.'),
  q('hard', 'professional deadline', 'Call a teammate about a deadline you may miss. Explain the causes, consequences, and recovery plan.', '마감일을 지키기 어려운 상황을 팀원에게 설명하고 원인, 영향과 만회 계획을 말해 보세요.'),
  q('hard', 'community proposal', 'Present a proposal to a community representative and respond to concerns about cost and inconvenience.', '지역사회 담당자에게 제안을 설명하고 비용과 불편에 관한 우려에 답해 보세요.'),
  q('hard', 'double booking', 'Resolve a double-booking problem with a venue manager while protecting the most important parts of your event.', '장소 관리자와 중복 예약 문제를 해결하며 행사의 가장 중요한 부분을 지켜 보세요.'),
]

const problemSolutionQuestions: QuestionSeed[] = [
  q('easy', 'noisy neighbor', 'Your neighbor is making too much noise at night. Explain the problem and suggest a solution.', '이웃이 밤에 너무 시끄럽습니다. 문제를 설명하고 해결책을 제안해 주세요.'),
  q('easy', 'late bus', 'Your bus is very late and you may miss an appointment. What would you do?', '버스가 매우 늦어 약속에 늦을 수 있습니다. 어떻게 하겠나요?'),
  q('easy', 'wrong order', 'You received the wrong food at a restaurant. Explain how you would solve the problem.', '식당에서 잘못된 음식이 나왔습니다. 문제를 어떻게 해결할지 설명해 주세요.'),
  q('easy', 'forgotten wallet', 'You arrived at a store without your wallet. Describe the problem and your next steps.', '지갑 없이 가게에 도착했습니다. 문제와 다음 행동을 설명해 주세요.'),
  q('easy', 'full parking lot', 'The parking lot is full when you arrive at an event. What alternatives can you try?', '행사장 주차장이 가득 찼습니다. 어떤 대안을 시도할 수 있나요?'),
  q('easy', 'rainy picnic', 'Heavy rain starts just before an outdoor picnic. Explain how you would change the plan.', '야외 소풍 직전에 폭우가 시작됩니다. 계획을 어떻게 바꿀지 설명해 주세요.'),
  q('easy', 'dead phone battery', 'Your phone battery dies while you are away from home. What problems could this cause, and what would you do?', '외출 중 휴대전화 배터리가 방전되었습니다. 어떤 문제가 생기고 어떻게 하겠나요?'),
  q('easy', 'missing ticket', 'You cannot find your ticket at the entrance to a performance. How would you handle it?', '공연장 입구에서 표를 찾을 수 없습니다. 어떻게 대처하겠나요?'),
  q('easy', 'closed cafe', 'The cafe where you planned to meet a friend is unexpectedly closed. Suggest a new plan.', '친구와 만나기로 한 카페가 갑자기 문을 닫았습니다. 새 계획을 제안해 주세요.'),
  q('medium', 'hotel room problem', 'Your hotel room is very different from the one you reserved. Explain the issue and propose solutions.', '호텔 객실이 예약한 것과 매우 다릅니다. 문제를 설명하고 해결책을 제안해 주세요.'),
  q('medium', 'internet outage', 'Your internet stops working during an important online meeting. Describe your immediate and long-term solutions.', '중요한 온라인 회의 중 인터넷이 끊겼습니다. 즉각적 해결책과 장기적 해결책을 설명해 주세요.'),
  q('medium', 'damaged purchase', 'An expensive item arrives damaged. Explain how you would document and resolve the problem.', '비싼 물건이 파손된 채 도착했습니다. 문제를 기록하고 해결하는 방법을 설명해 주세요.'),
  q('medium', 'overcrowded park', 'A neighborhood park has become overcrowded and dirty. Suggest practical improvements.', '동네 공원이 너무 붐비고 더러워졌습니다. 현실적인 개선책을 제안해 주세요.'),
  q('medium', 'schedule conflict', 'Two important events are scheduled at the same time. Explain how you would decide and communicate your choice.', '중요한 두 행사가 같은 시간에 있습니다. 선택하고 이를 알리는 방법을 설명해 주세요.'),
  q('medium', 'lost luggage', 'Your luggage does not arrive after a flight. Explain the steps you would take.', '비행 후 수하물이 도착하지 않았습니다. 취할 조치를 설명해 주세요.'),
  q('medium', 'team member absent', 'A team member is suddenly absent before a presentation. How would you reorganize the work?', '발표 직전 팀원이 갑자기 빠졌습니다. 업무를 어떻게 재구성하겠나요?'),
  q('medium', 'construction noise', 'Long-term construction noise is affecting local residents. Suggest a balanced solution.', '장기간의 공사 소음이 주민들에게 영향을 줍니다. 균형 잡힌 해결책을 제안해 주세요.'),
  q('hard', 'tourism congestion', 'A popular destination is suffering from traffic, waste, and resident complaints. Propose a comprehensive solution.', '인기 여행지가 교통, 쓰레기와 주민 불만 문제를 겪고 있습니다. 종합적인 해결책을 제안해 주세요.'),
  q('hard', 'remote work isolation', 'Employees working remotely feel isolated and communication is getting worse. Analyze the causes and propose solutions.', '원격 근무 직원들이 고립감을 느끼고 소통이 악화됩니다. 원인을 분석하고 해결책을 제안해 주세요.'),
  q('hard', 'public transport disruption', 'A major transit line will close for several months. Explain how the city should reduce the impact.', '주요 교통 노선이 몇 달간 폐쇄됩니다. 도시가 영향을 줄이는 방법을 설명해 주세요.'),
  q('hard', 'community facility budget', 'A community cannot afford all the requested facility improvements. Explain how priorities should be set.', '지역사회가 요청된 모든 시설 개선 비용을 감당할 수 없습니다. 우선순위를 정하는 방법을 설명해 주세요.'),
  q('hard', 'data privacy concern', 'A useful app is collecting more personal data than expected. Discuss the risks and a responsible response.', '유용한 앱이 예상보다 많은 개인정보를 수집합니다. 위험과 책임 있는 대응을 논의해 주세요.'),
  q('hard', 'event capacity crisis', 'Far more people arrive at an event than expected. Propose a solution that protects safety and fairness.', '예상보다 훨씬 많은 사람이 행사에 왔습니다. 안전과 공정성을 지키는 해결책을 제안해 주세요.'),
  q('hard', 'declining local business', 'Small local businesses are losing customers to online shopping. Analyze the problem and suggest sustainable responses.', '지역 소상공인이 온라인 쇼핑에 고객을 잃고 있습니다. 문제를 분석하고 지속 가능한 대응을 제안해 주세요.'),
  q('hard', 'extreme weather preparation', 'Your community is facing more frequent extreme weather. Propose immediate and long-term preparation measures.', '지역사회가 더 잦은 극한 날씨를 겪고 있습니다. 즉각적·장기적 대비책을 제안해 주세요.'),
]

const seedsByType: Record<QuestionType, QuestionSeed[]> = {
  description: descriptionQuestions,
  routine: routineQuestions,
  past_experience: pastExperienceQuestions,
  comparison: comparisonQuestions,
  role_play: rolePlayQuestions,
  problem_solution: problemSolutionQuestions,
}

export const QUESTION_TYPE_META: Record<
  QuestionType,
  { label: string; description: string; accent: string }
> = {
  description: {
    label: 'Description',
    description: '장소·사물의 특징을 구체적으로 묘사해요.',
    accent: 'blue',
  },
  routine: {
    label: 'Routine',
    description: '평소 행동을 순서와 빈도로 설명해요.',
    accent: 'amber',
  },
  past_experience: {
    label: 'Past Experience',
    description: '특정 과거 사건을 이야기로 전개해요.',
    accent: 'violet',
  },
  comparison: {
    label: 'Comparison & Change',
    description: '과거와 현재의 차이와 이유를 비교해요.',
    accent: 'green',
  },
  role_play: {
    label: 'Role-play',
    description: '상황에 맞는 3~4개의 질문과 요청을 만들어요.',
    accent: 'coral',
  },
  problem_solution: {
    label: 'Problem & Solution',
    description: '문제를 설명하고 현실적인 해결책을 제안해요.',
    accent: 'indigo',
  },
}

export const QUESTION_BANK: Question[] = Object.entries(seedsByType).flatMap(
  ([type, seeds]) =>
    seeds.map((seed, index) => ({
      id: `${type}-${String(index + 1).padStart(2, '0')}`,
      type: type as QuestionType,
      ...seed,
    })),
)

const validateQuestionBank = (questions: Question[]) => {
  const expectedDifficultyCounts: Record<Difficulty, number> = {
    easy: 9,
    medium: 8,
    hard: 8,
  }

  if (questions.length !== 150) {
    throw new Error(`Question bank must contain 150 questions, got ${questions.length}.`)
  }

  const ids = new Set(questions.map((question) => question.id))
  if (ids.size !== questions.length) {
    throw new Error('Question bank contains duplicate ids.')
  }

  for (const type of Object.keys(seedsByType) as QuestionType[]) {
    const typeQuestions = questions.filter((question) => question.type === type)
    if (typeQuestions.length !== 25) {
      throw new Error(`${type} must contain 25 questions.`)
    }

    for (const difficulty of Object.keys(expectedDifficultyCounts) as Difficulty[]) {
      const count = typeQuestions.filter(
        (question) => question.difficulty === difficulty,
      ).length
      if (count !== expectedDifficultyCounts[difficulty]) {
        throw new Error(
          `${type}/${difficulty} must contain ${expectedDifficultyCounts[difficulty]} questions.`,
        )
      }
    }
  }
}

validateQuestionBank(QUESTION_BANK)

export const getRandomQuestion = (
  difficulty: Difficulty,
  type?: QuestionType,
): Question => {
  const candidates = QUESTION_BANK.filter(
    (question) =>
      question.difficulty === difficulty && (!type || question.type === type),
  )
  const index = Math.floor(Math.random() * candidates.length)
  const question = candidates[index]
  if (!question) {
    throw new Error(`No question found for ${difficulty}/${type ?? 'all'}.`)
  }
  return question
}

