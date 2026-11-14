# scheduler（Cloudflare Worker）

GitHub Actions 的排程常延遲（實測 19～87 分鐘）甚至整次跳過，所以由這個 Worker 準時啟動 `update.yml`（`workflow_dispatch`）。`update.yml` 自己的排程保留作為備援。

每天臺灣時間 07:30、08:30、09:30、15:30、21:30 各啟動一次（cron 是 UTC，見 `wrangler.toml`）。

告警不在這裡做：`update.yml` 每次執行完都會回報 healthchecks.io（成功或失敗），太久沒收到成功回報、或收到失敗時，由 healthchecks.io 通知。所以不論是這個 Worker 停擺、token 過期，還是 GitHub 排程漏跑，都會被發現。

## 設定

需要 GitHub fine-grained personal access token：

* Repository access：Only select repositories → 本 repo
* Permissions：Actions → Read and write（Metadata 會自動加上唯讀）
* 有到期日。到期後啟動會失敗，資料不再更新，healthchecks.io 會通知；屆時換新 token 即可。

在本資料夾執行：

```
npx wrangler login
npx wrangler secret put GITHUB_TOKEN   # 貼上 token
npx wrangler deploy
```

repo 的 Actions secret `HC_PING_URL` 設為 healthchecks.io check 的 ping 網址；沒設時 `update.yml` 略過回報。
