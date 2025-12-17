# ArcGIS Pro ATBX to PYT Toolbox Converter

A Python tool for ArcGIS Pro that converts .ATBX Toolboxes to the more portable and editable .PYT Python Toolbox format.

This tool lets you take advantage of the convenient GUI for creating Tools and managing their Parameters by initially creating Script Tools in an .ATBX Toolbox. Once you've dialed in all the Parameters, their attributes, and even ToolValidator validation logic, you can convert to Python Tools in a .PYT Python Toolbox. A Python Toolbox is entirely written in Python and *may* be maintained and distributed as a single Python file, while an .ATBX Toolbox requires maintaining an opaque binary file alongside your .PY scripts.

Be warned that you will be responsible for adding the `execute()` method implementations to each Tool, since this converter doesn't attempt to change the .PY source for your Script Tools. You may choose to migrate their entire implementations into the .PYT file, or you may choose to `import` their contents from .PY scripts in the same folder. 

It's also possible that some custom ToolValidator code may not be imported perfectly, since Parameter validation supports arbitrary Python code. If you've kept your ToolValidator simple and based on ESRI's template class using an indexed list of `self.params`, then this importer should migrate your logic reasonably.


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
   - Stub `execute()` methods with TODO comments


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



## Limitations

- **Execute methods are not converted**: The original Python scripts are separate files and must be manually migrated
- **Complex parameter types**: Some advanced parameter types (GPValueTable with domains) may need manual adjustment
- **Custom Python imports**: Any imports in the original scripts must be added to the .pyt file
- **Toolsets**: Only processes tools in the root toolset (`<root>`)

This tool is a quick hack to support my own needs, but I hope it can be useful for others as well.


## License

MIT
