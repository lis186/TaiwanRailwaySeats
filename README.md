# TaiwanRailwaySeats

把臺鐵「全線剩餘票」開放資料整理成依乘車日分檔的 JSON，每天檢查四次來源，並保留每次變動的 git 歷史。

本專案是 [TaiwanTyphoonDays](https://github.com/lis186/TaiwanTyphoonDays) 的同作者姊妹專案，做法相同：GitHub Actions 定時抓取、整理成結構化 JSON 後 commit，並透過 jsDelivr 提供。

## 關於

資料來源為國營臺灣鐵路股份有限公司在政府資料開放平臺提供的[臺鐵全線剩餘票](https://data.gov.tw/dataset/37933)。
原始檔直接使用有下列困難：

* 單一 JSON 檔約 50 MB、約 48 萬筆，沒有換行，只想查一天也得下載整份
* 所有欄位（包括座位數）都是字串，記錄沒有固定順序
* 沒有任何時間資訊，無法得知是什麼時候的資料

故依乘車日拆成小檔、排序並固定格式，另以 `meta.json` 記錄本專案首次看到這份內容的時間。

## 資料檔

```
data/meta.json
data/{乘車日 YYYY-MM-DD}.json
```

`data/` 與來源目前的內容一致：來源有哪幾天就有哪幾個檔案，來源不再提供的日期（通常是已經過去的日期）會被刪除。要查某天有沒有資料，請讀 `meta.json` 的 `dates`。舊資料保留在 git 歷史中。

### 取用連結

需要最新資料時（例如程式定時抓取），請用 raw.githubusercontent.com，快取約 5 分鐘：

```
https://raw.githubusercontent.com/lis186/TaiwanRailwaySeats/main/data/meta.json
https://raw.githubusercontent.com/lis186/TaiwanRailwaySeats/main/data/{YYYY-MM-DD}.json
```

也可以用 jsDelivr CDN：

```
https://cdn.jsdelivr.net/gh/lis186/TaiwanRailwaySeats@main/data/meta.json
https://cdn.jsdelivr.net/gh/lis186/TaiwanRailwaySeats@main/data/{YYYY-MM-DD}.json
```

jsDelivr 會快取分支路徑最多 12 小時，而且每個檔案各自快取，所以可能拿到新的 `meta.json` 配上舊的日檔。請保留路徑中的 `@main`；需要固定版本時改成 `@<commit>`。

### 建議讀法

1. 先讀 `meta.json`，從 `dates` 確認該日有資料，並記下 `rows` 與 `freeSeats`。
2. 再讀該日檔案，確認筆數等於 `rows`、座位合計等於 `freeSeats`。不一致代表兩個檔案來自不同版本（CDN 快取），請稍後重試。
3. 可用 `sourceSha256` 判斷內容是否有更新，沒變就不必重抓日檔。

## 資料格式

### 日檔

依（車次的數值、起站代碼、迄站代碼）排序的陣列，一筆一行：

```json
[
{"trnOpDate":"2026-11-20","trnNo":"21","seatOriStaCode":"0990","seatDstStaCode":"1000","freeSeats":8},
{"trnOpDate":"2026-11-20","trnNo":"21","seatOriStaCode":"0990","seatDstStaCode":"1020","freeSeats":4}
]
```

| 欄位 | 說明 |
|---|---|
| `trnOpDate` | 乘車日 `YYYY-MM-DD`，與檔名相同 |
| `trnNo` | 車次，數字字串 |
| `seatOriStaCode` | 起站代碼（新版四碼站碼） |
| `seatDstStaCode` | 迄站代碼 |
| `freeSeats` | 剩餘座位數，整數 |

欄位名稱與順序和來源相同；與來源的差別只有 `freeSeats` 由字串轉為整數，以及記錄有排序。

常用站碼：臺北 `1000`、板橋 `1020`、新竹 `1210`、臺中 `3300`、彰化 `3360`、嘉義 `4080`、臺南 `4220`、新左營 `4340`、高雄 `4400`、屏東 `5000`、臺東 `6000`、花蓮 `7000`、宜蘭 `7190`。完整對照表見[臺鐵每日時刻表](https://data.gov.tw/dataset/6138)的開發手冊。

### `meta.json`

```json
{
  "schemaVersion": 1,
  "source": "https://ods.railway.gov.tw/tra-ods-web/ods/download/dataResource/5a2e672be26f4467a98f121d9ef43885",
  "sourceSha256": "05fe5540e694bcc5bbb2c801ffae744b772fe74947608153e458ddc1362e68bc",
  "firstSeenAt": "2026-11-13T19:10:13+08:00",
  "dates": {
    "2026-11-13": {"rows": 12428, "freeSeats": 211491}
  }
}
```

（`dates` 只節錄 1 天。）

| 欄位 | 說明 |
|---|---|
| `schemaVersion` | 格式版本，目前為 `1` |
| `source` | 原始檔下載網址 |
| `sourceSha256` | 產生這份資料的原始檔 SHA-256 |
| `firstSeenAt` | 本專案**首次抓到**這份內容的時間（臺灣時間）。來源沒有提供產生時間，所以這不是臺鐵的快照時間，最多可能晚 6 小時 |
| `dates` | 每個乘車日的筆數 `rows` 與座位合計 `freeSeats` |

`meta.json` 只在日檔內容有變動時才會更新，並與日檔放在同一個 commit；內容沒變的抓取不會產生 commit。

### 格式穩定性

上述就是全部的欄位，欄位名稱、型別與順序都固定（`tests/test_data.py` 檢查）。若日後需要變更，會遞增 `schemaVersion`，並在 commit 訊息與本文件註明。

## 使用上的注意事項

以下例子取自 2026-11-13 抓到的資料（`sourceSha256` 為 `05fe5540…`），可從 git 歷史重現。

**1. 沒有 0。** 整份資料沒有任何 `freeSeats` 為 0 的記錄；剩 0 的組合不會出現。

**2. 座位依起訖組合分開配額。** 同一班車，某個起訖組合沒有出現，另一個組合仍可能有座位。例：11/27 第 410 次沒有臺北 → 高雄（`1000` → `4400`），但有臺北 → 新左營（`1000` → `4340`）14 位。

**3. 「沒出現」不等於售完。** 一個起訖組合在資料中沒有出現，可能是已售完，也可能仍有座位，單看這份資料無法分辨。2026-11-13 到臺鐵訂票網站查證：11/18 臺北 → 高雄第 115 次在資料中沒有出現，網站上**有位**；11/27 臺北 → 臺中第 141 次在資料中沒有出現，網站上**沒位**。另外，11/18（週三）由臺北經過高雄的 32 班對號車中，有 16 班沒有臺北 → 高雄的記錄；同一天臺北 → 臺中的 29 班則全部都有。

**4. 不是即時資料。** 依 2026-11-13 的觀察，來源在數小時內內容完全相同，當天已開出的車次也仍在資料中，看起來是每天產生一次的快照。實際的更新時間尚在觀察中。`firstSeenAt` 只能說明本專案何時抓到，不代表座位在那個時間的狀況。

**5. 只有對號車。** 區間車等非對號列車不在資料中。資料大致涵蓋今天起約一個月，更後面的日期只有零星筆數。

## 更新資料

需求：Python 3（僅用標準函式庫）。於專案根目錄執行：

```
python3 scripts/fetch.py     # 下載原始檔到 .cache/seat.json（約 50 MB）
python3 scripts/build.py     # 產生 data/
python3 -m unittest discover -s tests   # 驗證
```

`.cache/` 不納入版控。

### 測試

* `tests/test_build.py`：用手寫的小份原始資料檢查轉換結果逐字正確、輸出不受來源順序影響、內容沒變時不改任何檔案，以及壞資料一定被拒絕。
* `tests/test_data.py`：檢查 `data/` 的欄位、型別、排序、唯一性，以及 `meta.json` 與日檔一致。

### 自動更新

`.github/workflows/update.yml` 每天四次（臺灣時間 07:37、09:37、15:37、21:37）自動執行，也可在 Actions 頁面手動觸發：

1. 下載原始檔並轉換。原始檔看起來有問題時**不發布**，該次執行標為失敗：不是合法 JSON、有欄位缺漏或格式不符、同一天有重複的組合、沒有今天（臺灣時間）的資料，或總筆數不到目前已發布的一半。
2. 通過驗證、且日檔有變動才 commit。
3. commit 後分別向 jsDelivr 與 raw.githubusercontent.com 取回檔案比對，並記錄 repo 大小（只量測、不清快取）。
4. 公開 repo 若 60 天沒有任何活動，GitHub 會停用排程，所以距離上次 commit 超過 30 天時會提交標記檔 `.github/keepalive`。
5. 最後檢查本文件的說明是否仍成立：出現 `freeSeats` 為 0、出現以前沒見過的站碼，或來源多了欄位時，**資料仍會發布，但該次執行會標為失敗**，請檢視後更新本文件。

## 授權

### 程式碼

`scripts/` 下的程式碼以 [MIT License](LICENSE) 授權。

### 資料

`data/` 的原始內容來自國營臺灣鐵路股份有限公司，依[政府資料開放授權條款－第 1 版](https://data.gov.tw/license)提供，使用時應註明出處。

使用本專案資料時請標示：

> 資料來源：國營臺灣鐵路股份有限公司「臺鐵全線剩餘票」，經 TaiwanRailwaySeats 整理

本專案是民間整理的非官方資料，**不代表臺鐵**；實際剩餘座位請以[臺鐵訂票系統](https://www.railway.gov.tw/)為準。
