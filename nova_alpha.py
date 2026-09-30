import sys
import os
import math
import time
import random as py_random
import getpass
import subprocess
import shutil
import re
import json
import urllib.request
import urllib.error
import urllib.parse
import tkinter as tk
import threading
from concurrent.futures import ThreadPoolExecutor


# ============================================================
# NOVA v0.8
# Full Feature Test: Graphics, Events, Networking, System, Async
# ============================================================

variables = {}
functions = {}
modules = {}
classes = {}

current_program = ""
current_object = None

# ============================================================
# NOVA v0.8 RUNTIME STATE
# ============================================================

graphics_root = None
graphics_canvas = None
graphics_color = "black"
graphics_events = []
async_executor = ThreadPoolExecutor(max_workers=8)
async_tasks = {}
async_task_counter = 0


# ============================================================
# CLASS SYSTEM
# ============================================================

class NovaClass:

    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent
        self.properties = {}
        self.methods = {}

    def get_property(self, name):

        if name in self.properties:
            return self.properties[name]

        if self.parent:
            return self.parent.get_property(name)

        raise Exception(
            f"Class '{self.name}' has no property '{name}'."
        )

    def get_method(self, name):

        if name in self.methods:
            return self.methods[name]

        if self.parent:
            return self.parent.get_method(name)

        raise Exception(
            f"Class '{self.name}' has no method '{name}'."
        )


class NovaObject:

    def __init__(self, nova_class):
        self.nova_class = nova_class
        self.properties = {}
        self.load_properties(nova_class)

    def load_properties(self, nova_class):

        if nova_class.parent:
            self.load_properties(nova_class.parent)

        for name, value in nova_class.properties.items():
            self.properties[name] = value

    def get(self, name):

        if name in self.properties:
            return self.properties[name]

        raise Exception(
            f"Object of class '{self.nova_class.name}' "
            f"has no property '{name}'."
        )

    def set(self, name, value):
        self.properties[name] = value


# ============================================================
# NETWORKING
# ============================================================

def network_decode(data):
    try:
        return json.loads(data)
    except Exception:
        return data


def network_get(url):
    request = urllib.request.Request(
        str(url),
        headers={"User-Agent": "Nova/0.7"}
    )

    with urllib.request.urlopen(request, timeout=10) as response:
        data = response.read().decode("utf-8")

    return network_decode(data)


def network_request(method, url, data=None):
    body = None

    if data is not None:
        if isinstance(data, (dict, list)):
            body = json.dumps(data).encode("utf-8")
        else:
            body = str(data).encode("utf-8")

    request = urllib.request.Request(
        str(url),
        data=body,
        method=method,
        headers={
            "User-Agent": "Nova/0.7",
            "Content-Type": "application/json"
        }
    )

    with urllib.request.urlopen(request, timeout=10) as response:
        result = response.read().decode("utf-8")

    return network_decode(result)


def network_online():
    try:
        urllib.request.urlopen(
            "https://example.com",
            timeout=3
        )
        return True
    except Exception:
        return False


# ============================================================
# STANDARD MODULES
# ============================================================

def load_standard_modules():

    return {

        "math": {
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "floor": math.floor,
            "ceil": math.ceil,
            "abs": abs,
            "round": round,
            "pow": pow,
            "pi": math.pi,
            "e": math.e,
        },

        "time": {
            "sleep": time.sleep,
            "now": lambda: time.strftime("%H:%M:%S"),
            "date": lambda: time.strftime("%Y-%m-%d"),
            "time": lambda: time.strftime("%H:%M:%S"),
            "year": lambda: int(time.strftime("%Y")),
            "month": lambda: int(time.strftime("%m")),
            "day": lambda: int(time.strftime("%d")),
            "hour": lambda: int(time.strftime("%H")),
            "minute": lambda: int(time.strftime("%M")),
            "second": lambda: int(time.strftime("%S")),
        },

        "random": {
            "random": lambda a, b:
                py_random.randint(int(a), int(b)),
            "choice": lambda x:
                py_random.choice(x),
            "chance": lambda x:
                py_random.random() < x,
        },

        "string": {
            "upper": lambda x: str(x).upper(),
            "lower": lambda x: str(x).lower(),
            "title": lambda x: str(x).title(),
            "reverse": lambda x: str(x)[::-1],
            "length": lambda x: len(x),
        },

        "network": {
            "get": lambda url: network_get(url),
            "post": lambda url, data: network_request("POST", url, data),
            "put": lambda url, data: network_request("PUT", url, data),
            "delete": lambda url: network_request("DELETE", url),
            "online": lambda: network_online(),
        },

        "system": {
            "os": lambda: os.name,
            "username": lambda: getpass.getuser(),
            "cwd": lambda: os.getcwd(),
            "run": lambda x:
                subprocess.call(x, shell=True),
            "env": lambda x:
                os.environ.get(str(x), ""),
            "cd": lambda x:
                os.chdir(str(x)),
        },

        "files": {
            "exists": lambda x:
                os.path.exists(str(x)),
            "size": lambda x:
                os.path.getsize(str(x)),
        }
    }


