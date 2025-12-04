# PetMedical.AI

7개 AI 에이전트 협진과 보호자 주도 데이터 관리를 구현한 반려동물 의료 플랫폼이다. 강아지, 고양이, 토끼, 햄스터, 새, 고슴도치, 파충류 총 7종 반려동물에 대해 종 특화 진단을 제공한다.

---

## 기술적 완성도

**Multi-Agent 협진 아키텍처**

Medical Agent와 Triage Engine이 독립적으로 진단을 수행한다. 두 에이전트의 판단이 불일치하면 Collaborative System이 Senior Reviewer를 호출하여 합의를 도출한다. 이 과정은 브라우저 콘솔에서 `has_discrepancies: true`, `consensus_reached: true` 로그로 실시간 확인이 가능하며, 단순 재호출이 아닌 실제 협진 로직이 구현되어 있다.

**보호자 중심 데이터 소유권 구현**

기존 병원 중심 의료 데이터 관리와 달리, 보호자가 Firestore에 저장된 자신의 진료 기록을 직접 관리한다. 보호자는 원하는 병원을 선택하여 진단 데이터를 선택적으로 공유하며, 병원 이동 시에도 앱에서 과거 이력을 조회하고 전달할 수 있다. 이는 의료 데이터 주권을 보호자에게 이전하는 기술적 구현이다.

---

## AI 기술 구현

**Polyglot AI 전략 (모델별 역할 분리)**

CS Agent와 Information Agent는 빠른 응답이 필요한 접수와 문진에서 Gemini 2.0 Flash를 사용한다. 이미지 분석이 필요한 Vision 기반 문진은 GPT-4o가 담당한다. Medical Agent와 Triage Engine은 Claude Sonnet 4로 의심 질환과 응급도를 독립적으로 계산한다. Hospital Packet 생성은 Claude 3.5 Sonnet이, Pattern Analyzer와 OCR Service는 Gemini 2.0 Flash가 처리한다.

**Collaborative Diagnosis (환각 방어 메커니즘)**

Medical Agent와 Triage Engine의 위험도 레벨, 응급도 점수, 병원 방문 권고를 다층 규칙 기반으로 비교하여 불일치를 감지한다. 불일치 시 Senior Reviewer가 Claude Sonnet 4로 양측 판단을 재검토하고, Second Opinion Agent가 GPT-4o로 추가 검증을 수행한다. 합의 결과는 보수적으로 상향 조정되어 의료 안전성을 확보한다.

---

## 백엔드 Multi-Agent 시스템

**LangGraph 기반 에이전트 파이프라인**

백엔드는 FastAPI + LangGraph로 구성된 5단계 파이프라인을 실행한다. 의존성이 없는 단계(예: Vision 분석과 Symptom Intake)는 병렬로 실행하여 응답 시간을 단축한다. 이후 단계는 TRD(Tool Routing Dispatch) 규칙에 따라 순차 실행되며, 각 단계의 출력이 다음 단계의 입력으로 전달된다.

```
사용자 입력 → [Symptom Intake ∥ Vision(선택)] → Medical → Triage → Careplan → 최종 보고서
```

| 에이전트 | 역할 | 모델 |
|---------|------|------|
| Symptom Intake | 자연어 증상을 JSON 구조화 | Gemini 1.5 Flash |
| Vision Agent | 이미지 분석 (상처, 부종 등) | GPT-4o |
| Medical Agent | 감별진단 및 위험요인 분석 | Claude Sonnet 4 |
| Triage Agent | 응급도 점수(0-5) 산정 | Claude Sonnet 4 |
| Careplan Agent | 홈케어 지침 생성 | Gemini 1.5 Pro |

**GraphState 상태 관리**

Pydantic 기반 GraphState가 에이전트 간 데이터를 관리한다. 각 에이전트의 결과는 `symptom_data`, `vision_data`, `medical_data`, `triage_data`, `careplan_data` 필드에 누적되어 최종 보고서 생성에 사용된다.

**Fail-over 및 안정성**

특정 모델의 응답 지연 또는 장애 발생 시 경량 모델(Gemini Flash, GPT-4o-mini)로 자동 대체하여 서비스 연속성을 보장한다.

**API 엔드포인트**

