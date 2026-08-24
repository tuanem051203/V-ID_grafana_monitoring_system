#!/usr/bin/env python3
"""Generate the 15-slide V-ID observability presentation with LibreOffice UNO."""

from __future__ import annotations

import argparse
import uno
from com.sun.star.awt import Point, Size
from com.sun.star.beans import PropertyValue


NAVY = 0x10233F
BLUE = 0x1976D2
CYAN = 0x00A6A6
GREEN = 0x2E7D32
ORANGE = 0xEF6C00
RED = 0xC62828
INK = 0x172033
MUTED = 0x5D687A
LIGHT = 0xF4F7FB
PALE_BLUE = 0xEAF3FF
PALE_GREEN = 0xEAF7EF
PALE_ORANGE = 0xFFF3E7
WHITE = 0xFFFFFF
LINE = 0xD7DEEA

PAGE_W = 33867
PAGE_H = 19050


def prop(name: str, value: object) -> PropertyValue:
    item = PropertyValue()
    item.Name = name
    item.Value = value
    return item


def rgb(value: int) -> int:
    return int(value)


class Deck:
    def __init__(self, doc: object) -> None:
        self.doc = doc
        self.pages = doc.getDrawPages()
        self.slide_no = 0

    def slide(self, title: str, kicker: str = "V-ID OBSERVABILITY") -> object:
        page = self.pages.getByIndex(0) if self.slide_no == 0 else self.pages.insertNewByIndex(self.slide_no)
        page.Width = PAGE_W
        page.Height = PAGE_H
        self.slide_no += 1
        self.rect(page, 0, 0, PAGE_W, PAGE_H, WHITE, WHITE, radius=False)
        self.rect(page, 0, 0, 520, PAGE_H, BLUE, BLUE, radius=False)
        self.text(page, 1250, 700, 29000, 500, kicker, 11, BLUE, bold=True)
        self.text(page, 1250, 1250, 30500, 1500, title, 26, NAVY, bold=True)
        self.line(page, 1250, 2850, 31200, 2850, LINE, 30)
        self.text(page, 30500, 18100, 1500, 400, f"{self.slide_no:02d}", 10, MUTED, align=1)
        return page

    def title_slide(self) -> object:
        page = self.pages.getByIndex(0)
        page.Width = PAGE_W
        page.Height = PAGE_H
        self.slide_no = 1
        self.rect(page, 0, 0, PAGE_W, PAGE_H, NAVY, NAVY, radius=False)
        self.rect(page, 0, 0, 800, PAGE_H, CYAN, CYAN, radius=False)
        self.text(page, 2100, 2350, 28000, 700, "V-ID OBSERVABILITY PLATFORM", 14, CYAN, bold=True)
        self.text(page, 2100, 3550, 28500, 3200, "Từ “hệ thống đang lỗi”\nđến “lỗi ở đúng service nào”", 30, WHITE, bold=True)
        self.text(page, 2100, 7500, 27000, 1200, "Authentication · OTP · Token · Authorization · Reliability", 17, 0xD5E5F8)
        self.pill(page, 2100, 9800, 5500, 850, "Prometheus + Grafana", BLUE)
        self.pill(page, 8000, 9800, 5700, 850, "OpenTelemetry + Tempo", CYAN)
        self.pill(page, 14050, 9800, 5200, 850, "Alerts + Runbooks", ORANGE)
        self.text(page, 2100, 15100, 28000, 900, "Synthetic lab → UAT observability contract", 15, 0xAFC4DE)
        return page

    def shape(self, page: object, service: str, x: int, y: int, w: int, h: int) -> object:
        obj = self.doc.createInstance(service)
        obj.Position = Point(x, y)
        obj.Size = Size(w, h)
        page.add(obj)
        return obj

    def rect(self, page: object, x: int, y: int, w: int, h: int, fill: int, border: int = LINE, radius: bool = True) -> object:
        obj = self.shape(page, "com.sun.star.drawing.RectangleShape", x, y, w, h)
        obj.FillColor = rgb(fill)
        obj.LineColor = rgb(border)
        obj.LineWidth = 25
        if radius:
            try:
                obj.CornerRadius = 220
            except Exception:
                pass
        return obj

    def text(self, page: object, x: int, y: int, w: int, h: int, value: str, size: float = 16, color: int = INK, bold: bool = False, align: int = 0) -> object:
        obj = self.shape(page, "com.sun.star.drawing.TextShape", x, y, w, h)
        obj.String = value
        obj.CharFontName = "DejaVu Sans"
        obj.CharHeight = size
        obj.CharColor = rgb(color)
        obj.CharWeight = 150.0 if bold else 100.0
        obj.ParaAdjust = align
        obj.TextVerticalAdjust = 1
        obj.LineStyle = 0
        obj.FillStyle = 0
        return obj

    def box(self, page: object, x: int, y: int, w: int, h: int, title: str, body: str = "", fill: int = LIGHT, accent: int = BLUE) -> None:
        self.rect(page, x, y, w, h, fill, LINE)
        self.rect(page, x, y, 140, h, accent, accent, radius=False)
        self.text(page, x + 450, y + 300, w - 750, 650, title, 16, NAVY, bold=True)
        if body:
            self.text(page, x + 450, y + 1050, w - 750, h - 1250, body, 12, MUTED)

    def pill(self, page: object, x: int, y: int, w: int, h: int, value: str, fill: int) -> None:
        self.rect(page, x, y, w, h, fill, fill)
        self.text(page, x + 180, y + 80, w - 360, h - 160, value, 12, WHITE, bold=True, align=1)

    def line(self, page: object, x1: int, y1: int, x2: int, y2: int, color: int = LINE, width: int = 35) -> None:
        obj = self.shape(page, "com.sun.star.drawing.LineShape", x1, y1, max(1, x2 - x1), max(1, y2 - y1))
        obj.LineColor = rgb(color)
        obj.LineWidth = width

    def arrow(self, page: object, x1: int, y1: int, x2: int, y2: int, color: int = BLUE) -> None:
        obj = self.shape(page, "com.sun.star.drawing.LineShape", x1, y1, max(1, x2 - x1), max(1, y2 - y1))
        obj.LineColor = rgb(color)
        obj.LineWidth = 55
        try:
            obj.LineEndName = "Arrow"
            obj.LineEndWidth = 260
        except Exception:
            pass

    def metric(self, page: object, x: int, y: int, w: int, value: str, label: str, color: int) -> None:
        self.rect(page, x, y, w, 2500, WHITE, LINE)
        self.text(page, x + 200, y + 300, w - 400, 1000, value, 28, color, bold=True, align=1)
        self.text(page, x + 300, y + 1450, w - 600, 600, label, 12, MUTED, align=1)

    def flow(self, page: object, labels: list[str], y: int, x: int = 1500, total_w: int = 30000, fill: int = PALE_BLUE) -> None:
        gap = 450
        bw = int((total_w - gap * (len(labels) - 1)) / len(labels))
        for i, label in enumerate(labels):
            bx = x + i * (bw + gap)
            self.rect(page, bx, y, bw, 1350, fill, LINE)
            self.text(page, bx + 100, y + 180, bw - 200, 950, label, 11, NAVY, bold=True, align=1)
            if i < len(labels) - 1:
                self.arrow(page, bx + bw, y + 675, bx + bw + gap - 60, y + 675, BLUE)


