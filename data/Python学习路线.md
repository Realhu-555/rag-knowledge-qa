# Python 学习路线

> 适合有 Java 基础的学习者，结合 Agent 开发和数据分析方向
> 预计总时长：2-3 个月（每天 2-3 小时）

---

## 目录

- [第一阶段：Python 核心语法](#第一阶段python-核心语法1-2周)
- [第二阶段：Python 进阶](#第二阶段python-进阶2-3周)
- [第三阶段：实用技能](#第三阶段实用技能3-4周)
- [第四阶段：高级主题](#第四阶段高级主题按需学习)
- [学习资源推荐](#学习资源推荐)
- [实战项目建议](#实战项目建议)
- [学习方法建议](#学习方法建议)

---

## 第一阶段：Python 核心语法（1-2周）

> 有 Java 基础，这部分重点是"Python 思维"而不是语法差异

### 1.1 基础语法

#### 变量和数据类型

```python
# Python 是动态类型，不需要声明类型
name = "莫斯"           # str
age = 25                # int
height = 1.75           # float
is_student = True       # bool

# Java 对比：
# String name = "莫斯";
# int age = 25;
# Python 更简洁，不需要类型声明
```

#### 数据类型详解

```python
# 数字类型
integer_num = 42            # int，无大小限制
float_num = 3.14            # float
complex_num = 1 + 2j        # complex，复数

# 字符串（不可变序列）
s1 = '单引号字符串'
s2 = "双引号字符串"
s3 = """多行字符串
第二行
第三行"""

# 布尔值
is_valid = True
is_empty = False

# None 类型（类似 Java 的 null）
result = None
```

#### 字符串格式化（f-string）

```python
name = "莫斯"
age = 25

# f-string（推荐，Python 3.6+）
print(f"我叫{name}，今年{age}岁")

# format 方法
print("我叫{}，今年{}岁".format(name, age))

# % 格式化（旧式，了解即可）
print("我叫%s，今年%d岁" % (name, age))

# f-string 支持表达式
print(f"明年{age + 1}岁")
print(f"名字长度：{len(name)}")
```

#### 缩进规则

```python
# Python 用缩进代替花括号，缩进必须一致（推荐 4 个空格）

# 正确示例
if True:
    print("缩进4个空格")
    print("同一代码块保持相同缩进")

# 错误示例（混合缩进会报错）
if True:
    print("4个空格")
  print("2个空格")  # IndentationError

# 嵌套缩进
for i in range(3):
    if i > 1:
        print(f"大于1: {i}")
```

### 1.2 数据结构

#### 列表（List）- 最常用

```python
# 创建列表
fruits = ["苹果", "香蕉", "橙子"]
mixed = [1, "hello", 3.14, True]  # 可以混合类型

# 访问元素
print(fruits[0])       # "苹果"（索引从0开始）
print(fruits[-1])      # "橙子"（负索引：从末尾开始）
print(fruits[1:3])     # ["香蕉", "橙子"]（切片）

# 修改元素
fruits[0] = "草莓"

# 添加元素
fruits.append("葡萄")          # 末尾添加
fruits.insert(1, "芒果")       # 指定位置插入
fruits.extend(["西瓜", "桃子"]) # 扩展列表

# 删除元素
fruits.remove("香蕉")  # 按值删除
del fruits[0]          # 按索引删除
popped = fruits.pop()  # 弹出最后一个

# 列表长度
print(len(fruits))

# 列表推导式（Python 特有，很强大）
squares = [x**2 for x in range(10)]  # [0, 1, 4, 9, 16, ...]
evens = [x for x in range(10) if x % 2 == 0]  # [0, 2, 4, 6, 8]

# Java 对比：
# List<String> fruits = new ArrayList<>();
# fruits.add("苹果");
# Python 的列表更灵活，推导式更简洁
```

#### 字典（Dict）- 键值对

```python
# 创建字典
person = {
    "name": "莫斯",
    "age": 25,
    "skills": ["Python", "AI"]
}

# 访问值
print(person["name"])           # "莫斯"
print(person.get("email", "无")) # 不存在返回默认值

# 修改/添加
person["email"] = "mosi@example.com"
person.update({"phone": "123", "city": "北京"})

# 删除
del person["phone"]
email = person.pop("email", None)

# 遍历
for key, value in person.items():
    print(f"{key}: {value}")

# 字典推导式
squares_dict = {x: x**2 for x in range(5)}
# {0: 0, 1: 1, 2: 4, 3: 9, 4: 16}

# 嵌套字典
users = {
    "user1": {"name": "张三", "age": 25},
    "user2": {"name": "李四", "age": 30}
}
print(users["user1"]["name"])  # "张三"
```

#### 元组（Tuple）- 不可变序列

```python
# 创建元组（不可修改）
point = (10, 20)
single = (42,)  # 单元素元组需要逗号

# 访问
print(point[0])  # 10

# 解包
x, y = point
print(x, y)  # 10 20

# 用途：函数返回多个值、作为字典的键
def get_min_max(numbers):
    return min(numbers), max(numbers)

low, high = get_min_max([3, 1, 4, 1, 5])
```

#### 集合（Set）- 无序不重复

```python
# 创建集合
fruits = {"苹果", "香蕉", "橙子"}
numbers = set([1, 2, 2, 3, 3, 4])  # {1, 2, 3, 4}

# 添加/删除
fruits.add("葡萄")
fruits.discard("香蕉")  # 不存在不报错

# 集合运算
a = {1, 2, 3, 4}
b = {3, 4, 5, 6}

print(a & b)  # 交集 {3, 4}
print(a | b)  # 并集 {1, 2, 3, 4, 5, 6}
print(a - b)  # 差集 {1, 2}
print(a ^ b)  # 对称差集 {1, 2, 5, 6}

# 去重
numbers = [1, 2, 2, 3, 3, 4]
unique = list(set(numbers))  # [1, 2, 3, 4]
```

### 1.3 控制流

#### 条件语句

```python
age = 18

# if-elif-else
if age < 18:
    print("未成年")
elif age == 18:
    print("刚成年")
else:
    print("成年")

# 三元表达式（比 Java 简洁）
status = "成年" if age >= 18 else "未成年"
print(status)

# 多条件
if 0 < age < 100:  # Python 支持链式比较
    print("有效年龄")

# Java 对比：
# String status = (age >= 18) ? "成年" : "未成年";
# Python 的三元表达式更易读
```

#### 循环

```python
# for 循环（Python 的 for 更像 for-each）
fruits = ["苹果", "香蕉", "橙子"]

for fruit in fruits:
    print(fruit)

# range 函数
for i in range(5):          # 0, 1, 2, 3, 4
    print(i)

for i in range(1, 10, 2):   # 1, 3, 5, 7, 9（步长为2）
    print(i)

# 带索引遍历
for index, fruit in enumerate(fruits):
    print(f"{index}: {fruit}")

# while 循环
count = 0
while count < 5:
    print(count)
    count += 1  # Python 没有 ++ 运算符

# break 和 continue
for i in range(10):
    if i == 3:
        continue  # 跳过本次循环
    if i == 7:
        break     # 终止循环
    print(i)

# for-else（Python 特有）
for i in range(5):
    if i == 10:
        break
else:
    print("循环正常结束（没有被 break）")
```

### 1.4 函数

#### 基础函数

```python
# 定义函数
def greet(name):
    return f"你好，{name}！"

# 调用
print(greet("莫斯"))

# 多返回值（返回元组）
def get_info():
    return "张三", 25, "北京"

name, age, city = get_info()  # 解包

# 默认参数
def power(base, exponent=2):
    return base ** exponent

print(power(3))      # 9（使用默认值）
print(power(3, 3))   # 27

# 关键字参数
def user_info(name, age, city):
    print(f"{name}, {age}岁, {city}")

user_info(age=25, city="北京", name="张三")  # 顺序无关
```

#### 可变参数

```python
# *args - 接收任意数量的位置参数（元组）
def sum_all(*args):
    print(f"参数类型: {type(args)}")  # <class 'tuple'>
    return sum(args)

print(sum_all(1, 2, 3, 4, 5))  # 15

# **kwargs - 接收任意数量的关键字参数（字典）
def print_info(**kwargs):
    print(f"参数类型: {type(kwargs)}")  # <class 'dict'>
    for key, value in kwargs.items():
        print(f"{key}: {value}")

print_info(name="张三", age=25, city="北京")

# 混合使用
def func(a, b, *args, **kwargs):
    print(f"a={a}, b={b}")
    print(f"args={args}")
    print(f"kwargs={kwargs}")

func(1, 2, 3, 4, x=5, y=6)
# a=1, b=2
# args=(3, 4)
# kwargs={'x': 5, 'y': 6}
```

#### Lambda 表达式

```python
# lambda 是匿名函数
square = lambda x: x ** 2
print(square(5))  # 25

# 常用于排序
students = [("张三", 85), ("李四", 92), ("王五", 78)]
students.sort(key=lambda s: s[1], reverse=True)
print(students)  # [("李四", 92), ("张三", 85), ("王五", 78)]

# map/filter 结合 lambda
numbers = [1, 2, 3, 4, 5]
squared = list(map(lambda x: x**2, numbers))  # [1, 4, 9, 16, 25]
evens = list(filter(lambda x: x % 2 == 0, numbers))  # [2, 4]

# Java 对比：
# List<Integer> squared = numbers.stream()
#     .map(x -> x * x)
#     .collect(Collectors.toList());
# Python 的 lambda 更简洁
```

#### 装饰器

```python
# 装饰器是 Python 的语法糖，用于修改函数行为
import time

# 定义装饰器
def timer(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} 执行时间: {end - start:.2f}秒")
        return result
    return wrapper

# 使用装饰器
@timer
def slow_function():
    time.sleep(1)
    return "完成"

result = slow_function()
# 输出: slow_function 执行时间: 1.00秒

# 带参数的装饰器
def repeat(n):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for _ in range(n):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

@repeat(3)
def say_hello():
    print("Hello!")

say_hello()
# 输出 3 次 Hello!
```

### 1.5 文件操作

```python
# 读取文件
with open("data.txt", "r", encoding="utf-8") as f:
    content = f.read()           # 读取全部内容
    # 或者逐行读取
    # lines = f.readlines()

# 写入文件
with open("output.txt", "w", encoding="utf-8") as f:
    f.write("第一行\n")
    f.write("第二行\n")

# 追加写入
with open("log.txt", "a", encoding="utf-8") as f:
    f.write("新日志\n")

# with 语句自动关闭文件（类似 Java 的 try-with-resources）

# pathlib（现代路径处理）
from pathlib import Path

# 创建路径对象
project_dir = Path("/home/user/project")
file_path = project_dir / "data" / "input.txt"  # 路径拼接

# 读取文件
content = file_path.read_text(encoding="utf-8")

# 检查文件是否存在
if file_path.exists():
    print("文件存在")

# 遍历目录
for file in project_dir.glob("*.py"):  # 所有 .py 文件
    print(file.name)
```

---

## 第二阶段：Python 进阶（2-3周）

> 区分"会写 Python"和"写好 Python"

### 2.1 面向对象编程

#### 类和对象

```python
# 定义类
class Dog:
    # 类变量（所有实例共享）
    species = "犬科"

    # 构造方法
    def __init__(self, name, age):
        # 实例变量
        self.name = name
        self.age = age

    # 实例方法
    def bark(self):
        return f"{self.name} says 汪汪！"

    # 魔术方法：字符串表示
    def __str__(self):
        return f"Dog(name={self.name}, age={self.age})"

    def __repr__(self):
        return f"Dog('{self.name}', {self.age})"

# 创建对象
dog1 = Dog("旺财", 3)
dog2 = Dog("小白", 2)

print(dog1.bark())      # "旺财 says 汪汪！"
print(dog1)             # "Dog(name=旺财, age=3)"
print(dog1.species)     # "犬科"
```

#### 继承

```python
# 基类
class Animal:
    def __init__(self, name):
        self.name = name

    def speak(self):
        raise NotImplementedError("子类必须实现 speak 方法")

# 继承
class Cat(Animal):
    def __init__(self, name, color):
        super().__init__(name)  # 调用父类构造方法
        self.color = color

    def speak(self):
        return f"{self.name} says 喵~"

class Dog(Animal):
    def speak(self):
        return f"{self.name} says 汪汪！"

# 多态
animals = [Cat("小花", "橘色"), Dog("旺财")]
for animal in animals:
    print(animal.speak())

# isinstance 检查
cat = Cat("小花", "橘色")
print(isinstance(cat, Cat))      # True
print(isinstance(cat, Animal))   # True
```

#### 魔术方法（Dunder Methods）

```python
class Vector:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    # 字符串表示
    def __str__(self):
        return f"Vector({self.x}, {self.y})"

    def __repr__(self):
        return f"Vector({self.x}, {self.y})"

    # 运算符重载
    def __add__(self, other):
        return Vector(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vector(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar):
        return Vector(self.x * scalar, self.y * scalar)

    # 比较运算符
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __lt__(self, other):
        return self.x < other.x

    # 长度
    def __len__(self):
        return int((self.x**2 + self.y**2)**0.5)

    # 可调用对象
    def __call__(self, scale):
        return Vector(self.x * scale, self.y * scale)

# 使用
v1 = Vector(1, 2)
v2 = Vector(3, 4)

v3 = v1 + v2           # Vector(4, 6)
v4 = v1 * 3            # Vector(3, 6)
print(v1 == v2)         # False
print(len(v1))          # 2
print(v1(2))            # Vector(2, 4)
```

#### Property 装饰器

```python
class Circle:
    def __init__(self, radius):
        self._radius = radius  # 私有属性（约定）

    # getter
    @property
    def radius(self):
        return self._radius

    # setter
    @radius.setter
    def radius(self, value):
        if value < 0:
            raise ValueError("半径不能为负数")
        self._radius = value

    # 只读属性
    @property
    def area(self):
        return 3.14159 * self._radius ** 2

# 使用
c = Circle(5)
print(c.radius)     # 5（调用 getter）
c.radius = 10       # 调用 setter
print(c.area)       # 314.159（只读属性）
# c.area = 100      # AttributeError: can't set attribute
```

#### 类方法和静态方法

```python
class Date:
    def __init__(self, year, month, day):
        self.year = year
        self.month = month
        self.day = day

    # 实例方法：操作实例数据
    def display(self):
        return f"{self.year}-{self.month:02d}-{self.day:02d}"

    # 类方法：操作类本身，常用作工厂方法
    @classmethod
    def from_string(cls, date_string):
        year, month, day = map(int, date_string.split("-"))
        return cls(year, month, day)  # cls 就是 Date 类

    # 静态方法：与类和实例无关的工具函数
    @staticmethod
    def is_valid(year, month, day):
        return 1 <= month <= 12 and 1 <= day <= 31

# 使用
d1 = Date(2025, 6, 15)
d2 = Date.from_string("2025-06-15")  # 工厂方法
print(d1.display())  # "2025-06-15"
print(Date.is_valid(2025, 13, 1))  # False
```

### 2.2 迭代器和生成器

#### 迭代器

```python
# 迭代器协议：实现 __iter__ 和 __next__
class Countdown:
    def __init__(self, start):
        self.current = start

    def __iter__(self):
        return self

    def __next__(self):
        if self.current <= 0:
            raise StopIteration
        self.current -= 1
        return self.current + 1

# 使用
for num in Countdown(5):
    print(num)  # 5, 4, 3, 2, 1

# iter() 和 next() 内置函数
it = iter([1, 2, 3])
print(next(it))  # 1
print(next(it))  # 2
print(next(it))  # 3
# print(next(it))  # StopIteration
```

#### 生成器

```python
# 生成器函数（使用 yield）
def countdown(n):
    while n > 0:
        yield n  # 暂停并返回值
        n -= 1

# 使用生成器
for num in countdown(5):
    print(num)  # 5, 4, 3, 2, 1

# 生成器表达式（类似列表推导式，但惰性求值）
squares_list = [x**2 for x in range(1000000)]  # 立即创建，占用内存
squares_gen = (x**2 for x in range(1000000))   # 惰性，按需生成

# 生成器的优势：省内存
import sys
print(sys.getsizeof(squares_list))  # ~8MB
print(sys.getsizeof(squares_gen))   # ~200 bytes

# 实际应用：读取大文件
def read_large_file(file_path):
    with open(file_path, "r") as f:
        for line in f:  # 逐行读取，不一次性加载
            yield line.strip()

# 使用
for line in read_large_file("huge_file.txt"):
    process(line)  # 每次只处理一行
```

#### 生成器高级用法

```python
# 生成器的 send 方法（双向通信）
def accumulator():
    total = 0
    while True:
        value = yield total
        if value is None:
            break
        total += value

acc = accumulator()
next(acc)           # 启动生成器
print(acc.send(10)) # 10
print(acc.send(20)) # 30
print(acc.send(30)) # 60

# yield from（委托生成器）
def flatten(nested):
    for item in nested:
        if isinstance(item, (list, tuple)):
            yield from flatten(item)  # 递归展平
        else:
            yield item

nested = [1, [2, 3], [4, [5, 6]]]
print(list(flatten(nested)))  # [1, 2, 3, 4, 5, 6]
```

### 2.3 异常处理

```python
# 基本异常处理
try:
    result = 10 / 0
except ZeroDivisionError as e:
    print(f"错误: {e}")
except (TypeError, ValueError) as e:
    print(f"类型或值错误: {e}")
except Exception as e:
    print(f"其他错误: {e}")
else:
    print("没有异常时执行")
finally:
    print("无论是否异常都执行")

# 自定义异常
class InsufficientFundsError(Exception):
    def __init__(self, balance, amount):
        self.balance = balance
        self.amount = amount
        super().__init__(f"余额不足：余额{balance}，需要{amount}")

class BankAccount:
    def __init__(self, balance=0):
        self.balance = balance

    def withdraw(self, amount):
        if amount > self.balance:
            raise InsufficientFundsError(self.balance, amount)
        self.balance -= amount
        return self.balance

# 使用
account = BankAccount(100)
try:
    account.withdraw(150)
except InsufficientFundsError as e:
    print(e)  # "余额不足：余额100，需要150"
```

### 2.4 模块和包

```python
# 模块导入
import os
import sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timedelta

# 别名
import numpy as np
import pandas as pd

# 从模块导入特定项
from math import pi, sqrt

# 条件导入
try:
    import ujson as json  # 更快的 JSON 库
except ImportError:
    import json  # 回退到标准库

# __name__ == "__main__"
def main():
    print("直接运行时执行")

if __name__ == "__main__":
    main()
# 当被 import 时不执行，直接运行时才执行

# 虚拟环境
# python -m venv myenv
# source myenv/bin/activate  # Linux/Mac
# myenv\Scripts\activate     # Windows
# pip install requests pandas
```

---

## 第三阶段：实用技能（3-4周）

> 结合 Agent 开发和数据分析方向

### 3.1 文件和数据处理

#### JSON 处理

```python
import json

# Python 对象 → JSON 字符串
data = {
    "name": "莫斯",
    "age": 25,
    "skills": ["Python", "AI"],
    "is_student": True
}

json_str = json.dumps(data, ensure_ascii=False, indent=2)
print(json_str)

# JSON 字符串 → Python 对象
parsed = json.loads(json_str)
print(parsed["name"])

# 读写 JSON 文件
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

with open("data.json", "r", encoding="utf-8") as f:
    loaded = json.load(f)

# 自定义序列化
class User:
    def __init__(self, name, age):
        self.name = name
        self.age = age

def user_serializer(obj):
    if isinstance(obj, User):
        return {"name": obj.name, "age": obj.age}
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

user = User("张三", 25)
json_str = json.dumps(user, default=user_serializer)
```

#### CSV 处理

```python
import csv

# 读取 CSV
with open("data.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(row["name"], row["age"])

# 写入 CSV
data = [
    {"name": "张三", "age": 25, "city": "北京"},
    {"name": "李四", "age": 30, "city": "上海"}
]

with open("output.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["name", "age", "city"])
    writer.writeheader()
    writer.writerows(data)
```

#### 路径处理（pathlib）

```python
from pathlib import Path

# 创建路径
p = Path("/home/user/documents")

# 路径操作
print(p.name)         # "documents"
print(p.parent)       # "/home/user"
print(p.suffix)       # ""
print(p.stem)         # "documents"

# 路径拼接
file_path = p / "data" / "file.txt"
print(file_path)      # "/home/user/documents/data/file.txt"

# 检查
print(file_path.exists())
print(file_path.is_file())
print(file_path.is_dir())

# 创建目录
p.mkdir(parents=True, exist_ok=True)

# 遍历目录
for file in p.glob("**/*.py"):  # 递归查找所有 .py 文件
    print(file)

# 读写文件
p = Path("test.txt")
p.write_text("Hello, World!", encoding="utf-8")
content = p.read_text(encoding="utf-8")
```

### 3.2 数据分析（Pandas）

#### DataFrame 基础

```python
import pandas as pd

# 创建 DataFrame
data = {
    "姓名": ["张三", "李四", "王五", "赵六"],
    "年龄": [25, 30, 28, 35],
    "城市": ["北京", "上海", "北京", "深圳"],
    "薪资": [15000, 20000, 18000, 25000]
}

df = pd.DataFrame(data)
print(df)
#    姓名  年龄  城市    薪资
# 0  张三   25  北京  15000
# 1  李四   30  上海  20000
# 2  王五   28  北京  18000
# 3  赵六   35  深圳  25000

# 基本信息
print(df.shape)       # (4, 4) 行列数
print(df.dtypes)      # 数据类型
print(df.info())      # 详细信息
print(df.describe())  # 统计摘要
```

#### 数据选择和过滤

```python
# 选择列
print(df["姓名"])
print(df[["姓名", "薪资"]])

# 选择行（iloc 基于位置，loc 基于标签）
print(df.iloc[0])      # 第一行
print(df.iloc[1:3])    # 第2-3行
print(df.loc[0, "姓名"])  # 第一行的姓名列

# 条件过滤
beijing = df[df["城市"] == "北京"]
high_salary = df[df["薪资"] > 18000]
complex_filter = df[(df["城市"] == "北京") & (df["薪资"] > 16000)]

# query 方法（更易读）
result = df.query("城市 == '北京' and 薪资 > 16000")
```

#### 数据清洗

```python
# 缺失值处理
df_with_nan = pd.DataFrame({
    "A": [1, 2, None, 4],
    "B": [5, None, 7, 8]
})

# 检查缺失值
print(df_with_nan.isnull())
print(df_with_nan.isnull().sum())

# 填充缺失值
df_filled = df_with_nan.fillna(0)                    # 用0填充
df_filled = df_with_nan.fillna(df_with_nan.mean())   # 用均值填充

# 删除缺失值
df_dropped = df_with_nan.dropna()                    # 删除有缺失值的行
df_dropped = df_with_nan.dropna(subset=["A"])        # 只看A列

# 数据类型转换
df["年龄"] = df["年龄"].astype(float)

# 重复值
print(df.duplicated())
df_unique = df.drop_duplicates()
```

#### 数据聚合

```python
# 分组聚合
grouped = df.groupby("城市")
print(grouped["薪资"].mean())   # 各城市平均薪资
print(grouped["薪资"].agg(["mean", "max", "min"]))

# 多级分组
result = df.groupby(["城市", "性别"]).agg({
    "薪资": "mean",
    "年龄": "max"
})

# 透视表
pivot = df.pivot_table(
    values="薪资",
    index="城市",
    columns="性别",
    aggfunc="mean"
)

# 排序
df_sorted = df.sort_values("薪资", ascending=False)
```

#### 常用操作

```python
# 新增列
df["年薪"] = df["薪资"] * 12
df["薪资等级"] = df["薪资"].apply(lambda x: "高" if x > 20000 else "低")

# apply 函数
def age_group(age):
    if age < 25:
        return "青年"
    elif age < 35:
        return "中年"
    else:
        return "老年"

df["年龄段"] = df["年龄"].apply(age_group)

# 字符串操作
df["城市_大写"] = df["城市"].str.upper()
df["姓名_长度"] = df["姓名"].str.len()

# 合并 DataFrame
df1 = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
df2 = pd.DataFrame({"id": [1, 2], "score": [90, 85]})

merged = pd.merge(df1, df2, on="id")  # 类似 SQL JOIN
concatenated = pd.concat([df1, df2])   # 上下拼接

# 导出
df.to_csv("output.csv", index=False, encoding="utf-8-sig")
df.to_excel("output.xlsx", index=False)
df.to_json("output.json", orient="records", force_ascii=False)
```

### 3.3 网络编程

#### requests 库

```python
import requests

# GET 请求
response = requests.get("https://api.github.com/user", 
                       params={"page": 1, "per_page": 10})
print(response.status_code)  # 200
print(response.json())       # 解析 JSON

# POST 请求
data = {"username": "test", "password": "123456"}
response = requests.post("https://httpbin.org/post", 
                        json=data,  # 自动设置 Content-Type
                        headers={"Authorization": "Bearer token123"})

# 带错误处理
try:
    response = requests.get("https://api.example.com/data", timeout=5)
    response.raise_for_status()  # 抛出 HTTP 错误
    data = response.json()
except requests.exceptions.RequestException as e:
    print(f"请求失败: {e}")

# Session（保持登录状态）
session = requests.Session()
session.post("https://example.com/login", data={"user": "test", "pass": "123"})
response = session.get("https://example.com/profile")  # 自动带 cookie
```

#### 异步请求（aiohttp）

```python
import asyncio
import aiohttp

async def fetch(session, url):
    async with session.get(url) as response:
        return await response.json()

async def main():
    urls = [
        "https://api.github.com/user",
        "https://api.github.com/repos",
        "https://api.github.com/orgs"
    ]
    
    async with aiohttp.ClientSession() as session:
        # 并发请求
        tasks = [fetch(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
        
        for result in results:
            print(result)

# 运行
asyncio.run(main())
```

### 3.4 并发编程

#### 多线程

```python
import threading
import time

def worker(name, duration):
    print(f"线程 {name} 开始")
    time.sleep(duration)
    print(f"线程 {name} 结束")

# 创建线程
t1 = threading.Thread(target=worker, args=("A", 2))
t2 = threading.Thread(target=worker, args=("B", 3))

# 启动线程
t1.start()
t2.start()

# 等待线程结束
t1.join()
t2.join()

print("所有线程完成")

# 线程锁（解决竞态条件）
lock = threading.Lock()
counter = 0

def increment():
    global counter
    with lock:  # 自动获取和释放锁
        counter += 1

# 线程池
from concurrent.futures import ThreadPoolExecutor

def process_item(item):
    time.sleep(1)
    return item * 2

with ThreadPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(process_item, [1, 2, 3, 4, 5]))
    print(results)  # [2, 4, 6, 8, 10]
```

#### 异步编程（asyncio）

```python
import asyncio

async def fetch_data(url, delay):
    print(f"开始请求 {url}")
    await asyncio.sleep(delay)  # 模拟网络请求
    print(f"完成请求 {url}")
    return f"数据来自 {url}"

async def main():
    # 并发执行多个协程
    tasks = [
        fetch_data("api1.com", 2),
        fetch_data("api2.com", 3),
        fetch_data("api3.com", 1)
    ]
    
    # gather 并发执行
    results = await asyncio.gather(*tasks)
    print(results)

# 运行
asyncio.run(main())

# 异步上下文管理器
async def async_operation():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.example.com") as resp:
            return await resp.json()

# 异步迭代器
async def async_generator():
    for i in range(10):
        await asyncio.sleep(0.1)
        yield i

async def consume():
    async for item in async_generator():
        print(item)
```

#### 多进程

```python
from multiprocessing import Process, Pool
import os

def worker(name):
    print(f"进程 {name}, PID: {os.getpid()}")

# 创建进程
if __name__ == "__main__":
    p1 = Process(target=worker, args=("A",))
    p2 = Process(target=worker, args=("B",))
    
    p1.start()
    p2.start()
    
    p1.join()
    p2.join()

# 进程池（CPU 密集型任务）
def cpu_heavy(n):
    return sum(i * i for i in range(n))

if __name__ == "__main__":
    with Pool(processes=4) as pool:
        results = pool.map(cpu_heavy, [10**6, 10**6, 10**6, 10**6])
        print(results)

# 进程间通信
from multiprocessing import Queue

def producer(q):
    for i in range(5):
        q.put(i)
    q.put(None)  # 结束信号

def consumer(q):
    while True:
        item = q.get()
        if item is None:
            break
        print(f"处理: {item}")

if __name__ == "__main__":
    q = Queue()
    p1 = Process(target=producer, args=(q,))
    p2 = Process(target=consumer, args=(q,))
    
    p1.start()
    p2.start()
    
    p1.join()
    p2.join()
```

---

## 第四阶段：高级主题（按需学习）

### 4.1 设计模式

#### 单例模式

```python
class Singleton:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, value):
        self.value = value

# 使用
s1 = Singleton(1)
s2 = Singleton(2)
print(s1 is s2)      # True
print(s1.value)      # 2（最后一次赋值）

# 装饰器实现单例
def singleton(cls):
    instances = {}
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance

@singleton
class Database:
    def __init__(self):
        print("初始化数据库连接")
```

#### 工厂模式

```python
from abc import ABC, abstractmethod

class Animal(ABC):
    @abstractmethod
    def speak(self):
        pass

class Dog(Animal):
    def speak(self):
        return "汪汪！"

class Cat(Animal):
    def speak(self):
        return "喵~"

class AnimalFactory:
    @staticmethod
    def create(animal_type):
        if animal_type == "dog":
            return Dog()
        elif animal_type == "cat":
            return Cat()
        else:
            raise ValueError(f"未知动物类型: {animal_type}")

# 使用
factory = AnimalFactory()
dog = factory.create("dog")
cat = factory.create("cat")
print(dog.speak())  # "汪汪！"
print(cat.speak())  # "喵~"
```

#### 观察者模式

```python
class EventEmitter:
    def __init__(self):
        self._listeners = {}
    
    def on(self, event, callback):
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)
    
    def emit(self, event, *args, **kwargs):
        if event in self._listeners:
            for callback in self._listeners[event]:
                callback(*args, **kwargs)
    
    def off(self, event, callback):
        if event in self._listeners:
            self._listeners[event].remove(callback)

# 使用
emitter = EventEmitter()

def on_data(data):
    print(f"收到数据: {data}")

def on_error(error):
    print(f"发生错误: {error}")

emitter.on("data", on_data)
emitter.on("error", on_error)

emitter.emit("data", {"key": "value"})
emitter.emit("error", "连接失败")
```

### 4.2 元编程

#### metaclass

```python
class Meta(type):
    def __new__(cls, name, bases, dict):
        # 在类创建时修改类
        dict['class_id'] = name.lower()
        return super().__new__(cls, name, bases, dict)

class MyClass(metaclass=Meta):
    pass

print(MyClass.class_id)  # "myclass"

# 实际应用：自动注册插件
class PluginMeta(type):
    _plugins = {}
    
    def __new__(cls, name, bases, dict):
        new_class = super().__new__(cls, name, bases, dict)
        if name != 'Plugin':
            cls._plugins[name] = new_class
        return new_class

class Plugin(metaclass=PluginMeta):
    pass

class PDFPlugin(Plugin):
    pass

class CSVPlugin(Plugin):
    pass

print(PluginMeta._plugins)  # {'PDFPlugin': <class 'PDFPlugin'>, ...}
```

#### 描述符

```python
class Validator:
    def __init__(self, min_value=None, max_value=None):
        self.min_value = min_value
        self.max_value = max_value
    
    def __set_name__(self, owner, name):
        self.name = name
    
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, f'_{self.name}', None)
    
    def __set__(self, obj, value):
        if self.min_value is not None and value < self.min_value:
            raise ValueError(f"{self.name} 不能小于 {self.min_value}")
        if self.max_value is not None and value > self.max_value:
            raise ValueError(f"{self.name} 不能大于 {self.max_value}")
        setattr(obj, f'_{self.name}', value)

class Student:
    age = Validator(min_value=0, max_value=150)
    score = Validator(min_value=0, max_value=100)
    
    def __init__(self, name, age, score):
        self.name = name
        self.age = age
        self.score = score

# 使用
s = Student("张三", 20, 85)
# s = Student("张三", -1, 85)  # ValueError: age 不能小于 0
```

### 4.3 性能优化

#### profiling

```python
import cProfile
import time

# 方法1：装饰器
def timer(func):
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        print(f"{func.__name__}: {end - start:.4f}秒")
        return result
    return wrapper

@timer
def slow_function():
    time.sleep(1)
    return "done"

# 方法2：cProfile
def profile_function():
    cProfile.run('slow_function()')

# 方法3：line_profiler（需要 pip install line_profiler）
# kernprof -l -v script.py
```

#### 常见优化技巧

```python
# 1. 使用生成器而不是列表
# 不好
def get_squares_bad(n):
    return [i**2 for i in range(n)]

# 好
def get_squares_good(n):
    return (i**2 for i in range(n))

# 2. 使用集合而不是列表进行成员检查
# 不好 O(n)
items = [1, 2, 3, 4, 5]
if 3 in items:
    pass

# 好 O(1)
items = {1, 2, 3, 4, 5}
if 3 in items:
    pass

# 3. 使用 defaultdict 避免 KeyError
from collections import defaultdict

# 不好
d = {}
for word in words:
    if word not in d:
        d[word] = 0
    d[word] += 1

# 好
d = defaultdict(int)
for word in words:
    d[word] += 1

# 4. 使用 join 而不是 + 拼接字符串
# 不好
s = ""
for word in words:
    s += word + " "

# 好
s = " ".join(words)

# 5. 使用局部变量
# 不好
def process():
    for i in range(1000000):
        math.sqrt(i)

# 好
def process():
    sqrt = math.sqrt  # 局部变量查找更快
    for i in range(1000000):
        sqrt(i)
```

### 4.4 测试

#### pytest

```python
# test_example.py
import pytest

def add(a, b):
    return a + b

# 基本测试
def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(0, 0) == 0

# 参数化测试
@pytest.mark.parametrize("a,b,expected", [
    (1, 2, 3),
    (-1, 1, 0),
    (0, 0, 0),
    (100, 200, 300)
])
def test_add_parametrize(a, b, expected):
    assert add(a, b) == expected

# 异常测试
def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        1 / 0

# fixture（测试前置/后置）
@pytest.fixture
def sample_data():
    return {"name": "测试", "value": 42}

def test_with_data(sample_data):
    assert sample_data["name"] == "测试"
    assert sample_data["value"] == 42

# mock
from unittest.mock import Mock, patch

def test_api_call():
    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = {"status": "ok"}
        result = requests.get("https://api.example.com").json()
        assert result["status"] == "ok"

# 运行：pytest test_example.py -v
```

#### unittest

```python
import unittest

class Calculator:
    def add(self, a, b):
        return a + b
    
    def divide(self, a, b):
        if b == 0:
            raise ValueError("除数不能为0")
        return a / b

class TestCalculator(unittest.TestCase):
    def setUp(self):
        """测试前执行"""
        self.calc = Calculator()
    
    def tearDown(self):
        """测试后执行"""
        pass
    
    def test_add(self):
        self.assertEqual(self.calc.add(1, 2), 3)
        self.assertEqual(self.calc.add(-1, 1), 0)
    
    def test_divide(self):
        self.assertEqual(self.calc.divide(10, 2), 5)
        
        # 测试异常
        with self.assertRaises(ValueError):
            self.calc.divide(10, 0)
    
    def test_add_negative(self):
        self.assertEqual(self.calc.add(-1, -2), -3)

if __name__ == "__main__":
    unittest.main()
```

---

## 学习资源推荐

### 官方文档
- **Python 官方文档**：https://docs.python.org/zh-cn/3/
- **Python 教程**：https://docs.python.org/zh-cn/3/tutorial/

### 书籍
- **《Python Crash Course》**（Python编程：从入门到实践）
  - 适合初学者，项目导向
- **《Fluent Python》**（流畅的Python）
  - 进阶必读，深入理解Pythonic
- **《Effective Python》**（Effective Python）
  - 90个实践建议，写出更好的代码
- **《Python Cookbook》**
  - 高级技巧和最佳实践

### 在线平台
- **LeetCode**：https://leetcode.cn/
  - 用Python刷题，熟悉语法
- **GitHub**：https://github.com/
  - 阅读优秀Python项目源码
- **Real Python**：https://realpython.com/
  - 高质量Python教程
- **Towards Data Science**：https://towardsdatascience.com/
  - 数据科学方向

### 视频教程
- **B站**：搜"Python教程"，很多免费优质内容
- **Coursera**：Python for Everybody（密歇根大学）
- **YouTube**：Corey Schafer 的 Python 系列

---

## 实战项目建议

### 第一阶段项目（1-2周）

**项目1：命令行计算器**
- 功能：支持加减乘除、括号、历史记录
- 技能：函数、异常处理、文件操作
- 代码量：~200行

**项目2：待办事项管理器**
- 功能：增删改查、持久化存储、优先级排序
- 技能：数据结构、JSON、文件操作
- 代码量：~300行

**项目3：文件整理工具**
- 功能：按类型/日期整理文件、重命名、统计
- 技能：pathlib、文件操作、正则表达式
- 代码量：~250行

### 第二阶段项目（2-3周）

**项目4：爬虫**
- 功能：爬取网页数据、解析HTML、保存到CSV
- 技能：requests、BeautifulSoup、数据处理
- 代码量：~400行

**项目5：数据分析报告**
- 功能：读取CSV数据、统计分析、生成图表
- 技能：Pandas、Matplotlib、数据处理
- 代码量：~350行

**项目6：简单的Web API**
- 功能：RESTful API、数据库操作、错误处理
- 技能：Flask/FastAPI、SQLAlchemy、JSON
- 代码量：~500行

### 第三阶段项目（3-4周）

**项目7：聊天机器人**
- 功能：自然语言处理、API调用、对话管理
- 技能：asyncio、API调用、状态管理
- 代码量：~600行

**项目8：数据可视化仪表板**
- 功能：实时数据、交互式图表、过滤功能
- 技能：Dash/Streamlit、Pandas、Plotly
- 代码量：~800行

**项目9：自动化测试框架**
- 功能：测试用例管理、报告生成、CI集成
- 技能：pytest、设计模式、配置管理
- 代码量：~700行

### 第四阶段项目（按需）

**项目10：Agent工具**
- 功能：自定义工具、API集成、错误处理
- 技能：异步编程、API设计、错误处理
- 代码量：~500行

**项目11：性能监控工具**
- 功能：系统监控、数据收集、告警
- 技能：psutil、asyncio、数据处理
- 代码量：~600行

---

## 学习方法建议

### 1. 学习节奏

**每天2-3小时**：
- 1小时学习新概念
- 1小时写代码练习
- 30分钟复习和总结

**每周目标**：
- 周一到周五：学习新内容
- 周六：做项目
- 周日：复习和整理笔记

### 2. 学习策略

**80/20法则**：
- 先学最常用的20%功能
- 比如：列表、字典、函数、文件操作
- 其他用到再学

**项目驱动**：
- 每学一个新概念，立即用到项目中
- 比如学了列表推导式，就用它重写之前的代码

**对比学习**：
- 你有Java基础，多对比Python和Java的区别
- 比如：Python的列表 vs Java的ArrayList

### 3. 代码质量

**Pythonic写法**：
```python
# 不好（Java风格）
result = []
for i in range(10):
    if i % 2 == 0:
        result.append(i * 2)

# 好（Python风格）
result = [i * 2 for i in range(10) if i % 2 == 0]
```

**命名规范**：
- 变量和函数：snake_case（user_name, get_data）
- 类名：PascalCase（User, DataProcessor）
- 常量：UPPER_CASE（MAX_VALUE, API_URL）
- 私有属性：_前缀（_internal_var）

**注释和文档**：
```python
def calculate_age(birth_year: int, current_year: int = 2025) -> int:
    """
    计算年龄
    
    Args:
        birth_year: 出生年份
        current_year: 当前年份，默认2025
    
    Returns:
        年龄（整数）
    
    Raises:
        ValueError: 如果出生年份大于当前年份
    
    Examples:
        >>> calculate_age(1990)
        35
        >>> calculate_age(1990, 2020)
        30
    """
    if birth_year > current_year:
        raise ValueError("出生年份不能大于当前年份")
    return current_year - birth_year
```

### 4. 调试技巧

**print调试**：
```python
# 基础
print(f"变量x的值: {x}")
print(f"变量x的类型: {type(x)}")

# 更好的方式：使用pprint
from pprint import pprint
pprint(complex_data_structure)
```

**使用断点**：
```python
# 在代码中插入断点
breakpoint()  # Python 3.7+

# 或者
import pdb; pdb.set_trace()
```

**日志记录**：
```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告信息")
logger.error("错误信息")
```

### 5. 进阶学习路径

**Agent开发方向**：
1. 异步编程（asyncio）
2. API设计（FastAPI）
3. 数据处理（Pandas）
4. 机器学习基础（scikit-learn）

**数据分析方向**：
1. 数据清洗（Pandas）
2. 数据可视化（Matplotlib、Seaborn、Plotly）
3. 统计分析（SciPy）
4. 机器学习（scikit-learn）

**Web开发方向**：
1. Web框架（Django、Flask、FastAPI）
2. 数据库（SQLAlchemy、Django ORM）
3. RESTful API设计
4. 前后端分离

---

## 快速参考

### 常用内置函数

```python
# 类型转换
int("123")      # 字符串→整数
str(123)        # 整数→字符串
float("3.14")   # 字符串→浮点数
list("abc")     # 字符串→列表 ['a', 'b', 'c']
tuple([1,2,3])  # 列表→元组 (1, 2, 3)
set([1,2,2,3])  # 列表→集合 {1, 2, 3}

# 数学函数
abs(-5)         # 5 绝对值
max(1, 2, 3)    # 3 最大值
min(1, 2, 3)    # 1 最小值
sum([1,2,3])    # 6 求和
round(3.14, 1)  # 3.1 四舍五入
pow(2, 3)       # 8 幂运算

# 序列操作
len([1,2,3])    # 3 长度
sorted([3,1,2]) # [1,2,3] 排序
reversed([1,2,3])  # 反转迭代器
enumerate(["a","b"])  # 带索引迭代
zip([1,2], [3,4])    # 并行迭代

# 类型检查
type(x)         # 获取类型
isinstance(x, int)  # 类型检查
```

### 常用标准库

```python
# 系统操作
import os           # 操作系统接口
import sys          # 系统参数
import pathlib      # 路径操作
import shutil       # 文件操作

# 数据处理
import json         # JSON
import csv          # CSV
import re           # 正则表达式
import collections  # 高级数据结构
import itertools    # 迭代器工具

# 时间日期
import datetime     # 日期时间
import time         # 时间函数
import calendar     # 日历

# 网络编程
import urllib       # URL处理
import http         # HTTP协议
import socket       # 套接字

# 并发
import threading    # 线程
import multiprocessing  # 进程
import asyncio      # 异步IO

# 调试测试
import logging      # 日志
import unittest     # 单元测试
import pdb          # 调试器
```

### 常用第三方库

```python
# 数据科学
import numpy as np         # 数值计算
import pandas as pd        # 数据分析
import matplotlib.pyplot as plt  # 绘图
import seaborn as sns      # 统计图表

# Web开发
import flask               # Web框架
import django              # 全栈框架
import fastapi             # 异步API框架

# 网络爬虫
import requests            # HTTP请求
import beautifulsoup4      # HTML解析
import scrapy              # 爬虫框架

# 机器学习
import scikit-learn        # 机器学习
import tensorflow          # 深度学习
import pytorch             # 深度学习

# 工具
import click               # CLI工具
import rich                # 终端美化
import typer               # CLI框架
```

---

## 学习计划模板

### 第1周：Python基础

| 天数 | 内容 | 练习 |
|------|------|------|
| Day 1 | 变量、数据类型、字符串 | 写个字符串处理工具 |
| Day 2 | 列表、元组、集合 | 实现学生成绩管理 |
| Day 3 | 字典、条件语句 | 写个简单计算器 |
| Day 4 | 循环、函数基础 | 九九乘法表、猜数字游戏 |
| Day 5 | 函数进阶、Lambda | 排序算法、数据过滤 |
| Day 6 | 文件操作 | 日志分析器 |
| Day 7 | 复习+项目 | 命令行待办事项 |

### 第2周：Python进阶

| 天数 | 内容 | 练习 |
|------|------|------|
| Day 1 | 面向对象基础 | 设计学生类 |
| Day 2 | 继承、多态 | 设计动物类层次 |
| Day 3 | 魔术方法、Property | 实现向量类 |
| Day 4 | 迭代器、生成器 | 实现自定义迭代器 |
| Day 5 | 异常处理 | 健壮的文件处理器 |
| Day 6 | 模块、包 | 创建自己的工具包 |
| Day 7 | 复习+项目 | 爬虫项目 |

### 第3周：实用技能

| 天数 | 内容 | 练习 |
|------|------|------|
| Day 1 | JSON、CSV处理 | 数据格式转换器 |
| Day 2 | pathlib、正则表达式 | 文件批量重命名 |
| Day 3 | Pandas基础 | 数据清洗 |
| Day 4 | Pandas进阶 | 数据分析报告 |
| Day 5 | requests、API调用 | 天气查询工具 |
| Day 6 | 并发编程 | 异步爬虫 |
| Day 7 | 复习+项目 | 数据可视化仪表板 |

### 第4周：高级主题

| 天数 | 内容 | 练习 |
|------|------|------|
| Day 1 | 设计模式 | 实现单例、工厂模式 |
| Day 2 | 元编程 | 描述符、元类 |
| Day 3 | 性能优化 | 优化之前的项目 |
| Day 4 | 测试 | 为项目写测试 |
| Day 5 | 调试技巧 | 排查复杂bug |
| Day 6 | 代码规范 | 重构代码 |
| Day 7 | 总结+项目 | 完整项目 |

---

## 常见问题

### Q: Python 和 Java 最大的区别是什么？

**A**: 
1. **类型系统**：Python 是动态类型，Java 是静态类型
2. **语法**：Python 用缩进，Java 用花括号
3. **运行方式**：Python 是解释型，Java 是编译型
4. **代码量**：Python 通常更简洁

### Q: Python 学到什么程度可以找工作？

**A**:
- **初级**：掌握基础语法、常用数据结构、文件操作
- **中级**：面向对象、异常处理、常用标准库
- **高级**：设计模式、性能优化、并发编程

建议：至少做完3-5个项目，有GitHub作品集

### Q: Python 哪个方向最好找工作？

**A**:
1. **数据分析**：需求大，入门相对容易
2. **Web开发**：Django/Flask/FastAPI，全栈方向
3. **自动化测试**：测试开发，薪资不错
4. **AI/Agent开发**：你正在做的方向，前景好

### Q: 学 Python 需要数学基础吗？

**A**:
- **基础开发**：不需要
- **数据分析**：基础统计知识
- **机器学习**：线性代数、概率论
- **AI开发**：看你具体做什么，调用API不需要

---

> **记住**：Python 的设计哲学是"简单优于复杂"，很多 Java 里要写 10 行的代码，Python 里 1 行就搞定。
> 
> 学习过程中遇到问题，多看官方文档，多写代码，多做项目。
> 
> 加油！🚀
