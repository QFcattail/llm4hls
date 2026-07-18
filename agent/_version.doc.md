# agent/_version.py 说明文档

## 中文说明

### 用途
项目版本号的唯一真相来源（single source of truth）。TUI 仪表盘标题栏通过 `app.title` 显示它，让用户能分辨"跑的是哪个版本"（规范 §11.3 硬约束：带界面的子系统必须在界面显示版本号）。

### 关键内容
| 名称 | 类型 | 职责 |
|---|---|---|
| `__version__` | str | 语义化版本（SemVer，`MAJOR.MINOR.PATCH`）。bump 规则见 `docs-development/PROJECT-CONVENTIONS.md` §11.2：运行时行为变更至少 patch +1，新功能 minor +1，仅文档/注释可不 bump |

### 导出
- `__version__`（被 `tui/app.py` 以 `from agent._version import __version__ as APP_VERSION` 导入，带 ImportError 回退为 `"unknown"`）

### 依赖
- 内部依赖：无
- 外部依赖：无（纯常量模块）

---

## English

### Purpose
Single source of truth for the project version. The TUI dashboard title bar displays it via `app.title` so users can tell which build is running (conventions §11.3 hard rule: any subsystem with a UI must show its version).

### Key Contents
| Name | Type | Responsibility |
|---|---|---|
| `__version__` | str | Semantic version (`MAJOR.MINOR.PATCH`). Bump rules in `docs-development/PROJECT-CONVENTIONS.md` §11.2: runtime behavior change -> at least patch +1; new feature -> minor +1; docs/comments only -> no bump |

### Exports
- `__version__` (imported by `tui/app.py` as `from agent._version import __version__ as APP_VERSION`, with an ImportError fallback to `"unknown"`)

### Dependencies
- Internal: none
- External: none (constant-only module)
