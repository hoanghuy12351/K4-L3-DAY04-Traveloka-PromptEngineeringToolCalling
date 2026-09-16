# TEAM — Day04, K4-L3B

**Làm nhóm.** Mỗi thành viên tự viết và commit phần INDIVIDUAL của mình.

## Thông tin bài nộp

- Tên nhóm: Traveloka
- Người đại diện / MSSV: Võ Huy Hoàng — 2A202602548
- Tên repo: `K4-L3-DAY04-Traveloka-PromptEngineeringToolCalling`
- URL repo: <https://github.com/hoanghuy12351/K4-L3-DAY04-Traveloka-PromptEngineeringToolCalling>
- Nhánh nộp: `main`
- Commit chốt: **Cập nhật sau commit cuối bằng `git rev-parse --short HEAD`.**
- Deadline: theo thông báo chính thức trên VLearn; mốc mặc định được mô tả trong
  [SUBMISSION.md](SUBMISSION.md).

## Thành viên

| Họ và tên      | MSSV        | GitHub          | Vai trò và công việc                                                                                                   | File/commit/PR                                                                                                                            |
| -------------- | ----------- | --------------- | ---------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Võ Huy Hoàng   | 2A202602548 | `hoanghuy12351` | Dữ liệu Travel; bộ eval cơ bản, nhóm và adversarial; cải thiện prompt v0/v1/v3; phân tích kết quả và hoàn thiện report | `3bbd221`, `b83b5b2`, `a0dc3a2`, `9e97aa9`, `2ace6f9`; `starter_v0/data/`, `starter_v0/analysis/`, `starter_v0/artifacts/REPORT.md`       |
| Bùi Quang Vinh | 2A202603012 | `vbwork2`       | Xây Travel tools và tool schema; cải thiện system prompt v2 với pre-tool argument gate; tích hợp/evaluate v3; xây Web UI, runtime và transcript | `13d1500`, `023d7bb`, `f56a4dd`; `starter_v0/tools/`, `starter_v0/artifacts/tools.yaml`, `starter_v0/artifacts/system_prompt.md`, `starter_v0/ui/`, `starter_v0/transcripts/` |

## Nhận xét chung

