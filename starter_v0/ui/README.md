# AI Travel Planner Web UI

## Run

From the repository root, run:

```powershell
python .\starter_v0\ui\server.py `
  --provider openai `
  --version v3
```

Open <http://127.0.0.1:7860>.

## Optional model

```powershell
python .\starter_v0\ui\server.py `
  --provider openai `
  --model "<model>" `
  --version v3
```

## Gemini example

```powershell
python .\starter_v0\ui\server.py `
  --provider gemini `
  --version v3
```

The server also accepts `--host`, `--port`, `--history-window`, and
`--max-tool-rounds`. It binds to `127.0.0.1` by default. A configured provider
API key is still required for model responses; the browser never receives it.

## Evidence generated

Every new or reset browser conversation writes a UTF-8 JSON transcript under:

```text
starter_v0/transcripts/
```

The interface displays the session ID, transcript ID, local file path, save
status, and last saved time. Use **View transcript** or **Download JSON** to
inspect the active conversation's real turns, tool calls, results, and errors.

## Demo

The scenario panel contains 14 controlled demo prompts. The five primary
showcases are:

1. Thiếu điểm xuất phát
2. Một yêu cầu, nhiều nguồn
3. Sửa điểm xuất phát và hủy ý định cũ
4. Đổi payload, xác nhận cũ mất hiệu lực
5. Xác nhận chính xác, tạo mock booking

Use **Load prompt**, send each turn yourself, then use **Next turn**. The UI
does not fabricate expected answers or traces: every displayed call and result
comes from the configured provider and local Travel tool registry.

## Limitations

The application uses fictional deterministic classroom travel data. Prices,
schedules, and availability are not live. A successful
`create_booking_request` result is a mock request only; it never makes a real
reservation or payment.
