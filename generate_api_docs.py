import re
import ast
import os

file_content = open('app/mcp/api_docs.py').read()

mcp_methods_start_tag = '"mcp_methods": {'
start_index = file_content.find(mcp_methods_start_tag)

documentation_output = []

if start_index != -1:
    start_index += len(mcp_methods_start_tag) - 1 # Adjust to point to the opening brace

    brace_count = 1
    current_index = start_index + 1
    end_index = -1

    while current_index < len(file_content):
        char = file_content[current_index]
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
        
        if brace_count == 0:
            end_index = current_index
            break
        current_index += 1
    
    if end_index != -1:
        mcp_methods_str = file_content[start_index : end_index + 1]
        
        try:
            # ast.literal_eval expects a valid Python literal.
            # The extracted string should be a dictionary literal.
            # Fix double quotes to single quotes for dictionary keys as ast.literal_eval expects.
            # Example: "key": "value" -> 'key': "value"
            # It should also handle cases where values are strings with double quotes.
            # This is complex, let's try a simpler approach if ast.literal_eval struggles.
            
            # The string `mcp_methods_str` likely has keys like "key": value and values like "string"
            # ast.literal_eval handles double quoted strings as values, but not keys with double quotes directly
            # without converting them to single quotes if they are identifiers.
            # So, only convert keys that look like simple identifiers.
            mcp_methods_str_fixed_keys = re.sub(r'"([a-zA-Z_][a-zA-Z0-9_.]*)":', r"'\1':", mcp_methods_str)

            mcp_methods = ast.literal_eval(mcp_methods_str_fixed_keys)

            for method_name, method_info in sorted(mcp_methods.items()):
                description = method_info.get("description", "No description available.").strip()
                
                # Format parameters if available
                params_str = ""
                parameters = method_info.get("parameters")
                if parameters:
                    params_str += "\n    Parameters:\n"
                    for param_name, param_details in parameters.items():
                        param_type = param_details.get("type", "unknown")
                        param_required = " (required)" if param_details.get("required") else ""
                        param_desc = param_details.get("description", "")
                        param_default = f" (default: {param_details.get('default')})" if "default" in param_details else ""
                        # Handle potential enum values for parameters
                        param_enum = f" (enum: {', '.join(param_details.get('enum'))})" if param_details.get('enum') else ""
                        params_str += f"      - {param_name} ({param_type}{param_required}{param_enum}): {param_desc}{param_default}\n"
                
                returns_str = ""
                returns = method_info.get("returns")
                if returns:
                    returns_str += "\n    Returns:\n"
                    for return_name, return_desc in returns.items():
                        returns_str += f"      - {return_name}: {return_desc}\n"

                documentation_output.append(
                    f"MCP Method: {method_name}\n"
                    f"  Description: {description}{params_str}{returns_str}\n"
                )
        except (ValueError, SyntaxError) as e:
            documentation_output.append(f"Error parsing mcp_methods section with ast.literal_eval: {e}\n")
            documentation_output.append(f"Raw mcp_methods string (fixed keys): {mcp_methods_str_fixed_keys}\n")
    else:
        documentation_output.append("Could not find closing brace for mcp_methods section.\n")
else:
    documentation_output.append("mcp_methods section not found in API_DOCUMENTATION.\n")

output_file_path = 'api-documentation.log'
with open(output_file_path, 'w') as f:
    f.write(''.join(documentation_output))

print(f"API documentation generated and saved to {output_file_path}")