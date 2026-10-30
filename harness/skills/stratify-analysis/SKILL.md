---
name: stratify-analysis
description: 수율·불량률·특성치가 변한 원인 후보를 비교한다. 층화, 교란 확인, 기여 분해에 사용한다.
---
# 층화 분석

함수: harness/scaffold/analysis_utils.py (daily_trend, period_compare, stratify, crosstab_counts, naive_vs_stratified, bootstrap_diff, radial_profile, waterfall, save_table, save_fig)

## 순서
1. 시계열: 변화가 계단형인지, 계단이 몇 개인지 보고 이벤트 날짜와 겹쳐 그린다.
2. 측정: 측정 조건이 바뀌었으면 그 효과를 먼저 추정한다. 방법 두 가지를 계산하고 추천을 붙인다.
3. 층화: 가설 요인을 교차한 표에서 셀별 평균·중앙값·단위 수를 본다. 집계 단위를 명시한다.
4. 교란: 요인 간 교차 빈도로 쏠림을 보고, 단순 비교와 층화 비교가 다른 이유를 설명한다.
5. 독립 근거: 다른 종류의 증거(공간·시간·다른 제품)로 같은 결론이 나오는지 본다.
6. 분해: 전체 변화를 요인 기여와 잔차로 나누고 가정을 적는다.
7. 확신 수준: 주 효과에 구간을 붙인다.

결과는 outputs/ 에 저장하고 FINDINGS 에 F-번호로 쓴다. 한 가설만 따로 검정하지 않고 대안과 같은 표에서 비교한다.
