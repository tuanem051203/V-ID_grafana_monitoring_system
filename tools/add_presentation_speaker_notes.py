#!/usr/bin/env python3
"""Create a copy of the V-ID deck with Vietnamese speaker notes."""

from __future__ import annotations

import html
import re
import zipfile
from pathlib import Path


SOURCE = Path("V-ID_Observability_Presentation.pptx")
OUTPUT = Path("V-ID_Observability_Presentation_with_speaker_notes.pptx")

NOTES = {
    1: [
        "Mở ý: Xin chào mọi người. Hôm nay tôi giới thiệu V-ID Grafana Monitoring System, một observability lab dành cho Identity Platform.",
        "Nội dung chính: Đây không phải là một dashboard đơn lẻ. Project xây dựng một luồng hoàn chỉnh từ synthetic traffic, metrics và recording rules, đến alerting, dashboard và distributed tracing. Mục tiêu là chuẩn hóa cách phát hiện và chẩn đoán vấn đề trước khi kết nối với telemetry UAT thật.",
        "Chuyển ý: Trước khi đi vào kiến trúc, chúng ta cần thống nhất câu hỏi mà hệ thống monitoring phải trả lời.",
    ],
    2: [
        "Mở ý: Monitoring hữu ích không chỉ cho biết hệ thống đang lỗi, mà còn phải chỉ ra người dùng đang bị ảnh hưởng ở flow nào và điểm nào cần điều tra.",
        "Nội dung chính: Project theo dõi các outcome quan trọng như authentication, OTP, token và availability. Metrics và SLO giúp phát hiện bất thường; dashboard giúp khoanh vùng; trace được dùng khi cần xem request path. Với OTP, câu hỏi không dừng ở việc OTP chậm mà phải xác định chậm tại Kong, IdP, Redis, queue, nhà cung cấp GSM hay carrier delivery.",
        "Chuyển ý: Từ mục tiêu đó, project giới hạn scope vào các luồng có ảnh hưởng trực tiếp tới identity, access và trải nghiệm OTP.",
    ],
    3: [
        "Mở ý: Scope observability được tổ chức theo user journey và business boundary, thay vì chỉ liệt kê từng service.",
        "Nội dung chính: Năm nhóm chính gồm Authentication, OTP, Token, Authorization và Platform. Authentication bao phủ cả IdP native hoặc transition và Hydra browser OIDC. OTP bao phủ send, delivery, verify và từng journey stage. Authorization phân biệt policy denial với system error. Platform sử dụng RED signals và dependency health. Các boundary như Kong, Redis, Postgres, Kafka và notification provider đều được mô hình hóa để hỗ trợ triage.",
        "Chuyển ý: Với scope này, slide tiếp theo cho thấy telemetry đi xuyên suốt hệ thống như thế nào.",
    ],
    4: [
        "Mở ý: Kiến trúc sử dụng một flow thống nhất cho metrics, alerting và tracing, trong đó Grafana là điểm hội tụ để vận hành.",
        "Nội dung chính: Metrics Simulator tạo traffic tổng hợp và expose metrics cho Prometheus. Prometheus scrape dữ liệu và tính 62 recording rules; 17 alert rules được chuyển tới Alertmanager. Khoảng một phần traffic OTP journey được gửi qua OTel Collector vào Tempo. Grafana sử dụng các nguồn này trong 8 dashboard cốt lõi. Nguyên tắc thiết kế là metrics trả lời cái gì đang xấu, còn trace trả lời xấu tại stage hoặc request path nào. Identifier có cardinality cao chỉ thuộc trace hoặc log, không đưa vào metric label.",
        "Chuyển ý: Trên kiến trúc đó, chúng ta chuẩn hóa sáu KPI cốt lõi.",
    ],
    5: [
        "Mở ý: Sáu KPI này chuyển các tín hiệu kỹ thuật thành outcome mà owner và đội vận hành có thể cùng thống nhất.",
        "Nội dung chính: Authentication success, token issuance success và platform availability hướng tới 99,9% trong 30 ngày. Authentication latency yêu cầu ít nhất 95% request dưới 500 mili giây. OTP delivery success có target 95% ở cả cửa sổ 24 giờ và 30 ngày. KPI-04, OTP verification success, hiện chỉ là baseline; chưa có SLO alert vì cần dữ liệu thực và owner phê duyệt trước. Mỗi KPI đều phải có numerator, denominator, target, window và exclusion rõ ràng.",
        "Chuyển ý: Để dashboard và alert không hiểu KPI theo hai cách khác nhau, project dùng một metric contract chung.",
    ],
    6: [
        "Mở ý: Metric contract là lớp chuẩn hóa nằm giữa raw telemetry và các nội dung người dùng nhìn thấy trên Grafana hoặc Alertmanager.",
        "Nội dung chính: Counter được đọc bằng rate hoặc increase; histogram thống nhất đơn vị giây; numerator phải là tập con của denominator. Labels chỉ dùng các dimension hữu hạn như environment, cluster, service, operation và result. PII, token, OTP, user ID, request ID và trace ID bị cấm làm label để tránh rò rỉ dữ liệu và cardinality explosion. 62 recording rules giúp dashboard và alert dùng cùng một định nghĩa PromQL, đồng thời giảm việc lặp truy vấn phức tạp.",
        "Chuyển ý: Sau khi có contract thống nhất, các câu hỏi vận hành được thể hiện thành hệ thống dashboard.",
    ],
    7: [
        "Mở ý: Dashboard được chia theo câu hỏi vận hành và user journey, không chỉ theo tên service.",
        "Nội dung chính: Overview cho biết sức khỏe tổng thể. Các dashboard Authentication, MFA & OTP, OTP Journey, Token Lifecycle và Authorization phục vụ từng flow. Platform & Dependencies hỗ trợ RED và dependency health; SLO & Incidents tập trung vào error budget và burn rate. Ngoài 8 dashboard cốt lõi còn có Platform deep-dive Requests, nên tổng artifact hiện tại là 9 dashboard và 83 panel. Variables dùng các dimension bounded, còn datasource UID ổn định giúp promote giữa các environment.",
        "Chuyển ý: Điểm nổi bật nhất trong nhóm dashboard là khả năng phân tích OTP Journey theo từng stage.",
    ],
    8: [
        "Mở ý: OTP Journey Monitoring giúp chuyển một triệu chứng chung là OTP chậm thành một vị trí điều tra cụ thể.",
        "Nội dung chính: Journey được tách từ edge, Kong, IdP, Redis, routing, queue, GSM submit đến carrier delivery. Metrics hiển thị p95 và error ratio theo stage, cùng queue depth hoặc delivery receipt, có thể lọc theo country, provider và channel. Khoảng 10% journey synthetic được sample để trace; exemplar trên histogram mang trace ID và mở trực tiếp waterfall trong Tempo. Khi triage, cần tìm stage đầu tiên lệch baseline và yêu cầu ít nhất hai tín hiệu đồng thuận; không kết luận chỉ từ một trace.",
        "Chuyển ý: Ví dụ tiếp theo minh họa vì sao việc tách stage giúp tránh quy trách nhiệm sai.",
    ],
    9: [
        "Mở ý: Trong ví dụ này, người dùng chờ OTP tổng cộng 12,4 giây, nhưng phần lớn thời gian không nằm trong synchronous path của V-ID.",
        "Nội dung chính: Các stage nội bộ như edge, Kong, IdP, Redis, routing và queue chỉ chiếm thời gian rất nhỏ. GSM submit mất 0,34 giây, trong khi carrier delivery mất 11,91 giây, tương đương khoảng 96% tổng latency. Waterfall vì vậy hướng điều tra sang downstream provider hoặc carrier, thay vì đổ lỗi cho IdP hay queue. Đây vẫn là giả thuyết triage và phải được xác nhận bằng metric theo stage, error ratio, queue hoặc provider signals.",
        "Chuyển ý: Để kiểm thử được tình huống như vậy trước khi có UAT telemetry, project sử dụng synthetic traffic.",
    ],
    10: [
        "Mở ý: Simulator tạo traffic có kiểm soát để kiểm thử observability contract, không phải để mô phỏng chính xác năng lực production.",
        "Nội dung chính: Các profile từ development 20 TPS đến peak 2.000 TPS phát ra tín hiệu cho authentication, OTP, token, HTTP và dependencies. Failure scenarios gồm latency degradation, error-rate increase, queue backlog và provider hoặc delivery delay. Nhờ đó có thể kiểm tra recording rules, SLO và burn rate, hành vi dashboard, alert routing và runbook triage trước UAT. Cần nhấn mạnh rằng dữ liệu synthetic không được dùng để suy ra production baseline, capacity hay threshold cuối cùng.",
        "Chuyển ý: Một trong những phần quan trọng được kiểm thử bằng simulator là SLO, error budget và burn rate.",
    ],
    11: [
        "Mở ý: Alerting được thiết kế theo mức ảnh hưởng người dùng và tốc độ tiêu error budget, thay vì page chỉ vì CPU hoặc số pod thay đổi.",
        "Nội dung chính: Error budget bằng một trừ SLO; burn rate là tỷ lệ lỗi quan sát được chia cho tỷ lệ lỗi cho phép. Với SLO 99,9%, budget chỉ là 0,1%, nên burn rate lớn hơn một nghĩa là đang tiêu budget quá nhanh. Alert yêu cầu đủ traffic và nhiều cửa sổ thời gian đồng thuận. No-data không được coi là 0% lỗi hoặc 100% thành công. Invalid credential, OTP sai hoặc hết hạn, và policy denial cũng không mặc định là platform failure. KPI-04 chưa page vì còn ở giai đoạn baseline.",
        "Chuyển ý: Khi alert thực sự fire, runbook chuẩn hóa cách đội vận hành đi từ tín hiệu tới hành động.",
    ],
    12: [
        "Mở ý: Project có 17 alert rules, nhưng giá trị vận hành nằm ở quy trình triage nhất quán sau khi nhận alert.",
        "Nội dung chính: Trước tiên xác nhận environment, thời gian, client và flow bị ảnh hưởng. Sau đó đi từ Overview vào dashboard chi tiết, tìm service hoặc stage đầu tiên suy giảm, rồi mở Tempo exemplar và đối chiếu với thay đổi gần nhất. Chỉ kết luận bottleneck khi có ít nhất hai tín hiệu; alert labels không chứa PII. Mitigation phải nằm trong thủ tục đã được owner phê duyệt. Cuối cùng cần xác nhận SLI phục hồi và không xuất hiện làn sóng retry hoặc backlog sau phục hồi.",
        "Chuyển ý: Để quy trình này hoạt động nhất quán ở nhiều môi trường, deployment cũng được quản lý bằng profile và validation gates.",
    ],
    13: [
        "Mở ý: Cấu hình được render theo environment, còn artifact đã generate không phải source of truth và không được sửa thủ công.",
        "Nội dung chính: Renderer hỗ trợ local, UAT và production cùng các traffic profile 20, 100, 500 và 2.000 TPS. Output gồm Docker Compose, Prometheus rules, Alertmanager config, Grafana datasource và resolved config. Secret không nằm trong config JSON; production cần secret manager hoặc Kubernetes Secret. Trước khi merge, quality gate kiểm tra Python, dashboard JSON contract, Prometheus config và rules, sáu KPI rule tests, Alertmanager, Docker Compose và smoke test. Một gate thất bại thì không promote.",
        "Chuyển ý: Từ các lớp contract, dashboard, alert và deployment đó, chúng ta có thể tổng kết những artifact project đã hoàn thành.",
    ],
    14: [
        "Mở ý: Project đã tạo được một baseline local và UAT có thể review, demo và kiểm thử bằng artifact được version-control.",
        "Nội dung chính: Hiện có 9 Grafana dashboard với 83 panel, 62 recording rules và 17 alert rules. Simulator bao phủ AuthN, OTP, token, AuthZ, HTTP, dependencies và sampled OTP traces. Stack gồm Prometheus, Grafana, Alertmanager, OTel Collector và Tempo. Ngoài ra còn có KPI contract, runbook, environment renderer, rule tests và smoke scripts. Các con số này mô tả artifact trong repo, không đồng nghĩa hệ thống đã production-ready hay threshold đã được xác thực bằng traffic thật.",
        "Chuyển ý: Vì vậy roadmap ưu tiên evidence và ownership thực tế thay vì chỉ tiếp tục tăng số dashboard.",
    ],
    15: [
        "Mở ý: Bước tiếp theo là thay các giả định synthetic bằng instrumentation, evidence và ownership thật trong UAT rồi mới promote có kiểm soát.",
        "Nội dung chính: Trước hết owner cần duyệt KPI boundary, exclusion, target, window và notification route. Sau đó triển khai ServiceMonitor hoặc PodMonitor, OTel middleware và trace propagation. Production còn cần SSO, RBAC, TLS, secret management, HA, storage và retention. UAT phải thu evidence cho trạng thái bình thường, suy giảm, no-data và low-traffic để tuning threshold, kèm rollout và rollback plan.",
        "Kết luận: Giá trị lớn nhất của project không nằm ở số dashboard, mà ở khả năng biến câu nói ‘hệ thống có vấn đề’ thành câu trả lời cụ thể: flow nào, KPI nào, stage nào và owner nào cần hành động. Xin cảm ơn mọi người.",
    ],
}


