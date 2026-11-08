# 2단계 홈페이지 시안 검증

기준일: 2026-11-08. `dist/index.html`을 로컬 브라우저에서 확인했습니다.

| 확인 항목 | 결과 |
| --- | --- |
| 메뉴 | Research, People, Publications, Presentations, News, About BR, Maps, Link (Data / SW) 8개 표시 및 전환 |
| 논문 목록 | 106건, Dataset 필터 3건, First author 필터 23건 |
| 검색 | Wiedemann 검색 1건; 결과 없는 검색과 Reset 정상 |
| 상세보기 | 저자 전체·날짜·DOI·인용문 표시, 닫기 정상 |
| 인용문 복사 | 클립보드 내용과 성공 알림 확인 |
| 목록 추가 표시 | 20건에서 40건으로 증가 |
| 발표 목록 | 158건; 같은 제목의 Oral과 Poster 2건을 별개로 유지 |
| 구성원 | Members 7명, Alumni 6명, Visitors 2명; 사용자 수정 사항 반영 |
| 뉴스 | 기존 홈페이지의 실제 뉴스 7건 |
| 프로필 | 경력·학력·수상·연구 소개 표시 |
| 지도 | 협력 9건; 방문 기록 81건을 78개 좌표에 묶어 표시, 장소 선택·검색 정상 |
| 자료 링크 | 13건; LaNN 검색 3건 |
| 넓은 화면 | 약 1,348 CSS px에서 첫 화면과 지도 배치 확인 |
| 좁은 화면 | 브라우저 확대를 사용한 449 CSS px에서 페이지 가로 넘침 없음; 별도 실제 모바일 기기 검증은 아님 |
| 실행 오류 | 해당 홈페이지 주소의 브라우저 콘솔 오류 없음 |
| 빌드 | Python 표준 라이브러리로 독립 HTML 생성, JavaScript 문법 검사 통과 |

## 남은 검토 범위

- 구성원·프로필·뉴스는 기존 공개 홈페이지를 바탕으로 옮겼으며, 현재 상태로 새로 확인한 내용은 아닙니다.
- 원본 데이터의 확인 항목은 `data/import_report.json`과 `VALIDATION.md`에 남아 있습니다.
- 외부 링크의 현재 서비스 상태는 전체 검증하지 않았습니다.
- GitHub 저장소 생성·업로드 및 공개 호스팅 배포는 이 단계에 포함하지 않았습니다.

## 사용자 수정 반영

- 논문·발표 및 첫 화면 목록에서 저자를 생략 없이 전원 표시하도록 변경했습니다. 저자 9명인 논문 목록을 브라우저에서 확인했습니다.
- Seunghyun OH, Nirma KUMARI, Aadil Fayaz WANI를 Alumni로 이동하고 해당 분류를 확인했습니다.
- Dipanwita Bhattacharjee를 새 포닥으로 추가했습니다. 연구 소개는 `Thermoelectric materials and interfaces for solid state cooling`입니다.
- Ji Hui SON의 소개에 thermoelectric data를 추가했습니다.

지도는 Natural Earth 육지 윤곽과 원본 좌표를 이용한 정적 SVG입니다. 위치 선택·검색을 지원하며, 상세 지도는 OpenStreetMap 링크로 엽니다. 방문 기록에는 연구 방문 외 여행·생활 위치도 포함되어 있습니다.
