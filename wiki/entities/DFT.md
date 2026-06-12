# DFT (密度泛函理论)

> 类型：计算方法
> 创建日期：2026-06-12
> 来源数：3

## 简介 (Introduction)

密度泛函理论（Density Functional Theory, DFT）是 NWChem 中最常用的量子化学计算方法之一，适用于中等大小分子的结构优化和性质计算。

## 语法结构 (Syntax Structure)

```nwchem
dft
  xc <functional>
  grid <grid_size>
  convergence <property> <value>
  ...
end
```

## 交换-相关泛函 (Exchange-Correlation Functionals)

### LDA/GGA 系列
- `LDA` / `S` - 局域密度近似
- `BLYP` - Becke-Lee-Yang-Parr
- `PBE` - Perdew-Burke-Ernzerhof
- `BP86` - Becke-Perdew 86
- `PW91` - Perdew-Wang 91
- `PBEsol` - 固体优化 PBE

### 杂化泛函 (Hybrid Functionals)
- `B3LYP` - Becke 三参数杂化（最常用）
- `PBE0` - PBE 杂化泛函
- `BHLYP` - Becke 半半杂化
- `B3PW91` - Becke-Perdew-Wang 91 杂化
- `X3LYP` / `O3LYP` - 改进杂化泛函

### 色散校正泛函 (Dispersion-Corrected)
- `B97-D` - Grimme 色散校正
- `wB97X-D` - 长程校正 + 色散
- `B97-1` / `B97-2` / `B98` - Becke 97 系列

### Meta-GGA
- `TPSS` - Tao-Perdew-Staroverov-Scuseria
- `M06-L` / `M06` / `M06-2X` / `M06-HF` - Minnesota 泛函系列
- `SCAN` / `rSCAN` / `r2SCAN` - 强约束近似泛函
- `MN12-L` / `MN12-SX` - Minnesota 12 泛函

### 长程校正泛函 (Range-Separated)
- `LC-BLYP` / `LC-PBE` - 长程校正
- `CAM-B3LYP` - Coulomb-attenuating 方法
- `wB97` / `wB97X` - 长程校正杂化
- `M11` / `M11-L` - M11 系列
- `M08-HX` / `M08-SO` - M08 系列

## DFT 选项 (DFT Options)

### 网格设置 (Grid Settings)
- `coarse` - 粗网格
- `medium` - 中等网格
- `fine` - 细网格（常用推荐）
- `xfine` - 超细网格
- `ultrafine` - 极细网格

### 收敛标准 (Convergence)
- `convergence energy <value>` - 能量收敛阈值
- `convergence density <value>` - 密度收敛阈值
- `convergence gradient <value>` - 梯度收敛阈值

### 其他选项 (Other Options)
- `direct` - 强制直接 SCF（重新计算积分）
- `noio` - 禁用积分的磁盘 I/O
- `odft` - 开壳层 DFT 计算
- `mult <n>` - 自旋多重度
- `iterations <n>` - 最大 SCF 迭代次数

## 示例 (Examples)

```nwchem
# Standard B3LYP calculation
dft
  xc b3lyp
  grid fine
  convergence energy 1e-8
end

# High-precision calculation with dispersion
dft
  xc wB97X-D
  grid xfine
  convergence energy 1e-10
  iterations 200
end

# Open-shell calculation
dft
  xc B3LYP
  mult 2
  odft
end
```

## 相关来源 (Related Sources)

- `raw/assets/keywords_data.py` - DFT_FUNCTIONALS 列表
- `raw/assets/water_dft.nw` - 示例
- `raw/assets/3carbo_dft.nw` - 示例

## 相关实体/概念 (Related Entities/Concepts)

- [[NWChem]]
- [[XC_Functional]]
- [[Task_Operation]]

## 历史更新 (History)

- 2026-06-12: 初始创建
