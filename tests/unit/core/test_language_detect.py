from __future__ import annotations

import pytest

from quill.core import language_detect as ld

SAMPLES = {
    "HTML": """<!DOCTYPE html>
<html>
  <head><title>Hi</title></head>
  <body><div class="x"><p>Hello <span>world</span></p></div></body>
</html>
""",
    "Markdown": """# Title

Some **bold** text and a [link](https://example.com).

- one
- two

```python
print("fenced")
```
""",
    "Python": """#!/usr/bin/env python
import sys


class Greeter:
    def greet(self, name):
        if name:
            print(f"Hello {name}")
        return None
""",
    "JavaScript": """import { thing } from './mod';

const add = (a, b) => a + b;
function main() {
  const x = add(1, 2);
  console.log(x);
}
""",
    "TypeScript": """interface User {
  name: string;
  age: number;
}

const greet = (u: User): string => `Hi ${u.name}`;
export function run(): void {
  const u = { name: 'a', age: 1 } as User;
}
""",
    "CSS": """.container {
  display: flex;
  color: #333;
}
@media (max-width: 600px) {
  .container { flex-direction: column; }
}
""",
    "JSON": """{
  "name": "quill",
  "version": "0.7.0",
  "items": [1, 2, 3],
  "nested": {"ok": true}
}
""",
    "Go": """package main

import "fmt"

func main() {
    msg := "hi"
    fmt.Println(msg)
}
""",
    "Rust": """fn main() {
    let mut total = 0;
    for i in 0..10 {
        total += i;
    }
    println!("{}", total);
}
""",
    "Shell": """#!/bin/bash
for f in *.txt; do
  if [ -f "$f" ]; then
    echo "$f"
  fi
done
""",
    "SQL": """SELECT id, name
FROM users
WHERE age > 21
ORDER BY name;
""",
    "C": """#include <stdio.h>

int main(void) {
    int total = 0;
    for (int i = 0; i < 10; i++) {
        total += i;
    }
    printf("%d\\n", total);
    return 0;
}
""",
    "C#": """using System;

namespace Demo
{
    public class Program
    {
        public static void Main(string[] args)
        {
            var msg = "hi";
            Console.WriteLine(msg);
        }
    }
}
""",
    "PHP": """<?php
namespace App;

class Greeter {
    public function greet($name) {
        echo "Hello " . $name;
        return $this->format($name);
    }
}
""",
}


@pytest.mark.parametrize("expected,text", list(SAMPLES.items()))
def test_detects_representative_snippets(expected: str, text: str) -> None:
    result = ld.detect_language(text)
    assert result.language == expected, f"got {result.language} ({result.confidence:.2f})"
    assert result.is_confident


def test_plain_prose_is_not_detected() -> None:
    prose = (
        "The quick brown fox jumps over the lazy dog. This is an ordinary "
        "paragraph of English text with no code in it whatsoever.\n"
        "It continues for a couple of sentences so length is not the issue."
    )
    result = ld.detect_language(prose)
    assert result.language is None
    assert not result.is_confident


def test_ascii_braille_brf_is_not_mistaken_for_code() -> None:
    # Pasted ASCII-braille (BRF) must NOT false-positive as a programming
    # language; braille is a format with its own Braille Mode, not a profile.
    brf = (
        ",! QUICK ,BROWN ,FOX JUMPS OV} ! LAZY ,DOG4\n"
        "#A4 ,! FIRST C8APT}3 ,A ,TALE\n"
        ",?IS IS A L9E OF GRADE #B ,BRAILLE4\n"
    )
    assert ld.detect_language(brf).language is None


def test_short_or_empty_text_is_not_detected() -> None:
    assert ld.detect_language("").language is None
    assert ld.detect_language("hello").language is None
    assert ld.detect_language("key: value").language is None  # ambiguous YAML-ish


def test_bias_breaks_a_tie_toward_session_language() -> None:
    # A snippet with a faint signal; bias should help it cross the line or pick.
    ambiguous = "name: example\nversion: 1\nitems:\n  - a\n  - b\n"
    base = ld.detect_language(ambiguous)
    biased = ld.detect_language(ambiguous, bias={"YAML": 5.0})
    # Bias must never *lower* YAML's standing.
    assert biased.scores.get("YAML", 0) >= base.scores.get("YAML", 0)


def test_should_switch_hysteresis() -> None:
    strong = ld.detect_language(SAMPLES["Python"])
    # First-time set (no current / plain) is allowed.
    assert ld.should_switch(None, strong) is True
    assert ld.should_switch("Plain text", strong) is True
    # Same language: no churn.
    assert ld.should_switch("Python", strong) is False
    # Not confident: never switch.
    assert ld.should_switch("Plain text", ld.detect_language("hello")) is False


def test_result_scores_are_normalised() -> None:
    result = ld.detect_language(SAMPLES["HTML"])
    assert result.language == "HTML"
    assert 0.0 < result.scores["HTML"] <= 1.0
    assert abs(sum(result.scores.values()) - 1.0) < 1e-6 or result.scores == {}
