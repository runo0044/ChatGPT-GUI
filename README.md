# ChatGPT-GUI
ChatGPTを用いたチャットボットのWebGUIです。
## 導入
必要なライブラリが入ったPython環境があればそのまま動作します。requirements.txtを参照してください。
仮想環境を用いる場合はリポジトリがpycharmプロジェクトとして読めるはずなので、cloneしたあとにインポートしてください。

## 環境設定
.envファイルを作成してください。

OpenAIのAPI KEYを

OPENAI_API_KEY="API_KEY"

の形式で.envファイルに書いてください。

## ChatBot
ボタンを押すだけです。

submit（投稿）、regenerate（AIの返答を再生成）、rollback（一つ前の自分の投稿まで削除）、clear（履歴全消去）、save（履歴を保存）

converterを有効にすると、応答文をconverterの設定で変換して表示します。デフォルトでは仕事のできない猫変換promptが設定されています。

## Q & A
ボタンを押すだけです。
submit（質問）、save（内容を保存）

## todo
会話履歴のLoad機能

system messageを保存・読み込む機能

## 未定
URLから情報を取得する機能
ファイルから情報を取得しQ&Aする機能
他社APIへの対応
