# Shark of the Wire II Write-up

## Challenge Summary

We are given a single file:

```text
chall.pcap
```

The prompt says the transmission was split into multiple fragments before being sent, so the main task is to identify all meaningful pieces, reconstruct the original message, and recover the flag.

## Initial Recon

The first useful observation is that the workspace only contains a packet capture:

```text
chall.pcap
```

A quick `strings` pass already hints that readable data exists inside the capture:

```text
VEFDSFlP
TntmcjRnb
TNudDNkXz
FzX24wXzR
1bn0=
```

Those fragments look very close to Base64, but `strings` alone is not reliable enough for a final answer because it may blend adjacent bytes from packet boundaries. The correct approach is to extract the actual TCP payloads from the PCAP.

## Understanding the Capture Format

This PCAP is not Ethernet-based. Its global header reports `network = 0`, which means the packets use the BSD loopback / `DLT_NULL` format.

That matters because every packet starts with a 4-byte address-family field before the IP header:

- `2` means IPv4
- `30` means IPv6

So if we parse packets manually, we cannot assume the IP header starts at offset `0`. It starts at offset `4`.

During parsing, the capture contains:

- `60` packets total
- `50` IPv4 loopback packets
- `10` IPv6 loopback packets

The IPv6 packets are noise for this challenge. The useful data is in the IPv4 TCP traffic to port `4444` on `127.0.0.1`.

## Extracting the Real Payloads

Because `tshark` was not available in the environment, the payloads were extracted directly with Python.

### Extraction Script

```python
import struct
from pathlib import Path

p = Path("chall.pcap").read_bytes()
off = 24
pkt_num = 0

while off < len(p):
    ts_sec, ts_usec, incl_len, orig_len = struct.unpack_from("<IIII", p, off)
    off += 16
    pkt = p[off:off + incl_len]
    off += incl_len
    pkt_num += 1

    family = struct.unpack_from("<I", pkt, 0)[0]
    if family != 2:
        continue

    ip = pkt[4:]
    if ip[9] != 6:
        continue

    ihl = (ip[0] & 0x0F) * 4
    tcp = ip[ihl:]

    src_port, dst_port, seq, ack, off_flags = struct.unpack_from("!HHIIH", tcp, 0)
    data_offset = ((off_flags >> 12) & 0xF) * 4
    flags = off_flags & 0x1FF
    payload = tcp[data_offset:]

    if payload:
        print(pkt_num, src_port, "->", dst_port, hex(flags), payload)
```

### Output

```text
7 59463 -> 4444 0x18 b'VEFDSFlP\n'
19 59465 -> 4444 0x18 b'TntmcjRnb\n'
31 59467 -> 4444 0x18 b'TNudDNkXz\n'
43 59469 -> 4444 0x18 b'FzX24wXzR\n'
55 59471 -> 4444 0x18 b'1bn0=\n'
```

Important observations:

- Only `5` packets carry application data.
- Every payload goes to destination port `4444`.
- Each fragment is sent in its own short TCP connection.
- The payloads are plain ASCII and end with a newline.

## Reconstructing the Transmission

Remove the trailing newlines and concatenate the fragments in packet order:

```text
VEFDSFlP
TntmcjRnb
TNudDNkXz
FzX24wXzR
1bn0=
```

Combined:

```text
VEFDSFlPTntmcjRnbTNudDNkXzFzX24wXzR1bn0=
```

This is valid Base64.

## Decoding the Reassembled Data

Decoding the reconstructed string:

```python
import base64

s = "VEFDSFlPTntmcjRnbTNudDNkXzFzX24wXzR1bn0="
print(base64.b64decode(s).decode())
```

Output:

```text
TACHYON{fr4gm3nt3d_1s_n0_4un}
```

## Why This Works

The trick in this challenge is that the sender did not transmit the message as one continuous stream. Instead, the Base64 text was broken into five separate fragments and sent across five different short-lived TCP connections.

If you only inspect a single TCP stream, you only get one chunk and the result looks incomplete. The correct solution is to:

1. Find all payload-carrying packets.
2. Notice they are sequential fragments of printable text.
3. Join them in chronological / packet order.
4. Decode the resulting Base64 string.

## Final Flag

```text
TACHYON{fr4gm3nt3d_1s_n0_4un}
```