- `POST /api/triage`: 메인 진단 API. 증상 설명, 종/품종/나이, 이미지 URL을 받아 전체 진단 파이프라인 실행
- `POST /api/question`: 진단 결과에 대한 보호자 후속 질문 처리
- `GET /health`: 서비스 상태 확인

---

## 시스템 아키텍처

```
[보호자 앱]
    ↓ Firebase Auth
[Firestore]
    ↓ realtime listener
[AI Orchestrator]
    ├→ Gemini 2.0 Flash (CS/Info/Care)
    ├→ GPT-4o (Vision Agent)
    ├→ Claude Sonnet 4 (Medical/Triage/Senior)
    └→ Claude 3.5 Sonnet (Hospital Packet)
    ↓
[Multi-Agent Backend - FastAPI/LangGraph]
    ├→ POST /api/triage (진단 파이프라인)
    └→ POST /api/question (후속 질문)
    ↓ JSON output
[병원 어드민]
    ↓ Submit Diagnosis
Firestore Update
    ↓ status: "completed"
[보호자 앱]
    └─ Realtime Sync & Display
```

**기술 스택**

- Frontend: React 18, Vite 5, TailwindCSS 3
- Backend: FastAPI, LangGraph, LangChain, Python 3.12
- Database: Firestore (NoSQL), Google Sheets
- AI: Claude Sonnet 4, Claude 3.5 Sonnet, GPT-4o, GPT-4o-mini, Gemini 2.0 Flash, Gemini 1.5 Flash/Pro
- API: Anthropic API, OpenAI API, Google AI API, Kakao Map API
- Deploy: GitHub Pages (Frontend), Railway (Backend)

**핵심 구현 파일**

```
# Frontend
src/services/ai/
├── agentOrchestrator.js      # 12개 에이전트 순차 실행 로직
├── collaborativeDiagnosis.js # 협진 검증 알고리즘 (240줄)
├── medicalAgent.js           # Claude 기반 의료 진단
└── triageEngine.js           # 응급도 계산 엔진

# Backend (petcare_advisor/)
src/petcare_advisor/
├── main.py                   # FastAPI 진입점
├── agents/
│   ├── root_orchestrator.py  # TRD 규칙 기반 워크플로우 조율
│   ├── symptom_intake_agent.py
│   ├── vision_agent.py
│   ├── medical_agent.py
│   ├── triage_agent.py
│   └── careplan_agent.py
└── shared/types.py           # GraphState, Pydantic 모델
```

---

## 설치 및 실행

**환경 요구사항**

Node.js 18+, Python 3.11+, Firebase 프로젝트, OpenAI API 키, Anthropic API 키, Google AI API 키, Kakao Map API 키

**Frontend 설치**

```bash
git clone https://github.com/ksy070822/ai-factory.git
npm install
cp .env.example .env.local
npm run dev  # http://localhost:5173
```

**Backend 설치**

```bash
git clone https://github.com/ksy070822/multi-agent.git
cd petcare_advisor
pip install -e .
cp .env.example .env
uvicorn petcare_advisor.main:app --reload  # http://localhost:8000
```

**Backend 배포 (Railway)**

Railway에서 GitHub 연동 후 환경 변수 설정:
- `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`
- 자동 빌드 및 배포 (railway.json 설정 적용)

---

## 보안 설계

- Firebase Authentication으로 사용자 인증 구현
- Firestore Security Rules로 데이터 읽기/쓰기 권한 제어
- API 키는 환경 변수로 관리하며 클라이언트에 노출되지 않음
- 백엔드 CORS 설정으로 허용된 도메인만 API 접근 가능
- 보호자가 진료 데이터를 직접 관리하고 병원 선택 시 선택적으로 공유

---

## 협진 시스템 검증

**실제 작동 콘솔 로그**

```javascript
협진 시스템 시작...
불일치 분석: { has_discrepancies: true, discrepancy_count: 1 }
검토 결과: {
  agreement_level: "significant_disagreement",
  medical_agent_assessment: "적절함",
  triage_agent_assessment: "과소평가"
}
최종 합의: {
  consensus_reached: true,
  final_triage_score: 3,
  confidence_score: 0.65
}
```

**검증 방법**

브라우저 개발자 도구(F12) → Console 탭에서 진단 실행 시 실시간 협진 로그 확인

---

Made with ❤️ by PetMedical.AI Team