modules = load_standard_modules()


# ============================================================
# ARGUMENT PARSER
# ============================================================

def split_arguments(text):

    args = []
    current = ""
    depth = 0
    quote = None

    for char in text:

        if quote:

            current += char

            if char == quote:
                quote = None

        else:

            if char in ['"', "'"]:

                quote = char
                current += char

            elif char in "([{":

                depth += 1
                current += char

            elif char in ")]}":

                depth -= 1
                current += char

            elif char == "," and depth == 0:

                args.append(current.strip())
                current = ""

            else:

                current += char

    if current.strip():
        args.append(current.strip())

    return args


# ============================================================
# CUSTOM MODULES
# ============================================================

def load_custom_module(module_name):

    current_folder = os.path.dirname(
        os.path.abspath(current_program)
    )

    module_path = os.path.join(
        current_folder,
        module_name.replace(".", os.sep) + ".nova"
    )

    if not os.path.exists(module_path):
        return None

    old_variables = variables.copy()
    old_functions = functions.copy()
    old_classes = classes.copy()

    variables.clear()
    functions.clear()
    classes.clear()

    try:

        with open(
            module_path,
            "r",
            encoding="utf-8"
        ) as file:

            module_lines = file.readlines()

        execute_lines(module_lines)

        contents = {}

        for name, value in variables.items():
            contents[name] = value

        for name, value in functions.items():
            contents[name] = ("function", value)

        for name, value in classes.items():
            contents[name] = value

        return contents

    finally:

        variables.clear()
        variables.update(old_variables)

        functions.clear()
        functions.update(old_functions)

        classes.clear()
        classes.update(old_classes)


# ============================================================
# FUNCTIONS
# ============================================================

def call_function(name, args):

    if name not in functions:
        raise Exception(
            f"Unknown function '{name}'."
        )

    params, body = functions[name]

    if len(args) != len(params):

        raise Exception(
            f"Function '{name}' expects "
            f"{len(params)} argument(s)."
        )

    old_variables = variables.copy()

    for param, value in zip(params, args):
        variables[param] = value

    result = execute_lines(body)

    variables.clear()
    variables.update(old_variables)

    return result


# ============================================================
# METHODS
# ============================================================

def call_method(obj, method_name, args):

    method = obj.nova_class.get_method(
        method_name
    )

    params, body = method

    if len(args) != len(params):

        raise Exception(
            f"Method '{method_name}' expects "
            f"{len(params)} argument(s)."
        )

    global current_object

    old_variables = variables.copy()
    old_object = current_object

    current_object = obj

    for name, value in obj.properties.items():
        variables[name] = value

    for param, value in zip(params, args):
        variables[param] = value

    result = execute_lines(body)

    for name in obj.properties:

        if name in variables:
            obj.properties[name] = variables[name]

    variables.clear()
    variables.update(old_variables)

    current_object = old_object

    return result


# ============================================================
# GRAPHICS
# ============================================================

def graphics_require():
    if graphics_root is None or graphics_canvas is None:
        raise Exception(
            "Graphics window has not been created. "
            "Use 'window width height' first."
        )


def graphics_window(width, height):
    global graphics_root, graphics_canvas

    if graphics_root is not None:
        try:
            graphics_root.destroy()
        except Exception:
            pass

    graphics_root = tk.Tk()
    graphics_root.title("Nova")
    graphics_root.geometry(
        f"{int(width)}x{int(height)}"
    )

    graphics_canvas = tk.Canvas(
        graphics_root,
        width=int(width),
        height=int(height),
        bg="white"
    )
    graphics_canvas.pack()

    return graphics_root


def graphics_rectangle(x, y, width, height):
    graphics_require()
    graphics_canvas.create_rectangle(
        float(x),
        float(y),
        float(x) + float(width),
        float(y) + float(height),
        fill=graphics_color,
        outline=graphics_color
    )


def graphics_circle(x, y, radius):
    graphics_require()
    graphics_canvas.create_oval(
        float(x) - float(radius),
        float(y) - float(radius),
        float(x) + float(radius),
        float(y) + float(radius),
        fill=graphics_color,
        outline=graphics_color
    )


def graphics_line(x1, y1, x2, y2):
    graphics_require()
    graphics_canvas.create_line(
        float(x1),
        float(y1),
        float(x2),
        float(y2),
        fill=graphics_color
    )


def graphics_text(x, y, value):
    graphics_require()
    graphics_canvas.create_text(
        float(x),
        float(y),
        text=str(value),
        fill=graphics_color,
        anchor="nw"
    )


def graphics_show():
    graphics_require()
    graphics_root.mainloop()


def graphics_bind_key(key_name, body):
    graphics_require()

    key_map = {
        "space": "<space>",
        "enter": "<Return>",
        "escape": "<Escape>",
        "up": "<Up>",
        "down": "<Down>",
        "left": "<Left>",
        "right": "<Right>",
        "tab": "<Tab>",
    }

    sequence = key_map.get(
        key_name.lower(),
        f"<KeyPress-{key_name}>"
    )

    def callback(event):
        execute_lines(body)

    graphics_root.bind(sequence, callback)


