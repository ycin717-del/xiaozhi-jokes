# xiaozhi-jokes

小智（ESP32-S3）用的台灣兒童笑話庫。自編韌體的 `self.jokes.get_joke` 工具每 6 小時從這裡下載：

https://raw.githubusercontent.com/ycin717-del/xiaozhi-jokes/main/jokes.json

## 格式
```json
{"version": "2026-11-18", "jokes": [{"id": 1, "q": "題目", "a": "答案", "age": "小|大|都", "type": "諧音"}]}
```
- `id`：唯一、不可重複使用（裝置用它記住講過哪些）
- `age`：小＝6 歲、大＝10 歲、都＝都適合
- 新增笑話：往 `jokes` 陣列尾端加，`id` 接著編號，並更新 `version`
