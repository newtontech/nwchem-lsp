# MP2 (二阶微扰理论)

> 类型：计算方法
> 创建日期：2026-06-12
> 来源数：2

## 简介 (Introduction)

MP2（Second-order Møller-Plesset perturbation theory）是二阶 Møller-Plesset 微扰理论，是一种包含电子相关能量的后 Hartree-Fock 方法，比 HF 更精确但计算成本适中。

## 语法结构 (Syntax Structure)

```nwchem
mp2
  freeze <option>
  [ri|cd]
  ...
end
```

## MP2 选项 (MP2 Options)

- `freeze atomic` - 冻结内层轨道（常用）
- `freeze <n>` - 冻结指定数量的轨道
- `tight` - 使用更严格的收敛标准
- `ri` - 使用分辨率恒等近似加速计算
- `cd` - 使用 Cholesky 分解加速
- `thize <value>` - 积分阈值
- `thize_g <value>` - 梯度积分阈值
- `scratch disk` - 使用磁盘存储积分

## 示例 (Examples)

```nwchem
# Standard MP2 with frozen core
mp2
  freeze atomic
end

# MP2 with RI approximation for speed
mp2
  freeze atomic
  ri
end

# High-precision MP2
mp2
  freeze atomic
  tight
end

task mp2 optimize
```

## 计算成本 (Computational Cost)

- 常规 MP2: O(N^5)
- RI-MP2: O(N^4) - 显著加速
- 适用于中等大小分子（~100 原子以内）

## 相关来源 (Related Sources)

- `raw/assets/keywords_data.py` - MP2_KEYWORDS
- `raw/assets/benzene_mp2.nw` - 示例

## 相关实体/概念 (Related Entities/Concepts)

- [[NWChem]]
- [[CCSD]]
- [[Task_Operation]]

## 历史更新 (History)

- 2026-06-12: 初始创建
