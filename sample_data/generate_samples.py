"""Generate synthetic bank statement PDFs and expected CSVs for testing."""

import csv
import io
import shutil
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pymupdf
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def get_base_transactions() -> list[dict[str, Any]]:
    """Return 28 base synthetic transactions with realistic Indian descriptions."""
    initial_balance = 75000.00
    raw_data: list[tuple[str, str, str, float, float]] = [
        # (day_str, line1, line2, debit, credit)
        ("01", "NEFT-SALARY-ACME TECH CORP", "Ref 0029384 Payroll Apr 2025", 0.0, 65000.00),
        ("02", "UPI/412345678901/SWIGGY/okaxis", "Order ref 882341 Bangalore IN", 450.00, 0.0),
        ("03", "ATM WDL 1234", "ATM ID S1NA0012 Mumbai West", 5000.00, 0.0),
        ("04", "POS AMAZON RETAIL", "Txn 492049102 Mumbai IN", 2499.00, 0.0),
        ("05", "UPI/412345678902/ZOMATO/paytm", "Order ref 554312 Gurgaon IN", 320.00, 0.0),
        ("06", "ACH D- LIC PREMIUM", "Policy 089234812 Mumbai", 3500.00, 0.0),
        ("07", "IMPS/P2A/4102938475/DIVIDEND", "Ref 902341 Equity Share", 0.0, 1250.00),
        ("08", "UPI/412345678903/UBER/axis", "Trip ref 120938 New Delhi", 280.00, 0.0),
        ("09", "POS RELIANCE FRESH MUMBAI", "Store 0214 Andheri East", 1850.50, 0.0),
        ("10", "CHRG SMS", "Quarterly Service Fee Q4", 17.70, 0.0),
        ("11", "UPI/412345678904/APOLLO/icici", "Invoice 99402 Hyderabad IN", 650.00, 0.0),
        ("12", "NEFT-REFUND-MAKEMYTRIP", "PNR 8923482 Flight Cancel", 0.0, 4800.00),
        ("13", "POS DMART GROCERIES", "Store 089 Thane West IN", 4210.00, 0.0),
        ("14", "INT.PD", "Auto Interest Credit SB", 0.0, 425.00),
        # Page 2 transactions
        ("15", "UPI/412345678905/FLIPKART/okicici", "Order 4920194 Bangalore IN", 1999.00, 0.0),
        ("16", "ATM WDL 5678", "ATM ID N2SB0098 Pune South", 3000.00, 0.0),
        ("17", "ACH D- MUTUAL FUND SIP", "Folio 1029384 HDFC MF", 5000.00, 0.0),
        ("18", "UPI/412345678906/AIRTEL/paytm", "Mobile Bill 9820098200", 899.00, 0.0),
        ("19", "POS SHELL PETROL PUMP", "Station 442 Navi Mumbai", 2500.00, 0.0),
        ("20", "IMPS/P2A/4102938476/RENT", "Ref 882019 Flat 402", 0.0, 22000.00),
        ("21", "UPI/412345678907/BOOKMYSHOW/axis", "Booking 390192 Mumbai IN", 640.00, 0.0),
        ("22", "POS TATA CLIQ RETAIL", "Order 99201 Mumbai City", 3200.00, 0.0),
        ("23", "UPI/412345678908/BIGBASKET/okaxis", "Order 109283 Bangalore", 1450.00, 0.0),
        ("24", "ACH D- TATA AIG INSURANCE", "Policy 7720194 Mumbai", 4500.00, 0.0),
        ("25", "ATM WDL 9012", "ATM ID W1AX0055 Chennai", 2000.00, 0.0),
        ("26", "UPI/412345678909/DUNZO/paytm", "Order 882018 Delivery IN", 180.00, 0.0),
        ("27", "CHRG SMS", "Quarterly Service Fee Q4", 17.70, 0.0),
        ("28", "INT.PD", "Savings Bank Interest", 0.0, 312.00),
    ]

    current_balance = initial_balance
    txns: list[dict[str, Any]] = []

    for day_str, line1, line2, debit, credit in raw_data:
        current_balance = round(current_balance - debit + credit, 2)
        txn_date = date(2025, 4, int(day_str))
        txns.append({
            "iso_date": txn_date.strftime("%Y-%m-%d"),
            "dmy_date": txn_date.strftime("%d/%m/%Y"),
            "mon_date": txn_date.strftime("%d-%b-%y"),
            "line1": line1,
            "line2": line2,
            "full_desc": f"{line1} {line2}",
            "debit": debit,
            "credit": credit,
            "balance": current_balance,
        })

    return txns


