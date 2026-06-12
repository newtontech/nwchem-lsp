# LSP Server (语言服务器)

> 类型：软件架构
> 创建日期：2026-06-12
> 来源数：4

## 简介 (Introduction)

nwchem-lsp 是 NWChem 的 Language Server Protocol（语言服务器协议）实现，为编辑器提供智能编辑功能，包括语法检查、自动补全、悬停文档等。

## 架构组件 (Architecture Components)

### 核心服务器 (Core Server)
- `NWChemLanguageServer` - 主 LSP 服务器类
- 基于 pygls 框架构建
- 版本: 0.5.0

### 特性提供器 (Feature Providers)

| 提供器 | 功能 |
|--------|------|
| `NwchemCompletionProvider` | 自动补全 |
| `NwchemHoverProvider` | 悬停文档 |
| `DiagnosticProvider` | 语法/错误诊断 |
| `NwchemSymbolProvider` | 文档符号 |
| `WorkspaceSymbolProvider` | 工作区符号 |
| `NwchemFormattingProvider` | 代码格式化 |
| `CodeActionsProvider` | 代码操作/快速修复 |
| `DefinitionProvider` | 跳转到定义 |
| `SemanticTokensProvider` | 语义高亮 |
| `InlayHintsProvider` | 内联提示 |
| `FoldingRangeProvider` | 代码折叠 |
| `ReferencesProvider` | 查找引用 |
| `RenameProvider` | 重命名 |

### 数据模块 (Data Module)
- `keywords.py` - 关键词数据库
- 包含化学元素、基组、泛函等

### 解析器模块 (Parser Module)
- `NwchemParser` - NWChem 输入文件解析器
- `ParseContext` - 解析上下文
- `NWchemSection` - 部分表示

## LSP 功能 (LSP Capabilities)

### v0.1.0 - 基础功能
- 语法验证
- 自动补全
- 悬停文档
- 文档符号

### v0.2.0
- 代码格式化

### v0.3.0
- 代码操作（快速修复）
- 跳转到定义

### v0.4.0
- 工作区符号
- 配置选项
- 语义高亮
- 内联提示

### v0.5.0
- 代码折叠
- 查找引用
- 重命名

## 支持的文件类型 (Supported File Types)

- `.nw` - NWChem 输入文件
- `.nwinp` - NWChem 输入文件（替代扩展名）

## 相关来源 (Related Sources)

- `raw/assets/README.md` - 项目文档
- `raw/assets/architecture.md` - 架构文档
- `raw/assets/nwchem_parser.py` - 解析器实现

## 相关实体/概念 (Related Entities/Concepts)

- [[NWChem]]
- [[Diagnostic_System]]

## 历史更新 (History)

- 2026-06-12: 初始创建
