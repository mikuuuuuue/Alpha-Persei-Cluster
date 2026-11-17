"""Focused checks for TCP stream reconstruction and source preservation."""
import hashlib
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "v5_server"))

import rebuild_capture_archive
from transport import pack_down


class CaptureRebuildTests(unittest.TestCase):
    def _packets(self):
        first = pack_down(12009, b"abc", index=1, server_idx=2)
        second = pack_down(12009, b"def", index=2, server_idx=3)
        return [
            self._packet(1, 100, first[:2]),
            self._packet(2, 102, first[2:]),
            self._packet(3, 102 + len(first) - 2, second),
        ]

    @staticmethod
    def _packet(number, seq, payload, syn=False, reset=False):
        return dict(number=number, seq=seq, payload=payload, time=float(number),
                    syn=syn, reset=reset)

    def test_out_of_order_retransmission_and_overlap_are_accepted(self):
        packets = self._packets()
        packets[0]["syn"] = True
        packets[0]["seq"] -= 1
        packets = [packets[2], packets[1], packets[0], dict(packets[1], number=4, time=4.0)]
        frames, audit = rebuild_capture_archive._reassemble(packets, "down")
        self.assertEqual([row["cmd"] for row in frames], [12009, 12009])
        self.assertEqual([row["payload_hex"] for row in frames], ["616263", "646566"])
        self.assertEqual(audit["retransmitted_bytes"], len(packets[1]["payload"]))

    def test_gap_is_rejected(self):
        packets = self._packets()
        packets[0]["syn"] = True
        packets[0]["seq"] -= 1
        packets[2]["seq"] += 1
        with self.assertRaisesRegex(ValueError, "缺口"):
            rebuild_capture_archive._reassemble(packets, "down")

    def test_overlap_with_different_bytes_is_rejected(self):
        packets = self._packets()
        packets[0]["syn"] = True
        packets[0]["seq"] -= 1
        overlap = bytearray(packets[1]["payload"])
        overlap[0] ^= 0xFF
        packets.append(self._packet(4, packets[1]["seq"], bytes(overlap)))
        with self.assertRaisesRegex(ValueError, "重叠字节冲突"):
            rebuild_capture_archive._reassemble(packets, "down")

    def test_original_capture_hash_is_unchanged(self):
        source = ROOT / "1116.pcapng"
        if not source.is_file():
            self.skipTest("1116.pcapng 不在当前工作区")
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        self.assertEqual(before,
                         "d42e78d4ef24f720d7836d52d71c1affa9eb437b2c96d75ede55420b9fef41ad")
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
