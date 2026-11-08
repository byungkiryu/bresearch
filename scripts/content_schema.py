"""Workbook contract shared by the editor template and content importer.

Row 1: exact machine keys, row 2: Korean help, row 3+: content.
Lists: newline for details/entries; semicolon for keywords/tags;
links: one ``label|https://...`` per line. Blank public means true.
"""
from __future__ import annotations

SCHEMA_VERSION = 1
SHEETS = {
    "사람": ["id", "name", "category", "title", "affiliation", "period", "description", "url", "image", "image_alt", "order", "public"],
    "행사": ["id", "title", "category", "start_date", "end_date", "place", "description", "status", "url", "image", "image_alt", "order", "public"],
    "홈": ["key", "value"],
    "연구": ["id", "title", "kicker", "description", "details", "keywords", "links", "image", "image_alt", "order", "public"],
    "프로필": ["id", "kind", "key", "value", "period", "title", "organization", "entries", "url", "order", "public"],
    "뉴스": ["id", "date", "title", "body", "url", "image", "image_alt", "featured", "order", "public"],
    "자료": ["id", "category", "title", "description", "url", "image", "image_alt", "order", "public"],
    "위치": ["id", "group", "name", "place", "lat", "lon", "description", "url", "image", "image_alt", "order", "public"],
    "논문해설": ["id", "title_reference", "summary", "image", "image_alt", "tags", "links", "person_ids", "featured", "order", "public"],
    "발표해설": ["id", "title_reference", "summary", "image", "image_alt", "tags", "links", "person_ids", "event_id", "featured", "order", "public"],
}
PROFILE_KINDS = ("scalar", "education", "career", "award", "about", "link")
PROFILE_SCALARS = ("name", "role", "institution", "location", "email", "description", "image", "image_alt")
HOME_DEFAULTS = {
    "site_title": "Byungki Ryu · Thermo-Electric Science",
    "site_description": "Thermoelectric science, materials physics, computation, data, and experiment.",
    "site_subtitle": "Thermo-Electric Science · KERI",
    "hero_kicker": "THERMO-ELECTRIC SCIENCE · KERI",
    "hero_title": "Thermoelectric science,",
    "hero_emphasis": "from atoms to applications.",
    "hero_summary": "",
    "hero_image": "",
    "hero_image_alt": "",
    "primary_label": "Explore publications",
    "primary_url": "#publications",
    "secondary_label": "About Byungki Ryu",
    "secondary_url": "#about",
    "research_heading": "Research directions",
    "research_description": "",
    "featured_publication_ids": "",
    "footer_text": "Byungki Ryu · Thermo-Electric Science",
    "footer_location": "Changwon, South Korea",
}
HELP = {
    "id": "고유 ID · 기존 값 유지 · 새 행은 중복 없는 ID",
    "name": "이름", "category": "분류", "title": "제목 / 직함", "affiliation": "소속",
    "period": "기간 · 자유 텍스트", "description": "설명", "url": "https:// 주소 · 비워도 됨",
    "image": "assets/ 아래 이미지 상대경로 · 예: assets/people/name.jpg",
    "image_alt": "이미지 대체 설명", "order": "표시 순서 · 숫자 · 빈칸은 행 순서",
    "public": "공개 여부 · TRUE/FALSE · 빈칸은 TRUE",
    "kind": "scalar/education/career/award/about/link",
    "start_date": "행사 시작일 YYYY-MM-DD · 모르면 빈칸", "end_date": "행사 종료일 YYYY-MM-DD · 모르면 빈칸",
    "place": "장소", "key": "설정 키 · 기존 키 유지", "value": "설정 값",
    "kicker": "연구 소제목", "details": "세부 설명 · 줄바꿈으로 구분",
    "keywords": "키워드 · 세미콜론(;)으로 구분", "links": "한 줄에 표시명|https://주소",
    "organization": "기관", "entries": "항목 · 줄바꿈으로 구분", "date": "날짜 YYYY-MM-DD · 모르면 빈칸",
    "body": "본문", "featured": "강조 여부 · TRUE/FALSE · 빈칸은 FALSE",
    "group": "collaborations 또는 visits", "lat": "위도 -90~90", "lon": "경도 -180~180",
    "title_reference": "Zotero 제목 참고용 · 제목 수정은 Zotero에서", "summary": "홈페이지 해설",
    "tags": "추가 태그 · 세미콜론(;)으로 구분", "event_id": "행사 시트 ID 연결 · 발표 날짜는 Zotero 유지",
    "status": "행사 상태 · 미확인/예정/확정/완료 등 직접 입력",
    "person_ids": "관련 인물 ID · 세미콜론(;) 구분 · 사람 시트 ID 사용",
}


def sheet_headers(name):
    return list(SHEETS[name])


def sheet_help(name):
    return [HELP.get(key, key) for key in SHEETS[name]]