def create_page_decorator(bank_name: str, total_pages: int = 2) -> Callable[[Any, Any], None]:
    """Create a canvas callback for repeated page header and footer."""
    def decorator(canvas: Any, doc: Any) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#4A5568"))
        canvas.drawString(36, 810, f"{bank_name} - ACCOUNT STATEMENT")
        canvas.drawRightString(595 - 36, 810, f"Page {doc.page} of {total_pages}")
        canvas.setStrokeColor(colors.HexColor("#CBD5E0"))
        canvas.setLineWidth(0.5)
        canvas.line(36, 804, 595 - 36, 804)

        canvas.line(36, 38, 595 - 36, 38)
        canvas.drawString(36, 28, "Computer Generated Statement - Does not require physical signature")
        canvas.drawRightString(595 - 36, 28, "Confidential - For Account Holder Only")
        canvas.restoreState()

    return decorator


def build_account_header(
    bank_name: str,
    account_holder: str,
    account_no: str,
    ifsc: str,
    period: str,
    styles: Any,
) -> list[Any]:
    """Build account details header block elements."""
    title_style = ParagraphStyle(
        "AccountTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1A202C"),
    )
    meta_label = ParagraphStyle(
        "MetaLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#4A5568"),
    )
    meta_val = ParagraphStyle(
        "MetaVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1A202C"),
    )

    header_data = [
        [
            Paragraph("Account Holder:", meta_label),
            Paragraph(account_holder, meta_val),
            Paragraph("Bank Name:", meta_label),
            Paragraph(bank_name, meta_val),
        ],
        [
            Paragraph("Account Number:", meta_label),
            Paragraph(account_no, meta_val),
            Paragraph("IFSC Code:", meta_label),
            Paragraph(ifsc, meta_val),
        ],
        [
            Paragraph("Statement Period:", meta_label),
            Paragraph(period, meta_val),
            Paragraph("Branch:", meta_label),
            Paragraph("Main Branch", meta_val),
        ],
    ]
    meta_table = Table(header_data, colWidths=[110, 150, 90, 173])
    meta_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ])
    )

    return [
        Paragraph(bank_name, title_style),
        Paragraph("STATEMENT OF ACCOUNT", meta_label),
        Spacer(1, 8),
        meta_table,
        Spacer(1, 14),
    ]


def save_expected_csv(
    transactions: list[dict[str, Any]],
    output_path: Path,
    use_multiline_desc: bool = False,
) -> None:
    """Save the expected transactions CSV."""
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "description", "debit", "credit", "balance"])
        for txn in transactions:
            desc = txn["full_desc"] if use_multiline_desc else txn["line1"]
            writer.writerow([
                txn["iso_date"],
                desc,
                f"{txn['debit']:.1f}" if txn["debit"] > 0 else "0.0",
                f"{txn['credit']:.1f}" if txn["credit"] > 0 else "0.0",
                f"{txn['balance']:.2f}",
            ])


