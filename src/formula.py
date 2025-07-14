from enum import Enum
from pysat.formula import IDPool

class FormulaType(Enum):
    ATOM = 1
    TRUE = 2
    FALSE = 3
    NOT = 4
    AND = 5
    OR = 6
    IMPLIES = 7
    IFF = 8

class CnfTransformation(Enum):
    NAIVE = 1
    TSEITIN = 2

class Formula:
    def __init__(self, type, left=None, right=None, atom=None):
        self.type = type
        self.left = left
        self.right = right
        self.atom = atom

    def __str__(self):
        if self.type == FormulaType.ATOM:
            return self.atom
        elif self.type == FormulaType.TRUE:
            return "+"
        elif self.type == FormulaType.FALSE:
            return "-"
        elif self.type == FormulaType.NOT:
            return f"!({self.left})"
        elif self.type == FormulaType.AND:
            return f"({self.left} && {self.right})"
        elif self.type == FormulaType.OR:
            return f"({self.left} || {self.right})"
        elif self.type == FormulaType.IMPLIES:
            return f"({self.left} => {self.right})"
        elif self.type == FormulaType.IFF:
            return f"({self.left} <=> {self.right})"
        return

    def __repr__(self):
        return self.__str__()

    def eliminate_iff(self):
        if self.type == FormulaType.IFF:
            a = self.left.eliminate_iff()
            b = self.right.eliminate_iff()
            return Formula(FormulaType.AND,
                           Formula(FormulaType.IMPLIES, left=a, right=b),
                           Formula(FormulaType.IMPLIES, left=b, right=a))
        elif self.type in [FormulaType.IMPLIES, FormulaType.AND, FormulaType.OR]:
            return Formula(self.type,
                           self.left.eliminate_iff(),
                           self.right.eliminate_iff())
        elif self.type == FormulaType.NOT:
            return Formula(FormulaType.NOT, left=self.left.eliminate_iff())
        else:
            return self

    def eliminate_implies(self):
        if self.type == FormulaType.IMPLIES:
            return Formula(FormulaType.OR,
                           Formula(FormulaType.NOT, left=self.left.eliminate_implies()),
                           self.right.eliminate_implies())
        elif self.type in [FormulaType.AND, FormulaType.OR]:
            return Formula(self.type,
                           self.left.eliminate_implies(),
                           self.right.eliminate_implies())
        elif self.type == FormulaType.NOT:
            return Formula(FormulaType.NOT, left=self.left.eliminate_implies())
        else:
            return self

    def push_not_inwards(self):
        if self.type == FormulaType.NOT:
            inner = self.left
            if inner.type == FormulaType.NOT:
                return inner.left.push_not_inwards()
            elif inner.type == FormulaType.AND:
                return Formula(FormulaType.OR,
                               Formula(FormulaType.NOT, left=inner.left).push_not_inwards(),
                               Formula(FormulaType.NOT, left=inner.right).push_not_inwards())
            elif inner.type == FormulaType.OR:
                return Formula(FormulaType.AND,
                               Formula(FormulaType.NOT, left=inner.left).push_not_inwards(),
                               Formula(FormulaType.NOT, left=inner.right).push_not_inwards())
            else:
                return Formula(FormulaType.NOT, left=inner.push_not_inwards())
        elif self.type in [FormulaType.AND, FormulaType.OR]:
            return Formula(self.type,
                           self.left.push_not_inwards(),
                           self.right.push_not_inwards())
        else:
            return self

    def distribute_or_over_and(self):
        if self.type == FormulaType.OR:
            A = self.left.distribute_or_over_and()
            B = self.right.distribute_or_over_and()
            if A.type == FormulaType.AND:
                return Formula(FormulaType.AND,
                               Formula(FormulaType.OR, A.left, B).distribute_or_over_and(),
                               Formula(FormulaType.OR, A.right, B).distribute_or_over_and())
            elif B.type == FormulaType.AND:
                return Formula(FormulaType.AND,
                               Formula(FormulaType.OR, A, B.left).distribute_or_over_and(),
                               Formula(FormulaType.OR, A, B.right).distribute_or_over_and())
            else:
                return Formula(FormulaType.OR, A, B)
        elif self.type == FormulaType.AND:
            return Formula(FormulaType.AND,
                           self.left.distribute_or_over_and(),
                           self.right.distribute_or_over_and())
        else:
            return self

    def to_cnf(self, method=CnfTransformation.NAIVE, id_pool=None, atom_true_varmap=None):
        if method == CnfTransformation.NAIVE:
            return self.eliminate_iff() \
                       .eliminate_implies() \
                       .push_not_inwards() \
                       .distribute_or_over_and()
        elif method == CnfTransformation.TSEITIN:
            if id_pool is None or atom_true_varmap is None:
                raise ValueError("id_pool and atom_true_varmap missing")
            clauses = []
            top_var = self.to_cnf_tseitin_recursive(id_pool, atom_true_varmap, clauses)
            return top_var, clauses
        else:
            raise ValueError("unknown CNF transformation method.")

    def to_cnf_tseitin_recursive(self, id_pool, atom_true_varmap, clauses):
        if self.type == FormulaType.ATOM:
            return atom_true_varmap[self.atom]

        elif self.type == FormulaType.TRUE:
            v = id_pool.id()
            clauses.append([v])
            return v

        elif self.type == FormulaType.FALSE:
            v = id_pool.id()
            clauses.append([-v])
            return v
        
        elif self.type == FormulaType.NOT:
            a = self.left.to_cnf_tseitin_recursive(id_pool, atom_true_varmap, clauses)
            v = id_pool.id()
            clauses.append([-v, -a])
            clauses.append([v, a])
            return v

        a = self.left.to_cnf_tseitin_recursive(id_pool, atom_true_varmap, clauses)
        b = self.right.to_cnf_tseitin_recursive(id_pool, atom_true_varmap, clauses)
        v = id_pool.id()

        if self.type == FormulaType.AND:
            clauses.append([-v, a])
            clauses.append([-v, b])
            clauses.append([v, -a, -b])
            return v

        elif self.type == FormulaType.OR:
            clauses.append([v, -a])
            clauses.append([v, -b])
            clauses.append([-v, a, b])
            return v

        elif self.type == FormulaType.IMPLIES:
            clauses.append([-v, -a, b])
            clauses.append([v, a])
            clauses.append([v, -b])
            return v

        elif self.type == FormulaType.IFF:
            clauses.append([-v, -a, b])
            clauses.append([-v, a, -b])
            clauses.append([v, a, b])
            clauses.append([v, -a, -b])
            return v
        
        else:
            raise RuntimeError("unknown formula type")

    def get_atoms(self):
        if self.type == FormulaType.ATOM:
            return {self.atom}
        elif self.type in {FormulaType.TRUE, FormulaType.FALSE}:
            return set()
        elif self.type == FormulaType.NOT:
            return self.left.get_atoms()
        elif self.type in {FormulaType.AND, FormulaType.OR, FormulaType.IMPLIES, FormulaType.IFF}:
            return self.left.get_atoms().union(self.right.get_atoms())
        else:
            return set()

    def is_atom(self):
        return self.type == FormulaType.ATOM

    def is_negation(self):
        return self.type == FormulaType.NOT

    def is_conjunction(self):
        return self.type == FormulaType.AND

    def is_disjunction(self):
        return self.type == FormulaType.OR

    def is_implication(self):
        return self.type == FormulaType.IMPLIES

    def is_equivalence(self):
        return self.type == FormulaType.IFF

    def is_tautology(self):
        return self.type == FormulaType.TRUE

    def is_contradiction(self):
        return self.type == FormulaType.FALSE

    def get_name(self):
        if self.is_atom():
            return self.atom
        return str(self)

    def get_subformulas(self):
        if self.type in {FormulaType.AND, FormulaType.OR, FormulaType.IMPLIES, FormulaType.IFF}:
            return [self.left, self.right]
        elif self.type == FormulaType.NOT:
            return [self.left]
        else:
            return []