# code/saving_data/buffer_data.py
"""Модель BufferData: семантический тип для .buf/.txt буферных файлов.

Заменяет ad-hoc __parse_data в saving_data/Parse_data.py.
Формат: текстовый поток с маркерами
    installation start
    device list: ...
    Settings device_N
    <device settings lines>
    Settings ch-N_meas
    <channel settings lines>
    Settings ch-N_meas
    ...
    --------------------
    <data lines: HH:MM:SS.SSS dev ch [name=value] ...>
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Optional

from file_io import RawDocument, register
from file_io.errors import ReadError


@dataclass
class OscRecord:
    """Одна осциллограмма в буферном файле."""

    name: str
    time: str
    step: float
    data: list[float]


@dataclass
class ChannelRecord:
    """Один канал прибора: settings + накопленные data + осциллограммы."""

    device: str
    channel: str
    settings: list[str] = field(default_factory=list)
    data: dict[str, list[str]] = field(default_factory=dict)
    osc: list[OscRecord] = field(default_factory=list)


@register(kind="buffer_data", formats=("buf", "txt"))
@dataclass
class BufferData:
    """Разобранный буферный файл эксперимента."""

    KIND: ClassVar[str] = "buffer_data"
    FORMATS: ClassVar[tuple[str, ...]] = ("buf", "txt")

    channels: list[ChannelRecord] = field(default_factory=list)
    schema_version: int = 1
    kind: str = KIND

    # ---------- parser ----------

    @classmethod
    def can_parse(cls, doc: RawDocument) -> bool:
        if doc.format not in cls.FORMATS:
            return False
        if not isinstance(doc.payload, bytes):
            return False
        try:
            text = doc.payload.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            return False
        return "installation start" in text

    @classmethod
    def parse(cls, doc: RawDocument) -> "BufferData":
        if not isinstance(doc.payload, bytes):
            raise ReadError(
                path=doc.path,
                position=None,
                reason="buffer_data: payload must be bytes",
            )
        try:
            text = doc.payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ReadError(
                path=doc.path, position=exc.start, reason=f"utf-8: {exc.reason}"
            ) from exc
        return cls._parse_text(text, path=doc.path)

    @classmethod
    def _parse_text(cls, text: str, *, path) -> "BufferData":
        channels: list[ChannelRecord] = []
        buf_device_settings: list[str] = []
        setting_device = False
        setting_channel = False
        parameters_reading = False
        is_correct_file = False
        current_dev_name: Optional[str] = None
        current_step: Optional[float] = None
        num_wave = 0

        def find(dev: str, ch: str) -> Optional[ChannelRecord]:
            for c in channels:
                if c.device == dev and c.channel == ch:
                    return c
            return None

        for raw_line in text.splitlines():
            line = raw_line.rstrip("\r").rstrip("\n")

            if not is_correct_file:
                if "installation start" in line:
                    is_correct_file = True
                continue

            is_device_line = "Settings " in line and "ch-" not in line
            is_channel_line = "Settings " in line and "ch-" in line

            if is_device_line:
                setting_device = True
                setting_channel = False
                parts = line.split()
                current_dev_name = parts[1] if len(parts) >= 2 else None
                buf_device_settings = []
                continue

            if setting_device:
                if is_channel_line:
                    setting_device = False
                    setting_channel = True
                    parts = line.split()
                    ch = parts[1] if len(parts) >= 2 else ""
                    channels.append(ChannelRecord(
                        device=current_dev_name or "",
                        channel=ch,
                        settings=list(buf_device_settings),
                    ))
                    buf_device_settings = []
                    continue
                buf_device_settings.append(line)
                continue

            if setting_channel:
                if is_channel_line:
                    parts = line.split()
                    ch = parts[1] if len(parts) >= 2 else ""
                    channels.append(ChannelRecord(
                        device=current_dev_name or "",
                        channel=ch,
                        settings=[],
                    ))
                    continue
                if "--------------------" in line:
                    setting_channel = False
                    continue
                if channels:
                    channels[-1].settings.append(line)
                continue

            if not parameters_reading and channels and not setting_device and not setting_channel:
                parameters_reading = True

            if parameters_reading:
                parts = line.split()
                if len(parts) < 3:
                    continue
                timestamp, dev_name, ch_name = parts[0], parts[1], parts[2]
                ch = find(dev_name, ch_name)
                if ch is None:
                    continue
                ch.data.setdefault("time", []).append(timestamp)
                time_len = len(ch.data["time"])
                for tok in parts[3:]:
                    stripped = tok.strip()
                    if not (stripped.startswith("[") and stripped.endswith("]")):
                        continue
                    inner = stripped[1:-1]
                    if "=" not in inner:
                        continue
                    pname, pval = inner.split("=", 1)
                    if pname == "step":
                        try:
                            current_step = float(pval)
                        except ValueError:
                            current_step = None
                    elif "wave" in pname:
                        try:
                            wave_vals = [float(v) for v in pval.split("|") if v]
                        except ValueError:
                            wave_vals = []
                        ch.osc.append(OscRecord(
                            name=f"{dev_name}_{pname}_{num_wave}",
                            time=timestamp,
                            step=current_step if current_step is not None else 0.0,
                            data=wave_vals,
                        ))
                        num_wave += 1
                    else:
                        arr = ch.data.setdefault(pname, ["fail"] * (time_len - 1))
                        while len(arr) < time_len - 1:
                            arr.append("fail")
                        arr.append(pval)

        return cls(channels=channels)

    # ---------- dataframe ----------

    def to_dataframe(self, result_description: Optional[str] = None,
                     meta_data: Optional[str] = None):
        """Построить pandas.DataFrame для записи в excel/txt.

        Импорт pandas — лениво, чтобы модель можно было использовать
        в окружениях без pandas (только чтение).
        """
        import pandas as pd

        column_number = 0
        for ch in self.channels:
            column_number += len(ch.data.keys()) + 1

        data_frame: dict[str, list] = {}
        for h in range(column_number):
            data_frame[str(h)] = []
            if result_description is not None:
                data_frame[str(h)].append(result_description if h == 0 else " ")
            if meta_data is not None:
                data_frame[str(h)].append(meta_data if h == 0 else " ")

        # метки приборов
        h = 0
        number_tab: list[int] = []
        for i, ch in enumerate(self.channels):
            data_frame[str(h)].append(f"Прибор:{ch.device} канал:{ch.channel}")
            h += 1
            number_tab.append(len(ch.data))
            for _ in range(number_tab[i]):
                data_frame[str(h)].append(" ")
                h += 1

        # имена параметров
        h = 0
        for ch in self.channels:
            for pname in ch.data.keys():
                data_frame[str(h)].append(pname)
                h += 1
            data_frame[str(h)].append(" ")
            h += 1

        # строки данных
        h = 0
        max_rows = 0
        for ch in self.channels:
            if "time" in ch.data and len(ch.data["time"]) > max_rows:
                max_rows = len(ch.data["time"])
        for _ in range(max_rows):
            for ch in self.channels:
                for pval in ch.data.values():
                    try:
                        data_frame[str(h)].append(f"{pval[_]}")
                    except IndexError:
                        data_frame[str(h)].append("---")
                    h += 1
                data_frame[str(h)].append(" ")
                h += 1
            h = 0

        # строки настроек
        h = 0
        max_settings = 0
        for ch in self.channels:
            if len(ch.settings) > max_settings:
                max_settings = len(ch.settings)
        for k in range(max_settings):
            d = 0
            for i, ch in enumerate(self.channels):
                try:
                    data_frame[str(h)].append(ch.settings[k])
                except IndexError:
                    data_frame[str(h)].append("---")
                h += 1
                for _ in range(number_tab[d]):
                    data_frame[str(h)].append(" ")
                    h += 1
                d += 1
            h = 0

        # осциллограммы
        waves_frames = []
        max_chunk = 950000 - 2
        for ch in self.channels:
            waves: dict[str, list] = {" ": ["Время", "Шаг"]}
            for wave in ch.osc:
                splits = (len(wave.data) // max_chunk) + 1
                for idx in range(splits):
                    key = wave.name + f"({idx})"
                    start = idx * max_chunk
                    end = min((idx + 1) * max_chunk, len(wave.data))
                    waves[key] = [wave.time, wave.step]
                    for j in range(start, end):
                        waves[key].append(wave.data[j])
            if len(waves) > 1:  # хотя бы одна реальная осциллограмма
                df = pd.DataFrame(dict((k, pd.Series(v)) for k, v in waves.items()))
                waves_frames.append(df)

        main_df = pd.DataFrame(data_frame)
        waves_frames.insert(0, main_df)
        return pd.concat(waves_frames, axis=1)