def graphics_bind_click(action, body):
    graphics_require()

    button_map = {
        "left_click": "<Button-1>",
        "middle_click": "<Button-2>",
        "right_click": "<Button-3>",
        "scroll_up": "<Button-4>",
        "scroll_down": "<Button-5>",
    }

    sequence = button_map.get(action)

    if sequence is None:
        raise Exception(
            f"Unknown mouse action '{action}'."
        )

    def callback(event):
        execute_lines(body)

    graphics_root.bind(sequence, callback)


# ============================================================
# EXPRESSION EVALUATOR
# ============================================================

def evaluate(expression):

    expression = expression.strip()

    if expression == "":
        return ""

    expression = re.sub(
        r"\btrue\b",
        "True",
        expression
    )

    expression = re.sub(
        r"\bfalse\b",
        "False",
        expression
    )

    # --------------------------------------------------------
    # OBJECT METHOD
    # --------------------------------------------------------

    method_match = re.match(
        r"^([A-Za-z_][A-Za-z0-9_]*)"
        r"\.([A-Za-z_][A-Za-z0-9_]*)"
        r"\((.*)\)$",
        expression
    )

    if method_match:

        object_name = method_match.group(1)
        method_name = method_match.group(2)
        inside = method_match.group(3)

        if object_name in variables:

            obj = variables[object_name]

            if isinstance(obj, NovaObject):

                args = []

                if inside.strip():

                    for arg in split_arguments(inside):
                        args.append(evaluate(arg))

                return call_method(
                    obj,
                    method_name,
                    args
                )

    # --------------------------------------------------------
    # OBJECT PROPERTY
    # --------------------------------------------------------

    property_match = re.match(
        r"^([A-Za-z_][A-Za-z0-9_]*)"
        r"\.([A-Za-z_][A-Za-z0-9_]*)$",
        expression
    )

    if property_match:

        object_name = property_match.group(1)
        property_name = property_match.group(2)

        if object_name in variables:

            obj = variables[object_name]

            if isinstance(obj, NovaObject):
                return obj.get(property_name)

    # --------------------------------------------------------
    # VARIABLE
    # --------------------------------------------------------

    if expression in variables:
        return variables[expression]

    # --------------------------------------------------------
    # CURRENT OBJECT PROPERTY
    # --------------------------------------------------------

    if (
        current_object is not None
        and expression in current_object.properties
    ):

        return current_object.get(expression)

    # --------------------------------------------------------
    # STRING
    # --------------------------------------------------------

    if (
        len(expression) >= 2
        and expression[0] == '"'
        and expression[-1] == '"'
    ):

        return expression[1:-1]

    if (
        len(expression) >= 2
        and expression[0] == "'"
        and expression[-1] == "'"
    ):

        return expression[1:-1]

    # --------------------------------------------------------
    # FUNCTION / CLASS CALL
    # --------------------------------------------------------

    function_match = re.match(
        r"^([A-Za-z_][A-Za-z0-9_]*)"
        r"\((.*)\)$",
        expression
    )

    if function_match:

        name = function_match.group(1)
        inside = function_match.group(2)

        args = []

        if inside.strip():

            for arg in split_arguments(inside):
                args.append(evaluate(arg))

        if name in classes:

            return NovaObject(
                classes[name]
            )

        if name in functions:

            return call_function(
                name,
                args
            )

        # Standard modules

        for module in modules.values():

            if name in module:

                value = module[name]

                if (
                    isinstance(value, tuple)
                    and value[0] == "function"
                ):

                    params, body = value[1]

                    old_variables = variables.copy()

                    for param, value2 in zip(
                        params,
                        args
                    ):

                        variables[param] = value2

                    result = execute_lines(body)

                    variables.clear()
                    variables.update(old_variables)

                    return result

                if callable(value):
                    return value(*args)

                if not args:
                    return value

        # Built-ins

        if name == "str":

            return "".join(
                str(x)
                for x in args
            )

        if name == "number":

            try:

                value = float(args[0])

                if value.is_integer():
                    return int(value)

                return value

            except:

                raise Exception(
                    "Cannot convert to number."
                )

        if name == "integer":
            return int(float(args[0]))

        if name == "decimal":
            return float(args[0])

        if name == "text":
            return str(args[0])

        if name == "boolean":

            value = args[0]

            if isinstance(value, str):
                return value.lower() == "true"

            return bool(value)

        if name == "length":
            return len(args[0])

        if name == "contains":
            return args[1] in args[0]

        if name == "index":
            return args[0].index(args[1])

        if name == "keys":
            return list(args[0].keys())

        if name == "values":
            return list(args[0].values())

        if name == "has_key":
            return args[1] in args[0]

        if name == "sort":

            result = list(args[0])
            result.sort()

            if isinstance(args[0], list):
                args[0][:] = result

            return result

        if name == "reverse":

            if isinstance(args[0], list):

                args[0].reverse()
                return args[0]

            return list(reversed(args[0]))

        if name == "clear":

            args[0].clear()
            return None

        if name == "input":
            prompt = str(args[0]) if args else ""
            return input(prompt)

        if name == "async":
            raise Exception(
                "Use 'set task = async function(...)' "
                "to create an async task."
            )

        raise Exception(
            f"Unknown function '{name}'."
        )

    # --------------------------------------------------------
    # LIST
    # --------------------------------------------------------

    if (
        expression.startswith("[")
        and expression.endswith("]")
    ):

        inside = expression[1:-1]

        if not inside.strip():
            return []

        return [
            evaluate(x)
            for x in split_arguments(inside)
        ]

    # --------------------------------------------------------
    # DICTIONARY / SET
    # --------------------------------------------------------

    if (
        expression.startswith("{")
        and expression.endswith("}")
    ):

        inside = expression[1:-1]

        if not inside.strip():
            return {}

        parts = split_arguments(inside)

        if any(":" in x for x in parts):

            result = {}

            for item in parts:

                key, value = item.split(
                    ":",
                    1
                )

                result[evaluate(key)] = evaluate(value)

            return result

        return set(
            evaluate(x)
            for x in parts
        )

    # --------------------------------------------------------
    # INDEXING
    # --------------------------------------------------------

    index_match = re.match(
        r"^([A-Za-z_][A-Za-z0-9_]*)"
        r"\[(.+)\]$",
        expression
    )

    if index_match:

        name = index_match.group(1)

        index = evaluate(
            index_match.group(2)
        )

        if name in variables:
            return variables[name][index]

    # --------------------------------------------------------
    # VARIABLES IN EXPRESSIONS
    # --------------------------------------------------------

    expression = re.sub(
        r"\b[A-Za-z_][A-Za-z0-9_]*\b",
        lambda match:
        repr(
            variables[match.group(0)]
        )
        if match.group(0) in variables
        else match.group(0),
        expression
    )

    try:

        return eval(
            expression,
            {
                "__builtins__": {}
            },
            {}
        )

    except Exception:

        return expression


