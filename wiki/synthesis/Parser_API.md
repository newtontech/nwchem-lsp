# Parser API (解析器 API)

> 创建日期：2026-06-12
> 最后更新：2026-06-12
> 覆盖来源：2

## 核心论点 (Core Thesis)

`NwchemParser` 是 nwchem-lsp 的核心解析组件，提供 NWChem 输入文件的完整语法分析能力。

## 类定义 (Class Definition)

```python
class NwchemParser:
    def __init__(self, source: str)
```

## 关键词集合 (Keyword Sets)

### SECTION_KEYWORDS
需要 `end` 关键字闭合的部分：

```
geometry, basis, scf, dft, mp2, ccsd, ccsd(t), ecp, so, tce,
mcscf, selci, hessian, vib, property, rt_tddft, pspw, band,
paw, ofpw, bq, cons
```

### TOP_LEVEL_KEYWORDS
顶层命令：

```
start, restart, title, echo, set, unset, stop, task, charge,
memory, permanent_dir, scratch_dir, print
```

## 主要方法 (Main Methods)

### get_context()
```python
def get_context(self, line_number: int, column: int) -> ParseContext
```

获取指定位置的解析上下文。

**返回**: `ParseContext` 包含：
- `line_number` - 行号
- `column` - 列号
- `current_section` - 当前部分名称
- `section_stack` - 部分层栈
- `line_content` - 行内容
- `word_at_cursor` - 光标处的词
- `is_in_block` - 是否在部分块内

### get_completion_context()
```python
def get_completion_context(self, line_number: int, column: int) -> Dict[str, Any]
```

获取补全上下文信息。

**返回**:
- `type` - 补全类型（top_level, geometry, basis, dft 等）
- `section` - 当前部分
- `word` - 当前单词
- `line` - 行内容
- `in_block` - 是否在块内

### get_section_at_line()
```python
def get_section_at_line(self, line_number: int) -> Optional[str]
```

获取指定行号所在的部分名称。

### get_all_sections()
```python
def get_all_sections(self) -> List[str]
```

获取所有部分名称列表。

### get_section_content()
```python
def get_section_content(self, section_name: str) -> List[NWchemSection]
```

获取指定部分的所有实例。

### is_valid_syntax()
```python
def is_valid_syntax(self) -> Tuple[bool, List[Tuple[int, str]]]
```

检查输入文件语法是否有效。

**返回**: `(is_valid, errors)`
- `is_valid` - 布尔值，是否有效
- `errors` - 错误列表，每个为 `(line_number, message)`

### parse()
```python
def parse(self) -> list[Any]
```

解析并返回所有部分作为块列表。

### validate()
```python
def validate(self) -> list[dict[str, Any]]
```

验证并返回错误字典列表。

## 数据结构 (Data Structures)

### ParseContext
```python
@dataclass
class ParseContext:
    line_number: int
    column: int
    current_section: Optional[str]
    section_stack: List[str]
    line_content: str
    word_at_cursor: str
    is_in_block: bool
```

### NWchemSection
```python
@dataclass
class NWchemSection:
    name: str
    start_line: int
    end_line: Optional[int]
    keywords: List[str]
    content: List[str]
    line_start: int = 0
```

## 使用示例 (Usage Examples)

### 基本解析
```python
from nwchem_lsp.parser.nwchem_parser import NwchemParser

source = """
geometry units angstroms
  O 0.0 0.0 0.0
  H 0.0 0.8 0.6
end
"""

parser = NwchemParser(source)
context = parser.get_context(1, 0)
print(context.current_section)  # "geometry"
```

### 语法验证
```python
is_valid, errors = parser.is_valid_syntax()
if not is_valid:
    for line, message in errors:
        print(f"Line {line}: {message}")
```

### 获取补全上下文
```python
ctx = parser.get_completion_context(2, 10)
print(ctx["type"])  # "geometry"
```

## 来源列表 (Source List)

- `raw/assets/nwchem_parser.py`
- `raw/assets/architecture.md`