def generate_bordered_sample(output_dir: Path, txns: list[dict[str, Any]]) -> None:
    """Generate text_bordered.pdf and text_bordered_expected.csv."""
    pdf_path = output_dir / "text_bordered.pdf"
    csv_path = output_dir / "text_bordered_expected.csv"
    save_expected_csv(txns, csv_path, use_multiline_desc=False)

    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle(
        "CellBordered",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
    )

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=45,
        bottomMargin=45,
    )

    story: list[Any] = []
    story.extend(
        build_account_header(
            bank_name="STATE BANK OF INDIA",
            account_holder="RAJESH SHARMA",
            account_no="10293847561",
            ifsc="SBIN0001234",
            period="01/04/2025 to 28/04/2025",
            styles=styles,
        )
    )

    headers = ["Date", "Description", "Debit", "Credit", "Balance"]
    col_widths = [70, 233, 70, 70, 80]
    table_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1A202C")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ])

    # Page 1: 14 rows
    t1_data = [headers]
    for txn in txns[:14]:
        dr_str = f"{txn['debit']:,.2f}" if txn["debit"] > 0 else ""
        cr_str = f"{txn['credit']:,.2f}" if txn["credit"] > 0 else ""
        t1_data.append([
            txn["dmy_date"],
            Paragraph(txn["line1"], cell_style),
            dr_str,
            cr_str,
            f"{txn['balance']:,.2f}",
        ])
    t1 = Table(t1_data, colWidths=col_widths)
    t1.setStyle(table_style)
    story.append(t1)

    story.append(PageBreak())

    # Page 2: 14 rows
    t2_data = [headers]
    for txn in txns[14:]:
        dr_str = f"{txn['debit']:,.2f}" if txn["debit"] > 0 else ""
        cr_str = f"{txn['credit']:,.2f}" if txn["credit"] > 0 else ""
        t2_data.append([
            txn["dmy_date"],
            Paragraph(txn["line1"], cell_style),
            dr_str,
            cr_str,
            f"{txn['balance']:,.2f}",
        ])
    t2 = Table(t2_data, colWidths=col_widths)
    t2.setStyle(table_style)
    story.append(t2)

    doc.build(
        story,
        onFirstPage=create_page_decorator("STATE BANK OF INDIA"),
        onLaterPages=create_page_decorator("STATE BANK OF INDIA"),
    )


def generate_borderless_sample(output_dir: Path, txns: list[dict[str, Any]]) -> None:
    """Generate text_borderless.pdf and text_borderless_expected.csv."""
    pdf_path = output_dir / "text_borderless.pdf"
    csv_path = output_dir / "text_borderless_expected.csv"
    save_expected_csv(txns, csv_path, use_multiline_desc=False)

    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle(
        "CellBorderless",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
    )

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=45,
        bottomMargin=45,
    )

    story: list[Any] = []
    story.extend(
        build_account_header(
            bank_name="HDFC BANK",
            account_holder="PRIYA PATEL",
            account_no="50100234567890",
            ifsc="HDFC0000456",
            period="2025-04-01 to 2025-04-28",
            styles=styles,
        )
    )

    headers = ["Date", "Description", "Debit", "Credit", "Balance"]
    col_widths = [75, 228, 70, 70, 80]
    table_style = TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#2D3748")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor("#4A5568")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ])

    # Page 1: 14 rows
    t1_data = [headers]
    for txn in txns[:14]:
        dr_str = f"{txn['debit']:,.2f}" if txn["debit"] > 0 else ""
        cr_str = f"{txn['credit']:,.2f}" if txn["credit"] > 0 else ""
        t1_data.append([
            txn["iso_date"],
            Paragraph(txn["line1"], cell_style),
            dr_str,
            cr_str,
            f"{txn['balance']:,.2f}",
        ])
    t1 = Table(t1_data, colWidths=col_widths)
    t1.setStyle(table_style)
    story.append(t1)

    story.append(PageBreak())

    # Page 2: 14 rows
    t2_data = [headers]
    for txn in txns[14:]:
        dr_str = f"{txn['debit']:,.2f}" if txn["debit"] > 0 else ""
        cr_str = f"{txn['credit']:,.2f}" if txn["credit"] > 0 else ""
        t2_data.append([
            txn["iso_date"],
            Paragraph(txn["line1"], cell_style),
            dr_str,
            cr_str,
            f"{txn['balance']:,.2f}",
        ])
    t2 = Table(t2_data, colWidths=col_widths)
    t2.setStyle(table_style)
    story.append(t2)

    doc.build(
        story,
        onFirstPage=create_page_decorator("HDFC BANK"),
        onLaterPages=create_page_decorator("HDFC BANK"),
    )


