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

## 寶可夢圖鑑（pokedex/）

小智的 `self.pokemon.lookup` 工具會讀這裡的資料。全部是官方繁體中文名稱與說明，來源是 [PokeAPI](https://github.com/PokeAPI/pokeapi) 的資料表，用 `tools/gen_pokedex.py` 產生。

- `pokedex/index.txt`：每行「名字<TAB>種類/編號」，名字包含繁體、簡體和英文（小寫、去掉空白符號）
- `pokedex/p/<全國圖鑑編號>.json`：寶可夢（屬性、特性、種族值、弱點、進化、圖鑑說明、升級招式）
- `pokedex/m/<編號>.json`：招式
- `pokedex/a/<編號>.json`：特性
- `pokedex/t/<編號>.json`：屬性相剋
- `pokedex/names.txt`：每行「編號<TAB>名字<TAB>屬性編號<TAB>圖片可見範圍 x,y,w,h<TAB>進化階段（>分隔階段、逗號分隔同階段）」，給小智的圖鑑翻頁用（範圍用 tools/add_sprite_boxes.py 產生，讓每隻寶可夢顯示一樣大）
- `pokedex/pinyin.txt`、`pokedex/pinyin_chars.txt`：讀音對照（只在小智內部用來比對語音辨識聽錯的同音字，例如「耿貴」→耿鬼，不會唸出來或顯示）

重新產生：下載 PokeAPI 的 `data/v2/csv` 後執行 `python tools/gen_pokedex.py <csv資料夾> pokedex`。
