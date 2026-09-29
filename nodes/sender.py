#!/usr/bin/env python3
"""Publish sequence numbers and monotonic timestamps for latency measurement."""

import argparse
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class LatencySender(Node):
    def __init__(self, rate_hz: float, count: int, topic: str) -> None:
        super().__init__("latency_sender")
        self.publisher = self.create_publisher(String, topic, 100)
        self.rate_hz = rate_hz
        self.count = count
        self.sequence = 0
        self.timer = None

    def publish_one(self) -> None:
        message = String()
        message.data = f"{self.sequence},{time.monotonic_ns()}"
        self.publisher.publish(message)
        self.sequence += 1
        if self.count > 0 and self.sequence >= self.count:
            self.get_logger().info(f"Sent {self.sequence} messages; shutting down.")
            self.timer.cancel()
            rclpy.shutdown()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rate", type=float, default=100.0, help="publish rate in Hz")
    parser.add_argument(
        "--count", type=int, default=1000, help="messages to send; 0 sends forever"
    )
    parser.add_argument("--topic", default="/latency_test")
    parser.add_argument(
        "--discovery-timeout", type=float, default=30.0,
        help="seconds to wait for a receiver; 0 skips the wait",
    )
    args = parser.parse_args()
    if args.rate <= 0:
        parser.error("--rate must be greater than zero")
    if args.count < 0:
        parser.error("--count must be zero or greater")
    return args


def main() -> None:
    args = parse_args()
    rclpy.init()
    node = LatencySender(args.rate, args.count, args.topic)
    deadline = time.monotonic() + args.discovery_timeout
    while args.discovery_timeout > 0 and node.publisher.get_subscription_count() == 0:
        if time.monotonic() >= deadline:
            node.get_logger().warning(
                "No receiver discovered before timeout; starting transmission anyway."
            )
            break
        time.sleep(0.1)

    node.get_logger().info(
        f"Publishing {args.topic} at {args.rate:g} Hz; receiver count="
        f"{node.publisher.get_subscription_count()}"
    )
    node.timer = node.create_timer(1.0 / args.rate, node.publish_one)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            rclpy.shutdown()
        node.destroy_node()


if __name__ == "__main__":
    main()