BODY_SHAPE = re.compile(
    rb'(<p:sp>\s*<p:nvSpPr>.*?<p:ph\s+type="body".*?</p:nvSpPr>.*?'
    rb'<p:txBody>\s*<a:bodyPr.*?</a:bodyPr>)(.*?)(</p:txBody>\s*</p:sp>)',
    re.DOTALL,
)


def paragraph(text: str) -> bytes:
    value = html.escape(text, quote=False)
    return (
        '<a:p><a:pPr marL="0" indent="0"><a:buNone/></a:pPr>'
        '<a:r><a:rPr lang="vi-VN" sz="1800"/><a:t>'
        f'{value}</a:t></a:r><a:endParaRPr lang="vi-VN" sz="1800"/></a:p>'
    ).encode("utf-8")


def update_notes_xml(data: bytes, lines: list[str]) -> bytes:
    replacement = b"".join(paragraph(line) for line in lines)
    updated, count = BODY_SHAPE.subn(
        lambda match: match.group(1) + replacement + match.group(3), data, count=1
    )
    if count != 1:
        raise RuntimeError("Could not find the notes body placeholder")
    return updated


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    with zipfile.ZipFile(SOURCE, "r") as src, zipfile.ZipFile(
        OUTPUT, "w", compression=zipfile.ZIP_DEFLATED
    ) as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            match = re.fullmatch(r"ppt/notesSlides/notesSlide(\d+)\.xml", item.filename)
            if match:
                slide_number = int(match.group(1))
                data = update_notes_xml(data, NOTES[slide_number])
            dst.writestr(item, data)

    print(f"Created {OUTPUT} with speaker notes for {len(NOTES)} slides")


if __name__ == "__main__":
    main()