- Kết quả và bằng chứng:
  - Base eval tăng từ `0.6333` ở v0 lên `0.7667` ở v1, `0.8000` ở v2 và
    `0.8667` ở v3. Chi tiết nằm trong
    [version_log.csv](starter_v0/artifacts/version_log.csv) và
    [REPORT.md](starter_v0/artifacts/REPORT.md#b1-version-evidence).
  - Team eval đạt `9/10`; adversarial eval đạt `8/12`, đều có
    `provider_error_cases=0`.
  - Web UI hiển thị phiên bản, model, tool call, arguments, kết quả/lỗi và lưu
    transcript thật. Danh mục bằng chứng nằm tại
    [transcripts/EVIDENCE.md](starter_v0/transcripts/EVIDENCE.md).
- Thay đổi hiệu quả nhất:
  - v1 làm rõ enum sở thích, ánh xạ phương tiện và quy tắc giữ nguyên option ID
    trong `tools.yaml`, giúp case accuracy tăng `0.1334`.
  - v3 ràng buộc xác nhận với payload hiện tại, sửa case xác nhận cũ bị tái sử
    dụng và đưa multiturn accuracy lên `0.9000` trong run base được chọn.
- Giới hạn còn lại:
  - Model đôi lúc bỏ `mode=flight`, tự suy đoán ngày còn thiếu hoặc tách một
    yêu cầu điểm tham quan thành nhiều tool call.
  - Prompt-only confirmation chưa đủ an toàn: các case A03, A04, A11 và một
    live trace đã tạo mock request khi xác nhận không hợp lệ. Không có dữ liệu
    thật hoặc exfiltration, nhưng write boundary vẫn cần enforcement trong code.
- Cách phân công và tích hợp:
  - Hoàng phụ trách dữ liệu, eval, version evidence, safety review và report.
  - Vinh phụ trách tool implementation, prompt iteration, runtime và Web UI.
  - Hai thành viên tích hợp trên nhánh `main`, dùng run JSON, artifact hash và
    transcript để kiểm tra thay đổi trước khi chốt bài.

## INDIVIDUAL

Mỗi thành viên phải tự hoàn thiện và commit mục của mình. Không chép cùng một
nội dung cho cả hai người.

### Võ Huy Hoàng — 2A202602548

- Phần việc và file/commit/PR: dữ liệu Travel, eval, version log, run analysis,
  adversarial review và report; tham chiếu các commit `3bbd221`, `b83b5b2`,
  `a0dc3a2`, `9e97aa9`, `2ace6f9`.
- Quyết định, khó khăn và cách xử lý: Tôi chuyển bộ kiểm thử từ Helpdesk sang Travel và kiểm tra tên tool trước khi chạy.
- Điều đã học: Tôi hiểu cách thiết kế tool schema và dùng eval để cải thiện system prompt.
- AI/công cụ đã dùng và cách kiểm tra: Dùng Codex hỗ trợ phân tích; tự kiểm tra bằng run JSON, tool trace và report.
- Thời điểm đã tự nộp URL repo chung trên VLearn: 16/09/2026, 10:30.

### Bùi Quang Vinh — 2A202603012

- Phần việc và file/commit/PR: Tôi phụ trách xây dựng các Travel tools và schema công cụ cho AI Travel Planner, cải thiện system prompt ở vòng v2, tích hợp runtime/evaluation và xây Web UI để theo dõi tool call, arguments, kết quả và transcript. Các commit kỹ thuật chính của tôi gồm `13d1500` (xây Travel tools và cập nhật `tools.yaml`), `023d7bb` (bổ sung `Pre-tool argument gate` cho `system_prompt.md` và cải thiện v2), và `f56a4dd` (tích hợp v3, Web UI và transcript). Các file chính gồm `starter_v0/tools/`, `starter_v0/artifacts/tools.yaml`, `starter_v0/artifacts/system_prompt.md`, `starter_v0/ui/` và `starter_v0/transcripts/`.

- Quyết định, khó khăn và cách xử lý: Khó khăn lớn nhất của tôi là model có thể chọn đúng tool nhưng vẫn truyền thiếu hoặc sai argument, ví dụ bỏ sót `mode=flight`, tự suy đoán ngày hoặc điểm xuất phát khi người dùng chưa cung cấp, tách một yêu cầu tìm điểm tham quan thành nhiều tool call, và có thể dùng lại xác nhận cũ sau khi payload booking đã thay đổi. Tôi xử lý bằng cách bổ sung `Pre-tool argument gate` trong v2: trước mỗi tool call phải kiểm tra đủ required fields, chuẩn hóa các giá trị như transport mode và interests, giữ nguyên ID do người dùng cung cấp, không tự suy đoán dữ kiện còn thiếu và kiểm tra lại booking payload trước write action. Khi thiếu thông tin, agent phải dùng `clarify` thay vì tự điền giá trị.

- Điều đã học: Qua bài lab tôi hiểu rõ hơn rằng chất lượng của agent không chỉ phụ thuộc vào system prompt mà còn phụ thuộc mạnh vào tool schema, required fields, cách chuẩn hóa argument và cách quản lý state của hội thoại nhiều lượt. Tôi cũng học được cách dùng eval theo từng version để kiểm tra một thay đổi prompt có thực sự cải thiện hành vi hay không thay vì chỉ nhìn vào câu trả lời cuối. Ngoài ra, việc xây UI và lưu transcript giúp tôi thấy rõ toàn bộ quá trình model chọn tool, truyền arguments và xử lý kết quả, từ đó dễ phát hiện các lỗi về missing information, wrong argument và confirmation boundary hơn.

- AI/công cụ đã dùng và cách kiểm tra: Tôi dùng ChatGPT/Codex để hỗ trợ đọc lỗi, đề xuất hướng sửa prompt, hỗ trợ code và phân tích tool trace. Tôi không chỉ dựa vào output của AI mà kiểm tra lại bằng Git diff, run JSON, `version_log.csv`, case accuracy, tool calls/arguments, Web UI và các transcript thực tế. Với v2, tôi đối chiếu run trước và sau thay đổi để kiểm tra `case_accuracy` tăng từ `0.7667` lên `0.8000`; với UI tôi chạy thử các scenario thiếu thông tin, multi-turn và booking confirmation để kiểm tra agent có gọi đúng tool và giữ đúng trạng thái hội thoại.

- Thời điểm đã tự nộp URL repo chung trên VLearn: 9h30 16/9/2026
