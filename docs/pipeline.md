# 전체 실행 파이프라인

이 문서는 새로운 환경에서 데이터베이스부터 웹 데모까지 준비하는 순서를 설명합니다. 모든 명령은 WSL Ubuntu 24.04의 프로젝트 루트에서 실행합니다.

## 1. 가상환경과 설정

```bash
source mcp/bin/activate
python -m pip install -e ".[dev]"
cp -n .env.example .env
chmod 600 .env
```

`.env`에서 `OPENAI_API_KEY`를 실제 키로 변경합니다. 기본 모델은 `gpt-5-mini`, 임베딩 모델은 `text-embedding-3-small`입니다.

## 2. PostgreSQL 실행

Docker Desktop을 먼저 실행하고 WSL Integration이 활성화되어 있는지 확인합니다.

```bash
docker compose up -d postgres
docker compose ps
```

`postgres`의 상태가 `healthy`이면 정상입니다. 자세한 접속과 조회 방법은 [PostgreSQL 문서](postgres.md)를 참고합니다.

## 3. 스키마 생성

```bash
alembic upgrade head
```

Alembic이 `migrations/versions/20260823_0001_create_observations.py`를 적용하여 `observations` 테이블을 생성하고 현재 버전을 `alembic_version`에 기록합니다.

## 4. CSV 적재

```bash
python -m manufacturing_mcp.pipeline.load_dataset
```

기본 입력은 `data/ai4i2020.csv`입니다. 로더는 CSV 스키마와 값을 검증하고 UDI를 기준으로 upsert하므로 다시 실행해도 중복 행을 만들지 않습니다.

```bash
docker compose exec postgres \
  psql -U manufacturing -d manufacturing \
  -c "SELECT COUNT(*) FROM observations;"
```

정상 적재 결과는 10,000행입니다.

## 5. 통계 계산

```bash
python -m manufacturing_mcp.analysis.statistics
```

PostgreSQL 집계 결과를 `out/statistics.json`에 저장합니다. 이 JSON은 LLM이 직접 수치를 계산하지 않도록 검증된 입력 자료로 재사용됩니다.

## 6. LangGraph 리포트 생성

```bash
python -m manufacturing_mcp.workflows.report
```

LangGraph가 통계 JSON을 검증하고 GPT-5-mini를 호출하여 다음 파일을 생성합니다.

- `reports/failure_summary.md`
- `reports/product_type_analysis.md`
- `reports/tool_wear_analysis.md`

이 단계는 OpenAI API를 세 번 호출하며 각 분석 노드는 병렬로 실행될 수 있습니다.

## 7. 청킹과 임베딩

```bash
python -m manufacturing_mcp.rag.chunker
python -m manufacturing_mcp.rag.embeddings
```

첫 명령은 리포트를 `##` 섹션 단위로 분할하여 `out/report_chunks.json`을 만듭니다. 두 번째 명령은 청크를 `text-embedding-3-small`로 임베딩하여 `out/report_embeddings.json`에 저장합니다.

리포트가 변경되면 리포트를 다시 생성한 뒤 청킹과 임베딩 단계도 다시 실행해야 합니다.

## 8. 검색과 답변 확인

LLM 답변 없이 검색 결과만 확인:

```bash
python -m manufacturing_mcp.rag.retriever \
  "공구 마모 시간이 길어질수록 고장 위험이 높아지니?" \
  --top-k 2
```

RAG 답변 확인:

```bash
python -m manufacturing_mcp.rag.answer \
  "공구 마모 시간이 길어질수록 고장 위험이 높아지니?" \
  --top-k 2
```

통합 라우터 확인:

```bash
python -m manufacturing_mcp.agent.chat \
  "실제 고장 데이터 샘플 2개 보여줘." \
  --show-route
```

## 9. 웹 데모 실행

```bash
python -m uvicorn manufacturing_mcp.api.app:app
```

브라우저에서 다음 주소를 사용합니다.

- 웹 데모: <http://127.0.0.1:8000>
- 상태 확인: <http://127.0.0.1:8000/health>
- Swagger 문서: <http://127.0.0.1:8000/docs>

종료하려면 Uvicorn 터미널에서 `Ctrl+C`를 누릅니다.

## 10. 테스트

```bash
python -m pytest
```

테스트에서는 실제 OpenAI API 호출 대신 테스트 대역을 사용하므로 일반적으로 API 비용이 발생하지 않습니다. 데이터베이스 통합 동작을 직접 실습할 때는 PostgreSQL 컨테이너가 실행 중이어야 합니다.

## 컨테이너 종료

```bash
docker compose down
```

`postgres_data` Docker 볼륨은 유지되므로 컨테이너를 다시 실행해도 적재된 데이터가 보존됩니다.
