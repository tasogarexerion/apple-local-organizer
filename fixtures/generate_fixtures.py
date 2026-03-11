#!/usr/bin/env python3
from __future__ import annotations

import base64
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"

PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WlH0T4AAAAASUVORK5CYII="
)
JPEG_BASE64 = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBxAQEBAQEBAVEBAVEBUQEBUVEBUQFxUVFhUXFhUV"
    "FRUYHSggGBolHRUVITEhJSkrLi4uFx8zODMsNygtLisBCgoKDg0OGhAQGy0lICYtLS0tLS0tLS0t"
    "LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLf/AABEIAAEAAgMBEQACEQEDEQH/"
    "xAAXAAEBAQEAAAAAAAAAAAAAAAAAAQID/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAwDAQACEAMQ"
    "AAAB6gD/xAAZEAEAAwEBAAAAAAAAAAAAAAABAAIDETH/2gAIAQEAAT8Aotj4J//EABQRAQAAAAAAAA"
    "AAAAAAAAAAAD/2gAIAQIBAT8Aaf/EABQRAQAAAAAAAAAAAAAAAAAAAD/2gAIAQMBAT8Aaf/Z"
)


def decode_base64(raw: str) -> bytes:
    return base64.b64decode(raw + "=" * (-len(raw) % 4))


def make_screenshot_png() -> bytes:
    swift_source = """
import AppKit

func pngData() -> Data? {
    let size = NSSize(width: 1280, height: 820)
    let image = NSImage(size: size)
    image.lockFocus()

    NSColor(calibratedWhite: 0.97, alpha: 1.0).setFill()
    NSBezierPath(rect: NSRect(origin: .zero, size: size)).fill()

    NSColor(calibratedWhite: 0.87, alpha: 1.0).setFill()
    NSBezierPath(rect: NSRect(x: 0, y: 760, width: 1280, height: 60)).fill()

    let titleAttrs: [NSAttributedString.Key: Any] = [
        .font: NSFont.systemFont(ofSize: 30, weight: .semibold),
        .foregroundColor: NSColor.black,
    ]
    let bodyAttrs: [NSAttributedString.Key: Any] = [
        .font: NSFont.monospacedSystemFont(ofSize: 26, weight: .regular),
        .foregroundColor: NSColor(calibratedWhite: 0.12, alpha: 1.0),
    ]
    let accentAttrs: [NSAttributedString.Key: Any] = [
        .font: NSFont.monospacedSystemFont(ofSize: 24, weight: .medium),
        .foregroundColor: NSColor.systemBlue,
    ]

    NSString(string: "Downloads Review").draw(at: NSPoint(x: 36, y: 774), withAttributes: titleAttrs)
    NSString(string: "Project Notes").draw(at: NSPoint(x: 56, y: 690), withAttributes: titleAttrs)
    NSString(string: "- Update roadmap").draw(at: NSPoint(x: 72, y: 630), withAttributes: bodyAttrs)
    NSString(string: "- Confirm WWDC messaging").draw(at: NSPoint(x: 72, y: 584), withAttributes: bodyAttrs)
    NSString(string: "- Draft menu bar UX").draw(at: NSPoint(x: 72, y: 538), withAttributes: bodyAttrs)
    NSString(string: "Review status: ready").draw(at: NSPoint(x: 72, y: 460), withAttributes: accentAttrs)
    NSString(string: "2026-03-11 12:00").draw(at: NSPoint(x: 980, y: 774), withAttributes: bodyAttrs)

    image.unlockFocus()
    guard let tiff = image.tiffRepresentation,
          let rep = NSBitmapImageRep(data: tiff) else {
        return nil
    }
    return rep.representation(using: .png, properties: [:])
}

@main
struct Runner {
    static func main() throws {
        guard let data = pngData() else {
            throw NSError(domain: "Fixture", code: 1)
        }
        let output = URL(fileURLWithPath: CommandLine.arguments[1])
        try data.write(to: output)
    }
}
"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        source = temp_root / "make_screenshot.swift"
        binary = temp_root / "make_screenshot"
        output = temp_root / "screenshot.png"
        module_cache = temp_root / "module-cache"
        module_cache.mkdir()
        source.write_text(swift_source, encoding="utf-8")
        subprocess.run(
            [
                "swiftc",
                "-parse-as-library",
                "-module-cache-path",
                str(module_cache),
                "-o",
                str(binary),
                str(source),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [str(binary), str(output)],
            check=True,
            capture_output=True,
            text=True,
        )
        if output.exists():
            return output.read_bytes()
    return decode_base64(PNG_BASE64)


def make_pdf_with_text(text: str) -> bytes:
    stream = f"BT /F1 18 Tf 72 720 Td ({text}) Tj ET"
    pdf = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Count 1 /Kids [3 0 R] >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
5 0 obj
<< /Length {len(stream)} >>
stream
{stream}
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000060 00000 n 
0000000117 00000 n 
0000000243 00000 n 
0000000313 00000 n 
trailer
<< /Root 1 0 R /Size 6 >>
startxref
390
%%EOF
"""
    return pdf.encode("utf-8")


def make_pdf_without_text() -> bytes:
    stream = "0.9 g 100 100 200 400 re f"
    pdf = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Count 1 /Kids [3 0 R] >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length {len(stream)} >>
stream
{stream}
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000060 00000 n 
0000000117 00000 n 
0000000206 00000 n 
trailer
<< /Root 1 0 R /Size 5 >>
startxref
276
%%EOF
"""
    return pdf.encode("utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "clipboard_input.txt").write_text(
        "来週の発表準備について、資料更新とレビュー調整が必要です。",
        encoding="utf-8",
    )
    (OUT / "sample_notes.md").write_text(
        "# Project Notes\n\n- Update the roadmap\n- Confirm WWDC messaging\n- Draft menu bar UX\n",
        encoding="utf-8",
    )
    (OUT / "embedded_text.pdf").write_bytes(make_pdf_with_text("Apple Intelligence invoice"))
    (OUT / "ocr_only.pdf").write_bytes(make_pdf_without_text())
    (OUT / "screenshot.png").write_bytes(make_screenshot_png())
    (OUT / "photo.jpg").write_bytes(decode_base64(JPEG_BASE64))
    (OUT / "archive.zip").write_text("PK placeholder", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
