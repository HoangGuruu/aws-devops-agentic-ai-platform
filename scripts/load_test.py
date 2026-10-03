#!/usr/bin/env python3
"""Bounded traffic generator; errors are expected during the course fault drill."""
import argparse,time,urllib.request,urllib.error
p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:9080/productpage');p.add_argument('--seconds',type=int,default=240);a=p.parse_args()
if not 1 <= a.seconds <= 3600:p.error('seconds must be 1..3600')
end=time.monotonic()+a.seconds
counts={}
while time.monotonic()<end:
    try:
        with urllib.request.urlopen(a.url,timeout=5) as r:status=str(r.status)
    except urllib.error.HTTPError as e:status=str(e.code)
    except (OSError,TimeoutError):status='connection_error'
    counts[status]=counts.get(status,0)+1
    time.sleep(.2)
print(counts)
