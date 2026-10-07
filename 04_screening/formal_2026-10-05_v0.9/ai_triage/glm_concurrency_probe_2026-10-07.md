# GLM concurrency probe 2026-10-07T12:27:32Z

model: glm-5.3-flash; endpoint: https://api.z.ai/api/anthropic; one record per request; no retries.

| 并发数 | 成功 | 429 | 其他失败 | 合规 JSON | 中位耗时 s | 最长耗时 s | 整批耗时 s |
|---|---|---|---|---|---|---|---|
| 4 | 4 | 0 | 0 | 4 | 21.62 | 36.51 | 36.5 |
| 8 | 8 | 0 | 0 | 8 | 7.82 | 66.42 | 66.4 |
| 8 | 8 | 0 | 0 | 7 | 13.68 | 35.76 | 35.8 |
| 12 | 12 | 0 | 0 | 12 | 6.85 | 113.66 | 113.7 |
| 16 | 16 | 0 | 0 | 16 | 14.83 | 84.78 | 84.8 |
| 16 | 13 | 3 | 0 | 13 | 9.52 | 31.41 | 31.4 |
| 24 | 14 | 10 | 0 | 13 | 6.77 | 37.72 | 37.7 |

Server messages seen:
- {"type":"error","error":{"type":"rate_limit_error","code":"1302","message":"[1302][Rate limit reached for requests][2026
