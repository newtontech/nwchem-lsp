# NWChem DSL Reference (NWChem 领域特定语言参考)

> 创建日期：2026-06-12
> 最后更新：2026-06-12
> 覆盖来源：3

## 核心论点 (Core Thesis)

NWChem 输入文件是一种领域特定语言（DSL），用于描述量子化学计算。本参考提供了完整的语法结构。

## 输入文件结构 (Input File Structure)

```nwchem
# 1. 计算标识
start <project_name>

# 2. 标题
title "<calculation_title>"

# 3. 电荷（可选）
charge <integer>

# 4. 内存设置（可选）
memory total <n> gb

# 5. 几何结构（必需）
geometry [units <unit>] [options]
  <element> <x> <y> <z>
  ...
end

# 6. 基组（必需）
basis [spherical|cartesian]
  <element> library <basis_set>
  * library <basis_set>
end

# 7. 赝势（可选）
ecp
  <element> library <ecp_name>
end

# 8. 理论方法配置
scf|dft|mp2|ccsd
  <method_options>
end

# 9. 任务（必需）
task <theory> <operation>
```

## 顶层关键词 (Top-Level Keywords)

### 计算控制 (Calculation Control)
- `start <name>` - 指定重启文件名
- `restart <name>` - 从之前的计算重启
- `title "<string>"` - 设置计算标题
- `charge <n>` - 设置分子电荷
- `echo ["<string>"]` - 输出字符串

### 资源设置 (Resource Settings)
- `memory total <n> gb` - 设置内存限制
- `memory stack <n> mb` - 设置栈内存
- `memory heap <n> mb` - 设置堆内存
- `permanent_dir <path>` - 永久目录
- `scratch_dir <path>` - 临时目录

### 部分定义 (Section Definitions)
- `geometry` - 几何结构
- `basis` - 基组
- `ecp` - 有效核势
- `scf` - SCF 配置
- `dft` - DFT 配置
- `mp2` - MP2 配置
- `ccsd` - CCSD 配置
- `task` - 执行任务

## 部分语法 (Section Syntax)

### Geometry 部分
```nwchem
geometry [units angstroms|bohr|...] [autosym|noautoz] [center|nocenter]
  <element> <x> <y> <z>
  ...
end
```

### Basis 部分
```nwchem
basis [spherical|cartesian]
  <element> library <basis_set>
  * library <basis_set>  # 所有元素
end
```

### DFT 部分
```nwchem
dft
  xc <functional>
  grid <coarse|medium|fine|xfine|ultrafine>
  convergence energy <value>
  iterations <n>
end
```

### SCF 部分
```nwchem
scf
  [singlet|doublet|triplet|quartet|quintet]
  [rhf|uhf|rohf]
  thresh <value>
  maxiter <n>
end
```

### MP2 部分
```nwchem
mp2
  freeze [atomic|<n>]
  [ri|cd]
  [tight]
end
```

### CCSD 部分
```nwchem
ccsd
  freeze [atomic|<n>]
  thresh <value>
  maxiter <n>
end
```

### Task 命令
```nwchem
task <theory> <operation>

# 理论：scf, dft, mp2, ccsd, ccsd(t), mcscf, semi, rimp2
# 操作：energy, optimize, gradient, frequencies, hessian, dynamics, property, saddle
```

## 语法约定 (Syntax Conventions)

1. **大小写不敏感** - 关键词不区分大小写
2. **注释** - `#` 开始单行注释
3. **字符串** - 使用双引号
4. **结束标记** - 部分块以 `end` 结束
5. **行续** - 使用反斜杠 `\` 续行

## 完整示例 (Complete Example)

```nwchem
start water_dft

title "Water molecule DFT/B3LYP optimization"

charge 0
memory total 2 gb

geometry units angstroms autosym
  O  0.000000  0.000000  0.000000
  H  0.000000  0.790000  0.580000
  H  0.000000 -0.790000  0.580000
end

basis spherical
  * library 6-31G*
end

dft
  xc b3lyp
  grid fine
  convergence energy 1e-8
  iterations 100
end

task dft optimize
```

## 来源列表 (Source List)

- `raw/assets/README.md`
- `raw/assets/keywords_data.py`
- `raw/assets/water_dft.nw`
