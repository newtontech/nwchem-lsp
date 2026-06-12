# XC Functional (交换-相关泛函)

> 类型：量子化学概念
> 创建日期：2026-06-12
> 来源数：2

## 简介 (Introduction)

交换-相关泛函（Exchange-Correlation Functional）是 DFT 计算的核心，决定了计算的精度和适用性。

## 泛函分类 (Functional Categories)

### 局域密度近似 (LDA)
- `LDA` / `S` - 基于均匀电子气模型

### 广义梯度近似 (GGA)
- `PBE` - Perdew-Burke-Ernzerhof
- `BLYP` - Becke-Lee-Yang-Parr
- `BP86` - Becke-Perdew 86
- `PW91` - Perdew-Wang 91

### 杂化泛函 (Hybrid)
- `B3LYP` - 最常用，20% HF 交换
- `PBE0` - 25% HF 交换
- `X3LYP` - 改进的杂化泛函

### 色散校正 (Dispersion-Corrected)
- `B97-D` - Grimme 色散
- `wB97X-D` - 长程 + 色散

### Meta-GGA
- `TPSS` - Tao-Perdew-Staroverov-Scuseria
- `M06-2X` - 高非局域性
- `SCAN` / `rSCAN` / `r2SCAN` - 强约束近似

### 双杂化 (Double Hybrid)
- `B2PLYP` - 包含 MP2 相关

## 在 DFT 部分使用 (Usage in DFT Section)

```nwchem
dft
  xc <functional_name>
end
```

## 泛函选择指南 (Functional Selection Guide)

| 应用场景 | 推荐泛函 |
|---------|---------|
| 一般有机分子 | B3LYP, PBE0 |
| 含弱相互作用 | B97-D, wB97X-D |
| 固体/表面 | PBEsol, SCAN |
| 过渡金属 | M06-L, TPSS |
| 高精度要求 | wB97X, DSD-PBEP86 |
| 快速筛选 | BLYP, PBE |

## 相关来源 (Related Sources)

- `raw/assets/keywords_data.py` - DFT_FUNCTIONALS 列表

## 相关实体/概念 (Related Entities/Concepts)

- [[DFT]]
- [[NWChem]]

## 历史更新 (History)

- 2026-06-12: 初始创建
