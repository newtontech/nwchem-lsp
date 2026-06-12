# Basis Set (基组)

> 类型：量子化学概念
> 创建日期：2026-06-12
> 来源数：3

## 简介 (Introduction)

基组是用于描述分子轨道的数学函数集合。NWChem 支持多种标准基组库。

## 语法结构 (Syntax Structure)

```nwchem
basis [spherical|cartesian]
  <element> library <basis_name>
  * library <basis_name>  # Apply to all elements
end
```

## 常用基组 (Common Basis Sets)

### Pople 系列 (Pople Series)
- `STO-3G` - 最小基组 / Minimal basis
- `3-21G` - 分裂价键基组
- `6-31G` / `6-31G*` / `6-31G**` - 标准分裂价键
- `6-311G` / `6-311G**` - 三重分裂价键
- `6-31+G*` - 含弥散函数

### Dunning 相关一致基组 (Dunning Correlation-Consistent)
- `cc-pVDZ` - 相关一致双-zeta
- `cc-pVTZ` - 相关一致三-zeta
- `cc-pVQZ` / `cc-pV5Z` / `cc-pV6Z` - 更高精度
- `aug-cc-pVXZ` - 含弥散函数增强

### Def2 系列
- `def2-SVP` - 分裂价键加极化
- `def2-TZVP` - 三-zeta 价键加极化
- `def2-TZVPP` / `def2-QZVP` / `def2-QZVPP`

### 赝势基组 (ECP Basis Sets)
- `LANL2DZ` / `LANL2TZ` - Los Alamos 赝势基组
- `SDD` - Stuttgart-Dresden 赝势

### 其他
- `DGDZVP` - Godunov 基组
- `MINI` / `MIDI` - 小型基组

## 示例 (Examples)

```nwchem
# Apply 6-31G* to all elements
basis spherical
  * library 6-31G*
end

# Different basis for different elements
basis spherical
  H library STO-3G
  O library 6-31G*
end

# High-quality calculation
basis spherical
  * library cc-pVTZ
end
```

## 选项 (Options)

- `spherical` - 球谐基函数 / Spherical harmonic basis functions
- `cartesian` - 笛卡尔基函数 / Cartesian basis functions
- `library` - 从库中加载基组
- `file` - 从文件加载基组

## 相关来源 (Related Sources)

- `raw/assets/keywords_data.py` - BASIS_SETS 列表
- `raw/assets/water_dft.nw` - 示例
- `raw/assets/benzene_mp2.nw` - 示例

## 相关实体/概念 (Related Entities/Concepts)

- [[NWChem]]
- [[ECP]]

## 历史更新 (History)

- 2026-06-12: 初始创建
