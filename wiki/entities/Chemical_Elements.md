# Chemical Elements (化学元素)

> 类型：数据
> 创建日期：2026-06-12
> 来源数：1

## 简介 (Introduction)

NWChem 支持全部 118 种化学元素，可用于几何结构定义和基组指定。

## 元素列表 (Element List)

NWChem 支持的元素符号（按原子序数）：

1-18 (主族元素):
- H, He, Li, Be, B, C, N, O, F, Ne
- Na, Mg, Al, Si, P, S, Cl, Ar

19-36:
- K, Ca, Sc, Ti, V, Cr, Mn, Fe, Co, Ni, Cu, Zn
- Ga, Ge, As, Se, Br, Kr

37-54:
- Rb, Sr, Y, Zr, Nb, Mo, Tc, Ru, Rh, Pd, Ag, Cd
- In, Sn, Sb, Te, I, Xe

55-86:
- Cs, Ba, La-Lu (镧系)
- Hf, Ta, W, Re, Os, Ir, Pt, Au, Hg, Tl, Pb, Bi, Po, At, Rn

87-118:
- Fr, Ra, Ac-Lr (锕系)
- Rf, Db, Sg, Bh, Hs, Mt, Ds, Rg, Cn, Nh, Fl, Mc, Lv, Ts, Og

## 在几何结构中的使用 (Usage in Geometry)

```nwchem
geometry units angstroms
  H  0.0  0.0  0.0
  C  0.0  0.0  1.0
  O  0.0  0.0  2.0
  Fe 0.0  0.0  3.0
  Pt 0.0  0.0  4.0
end
```

## 在基组中的使用 (Usage in Basis)

```nwchem
basis spherical
  H library 6-31G*
  C library cc-pVTZ
  Fe library def2-TZVP
  Pt library LANL2DZ
end
```

## 相关来源 (Related Sources)

- `raw/assets/keywords_data.py` - ELEMENTS 列表

## 相关实体/概念 (Related Entities/Concepts)

- [[NWChem]]
- [[Geometry_Section]]
- [[Basis_Set]]

## 历史更新 (History)

- 2026-06-12: 初始创建
