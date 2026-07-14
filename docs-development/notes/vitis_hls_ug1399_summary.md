# Vitis HLS User Guide (UG1399) 重点摘要

> 来源：https://docs.amd.com/r/en-US/ug1399-vitis-hls
> 文档 ID：UG1399 | 版本：2026.1 English | 发布日期：2026-06-23
> 提取：2026-07-11，用 browser-use MCP 抓取 JS 渲染页

---

## 一、HLS 基本流程（Agent 核心知识）

HLS 组件开发流程（agent 需要自动化的部分）：

1. **架构算法**：基于设计原则编写 C/C++ 函数
2. **C-Simulation (csim)**：用 C/C++ testbench 验证功能正确性
3. **C-Synthesis (csynth)**：用 `v++` 编译器将 C/C++ 生成 RTL
4. **C/RTL Co-Simulation (cosim)**：用 C/C++ testbench 验证生成的 RTL
5. **Package**：审查综合报告和实现时序报告
6. **迭代**：重复上述步骤直到达到性能目标

> **对 agent 的意义**：赛题要求 agent 调用 csim/cosim/synth 并解析报告。这 3 个步骤是 agent 的核心工具。

---

## 二、支持的操作系统与编译器

- 默认编译器：**Clang16**，支持大部分 C++17 特性
- 支持 OS：Ubuntu 22.04/24.04、RHEL 8/9/10、SUSE 15、Windows 10/11 等
- 许可证：需要 Vitis HLS License（从 https://www.xilinx.com/getlicense 获取）

---

## 三、关键概念（Agent 需要理解的设计原则）

### 1. 硬件接口 (Hardware Interfaces)
- 顶层函数参数被综合成接口和端口
- `v++` 编译器自动定义接口协议（行业标准协议）
- 默认接口因目标流程不同而异（Vivado IP vs Vitis Kernel）
- 可用 **INTERFACE pragma** 覆盖默认接口

### 2. 执行控制 (Block-Level Control)
- HLS 组件的执行模式由 block-level control protocol 指定
- 可以有 start/stop 控制信号，也可以纯数据驱动
- 详见 "Execution Modes of HLS Designs"

### 3. 任务级并行 (Task-Level Parallelism, TLP)
- 两种方式实现：
  - **DATAFLOW pragma**：自动推断函数间流水线
  - **hls::task**：显式创建并行任务

### 4. 存储架构 (Memory Architecture)
- C++ 数组在硬件中实现为存储器或寄存器
- 全局存储（DDR/HBM）访问延迟高，本地存储快
- 不能动态分配内存（无法综合）
- 存储访问优化：burst access / coalescing（合并多次访问为一次宽访问）

### 5. 微观优化 (Micro-Level Optimization)
- **PIPELINE**：流水线化循环/函数
- **UNROLL**：展开循环
- **ARRAY_PARTITION**：分割数组
- **PERFORMANCE pragma**：定义顶层性能目标，工具自动推断底层 pragma

---

## 四、代码重构示例

从 CPU C++ 代码重构为 HLS 代码的关键点：
- 用固定大小数组替代 `std::vector`（不能动态分配）
- 用 `hls::stream` FIFO 替代函数间数据传递
- 添加适当的 pragma（PIPELINE、UNROLL、DATAFLOW、ARRAY_PARTITION）
- 考虑接口协议（AXI-Stream、AXI-MM、AXI-Lite 等）

---

## 五、重要子页面索引（待深入阅读）

以下页面是 UG1399 的子章节，按对 Track A 的重要性排序：

| 优先级 | 页面 | 内容 |
|---|---|---|
| ★★★ | Running C Simulation | csim 命令行、报告格式、错误信息 |
| ★★★ | Running C Synthesis | csynth 命令行、综合报告（II/latency/资源） |
| ★★★ | Running C/RTL Co-Simulation | cosim 命令行、协议错误、死锁诊断 |
| ★★★ | Design Principles | HLS 编码设计原则 |
| ★★☆ | Execution Modes of HLS Designs | ap_ctrl、start/stop/done 协议 |
| ★★☆ | Interfaces for Vivado IP Flow | 接口协议选择 |
| ★★☆ | Loops Primer | 循环优化基础 |
| ★★☆ | Abstract Parallel Programming Model for HLS | hls::task、DATAFLOW |
| ★☆☆ | Navigating Content by Design Process | 文档导航 |
| ★☆☆ | Tutorials and Examples | 官方示例 |

> 这些子页面都是 JS 渲染的，需要用 browser-use MCP 逐个抓取。当前先记录索引，需要时再深入。

---

## 六、与 AMD 案例文章的关联

AMD SHA-256 案例文章中提到的几个关键点与 UG1399 对应：
- **DATAFLOW 与 PIPELINE 冲突**：不能在同一层级同时使用 → UG1399 有明确文档
- **hls::stream FIFO**：函数间数据传递 → UG1399 "Abstract Parallel Programming Model"
- **综合报告解读**：latency/II/资源 → UG1399 "Running C Synthesis"
- **Co-Simulation 验证**：→ UG1399 "Running C/RTL Co-Simulation"
