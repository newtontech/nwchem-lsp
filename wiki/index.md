# NWChem LSP Wiki (NWChem 语言服务器知识库)

> 创建日期：2026-06-12
> 最后更新：2026-06-12
> Wiki 类型：Karpathy 风格 LLM Wiki

## 概述 (Overview)

本知识库是 nwchem-lsp 项目的官方文档和参考指南，涵盖 NWChem 量子化学软件的 LSP 实现和 NWChem 领域知识。

## 目录结构 (Structure)

### 实体 (Entities)
NWChem 特定概念和组件的详细页面：

- [[NWChem]] - NWChem 量子化学软件
- [[Geometry_Section]] - 几何结构部分
- [[Basis_Set]] - 基组规范
- [[DFT]] - 密度泛函理论
- [[Task_Operation]] - 任务操作
- [[SCF]] - 自洽场方法
- [[MP2]] - 二阶微扰理论
- [[CCSD]] - 耦合簇方法
- [[ECP]] - 有效核势
- [[Chemical_Elements]] - 化学元素
- [[XC_Functional]] - 交换-相关泛函
- [[LSP_Server]] - 语言服务器
- [[Diagnostic_System]] - 诊断系统

### 概念 (Concepts)
跨领域的量子化学概念和方法论：

- [[Quantum_Chemistry_Methods]] - 量子化学方法层级
- [[Basis_Set_Selection]] - 基组选择策略
- [[Geometry_Input_Formats]] - 几何输入格式
- [[Convergence_Control]] - 收敛控制
- [[Spin_and_Multiplicity]] - 自旋与多重度

### 综合 (Synthesis)
API 参考、诊断目录和 DSL 规范：

- [[NWChem_DSL_Reference]] - NWChem DSL 完整参考
- [[Diagnostics_Catalog]] - 诊断目录
- [[Feature_Providers_API]] - 特性提供器 API
- [[Parser_API]] - 解析器 API

## 原始材料 (Raw Materials)

详细源证据位于 `raw/assets/`：

- `README.md` - 项目文档
- `PLAN.md` - 开发计划
- `AGENTS.md` - 代理工作流指南
- `architecture.md` - 架构文档
- `DIAGNOSTIC_ENGINE_V1.md` - 诊断引擎规范
- `keywords_data.py` - 关键词数据库
- `nwchem_parser.py` - 解析器实现
- `*.nw` - 示例输入文件

## 更新日志 (Change Log)

见 `log.md` 获取详细变更历史。

## 快速导航 (Quick Navigation)

### 对于 LSP 用户
- [[LSP_Server]] - LSP 功能概述
- [[Diagnostics_Catalog]] - 可用的诊断
- [[Feature_Providers_API]] - 功能详情

### 对于 NWChem 用户
- [[NWChem_DSL_Reference]] - 完整语法参考
- [[Geometry_Section]] - 几何定义
- [[Basis_Set]] - 基组选择
- [[DFT]] - DFT 配置

### 对于开发者
- [[Parser_API]] - 解析器 API
- [[Feature_Providers_API]] - 扩展指南
- [[Diagnostic_System]] - 诊断系统架构

## 贡献指南 (Contributing)

更新 Wiki 时：
1. 保持原始材料在 `raw/assets/` 不变
2. 在 `wiki/` 中更新衍生内容
3. 记录变更到 `log.md`
4. 更新相关链接

---

本 Wiki 使用 Obsidian 兼容的 markdown 格式，支持 `[[Wiki_Link]]` 双向链接。
