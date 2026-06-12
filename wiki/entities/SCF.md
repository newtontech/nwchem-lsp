# SCF (自洽场方法)

> 类型：计算方法
> 创建日期：2026-06-12
> 来源数：3

## 简介 (Introduction)

SCF（Self-Consistent Field，自洽场）方法是量子化学计算的基础方法，也称为 Hartree-Fock 方法。NWChem 的 `scf` 部分用于配置 SCF 计算参数。

## 语法结构 (Syntax Structure)

```nwchem
scf
  <spin_state>
  <method>
  <convergence_options>
  ...
end
```

## 自旋状态 (Spin States)

- `singlet` - 单重态
- `doublet` - 二重态
- `triplet` - 三重态
- `quartet` - 四重态
- `quintet` - 五重态

## SCF 方法 (SCF Methods)

- `rhf` - 限制性 Hartree-Fock / Restricted Hartree-Fock
- `uhf` - 非限制性 Hartree-Fock / Unrestricted Hartree-Fock
- `rohf` - 限制性开壳层 Hartree-Fock / Restricted Open-shell HF
- `mcscf` - 多组态自洽场 / Multi-Configurational SCF

## 收敛选项 (Convergence Options)

- `thresh <value>` - 收敛阈值（默认 1e-6）
- `maxiter <n>` - 最大迭代次数（默认 50）
- `direct` - 直接 SCF（重新计算所有积分）
- `semidirect` - 半直接 SCF

## 示例 (Examples)

```nwchem
# Standard closed-shell RHF
scf
  singlet
  rhf
  maxiter 100
  thresh 1e-8
end

# Open-shell UHF calculation
scf
  doublet
  uhf
  thresh 1e-6
end

# High-precision calculation
scf
  singlet
  rhf
  thresh 1e-10
  maxiter 200
end
```

## 相关来源 (Related Sources)

- `raw/assets/keywords_data.py` - SCF_KEYWORDS
- `raw/assets/h2o_scf.nw` - 示例
- `raw/assets/3carbo.nw` - 示例

## 相关实体/概念 (Related Entities/Concepts)

- [[NWChem]]
- [[DFT]]
- [[Task_Operation]]

## 历史更新 (History)

- 2026-06-12: 初始创建
