# PostgreSQL

이 프로젝트는 Docker Compose로 PostgreSQL 16을 실행하고 AI4I 2020 관측값을 저장합니다.

## 실행 정보

| 항목 | 값 |
| --- | --- |
| 이미지 | `postgres:16-alpine` |
| 데이터베이스 | `manufacturing` |
| 사용자 | `manufacturing` |
| 주소 | `localhost:5432` |
| 볼륨 | `manufacturing-mcp_postgres_data` |

## 스키마와 마이그레이션

첫 마이그레이션인 [`20260823_0001_create_observations.py`](../migrations/versions/20260823_0001_create_observations.py)는 다음 테이블을 생성합니다.

- `alembic_version`: 적용된 마이그레이션 버전 기록
- `observations`: 제조 설비 관측값 저장

`observations`는 `udi`를 기본키로 사용하며, 제품 유형과 고장 여부를 위한 제약조건 및 인덱스를 포함합니다.

## 적재 결과

| 구분 | 개수 |
| --- | ---: |
| 전체 관측값 | 10,000 |
| 고장 없음 | 9,661 |
| 고장 발생 | 339 |

## 실행 및 데이터 적재

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

`docker compose ps`에서 `postgres` 서비스가 `healthy`이면 정상입니다. CSV 로더는 UDI를 기준으로 기존 행을 갱신하므로 다시 실행해도 중복 행을 생성하지 않습니다.

PostgreSQL에 직접 접속하거나 컨테이너를 중지하려면 다음 명령을 사용합니다.

```bash
# PostgreSQL 접속
docker compose exec postgres psql -U manufacturing -d manufacturing

# 컨테이너 중지
docker compose down
```


## 확인 결과

전체 관측값 개수:

```sql
SELECT COUNT(*) FROM observations;
```

```text
 count
-------
 10000
```

UDI 순서의 첫 5개 관측값:

```sql
SELECT * FROM observations ORDER BY udi LIMIT 5;
```

| udi | product_id | product_type | air_temperature | process_temperature | rotational_speed | torque | tool_wear | machine_failure | twf | hdf | pwf | osf | rnf |
| ---: | --- | :---: | ---: | ---: | ---: | ---: | ---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | M14860 | M | 298.1 | 308.6 | 1551 | 42.8 | 0 | false | false | false | false | false | false |
| 2 | L47181 | L | 298.2 | 308.7 | 1408 | 46.3 | 3 | false | false | false | false | false | false |
| 3 | L47182 | L | 298.1 | 308.5 | 1498 | 49.4 | 5 | false | false | false | false | false | false |
| 4 | L47183 | L | 298.2 | 308.6 | 1433 | 39.5 | 7 | false | false | false | false | false | false |
| 5 | L47184 | L | 298.2 | 308.7 | 1408 | 40.0 | 9 | false | false | false | false | false | false |
