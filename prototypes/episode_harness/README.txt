具身 agent harness · 协议原型

目标：每条任务创建独立 gpt-6.1-sol 会话，只提供任务目标、第一人称 RGB、技能说明和最多 8 次自己的动作。模型只返回 JSON；受信任执行器校验后执行原生机器人技能。

现有实现：
- harness.py：白名单构造输入；动作字段/范围、任务归属、观测编号校验；待执行动作绑定；任务关闭与历史清理。
- agent_instructions.txt：任务级指令。
- test_harness.py：协议边界测试。

尚未接入：模型传输、权限受限的运行时、node43 RGB 传感器、物理技能执行器、独立任务验收器。没有进行实际机器人 rollout。

安全边界：
普通子 agent 的 fork_turns=none 只能隔离历史，不能隔离工具和文件。正式运行必须配置无宿主工具的独立模型通道；不能把含完整文件/网络工具的普通子 agent 当作已经隔离的具身 agent。
request() 返回工具为空的传输意图，不自行强制宿主权限。模型传输层必须执行这项约束，并审计实际请求。禁止传递场景对象字典、深度、地图、世界坐标和其他任务日志。
validation_schema 是本地通用 JSON Schema（包含顶层 oneOf），不能直接视作任意模型供应商的 strict response schema。供应商适配器需要转换为其支持的 schema 子集，仍需调用 accept() 做最终校验。
PNG 当前只检查格式签名和大小；真实传感器接入还需解码检查尺寸、RGB 通道及去除元数据。测试图像仅为协议占位数据，不代表视觉模型验收。

运行生命周期：
1. 受信任监督器加载任务并在私有通道验证可行性。
2. 创建 Episode 与新的模型会话。
3. 只发送 request(rgb) 构造的输入；accept(raw_json) 验证模型输出。
4. 执行器执行该命令，返回后调用 executed(command)，采集新图像。
5. finish、预算、异常或超时后独立判定，finally 调用 close() 并销毁模型会话。
6. 下一任务新建 Episode；不得注入前一任务归档、监督器推理或隐藏验收信息。

初始技能：move_forward 0.05–0.50m，turn -90–90deg，wait 0.1–1s，finish。
决策按技能完成触发；30fps 为传感器记录频率。以任务结束或预算终止，不强制 10 秒。
测试：python3 -m unittest discover -s isaac-rigidtrack-20261023/embodied-agent-harness -v
