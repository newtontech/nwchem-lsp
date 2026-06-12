# Feature Providers API (特性提供器 API)

> 创建日期：2026-06-12
> 最后更新：2026-06-12
> 覆盖来源：4

## 核心论点 (Core Thesis)

nwchem-lsp 采用模块化的特性提供器架构，每个 LSP 功能由独立的提供器类实现，便于维护和扩展。

## 提供器列表 (Provider List)

### 1. CompletionProvider (自动补全)

**类**: `NwchemCompletionProvider`

**方法**:
- `get_completions(text, position)` - 返回补全项列表

**支持上下文**:
- 顶层关键词补全
- 部分内部关键词补全
- 基组名称补全
- DFT 泛函补全
- 任务操作补全
- 化学元素补全

**触发字符**: 空格, 换行

### 2. HoverProvider (悬停文档)

**类**: `NwchemHoverProvider`

**方法**:
- `get_hover(text, position)` - 返回悬停信息

**提供信息**:
- 关键词描述
- 参数说明
- 示例代码
- 相关关键词

### 3. DiagnosticProvider (诊断提供器)

**类**: `DiagnosticProvider`

**方法**:
- `get_diagnostics(text)` - 返回诊断列表
- `update_cache(uri, diagnostics)` - 更新诊断缓存
- `snapshot_to_json(uri)` - 导出 JSON 格式诊断

**检测内容**:
- 未闭合的部分块
- 意外的 `end` 关键字
- 未知的基组
- 未知的泛函
- 缺失的 `start` 指令

### 4. SymbolProvider (符号提供器)

**类**: `NwchemSymbolProvider`

**方法**:
- `get_document_symbols(text)` - 返回文档符号列表

**符号类型**:
- 部分（geometry, basis, scf, dft 等）
- 任务

### 5. WorkspaceSymbolProvider (工作区符号)

**类**: `WorkspaceSymbolProvider`

**方法**:
- `get_workspace_symbols(query, documents)` - 跨文档搜索符号

### 6. FormattingProvider (格式化提供器)

**类**: `NwchemFormattingProvider`

**方法**:
- `format_document(text, params)` - 格式化整个文档
- `format_range(text, params)` - 格式化选定范围

**格式化规则**:
- 关键词小写
- 移除多余空行
- 统一缩进

### 7. CodeActionsProvider (代码操作提供器)

**类**: `CodeActionsProvider`

**方法**:
- `get_code_actions(text, diagnostics, uri)` - 返回可用的代码操作

**支持的代码操作**:
- 添加缺失的 `end`
- 删除意外的 `end`
- 修正拼写错误
- 添加 `start` 指令

### 8. DefinitionProvider (定义提供器)

**类**: `DefinitionProvider`

**方法**:
- `get_definition(text, position)` - 返回定义位置

**功能**:
- 从 `end` 跳转到对应的部分开始
- 从任务跳转到相关配置

### 9. SemanticTokensProvider (语义标记提供器)

**类**: `SemanticTokensProvider`

**方法**:
- `get_semantic_tokens(text)` - 返回语义标记

**标记类型**:
- 关键词
- 元素符号
- 数值
- 注释

### 10. InlayHintsProvider (内联提示提供器)

**类**: `InlayHintsProvider`

**方法**:
- `get_inlay_hints(text, start_line, end_line)` - 返回内联提示

**提示内容**:
- 单位信息
- 电荷状态
- 参数说明

### 11. FoldingRangeProvider (代码折叠提供器)

**类**: `FoldingRangeProvider`

**方法**:
- `get_folding_ranges(text)` - 返回可折叠范围

**折叠区域**:
- 所有以 `end` 结束的部分块

### 12. ReferencesProvider (引用提供器)

**类**: `ReferencesProvider`

**方法**:
- `get_references(text, uri, position, include_declaration)` - 查找符号引用

### 13. RenameProvider (重命名提供器)

**类**: `RenameProvider`

**方法**:
- `get_rename_edits(text, uri, position, new_name)` - 执行符号重命名

**重命名范围**:
- 部分名称
- 任务引用

### 14. ConfigProvider (配置提供器)

**类**: `ConfigProvider`

**方法**:
- `get_config(section)` - 获取配置项

**配置选项**:
- 格式化选项
- 诊断选项
- 补全选项

## 扩展指南 (Extension Guide)

添加新特性提供器：

1. 创建新类继承基础功能
2. 实现必需的方法
3. 在 `NWChemLanguageServer.__init__` 中注册
4. 在 `_register_handlers` 中添加 LSP 处理器

## 来源列表 (Source List)

- `raw/assets/architecture.md`
- `raw/assets/README.md`
- `raw/assets/nwchem_lsp/server.py`
