import random
import weakref
from typing import Any, Optional, Set, List, Dict
import logging

logger = logging.getLogger(__name__)

class ColorManager:
    def __init__(self, colors: List[str] = None):
        if colors is None:
            self._all_colors = [
                "rgba(71, 235, 235, 1)", "rgba(71, 235, 205, 1)", "rgba(71, 235, 175, 1)",
                "rgba(86, 71, 235, 1)", "rgba(116, 71, 235, 1)", "rgba(146, 71, 235, 1)",
                "rgba(175, 71, 235, 1)", "rgba(205, 71, 235, 1)", "rgba(235, 71, 235, 1)",
                "rgba(235, 71, 205, 1)", "rgba(235, 71, 175, 1)", "rgba(235, 71, 146, 1)",
                "rgba(235, 71, 116, 1)", "rgba(235, 71, 86, 1)", "rgba(235, 86, 71, 1)",
                "rgba(235, 106, 71, 1)", "rgba(235, 126, 71, 1)", "rgba(235, 146, 71, 1)"
            ]
        else:
            self._all_colors = colors[:]

        self._main_to_color = weakref.WeakKeyDictionary()  # main_obj -> color
        self._main_to_ids = weakref.WeakKeyDictionary()    # main_obj -> set of identifiers
        self._color_to_main: Dict[str, weakref.ref] = {}   # color -> weakref to main_obj
        self._id_to_main: Dict[Any, weakref.ref] = {}      # identifier -> weakref to main_obj

    def _cleanup(self):
        dead_colors = [c for c, ref in self._color_to_main.items() if ref() is None]
        for c in dead_colors:
            del self._color_to_main[c]

        dead_ids = [id_ for id_, ref in self._id_to_main.items() if ref() is None]
        for id_ in dead_ids:
            del self._id_to_main[id_]

    def _get_available_colors(self) -> Set[str]:
        self._cleanup()
        used = set(self._color_to_main.keys())
        return set(self._all_colors) - used

    def register_color(self, main_obj: Any, identifiers: list) -> str:
        try:
            ref = weakref.ref(main_obj)
        except TypeError:
            raise TypeError(f"Object {main_obj} does not support weak references")

        self._cleanup()

        # если объект уже зарегистрирован, добавляем новые идентификаторы (после проверки)
        if main_obj in self._main_to_color:
            color = self._main_to_color[main_obj]
            existing_ids = self._main_to_ids.setdefault(main_obj, set())
            for id_ in identifiers:
                other_ref = self._id_to_main.get(id_)
                if other_ref is not None:
                    other = other_ref()
                    if other is not None and other is not main_obj:
                        raise ValueError(f"Identifier {id_} already used by another live object")
                # добавляем идентификатор (если его не было или он принадлежал мёртвому объекту)
                self._id_to_main[id_] = ref
                existing_ids.add(id_)
            return color

        for id_ in identifiers:
            other_ref = self._id_to_main.get(id_)
            if other_ref is not None:
                other = other_ref()
                if other is not None:
                    raise ValueError(f"Identifier {id_} already used by another live object")

        available = self._get_available_colors()
        if not available:
            return "rgba(235, 0, 0, 1)"  #резервный

        chosen = random.choice(list(available))

        self._main_to_color[main_obj] = chosen
        self._main_to_ids[main_obj] = set(identifiers)
        self._color_to_main[chosen] = ref
        for id_ in identifiers:
            self._id_to_main[id_] = ref

        logger.info(f"Object {main_obj} {identifiers=} registered with color {chosen}")
        return chosen

    def get_color(self, key: Any) -> Optional[str]:
        self._cleanup()
        if key in self._main_to_color:
            return self._main_to_color[key]
        ref = self._id_to_main.get(key)
        if ref is not None:
            obj = ref()
            if obj is not None:
                return self._main_to_color.get(obj)
        return None

    def release_all(self) -> None:
        self._main_to_color.clear()
        self._main_to_ids.clear()
        self._color_to_main.clear()
        self._id_to_main.clear()

    @property
    def used_colors(self) -> Set[str]:
        self._cleanup()
        return set(self._color_to_main.keys())

    @property
    def available_colors(self) -> Set[str]:
        return self._get_available_colors()

    def __repr__(self) -> str:
        return f"ColorManager(used={len(self.used_colors)} colors, available={len(self.available_colors)})"