def evaluate_condition(condition):

    try:
        return bool(
            evaluate(condition)
        )

    except:
        return False


# ============================================================
# FILE WRITING
# ============================================================

def write_file(
    filename,
    text,
    line_number=None
):

    if line_number is None:

        with open(
            filename,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(text + "\n")

    else:

        if os.path.exists(filename):

            with open(
                filename,
                "r",
                encoding="utf-8"
            ) as file:

                lines = file.readlines()

        else:

            lines = []

        while len(lines) < line_number:
            lines.append("\n")

        lines[line_number - 1] = (
            text + "\n"
        )

        with open(
            filename,
            "w",
            encoding="utf-8"
        ) as file:

            file.writelines(lines)

# ============================================================
# EXECUTION ENGINE
# ============================================================

def execute_lines(lines):

    global current_object

    i = 0

    while i < len(lines):

        raw_line = lines[i]
        line = raw_line.strip()

        # ----------------------------------------------------
        # BLANK / COMMENT
        # ----------------------------------------------------

        if not line or line.startswith("#"):

            i += 1
            continue

        # ----------------------------------------------------
        # IMPORT
        # ----------------------------------------------------

        if (
            line.startswith("from ")
            and " import " in line
        ):

            match = re.match(
                r"from\s+([A-Za-z0-9_.]+)"
                r"\s+import\s+(.+)",
                line
            )

            if match:

                module_name = match.group(1)
                imported = match.group(2).strip()

                if module_name in modules:

                    module = modules[module_name]

                else:

                    module = load_custom_module(
                        module_name
                    )

                    if module is None:

                        raise Exception(
                            f"Module '{module_name}' "
                            f"not found."
                        )

                    modules[module_name] = module

                if imported == "*":

                    for name, value in module.items():
                        variables[name] = value

                else:

                    for name in split_arguments(imported):

                        name = name.strip()

                        if name not in module:

                            raise Exception(
                                f"'{name}' was not found "
                                f"in module "
                                f"'{module_name}'."
                            )

                        variables[name] = module[name]

            i += 1
            continue

        # ====================================================
        # CLASS
        # ====================================================

        if (
            line.startswith("class ")
            and line.endswith(":")
        ):

            header = line[6:-1].strip()

            if " extends " in header:

                class_name, parent_name = header.split(
                    " extends ",
                    1
                )

                class_name = class_name.strip()
                parent_name = parent_name.strip()

                if parent_name not in classes:

                    raise Exception(
                        f"Parent class "
                        f"'{parent_name}' not found."
                    )

                parent = classes[parent_name]

            else:

                class_name = header
                parent = None

            new_class = NovaClass(
                class_name,
                parent
            )

            i += 1

            while i < len(lines):

                class_line = lines[i]

                # Blank lines allowed
                if not class_line.strip():

                    i += 1
                    continue

                # Class body must be indented
                if not class_line.startswith("    "):
                    break

                content = class_line[4:].strip()

                # ------------------------------------------------
                # PROPERTY
                # ------------------------------------------------

                property_match = re.match(
                    r"^(str|int|float|bool)\s+"
                    r"([A-Za-z_][A-Za-z0-9_]*)"
                    r"(?:\s*=\s*(.*))?$",
                    content
                )

                if property_match:

                    property_type = (
                        property_match.group(1)
                    )

                    property_name = (
                        property_match.group(2)
                    )

                    value_text = (
                        property_match.group(3)
                    )

                    if value_text is not None:

                        value = evaluate(
                            value_text
                        )

                    elif property_type == "str":

                        value = ""

                    elif property_type == "int":

                        value = 0

                    elif property_type == "float":

                        value = 0.0

                    else:

                        value = False

                    new_class.properties[
                        property_name
                    ] = value

                    i += 1
                    continue

                # ------------------------------------------------
                # METHOD
                # ------------------------------------------------

                if (
                    content.startswith("def ")
                    and content.endswith(":")
                ):

                    method_header = (
                        content[4:-1].strip()
                    )

                    opening = (
                        method_header.find("(")
                    )

                    method_name = (
                        method_header[:opening].strip()
                    )

                    params_text = (
                        method_header[
                            opening + 1:
                        ].rsplit(
                            ")",
                            1
                        )[0]
                    )

                    if params_text.strip():

                        params = [
                            x.strip()
                            for x in params_text.split(",")
                        ]

                    else:

                        params = []

                    body = []

                    i += 1

                    while i < len(lines):

                        method_line = lines[i]

                        if method_line.startswith(
                            "        "
                        ):

                            body.append(
                                method_line[8:]
                            )

                            i += 1

                        elif not method_line.strip():

                            body.append(
                                method_line
                            )

                            i += 1

                        else:

                            break

                    new_class.methods[
                        method_name
                    ] = (
                        params,
                        body
                    )

                    continue

                i += 1

            classes[class_name] = new_class

            continue

        # ====================================================
        # SAY
        # ====================================================

        if (
            line.startswith("say(")
            and line.endswith(")")
        ):

            inside = line[4:-1]

            output = [
                evaluate(arg)
                for arg in split_arguments(inside)
            ]

            print(*output)

            i += 1
            continue

        # ====================================================
        # FUNCTION
        # ====================================================

        if (
            (
                line.startswith("def ")
                or line.startswith("async def ")
            )
            and line.endswith(":")
        ):

            if line.startswith("async def "):
                header = line[10:-1].strip()
            else:
                header = line[4:-1].strip()

            opening = header.find("(")

            name = header[:opening].strip()

            params_text = (
                header[
                    opening + 1:
                ].rsplit(
                    ")",
                    1
                )[0]
            )

            if params_text.strip():

                params = [
                    x.strip()
                    for x in params_text.split(",")
                ]

            else:

                params = []

            body = []

            i += 1

            while i < len(lines):

                if lines[i].startswith("    "):

                    body.append(
                        lines[i][4:]
                    )

                    i += 1

                elif not lines[i].strip():

                    i += 1

                else:

                    break

            functions[name] = (
                params,
                body
            )

            continue

        # ====================================================
        # PARALLEL
        # ====================================================

        if line == "parallel:":

            tasks = []
            i += 1

            while i < len(lines):

                if lines[i].startswith("    "):
                    command = lines[i][4:].strip()
                    tasks.append(command)
                    i += 1

                elif not lines[i].strip():
                    i += 1

                else:
                    break

            futures = []

            for command in tasks:
                futures.append(
                    async_executor.submit(
                        execute_lines,
                        [command]
                    )
                )

            for future in futures:
                future.result()

            continue

        # ====================================================
        # RETURN
        # ====================================================

        if line.startswith("return "):

            return evaluate(
                line[7:]
            )

        # ====================================================
        # IF / ELIF / ELSE
        # ====================================================

        if (
            line.startswith("if ")
            and line.endswith(":")
        ):

            branches = []

            condition = line[3:-1].strip()

            i += 1

            body = []

            while i < len(lines):

                if lines[i].startswith("    "):

                    body.append(
                        lines[i][4:]
                    )

                    i += 1

                else:

                    break

            branches.append(
                (condition, body)
            )

            while i < len(lines):

                next_line = lines[i].strip()

                if (
                    next_line.startswith("elif ")
                    and next_line.endswith(":")
                ):

                    condition = (
                        next_line[5:-1].strip()
                    )

                    i += 1

                    body = []

                    while i < len(lines):

                        if lines[i].startswith("    "):

                            body.append(
                                lines[i][4:]
                            )

                            i += 1

                        else:

                            break

                    branches.append(
                        (condition, body)
                    )

                elif next_line == "else:":

                    i += 1

                    body = []

                    while i < len(lines):

                        if lines[i].startswith("    "):

                            body.append(
                                lines[i][4:]
                            )

                            i += 1

                        else:

                            break

                    branches.append(
                        ("else", body)
                    )

                    break

                else:

                    break

            for condition, body in branches:

                if (
                    condition == "else"
                    or evaluate_condition(condition)
                ):

                    execute_lines(body)
                    break

            continue

        # ====================================================
        # REPEAT
        # ====================================================

        if (
            line.startswith("repeat ")
            and line.endswith(":")
        ):

            amount = evaluate(
                line[7:-1]
            )

            i += 1

            body = []

            while i < len(lines):

                if lines[i].startswith("    "):

                    body.append(
                        lines[i][4:]
                    )

                    i += 1

                else:

                    break

            for _ in range(int(amount)):

                execute_lines(body)

            continue

        # ====================================================
        # WHILE
        # ====================================================

        if (
            line.startswith("while ")
            and line.endswith(":")
        ):

            condition = line[6:-1].strip()

            i += 1

            body = []

            while i < len(lines):

                if lines[i].startswith("    "):

                    body.append(
                        lines[i][4:]
                    )

                    i += 1

                else:

                    break

            while evaluate_condition(
                condition
            ):

                execute_lines(body)

            continue

        # ====================================================
        # OBJECT PROPERTY SET
        # ====================================================

        property_set = re.match(
            r"^set\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)"
            r"\.([A-Za-z_][A-Za-z0-9_]*)"
            r"\s*=\s*(.*)$",
            line
        )

        if property_set:

            object_name = property_set.group(1)
            property_name = property_set.group(2)

            value = evaluate(
                property_set.group(3)
            )

            if object_name not in variables:

                raise Exception(
                    f"Object '{object_name}' "
                    f"not found."
                )

            obj = variables[
                object_name
            ]

            if not isinstance(
                obj,
                NovaObject
            ):

                raise Exception(
                    f"'{object_name}' "
                    f"is not an object."
                )

            obj.set(
                property_name,
                value
            )

            i += 1
            continue

        # ====================================================
        # INDEXED SET
        # ====================================================

        index_set = re.match(
            r"^set\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)"
            r"\[(.+)\]\s*=\s*(.*)$",
            line
        )

        if index_set:

            name = index_set.group(1)

            index = evaluate(
                index_set.group(2)
            )

            value = evaluate(
                index_set.group(3)
            )

            variables[name][index] = value

            i += 1
            continue

        # ====================================================
        # TYPED VARIABLE
        # ====================================================

        type_match = re.match(
            r"^(str|int|float|bool)\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)"
            r"\s*=\s*(.*)$",
            line
        )

        if type_match:

            variable_type = type_match.group(1)
            name = type_match.group(2)

            value = evaluate(
                type_match.group(3)
            )

            if variable_type == "str":
                value = str(value)

            elif variable_type == "int":
                value = int(value)

            elif variable_type == "float":
                value = float(value)

            elif variable_type == "bool":
                value = bool(value)

            variables[name] = value

            i += 1
            continue

       
        # ====================================================
        # READ FILE
        # ====================================================

        if line.startswith("set ") and " = read " in line:

            match = re.match(
                r"set\s+"
                r"([A-Za-z_][A-Za-z0-9_]*)"
                r"\s*=\s*read\s+"
                r"file\.(\S+)",
                line
            )

            if match:

                name = match.group(1)
                filename = match.group(2)

                if not os.path.exists(filename):

                    raise Exception(
                        f"File '{filename}' "
                        f"does not exist."
                    )

                with open(
                    filename,
                    "r",
                    encoding="utf-8"
                ) as file:

                    variables[name] = file.read()

                i += 1
                continue

        # ====================================================
        # READ SPECIFIC LINE
        # ====================================================

        if line.startswith("set ") and " = read(" in line:

            match = re.match(
                r"set\s+"
                r"([A-Za-z_][A-Za-z0-9_]*)"
                r"\s*=\s*read\((\d+)\)\s+"
                r"file\.(\S+)",
                line
            )

            if match:

                name = match.group(1)
                line_number = int(match.group(2))
                filename = match.group(3)

                if not os.path.exists(filename):

                    raise Exception(
                        f"File '{filename}' "
                        f"does not exist."
                    )

                with open(
                    filename,
                    "r",
                    encoding="utf-8"
                ) as file:

                    lines_in_file = file.readlines()

                if (
                    line_number < 1
                    or line_number > len(lines_in_file)
                ):

                    variables[name] = ""

                else:

                    variables[name] = (
                        lines_in_file[
                            line_number - 1
                        ].rstrip("\n")
                    )

                i += 1
                continue

        # ====================================================
        # EVENTS
        # ====================================================

        if (
            line.startswith("on ")
            and line.endswith(":")
        ):

            event_header = line[3:-1].strip()

            event_match = re.match(
                r"^keypress\(([^)]+)\)$",
                event_header
            )

            click_match = re.match(
                r"^click\(([^)]+)\)$",
                event_header
            )

            body = []
            i += 1

            while i < len(lines):

                if lines[i].startswith("    "):
                    body.append(lines[i][4:])
                    i += 1

                elif not lines[i].strip():
                    body.append(lines[i])
                    i += 1

                else:
                    break

            if event_match:
                graphics_bind_key(
                    event_match.group(1).strip(),
                    body
                )

            elif click_match:
                graphics_bind_click(
                    click_match.group(1).strip(),
                    body
                )

            else:
                raise Exception(
                    f"Unknown event '{event_header}'."
                )

            continue

        # ====================================================
        # GRAPHICS
        # ====================================================

        if line.startswith("window "):

            parts = line.split()

            if len(parts) != 3:
                raise Exception(
                    "window requires width and height."
                )

            graphics_window(
                evaluate(parts[1]),
                evaluate(parts[2])
            )

            i += 1
            continue

        if line.startswith("color "):

            globals()["graphics_color"] = str(
                evaluate(line[6:])
            )

            i += 1
            continue

        if line.startswith("rectangle "):

            parts = line.split()

            if len(parts) != 5:
                raise Exception(
                    "rectangle requires x y width height."
                )

            graphics_rectangle(
                evaluate(parts[1]),
                evaluate(parts[2]),
                evaluate(parts[3]),
                evaluate(parts[4])
            )

            i += 1
            continue

        if line.startswith("circle "):

            parts = line.split()

            if len(parts) != 4:
                raise Exception(
                    "circle requires x y radius."
                )

            graphics_circle(
                evaluate(parts[1]),
                evaluate(parts[2]),
                evaluate(parts[3])
            )

            i += 1
            continue

        if line.startswith("line "):

            parts = line.split()

            if len(parts) != 5:
                raise Exception(
                    "line requires x1 y1 x2 y2."
                )

            graphics_line(
                evaluate(parts[1]),
                evaluate(parts[2]),
                evaluate(parts[3]),
                evaluate(parts[4])
            )

            i += 1
            continue

        if line.startswith("text "):

            parts = line.split(maxsplit=3)

            if len(parts) == 4:
                graphics_text(
                    evaluate(parts[1]),
                    evaluate(parts[2]),
                    evaluate(parts[3])
                )

                i += 1
                continue

        if line == "show()":

            graphics_show()
            i += 1
            continue

        # ====================================================
        # ASYNC TASK CREATION
        # ====================================================

        async_set = re.match(
            r"^set\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)"
            r"\s*=\s*async\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)"
            r"\((.*)\)$",
            line
        )

        if async_set:

            task_name = async_set.group(1)
            function_name = async_set.group(2)
            inside = async_set.group(3)

            args = []

            if inside.strip():
                for arg in split_arguments(inside):
                    args.append(evaluate(arg))

            task = async_executor.submit(
                call_function,
                function_name,
                args
            )

            async_tasks[task_name] = task
            variables[task_name] = task

            i += 1
            continue

        # ====================================================
        # AWAIT
        # ====================================================

        await_set = re.match(
            r"^set\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)"
            r"\s*=\s*await\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)$",
            line
        )

        if await_set:

            result_name = await_set.group(1)
            task_name = await_set.group(2)

            if task_name not in async_tasks:
                raise Exception(
                    f"Async task '{task_name}' not found."
                )

            variables[result_name] = (
                async_tasks[task_name].result()
            )

            i += 1
            continue

        # ====================================================
        # NORMAL SET
        # ====================================================

        if line.startswith("set "):

            match = re.match(
                r"set\s+"
                r"([A-Za-z_][A-Za-z0-9_]*)"
                r"\s*=\s*(.*)",
                line
            )

            if match:

                name = match.group(1)

                value = evaluate(
                    match.group(2)
                )

                variables[name] = value

                i += 1
                continue

        # ====================================================
        # WRITE
        # ====================================================

        if line.startswith("write("):

            match = re.match(
                r'write\((\d+)\)\s+'
                r'file\.(\S+)\s+"(.*)"',
                line
            )

            if match:

                write_file(
                    match.group(2),
                    match.group(3),
                    int(match.group(1))
                )

                i += 1
                continue

        if line.startswith("write "):

            match = re.match(
                r'write\s+file\.(\S+)\s+"(.*)"',
                line
            )

            if match:

                write_file(
                    match.group(1),
                    match.group(2)
                )

                i += 1
                continue

        # ====================================================
        # APPEND
        # ====================================================

        if line.startswith("append "):

            match = re.match(
                r'append\s+file\.(\S+)\s+"(.*)"',
                line
            )

            if match:

                with open(
                    match.group(1),
                    "a",
                    encoding="utf-8"
                ) as file:

                    file.write(
                        match.group(2)
                    )

                i += 1
                continue

        # ====================================================
        # LOG
        # ====================================================

        if line.startswith("log file."):

            filename = line[9:]

            if not os.path.exists(filename):

                raise Exception(
                    f"File '{filename}' "
                    f"does not exist."
                )

            with open(
                filename,
                "r",
                encoding="utf-8"
            ) as file:

                print(
                    file.read(),
                    end=""
                )

            i += 1
            continue

        # ====================================================
        # DELETE FILE
        # ====================================================

        if line.startswith("delete file."):

            filename = line[12:]

            if not os.path.exists(filename):

                raise Exception(
                    f"File '{filename}' "
                    f"does not exist."
                )

            os.remove(filename)

            i += 1
            continue

        # ====================================================
        # CREATE FOLDER
        # ====================================================

        if line.startswith("create folder."):

            os.makedirs(
                line[14:],
                exist_ok=True
            )

            i += 1
            continue

        # ====================================================
        # DELETE FOLDER
        # ====================================================

        if line.startswith("delete folder."):

            folder = line[14:]

            if os.path.exists(folder):
                shutil.rmtree(folder)

            i += 1
            continue

        # ====================================================
        # RENAME
        # ====================================================

        if line.startswith("rename file."):

            parts = line.split()

            if len(parts) == 3:

                os.rename(
                    parts[1][5:],
                    parts[2][5:]
                )

                i += 1
                continue

        # ====================================================
        # INSERT
        # ====================================================

        if line.startswith("insert "):

            parts = line.split(
                maxsplit=3
            )

            if len(parts) == 4:

                name = parts[1]
                position = int(
                    evaluate(parts[2])
                )
                value = evaluate(parts[3])

                variables[name].insert(
                    position,
                    value
                )

                i += 1
                continue

        # ====================================================
        # ADD
        # ====================================================

        if line.startswith("add "):

            parts = line.split(
                maxsplit=2
            )

            if len(parts) == 3:

                name = parts[1]
                value = evaluate(parts[2])

                if isinstance(
                    variables[name],
                    set
                ):

                    variables[name].add(value)

                else:

                    variables[name].append(value)

                i += 1
                continue

        # ====================================================
        # REMOVE
        # ====================================================

        if line.startswith("remove "):

            parts = line.split(
                maxsplit=2
            )

            if len(parts) == 3:

                name = parts[1]
                value = evaluate(parts[2])

                if isinstance(
                    variables[name],
                    set
                ):

                    variables[name].remove(value)

                elif isinstance(
                    variables[name],
                    list
                ):

                    if isinstance(
                        value,
                        int
                    ):

                        variables[name].pop(value)

                    else:

                        variables[name].remove(value)

                i += 1
                continue

        # ====================================================
        # SORT
        # ====================================================

        if line.startswith("sort(") and line.endswith(")"):

            name = line[5:-1].strip()

            if name in variables:

                variables[name].sort()

            i += 1
            continue

        # ====================================================
        # REVERSE
        # ====================================================

        if line.startswith("reverse(") and line.endswith(")"):

            name = line[8:-1].strip()

            if name in variables:

                variables[name].reverse()

            i += 1
            continue

        # ====================================================
        # CLEAR
        # ====================================================

        if line.startswith("clear(") and line.endswith(")"):

            name = line[6:-1].strip()

            if name in variables:

                variables[name].clear()

            i += 1
            continue

        # ====================================================
        # INCREMENT
        # ====================================================

        if line.endswith("++"):

            variables[
                line[:-2].strip()
            ] += 1

            i += 1
            continue

        # ====================================================
        # DECREMENT
        # ====================================================

        if line.endswith("--"):

            variables[
                line[:-2].strip()
            ] -= 1

            i += 1
            continue

        # ====================================================
        # COMPOUND ASSIGNMENT
        # ====================================================

        compound = re.match(
            r"^([A-Za-z_][A-Za-z0-9_]*)"
            r"\s*(\+=|-=|\*=|/=)\s*(.*)$",
            line
        )

        if compound:

            name = compound.group(1)
            operator = compound.group(2)

            value = evaluate(
                compound.group(3)
            )

            if operator == "+=":
                variables[name] += value

            elif operator == "-=":
                variables[name] -= value

            elif operator == "*=":
                variables[name] *= value

            elif operator == "/=":
                variables[name] /= value

            i += 1
            continue

        # ====================================================
        # FUNCTION / METHOD CALL
        # ====================================================

        if re.match(
            r"^[A-Za-z_][A-Za-z0-9_]*"
            r"(?:\.[A-Za-z_][A-Za-z0-9_]*)?"
            r"\(.*\)$",
            line
        ):

            evaluate(line)

            i += 1
            continue

        # ====================================================
        # FALLBACK
        # ====================================================

        evaluate(line)

        i += 1


# ============================================================
# NOVA v0.8 CLI
# ============================================================

NOVA_VERSION = "0.8.0"


def nova_cli_help():
    print("Nova programming language")
    print()
    print("Usage:")
    print("  nova <file.nova>")
    print("  nova --version")
    print("  nova help")
    print()
    print("Commands:")
    print("  <file.nova>   Run a Nova program")
    print("  --version     Show the Nova version")
    print("  help          Show this help message")


def nova_cli():
    args = sys.argv[1:]

    if not args:
        nova_cli_help()
        return

    command = args[0].lower()

    if command in ("--version", "-v", "version"):
        print("Nova 0.8.0")
        return

    if command in ("help", "--help", "-h"):
        nova_cli_help()
        return

    filename = args[0]

    if not filename.lower().endswith(".nova"):
        print("Nova Error: expected a .nova source file.")
        print("Try: nova myprogram.nova")
        return

    if not os.path.isfile(filename):
        print(f"Nova Error: file '{filename}' not found.")
        return

    try:
        with open(filename, "r", encoding="utf-8") as file:
            lines = file.readlines()

        execute_lines(lines)

    except Exception as error:
        print(f"Nova Error: {error}")


if __name__ == "__main__":
    nova_cli()

