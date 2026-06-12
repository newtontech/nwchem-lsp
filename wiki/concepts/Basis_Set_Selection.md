# Basis Set Selection (基组选择策略)

> 类型：概念
> 学科/领域：量子化学

## 定义 (Definition)

基组选择是平衡计算精度和成本的关键决策。基组质量直接影响计算结果的准确性。

## 基组分类 (Basis Set Classification)

### 最小基组 (Minimal Basis)
- `STO-3G`
- 每个原子一个基函数
- 用途：快速测试、教学演示

### 分裂价键基组 (Split-Valence)
- `3-21G`, `6-31G`, `6-311G`
- 价轨道分裂为多个基函数
- 用途：常规计算

### 极化基组 (Polarized Basis)
- `6-31G*` / `6-31G(d)` - 添加 d 极化函数
- `6-31G**` / `6-31G(d,p)` - 重原子加 d，氢加 p
- 用途：精确几何、能量

### 弥散函数基组 (Diffuse Basis)
- `6-31+G*` - 添加弥散函数
- `aug-cc-pVXZ` - 全部元素加弥散
- 用途：阴离子、弱相互作用、激发态

### 相关一致基组 (Correlation-Consistent)
- `cc-pVDZ`, `cc-pVTZ`, `cc-pVQZ`, `cc-pV5Z`
- 系统收敛，适合外推
- 用途：高精度相关能计算

## 选择策略 (Selection Strategy)

### DFT 计算
```nwchem
# 标准计算
basis spherical
  * library 6-31G*
end

# 高精度
basis spherical
  * library def2-TZVP
end

# 弱相互作用/阴离子
basis spherical
  * library aug-cc-pVTZ
end
```

### 高精度波函数方法
```nwchem
# MP2/CCSD
basis spherical
  * library cc-pVTZ
end

# 完全基组极限外推
basis spherical
  * library cc-pVQZ
end
```

### 过渡金属
```nwchem
# 赝势 + 双-zeta
ecp
  * library LANL2DZ
end

basis spherical
  * library LANL2DZ
end
```

## 基组与方法的匹配 (Basis-Method Matching)

| 方法 | 推荐基组 | 说明 |
|------|---------|------|
| DFT-GGA | 6-31G*, def2-SVP | 标准精度 |
| DFT-杂化 | def2-TZVP, cc-pVTZ | 高精度 |
| MP2 | cc-pVTZ, aug-cc-pVDZ | 需要极化 |
| CCSD(T) | cc-pVTZ/cc-pVQZ | 接近完全基组极限 |

## 相关概念 (Related Concepts)

- [[Basis_Set]]
- [[ECP]]
- [[MP2]]

## 来源 (Sources)

- `raw/assets/keywords_data.py` - BASIS_SETS
