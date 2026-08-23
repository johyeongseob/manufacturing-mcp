# Manufacturing MCP

제조 설비 데이터를 탐색하고 고장 위험을 분석하는 MCP(Model Context Protocol) 기반 AI Agent 프로젝트입니다.

## 데이터셋

이 프로젝트는 **AI4I 2020 Predictive Maintenance Dataset**을 사용합니다. 실제 산업 현장의 예지보전 데이터를 모사하여 생성된 합성 데이터셋으로, 총 10,000개의 설비 운전 관측값과 14개 열로 구성되어 있습니다. 결측값은 없습니다.

각 관측값에는 **제품 등급, 공기 및 공정 온도, 회전 속도, 토크, 공구 마모 시간**과 함께 **설비 고장 여부** 및 **고장 유형**이 기록되어 있습니다. 따라서 아래와 같은 예지보전 시나리오에 활용할 수 있습니다.
- **설비 상태 조회 (Monitoring)**
- **고장 위험 분류 (Classification)**
- **이상 조건 탐색 (Anomaly Detection)** 

### 주요 컬럼

각 컬럼의 의미와 단위는 [데이터셋 컬럼 문서](docs/dataset.md)에서 확인할 수 있습니다.

### 데이터 샘플

아래는 원본 CSV의 첫 3개 관측값입니다.

| UDI | Product ID | Type | Air temperature [K] | Process temperature [K] | Rotational speed [rpm] | Torque [Nm] | Tool wear [min] | Machine failure | TWF | HDF | PWF | OSF | RNF |
| ---: | --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | M14860 | M | 298.1 | 308.6 | 1551 | 42.8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2 | L47181 | L | 298.2 | 308.7 | 1408 | 46.3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| 3 | L47182 | L | 298.1 | 308.5 | 1498 | 49.4 | 5 | 0 | 0 | 0 | 0 | 0 | 0 |

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

코드 변경 후 테스트, 린트, 포맷 검사를 실행합니다.

```bash
pytest
ruff check .
ruff format --check .
```

현재 Python 패키지는 `src/manufacturing_mcp`에, 테스트는 `tests`에 위치합니다. 애플리케이션 설정은 `src/manufacturing_mcp/config.py`에서 환경변수와 `.env` 파일로부터 불러옵니다.

## PostgreSQL 실행

Docker Compose로 PostgreSQL 컨테이너를 백그라운드에서 실행합니다.

```bash
docker compose up -d postgres
docker compose ps
```

`postgres` 서비스의 상태가 `healthy`이면 정상입니다. PostgreSQL에 직접 접속하려면 다음 명령을 사용합니다.

```bash
docker compose exec postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

접속을 종료하려면 `\q`를 입력합니다. 컨테이너를 중지할 때는 다음 명령을 사용합니다.

```bash
docker compose down
```

PostgreSQL 데이터는 `postgres_data` Docker 볼륨에 보존되므로 컨테이너를 중지하거나 다시 만들어도 유지됩니다.

## 출처 및 저작권

- 프로젝트 코드: Copyright © 2026 Johyeongseob. [MIT License](LICENSE)에 따라 배포됩니다.
- 데이터셋: *AI4I 2020 Predictive Maintenance Dataset* (2020), UCI Machine Learning Repository, [https://doi.org/10.24432/C5HS5C](https://doi.org/10.24432/C5HS5C)
- 관련 논문: Stephan Matzka, “Explainable Artificial Intelligence for Predictive Maintenance Applications,” *2020 Third International Conference on Artificial Intelligence for Industries (AI4I)*, pp. 69–74, [https://doi.org/10.1109/AI4I49448.2020.00023](https://doi.org/10.1109/AI4I49448.2020.00023)
- 데이터셋 라이선스: [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/). 데이터셋의 공유 및 수정은 허용되며, 사용 시 원저작자와 출처를 적절히 표시해야 합니다.
