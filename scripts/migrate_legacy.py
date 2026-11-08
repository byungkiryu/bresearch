#!/usr/bin/env python3
"""One-time migration from the archived Streamlit source into editable site content.

Reads workbooks only. The resulting site.json is the ongoing content source;
running this migration again will replace manually edited site.json content.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime
import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit
from openpyxl import load_workbook


def clean(value):
    if value is None or isinstance(value, float) and math.isnan(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def safe_url(value):
    value = clean(value)
    try:
        parsed = urlsplit(value)
        if parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username:
            return value
    except ValueError:
        pass
    return ""


def rows(source, filename, sheet):
    workbook = load_workbook(source / filename, read_only=True, data_only=True)
    iterator = workbook[sheet].values
    headers = next(iterator)
    result = [dict(zip(headers, row)) for row in iterator if any(v is not None for v in row)]
    workbook.close()
    return result


def date_text(value, month_only=False):
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m" if month_only else "%Y-%m-%d")
    return clean(value)


def coordinates(row):
    try:
        lat, lon = float(row["latitude"]), float(row["longitude"])
        if math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon
    except (TypeError, ValueError, KeyError):
        pass
    return None


PROFILE = {
    "name": "Byungki Ryu",
    "role": "Principal Researcher · Professor",
    "institution": "Korea Electrotechnology Research Institute (KERI) · University of Science and Technology (UST)",
    "location": "Changwon, South Korea",
    "email": "byungkiryu@keri.re.kr",
    "description": "A physicist working across thermoelectric energy conversion, materials and interfaces, and computational materials design—from fundamental phenomena to practical devices.",
    "education": [
        {"period": "2005.03–2011.02", "title": "Ph.D. in Physics", "organization": "Korea Advanced Institute of Science and Technology (KAIST)"},
        {"period": "2000.03–2005.02", "title": "B.S. in Physics and Mathematics (double major)", "organization": "Korea Advanced Institute of Science and Technology (KAIST)"}
    ],
    "career": [
        {"period": "2013.12–Present", "title": "Research appointment", "organization": "Korea Electrotechnology Research Institute (KERI)"},
        {"period": "2011.03–2013.12", "title": "Research Staff Member", "organization": "Samsung Advanced Institute of Technology (SAIT)"}
    ],
    "awards": [
        {"period": "2022.10", "title": "논문상", "organization": "한국물리학회"},
        {"period": "2022.09", "title": "우수논문상", "organization": "한국계산과학공학회"},
        {"period": "2022.06", "title": "표창장 최우수상(개인)", "organization": "한국전기연구원"},
        {"period": "2020.10", "title": "한국과학기술이사회 이사장 포상 표창장", "organization": ""},
        {"period": "2020.05.13", "title": "Featured Article", "organization": "Applied Physics Letters"},
        {"period": "2017.07.07", "title": "제27회 과학기술우수논문상", "organization": "한국과학기술단체총연합회"},
        {"period": "2017.01.02", "title": "KERI 대상 우수상(팀)", "organization": "한국전기연구원"},
        {"period": "2016.10.22", "title": "가을추계 우수발표상", "organization": "한국물리학회"},
        {"period": "2016.07.25", "title": "우수논문상", "organization": "한국세라믹학회"},
        {"period": "2012.11", "title": "삼성논문상 금상", "organization": "삼성"},
        {"period": "2011.01", "title": "우수논문상", "organization": "4th BK21 Young Physicists Workshop"},
        {"period": "2007.06", "title": "Kaleidoscope of June", "organization": "Physical Review B"}
    ],
    "links": [
        {"label": "Google Scholar", "url": "https://scholar.google.com/citations?user=fldxgiEAAAAJ"},
        {"label": "LinkedIn", "url": "https://linkedin.com/in/byungki-ryu-9896a222"}
    ],
    "about_sections": [
        {"title": "Research statement", "entries": [
            "Thermoelectric energy conversion spanning fundamental phenomena and practical applications, theoretical modeling and experimental validation, and materials, devices, and system-level integration.",
            "Recent research focuses on enhancing thermoelectric generator performance and understanding incommensurate interphase boundaries.",
            "Broader interests include thermal management, thermoelectric cooling, and temperature-driven information technology."
        ]},
        {"title": "Research expertise", "entries": [
            "Thermoelectric materials and devices: from phenomena to performance.",
            "Defect physics and interface science: alloy design and incommensurate phase boundaries.",
            "Computational methods: first-principles calculations, machine-learning potentials, and finite-element simulations.",
            "Experimental validation: design and analysis of high-performance, reliable devices.",
            "Data-driven research: thermoelectric property data and machine-learning prediction."
        ]},
        {"title": "Research contributions", "entries": [
            "General efficiency theory of thermoelectric conversion and three thermoelectric degrees of freedom.",
            "An algebraic framework for thermoelectric devices under the constant-Seebeck approximation.",
            "Thermoelectric materials and devices, metastable structures, and intrinsic, extrinsic, and complex defects.",
            "Large-scale interface modeling for alloys and interfaces.",
            "Thermoelectric instability and device physics in modules.",
            "Data structures for thermoelectric material properties and device performance.",
            "The pykeri2019 thermoelectric device simulator and LaNN representation for property curves, with core development by Dr. Jaywan Chung.",
            "Supervision of postdoctoral researchers and thermoelectric design projects.",
            "Earlier SAIT research: materials design for thermoelectrics, H₂/CO₂ membranes, LED phosphors, and transparent electrodes."
        ]},
        {"title": "Appointments", "entries": [
            "Principal Researcher, Energy Conversion Research Center, Electrical Materials Division, KERI.",
            "Professor, Electric Energy and Materials Engineering, KERI School, University of Science and Technology."
        ]},
        {"title": "Doctoral thesis", "entries": [
            "First-principles study of the atomic and electronic structures of semiconductor/insulator interfaces and transparent amorphous oxide semiconductors."
        ]},
        {"title": "Methods and software", "entries": [
            "Thermoelectric transport, density-functional theory, and numerical modeling.",
            "VASP, Python, Excel, COMSOL Multiphysics, m3gnet, and SevenNet.",
            "Korean (native) and English (professional working proficiency)."
        ]}
    ]
}


RESEARCH = {
    "intro": "We investigate thermoelectric phenomena and the physics of materials, connecting fundamental understanding with energy conversion and thermal management.",
    "topics": [
        {"id": "devices", "title": "Thermoelectric devices & applications", "kicker": "Conversion & cooling", "description": "From materials interfaces to generator performance and active cooling.", "details": [
            "Thermoelectric material interface design based on solute chemical potentials.",
            "Thermoelectric efficiency and invariance under temperature and geometry transformations.",
            "Thermoelectric metrology for device and module power characteristics.",
            "Chip hot spots and thermoelectric active cooling.",
            "Thermoelectric lifetime modeling."
        ], "keywords": ["Efficiency", "Interfaces", "Thermal management"], "links": []},
        {"id": "transport", "title": "Thermoelectric phenomena & transport", "kicker": "Fundamental physics", "description": "Electronic and phononic transport from first principles.", "details": [
            "First-principles Boltzmann transport calculations for electrons and phonons.",
            "Diffusion and Kim's Law.",
            "Temperature quantization."
        ], "keywords": ["First principles", "Electron–phonon", "Transport"], "links": []},
        {"id": "data-ai", "title": "Data & machine learning", "kicker": "Property curves", "description": "High-quality thermoelectric data and machine-learning representations of temperature-dependent properties.", "details": [
            "teMatDb: an ultra-high-quality thermoelectric material property database and self-consistent ZT filter.",
            "LaNN: an artificial neural-network model predicting thermoelectric property curves.",
            "Online models for BiTe-based materials, PbTe-based materials, and copper alloys."
        ], "keywords": ["teMatDb", "LaNN", "σ(T) · S(T) · κ(T)"], "links": [
            {"label": "teMatDb", "url": "https://tematdb.streamlit.app/"},
            {"label": "BiTe model", "url": "https://jaywan-chung.github.io/ml-tep-BiTe/"},
            {"label": "PbTe model", "url": "https://jaywan-chung.github.io/ml-tep-PbTe/"},
            {"label": "Copper alloys model", "url": "https://jaywan-chung.github.io/ml-copper-poongsan/"}
        ]},
        {"id": "materials", "title": "Thermoelectric materials design", "kicker": "Structure & composition", "description": "Lattice structures, chemical stacking faults, and reference materials for thermoelectric performance.", "details": [
            "Ag-induced chemical stacking faults and metastable BiSbTe thermoelectric alloys.",
            "Lattice similarity for PGEC-like materials.",
            "Reference BiTe thermoelectric alloys: compositions, legs, and thermoelectric generator modules.",
            "Origin of incommensurate structures in higher manganese silicides.",
            "Order–disorder and high-power-factor Bi–Te–Se thermoelectric alloys.",
            "Fermi-surface anisotropy and material texture."
        ], "keywords": ["Metastability", "BiTe", "Lattice similarity"], "links": []},
        {"id": "simulation", "title": "Simulation & circuits", "kicker": "Models to modules", "description": "Thermoelectric simulation across legs, modules, and circuits.", "details": [
            "The pykeri2019 thermoelectric simulator and the TES web simulator.",
            "Finite-element analysis of thermoelectric generator modules.",
            "Thermoelectric circuits."
        ], "keywords": ["pykeri2019", "Finite elements", "TES"], "links": [
            {"label": "Open TESimulator", "url": "https://tes.keri.re.kr/"}
        ]},
        {"id": "defects", "title": "Defect-rich thermoelectric materials", "kicker": "Local environments", "description": "Defects and impurity clusters as a route to understanding thermoelectric materials.", "details": [
            "Defect–impurity clustering in thermoelectric materials."
        ], "keywords": ["Defects", "Impurities", "Clustering"], "links": []},
        {"id": "alloys", "title": "Materials, interfaces & alloys", "kicker": "Beyond periodic structures", "description": "Modeling incommensurate structures and alloy interfaces with first-principles data and machine-learning potentials.", "details": [
            "Modeling methods for incommensurate structures.",
            "A database of single and clustered solutes in alloys.",
            "Graph machine-learning potentials for solutes and interfaces in copper alloys.",
            "Tilted and twisted grain boundaries in Cu–Ni–Si–Mn alloys.",
            "Orientation-independent interface energies."
        ], "keywords": ["ML potentials", "Grain boundaries", "Alloy design"], "links": [
            {"label": "Alloy Design DB", "url": "https://byungkiryu-alloydesigndb-demo-v0-33-main-v0-33-u86ejf.streamlit.app/"}
        ]}
    ]
}


def migrate(source, output):
    people = []
    for row in rows(source, "ZDATA__people.xlsx", "people"):
        if not clean(row.get("name")) or row.get("status") not in {"Members", "Alumni", "Visitors"}:
            continue
        description = clean(row.get("brief")).replace("Mathematcian", "Mathematician").replace("calcualtions", "calculations")
        if row.get("name") == "Johannes de Boor":
            description = "Invited for KERI–DLR collaboration; German Aerospace Center (DLR), Germany."
        people.append({
            "id": f"person-{int(row['id']) + 1:04d}", "name": clean(row["name"]),
            "category": clean(row["status"]), "title": clean(row["title"]),
            "affiliation": clean(row["where_now"]), "period": clean(row["period"]),
            "description": description
        })
    news = []
    for index, row in enumerate(rows(source, "ZDATA__news.xlsx", "news_all"), 1):
        # The source explicitly disables one test row; do not publish test content.
        if clean(row.get("title")).startswith("Test:"):
            continue
        title, body, url = clean(row.get("title")), clean(row.get("description")), safe_url(row.get("link"))
        if title == "Thermoelectric Inequality Paper Published in APL":
            title = "Thermoelectric Inequality Paper Published in Journal of Applied Physics"
            body = body.replace("in APL", "in Journal of Applied Physics")
            url = "https://doi.org/10.1063/5.0247466"
        elif title == "Thermoelectric Algebra Paper Published in APL":
            title = "Thermoelectric Algebra Paper Published in Journal of Applied Physics"
            body = body.replace("thermoelectcric", "thermoelectric")
            url = "https://doi.org/10.1063/5.0242991"
        news.append({"id": f"news-{index:04d}", "date": date_text(row["date"]), "title": title,
                     "body": body, "url": url, "featured": row.get("recentnews") == 1})
    news.sort(key=lambda x: x["date"], reverse=True)
    links = []
    for index, row in enumerate(rows(source, "ZDATA__link_for_DBSW.xlsx", "read"), 1):
        if not clean(row.get("name")):
            continue
        links.append({"id": f"link-{index:04d}", "category": clean(row["contenttype"]),
                      "title": clean(row["name"]).replace("Physicst", "Physicist"),
                      "description": clean(row["content"]).replace("devloped", "developed").replace("Engined by", "Powered by"),
                      "url": safe_url(row["link"])})
    collaborations, visits = [], []
    omitted = {"collaborations": 0, "visits": 0}
    for index, row in enumerate(rows(source, "ZDATA_map_collaborations.xlsx", "read"), 1):
        position = coordinates(row)
        if not position:
            omitted["collaborations"] += 1
            continue
        name = clean(row["site"])
        description = " · ".join(x for x in (clean(row["who"]), clean(row["Collaboration"])) if x and x != "We are")
        collaborations.append({"id": f"collaboration-{index:04d}", "name": name,
                               "place": clean(row["City"]).replace("Changon", "Changwon"),
                               "lat": position[0], "lon": position[1], "description": description})
    for index, row in enumerate(rows(source, "ZDATA_map_I_have_been.xlsx", "read"), 1):
        position = coordinates(row)
        if not position:
            omitted["visits"] += 1
            continue
        when = date_text(row.get("when"), month_only=True)
        description = " · ".join(x for x in (when, clean(row.get("contents"))) if x)
        visits.append({"id": f"visit-{index:04d}", "name": clean(row.get("site")) or clean(row.get("city")),
                       "place": ", ".join(x for x in (clean(row.get("city")), clean(row.get("country"))) if x),
                       "lat": position[0], "lon": position[1], "description": description})
    site = {"profile": PROFILE, "research": RESEARCH, "people": people, "news": news, "links": links,
            "maps": {"collaborations": collaborations, "visits": visits},
            "provenance": {"source_repository": "https://github.com/byungkiryu/byungkiryu",
                           "source_commit": "23a1be7b36725e95268465599db9d23e3e10ca1c", "import_date": "2026-11-08"}}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(site, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"people": len(people), "people_categories": Counter(x["category"] for x in people),
                      "news": len(news), "links": len(links), "research_topics": len(RESEARCH["topics"]),
                      "collaborations": len(collaborations), "visits": len(visits), "omitted_invalid_coordinates": omitted},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True,
                        help="Directory containing the archived original Excel files")
    parser.add_argument("--output", type=Path, required=True,
                        help="Destination site.json; existing content at this path will be overwritten")
    args = parser.parse_args()
    migrate(args.source, args.output)
