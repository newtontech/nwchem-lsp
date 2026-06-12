# Geometry Input Formats (几何输入格式)

> 类型：概念
> 学科/领域：量子化学输入

## 定义 (Definition)

NWChem 支持多种几何输入格式，包括笛卡尔坐标、Z 矩阵等。

## 笛卡尔坐标格式 (Cartesian Coordinates)

最常用的格式，直接指定 x, y, z 坐标：

```nwchem
geometry units angstroms
  O  0.000  0.000  0.000
  H  0.000  0.790  0.580
  H  0.000 -0.790  0.580
end
```

格式：`<元素> <x> <y> <z>`

## 单位选项 (Unit Options)

- `angstroms` - 埃（默认常用）
- `bohr` / `au` - 原子单位
- `nanometers` - 纳米
- `picometers` - 皮米

## Z 矩阵格式 (Z-Matrix)

内坐标格式，用键长、键角、二面角定义：

```nwchem
geometry noautoz
  O
  H  1  0.96
  H  1  0.96  2  104.5
end
```

格式：`<元素> [参考原子1] [键长] [参考原子2] [键角] [参考原子3] [二面角]`

## 几何优化选项 (Geometry Optimization Options)

### 对称性 (Symmetry)
- `autosym` - 自动检测分子对称性
- `noautosym` - 禁用对称性检测

### 坐标系统 (Coordinate Systems)
- `center` - 将分子中心置于原点
- `nocenter` - 不移动分子

### 周期性系统 (Periodic Systems)
- `system crystal` - 晶体
- `system slab` - 表面/平板
- `system polymer` - 聚合物
- `system helix` - 螺旋结构

## 示例 (Examples)

### 水分子（笛卡尔）
```nwchem
geometry units angstroms
  O  0.000  0.000  0.000
  H  0.000  0.790  0.580
  H  0.000 -0.790  0.580
end
```

### 苯（自动对称）
```nwchem
geometry units angstroms autosym
  C    1.398    0.000    0.000
  C    0.699    1.212    0.000
  C   -0.699    1.212    0.000
  C   -1.398    0.000    0.000
  C   -0.699   -1.212    0.000
  C    0.699   -1.212    0.000
  H    2.482    0.000    0.000
  H    1.241    2.152    0.000
  H   -1.241    2.152    0.000
  H   -2.482    0.000    0.000
  H   -1.241   -2.152    0.000
  H    1.241   -2.152    0.000
end
```

## 相关概念 (Related Concepts)

- [[Geometry_Section]]
- [[Chemical_Elements]]

## 来源 (Sources)

- `raw/assets/keywords_data.py` - GEOMETRY_KEYWORDS
- `raw/assets/water_dft.nw`
