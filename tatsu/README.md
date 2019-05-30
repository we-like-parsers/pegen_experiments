Add a timing test with TatSu
----------------------------

To run:
```
pip3 install tatsu
tatsu grammar.ebnf --whitespace ' ' >parse.py
python3 timings.py ../testdata/medium.txt
```
Timing output:
```
100 lines in 3.406 secs
29 lines/sec
Memory stats:
  rss         :        122 MiB
  vms         :       4315 MiB
  maxrss      :        122 MiB
```
Concluding, TatSu's Python parser is much slower than my toy parser
(29 lines/sec vs. 600 line/sec, i.e. ~35x).  Then again, the native
parser is 25x faster than my toy parse.
