---
id: auth-overview
created: 2026-05-15
updated: 2026-05-15
sources:
  - path: src/auth/
    note: 整個 auth 模組
  - path: docs/auth-spec.pdf
    pages: 1-3
links:
  - auth-jwt-flow
  - auth-session-mgmt
  - decision-jwt-vs-session
  - security-token-rotation
tags: [auth, 主題卡]
---

# Auth 模組總覽

## 摘要
本專案 auth 模組採 JWT + refresh token 的 stateless 設計,搭配 Redis
儲存 refresh token 狀態以支援撤銷。整體流程分為簽發、驗證、刷新、撤銷
四個階段。

## 設計概觀
登入後由 [JWT 簽發流程](./auth-jwt-flow.md)產生 access token 與 refresh token;
access token 短效(15 分鐘),refresh token 長效(14 天)。token 狀態與
撤銷由 [session 管理](./auth-session-mgmt.md)負責。

選擇 stateless 而非 server-side session 的脈絡見
[為什麼選 JWT 而非 session](./decision-jwt-vs-session.md)。為了降低 token 洩漏
風險,refresh 階段套用 [token rotation 策略](./security-token-rotation.md)。

## 子題導覽
- [auth-jwt-flow](./auth-jwt-flow.md) — token 怎麼簽發
- [auth-session-mgmt](./auth-session-mgmt.md) — session 怎麼追蹤與撤銷
- [decision-jwt-vs-session](./decision-jwt-vs-session.md) — 為什麼選這個架構
- [security-token-rotation](./security-token-rotation.md) — refresh token 一次性策略

## 何時往下追
- 想看完整登入流程 → [auth-jwt-flow](./auth-jwt-flow.md)
- 想看登出 / 撤銷邏輯 → [auth-session-mgmt](./auth-session-mgmt.md)
- 想理解架構決策 → [decision-jwt-vs-session](./decision-jwt-vs-session.md)
- 想看程式碼 → `src/auth/`
