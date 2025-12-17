# -*- coding: utf-8 -*-

import arcpy
import zipfile
import json
import os


class AtbxReader:
    """Helper class to read and parse ATBX toolbox files."""

    def __init__(self, atbx_path):
        self.atbx_path = atbx_path
        self.zip_ref = None

    def __enter__(self):
        self.zip_ref = zipfile.ZipFile(self.atbx_path, 'r')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.zip_ref:
            self.zip_ref.close()

    def read_json(self, filepath):
        """Read and parse a JSON file from the archive."""
        with self.zip_ref.open(filepath) as f:
            return json.load(f)

    def read_text(self, filepath):
        """Read a text file from the archive."""
        try:
            with self.zip_ref.open(filepath) as f:
                return f.read().decode('utf-8')
        except KeyError:
            return None

    def resolve_rc(self, value, rc_map):
        """Resolve $rc: references to actual values."""
        if isinstance(value, str) and value.startswith("$rc:"):
            key = value[4:]  # Remove "$rc:" prefix
            return rc_map.get(key, value)
        return value

    def get_toolbox_metadata(self):
        """Extract toolbox metadata."""
        content = self.read_json("toolbox.content")
        content_rc = self.read_json("toolbox.content.rc")
        rc_map = content_rc.get("map", {})

        return {
            "alias": content.get("alias", ""),
            "label": self.resolve_rc(content.get("displayname", ""), rc_map),
            "tools": content.get("toolsets", {}).get("<root>", {}).get("tools", [])
        }

    def get_tool_metadata(self, tool_name):
        """Extract tool metadata."""
        tool_dir = f"{tool_name}.tool/"
        content = self.read_json(f"{tool_dir}tool.content")
        content_rc = self.read_json(f"{tool_dir}tool.content.rc")
        rc_map = content_rc.get("map", {})

        # Read validation code if it exists
        validation_code = self.read_text(f"{tool_dir}tool.script.validate.py")
        validation_methods = None
        if validation_code:
            validation_methods = self.parse_validation_methods(validation_code)

        # Read execute script link if it exists
        execute_link = self.read_text(f"{tool_dir}tool.script.execute.link")
        if execute_link:
            execute_link = execute_link.strip()

        return {
            "name": tool_name,
            "label": self.resolve_rc(content.get("displayname", ""), rc_map),
            "description": self.resolve_rc(content.get("description", ""), rc_map),
            "params": content.get("params", {}),
            "rc_map": rc_map,
            "validation": validation_methods,
            "execute_script": execute_link
        }

    def parse_validation_methods(self, code):
        """Extract method bodies from ToolValidator class."""
        methods = {
            "initializeParameters": None,
            "updateParameters": None,
            "updateMessages": None
        }

        lines = code.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]

            # Look for method definitions
            for method_name in methods.keys():
                if f"def {method_name}(self):" in line:
                    # Extract the method body
                    method_lines = []
                    i += 1
                    # Get the base indentation of the method body
                    while i < len(lines):
                        current_line = lines[i]
                        stripped = current_line.strip()

                        # Stop if we hit another method or class definition
                        if current_line.strip() and not current_line.startswith(' '):
                            break
                        if stripped.startswith('def '):
                            break

                        # Add non-comment, non-docstring lines to method body
                        if stripped and not stripped.startswith('#'):
                            # Skip return statements that are just "return"
                            if stripped != "return":
                                method_lines.append(current_line)

                        i += 1

                    if method_lines:
                        methods[method_name] = method_lines
                    break
            i += 1

        return methods


