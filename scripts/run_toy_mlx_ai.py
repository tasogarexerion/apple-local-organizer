#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim


DEFAULT_CORPUS = """\
Apple Intelligence を使うローカル常駐ツールを作っている。
Desktop と Downloads を監視し、スクリーンショットや PDF をすばやく把握したい。
オンデバイスで動く小さな自作 AI の感触を確かめたい。
整理候補、タグ、短い要約、次のアクションを手元で回せると気持ちがいい。
"""


@dataclass
class Vocabulary:
    stoi: dict[str, int]
    itos: list[str]

    def encode(self, text: str) -> list[int]:
        return [self.stoi[char] for char in text]

    def decode(self, tokens: list[int]) -> str:
        return "".join(self.itos[token] for token in tokens)


class BigramLanguageModel(nn.Module):
    def __init__(self, vocab_size: int) -> None:
        super().__init__()
        self.token_embedding_table = nn.Embedding(vocab_size, vocab_size)

    def __call__(self, x: mx.array) -> mx.array:
        return self.token_embedding_table(x)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a tiny MLX bigram language model on-device.")
    parser.add_argument("--file", help="Optional UTF-8 corpus file.")
    parser.add_argument("--steps", type=int, default=400, help="Training steps.")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--block-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--prompt", default="オン", help="Seed text for generation.")
    parser.add_argument("--tokens", type=int, default=120, help="Number of tokens to generate.")
    return parser.parse_args()


def load_corpus(path: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8")
    return DEFAULT_CORPUS


def build_vocab(text: str) -> Vocabulary:
    chars = sorted(set(text))
    return Vocabulary(
        stoi={char: index for index, char in enumerate(chars)},
        itos=chars,
    )


def make_batch(data: list[int], batch_size: int, block_size: int) -> tuple[mx.array, mx.array]:
    starts = mx.random.randint(0, len(data) - block_size - 1, shape=(batch_size,))
    x_rows = [data[int(start.item()): int(start.item()) + block_size] for start in starts]
    y_rows = [data[int(start.item()) + 1: int(start.item()) + block_size + 1] for start in starts]
    return mx.array(x_rows, dtype=mx.int32), mx.array(y_rows, dtype=mx.int32)


def loss_fn(model: BigramLanguageModel, inputs: mx.array, targets: mx.array, vocab_size: int) -> mx.array:
    logits = model(inputs)
    flat_logits = logits.reshape(-1, vocab_size)
    flat_targets = targets.reshape(-1)
    return mx.mean(nn.losses.cross_entropy(flat_logits, flat_targets))


def generate(
    model: BigramLanguageModel,
    vocab: Vocabulary,
    prompt: str,
    tokens: int,
) -> str:
    known_prompt = prompt if prompt else vocab.itos[0]
    encoded = vocab.encode("".join(char for char in known_prompt if char in vocab.stoi) or vocab.itos[0])
    context = mx.array([encoded], dtype=mx.int32)

    for _ in range(tokens):
        logits = model(context)
        next_logits = logits[:, -1, :]
        next_token = mx.random.categorical(next_logits)
        context = mx.concatenate([context, next_token.reshape(1, 1)], axis=1)

    return vocab.decode(context.tolist()[0])


def main() -> int:
    args = parse_args()
    corpus = load_corpus(args.file)
    vocab = build_vocab(corpus)
    data = vocab.encode(corpus)

    if len(data) <= args.block_size + 1:
        raise ValueError("Corpus is too small for the requested block size.")

    mx.random.seed(args.seed)
    model = BigramLanguageModel(len(vocab.itos))
    optimizer = optim.Adam(learning_rate=args.lr)
    loss_and_grad = nn.value_and_grad(model, lambda m, x, y: loss_fn(m, x, y, len(vocab.itos)))

    mx.eval(model.parameters(), optimizer.state)

    for step in range(1, args.steps + 1):
        inputs, targets = make_batch(data, args.batch_size, args.block_size)
        loss, grads = loss_and_grad(model, inputs, targets)
        optimizer.update(model, grads)
        mx.eval(loss, model.parameters(), optimizer.state)
        if step == 1 or step % max(1, args.steps // 5) == 0 or step == args.steps:
            print(f"step={step:04d} loss={float(loss.item()):.4f}")

    output = generate(model, vocab, args.prompt, args.tokens)
    print("\n--- generated ---")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
