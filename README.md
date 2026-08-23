# Manufacturing MCP

제조 설비 데이터를 탐색하고 고장 위험을 분석하는 MCP(Model Context Protocol) 기반 AI Agent 프로젝트입니다.

## 데이터셋

이 프로젝트는 **AI4I 2020 Predictive Maintenance Dataset**을 사용합니다. 실제 산업 현장의 예지보전 데이터를 모사하여 생성된 합성 데이터셋으로, 총 10,000개의 설비 운전 관측값과 14개 열로 구성되어 있습니다. 결측값은 없습니다.

각 관측값에는 **제품 등급, 공기 및 공정 온도, 회전 속도, 토크, 공구 마모 시간**과 함께 **설비 고장 여부** 및 **고장 유형**이 기록되어 있습니다. 따라서 아래와 같은 예지보전 시나리오에 활용할 수 있습니다.
- **설비 상태 조회 (Monitoring)**
- **고장 위험 분류 (Classification)**
- **이상 조건 탐색 (Anomaly Detection)** 

### 주요 컬럼

| 컬럼 | 설명 | 단위 또는 값 |
| --- | --- | --- |
| `UDI` | 관측값의 고유 식별자 | 1–10,000 |
| `Product ID` | 제품 등급 문자와 일련번호로 구성된 제품 식별자 | 예: `M14860` |
| `Type` | 제품 품질 등급 | `L`(Low), `M`(Medium), `H`(High) |
| `Air temperature [K]` | 공기 온도 | K |
| `Process temperature [K]` | 공정 온도 | K |
| `Rotational speed [rpm]` | 회전 속도 | rpm |
| `Torque [Nm]` | 토크 | Nm |
| `Tool wear [min]` | 누적 공구 마모 시간 | min |
| `Machine failure` | 하나 이상의 고장 유형이 발생했는지 여부 | `0` 또는 `1` |
| `TWF` | 공구 마모 고장(Tool Wear Failure) 여부 | `0` 또는 `1` |
| `HDF` | 방열 고장(Heat Dissipation Failure) 여부 | `0` 또는 `1` |
| `PWF` | 동력 고장(Power Failure) 여부 | `0` 또는 `1` |
| `OSF` | 과부하 고장(Overstrain Failure) 여부 | `0` 또는 `1` |
| `RNF` | 무작위 고장(Random Failure) 여부 | `0` 또는 `1` |

### 데이터 샘플

아래는 원본 CSV의 첫 3개 관측값입니다.

| UDI | Product ID | Type | Air temperature [K] | Process temperature [K] | Rotational speed [rpm] | Torque [Nm] | Tool wear [min] | Machine failure | TWF | HDF | PWF | OSF | RNF |
| ---: | --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | M14860 | M | 298.1 | 308.6 | 1551 | 42.8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2 | L47181 | L | 298.2 | 308.7 | 1408 | 46.3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| 3 | L47182 | L | 298.1 | 308.5 | 1498 | 49.4 | 5 | 0 | 0 | 0 | 0 | 0 | 0 |

## 출처 및 저작권

- 데이터셋: *AI4I 2020 Predictive Maintenance Dataset* (2020), UCI Machine Learning Repository, [https://doi.org/10.24432/C5HS5C](https://doi.org/10.24432/C5HS5C)
- 관련 논문: Stephan Matzka, “Explainable Artificial Intelligence for Predictive Maintenance Applications,” *2020 Third International Conference on Artificial Intelligence for Industries (AI4I)*, pp. 69–74, [https://doi.org/10.1109/AI4I49448.2020.00023](https://doi.org/10.1109/AI4I49448.2020.00023)
- 데이터셋 라이선스: [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/). 데이터셋의 공유 및 수정은 허용되며, 사용 시 원저작자와 출처를 적절히 표시해야 합니다.
