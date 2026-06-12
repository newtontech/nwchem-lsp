# Task Operation (任务操作)

> 类型：NWChem 命令
> 创建日期：2026-06-12
> 来源数：3

## 简介 (Introduction)

`task` 命令指定 NWChem 要执行的计算任务。它是 NWChem 输入文件中的必需部分，定义了使用何种理论方法执行何种计算类型。

## 语法结构 (Syntax Structure)

```nwchem
task <theory> <operation>
```

## 理论方法 (Theories)

- `scf` - 自洽场方法 / Self-Consistent Field
- `dft` - 密度泛函理论 / Density Functional Theory
- `mp2` - 二阶微扰理论 / MP2 perturbation theory
- `ccsd` - 耦合簇 Singles and Doubles
- `ccsd(t)` - CCSD with perturbative Triples
- `mcscf` - 多组态自洽场 / Multi-Configurational SCF
- `semi` - 半经验方法 / Semi-empirical methods
- `rimp2` - 分辨率恒等 MP2 / RI-MP2

## 计算操作 (Operations)

### 能量计算 (Energy Calculations)
- `energy` - 单点能量计算

### 几何优化 (Geometry Optimization)
- `optimize` - 分子几何结构优化

### 梯度相关 (Gradient Related)
- `gradient` - 梯度计算

### 振动分析 (Vibrational Analysis)
- `frequencies` / `freq` / `vib` - 振动频率计算
- `hessian` - Hessian 矩阵计算

### 过渡态 (Transition State)
- `saddle` - 过渡态搜索

### 动力学 (Dynamics)
- `dynamics` - 分子动力学模拟
- `thermodynamics` - 热力学性质计算

### 性质计算 (Property Calculations)
- `property` - 分子性质计算

### 高级方法 (Advanced Methods)
- `tce` - 张量收缩引擎
- `ccsd` / `ccsd(t)` - 耦合簇计算
- `mp2` / `mp3` / `mp4` - 微扰理论
- `mcscf` - 多组态自洽场
- `selci` - 选定 CI
- `pspw` - 赝势平面波
- `band` - 能带结构计算
- `paw` - 投影缀加波
- `ofpw` - 正交平面波

## 示例 (Examples)

```nwchem
# DFT geometry optimization
task dft optimize

# Single point energy calculation
task scf energy

# MP2 frequency calculation
task mp2 frequencies

# CCSD(T) single point
task ccsd(t) energy

# Molecular dynamics
task scf dynamics

# Hessian calculation
task dft hessian
```

## 相关来源 (Related Sources)

- `raw/assets/keywords_data.py` - TASK_OPERATIONS 列表
- `raw/assets/water_dft.nw` - 示例
- `raw/assets/benzene_mp2.nw` - 示例

## 相关实体/概念 (Related Entities/Concepts)

- [[NWChem]]
- [[DFT]]
- [[SCF]]
- [[MP2]]

## 历史更新 (History)

- 2026-06-12: 初始创建
