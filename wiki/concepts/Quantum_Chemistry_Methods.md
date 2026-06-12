# Quantum Chemistry Methods (量子化学方法层级)

> 类型：概念
> 学科/领域：量子化学

## 定义 (Definition)

量子化学方法按精度和计算成本分为多个层级，从快速的经验方法到高精度的从头算方法。

## 方法层级 (Method Hierarchy)

### 1. 经验方法 (Empirical Methods)
- 计算成本：最低
- 精度：定性
- 适用场景：快速筛选、超大规模

### 2. 半经验方法 (Semi-Empirical)
- 计算成本：O(N³)
- 精度：中等
- 方法：AM1, PM3, MNDO
- 适用场景：中等有机分子

### 3. Hartree-Fock (HF)
- 计算成本：O(N⁴)
- 精度：定性，无电子相关
- NWChem: `task scf`
- 局限：不包含电子相关能量

### 4. 密度泛函理论 (DFT)
- 计算成本：O(N³) 到 O(N⁴)
- 精度：定量
- NWChem: `task dft`
- 常用泛函：B3LYP, PBE0, wB97X-D
- 适用场景：最常用的方法

### 5. 微扰理论 (MP2, MP3, MP4)
- 计算成本：MP2 O(N⁵), MP3 O(N⁶), MP4 O(N⁷)
- 精度：良好
- NWChem: `task mp2`
- 适用场景：中等大小分子的相关能校正

### 6. 耦合簇方法 (CCSD, CCSD(T))
- 计算成本：CCSD O(N⁶), CCSD(T) O(N⁷)
- 精度：极高（金标准）
- NWChem: `task ccsd(t)`
- 局限：仅适用于小分子

## 方法选择指南 (Method Selection Guide)

| 分子大小 | 推荐方法 | 精度/成本平衡 |
|---------|---------|--------------|
| > 200 原子 | 半经验 | 快速筛选 |
| 50-200 原子 | DFT (GGA) | 日常计算 |
| 20-50 原子 | DFT (杂化) | 精确计算 |
| 10-20 原子 | DFT + 色散 | 高精度 |
| < 10 原子 | CCSD(T) | 金标准 |

## 相关概念 (Related Concepts)

- [[DFT]]
- [[MP2]]
- [[CCSD]]

## 来源 (Sources)

- `raw/assets/README.md`
- 量子化学标准教材
