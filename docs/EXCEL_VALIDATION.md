# Excel 기반 홈페이지 검증

검증일: 2026-11-08

- 10개 입력 시트를 실제 Excel 파일로 생성하고 모든 시트를 렌더링해 확인했습니다.
- 기존 사람 15명, 연구 7개, 프로필 32행, 뉴스 7개, 자료 13개, 위치 90행을 보존했습니다.
- 논문 106개와 발표 158개는 Zotero 서지정보와 별도 고정 ID를 유지합니다. 해설은 Excel에서 따로 입력합니다.
- 행사는 빈 입력 양식으로 두었습니다. 확인되지 않은 행사 내용을 추가하지 않았습니다.
- 실제 입력 파일로 CSV 가져오기, Excel 변환, 독립 HTML 빌드를 모두 완료했습니다.
- 고정 ID 연결, 비공개 원본 열 제거, 잘못된 입력 차단, 실패 시 기존 출력 보존, 이미지·첨부 경로 검증을 자동 검사합니다.
- 브라우저에서 8개 메뉴 전환, People의 Members/Alumni 분류, 전체 저자 표시, 논문 검색과 상세보기, 발표 목록과 Events 빈 상태를 확인했습니다.
- 요청한 인물 수정: Seunghyun OH·Nirma KUMARI·Aadil Fayaz WANI는 Alumni, Dipanwita Bhattacharjee는 Post-doc., Ji Hui SON은 thermoelectric data를 포함합니다.
- CSV 준비 도구는 허용된 17개 열만 남깁니다. 원본의 Notes, Extra, 첨부파일 경로를 업로드용 CSV에 포함하지 않습니다. 브라우저 도구와 Python 출력도 일치했습니다.

원본 서지정보의 확인 대상 35개는 `VALIDATION.md`에 설명되어 있습니다. 미해결 ID 연결은 0개입니다. 외부 링크의 서비스 상태를 전부 검사하거나, 기존 홈페이지의 모든 인물·경력을 새로 사실 확인한 것은 아닙니다.

`UI_VALIDATION.md`는 앞선 시안 단계의 검증 기록입니다. GitHub Pages의 실제 게시 여부는 저장소 Actions의 최신 실행과 Settings → Pages에서 확인합니다.
