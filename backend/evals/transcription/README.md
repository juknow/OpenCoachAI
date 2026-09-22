# STT 평가 자료 폴더

이 폴더는 운영 기능이 아니라 STT 모델과 prompt를 같은 조건으로 비교하기 위한
오프라인 시험 공간이다.

## 파일 구조

```text
transcription/
├─ README.md
├─ manifest.example.json   공개 가능한 구조 예시
├─ manifest.local.json     로컬 실제 목록, Git에서 제외
├─ samples/                평가 음성, Git에서 제외
└─ results/                모델 전사 결과, Git에서 제외
```

## 시작 방법

1. `manifest.example.json`을 `manifest.local.json`으로 복사한다.
2. 명시적 동의를 받았거나 공개 사용이 허용된 음성만 `samples/`에 둔다.
3. 각 음성을 사람이 확인해 `referenceTranscript`를 작성한다.
4. 음성의 특징을 소문자 tag로 기록한다.
5. manifest 검증 테스트를 실행한다.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_transcription_dataset.py
```

## source 값

| 값 | 의미 |
|---|---|
| `synthetic` | 테스트 목적으로 만든 합성 음성 |
| `explicit-test-consent` | 평가 자료 사용에 명시적으로 동의한 사람의 음성 |
| `public-license` | 평가 용도를 허용하는 공개 라이선스 자료 |

출처를 확인할 수 없는 음성은 사용하지 않는다.

## expectedBehavior 값

| 값 | 기대 결과 |
|---|---|
| `transcribe` | 사람이 검수한 `referenceTranscript`와 비교 |
| `empty-or-rejected` | 무음·비음성 입력이며 빈 결과 또는 안전한 거부를 기대 |
| `rejected` | 손상 또는 잘못된 파일이며 입력 단계 거부를 기대 |

## 개인정보 원칙

- 운영 사용자 녹음을 자동으로 복사하지 않는다.
- 이름, 학교, 회사, 주소처럼 개인을 알아볼 수 있는 내용을 넣지 않는다.
- 실제 사람의 음성은 동의 범위와 삭제 요청 방법을 별도로 기록한다.
- `samples/`, `results/`, `manifest.local.json`은 기본적으로 Git에서 제외된다.
- 공개 저장소에는 합성 또는 공개 허가를 확실히 증명할 수 있는 작은 fixture만 별도
  검토 후 추가한다.

