Questions: 16 in-corpus, 4 out-of-corpus. k = 4, MIN_RELEVANCE = 0.38.

| Configuration | Chunks | Index (s) | Hit@1 | Hit@4 | MRR | Refusal (out) | False refusal (in) | Retrieval mean / p95 (ms) |
|---|---|---|---|---|---|---|---|---|
| chroma | multilingual-MiniLM | chunk 300 | 27 | 2.366 | 0.81 | 0.94 | 0.86 | 100% | 0% | 18.23 / 20.88 |
| faiss | multilingual-MiniLM | chunk 300 | 27 | 2.091 | 0.81 | 0.94 | 0.86 | 100% | 0% | 19.25 / 24.19 |
| chroma | multilingual-MiniLM | chunk 500 | 18 | 1.772 | 0.62 | 0.94 | 0.76 | 75% | 6% | 19.14 / 22.36 |
| faiss | multilingual-MiniLM | chunk 500 | 18 | 1.702 | 0.62 | 0.94 | 0.76 | 75% | 6% | 15.01 / 17.08 |
| chroma | multilingual-MiniLM | chunk 800 | 10 | 1.045 | 0.62 | 1.00 | 0.79 | 75% | 6% | 22.66 / 27.12 |
| faiss | multilingual-MiniLM | chunk 800 | 10 | 0.922 | 0.62 | 1.00 | 0.79 | 75% | 6% | 15.63 / 18.17 |
| chroma | bge-small-en | chunk 800 | 10 | 1.753 | 0.44 | 0.81 | 0.57 | 0% | 0% | 21.76 / 27.34 |
