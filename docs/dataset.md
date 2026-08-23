# 데이터셋 컬럼

AI4I 2020 Predictive Maintenance Dataset은 식별자, 제품 품질 등급, 설비 운전 조건과 고장 레이블을 포함합니다.

## 주요 컬럼

| 컬럼 | 설명 | 단위 또는 값 | 모델 역할 |
| --- | --- | --- | --- |
| `UDI` | 관측값의 고유 식별자 | 1–10,000 | 식별자(입력 제외) |
| `Product ID` | 제품 등급 문자와 일련번호로 구성된 제품 식별자 | 예: `M14860` | 식별자(입력 제외) |
| `Type` | 제품 품질 등급 | `L`(Low), `M`(Medium), `H`(High) | 입력 특성(Feature) |
| `Air temperature [K]` | 공기 온도 | K | 입력 특성(Feature) |
| `Process temperature [K]` | 공정 온도 | K | 입력 특성(Feature) |
| `Rotational speed [rpm]` | 회전 속도 | rpm | 입력 특성(Feature) |
| `Torque [Nm]` | 토크 | Nm | 입력 특성(Feature) |
| `Tool wear [min]` | 누적 공구 마모 시간 | min | 입력 특성(Feature) |
| `Machine failure` | 하나 이상의 고장 유형이 발생했는지 여부 | `0` 또는 `1` | 기본 출력 레이블(Label) |
| `TWF` | 공구 마모 고장(Tool Wear Failure) 여부 | `0` 또는 `1` | 고장 유형 레이블 |
| `HDF` | 방열 고장(Heat Dissipation Failure) 여부 | `0` 또는 `1` | 고장 유형 레이블 |
| `PWF` | 동력 고장(Power Failure) 여부 | `0` 또는 `1` | 고장 유형 레이블 |
| `OSF` | 과부하 고장(Overstrain Failure) 여부 | `0` 또는 `1` | 고장 유형 레이블 |
| `RNF` | 무작위 고장(Random Failure) 여부 | `0` 또는 `1` | 고장 유형 레이블 |

## 활용 시나리오별 입력과 출력

| 활용 시나리오 | 입력 | 출력 또는 평가 기준 |
| --- | --- | --- |
| 설비 상태 조회(Monitoring) | 설비 운전 데이터 | 현재 상태와 측정값 |
| 고장 위험 분류(Classification) | 설비 운전 데이터 | `Machine failure` 또는 `TWF`, `HDF`, `PWF`, `OSF`, `RNF` |
| 이상 조건 탐색(Anomaly Detection) | 설비 운전 데이터 | 이상 점수, `Machine failure`를 평가용 정답으로 활용 |

`Machine failure`는 `0`이면 고장 없음, `1`이면 고장 발생을 나타내는 이진 분류(Binary Classification) 레이블입니다.

## 데이터 샘플

아래는 원본 CSV의 첫 3개 관측값입니다.

| UDI | Product ID | Type | Air temperature [K] | Process temperature [K] | Rotational speed [rpm] | Torque [Nm] | Tool wear [min] | Machine failure | TWF | HDF | PWF | OSF | RNF |
| ---: | --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | M14860 | M | 298.1 | 308.6 | 1551 | 42.8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2 | L47181 | L | 298.2 | 308.7 | 1408 | 46.3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| 3 | L47182 | L | 298.1 | 308.5 | 1498 | 49.4 | 5 | 0 | 0 | 0 | 0 | 0 | 0 |
