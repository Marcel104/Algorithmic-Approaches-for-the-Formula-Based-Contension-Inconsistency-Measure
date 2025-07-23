# Introduction

This project is based on the Master-Thesis 'Algorithmic Approaches for the Formula-Based Contension Inconsistency Measure' at the 'Fernuniversität in Hagen'.

Inconsistency measures are used to quantitatively measure the degree of logical inconsistency. 
For example, they can provide information about the number of logical contradictions within a collection of statements, which also allows for more in-depth analysis or localization. 
Such a collection of statements is also called a knowledge base, which can be expanded accordingly by deriving rules between the existing statements.

The agorithmic approaches, provided in this project, use Max SAT Solver and Answer Set Programming.

# Formula-Based Contension Inconsistency Measure

To calculate the formula-based contension inconsistency measure ($I_{fc}$) we use the three-valued logic by Graham Priest where we can assign each Atom a third truth-value 'both'.
$I_{fc}$ now calculates the minimum of formulas, where at least one atom got assigned the value 'both'.

$I_{fc}$ is formulawise satisfiability-oriented: each formula is checked individually whether it needs a both-valued atom to be satisfied. This leads to syntactic sensitivity as logically equivalent transformations can change the number of formulas and how they are affected by both-assignments.

# Experiment Orchestration

The *main.py* script is the execution entry point and manages the entire experiment lifecycle. The process is initiated within the if *__name__ == "__main__"* clause.
Initially, CSV log files are initialized with appropriate headers. Then, the *get_all_files()* function scans the data directory and compiles a list of all knowl-
edge bases to be processed. In the main loop, each file is read in, and for each knowledgebase, the three solving functions *asp_encode_and_solve()*, *maxsat_encode_and_solve()*, and *maxsat_tseitin_encode_and_solve()* are called.

To ensure the robustness of the experimental process, each solver call is wrapped by the *run_without_timeout function*. This function starts the solver in a separate process and enforces a hard time limit of 1000 seconds. 
If the solver fails or exceeds the time limit, the process is safely terminated and the error or timeout is logged without interrupting the overall experiment.
Result extraction is implemented in a solver-specific manner. 
The function *asp_encode_and_solve* uses the *on_model* callback function from the Clingo library. 
For each optimal model found, this callback extracts the cost and the atoms of the *val/2* and *f_inconsistent/1* predicates to reconstruct the solution details.

The MaxSAT functions use the RC2 solver from the PySAT library. 
After computing the result using *rc2.compute()*, the cost is directly read from the solver object. 
To retrieve solution details, the returned model is analyzed and integer variables are translated back into their boolean interpretations using a reverse_varmap. 
The violated soft clauses reveal the inconsistent formulas.
All collected data, including precise runtime measurements for encoding and solving, are written by write_result to two separate CSV files: *log_file_general.csv* for general results and *log_file_maxsat.csv* for additional MaxSAT-specific metrics such as the number of hard clauses.
