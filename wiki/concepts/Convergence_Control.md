# Convergence Control (收敛控制)

> 类型：概念
> 学科/领域：量子化学计算

## 定义 (Definition)

收敛控制参数决定 SCF 和几何优化的精度和收敛行为。

## SCF 收敛 (SCF Convergence)

### 收敛阈值 (Convergence Threshold)
```nwchem
scf
  thresh 1e-8
end

# DFT 中的收敛控制
dft
  convergence energy 1e-8
  convergence density 1e-6
  convergence gradient 1e-5
end
```

### 最大迭代次数 (Maximum Iterations)
```nwchem
scf
  maxiter 200
end

dft
  iterations 150
end
```

### 收敛加速 (Convergence Acceleration)
```nwchem
scf
  diis          # DIIS 加速（默认启用）
  levelshifting  # 能级移动
  damping        # 阻尼
end
```

## 几何优化收敛 (Geometry Optimization Convergence)

NWChem 默认使用内部优化器，收敛标准包括：
- 能量变化
- 梯度最大分量
- 梯度均方根
- 位移变化

## 常见收敛问题 (Common Convergence Problems)

### SCF 不收敛
- 症状：达到最大迭代次数仍未收敛
- 解决方案：
  1. 降低收敛阈值（`thresh 1e-5`）
  2. 增加最大迭代次数（`maxiter 200`）
  3. 尝试更好的初始猜测（`scf guess`）
  4. 使用阻尼或能级移动

### 几何优化不收敛
- 症状：优化步数过多
- 解决方案：
  1. 改变优化算法
  2. 检查势能面的平坦区域
  3. 尝试更好的初始几何

## 收敛阈值推荐 (Recommended Thresholds)

| 计算类型 | SCF 阈值 | 几何优化阈值 |
|---------|---------|-------------|
| 快速测试 | 1e-5 | 宽松 |
| 标准计算 | 1e-6 | 标准 |
| 高精度 | 1e-8 | 严格 |
| 发表级 | 1e-10 | 极严格 |

## 相关概念 (Related Concepts)

- [[SCF]]
- [[DFT]]
- [[Task_Operation]]

## 来源 (Sources)

- `raw/assets/keywords_data.py` - SCF_KEYWORDS, DFT_KEYWORDS
