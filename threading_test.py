import threading


bajs = 5

def threading_fun(c):
    
    for i in range(10):
        print(c + i + bajs)


thread = threading.Thread(target = threading_fun, args=(100,))

thread.start()

print("done")