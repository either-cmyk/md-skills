#!/usr/bin/env python3
"""쿠팡 팔레트 적재리스트 PDF 생성 (2026.04.21 신양식: 팔레트별 페이지)

JSON 데이터 구조 (신):
{
  "company_name": "...",
  "company_code": "...",
  "order_id": "...",
  "center": "...",
  "delivery_date": "YYYY-MM-DD",
  "pallet_count": N,
  "pallets": [
    {
      "seq": 1,                  # 팔레트 순번 (1..N)
      "box_count": 16,           # 해당 팔레트 박스수
      "rows": [
        {"no": 1, "sku": "...", "name": "...", "box_no": "16-1", "qty": 30},
        ...
      ]
    }, ...
  ]
}

규칙:
- 팔레트 번호: {pallet_count}-{seq}
- 총 박스(페이지 필드): 해당 팔레트의 박스수 (box_count)
- 박스 번호: 혼적박스만 "{box_count}-{박스순번}", 단독은 공란
- 같은 SKU가 여러 혼적박스에 걸치면 박스마다 별도 행
- 단독박스 상품들은 SKU별 합산 1행 (box_no 공란)
"""

import argparse
import json
import os
import sys

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, PageBreak
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.enums import TA_CENTER
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab", "--break-system-packages", "-q"])
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, PageBreak
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.enums import TA_CENTER


def pick_layout(row_count: int) -> dict:
    """행 개수에 따른 레이아웃 프리셋."""
    if row_count <= 12:
        return dict(
            slots=max(12, row_count),
            title_fs=13, title_lead=16, title_sa=2,
            warn_fs=9, warn_sa=8,
            section_fs=10, section_lead=14, section_sb=6, section_sa=2,
            info_fs=10, info_pad_top=4, info_pad_bot=4,
            item_header_fs=8, item_row_fs=8, item_name_fs=8, item_name_lead=10,
            box_no_fs=7.5, box_no_lead=9,
            header_row_h=9.0, row_h=10.0,
            doc_left=15.0, doc_right=15.0, doc_top=12.0, doc_bot=12.0,
        )
    if row_count <= 25:
        return dict(
            slots=row_count,
            title_fs=11, title_lead=13, title_sa=1,
            warn_fs=8, warn_sa=4,
            section_fs=9, section_lead=11, section_sb=3, section_sa=1,
            info_fs=9, info_pad_top=2, info_pad_bot=2,
            item_header_fs=7.5, item_row_fs=7.5, item_name_fs=7.5, item_name_lead=9,
            box_no_fs=7, box_no_lead=8,
            header_row_h=7.5, row_h=7.0,
            doc_left=12.0, doc_right=12.0, doc_top=8.0, doc_bot=8.0,
        )
    return dict(
        slots=row_count,
        title_fs=10, title_lead=12, title_sa=0,
        warn_fs=7, warn_sa=2,
        section_fs=8.5, section_lead=10, section_sb=2, section_sa=0,
        info_fs=8, info_pad_top=1, info_pad_bot=1,
        item_header_fs=7, item_row_fs=7, item_name_fs=6.5, item_name_lead=8,
        box_no_fs=6.5, box_no_lead=7.5,
        header_row_h=6.0, row_h=4.5,
        doc_left=10.0, doc_right=10.0, doc_top=6.0, doc_bot=6.0,
    )


def register_korean_fonts(assets_dir):
    reg = os.path.join(assets_dir, "NotoSansKR-Regular.ttf")
    bold = os.path.join(assets_dir, "NotoSansKR-Bold.ttf")
    if not os.path.exists(reg) or not os.path.exists(bold):
        raise FileNotFoundError(f"폰트 파일이 없습니다: {reg}, {bold}")
    pdfmetrics.registerFont(TTFont("NotoKR", reg))
    pdfmetrics.registerFont(TTFont("NotoKR-Bold", bold))


