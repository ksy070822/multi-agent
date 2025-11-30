# Railway 배포 설정 가이드

## 1. Railway CLI 설치 및 로그인

```bash
# Railway CLI 설치 (이미 설치됨)
curl -fsSL https://railway.app/install.sh | sh

# Railway 로그인
railway login
```

## 2. 프로젝트 초기화 및 GitHub 연결

```bash
cd /Users/may.08/Desktop/해커톤/multi-agent

# Railway 프로젝트 초기화
railway init

# GitHub 레포지토리 연결
# Railway 대시보드에서 직접 연결하는 것이 더 쉬울 수 있습니다
```

## 3. Railway 웹 대시보드에서 설정 (권장)

### 3.1 프로젝트 생성
1. https://railway.app 접속
2. "New Project" 클릭
3. "Deploy from GitHub repo" 선택
4. 레포지토리 선택: `ksy070822/petcare-multi-agent-backend` 또는 `ksy070822/multi-agent`

### 3.2 서비스 설정
1. 생성된 서비스에서 "Settings" 클릭
2. **Root Directory**: `petcare_advisor` 설정
3. **Build Command**: (자동 감지 또는 비워두기)
4. **Start Command**: `PYTHONPATH=src uvicorn petcare_advisor.main:app --host 0.0.0.0 --port $PORT`

### 3.3 환경 변수 설정
Variables 탭에서 다음 환경 변수 추가:

```
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
API_HOST=0.0.0.0
LOG_LEVEL=INFO
```

## 4. 배포 확인

배포가 완료되면:
1. Railway 대시보드에서 "Settings" → "Networking" 확인
2. "Generate Domain" 클릭하여 Public URL 생성
3. URL 형식: `https://your-app-name.up.railway.app`

## 5. Health Check

배포된 URL로 테스트:
```bash
curl https://your-app-name.up.railway.app/health
```

예상 응답:
```json
{"status":"healthy","service":"petcare-advisor"}
```

## 6. 프론트엔드 연결

### 6.1 GitHub Secrets 설정
1. `pet-link-ai_11301100` (또는 `ai-factory`) 레포지토리로 이동
2. Settings → Secrets and variables → Actions
3. New repository secret 추가:
   - Name: `VITE_TRIAGE_API_BASE_URL`
   - Value: `https://your-app-name.up.railway.app` (Railway에서 생성한 URL)

### 6.2 로컬 개발 환경
`.env` 파일에 추가:
```env
VITE_TRIAGE_API_BASE_URL=https://your-app-name.up.railway.app
```

### 6.3 코드 확인
`App.jsx`의 `getTriageApiBaseUrl()` 함수가 환경 변수를 우선 사용하도록 이미 설정되어 있습니다.

## 7. CORS 설정 확인

백엔드 `main.py`에서 GitHub Pages 도메인이 이미 허용되어 있습니다:
- `https://ksy070822.github.io`

## 문제 해결

### 배포 실패 시
1. Railway 로그 확인: Deployments → 최신 배포 → Logs
2. Root Directory가 `petcare_advisor`로 설정되어 있는지 확인
3. 환경 변수가 올바르게 설정되어 있는지 확인

### API 연결 실패 시
1. Railway Public URL이 올바른지 확인
2. CORS 설정 확인
3. 브라우저 개발자 도구에서 네트워크 오류 확인

