---
id: auth-jwt-flow
created: 2026-05-15
updated: 2026-05-15
sources:
  - path: src/auth/jwt.ts
    lines: 12-89
    note: 簽發實作
  - path: docs/auth-spec.pdf
    pages: 4-6
links:
  - auth-overview
  - decision-jwt-vs-session
  - auth-session-mgmt
  - security-token-rotation
tags: [auth, security]
---

# JWT 簽發流程

## 摘要
JWT 簽發流程是本系統認證的核心步驟,負責在使用者登入後產生帶 user payload
的 stateless token。根據[當初的決策](./decision-jwt-vs-session.md),本系統採
stateless 設計而非 server-side session。

## 內容
登入請求依[auth layer 規範](./architecture-auth-layer.md),先由 API gateway
驗證請求格式,再交給 auth service 處理。auth service 從資料庫驗證帳密後,
組裝 payload(uid, role, exp)並用 RS256 簽發。

簽發後的 token 狀態追蹤交給 [auth-session-mgmt](./auth-session-mgmt.md) 負責,
並搭配[token rotation 策略](./security-token-rotation.md)降低洩漏風險——
refresh token 一次性使用,使用後立即作廢。

## 何時往下追
- 為什麼選 JWT,不選 session → [decision-jwt-vs-session](./decision-jwt-vs-session.md)
- session / refresh token 怎麼配合 → [auth-session-mgmt](./auth-session-mgmt.md)
- rotation 策略細節 → [security-token-rotation](./security-token-rotation.md)
- 實作程式碼 → `src/auth/jwt.ts:12-89`
- 規格原文 → `docs/auth-spec.pdf` p.4-6
