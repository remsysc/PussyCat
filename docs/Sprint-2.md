# Sprint 2: Transpiler Pipeline Implementation

**Status:** 11/11 tasks completed

## Tasks

### Lexer
- [x] ~~#15. Implement regex pattern: `r'[a-zA-Z_]\w*|[0-9]+(?:\.[0-9]+)?|"[^"]*"|\'[^\']*\'|[^\s]|\s+'`~~
- [x] ~~#16. Implement line tracking by counting `\n` in each match~~
- [x] ~~#17. Implement token classification (KEYWORD, IDENT, NUMBER, STRING, SYMBOL, WHITESPACE, COMMENT)~~
- [x] ~~#18. Handle unknown tokens with `LexerError` including line number~~
- [x] ~~#19. Unit tests for tokenize() with edge cases~~

### Transpiler
- [x] ~~#20. Implement token iteration and Python code building~~
- [x] ~~#21. Implement line_map generation (Python line → PussyCat source line)~~
- [x] ~~#22. Handle KEYWORD_MAP substitution for all 19 keywords~~

### Executor
- [x] ~~#23. Write Python code to tempfile, subprocess.run with 10s timeout, capture output~~
- [x] ~~#24. Implement stderr line number remapping to PussyCat source~~
- [x] ~~#25. Unit tests for execute() with success/error/timeout cases~~
