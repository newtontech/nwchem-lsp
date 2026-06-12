# Geometry Section (几何结构部分)

> 类型：输入文件部分
> 创建日期：2026-06-12
> 来源数：3

## 简介 (Introduction)

`geometry` 部分定义分子的原子坐标和几何参数。这是 NWChem 输入文件中的必需部分。

## 语法结构 (Syntax Structure)

```nwchem
geometry [units <unit>] [options]
  <element> <x> <y> <z>
  ...
end
```

## 关键选项 (Key Options)

### 单位指定 (Units)
- `angstroms` - 埃（默认）/ Angstroms (default)
- `bohr` / `au` - 玻尔半径 / Bohr
- `nanometers` - 纳米 / Nanometers
- `picometers` - 皮米 / Picometers

### 几何选项 (Geometry Options)
- `autosym` - 自动对称性检测 / Automatic symmetry detection
- `noautoz` - 禁用自动 Z 矩阵生成 / Disable automatic Z-matrix
- `center` / `nocenter` - 是否将分子中心置于原点
- `system` - 周期性边界条件 / Periodic boundary conditions

## 示例 (Examples)

```nwchem
# Water molecule in Angstroms
geometry units angstroms
  O  0.000  0.000  0.000
  H  0.000  0.790  0.580
  H  0.000 -0.790  0.580
end

# Benzene with automatic symmetry
geometry units angstroms autosym
  C    1.398    0.000    0.000
  C    0.699    1.212    0.000
  ...
end
```

## 相关来源 (Related Sources)

- `raw/assets/keywords_data.py` - GEOMETRY_KEYWORDS
- `raw/assets/water_dft.nw` - 示例
- `raw/assets/benzene_mp2.nw` - 示例

## 相关实体/概念 (Related Entities/Concepts)

- [[NWChem]]
- [[Chemical_Elements]]

## 历史更新 (History)

- 2026-06-12: 初始创建
