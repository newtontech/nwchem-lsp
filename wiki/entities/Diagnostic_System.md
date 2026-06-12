# Diagnostic System (诊断系统)

> 类型：系统设计
> 创建日期：2026-06-12
> 来源数：2

## 简介 (Introduction)

nwchem-lsp 实现了结构化的诊断系统，符合 Scientific LSP 诊断契约，提供确定性 JSON 输出用于代理驱动的检查/修复循环。

## 严重程度策略 (Severity Policy)

- `error` - 高置信度的语法、模式、类型/值或引用问题，应阻止自动提交
- `warning` - 高风险或可疑输入，可能是故意的
- `information` / `hint` - 风格、文档或可选优化信息

## 诊断类别 (Diagnostic Categories)

- `syntax` - 语法错误
- `schema` - 模式违反（缺失必需部分等）
- `type/value` - 类型或值错误
- `cross-file reference` - 跨文件引用问题
- `semantic consistency` - 语义一致性
- `preflight/runtime-risk` - 运行时风险
- `style/deprecation` - 风格或弃用警告

## 常见诊断 (Common Diagnostics)

### 语法错误 (Syntax Errors)
- `UNCLOSED_SECTION` - 未闭合的部分块
- `UNEXPECTED_END` - 意外的 `end` 关键字
- `MISSING_START` - 缺少 `start` 指令

### 模式错误 (Schema Errors)
- `UNKNOWN_BASIS_SET` - 不支持的基组
- `UNKNOWN_FUNCTIONAL` - 不支持的 DFT 泛函
- `INVALID_TASK` - 无效的任务操作

### 快速修复 (Quick Fixes)
- 添加缺失的 `end` 关键字
- 删除意外的 `end` 关键字
- 修正常见拼写错误（gemoetry → geometry）
- 添加缺失的 `start` 指令

## 富诊断形状 (Rich Diagnostic Shape)

```json
{
  "code": "STABLE_CODE",
  "severity": "error",
  "category": "schema",
  "confidence": 1.0,
  "source": "nwchem-lsp",
  "range": {
    "start": {"line": 0, "character": 0},
    "end": {"line": 0, "character": 1}
  },
  "software": "nwchem",
  "file_type": "input",
  "path": "input",
  "expected": null,
  "actual": null,
  "manual_ref": null,
  "fix_hints": [],
  "blocking": true
}
```

## 代理 CLI (Agent CLI)

```bash
nwchem-lsp-tool check path/to/input --format json
nwchem-lsp-tool context path/to/input --format json
nwchem-lsp-tool complete path/to/input --format json
nwchem-lsp-tool hover path/to/input --format json
nwchem-lsp-tool symbols path/to/input --format json
nwchem-lsp-tool fix path/to/input --format json
```

## 相关来源 (Related Sources)

- `raw/assets/DIAGNOSTIC_ENGINE_V1.md` - 诊断引擎文档

## 相关实体/概念 (Related Entities/Concepts)

- [[LSP_Server]]
- [[NWChem]]

## 历史更新 (History)

- 2026-06-12: 初始创建
