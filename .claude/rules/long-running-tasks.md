## 長時間タスクの待ち方

ScheduleWakeupで長時間タスクをポーリングしてはいけない。指定した遅延秒数が守られず、大量のポーリングが発生してコンテキストを浪費する。

代わりに、SSH先でブロッキングコマンドを実行し、Bashツールのフォアグラウンドで最大10分（timeout: 600000ms）待つことを繰り返す。

### パターン

```bash
# SSH先で完了条件を待つループ（最大10分でタイムアウト）
ssh pakari "for i in \$(seq 1 20); do
    grep -q '完了キーワード' /path/to/log 2>/dev/null && break
    sleep 30
done
grep -q '完了キーワード' /path/to/log 2>/dev/null && echo 'COMPLETED' || echo 'STILL_RUNNING'"
```

- タイムアウトした場合は結果を確認し、未完了なら同じコマンドを再度実行する
- `run_in_background: true` は使わない（フォアグラウンドで待つことで、完了後すぐに次の作業に進める）
- ScheduleWakeupは使わない
