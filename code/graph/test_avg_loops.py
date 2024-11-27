import numpy as np
import matplotlib.pyplot as plt
import copy
from calc_values_for_graph import ArrayProcessor

class hystLoop:
    '''хранит данные о петле и ее исходных параметрах, содержит методы расчета петли'''
    def __init__(self, raw_x, raw_y, resistance, wire_square) -> None:
        self.raw_data_x = raw_x
        self.raw_data_y = raw_y
        self.filtered_raw_data_x = raw_x
        self.filtered_raw_data_y = raw_y
        self.plot_obj = None
        self.data_x = None
        self.data_y = None
        self.Q2 = 1.67
        self.resistance = resistance
        self.wire_square = wire_square
        
        
def my_custom_function(x):
    #return np.sin(x) ** 2 + np.cos(x) ** 2
    return np.array([15 for i in range(len(x))])


def gen_my_func():
	x = np.linspace(0, 5, 500)  
	y = my_custom_function(x)
	new = hystLoop(raw_x=x.tolist(), raw_y=y.tolist(), resistance=resistance, wire_square=wire_square)
	return new

def generate_data(func, num_points, variation, start, stop):
    x = np.linspace(start, stop, num_points)
    y = func(x) + np.random.normal(0.1, variation, size=x.shape)
    return x, y


loops = [] 
for i in range(1):
    x, y = generate_data(np.sin, 50, 0.1 + i * 0.01 , 0, 10)
    resistance = 5
    wire_square = 1
    loops.append(hystLoop(raw_x=x.tolist(), raw_y=y.tolist(), resistance=resistance, wire_square=wire_square))

for i in range(1):
    x, y = generate_data(np.sin, 50, 0.1 + i * 0.01, 2, 8)
    resistance = 5
    wire_square = 1
    loops.append(hystLoop(raw_x=x.tolist(), raw_y=y.tolist(), resistance=resistance, wire_square=wire_square))
    
loops.append(gen_my_func())


build_loops = copy.deepcopy(loops)

def plot_loops(loops, new_loops=None):
    plt.figure(figsize=(12, 8))
    
    for loop in loops:
        plt.plot(loop.raw_data_x, loop.raw_data_y, label=f'Resistance: {loop.resistance}, Wire: {loop.wire_square}', alpha=0.5)
    
    if new_loops is not None:
        for loop in new_loops:
            plt.plot(loop.raw_data_x, loop.raw_data_y, label='Average Loop', color='orange', linewidth=2.5, alpha=1.0)
    
    plt.title('Графики hystLoop')
    plt.xlabel('X')
    plt.ylabel('Y')
    plt.legend()
    plt.grid()
    plt.show()

class LoopAnalyzer:
    def __init__(self, loops_stack):
        self.loops_stack = loops_stack

    def avg_loop(self):
        new_loop, before_comb, after_comb = self.calc_avg_loop(loops_stack=self.loops_stack)
        return new_loop, before_comb, after_comb

    def calc_avg_loop(self, loops_stack):
        '''вернет объект петли, полученный усреднением стека петель'''
        print("вычисляем среднюю петлю")
        if len(loops_stack) == 1:
            return loops_stack[0]
        
        last_loop = None
        if len(loops_stack)%2 == 1:
            last_loop = loops_stack[-1]
            loops_stack.pop()
            
        while len(loops_stack) > 1:
            new_loop_stack = []
            for i in range(len(loops_stack)-1, 0, -2):
                print(f"{i=} {loops_stack=}")
                loop_first = loops_stack[i]
                loop_second = loops_stack[i-1]
                loops_stack.pop()
                loops_stack.pop()
                         
                new_loop, before_comb, after_comb = self.calc_avg_two_loops(loop_first, loop_second)
                
                new_loop_stack.append(new_loop)

                print(f"{i=} {new_loop_stack=}")
                
            loops_stack = new_loop_stack
            
        if last_loop is not None:
            new_loop, before_comb, after_comb = self.calc_avg_two_loops(last_loop, loops_stack[0])
        else:
            new_loop = loops_stack[0]
        return new_loop, before_comb, after_comb
            
    def calc_avg_two_loops(self, loop1, loop2):
        calculator = ArrayProcessor()
        y1, y2, mean_x = calculator.combine_interpolate_arrays(arr_time_x1=loop1.filtered_raw_data_x,
                                                      arr_time_x2=loop2.filtered_raw_data_x,
                                                      values_y1=loop1.filtered_raw_data_y,
                                                      values_y2=loop2.filtered_raw_data_y)
        mean_resistance = (loop1.resistance + loop2.resistance)/2
        mean_wire_square = (loop1.wire_square + loop2.wire_square)/2
        
        mean_y = (y1+y2)/2
        
        new_loop = hystLoop(raw_x=mean_x,
                            raw_y=mean_y,
                            resistance=mean_resistance,
                            wire_square=mean_wire_square
                            )
        
        after_comb = []
        after_comb.append(hystLoop(raw_x=mean_x, raw_y=y1, resistance=20, wire_square=20))
        #after_comb.append(hystLoop(raw_x=mean_x, raw_y=y2, resistance=20, wire_square=20))

        before_comb = []
        before_comb.append(hystLoop(raw_x=loop1.filtered_raw_data_x, raw_y=loop1.filtered_raw_data_y, resistance=20, wire_square=20))
        before_comb.append(hystLoop(raw_x=loop2.filtered_raw_data_x, raw_y=loop2.filtered_raw_data_y, resistance=20, wire_square=20))

        
        
        return new_loop, before_comb, after_comb
analyzer = LoopAnalyzer(loops)
new_loop, before_comb, after_comb = analyzer.avg_loop()

plot_loops(build_loops, [new_loop])

plot_loops(before_comb, after_comb)