from . import tools
import concurrent.futures
import json

TOOL_TIMEOUT_SECONDS = 30


def execute_tool(tool_name: str, parameters: dict, user=None, context: dict = None):
    """
    Routs the tool_name to the appropriate function in tools.py
    and returns its JSON string result.
    
    Smart-Injection: If data_source_id is missing from parameters but exists 
    in the context, it is automatically injected.
    """
    # 1. Smart-Injection logic
    if context and 'data_source_id' not in parameters:
        # If we have a context dictionary (or a string representing it)
        ds_id = None
        if isinstance(context, dict):
            ds_id = context.get('data_source_id')
        elif isinstance(context, str) and 'data_source_id":' in context:
            # Simple heuristic for string context
            import re
            match = re.search(r'"data_source_id":\s"?(\d+)"?', context)
            if match:
                ds_id = match.group(1)
        
        if ds_id:
            parameters['data_source_id'] = ds_id
        else:
            # Tek veri kaynağı olduğu için varsayılan olarak 1 enjekte et (Sessiz Enjeksiyon)
            parameters['data_source_id'] = 1

    func = getattr(tools, tool_name, None)
    if func and callable(func):
        try:
            import inspect
            sig = inspect.signature(func)
            valid_params = set(sig.parameters.keys())
            filtered = {k: v for k, v in parameters.items() if k in valid_params}
            if 'user' in valid_params:
                filtered['user'] = user

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, **filtered)
                try:
                    return future.result(timeout=TOOL_TIMEOUT_SECONDS)
                except concurrent.futures.TimeoutError:
                    error_data = {"status": "error", "tool": tool_name, "message": f"Tool zaman aşımına uğradı ({TOOL_TIMEOUT_SECONDS}s)"}
                    return json.dumps(error_data, ensure_ascii=False)
        except Exception as e:
            error_data = {"status": "error", "tool": tool_name, "message": str(e)}
            return json.dumps(error_data, ensure_ascii=False)
    error_data = {"status": "error", "message": f"Tool {tool_name} bulunamadı"}
    return json.dumps(error_data, ensure_ascii=False)