class PytGenerator:
    """Helper class to generate Python Toolbox code."""

    def __init__(self):
        self.lines = []

    def add(self, line="", indent=0):
        """Add a line with proper indentation."""
        if line:
            self.lines.append("    " * indent + line)
        else:
            self.lines.append("")

    def generate_header(self):
        """Generate the file header."""
        self.add("# -*- coding: utf-8 -*-")
        self.add()
        self.add("import arcpy")
        self.add()
        self.add()

    def generate_toolbox_class(self, metadata):
        """Generate the Toolbox class."""
        self.add("class Toolbox:")
        self.add("def __init__(self):", 1)
        self.add('"""Define the toolbox (the name of the toolbox is the name of the', 2)
        self.add('.pyt file)."""', 2)
        self.add(f'self.label = "{metadata["label"]}"', 2)
        self.add(f'self.alias = "{metadata["alias"]}"', 2)
        self.add()
        self.add("# List of tool classes associated with this toolbox", 2)

        # Build the tools list
        tool_classes = [f"{tool}Tool" for tool in metadata["tools"]]
        self.add(f'self.tools = [{", ".join(tool_classes)}]', 2)
        self.add()
        self.add()

    def map_datatype(self, gp_type):
        """Map GP datatype to arcpy Parameter datatype string."""
        type_map = {
            "DEFolder": "DEFolder",
            "DEFile": "DEFile",
            "DEWorkspace": "DEWorkspace",
            "GPString": "GPString",
            "GPDouble": "GPDouble",
            "GPLong": "GPLong",
            "GPMultiValue": "GPMultiValue",
            "GPValueTable": "GPValueTable"
        }
        return type_map.get(gp_type, "GPString")

    def generate_parameter(self, param_name, param_info, rc_map, param_index):
        """Generate code for a single parameter."""
        # Determine if required or optional
        param_type = "Required" if param_info.get("type") != "optional" else "Optional"

        # Get display name
        display_name_raw = param_info.get("displayname", param_name)
        display_name = rc_map.get(display_name_raw[4:], param_name) if display_name_raw.startswith("$rc:") else display_name_raw

        # Get datatype
        datatype_info = param_info.get("datatype", {})
        datatype = self.map_datatype(datatype_info.get("type", "GPString"))

        # Get description if available
        description_raw = param_info.get("description", "")
        description = rc_map.get(description_raw[4:], "") if description_raw.startswith("$rc:") else description_raw
        # Strip XML tags from description
        if description:
            description = description.replace("<xdoc>", "").replace("</xdoc>", "")
            description = description.replace("<p>", "").replace("</p>", "")
            description = description.replace("<span>", "").replace("</span>", "")
            description = description.strip()

        # Get category if available
        category_raw = param_info.get("category", "")
        category = rc_map.get(category_raw[4:], "") if category_raw.startswith("$rc:") else category_raw

        self.add(f"param{param_index} = arcpy.Parameter(", 2)
        self.add(f'displayName="{display_name}",', 3)
        self.add(f'name="{param_name}",', 3)
        self.add(f'datatype="{datatype}",', 3)
        self.add(f'parameterType="{param_type}",', 3)
        self.add('direction="Input")', 3)

        # Add filter for file types
        if "domain" in param_info:
            domain = param_info["domain"]
            if domain.get("type") == "GPFileDomain":
                filetypes = domain.get("filetypes", [])
                if filetypes:
                    self.add(f'param{param_index}.filter.list = {filetypes}', 2)

        # Add category
        if category:
            self.add(f'param{param_index}.category = "{category}"', 2)

        # Add description
        if description:
            # Escape double quotes in description
            description = description.replace('"', '\\"')
            self.add(f'param{param_index}.description = "{description}"', 2)

        self.add()

    def transform_validation_code(self, code_lines, target_var="parameters"):
        """Transform validation code from ToolValidator to Tool class format."""
        transformed = []
        for line in code_lines:
            # Replace self.params with the target variable
            new_line = line.replace("self.params", target_var)
            # Dedent by one level (remove 4 spaces) since we're moving from ToolValidator to Tool method
            if new_line.startswith("        "):
                new_line = new_line[4:]
            transformed.append(new_line)
        return transformed

    def generate_tool_class(self, metadata):
        """Generate a Tool class."""
        tool_name = metadata["name"]
        class_name = f"{tool_name}Tool"
        validation = metadata.get("validation")

        self.add(f"class {class_name}:")
        self.add("def __init__(self):", 1)
        self.add('"""Define the tool (tool name is the name of the class)."""', 2)
        self.add(f'self.label = "{metadata["label"]}"', 2)
        self.add(f'self.description = "{metadata["description"]}"', 2)
        self.add()

        # Generate getParameterInfo
        self.add("def getParameterInfo(self):", 1)
        self.add('"""Define the tool parameters."""', 2)

        params = metadata["params"]
        rc_map = metadata["rc_map"]

        if params:
            # Generate each parameter
            for idx, (param_name, param_info) in enumerate(params.items()):
                self.generate_parameter(param_name, param_info, rc_map, idx)

            # Create params list
            param_list = ", ".join([f"param{i}" for i in range(len(params))])
            self.add(f"params = [{param_list}]", 2)
            self.add()

            # Insert initializeParameters code if it exists
            if validation and validation.get("initializeParameters"):
                self.add("# Validation code from initializeParameters", 2)
                init_code = self.transform_validation_code(validation["initializeParameters"], "params")
                for line in init_code:
                    if line.strip():
                        self.add(line, 2)
                self.add()

            self.add("return params", 2)
        else:
            self.add("return []", 2)

        self.add()

        # Generate isLicensed - always as a stub
        # NOTE: isLicensed and postExecute are commented out by default in ATBX templates
        # and rarely used. They are included here for completeness but as stubs.
        self.add("def isLicensed(self):", 1)
        self.add('"""Set whether the tool is licensed to execute."""', 2)
        self.add("return True", 2)
        self.add()

        # Generate updateParameters
        self.add("def updateParameters(self, parameters):", 1)
        self.add('"""Modify the values and properties of parameters before internal', 2)
        self.add('validation is performed.  This method is called whenever a parameter', 2)
        self.add('has been changed."""', 2)

        if validation and validation.get("updateParameters"):
            # Insert validation code
            update_code = self.transform_validation_code(validation["updateParameters"], "parameters")
            for line in update_code:
                if line.strip():
                    self.add(line, 2)
        else:
            self.add("return", 2)

        self.add()

        # Generate updateMessages
        self.add("def updateMessages(self, parameters):", 1)
        self.add('"""Modify the messages created by internal validation for each tool', 2)
        self.add('parameter. This method is called after internal validation."""', 2)

        if validation and validation.get("updateMessages"):
            # Insert validation code
            messages_code = self.transform_validation_code(validation["updateMessages"], "parameters")
            for line in messages_code:
                if line.strip():
                    self.add(line, 2)
        else:
            self.add("return", 2)

        self.add()

        # Generate execute
        self.add("def execute(self, parameters, messages):", 1)
        self.add('"""The source code of the tool."""', 2)

        # Add warning and reference to original script if it exists
        execute_script = metadata.get("execute_script")
        if execute_script:
            self.add(f'# TODO: Implement tool execution logic here', 2)
            self.add(f'# Original script was located at: {execute_script}', 2)
            self.add(f'# You will need to migrate that code into this method.', 2)
            self.add(f'arcpy.AddWarning("Tool execution not yet implemented. See original script: {execute_script}")', 2)
        else:
            self.add("# TODO: Implement tool execution logic here", 2)
            self.add('arcpy.AddWarning("Tool execution not yet implemented.")', 2)

        self.add("return", 2)
        self.add()

        # Generate postExecute
        self.add("def postExecute(self, parameters):", 1)
        self.add('"""This method takes place after outputs are processed and', 2)
        self.add('added to the display."""', 2)
        self.add("return", 2)
        self.add()
        self.add()

    def get_code(self):
        """Get the generated code as a string."""
        return "\n".join(self.lines)


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox Converter"
        self.alias = "ToolboxConverter"

        # List of tool classes associated with this toolbox
        self.tools = [AtbxToPytConverterTool]


