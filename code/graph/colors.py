import random 

contrast_colors = [
    "#FF0A00", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF",
    "#FFA500", "#FFA07A", "#FF1403", "#00FA9A", "#1E90FF", "#FFD700",
    "#ADFF2F", "#FF5600", "#FF69B4", "#FFB6C1", "#FFDAB9", "#98FB98",
    "#7B68EE", "#FFD700", "#bF6347", "#FF00FF", "#00BFFF", "#FF8C00",
    "#00FF7F", "#FF2499", "#FF7F50", "#FFD700", "#FFA500", "#FFB559",
    "#3CB371", "#00CED1", "#ADFF2F"
]

cold_colors = [
    "#0000ff", "#00bfff", "#1e90ff", "#00ffff", "#6495ed", "#4682b4",
    "#4169e1", "#7b68ee", "#6a5acd", "#00ced1", "#5f9ea0", "#48d1cc",
    "#00fa9a", "#98fb98", "#3cb371", "#00ff7f", "#20b2aa", "#4682b4",
    "#7fffd4", "#add8e6"
]

warm_colors = [
    "#ff0000", "#ff450a", "#ff7f50", "#fb6347", "#ff8c00", "#ffa500",
    "#ffd700", "#fa1493", "#db7093", "#ff69b4", "#ffb6c1", "#ff8c00",
    "#cd5c5c", "#f08080", "#e9967a", "#ff7f00", "#ff4500", "#ff6347",
    "#fa8072", "#ff1493"
]

class GColors():
    def __init__(self):
        self.used_colors = set()

    def get_random_color(self, special_color=None):
        while True:
            my_used_colors = set(self.used_colors)
            if not special_color:
                my_colors = set(contrast_colors) | set(warm_colors) | set(cold_colors)
            else:
                my_colors = set(special_color)
            missing = my_colors - my_used_colors

            if not missing:  
                self.used_colors.clear()
                color = random.choice(contrast_colors)
            else:
                color = random.choice(list(missing))

            self.used_colors.add(color)
            yield color

    def get_random_cold_color(self):
        return self.get_random_color(special_color=cold_colors)

    def get_random_warm_color(self):
        return self.get_random_color(special_color=warm_colors)