def make_page(pallet_data, data, layout):
    """한 팔레트 페이지의 요소 리스트"""
    elements = []
    pallet_count = data["pallet_count"]
    pallet_seq = pallet_data["seq"]
    pallet_no = f"{pallet_count}-{pallet_seq}"
    box_count = pallet_data["box_count"]
    rows_data = pallet_data["rows"]

    title_style = ParagraphStyle(
        "title", fontName="NotoKR-Bold",
        fontSize=layout["title_fs"], leading=layout["title_lead"],
        alignment=TA_CENTER, spaceAfter=layout["title_sa"])
    warn_style = ParagraphStyle(
        "warn", fontName="NotoKR",
        fontSize=layout["warn_fs"], alignment=TA_CENTER, spaceAfter=layout["warn_sa"])
    section_style = ParagraphStyle(
        "section", fontName="NotoKR-Bold",
        fontSize=layout["section_fs"], leading=layout["section_lead"],
        spaceBefore=layout["section_sb"], spaceAfter=layout["section_sa"])

    elements.append(Paragraph("쿠팡 팔레트 적재리스트 (각 팔레트 부착 필수)", title_style))
    elements.append(Paragraph("※ 팔레트의 높이는 1,700mm를 초과할 수 없습니다 ※", warn_style))

    info_style = TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "NotoKR"),
        ("FONTSIZE", (0, 0), (-1, -1), layout["info_fs"]),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F0F0F0")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), layout["info_pad_top"]),
        ("BOTTOMPADDING", (0, 0), (-1, -1), layout["info_pad_bot"]),
    ])

    elements.append(Paragraph("1) 업체 정보", section_style))
    t1 = Table([
        ["업체명", data["company_name"]],
        ["업체코드", data.get("company_code", "")],
    ], colWidths=[40*mm, 140*mm])
    t1.setStyle(info_style)
    elements.append(t1)

    elements.append(Paragraph("2) 입고 예약 정보", section_style))
    t2 = Table([
        ["요청 ID", str(data["order_id"])],
        ["물류센터", data["center"]],
        ["물류센터 도착예정일", data["delivery_date"]],
        ["팔레트 번호", pallet_no],
        ["총 박스", str(box_count)],
    ], colWidths=[40*mm, 140*mm])
    t2.setStyle(info_style)
    elements.append(t2)

    elements.append(Paragraph("3) 상품 정보", section_style))
    header = ["No.", "SKU ID", "물류입고용 상품명 / 옵션명", "박스 번호", "상품 수량", "소비기한/\n제조일자"]
    rows = [header]
    name_style = ParagraphStyle("name", fontName="NotoKR",
        fontSize=layout["item_name_fs"], leading=layout["item_name_lead"])
    box_style = ParagraphStyle("box", fontName="NotoKR",
        fontSize=layout["box_no_fs"], leading=layout["box_no_lead"], alignment=TA_CENTER)

    slots = max(layout["slots"], len(rows_data))
    for i in range(slots):
        if i < len(rows_data):
            r = rows_data[i]
            bx = str(r.get("box_no", "") or "")
            rows.append([
                str(r["no"]),
                str(r["sku"]),
                Paragraph(r["name"], name_style),
                Paragraph(bx, box_style) if bx else "",
                str(r["qty"]),
                "",
            ])
        else:
            rows.append([str(i + 1), "", "", "", "", ""])

    t3 = Table(rows,
        colWidths=[10*mm, 22*mm, 80*mm, 20*mm, 20*mm, 28*mm],
        rowHeights=[layout["header_row_h"]*mm] + [layout["row_h"]*mm] * slots)
    t3.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "NotoKR"),
        ("FONTSIZE", (0, 0), (-1, -1), layout["item_row_fs"]),
        ("FONTNAME", (0, 0), (-1, 0), "NotoKR-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), layout["item_header_fs"]),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E8E8")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("ALIGN", (3, 0), (5, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(t3)
    return elements


def generate(assets_dir, data_path, output_path):
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    register_korean_fonts(assets_dir)

    # 페이지별 레이아웃 (최대 행수 기준으로 한 번만 계산)
    max_rows = max((len(p["rows"]) for p in data["pallets"]), default=0)
    layout = pick_layout(max_rows)

    doc = SimpleDocTemplate(output_path, pagesize=A4,
        leftMargin=layout["doc_left"]*mm, rightMargin=layout["doc_right"]*mm,
        topMargin=layout["doc_top"]*mm, bottomMargin=layout["doc_bot"]*mm)

    elements = []
    pallets = sorted(data["pallets"], key=lambda p: p["seq"])
    for i, p in enumerate(pallets):
        elements.extend(make_page(p, data, layout))
        if i < len(pallets) - 1:
            elements.append(PageBreak())
    doc.build(elements)

    total_rows = sum(len(p["rows"]) for p in pallets)
    mix_rows = sum(1 for p in pallets for r in p["rows"] if r.get("box_no"))
    print(json.dumps({
        "status": "success",
        "output": output_path,
        "pages": len(pallets),
        "max_rows": max_rows,
        "total_rows": total_rows,
        "mixed_box_rows": mix_rows,
        "order_id": str(data["order_id"]),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    generate(args.assets, args.data, args.output)