def generate_drcr_sample(output_dir: Path, txns: list[dict[str, Any]]) -> None:
    """Generate text_drcr.pdf and text_drcr_expected.csv."""
    pdf_path = output_dir / "text_drcr.pdf"
    csv_path = output_dir / "text_drcr_expected.csv"
    save_expected_csv(txns, csv_path, use_multiline_desc=False)

    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle(
        "CellDrCr",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
    )

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=45,
        bottomMargin=45,
    )

    story: list[Any] = []
    story.extend(
        build_account_header(
            bank_name="ICICI BANK",
            account_holder="AMIT VERMA",
            account_no="001105001234",
            ifsc="ICIC0000789",
            period="01/04/2025 to 28/04/2025",
            styles=styles,
        )
    )

    headers = ["Date", "Description", "Amount", "Balance"]
    col_widths = [75, 273, 90, 85]
    table_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1A202C")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ])

    # Page 1: 14 rows
    t1_data = [headers]
    for txn in txns[:14]:
        amt_str = f"{txn['debit']:,.2f} Dr" if txn["debit"] > 0 else f"{txn['credit']:,.2f} Cr"
        t1_data.append([
            txn["dmy_date"],
            Paragraph(txn["line1"], cell_style),
            amt_str,
            f"{txn['balance']:,.2f}",
        ])
    t1 = Table(t1_data, colWidths=col_widths)
    t1.setStyle(table_style)
    story.append(t1)

    story.append(PageBreak())

    # Page 2: 14 rows
    t2_data = [headers]
    for txn in txns[14:]:
        amt_str = f"{txn['debit']:,.2f} Dr" if txn["debit"] > 0 else f"{txn['credit']:,.2f} Cr"
        t2_data.append([
            txn["dmy_date"],
            Paragraph(txn["line1"], cell_style),
            amt_str,
            f"{txn['balance']:,.2f}",
        ])
    t2 = Table(t2_data, colWidths=col_widths)
    t2.setStyle(table_style)
    story.append(t2)

    doc.build(
        story,
        onFirstPage=create_page_decorator("ICICI BANK"),
        onLaterPages=create_page_decorator("ICICI BANK"),
    )


def generate_multiline_sample(output_dir: Path, txns: list[dict[str, Any]]) -> None:
    """Generate text_multiline.pdf and text_multiline_expected.csv."""
    pdf_path = output_dir / "text_multiline.pdf"
    csv_path = output_dir / "text_multiline_expected.csv"
    save_expected_csv(txns, csv_path, use_multiline_desc=True)

    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle(
        "CellMultiline",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
    )

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=45,
        bottomMargin=45,
    )

    story: list[Any] = []
    story.extend(
        build_account_header(
            bank_name="AXIS BANK",
            account_holder="SNEHA REDDY",
            account_no="912010045678123",
            ifsc="UTIB0000321",
            period="01-Apr-2025 to 28-Apr-2025",
            styles=styles,
        )
    )

    headers = ["Date", "Description", "Debit", "Credit", "Balance"]
    col_widths = [70, 233, 70, 70, 80]
    table_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1A202C")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ])

    # Page 1: 14 rows
    t1_data = [headers]
    for txn in txns[:14]:
        dr_str = f"{txn['debit']:,.2f}" if txn["debit"] > 0 else ""
        cr_str = f"{txn['credit']:,.2f}" if txn["credit"] > 0 else ""
        desc_p = Paragraph(f"{txn['line1']}<br/>{txn['line2']}", cell_style)
        t1_data.append([
            txn["mon_date"],
            desc_p,
            dr_str,
            cr_str,
            f"{txn['balance']:,.2f}",
        ])
    t1 = Table(t1_data, colWidths=col_widths)
    t1.setStyle(table_style)
    story.append(t1)

    story.append(PageBreak())

    # Page 2: 14 rows
    t2_data = [headers]
    for txn in txns[14:]:
        dr_str = f"{txn['debit']:,.2f}" if txn["debit"] > 0 else ""
        cr_str = f"{txn['credit']:,.2f}" if txn["credit"] > 0 else ""
        desc_p = Paragraph(f"{txn['line1']}<br/>{txn['line2']}", cell_style)
        t2_data.append([
            txn["mon_date"],
            desc_p,
            dr_str,
            cr_str,
            f"{txn['balance']:,.2f}",
        ])
    t2 = Table(t2_data, colWidths=col_widths)
    t2.setStyle(table_style)
    story.append(t2)

    doc.build(
        story,
        onFirstPage=create_page_decorator("AXIS BANK"),
        onLaterPages=create_page_decorator("AXIS BANK"),
    )


