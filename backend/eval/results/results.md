Questions: 16 in-corpus, 4 out-of-corpus. k = 4, MIN_RELEVANCE = 0.38.

| Configuration | Chunks | Index (s) | Hit@1 | Hit@4 | MRR | Refusal (out) | False refusal (in) | Retrieval mean / p95 (ms) |
|---|---|---|---|---|---|---|---|---|
| chroma | multilingual-MiniLM | chunk 300 | 27 | 3.096 | 0.81 | 0.94 | 0.86 | 100% | 0% | 24.91 / 31.64 |
| faiss | multilingual-MiniLM | chunk 300 | 27 | 1.794 | 0.81 | 0.94 | 0.86 | 100% | 0% | 16.37 / 20.0 |
| chroma | multilingual-MiniLM | chunk 500 | 18 | 2.737 | 0.62 | 0.94 | 0.76 | 75% | 6% | 48.37 / 97.25 |
| faiss | multilingual-MiniLM | chunk 500 | 18 | 2.795 | 0.62 | 0.94 | 0.76 | 75% | 6% | 46.63 / 79.31 |
| chroma | multilingual-MiniLM | chunk 800 | 10 | 1.243 | 0.62 | 1.00 | 0.79 | 75% | 6% | 19.47 / 23.57 |
| faiss | multilingual-MiniLM | chunk 800 | 10 | 0.909 | 0.62 | 1.00 | 0.79 | 75% | 6% | 21.43 / 29.05 |
| chroma | bge-small-en | chunk 800 | 10 | 1.9 | 0.44 | 0.81 | 0.57 | 0% | 0% | 24.06 / 32.39 |
