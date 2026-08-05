import os

import squirrel

module_name = os.getenv("MODULE_NAME", "app")
variable_name = os.getenv("VARIABLE_NAME", "app")

# check for legacy compatibility
if ":" not in module_name:
    print("old MODULE_NAME only invocation detected, going to add variable name")
    app = f"{module_name}:{variable_name}"
else:
    app = module_name

if __name__ == "__main__":
    squirrel.run(app)