def generate_scanned_sample(
    src_pdf_path: Path,
    out_pdf_path: Path,
    angle: float = 1.2,
    noise_sigma: float = 3.0,
) -> None:
    """Render a text PDF to 300 DPI images, apply rotation and noise, and save as image-only PDF."""
    src_doc = pymupdf.open(str(src_pdf_path))
    out_doc = pymupdf.open()

    for page_idx, page in enumerate(src_doc):
        pix = page.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        rot_img = img.rotate(
            angle,
            resample=Image.Resampling.BICUBIC,
            expand=False,
            fillcolor=(255, 255, 255),
        )
        arr = np.array(rot_img)

        rng = np.random.default_rng(42 + page_idx)
        noise = rng.normal(0, noise_sigma, arr.shape).astype(np.int16)
        noisy_arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        noisy_img = Image.fromarray(noisy_arr)

        buf = io.BytesIO()
        noisy_img.save(buf, format="JPEG", quality=95)

        new_page = out_doc.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(page.rect, stream=buf.getvalue())

    out_doc.save(str(out_pdf_path))
    out_doc.close()
    src_doc.close()


def main() -> None:
    """Generate all synthetic PDFs and their matching CSV files."""
    output_dir = Path(__file__).resolve().parent
    output_dir.mkdir(parents=True, exist_ok=True)
    txns = get_base_transactions()

    print("Generating sample data in:", output_dir)
    generate_bordered_sample(output_dir, txns)
    print("  Created text_bordered.pdf and text_bordered_expected.csv")

    generate_borderless_sample(output_dir, txns)
    print("  Created text_borderless.pdf and text_borderless_expected.csv")

    generate_drcr_sample(output_dir, txns)
    print("  Created text_drcr.pdf and text_drcr_expected.csv")

    generate_multiline_sample(output_dir, txns)
    print("  Created text_multiline.pdf and text_multiline_expected.csv")

    generate_scanned_sample(
        output_dir / "text_bordered.pdf",
        output_dir / "scanned_bordered.pdf",
    )
    shutil.copyfile(
        output_dir / "text_bordered_expected.csv",
        output_dir / "scanned_bordered_expected.csv",
    )
    print("  Created scanned_bordered.pdf and scanned_bordered_expected.csv")

    generate_scanned_sample(
        output_dir / "text_drcr.pdf",
        output_dir / "scanned_drcr.pdf",
    )
    shutil.copyfile(
        output_dir / "text_drcr_expected.csv",
        output_dir / "scanned_drcr_expected.csv",
    )
    print("  Created scanned_drcr.pdf and scanned_drcr_expected.csv")

    print("All sample files generated successfully.")


if __name__ == "__main__":
    main()
