# Railway 배포 가이드

## 문제 해결

Railway가 프로젝트를 인식하지 못하는 경우, 다음을 확인하세요:

### 1. Railway 설정

1. **Railway 대시보드에서 프로젝트 설정 확인**
   - Settings → Build & Deploy
   - **Root Directory**: `petcare_advisor`로 설정
   - 또는 루트 디렉토리를 비워두고 `Procfile`이 루트에 있는지 확인

### 2. 빌드 설정

Railway는 다음 파일들을 사용합니다:
- `requirements.txt` - Python 의존성
- `Procfile` - 실행 명령
- `nixpacks.toml` - 빌드 설정 (선택)
- `railway.json` - Railway 설정 (선택)

### 3. 환경 변수 설정

Railway 대시보드 → Variables에서 다음 환경 변수 추가:

```
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key (선택)
API_HOST=0.0.0.0
LOG_LEVEL=INFO
```

### 4. 배포 후 확인

배포가 완료되면:
1. Railway가 제공하는 URL 확인 (예: `https://your-app.railway.app`)
2. Health check: `https://your-app.railway.app/health`
3. API 문서: `https://your-app.railway.app/docs`

### 5. 프론트엔드 연결

프론트엔드의 GitHub Secrets에 배포된 URL 추가:
- `VITE_TRIAGE_API_BASE_URL` = `https://your-app.railway.app`

## 대안: Render 배포

Railway가 계속 문제가 있으면 Render를 사용할 수 있습니다:

1. https://render.com 접속
2. New → Web Service
3. GitHub 레포지토리 연결
4. 설정:
   - **Root Directory**: `petcare_advisor`
   - **Build Command**: `pip install -r ../requirements.txt && pip install -e .`
   - **Start Command**: `PYTHONPATH=src python -m uvicorn petcare_advisor.main:app --host 0.0.0.0 --port $PORT`
   - **Environment**: Python 3

## 대안: Fly.io 배포

1. https://fly.io 접속
2. `flyctl` 설치
3. `fly launch` 실행
4. 설정 파일 자동 생성 후 수정

