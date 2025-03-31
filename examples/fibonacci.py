def fibonacci(n):
    if n <= 1:
        return n
    else:
        return fibonacci(n-1) + fibonacci(n-2)

def main():
    n = 10
    result = 0
    
    for i in range(n + 1):
        result = fibonacci(i)
        
    return result
