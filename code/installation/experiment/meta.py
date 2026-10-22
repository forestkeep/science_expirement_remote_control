import time
from functions import get_active_ch_and_device

class metaDataExp( ):

    def __init__(self):
        super().__init__()
        self.actors_names   = {}
        self.actors_classes = {}
        self.numbers        = {}
        self.exp_queue      = []
        self.queue_info     = []
        self.exp_start_time = 0
        self.adjusted_start_time = 0
        self.exp_stop_time  = 0
 
    def get_meta_data(self):
        pass

    def write_start_meta_data(self, devices: dict):
        self.exp_start_time = time.perf_counter()
        
        number = 1
        for dev, ch in get_active_ch_and_device( devices ):
            key = f"{dev.get_name()} {ch.get_name()}"
            self.actors_classes[number] = ch
            self.actors_names[number] = key
            self.numbers[key] = number
            number+=1
    
    def print_meta_data(self):
        print("number: \t name: \t steps:")
        for num, obj in self.actors_classes.items():
            name = self.actors_names[num]
            num_steps = obj.dict_settable_parameters["num steps"]
            print(f"{num} \t { name } \t { num_steps }")
            
        print("exp queue:")
        print(self.exp_queue)
        
        print("queue info:")
        print(self.queue_info)
        
        print(f"time exp = {self.exp_stop_time - self.exp_start_time} sec")
        
        max_chars = max(  len(act) for act in self.actors_names.values()  )
        
        for num_actor in self.actors_names.keys():
            buf = []
            name = self.actors_names[num_actor]
            for act in self.exp_queue:
                if num_actor == act:
                    buf.append("###")
                else:
                    buf.append("...")
            print(name.ljust(max_chars),  "".join(buf))