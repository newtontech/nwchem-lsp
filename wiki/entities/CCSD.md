# CCSD (耦合簇方法)

> 类型：计算方法
> 创建日期：2026-06-12
> 来源数：2

## 简介 (Introduction)

CCSD（Coupled Cluster Singles and Doubles）是一种高精度的电子相关方法，包含单激发和双激发。CCSD(T) 方法加上微扰三重激发，被称为"量子化学的金标准"。

## 语法结构 (Syntax Structure)

```nwchem
ccsd
  freeze <option>
  thresh <value>
  maxiter <n>
  ...
end
```

## CCSD 选项 (CCSD Options)

- `freeze atomic` - 冻结内层轨道（常用）
- `freeze <n>` - 冻结指定数量的轨道
- `thresh <value>` - 收敛阈值（默认 1e-6）
- `maxiter <n>` - 最大迭代次数
- `tce` - 使用张量收缩引擎
- `io` - 控制磁盘 I/O 策略
- `diis` - DIIS 加速收敛
- `nodis` - 禁用 DIIS
- `ccsd(t)` - 激活微扰三重激发

## CCSD 变体 (CCSD Variants)

- `ccsd` - 标准耦合簇 Singles and Doubles
- `ccsd(t)` - CCSD with perturbative Triples（金标准）
- `ccsd[t]` - CCSD with approximate Triples

## 示例 (Examples)

```nwchem
# Standard CCSD calculation
ccsd
  freeze atomic
  thresh 1e-7
end

# CCSD(T) - "Gold Standard"
ccsd
  freeze atomic
  thresh 1e-7
  maxiter 100
end

task ccsd(t) energy
```

## 计算成本 (Computational Cost)

- CCSD: O(N^6)
- CCSD(T): O(N^7)
- 适用于小分子（~20 原子以内）

## 相关来源 (Related Sources)

- `raw/assets/keywords_data.py` - CC_KEYWORDS
- `raw/assets/methane_ccsd.nw` - 示例

## 相关实体/概念 (Related Entities/Concepts)

- [[NWChem]]
- [[MP2]]
- [[Task_Operation]]

## 历史更新 (History)

- 2026-06-12: 初始创建
