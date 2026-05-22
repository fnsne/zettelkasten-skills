---
id: decision-jwt-vs-session
created: 2026-05-15
updated: 2026-05-15
sources:
  - path: meetings/2026-04-12-auth-design.md
    note: 決策討論記錄
  - path: docs/auth-spec.pdf
    pages: 2-3
links:
  - auth-overview
  - auth-jwt-flow
  - decisions-log
tags: [decision, auth]
---

# 為什麼選 JWT 而非 session

## 摘要
本專案選擇 JWT (stateless token) 而非 server-side session,主因是需要支援
多服務間共享認證狀態,且避免單點 session store 成為瓶頸。

## 脈絡
2026/04 設計階段討論過三個選項:純 session、純 JWT、JWT + Redis 撤銷清單。

**選 JWT + Redis 撤銷清單** 的理由:
- 多個 microservice 需要驗證身份,JWT 可由各服務獨立驗章,不必每次回到 auth service
- 預期流量增長,server-side session 的 Redis store 會變成瓶頸
- Redis 仍保留 refresh token 狀態以支援撤銷,折衷兩者優點

**未選純 session** 因為:扛不住跨服務驗證的延遲。
**未選純 JWT** 因為:無法主動撤銷已簽發的 token。

實作落地見 [auth-jwt-flow](./auth-jwt-flow.md),session 與撤銷邏輯見 [auth-session-mgmt](./auth-session-mgmt.md)。

## 何時往下追
- 實作怎麼做 → [auth-jwt-flow](./auth-jwt-flow.md)
- 撤銷怎麼運作 → [auth-session-mgmt](./auth-session-mgmt.md)
- 完整決策記錄 → `meetings/2026-04-12-auth-design.md`
- 其他歷史決策 → [decisions-log](./decisions-log.md)
