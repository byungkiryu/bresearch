# bresearch

Byungki RYU at KERI — thermoelectrics and materials science.

**Excel, Zotero CSV와 이미지 파일을 바꾸면 홈페이지가 갱신됩니다.** GitHub Actions가 입력을 검사하고 GitHub Pages에 게시합니다. 홈페이지 방문자에게는 Python 설치나 로그인이 필요하지 않습니다.

기존 메뉴 8개를 유지합니다: Research · People · Publications · Presentations · News · About BR · Maps · Link (Data / SW).

## 처음 한 번: 홈페이지 게시

1. 이 프로젝트의 파일과 폴더를 `byungkiryu/bresearch` 저장소의 `main`에 올립니다. `input`, `assets`, `scripts`, `src`, `data`, `content`, `.github` 폴더 구조를 유지합니다.
2. 저장소의 **Settings → Pages → Build and deployment → Source**를 **GitHub Actions**로 선택합니다.
3. **Actions → Update and deploy homepage → Run workflow → main → Run workflow**를 누릅니다.
4. `build`, `deploy`가 모두 초록색으로 완료되면 Pages에 표시된 홈페이지 주소를 엽니다. 기본 주소는 [https://byungkiryu.github.io/bresearch/](https://byungkiryu.github.io/bresearch/)입니다.

저장소를 만든 것만으로 홈페이지가 게시되지는 않습니다. 첫 배포가 성공해야 위 주소에서 볼 수 있습니다. 기존 [Streamlit 홈페이지](https://byungkiryu.streamlit.app/)는 별도로 유지됩니다.

## 평소에 바꾸는 파일

| 수정할 내용 | 바꿀 파일 |
| --- | --- |
| 사람, 행사, 첫 화면, 연구, 프로필, 뉴스, 자료, 위치 | `input/content.xlsx` |
| 논문 서지정보·전체 저자·Zotero 태그 | `input/zotero-publications.csv` |
| 발표 서지정보·전체 저자·날짜·Zotero 태그 | `input/zotero-presentations.csv` |
| 논문·발표의 별도 해설, 그림, 관련 인물, 추가 링크 | Excel의 `논문해설`, `발표해설` 시트 |
| 사진·그림·공개 첨부자료 | `assets/` 아래 파일 |

수정한 파일을 GitHub의 같은 경로에 교체하고 **Commit changes**를 누르면 자동으로 검사·배포합니다. 여러 파일이 연결되어 있으면 함께 올립니다. 예를 들어 새 사진과 그 사진 경로를 적은 Excel은 한 번에 올리는 편이 좋습니다.

GitHub 웹 화면에서는 폴더를 연 뒤 **Add file → Upload files**로 교체할 수 있습니다. Excel은 기존 파일을 다운로드하여 수정한 뒤 동일한 이름으로 올립니다. 파일명·폴더명의 대소문자도 그대로 맞춥니다.

## Excel 입력 방법

`input/content.xlsx`에는 다음 시트가 있습니다.

| 시트 | 입력 내용 |
| --- | --- |
| 사람 | 이름, 구분, 직함, 소속, 기간, 소개, 사진·링크 |
| 행사 | 행사명, 날짜, 장소, 소개, 상태, 관련 자료 |
| 홈 | 첫 화면 제목·설명·버튼·대표 논문 |
| 연구 | 연구 주제, 설명, 키워드, 그림·링크 |
| 프로필 | Byungki Ryu 소개, 학력, 경력, 수상·외부 링크 |
| 뉴스 | 날짜, 제목, 본문, 사진·링크 |
| 자료 | 데이터·소프트웨어·외부 자료 |
| 위치 | 협력·방문 기관과 지도 좌표 |
| 논문해설 | 홈페이지 고정 ID별 해설, 그림, 태그·링크 |
| 발표해설 | 홈페이지 고정 ID별 해설, 그림, 태그·링크, 행사 연결 |

- **1행은 프로그램용 열 이름, 2행은 입력 설명, 3행부터 실제 내용**입니다. 1·2행과 시트 이름을 유지합니다.
- 기존 `id`는 유지합니다. 새 사람·행사 등을 추가할 때는 중복되지 않는 ID를 씁니다.
- `public`은 `TRUE`이면 표시, `FALSE`이면 홈페이지에서 숨김입니다. 빈칸은 표시합니다. **공개 GitHub 저장소에 올린 내용은 `FALSE`여도 저장소에서 볼 수 있습니다.**
- 날짜는 `YYYY-MM-DD`, 이미지 경로는 `assets/people/name.jpg`처럼 입력합니다. `order`는 표시 순서이며 작은 숫자가 먼저 나옵니다.
- `tags`, `keywords`, `person_ids`는 세미콜론(`;`)으로 구분합니다. 여러 링크는 한 줄에 하나씩 `표시명|https://주소`로 입력합니다.
- `title_reference`는 참고용 제목입니다. 논문·발표 제목, 저자와 날짜의 수정은 Zotero에서 합니다.
- 발표를 행사와 연결하려면 `발표해설.event_id`에 `행사.id`를 적습니다. 발표 날짜 자체는 Zotero 값을 사용합니다.

사람 구분과 연구 소개에는 요청된 수정이 반영되어 있습니다. SH Oh, Nirma, Aadil은 Alumni이며 Dipanwita Bhattacharjee는 새 박사후연구원으로 표시합니다. Ji Hui SON 소개에는 thermoelectric data가 포함됩니다. 저자는 `et al.`로 줄이지 않고 입력된 전체 저자를 표시합니다.

## 행사 전용 페이지

행사별 안내와 프로그램은 `src/events/<행사주소>/index.html`에 보관합니다. 빌드하면 같은 경로의 `events/<행사주소>/`로 게시되므로, 행사 종료 뒤에도 파일을 유지하면 주소가 계속 유지됩니다. 각 페이지는 CSS와 인쇄 버튼을 포함한 독립 HTML입니다. 새 행사에는 폴더를 추가하고 제목·날짜·프로그램을 수정합니다.

2026년 11월 20일 워크숍은 `src/events/2026-11-20/index.html`에서 관리하며, `https://byungkiryu.github.io/bresearch/events/2026-11-20/`에 게시됩니다. 화면의 **Print / Save as PDF**로 A4 세로 프로그램을 출력할 수 있습니다. 행사 상세 일정은 이 HTML에서 수정하고, 홈페이지 뉴스와 행사 목록의 제목·기간·링크는 `input/content.xlsx`에서 관리합니다. 인쇄 시 A4 세로, 배율 100%, 브라우저 머리글·바닥글 끄기를 사용합니다.

## 방문자 지도

**Maps → Visitors**에서 MapMyVisitors 방문자 지도와 통계 링크를 볼 수 있습니다. 직접 주소는 `https://byungkiryu.github.io/bresearch/#maps?view=visitors`이며, 상세 방문 통계는 `https://mapmyvisitors.com/web/1c9dp`에서 확인합니다.

홈페이지의 어느 메뉴로 처음 들어오든 위젯을 한 번 실행합니다. 같은 문서 안에서 메뉴·검색·필터를 바꿔도 위젯을 다시 만들지 않습니다. 독립 행사 페이지는 이 집계에 포함하지 않습니다. 로컬 파일이나 미리보기 환경은 집계하지 않고, `byungkiryu.github.io/bresearch/`에서만 방문자 서비스를 불러옵니다. 홈페이지 주소를 바꾸면 `src/app.js`의 `initVisitorWidget()` 호스트 조건과 서비스 등록 주소를 함께 수정합니다.

위치는 IP 기반 추정치이며, 서비스의 방문자 수는 IP당 하루 1회 기준입니다. 일별 방문자 수의 합은 장기간 중복을 제거한 실인원과 다릅니다. 설치 이전 방문 기록을 소급 생성하지 않습니다. 외부 서비스나 차단 프로그램 때문에 지도가 열리지 않으면 안내문과 통계 링크를 표시합니다. 방문자 지도에는 인터넷 연결이 필요합니다.

## Zotero 목록 갱신

논문과 발표를 Zotero에서 각각 **CSV**로 내보냅니다. Zotero CSV에는 `Notes`, `Extra`, `File Attachments`, `Link Attachments`, 로컬 파일 경로가 포함될 수 있으므로 **원본을 공개 저장소에 바로 올리지 않습니다.**

Python 없이 준비하려면 저장소의 `tools/prepare-zotero.html`을 다운로드하여 브라우저에서 엽니다. 원본 CSV를 선택하고 내려받은 정리된 CSV를 `input/`의 같은 이름 파일과 교체합니다. 원본은 컴퓨터에 보관합니다.

Python을 사용하는 경우에는 다음처럼 정리합니다. 논문 또는 발표 한 종류만 바꿀 때는 해당 옵션만 씁니다.

```bash
python scripts/prepare_zotero.py --papers "원본-논문.csv" --presentations "원본-발표.csv"
```

출력 이름은 `input/zotero-publications.csv`, `input/zotero-presentations.csv`입니다. 이 도구는 홈페이지에 필요한 열을 남기며 Zotero Key와 서지정보를 보존합니다.

Zotero의 Key가 바뀌어도 홈페이지는 별도의 고정 ID와 DOI 등으로 기존 항목을 연결합니다. 확실하지 않은 연결은 자동으로 확정하지 않고 검사를 중단합니다. `data/registry.json`, `data/identity-map.csv`는 이 연결을 보존하므로 삭제하거나 새로 만들지 않습니다. 충돌 처리 방법은 [데이터 명세](docs/DATA_SPEC.md)를 참고합니다.

새 논문·발표는 Zotero CSV만 추가해도 목록에 표시됩니다. 별도 해설을 쓰려면 배포 후 `data/identity-map.csv`에서 해당 고정 ID를 확인하고 Excel 해설 시트에 행을 추가합니다. 기존 해설 행의 ID를 바꾸지 않습니다.

## 확인과 오류 처리

GitHub의 **Actions**에서 가장 최근 실행을 확인합니다. 입력 오류가 있으면 배포를 중단하고 이전에 게시된 홈페이지를 유지합니다. **build → Show import diagnostics**를 열면 Excel의 시트·행·열·오류 설명과 Zotero의 Key·연결 후보 ID를 확인할 수 있습니다. 오류·검토 대기·경고는 각각 앞의 30개까지 표시합니다. 표시된 항목을 수정하고 다시 실행하거나 로컬 `reports/`에서 전체를 확인합니다. 이 로그에는 원본 입력 행과 첨부파일 경로를 복사하지 않습니다.

빌드 도중 `main changed during the build`가 나오면 그 사이 다른 수정이 올라온 것입니다. 후속 실행이 최신 파일을 처리합니다. 후속 실행이 없으면 **Run workflow**를 누릅니다. 생성된 고정 ID를 덮어쓰지 않도록 이 경우에는 자동 병합하거나 강제 푸시하지 않습니다.

`Preserve stable IDs` 단계에서 권한 오류가 나면 저장소의 **Settings → Actions → General → Workflow permissions**와 `main` 보호 규칙이 Actions의 데이터 저장을 허용하는지 확인합니다. 별도 토큰을 Excel이나 코드에 입력할 필요는 없습니다.

로컬에서 미리 확인하려면 Python 3.10 이상에서 실행합니다.

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/update.py
```

완료 후 `dist/index.html`을 엽니다. 배포되는 파일은 `dist/`이며, 홈페이지용 코드와 입력 자료 전체를 웹사이트 산출물에 그대로 복사하지 않습니다. 외부 논문·도구 링크에는 인터넷 연결이 필요합니다.

파일을 바꾸지 않고 검사만 하려면 `python scripts/update.py --check`를 실행합니다. 이 명령은 `data`, `content`, `dist`를 바꾸지 않고 검사 결과만 `reports/`에 남깁니다.

## 자동 생성 파일과 코드

일상적인 콘텐츠 수정은 위의 입력 파일에서 합니다. 다음 파일은 자동 생성되거나 화면 구현에 사용됩니다.

| 위치 | 역할 |
| --- | --- |
| `data/registry.json`, `data/identity-map.csv` | Zotero Key와 홈페이지 고정 ID 연결·보존 |
| `data/publications.json`, `data/presentations.json`, `data/import_report.json` | 변환된 서지정보와 가져오기 결과 |
| `content/site.json`, `content/items.json` | Excel에서 생성된 화면 콘텐츠 |
| `src/` | 화면 구성·스타일·검색·필터 |
| `scripts/update.py` | 입력 검증, 변환, 사이트 생성 |
| `.github/workflows/pages.yml` | 검사, 고정 ID 저장, GitHub Pages 배포 |

Actions는 성공적으로 생성된 데이터가 바뀌었을 때만 `Update generated homepage data [skip ci]` 커밋을 남깁니다. 수동 입력과 생성 데이터를 구분하여 변경 이력을 확인할 수 있습니다.

## 출처

- 기존 홈페이지: [byungkiryu.streamlit.app](https://byungkiryu.streamlit.app/)
- 원본 공개 저장소: [byungkiryu/byungkiryu](https://github.com/byungkiryu/byungkiryu), 사용한 commit `23a1be7b36725e95268465599db9d23e3e10ca1c`
- 최초 논문·발표 목록: 사용자가 제공한 2026-11-08 Zotero CSV
- 지도 윤곽: [Natural Earth](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_land.geojson), public domain

