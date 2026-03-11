# Local AI Playground

このリポジトリには、Apple Silicon 上で「自作の小さなオンデバイス AI」を触るための最短導線を入れています。

## 1. すぐ触る: 自作ミニモデル

`MLX` の上で、文字単位の tiny bigram model を学習してテキスト生成します。
モデルの規模は小さいですが、学習と生成の一往復を数十秒で触れます。

```bash
.venv-fm312/bin/python scripts/run_toy_mlx_ai.py
```

自前のテキストで試す場合:

```bash
.venv-fm312/bin/python scripts/run_toy_mlx_ai.py --file notes.txt --steps 600 --prompt "要" --tokens 160
```

## 2. もう少し実用寄り: ローカル LLM

`mlx-lm` を使って、MLX 形式のローカル LLM を Apple Silicon で実行します。
初回は Hugging Face からモデルを取得します。

```bash
./scripts/run_local_mlx_llm.sh "Apple Intelligence と MLX の違いを3点で説明して"
```

モデルを変える場合:

```bash
MODEL=mlx-community/Qwen2.5-1.5B-Instruct-4bit ./scripts/run_local_mlx_llm.sh "短く自己紹介して"
```

## 3. リリース文前に最低限見るポイント

- ローカルで本当に生成が返るか
- レスポンス速度の感触
- 日本語の崩れ方
- 小さいモデルと Apple Foundation Models の役割分担

## 4. 使い分け

- `Foundation Models`
  Apple Intelligence のオンデバイスモデルを高レベル API で使う
- `MLX / mlx-lm`
  自前でモデルを触る、学習する、推論をいじる

## 5. 今のこの repo との相性

- `run_toy_mlx_ai.py`
  自作 AI を最短で触る入口
- `run_local_mlx_llm.sh`
  将来的に要約や分類の代替ローカルパイプラインを検証する入口
