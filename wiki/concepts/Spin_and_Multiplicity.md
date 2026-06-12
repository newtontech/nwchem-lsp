# Spin and Multiplicity (自旋与多重度)

> 类型：概念
> 学科/领域：量子化学

## 定义 (Definition)

自旋态和多重度是描述分子电子状态的基本参数，影响 SCF 方法的类型选择。

## 多重度定义 (Multiplicity Definition)

多重度 = 2S + 1，其中 S 是总自旋量子数。

## 常见自旋态 (Common Spin States)

### 单重态 (Singlet, Mult = 1)
- 所有电子配对
- 闭壳层分子
- 示例：H₂, CO, 苯

```nwchem
scf
  singlet
  rhf
end
```

### 二重态 (Doublet, Mult = 2)
- 一个未配对电子
- 自由基
- 示例：CH₃•, OH•

```nwchem
scf
  doublet
  uhf
end

# 或在 DFT 中
dft
  mult 2
  odft
end
```

### 三重态 (Triplet, Mult = 3)
- 两个未配对电子
- 示例：O₂（基态）

```nwchem
scf
  triplet
  uhf
end
```

## SCF 方法与自旋 (SCF Methods and Spin)

### 闭壳层 (Closed Shell)
- `rhf` - 限制性 Hartree-Fock
- 适用于：单重态

### 开壳层 (Open Shell)
- `uhf` - 非限制性 Hartree-Fock
- 适用于：自由基、三重态等

- `rohf` - 限制性开壳层 HF
- 适用于：需要限制性形式的开壳层

## 电荷与多重度 (Charge and Multiplicity)

NWChem 通过 `charge` 命令设置总电荷：

```nwchem
charge -1  # 阴离子
charge 0   # 中性分子
charge +1  # 阳离子

scf
  doublet  # 对于阴离子自由基
end
```

## 自旋污染 (Spin Contamination)

UHF 计算可能产生自旋污染（⟨S²⟩ 偏离理论值）。
- 检查：查看输出中的 ⟨S²⟩ 值
- 解决：使用 ROHF 或更高精度方法

## 相关概念 (Related Concepts)

- [[SCF]]
- [[DFT]]
- [[Task_Operation]]

## 来源 (Sources)

- `raw/assets/keywords_data.py` - SCF_KEYWORDS