def show_colors( colors ):
    import webbrowser
    import os

    unique_colors = [
        "rgba(71, 235, 235, 1)",   # h=180°
        "rgba(71, 235, 205, 1)",   # h=185°
        "rgba(71, 235, 175, 1)",   # h=190°
        "rgba(86, 71, 235, 1)",    # h=245°
        "rgba(116, 71, 235, 1)",   # h=250°
        "rgba(146, 71, 235, 1)",   # h=255°
        "rgba(175, 71, 235, 1)",   # h=260°
        "rgba(205, 71, 235, 1)",   # h=265°
        "rgba(235, 71, 235, 1)",   # h=270°
        "rgba(235, 71, 205, 1)",   # h=275°
        "rgba(235, 71, 175, 1)",   # h=280°
        "rgba(235, 71, 146, 1)",   # h=285°
        "rgba(235, 71, 116, 1)",   # h=290°
        "rgba(235, 71, 86, 1)",    # h=295°
        "rgba(235, 86, 71, 1)",    # h=300°
        "rgba(235, 106, 71, 1)",   # h=305°
        "rgba(235, 126, 71, 1)",   # h=310°
        "rgba(235, 146, 71, 1)",   # h=315°
    ]

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Цветовая палитра</title>
        <style>
            body { display: flex; flex-wrap: wrap; gap: 10px; padding: 20px; background: #222; }
            .color-block {
                width: 120px;
                height: 120px;
                border-radius: 8px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                color: white;
                text-shadow: 1px 1px 2px black;
                font-family: monospace;
                font-size: 12px;
                text-align: center;
                box-shadow: 0 2px 5px rgba(0,0,0,0.3);
            }
        </style>
    </head>
    <body>
    """

    for i, color in enumerate(unique_colors):
        rgb = color.replace("rgba", "rgb").replace(", 1)", ")")
        html_content += f'<div class="color-block" style="background-color: {color};"><span>#{i+1}</span><span>{rgb}</span></div>\n'

    html_content += """
    </body>
    </html>
    """

    file_path = "colors.html"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    webbrowser.open("file://" + os.path.realpath(file_path))
if __name__ == "__main__":
    import gc

    # Создаём менеджер с цветами по умолчанию
    cm = ColorManager()

    # Простой класс для создания объектов
    class Entity:
        def __init__(self, name):
            self.name = name
        def __repr__(self):
            return f"Entity({self.name})"

    # Создаём объект и регистрируем его с несколькими идентификаторами
    obj1 = Entity("obj1")
    color1 = cm.register_color(obj1, ["id_alpha", 42, "extra_id"])
    print(f"Зарегистрирован объект {obj1} с цветом {color1}")
    print(f"Цвет по объекту: {cm.get_color(obj1)}")
    print(f"Цвет по идентификатору 'id_alpha': {cm.get_color('id_alpha')}")
    print(f"Цвет по идентификатору 42: {cm.get_color(42)}")
    print(f"Цвет по идентификатору 'extra_id': {cm.get_color('extra_id')}")
    print()

    # Пытаемся зарегистрировать другой объект с уже занятым идентификатором
    obj2 = Entity("obj2")
    try:
        cm.register_color(obj2, [42])  # 42 уже занят
    except ValueError as e:
        print(f"Ожидаемая ошибка при повторном использовании идентификатора: {e}")
    print()

    # Удаляем объект и принудительно запускаем сборку мусора
    del obj1
    gc.collect()
    print("После удаления obj1 и сборки мусора:")
    print(f"Цвет по идентификатору 'id_alpha': {cm.get_color('id_alpha')}")
    print(f"Цвет по идентификатору 42: {cm.get_color(42)}")
    print(f"Цвет по объекту (уже не существует) при вызове с None? Но get_color ожидает ключ, проверим другой способ:")
    # Мы не можем передать удалённый объект, но можем проверить, что идентификаторы очищены
    print(f"Повторная регистрация obj2 с освободившимся идентификатором 42:")
    color2 = cm.register_color(obj2, [42])
    print(f"obj2 получил цвет {color2} по идентификатору 42")
    print(f"Цвет по объекту obj2: {cm.get_color(obj2)}")
    print(f"Цвет по идентификатору 42: {cm.get_color(42)}")
    print()

    # Очистка всех данных
    cm.release_all()
    print("После release_all:")
    print(f"Цвет по объекту obj2: {cm.get_color(obj2)}")
    print(f"Цвет по идентификатору 42: {cm.get_color(42)}")