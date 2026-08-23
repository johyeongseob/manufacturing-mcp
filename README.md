# Manufacturing MCP

제조 설비 데이터를 탐색하고 고장 위험을 분석하는 MCP(Model Context Protocol) 기반 AI Agent 프로젝트입니다.

## DEMO

데모 웹서버 만들기


## 데이터셋

이 프로젝트는 **AI4I 2020 Predictive Maintenance Dataset**을 사용합니다. 실제 산업 현장의 예지보전 데이터를 모사하여 생성된 합성 데이터셋으로, 총 10,000개의 설비 운전 관측값과 14개 열로 구성되어 있습니다. 결측값은 없습니다.

각 관측값에는 **제품 등급, 공기 및 공정 온도, 회전 속도, 토크, 공구 마모 시간**과 함께 **설비 고장 여부** 및 **고장 유형**이 기록되어 있습니다. 따라서 아래와 같은 예지보전 시나리오에 활용할 수 있습니다.
- **설비 상태 조회 (Monitoring)**
- **고장 위험 분류 (Classification)**
- **이상 조건 탐색 (Anomaly Detection)** 

### 데이터셋 상세 정보

각 컬럼의 의미와 단위, 데이터 샘플은 [데이터셋 문서](docs/dataset.md)에서 확인할 수 있습니다.

## 개발 환경 구성

이 프로젝트는 Python 3.12 이상을 사용합니다. WSL Ubuntu 24.04의 프로젝트 루트에서 가상환경을 활성화하고 개발 의존성을 설치합니다.

```bash
source mcp/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

`.env.example`을 참고해 로컬 `.env` 파일을 작성합니다. 실제 API Key가 들어 있는 `.env`는 Git에 포함되지 않습니다.

```bash
cp -n .env.example .env
chmod 600 .env
```


## PostgreSQL

이 프로젝트는 Docker Compose로 PostgreSQL 16을 실행하고, AI4I 2020 CSV의 관측값을 `manufacturing` 데이터베이스의 `observations` 테이블에 저장합니다.

```text
data/ai4i2020.csv
  → Python 적재 파이프라인
  → PostgreSQL observations 테이블
  → MCP Server 조회
```

현재 데이터베이스에는 전체 관측값 10,000개가 저장되어 있으며, 고장 없음 9,661개와 고장 발생 339개로 구성됩니다.

PostgreSQL 실행부터 데이터 적재까지 다음 순서로 진행합니다.

```bash
# PostgreSQL 실행 및 상태 확인
docker compose up -d postgres
docker compose ps

# observations 테이블 생성 또는 갱신
alembic upgrade head

# CSV 데이터 적재
python -m manufacturing_mcp.pipeline.load_dataset

# 적재 결과 확인
docker compose exec postgres \
  psql -U manufacturing -d manufacturing \
  -c "SELECT COUNT(*) FROM observations;"
```

데이터베이스 구성과 조회 방법은 [PostgreSQL 문서](docs/postgres.md), `observations` 컬럼의 의미는 [데이터셋 문서](docs/dataset.md)를 참고합니다.

## 출처 및 저작권

- 프로젝트 코드: Copyright © 2026 Johyeongseob. [MIT License](LICENSE)에 따라 배포됩니다.
- 데이터셋: *AI4I 2020 Predictive Maintenance Dataset* (2020), UCI Machine Learning Repository, [https://doi.org/10.24432/C5HS5C](https://doi.org/10.24432/C5HS5C)
- 관련 논문: Stephan Matzka, “Explainable Artificial Intelligence for Predictive Maintenance Applications,” *2020 Third International Conference on Artificial Intelligence for Industries (AI4I)*, pp. 69–74, [https://doi.org/10.1109/AI4I49448.2020.00023](https://doi.org/10.1109/AI4I49448.2020.00023)
- 데이터셋 라이선스: [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/). 데이터셋의 공유 및 수정은 허용되며, 사용 시 원저작자와 출처를 적절히 표시해야 합니다.
