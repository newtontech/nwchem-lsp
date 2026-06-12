# NWChem (量子化学软件)

> 类型：软件 / 量子化学计算
> 创建日期：2026-06-12
> 来源数：5

## 简介 (Introduction)

NWChem is an open-source quantum chemistry software package designed for high-performance computing. It provides capabilities for molecular structure optimization, property calculations, and dynamics simulations using various quantum mechanical methods.

## 关键特性 (Key Features)

- 支持多种量子化学方法 (Supports multiple quantum chemistry methods)
  - SCF (自洽场) / Self-Consistent Field
  - DFT (密度泛函理论) / Density Functional Theory
  - MP2 (二阶微扰理论) / Second-order Møller-Plesset perturbation theory
  - CCSD/CCSD(T) (耦合簇) / Coupled Cluster
- 并行计算支持 (Parallel computing support)
- 支持周期性体系 (Periodic system support)
- 分子动力学模拟 (Molecular dynamics simulations)

## 输入文件格式 (Input File Format)

NWChem 使用 `.nw` 或 `.nwinp` 扩展名的输入文件，包含以下主要部分：

1. **start** - 指定计算名称
2. **title** - 计算标题
3. **geometry** - 分子几何结构
4. **basis** - 基组指定
5. **理论模块** - scf, dft, mp2, ccsd 等
6. **task** - 执行的任务

## 相关来源 (Related Sources)

- `raw/assets/README.md` - 项目文档
- `raw/assets/water_dft.nw` - 示例输入文件
- `raw/assets/keywords_data.py` - 关键词数据库

## 相关实体/概念 (Related Entities/Concepts)

- [[Geometry_Section]]
- [[Basis_Set]]
- [[DFT]]
- [[Task_Operation]]

## 历史更新 (History)

- 2026-06-12: 初始创建
