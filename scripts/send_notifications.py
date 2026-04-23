"""
晩ごはんアプリ プッシュ通知送信スクリプト
GitHub Actions から15分毎に呼ばれる。

処理内容:
1. Firestore の state ドキュメントを読む
2. 毎日 21:00 JST に「翌日空白」ならメイに通知(一日一回だけ)
3. `notifications` コレクションの未送信通知を処理して送信

設計メモ:
- FIREBASE_CREDENTIALS 環境変数に Firebase サービスアカウントJSONを入れる
- state.users に role フィールド(child / parent)
- state.tokens[userId] = {token, role, updatedAt}
- 通知は notifications コレクションに溜まる。処理後 sent:true に更新
"""

import os
import json
import sys
import traceback
from datetime import datetime, timezone, timedelta, date

import firebase_admin
from firebase_admin import credentials, firestore, messaging


JST = timezone(timedelta(hours=9))


def init_firebase():
    creds_raw = os.environ.get("FIREBASE_CREDENTIALS")
    if not creds_raw:
        print("ERROR: FIREBASE_CREDENTIALS env not set", file=sys.stderr)
        sys.exit(1)
    creds_dict = json.loads(creds_raw)
    cred = credentials.Certificate(creds_dict)
    firebase_admin.initialize_app(cred)
    return firestore.client()


def find_user_by_role(users, role):
    for u in users:
        if u.get("role") == role:
            return u
    return None


def get_token_for_user(tokens, user):
    if not user:
        return None
    t = tokens.get(user["id"])
    if not t:
        return None
    return t.get("token")


def send_fcm(token, title, body, data=None):
    msg = messaging.Message(
        token=token,
        notification=messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
        # iOS (APNs) 向け: sound=default でデフォルトサウンド
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    sound="default",
                    badge=1,
                ),
            ),
        ),
        # Web Push 向け: バイブ・アイコン指定
        webpush=messaging.WebpushConfig(
            notification=messaging.WebpushNotification(
                title=title,
                body=body,
                icon="/dinner-app/icons/icon-192.png",
                badge="/dinner-app/icons/icon-192.png",
                vibrate=[200, 100, 200],
                require_interaction=False,
            ),
            fcm_options=messaging.WebpushFCMOptions(
                link="https://invalley1976-cmyk.github.io/dinner-app/",
            ),
        ),
    )
    try:
        resp = messaging.send(msg)
        print(f"SENT: {resp} | {title} / {body[:50]}")
        return True
    except Exception as e:
        print(f"SEND_FAILED: {e}", file=sys.stderr)
        return False


def run_daily_check(db, state):
    """21:00 JST に翌日空白なら メイ に通知。重複防止のため meta/lastDailyCheck を使う"""
    now_jst = datetime.now(JST)
    today_jst = now_jst.date()

    # 21:00 JST 付近の起動だけ対象 (21:00 ~ 21:29)
    if now_jst.hour != 21:
        return
    if now_jst.minute >= 30:
        return

    # 重複防止: 今日すでに送っていればスキップ
    meta_ref = db.collection("meta").document("lastDailyCheck")
    meta = meta_ref.get()
    if meta.exists:
        last_date = meta.to_dict().get("date")
        if last_date == today_jst.isoformat():
            print("DAILY_CHECK: already ran today, skip")
            return

    # 翌日を計算
    tomorrow_jst = today_jst + timedelta(days=1)
    tomorrow_key = tomorrow_jst.isoformat()

    schedule = state.get("schedule") or {}
    users = state.get("users") or []
    tokens = state.get("tokens") or {}

    if tomorrow_key in schedule and schedule[tomorrow_key].get("answer") in ("yes", "no"):
        print(f"DAILY_CHECK: tomorrow {tomorrow_key} already filled, skip")
    else:
        # メイに通知
        mei = find_user_by_role(users, "child")
        token = get_token_for_user(tokens, mei)
        if token:
            ok = send_fcm(
                token,
                title="晩ごはんチェック",
                body="明日の晩ごはんどうする～？",
                data={"type": "daily_reminder", "date": tomorrow_key},
            )
            if ok:
                print("DAILY_CHECK: notified メイ")
        else:
            print("DAILY_CHECK: no token for メイ, skip")

    # 実行済みマーク
    meta_ref.set({"date": today_jst.isoformat(), "ranAt": datetime.now(timezone.utc)})


def run_queued_notifications(db, state):
    """notifications コレクションの未送信通知を処理"""
    users = state.get("users") or []
    tokens = state.get("tokens") or {}

    # 未送信のみ取得
    pending = (
        db.collection("notifications").where("sent", "==", False).limit(50).stream()
    )
    count = 0
    for doc in pending:
        data = doc.to_dict()
        target_role = data.get("targetRole")
        title = data.get("title") or "晩ごはんチェック"
        body = data.get("body") or ""

        # 対象ユーザー特定
        if target_role in ("child", "parent"):
            target_user = find_user_by_role(users, target_role)
            token = get_token_for_user(tokens, target_user)
        else:
            token = None

        if token:
            ok = send_fcm(token, title, body, data={"type": data.get("type", "msg")})
        else:
            print(f"NOTIF {doc.id}: no target token (role={target_role}), marking sent")
            ok = True  # トークンが無い場合は諦めてsent=trueにする(永遠に再送しない)

        doc.reference.update(
            {
                "sent": True,
                "sentAt": datetime.now(timezone.utc),
                "success": ok,
            }
        )
        count += 1
    print(f"QUEUED: processed {count} notifications")


def main():
    try:
        db = init_firebase()
        # state 読み込み
        state_ref = db.collection("app").document("state")
        state_snap = state_ref.get()
        state = state_snap.to_dict() if state_snap.exists else {}

        run_daily_check(db, state)
        run_queued_notifications(db, state)
    except Exception:
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
