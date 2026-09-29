# ROS 2 Humble 双容器通信与延迟测试

使用两个独立的 Docker 容器运行 ROS 2 节点：发送端按设定频率发布带序号和单调时钟时间戳的消息，接收端计算单向延迟并按批输出统计值。

## 环境与设计

- 基础镜像：官方 `ros:humble-ros-base`，基于 Ubuntu 22.04。
- 两个容器复用同一个轻量基础镜像，不安装额外系统依赖。
- `nodes/sender.py` 和 `nodes/receiver.py` 以只读 bind mount 分别挂入发送端和接收端容器，改动脚本无需重建镜像。
- 使用 ROS 2 默认 DDS 中间件和 Docker bridge 网络；两个服务设置相同的 `ROS_DOMAIN_ID`。
- 消息类型为 `std_msgs/msg/String`，不需要自定义消息包或构建工作空间。

## 启动测试

需要已安装 Docker Engine 和 Docker Compose v2。在仓库根目录运行：

```bash
docker compose up --build
```

Compose 会启动接收端，再启动发送端。发送端等待发现接收端后，以 100 Hz 发布 1000 条消息。接收端每收到 100 条消息，在日志中报告样本数、最小值、平均值、p50、p95、p99 和最大值（单位毫秒）。默认测试约持续 10 秒；查看日志后按 `Ctrl+C` 停止并清理容器：

```bash
docker compose down
```

## 调整测试参数

可在 `compose.yaml` 中修改服务的命令参数。例如将发送频率改为 500 Hz、总数改为 5000：

```yaml
command: ["python3", "/ros_nodes/sender.py", "--rate", "500", "--count", "5000"]
```

接收端的 `--report-every` 控制每批统计的样本数。也可只重启发送服务，直接覆盖启动命令：

```bash
docker compose run --rm sender --rate 50 --count 500
```

命令行参数还支持 `--count 0` 持续发送、`--topic /another_topic` 修改话题，以及发送端的 `--discovery-timeout 0` 跳过订阅发现等待。单独运行节点时，需让两端使用相同的话题与 `ROS_DOMAIN_ID`。

## 延迟结果说明

延迟按接收回调时的 `time.monotonic_ns()` 与发送时写入消息的单调时钟时间作差，因此本方案面向同一台 Linux 主机上的两个 Docker 容器；容器共享主机内核时钟。统计值包含 DDS 传输与两端进程调度、回调处理的影响，适合比较当前环境下的通信延迟，不等同于纯网络链路延迟。若扩展到不同主机，需先配置可靠的时钟同步（如 PTP），再采用适合跨主机的时间戳方案。

如 Docker 主机防火墙或网络策略阻止 DDS 发现/数据流量，节点可能无法互相发现；请允许该 bridge 网络上的 DDS UDP 多播与数据流量。
