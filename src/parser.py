from enum import Enum
from .formula import Formula, FormulaType
from .knowledgebase import Kb

class Associates(Enum):
    LEFT = 1
    RIGHT = 2

class Parser:
    def is_ignore_token(self, token):
        return token.strip() == ""

    def precedence(self, op):
        return {
            "!": 4,
            "&&": 3,
            "||": 2,
            "=>": 1,
            "<=>": 0
        }.get(op, -1)

    def associativity(self, op):
        if op in {"!", "=>"}:
            return Associates.RIGHT
        return Associates.LEFT

    def parse_kb_from_string(self, s):
        kb = Kb()
        for line in s.strip().splitlines():
            line = line.strip()
            if line:
                kb.add(self.parse_formula(line))
        return kb

    def parse_kb_from_file(self, path):
        with open(path, "r") as f:
            return self.parse_kb_from_string(f.read())

    def tokenize(self, formula_str):
        import re
        pattern = r"(<=>|=>|&&|\|\||[()!]|[A-Za-z0-9_]+|[\+\-])"
        return re.findall(pattern, formula_str)

    def parse_formula(self, formula_str):
        tokens = self.tokenize(formula_str)
        output = []
        stack = []

        for token in tokens:
            if token in {"&&", "||", "=>", "<=>", "!"}:
                while stack and stack[-1] not in {"(", ")"}:
                    top = stack[-1]
                    if (self.associativity(token) == Associates.LEFT and self.precedence(token) <= self.precedence(top)) or \
                       (self.associativity(token) == Associates.RIGHT and self.precedence(token) < self.precedence(top)):
                        output.append(stack.pop())
                    else:
                        break
                stack.append(token)
            elif token == "(":
                stack.append(token)
            elif token == ")":
                while stack and stack[-1] != "(":
                    output.append(stack.pop())
                if not stack:
                    raise RuntimeError("Mismatched parentheses")
                stack.pop()
            else:
                output.append(token)

        while stack:
            if stack[-1] in {"(", ")"}:
                raise RuntimeError("Mismatched parentheses")
            output.append(stack.pop())

        return self._parse_output(output)

    def _parse_output(self, output_tokens):
        stack = []

        for token in output_tokens:
            if token == "!":
                if not stack:
                    raise RuntimeError("Missing operand for '!'")
                operand = stack.pop()
                stack.append(Formula(FormulaType.NOT, left=operand))
            elif token in {"&&", "||", "=>", "<=>"}:
                if len(stack) < 2:
                    raise RuntimeError(f"Missing operands for '{token}'")
                right = stack.pop()
                left = stack.pop()
                type_map = {
                    "&&": FormulaType.AND,
                    "||": FormulaType.OR,
                    "=>": FormulaType.IMPLIES,
                    "<=>": FormulaType.IFF
                }
                stack.append(Formula(type_map[token], left=left, right=right))
            else:
                if token == "+":
                    stack.append(Formula(FormulaType.TRUE))
                elif token == "-":
                    stack.append(Formula(FormulaType.FALSE))
                else:
                    stack.append(Formula(FormulaType.ATOM, atom=token))

        if len(stack) != 1:
            raise RuntimeError("Invalid formula structure")

        return stack[0]