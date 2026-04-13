# 향후 작업 메모

사용자의 요청에 따라, 차후 질문 시 최우선으로 안내하고 진행할 내용입니다.

## 질문 시나리오
- **사용자**: "우리가 무얼 해야 하지?"
- **응답**: "관리자 대시보드 리포트 탭에서 발생하는 `column schedule_1.group_id does not exist` 에러를 가장 먼저 해결해야 합니다."

## 에러 상세 정보
- **메시지**: `출석 기록 로드 오류: {'message': "column schedule_1.group_id does not exist", 'code': '42703', 'hint': None, 'details': None}`
- **현상**: 관리자 대시보드 `리포트` 메뉴의 `출석 조회` 시 붉은색 에러 바가 표시됨.
- **분석**: `admin_app.py` 또는 `supabase_client.py`에서 `attendance`와 `schedule` 테이블을 조인하여 조회할 때, 존재하지 않는 `group_id` 컬럼을 참조하고 있음. (최근 스케마 변경으로 인해 `class_group_id`로 변경되었을 가능성이 큼)
