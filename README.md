# dinner-app

家族で使う「晩ごはんいる?いらない?」確認アプリ。

## 構成
- Cloudflare Pages (静的ホスティング + Functions)
- Cloudflare D1 (家族共有データ保存)
- PWA (iPhoneホーム画面追加対応)

## ファイル
- `index.html` … アプリ本体 (フロント)
- `manifest.json` `sw.js` `icons/` … PWA関連
- `functions/api/state.js` … サーバーAPI (D1で読み書き)
- `schema.sql` … D1のテーブル定義

## デプロイ手順 (参考・初回のみ)
1. GitHubリポジトリを Cloudflare Pages に連携
2. D1 データベースを作成 → `schema.sql` を実行
3. Pages プロジェクトの「設定 → Functions → D1 バインディング」で
   変数名 `DB` に D1 を紐付け
4. 再デプロイ
