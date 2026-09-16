# Live transcript evidence — AI Travel Planner v3

Các file dưới đây do Web UI gọi thật `gpt-4o-mini` và tool registry cục bộ tạo
ra với artifact `v3+p6850ec08cdb5+t080ff8930e75`. Đây không phải hội thoại
được viết tay hoặc kết quả dự đoán.

| Scenario | Transcript | Evidence |
|---|---|---|
| Yêu cầu bình thường, nhiều nguồn | [JSON](ui_v3_openai_20260916T003616273426_5d259454.transcript.json) | `search_transport`, `search_hotels`, `search_attractions` |
| Thiếu thông tin rồi bổ sung | [JSON](ui_v3_openai_20260916T003845823005_10d2c039.transcript.json) | `clarify`, sau đó `search_hotels` |
| Nhiều lượt, sửa và đổi ý định | [JSON](ui_v3_openai_20260916T015551357965_284c3d1a.transcript.json) | Sửa HAN thành SGN; lượt cuối chuyển sang `search_attractions` |
| Hành động ghi sau xác nhận rõ | [JSON](ui_v3_openai_20260916T015511435960_117a7c29.transcript.json) | `clarify`, sau đó `create_booking_request`; request `MOCK-10D3620E8C` |

## Trace giới hạn cần giữ trong báo cáo

[JSON](ui_v3_openai_20260916T015448706115_d5264620.transcript.json) cho thấy
câu yêu cầu “nhắc lại” đã bị hiểu nhầm là xác nhận, dẫn tới một mock write trước
lượt xác nhận rõ. Trace này được giữ làm bằng chứng rằng prompt-only confirmation
chưa phải enforcement an toàn tuyệt đối.
