import os

import squirrel

minion_module_name = os.getenv("MODULE_NAME", "minion")
minion_variable_name = os.getenv("VARIABLE_NAME", "minion")

# check for legacy compatibility
if ":" not in minion_module_name:
    print("old MODULE_NAME only invocation detected, going to add variable name")
    app = f"{minion_module_name}:{minion_variable_name}"
else:
    app = minion_module_name

if __name__ == "__main__":
    squirrel.run(app)
