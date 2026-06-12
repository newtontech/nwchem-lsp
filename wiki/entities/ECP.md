# ECP (有效核势)

> 类型：基组/方法
> 创建日期：2026-06-12
> 来源数：1

## 简介 (Introduction)

ECP（Effective Core Potential，有效核势）也称为赝势，用于替代重金属原子的内层电子，减少计算成本同时保持合理的精度。

## 语法结构 (Syntax Structure)

```nwchem
ecp
  <element> library <ecp_name>
end
```

## 常用 ECP (Common ECPs)

- `LANL2DZ` - Los Alamos ECP + 双-zeta 价基
- `LANL2TZ` - Los Alamos ECP + 三-zeta 价基
- `SDD` - Stuttgart/Dresden ECP

## 适用元素 (Applicable Elements)

ECP 主要用于：
- 过渡金属（Transition metals）
- 镧系和锕系（Lanthanides and actinides）
- 重元素（Heavy elements, Z > 36）

## 示例 (Examples)

```nwchem
# Platinum with LANL2DZ ECP
ecp
  Pt library LANL2DZ
end

basis
  Pt library LANL2DZ
  * library 6-31G*
end

# Transition metal complex
ecp
  Fe library SDD
  Cu library SDD
end

basis spherical
  Fe library SDD
  Cu library SDD
  H library 6-31G*
end
```

## 相关来源 (Related Sources)

- `raw/assets/keywords_data.py` - ECP 关键词定义
- `raw/assets/fe_scf_ecp.nw` - 示例

## 相关实体/概念 (Related Entities/Concepts)

- [[NWChem]]
- [[Basis_Set]]

## 历史更新 (History)

- 2026-06-12: 初始创建
