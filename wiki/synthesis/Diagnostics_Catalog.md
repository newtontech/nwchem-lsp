# Diagnostics Catalog (诊断目录)

> 创建日期：2026-06-12
> 最后更新：2026-06-12
> 覆盖来源：2

## 核心论点 (Core Thesis)

nwchem-lsp 提供全面的诊断检测，帮助用户在运行 NWChem 前发现输入文件错误。

## 诊断分类 (Diagnostic Categories)

### 1. 语法错误 (Syntax Errors)

#### UNCLOSED_SECTION
- **代码**: `UNCLOSED_SECTION`
- **严重程度**: `error`
- **类别**: `syntax`
- **描述**: 部分块未闭合
- **示例**:
```nwchem
geometry
  O 0.0 0.0 0.0
# 缺少 'end'
```
- **修复**: 添加 `end` 关键字

#### UNEXPECTED_END
- **代码**: `UNEXPECTED_END`
- **严重程度**: `error`
- **类别**: `syntax`
- **描述**: 意外的 `end` 关键字
- **示例**:
```nwchem
end  # 没有匹配的部分开始
```
- **修复**: 删除多余的 `end`

#### MISSING_START
- **代码**: `MISSING_START`
- **严重程度**: `warning`
- **类别**: `syntax`
- **描述**: 缺少 `start` 指令
- **修复**: 添加 `start <name>`

### 2. 模式错误 (Schema Errors)

#### UNKNOWN_BASIS_SET
- **代码**: `UNKNOWN_BASIS_SET`
- **严重程度**: `error`
- **类别**: `schema`
- **描述**: 不支持的基组名称
- **示例**:
```nwchem
basis
  * library INVALID_BASIS
end
```
- **修复**: 使用有效基组名

#### UNKNOWN_FUNCTIONAL
- **代码**: `UNKNOWN_FUNCTIONAL`
- **严重程度**: `error`
- **类别**: `schema`
- **描述**: 不支持的 DFT 泛函
- **示例**:
```nwchem
dft
  xc INVALID_FUNCTIONAL
end
```
- **修复**: 使用有效泛函名

#### INVALID_TASK_OPERATION
- **代码**: `INVALID_TASK_OPERATION`
- **严重程度**: `error`
- **类别**: `schema`
- **描述**: 无效的任务操作组合

### 3. 拼写错误 (Typos)

#### TYPO_KEYWORD
- **代码**: `TYPO_KEYWORD`
- **严重程度**: `warning`
- **类别**: `style/deprecation`
- **描述**: 检测到常见拼写错误
- **示例**: `gemoetry` → `geometry`
- **修复**: 应用自动修复建议

### 4. 引用错误 (Reference Errors)

#### UNDEFINED_VARIABLE
- **代码**: `UNDEFINED_VARIABLE`
- **严重程度**: `error`
- **类别**: `cross-file reference`
- **描述**: 引用了未定义的变量

## 快速修复 (Quick Fixes)

### 代码操作 (Code Actions)

1. **添加缺失的 `end`**
   - 自动检测未闭合的部分
   - 在合适位置插入 `end`

2. **删除意外的 `end`**
   - 删除没有匹配的部分开始

3. **修正拼写错误**
   - 使用模糊匹配检测常见拼写错误
   - 提供修正建议

4. **添加 `start` 指令**
   - 当缺失时提供插入建议

## 严重程度策略 (Severity Policy)

| 严重程度 | 含义 | 阻止提交 |
|---------|------|---------|
| `error` | 高置信度错误，NWChem 将拒绝输入 | 是 |
| `warning` | 高风险输入，可能是故意的 | 否 |
| `information` | 风格或优化建议 | 否 |
| `hint` | 文档提示 | 否 |

## 诊断 API (Diagnostic API)

### 获取诊断
```bash
nwchem-lsp-tool check path/to/input.nw --format json
```

### 诊断输出格式
```json
{
  "uri": "file:///path/to/input.nw",
  "diagnostics": [
    {
      "code": "UNCLOSED_SECTION",
      "severity": "error",
      "category": "syntax",
      "confidence": 1.0,
      "range": {...},
      "message": "Unclosed section: 'geometry'"
    }
  ]
}
```

## 来源列表 (Source List)

- `raw/assets/DIAGNOSTIC_ENGINE_V1.md`
- `raw/assets/README.md`
