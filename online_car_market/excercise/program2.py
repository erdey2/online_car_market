
def add(x, y):
    return x + y
def subtract(x, y):
    return x - y
def multiply(x, y):
    return x * y
def divide(x, y):
    if x == 0:
        return "Error: Cannot divide by zero"
    return x / y

num1 = int(input("enter the first number: "))
num2 = int(input("enter a second number: "))
result = 0
op = input("enter an operation + for addition - for subtraction * for multiplication \ for division: ")
if op == '+':
    result = add(num1, num2)
elif op == '-':
    result = subtract(num1, num2)
elif op == '*':
    result = multiply(num1, num2)
elif op == '/':
    result = divide(num1, num2)
else:
    print("wrong operator")
print('result: ', result)
print(num1, op, num2, ' = ', result)
