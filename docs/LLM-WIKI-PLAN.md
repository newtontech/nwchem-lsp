# LLM Wiki Structure Plan (LLM Wiki 结构计划)

> 项目：nwchem-lsp
> 创建日期：2026-06-12
> Wiki 版本：1.0

## 概述 (Overview)

本 Wiki 采用 Karpathy 风格的 LLM 维护模式，将原始证据材料（raw/）与衍生知识页面（wiki/）分离，确保知识可追溯和可更新。

## 目录结构 (Directory Structure)

```
nwchem-lsp/
├── raw/
│   └── assets/
│       ├── README.md
│       ├── PLAN.md
│       ├── AGENTS.md
│       ├── CHANGELOG.md
│       ├── architecture.md
│       ├── DIAGNOSTIC_ENGINE_V1.md
│       ├── keywords_data.py
│       ├── nwchem_parser.py
│       ├── water_dft.nw
│       ├── benzene_mp2.nw
│       ├── methane_ccsd.nw
│       ├── h2o_scf.nw
│       ├── 3carbo.nw
│       └── 3carbo_dft.nw
├── wiki/
│   ├── entities/       # NWChem 特定实体
│   │   ├── NWChem.md
│   │   ├── Geometry_Section.md
│   │   ├── Basis_Set.md
│   │   ├── DFT.md
│   │   ├── Task_Operation.md
│   │   ├── SCF.md
│   │   ├── MP2.md
│   │   ├── CCSD.md
│   │   ├── ECP.md
│   │   ├── Chemical_Elements.md
│   │   ├── XC_Functional.md
│   │   ├── LSP_Server.md
│   │   └── Diagnostic_System.md
│   ├── concepts/       # 跨领域概念
│   │   ├── Quantum_Chemistry_Methods.md
│   │   ├── Basis_Set_Selection.md
│   │   ├── Geometry_Input_Formats.md
│   │   ├── Convergence_Control.md
│   │   └── Spin_and_Multiplicity.md
│   ├── synthesis/      # API 参考和综合文档
│   │   ├── NWChem_DSL_Reference.md
│   │   ├── Diagnostics_Catalog.md
│   │   ├── Feature_Providers_API.md
│   │   └── Parser_API.md
│   ├── index.md        # 导航中心
│   └── log.md          # 变更日志
```

## 内容分类 (Content Classification)

### 实体页面 (Entity Pages)

NWChem 特定的概念、组件和数据结构：

| 页面 | 描述 | 关键属性 |
|------|------|---------|
| NWChem | 量子化学软件 | 方法、功能、输入格式 |
| Geometry_Section | 几何结构部分 | 单位、选项、格式 |
| Basis_Set | 基组规范 | 类型、系列、选择策略 |
| DFT | 密度泛函理论 | 泛函、网格、收敛 |
| Task_Operation | 任务操作 | 理论、操作类型 |
| SCF | 自洽场方法 | 自旋态、收敛选项 |
| MP2 | 二阶微扰理论 | 冻结轨道、近似 |
| CCSD | 耦合簇方法 | 激发态、精度 |
| ECP | 有效核势 | 赝势类型、适用元素 |
| Chemical_Elements | 化学元素 | 118 种元素列表 |
| XC_Functional | 交换-相关泛函 | LDA、GGA、杂化 |
| LSP_Server | 语言服务器 | 特性、提供器 |
| Diagnostic_System | 诊断系统 | 错误类别、快速修复 |

### 概念页面 (Concept Pages)

跨领域的量子化学概念和方法论：

| 页面 | 描述 | 核心内容 |
|------|------|---------|
| Quantum_Chemistry_Methods | 方法层级 | 精度/成本权衡 |
| Basis_Set_Selection | 基组选择 | 选择策略指南 |
| Geometry_Input_Formats | 几何格式 | 笛卡尔、Z 矩阵 |
| Convergence_Control | 收敛控制 | SCF、几何优化 |
| Spin_and_Multiplicity | 自旋多重度 | 单重、二重、三重态 |

### 综合页面 (Synthesis Pages)

API 参考、目录和规范：

| 页面 | 描述 | 内容类型 |
|------|------|---------|
| NWChem_DSL_Reference | DSL 语法参考 | 完整语法、示例 |
| Diagnostics_Catalog | 诊断目录 | 错误代码、修复 |
| Feature_Providers_API | 特性提供器 | LSP 功能 API |
| Parser_API | 解析器 API | 类、方法、数据结构 |

## 维护指南 (Maintenance Guidelines)

### 更新规则

1. **原始材料优先** - raw/ 文件不可变，除非用户明确要求
2. **源引用** - 所有 Wiki 页面必须引用原始来源
3. **双向链接** - 使用 `[[Wiki_Link]]` 连接相关页面
4. **变更记录** - 每次更新记录到 log.md

### 页面模板

**实体页面**:
```markdown
# Entity_Name

> 类型：材料 / 方法 / 人物 / 组织 / 框架 / 数据集 / 其他
> 创建日期：YYYY-MM-DD
> 来源数：N

## 简介
## 关键属性
## 相关来源
## 相关实体/概念
## 历史更新
```

**概念页面**:
```markdown
# Concept_Name

> 类型：概念
> 学科/领域：

## 定义
## 核心机制
## 应用场景
## 相关概念
## 来源
```

**综合页面**:
```markdown
# Topic

> 创建日期：YYYY-MM-DD
> 最后更新：YYYY-MM-DD
> 覆盖来源：N

## 核心论点
## 证据梳理
## 操作框架
## 开放问题
## 来源列表
```

### 链接约定

- 实体链接：`[[Entity_Name]]`
- 概念链接：`[[Concept_Name]]`
- 原始文件：`raw/assets/filename.ext`

## 扩展指南 (Extension Guidelines)

### 添加新实体

1. 在 `wiki/entities/` 创建新页面
2. 使用实体页面模板
3. 添加到 `index.md` 目录
4. 记录到 `log.md`

### 添加新概念

1. 在 `wiki/concepts/` 创建新页面
2. 使用概念页面模板
3. 链接相关实体和概念
4. 更新导航

### 更新现有页面

1. 保持原始引用
2. 添加更新日期
3. 记录变更到 log.md
4. 更新相关链接

## 质量标准 (Quality Standards)

- 所有主张必须有源引用
- 不确定的信息标注不确定性
- 使用双语（中文标题，英文术语）
- 保持 Obsidian 兼容性
- 维护双向链接一致性

---

**版本历史**:
- v1.0 (2026-06-12): 初始 Wiki 结构