def build_deck(doc: object) -> None:
    d = Deck(doc)
    d.title_slide()

    p = d.slide("6 tính năng quan trọng của dự án")
    features = [
        ("1", "Synthetic monitoring", "Traffic và incident có thể lặp lại", BLUE, PALE_BLUE),
        ("2", "KPI / SLI / SLO", "Contract, error budget và burn rate", GREEN, PALE_GREEN),
        ("3", "Metrics & alerting", "Prometheus rules + Alertmanager", ORANGE, PALE_ORANGE),
        ("4", "Dashboard drill-down", "9 dashboard, 83 panel", CYAN, PALE_BLUE),
        ("5", "OTP bottleneck locator", "Định vị theo 7 stage", RED, PALE_ORANGE),
        ("6", "Distributed tracing", "Exemplar → Tempo waterfall", NAVY, LIGHT),
    ]
    for i, (num, title, body, accent, fill) in enumerate(features):
        col, row = i % 3, i // 3
        x, y = 1500 + col * 10400, 3600 + row * 5000
        d.rect(p, x, y, 9200, 3900, fill, LINE)
        d.text(p, x + 400, y + 300, 1100, 650, num, 18, accent, bold=True)
        d.text(p, x + 400, y + 1200, 8300, 700, title, 16, NAVY, bold=True)
        d.text(p, x + 400, y + 2150, 8300, 900, body, 12, MUTED)
    d.text(p, 2500, 14100, 28800, 800, "Một workflow thống nhất: Detect → Localize → Prove → Alert → Recover", 16, NAVY, bold=True, align=1)

    p = d.slide("Phạm vi kiến trúc V-ID")
    d.flow(p, ["Client", "Kong", "identity-provider", "Redis / DB", "Notification / GSM"], 4200)
    d.box(p, 1800, 7200, 9000, 4000, "OAuth2/OIDC", "Hydra là issuer của web flow; target architecture là Hydra-as-issuer.", PALE_BLUE, BLUE)
    d.box(p, 12400, 7200, 9000, 4000, "Authorization", "authz thực hiện RBAC; organization là source of truth cho organization.", PALE_GREEN, GREEN)
    d.box(p, 23000, 7200, 8500, 4000, "OTP delivery", "Notification Center/GSM là external boundary; provider accepted ≠ delivered.", PALE_ORANGE, ORANGE)

    p = d.slide("Kiến trúc observability đã xây dựng")
    d.box(p, 1400, 5000, 6100, 2900, "Metrics Simulator", "Synthetic traffic + incidents", PALE_BLUE, BLUE)
    d.arrow(p, 7500, 6450, 9800, 6450)
    d.box(p, 9800, 3800, 6500, 2400, "Prometheus", "Metrics + rules", PALE_GREEN, GREEN)
    d.box(p, 9800, 7600, 6500, 2400, "OTel Collector", "Sampled OTLP traces", PALE_BLUE, CYAN)
    d.arrow(p, 16300, 5000, 19000, 5000)
    d.arrow(p, 16300, 8800, 19000, 8800)
    d.box(p, 19000, 3800, 5600, 2400, "Alertmanager", "Route + inhibit", PALE_ORANGE, ORANGE)
    d.box(p, 19000, 7600, 5600, 2400, "Tempo", "Trace waterfall", PALE_BLUE, CYAN)
    d.arrow(p, 24600, 5000, 27000, 6500)
    d.arrow(p, 24600, 8800, 27000, 6500)
    d.box(p, 27000, 5000, 4500, 3000, "Grafana", "Dashboard\nMetrics → Trace", PALE_GREEN, GREEN)

    p = d.slide("Tính năng 1 — Synthetic monitoring")
    d.box(p, 1400, 3600, 9500, 4000, "User journeys", "Authentication\nOTP send/delivery/verify\nToken issuance\nAuthorization", PALE_BLUE, BLUE)
    d.box(p, 12150, 3600, 9500, 4000, "Operational signals", "HTTP and service health\nDatabase and infrastructure\nProvider status and queue", PALE_GREEN, GREEN)
    d.box(p, 22900, 3600, 8500, 4000, "Simulation model", "Time-based traffic\nLog-normal latency\nRepeatable incidents", PALE_ORANGE, ORANGE)
    d.text(p, 2100, 9100, 29000, 2100, "Giá trị: kiểm thử normal, degradation, no-data và recovery trước khi có telemetry UAT", 20, NAVY, bold=True, align=1)

    p = d.slide("Tính năng 2 — KPI, SLI và SLO")
    rows = [("Authentication", "Success + latency < 500 ms"), ("OTP", "Submission + delivery + verification"), ("Token", "Issuance theo issuer/grant"), ("Platform", "Critical operation availability"), ("Reliability", "Error budget + burn rate")]
    for i, (a, b) in enumerate(rows):
        y = 3500 + i * 2100
        d.rect(p, 2200, y, 7800, 1500, NAVY if i == 0 else LIGHT, LINE)
        d.text(p, 2500, y + 220, 7200, 950, a, 15, WHITE if i == 0 else NAVY, bold=True)
        d.rect(p, 10300, y, 20100, 1500, WHITE, LINE)
        d.text(p, 10800, y + 220, 19000, 950, b, 14, INK)
    d.text(p, 2200, 14500, 28200, 950, "Business rejection ≠ system failure · No-data ≠ healthy · SLO lab cần owner phê duyệt", 14, RED, bold=True, align=1)

    p = d.slide("Tính năng 3 — Metrics và alerting")
    d.metric(p, 1800, 3900, 8500, "62", "recording rules", BLUE)
    d.metric(p, 12600, 3900, 8500, "17", "alert rules", ORANGE)
    d.metric(p, 23400, 3900, 8500, "5", "SLO windows", GREEN)
    d.flow(p, ["Raw metrics", "Rate / Ratio / p95", "Recorded KPI", "Alerts", "Runbook"], 8500, 1800, 30000)
    d.text(p, 2300, 12200, 29000, 1400, "Ưu tiên user-impact symptoms; resource metrics là context điều tra", 18, NAVY, bold=True, align=1)

    p = d.slide("Tính năng 4 — Dashboard drill-down")
    d.metric(p, 2000, 3800, 9000, "9", "dashboards", BLUE)
    d.metric(p, 12400, 3800, 9000, "83", "panels", CYAN)
    d.metric(p, 22800, 3800, 9000, "1-click", "metrics → trace", GREEN)
    d.box(p, 1800, 7900, 14200, 4700, "Dashboard coverage", "Overview · Authentication · MFA & OTP · OTP Journey\nToken · Authorization · Platform · Reliability · Cross-region", PALE_BLUE, BLUE)
    d.box(p, 17800, 7900, 14000, 4700, "Operational usability", "Environment/cluster filters\nStable UID + auto provisioning\nNo-data handling\nExemplar drill-down", PALE_GREEN, GREEN)

    p = d.slide("Tính năng 5 — International OTP monitoring")
    d.flow(p, ["Edge", "Kong", "IdP", "Redis", "Route", "Queue", "GSM", "Carrier"], 4400, 1200, 31300)
    d.box(p, 2500, 7700, 12800, 3600, "Synchronous path", "Request gửi OTP → provider chấp nhận", PALE_BLUE, BLUE)
    d.box(p, 18500, 7700, 12800, 3600, "Asynchronous delivery", "Provider accepted → delivery receipt", PALE_ORANGE, ORANGE)
    d.text(p, 2100, 13200, 29500, 1200, "International phone country không đồng nghĩa destination datacenter", 17, RED, bold=True, align=1)

    p = d.slide("Chia OTP journey thành 7 stage")
    stages = [("01", "edge_to_kong"), ("02", "kong_to_idp"), ("03", "redis_challenge"), ("04", "route_selection"), ("05", "queue_wait"), ("06", "gsm_submit"), ("07", "carrier_delivery")]
    for i, (num, name) in enumerate(stages):
        col, row = i % 4, i // 4
        x, y = 1500 + col * 7900, 3700 + row * 4000
        d.rect(p, x, y, 6900, 3000, WHITE, LINE)
        d.text(p, x + 350, y + 250, 1000, 700, num, 18, BLUE, bold=True)
        d.text(p, x + 350, y + 1100, 6200, 900, name, 14, NAVY, bold=True)
    d.box(p, 2500, 12300, 28500, 2300, "Terminal failure rule", "Stage lỗi được ghi nhận; journey dừng và không sinh stage phía sau.", PALE_ORANGE, ORANGE)

    p = d.slide("Tính năng 6 — Bottleneck detection + tracing")
    d.flow(p, ["Symptom", "Filter scope", "Compare stages", "Check evidence", "Open trace", "Assign owner"], 4600, 1200, 31400)
    d.box(p, 2500, 8000, 13000, 3800, "Metrics evidence", "Stage p95 + error ratio\nThroughput + queue depth\nFailure reason", PALE_BLUE, BLUE)
    d.box(p, 18300, 8000, 13000, 3800, "Trace evidence", "Waterfall duration\nFirst failed span\nRepeated pattern across samples", PALE_GREEN, GREEN)
    d.text(p, 2500, 13200, 28800, 900, "Kết luận khi có ít nhất 2 tín hiệu đồng thuận", 17, RED, bold=True, align=1)

    p = d.slide("Ví dụ trace waterfall — carrier bottleneck")
    spans = [("edge_to_kong", 0.02), ("kong_to_idp", 0.05), ("redis_challenge", 0.01), ("route_selection", 0.004), ("queue_wait", 0.07), ("gsm_submit", 0.34), ("carrier_delivery", 11.91)]
    max_v = max(v for _, v in spans)
    for i, (name, val) in enumerate(spans):
        y = 3400 + i * 1500
        d.text(p, 1500, y, 6500, 700, name, 12, INK, bold=i == 6)
        bar_w = max(120, int(21000 * val / max_v))
        d.rect(p, 8200, y, bar_w, 700, ORANGE if i == 6 else BLUE, ORANGE if i == 6 else BLUE, radius=False)
        d.text(p, 29600, y, 2300, 700, f"{val:g} s", 12, ORANGE if i == 6 else MUTED, bold=True, align=1)
    d.box(p, 19000, 14600, 12500, 1900, "Kết luận", "Carrier chiếm ~96% tổng latency → chuyển đúng provider owner.", PALE_ORANGE, ORANGE)

    p = d.slide("Kịch bản demo trực tiếp")
    d.flow(p, ["Baseline", "Trigger ID carrier", "p95 tăng", "Find stage", "Open Tempo", "Clear & recover"], 4600, 1200, 31400, PALE_GREEN)
    d.box(p, 2000, 8000, 9000, 4000, "1. Observe", "Journey success, p95, stage latency và queue ở trạng thái bình thường.", PALE_BLUE, BLUE)
    d.box(p, 12400, 8000, 9000, 4000, "2. Degrade", "Tăng 5× latency và 15% failure tại Indonesia carrier delivery.", PALE_ORANGE, ORANGE)
    d.box(p, 22800, 8000, 9000, 4000, "3. Prove", "Grafana localize stage; Tempo waterfall xác minh; clear scenario.", PALE_GREEN, GREEN)

    p = d.slide("Chất lượng, bảo mật và giới hạn")
    d.box(p, 1500, 3600, 9400, 6500, "Quality gates", "✓ Python and unit tests\n✓ Dashboard contract tests\n✓ Prometheus rule tests\n✓ Compose/config validation\n✓ GitOps + CI workflow", PALE_GREEN, GREEN)
    d.box(p, 12200, 3600, 9400, 6500, "Telemetry safety", "✓ Không phone/email/OTP/token\n✓ Không request ID trong labels\n✓ Bounded cardinality\n✓ trace_id chỉ để correlation", PALE_BLUE, BLUE)
    d.box(p, 22900, 3600, 8500, 6500, "Current limits", "• Synthetic traffic/traces\n• Một simulator\n• Mock delivery receipt\n• Threshold chưa là prod SLO", PALE_ORANGE, ORANGE)
    d.text(p, 2200, 12200, 29000, 1700, "Demo chứng minh contract và workflow — không khẳng định production topology", 19, NAVY, bold=True, align=1)

    p = d.slide("Kết quả và bước tiếp theo")
    d.box(p, 1500, 3600, 14000, 5400, "Giá trị đã đạt", "✓ Lab end-to-end, tái hiện sự cố\n✓ KPI/SLI/SLO + dashboards + alerts\n✓ OTP bottleneck bằng metrics + traces\n✓ Nền tảng tích hợp UAT", PALE_GREEN, GREEN)
    d.box(p, 18000, 3600, 14000, 5400, "Đề xuất tiếp theo", "1. Owner xác nhận topology/SLI\n2. Instrument Kong + Go services\n3. Propagate HTTP/gRPC/Kafka context\n4. UAT baseline và tune threshold", PALE_BLUE, BLUE)
    d.flow(p, ["Confirm", "Instrument", "Correlate", "Baseline", "Production"], 10500, 2300, 29000)
    d.text(p, 2300, 13900, 29000, 1700, "Không chỉ biết OTP chậm — xác định chậm ở đâu và cung cấp bằng chứng để chuyển đúng đội xử lý.", 19, NAVY, bold=True, align=1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", default="2002")
    args = parser.parse_args()

    local_ctx = uno.getComponentContext()
    resolver = local_ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local_ctx
    )
    ctx = resolver.resolve(
        f"uno:socket,host={args.host},port={args.port};urp;StarOffice.ComponentContext"
    )
    desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    doc = desktop.loadComponentFromURL("private:factory/simpress", "_blank", 0, ())
    build_deck(doc)
    output_url = uno.systemPathToFileUrl(args.output)
    doc.storeAsURL(output_url, (prop("FilterName", "Impress MS PowerPoint 2007 XML"), prop("Overwrite", True)))
    doc.close(True)


if __name__ == "__main__":
    main()
