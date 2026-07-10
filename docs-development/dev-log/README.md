# 开发日志规范 (Dev Log Convention)

本目录下每一篇日志对应一次开发会话，文件名格式为 `YYYY-MM-DD-<序号>.md`（同一天有多次会话时用序号区分，如 `2026-07-10-01.md`）。

## 模板 (Template)

每篇日志包含以下字段：

```markdown
# 开发日志 YYYY-MM-DD-NN

## 基本信息 (Meta)
- 日期 (Date):
- 参与者 (Participants):
- 所处阶段 (Phase): 对应 engineering-plan.md 中的阶段编号

## 本次目标 (Goal of This Session)
简述本次会话打算完成什么。

## 完成的工作 (What Was Done)
- 逐条列出实际完成的原子任务，附对应 engineering-plan.md 中的任务ID
- 涉及的关键决策和理由

## 遇到的问题与解决方案 (Issues & Resolutions)
- 问题描述
- 排查过程（简述即可，细节可放 internal-notes/）
- 最终解决方案 / 或标注为待解决

## 未完成 / 下一步 (Unfinished / Next Steps)
- 列出本次没做完、留给下次的事情
- 对应 engineering-plan.md 中状态仍为“进行中”或“未开始”的任务ID

## 相关提交 (Related Commits)
- commit hash + 简述

## 需要用户确认的事项 (Needs User Confirmation)
- 如果有需要用户决策/确认才能继续的事项，列在这里
```

## 为什么要写这个 (Why This Matters)

本项目的硬性要求：**如果开发者某天突然中断，另一个人接手，应该能零压力地接着做**。日志 + `engineering-plan.md` 配合使用：

- `engineering-plan.md` 告诉你**现在的状态**（哪些任务完成了、哪些没完成）。
- 开发日志告诉你**为什么会是这个状态**（做了什么决策、踩了什么坑、为什么这么设计）。
