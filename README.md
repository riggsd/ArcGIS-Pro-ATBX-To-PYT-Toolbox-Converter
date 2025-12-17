# ArcGIS Pro ATBX to PYT Toolbox Converter

A Python Toolbox (.pyt) for ArcGIS Pro that converts legacy .ATBX toolboxes to the more portable and editable Python Toolbox (.pyt) format.

## Overview

This tool helps migrate ArcGIS Pro toolboxes from the binary .ATBX format to Python Toolbox format, which offers several advantages:
- **Human-readable**: Python Toolboxes are plain text Python files
- **Version control friendly**: Easy to track changes in Git or other VCS
- **Portable**: Can be easily shared and edited without ArcGIS Pro
- **Extensible**: Direct access to Python code for customization

## Features

The converter extracts and translates:
- ✅ Toolbox metadata (name, alias, label)
- ✅ Tool definitions and descriptions
- ✅ Parameter definitions with all attributes:
  - Display names and internal names
  - Data types (folders, files, workspaces, strings, numbers, etc.)
  - Required/Optional status
  - File type filters
  - Parameter categories
  - Help descriptions
- ✅ Validation logic:
  - `initializeParameters()` - merged into `getParameterInfo()`
  - `updateParameters()` - parameter dependency logic
  - `updateMessages()` - custom validation messages
- ✅ Execute script references - identifies original implementation scripts

## Installation

1. Download or clone this repository
2. Open ArcGIS Pro
3. In the Catalog pane, navigate to the folder containing `ToolBoxConverter.pyt`
4. The toolbox will appear and can be added to your project

## Usage

1. **Open the Tool**: In ArcGIS Pro, Analysis -> Tools, expand the "Toolbox Converter" toolbox and double-click "ATBX to PYT Converter"

2. **Set Input**: Browse to your .ATBX toolbox file

3. **Set Output** (optional): Specify the output .pyt file path. If not specified, the tool will create a .pyt file with the same name as the input in the same directory.

4. **Run**: Click "Run" to perform the conversion

5. **Review Output**: The generated .pyt file will contain:
   - Complete toolbox structure
   - All tool definitions with parameters
   - Migrated validation logic
   - Stub execute() methods with TODO comments

## Post-Conversion Steps

The converter creates a fully functional toolbox skeleton, but **you must implement the execution logic** for each tool:

1. **Review the generated .pyt file** - Check that all parameters and validation logic were correctly migrated

2. **Implement execute() methods** - Each tool's `execute()` method contains:
   - A comment referencing the original script location (from `tool.script.execute.link`)
   - A warning message indicating that the implementation is needed
   - TODO markers for where to add your code
   - Hopefully your original tools are structured so that they can be imported from standalone .py files, but this depends entirely on the structure of your code

3. **Test the toolbox** - Verify parameters appear correctly and validation logic works as expected

4. **Migrate execution code** - Copy the logic from the original Python scripts referenced in the TODO comments into the `execute()` methods

## Technical Details

### What Gets Converted

The tool reads and parses the following files from the .ATBX archive:
- `toolbox.content` and `toolbox.content.rc` - Toolbox metadata
- `{ToolName}.tool/tool.content` and `tool.content.rc` - Tool metadata and parameters
- `{ToolName}.tool/tool.script.validate.py` - Validation logic
- `{ToolName}.tool/tool.script.execute.link` - Reference to execution script

### Validation Code Migration

The converter automatically migrates validation methods:

- **initializeParameters()** → Inserted into `getParameterInfo()` after parameter creation
- **updateParameters()** → Copied to `updateParameters()` with variable name adjustments
- **updateMessages()** → Copied to `updateMessages()` with variable name adjustments

The code transformation includes:
- Replacing `self.params` with `parameters` (or `params` in getParameterInfo)
- Adjusting indentation levels
- Preserving all logic and comments

### Limitations

- **Execute methods are not converted**: The original Python scripts are separate files and must be manually migrated
- **Complex parameter types**: Some advanced parameter types (GPValueTable with domains) may need manual adjustment
- **Custom Python imports**: Any imports in the original scripts must be added to the .pyt file
- **Toolsets**: Only processes tools in the root toolset (`<root>`)

## License

MIT