class AtbxToPytConverterTool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "ATBX to PYT Converter"
        self.description = "This tool converts an .ATBX Toolbox to .PYT Python Toolbox "

    def getParameterInfo(self):
        """Define the tool parameters."""
        # Input ATBX Toolbox parameter (required)
        param0 = arcpy.Parameter(
            displayName="Input ATBX Toolbox",
            name="input_atbx",
            datatype="DEFile",
            parameterType="Required",
            direction="Input")
        param0.filter.list = ["atbx"]
        param0.description = "The source .ATBX toolbox to convert to Python Toolbox format."

        # Output PYT Toolbox parameter (optional)
        param1 = arcpy.Parameter(
            displayName="Output PYT Toolbox",
            name="output_pyt",
            datatype="DEFile",
            parameterType="Optional",
            direction="Output")
        param1.filter.list = ["pyt"]
        param1.description = "The output .PYT Python Toolbox file. If not specified, uses the same name as the input toolbox with .pyt extension."

        params = [param0, param1]
        return params

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        # Get parameters
        input_atbx = parameters[0].valueAsText
        output_pyt = parameters[1].valueAsText

        # If output path not specified, use same name as input with .pyt extension
        if not output_pyt:
            output_pyt = os.path.splitext(input_atbx)[0] + ".pyt"

        arcpy.AddMessage(f"Converting: {input_atbx}")
        arcpy.AddMessage(f"Output: {output_pyt}")
        arcpy.AddMessage("-" * 60)

        # Read ATBX and generate PYT code
        with AtbxReader(input_atbx) as reader:
            # Get toolbox metadata
            toolbox_meta = reader.get_toolbox_metadata()
            arcpy.AddMessage(f"Toolbox: {toolbox_meta['label']}")

            # Initialize code generator
            generator = PytGenerator()
            generator.generate_header()
            generator.generate_toolbox_class(toolbox_meta)

            # Generate each tool class
            for tool_name in toolbox_meta["tools"]:
                arcpy.AddMessage(f"Processing tool: {tool_name}")
                tool_meta = reader.get_tool_metadata(tool_name)
                generator.generate_tool_class(tool_meta)

        # Write the generated code to file
        generated_code = generator.get_code()
        with open(output_pyt, 'w', encoding='utf-8') as f:
            f.write(generated_code)

        arcpy.AddMessage("-" * 60)
        arcpy.AddMessage(f"Conversion complete! Generated: {output_pyt}")

        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
