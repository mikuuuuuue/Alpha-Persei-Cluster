
import os, zlib, sys
def ratio(p):
    n = os.path.getsize(p)
    with open(p,'rb') as f: data = f.read()
    c = zlib.compress(data, 6)
    return n, len(c), (len(c)/n*100 if n else 0)

targets = [
  r"v5_server/static_resources/pc/assethash_307_229_3807d27e1a6e26853f1fccfa8b7681d0.bytes",
  r"v5_server/account.db",
  r"v5_server/lua_proto_messages.json",
  r"Alpha-Persei-Captures/2026-09-27_补抓2/AetherGazer_Bili 2026-09-27 09-25-11.mp4",
]
for t in targets:
    if os.path.exists(t):
        n,c,pct = ratio(t)
        print(f"{os.path.basename(t)[:50]:52s} raw={n/1048576:8.2f}MB  zlib={c/1048576:8.2f}MB  {pct:5.1f}%")
    else:
        print("MISSING", t)
