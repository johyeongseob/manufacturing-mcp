# 데이터셋 컬럼

AI4I 2020 Predictive Maintenance Dataset은 식별자, 제품 품질 등급, 설비 운전 조건과 고장 레이블을 포함합니다.

## 주요 컬럼

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
