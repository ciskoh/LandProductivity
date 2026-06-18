Code simplifier instruction

1. Take one module at a time, and exhamine the overall logic
2. streamline the overall logic of the module. Each module should start with a docstring describing why it is there and what is used for (including other modules that import its function)
3. If the logic opf the module allows it, have a main function at the bottom that is named like the module
4. Ensure as much as possible functional programming is followed, as well as pep8 throughout
5. Improve the logic of each function by prioritzing clarity and transparency of code
6. Always verify that all the test pass otherwise restart from point 2
7. Add dostring (google style) to each function describing the params but also why a function was created and where it is used
8. Commit atomically including "refactoring by claude" in the commit message