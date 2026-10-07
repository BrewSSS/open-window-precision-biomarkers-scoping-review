# GPT-6 Luna effort timing (5-record batch, strict schema, default instructions) 2026-10-07

Same 5 pilot records (FS-000056, FS-000120, FS-000219, FS-000235, FS-000242); streaming harness scripts/codex_stream_call.py; isolated CODEX_HOME; ChatGPT HTTP/SSE provider.

| effort | time to completion s | input tokens | reasoning tokens | output tokens (incl. reasoning) | schema-valid | element agreement with GLM-Flash (of 25) | E5 values | E5 absent-with-quote contradictions |
|---|---|---|---|---|---|---|---|---|
| medium | 21.6 | 17823 | 0 | 1030 | 5/5 | 20 | abs abs abs abs pre | 4 |
| high | 70.6 | 17823 | 1398 | 2398 | 5/5 | 18 | pre abs abs pre pre | 0 |
| xhigh | 86.8 | 18827 | 3624 | 4590 | 5/5 | 18 | pre abs abs pre pre | 0 |
| max | 48.7 | 17823 | 5034 | 6047 | 5/5 | 18 | pre abs abs pre pre | 0 |

Root cause of the earlier 'xhigh never returns' observations: `codex exec` waits for EOF on an open stdin pipe before sending the request ('Reading additional input from stdin...' in stderr). Fixed by closing stdin (stdin=DEVNULL) in the harness. Codex upstream also has open issues on stalls without idle timeout (#50775, #31376, #41985); the isolated provider now sets request_max_retries 8, stream_max_retries 10, stream_idle_timeout_ms 240000, and the harness enforces a hard per-call cap.
