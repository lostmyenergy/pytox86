def factorial(n):
    if n <= 1:
        return 1
    else:
        return n * factorial(n - 1)

def iterative_factorial(n):
    result = 1
    while n > 1:
        result = result * n
        n = n - 1
    return result

def main():
    x = 5
    
    rec_result = factorial(x)
    iter_result = iterative_factorial(x)
    
    if rec_result == iter_result:
        return rec_result
    else:
        return 0
