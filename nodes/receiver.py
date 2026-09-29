#!/usr/bin/env python3
"""Subscribe to timestamped messages and report one-way latency statistics."""

import argparse
import math
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


def percentile(values: list[float], fraction: float) -> float:
    """Return a nearest-rank percentile from a non-empty list."""
    ordered = sorted(values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


class LatencyReceiver(Node):
    def __init__(self, topic: str, report_every: int) -> None:
        super().__init__("latency_receiver")
        self.report_every = report_every
        self.received = 0
        self.latencies_ms: list[float] = []
        self.subscription = self.create_subscription(String, topic, self.on_message, 100)
        self.get_logger().info(f"Listening on {topic}; reporting every {report_every} samples.")

    def on_message(self, message: String) -> None:
        try:
            sequence_text, sent_ns_text = message.data.split(",", maxsplit=1)
            sequence = int(sequence_text)
            sent_ns = int(sent_ns_text)
        except (ValueError, TypeError):
            self.get_logger().warning("Ignoring malformed message")
            return

        latency_ms = (time.monotonic_ns() - sent_ns) / 1_000_000
        self.latencies_ms.append(latency_ms)
        self.received += 1
        if len(self.latencies_ms) >= self.report_every:
            self.report()
            self.latencies_ms.clear()

    def report(self) -> None:
        if not self.latencies_ms:
            return
        values = self.latencies_ms
        mean = sum(values) / len(values)
        self.get_logger().info(
            f"samples={len(values)} total_received={self.received} "
            f"min={min(values):.3f} ms mean={mean:.3f} ms "
            f"p50={percentile(values, 0.50):.3f} ms "
            f"p95={percentile(values, 0.95):.3f} ms "
            f"p99={percentile(values, 0.99):.3f} ms max={max(values):.3f} ms"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", default="/latency_test")
    parser.add_argument("--report-every", type=int, default=100)
    args = parser.parse_args()
    if args.report_every <= 0:
        parser.error("--report-every must be greater than zero")
    return args


def main() -> None:
    args = parse_args()
    rclpy.init()
    node = LatencyReceiver(args.topic, args.report_every)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.report()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()

