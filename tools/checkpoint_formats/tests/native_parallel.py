"""Run independent fresh-process checks without dropping failed sibling checks."""
from concurrent.futures import ThreadPoolExecutor

def checked_map(action, items):
    with ThreadPoolExecutor(max_workers=4) as pool:
        pending=[pool.submit(action,item) for item in items]
        results=[];errors=[]
        for future in pending:
            try:results.append(future.result())
            except BaseException as error:errors.append(error)
    if errors:raise errors[0]
    return results
