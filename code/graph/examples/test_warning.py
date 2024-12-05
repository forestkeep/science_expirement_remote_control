

def update_data(self):
        string_x = self.get_last_item_parameter(self.x_param_selector)
        string_y = self.get_last_item_parameter(self.y_first_param_selector)
        string_y2 = self.get_last_item_parameter(self.y_second_param_selector)

        current_items_y = list(item.text() for item in self.y_first_param_selector.selectedItems())
        current_items_y2 = list(item.text() for item in self.y_second_param_selector.selectedItems())

        if string_y not in current_items_y and string_y != "Select parameter":
                device_y, ch_y, key_y = self.decode_name_parameters(string_y)
                if key_y in self.y.keys():
                    self.y.pop(key_y)
                    self.graphView.removeItem(self.curve1[key_y])
                    self.curve1.pop(key_y)
                    return
                else:
                    string_y = "Select parameter"

        if string_y2 not in current_items_y2 and string_y2 != "Select parameter":
                device_y2, ch_y2, key_y2 = self.decode_name_parameters(string_y2)
                if key_y2 in self.y2.keys():
                    self.y2.pop(key_y2)
                    self.p2.removeItem(self.curve2[key_y2])
                    self.p2.removeItem(self.curve2_dots[key_y2])
                    self.curve2.pop(key_y2)
                    self.curve2_dots.pop(key_y2)
                    return
                else:
                    string_y2 = "Select parameter"

        if string_x != "Select parameter":
            self.remove_parameter("Select parameter", self.x_param_selector)

        if string_y != "Select parameter":
            self.remove_parameter("Select parameter", self.y_first_param_selector)

        if string_y2 != "Select parameter":
            self.remove_parameter("Select parameter", self.y_second_param_selector)

        check_main = True
        
        if not self.multiple_checkbox.isChecked():
            self.y.clear()
            self.y2.clear()

        if string_x == "Select parameter" or string_y == "Select parameter":
            check_main = False
            if self.second_check_box.isChecked():
                if string_x == "Select parameter" or string_y2 == "Select parameter":
                    return
            else:
                return

        if string_x == "time" and string_y == "time":
            check_main = False
            if self.second_check_box.isChecked():
                if string_x == "time" or string_y2 == "time":
                    return
            else:
                return

        if check_main == True:
            if self.y is self.y2:
                self.y = {}
                self.x = []
                self.y_main_axis_label = ""
            if (
                string_x == "time"
                and string_y != "time"
                and string_y != "Select parameter"
            ):
                device_y, ch_y, parameter_y = self.decode_name_parameters(string_y)
                self.y_main_axis_label = parameter_y
                self.x_axis_label = "time"
                self.x = self.dict_param[device_y][ch_y]["time"]
                self.y[parameter_y] = self.dict_param[device_y][ch_y][parameter_y]
                
            elif string_y == "time" and string_x != "time":
                device_x, ch_x, parameter_x = self.decode_name_parameters(string_x)
                self.x_axis_label = parameter_x
                self.y_main_axis_label = "time"
                self.y["time"] = self.dict_param[device_x][ch_x]["time"]
                self.x = self.dict_param[device_x][ch_x][parameter_x]
                
            elif string_x == string_y:
                device_x, ch_x, parameter_x = self.decode_name_parameters(string_x)
                self.x = self.dict_param[device_x][ch_x][parameter_x]
                self.y[parameter_x] = self.dict_param[device_x][ch_x][parameter_x]
                self.y_main_axis_label = parameter_x
                self.x_axis_label = parameter_x
            else:

                device_y, ch_y, parameter_y = self.decode_name_parameters(string_y)
                device_x, ch_x, parameter_x = self.decode_name_parameters(string_x)
                print(self.dict_param)
                x_param = self.dict_param[device_x][ch_x][parameter_x]
                y_param = self.dict_param[device_y][ch_y][parameter_y]
                if self.is_time_column:

                    x_time = self.dict_param[device_x][ch_x]["time"]
                    y_time = self.dict_param[device_y][ch_y]["time"]
                    calculator_param = ArrayProcessor()
                    
                    self.x, bufy, _ = calculator_param.combine_interpolate_arrays(
                        arr_time_x1=x_time,
                        arr_time_x2=y_time,
                        values_y1=x_param,
                        values_y2=y_param,
                                        )
                        
                    self.y[parameter_y] = bufy
                    
                else:
                    self.x = x_param
                    self.y[parameter_y] = y_param
                
                self.y_main_axis_label = parameter_y
                self.x_axis_label = parameter_x

        if self.second_check_box.isChecked():
            if (
                string_x == "time" and string_y2 == "time"
            ) or string_y2 == "Select parameter":
                self.y_second_axis_label = ""
                self.x2 = []
                self.y2.clear()
            elif (
                string_x == "time"
                and string_y2 != "time"
                and string_y2 != "Select parameter"
            ):
                
                device_y2, ch_y2, parameter_y2 = self.decode_name_parameters(string_y2)
                self.y_second_axis_label = parameter_y2
                self.x_axis_label = "time"
                self.x2 = self.dict_param[device_y2][ch_y2]["time"]
                self.y2[parameter_y2] = self.dict_param[device_y2][ch_y2][parameter_y2]

            elif string_y2 == "time" and string_x != "time":
                device_x, ch_x, parameter_x = self.decode_name_parameters(string_x)
                self.x_axis_label = parameter_x
                self.y_second_axis_label = "time"
                self.y2["time"] = self.dict_param[device_x][ch_x]["time"]
                self.x2 = self.dict_param[device_x][ch_x][parameter_x]
            elif string_x == string_y2 and string_y2 != "time":
                device_x, ch_x, parameter_x = self.decode_name_parameters(string_x)
                self.x2 = self.dict_param[device_x][ch_x][parameter_x]
                self.y2[parameter_x] = self.x2
                self.y_second_axis_label = parameter_x
                self.x_axis_label = parameter_x
            else:
                device_y2, ch_y2, parameter_y2 = self.decode_name_parameters(string_y2)
                device_x, ch_x, parameter_x = self.decode_name_parameters(string_x)
                x_param = self.dict_param[device_x][ch_x][parameter_x]
                y_param = self.dict_param[device_y2][ch_y2][parameter_y2]
                if self.is_time_column:
                    x_time = self.dict_param[device_x][ch_x]["time"]
                    y_time = self.dict_param[device_y2][ch_y2]["time"]
                    calculator_param = ArrayProcessor()
                    self.x2, bufy2, _ = calculator_param.combine_interpolate_arrays(
                        arr_time_x1=x_time,
                        arr_time_x2=y_time,
                        values_y1=x_param,
                        values_y2=y_param,
                    )
                    self.y2[parameter_y2] = bufy2
                else:
                    self.x2 = x_param
                    self.y2[parameter_y2] = y_param
                    
                self.y_second_axis_label = parameter_y2
                self.x_axis_label = parameter_x

        else:
            self.y_second_axis_label = ""
            self.x2 = self.x2[:0]
            self.y2.clear()

        if len(self.y.keys()) > 1:
            #если множественное построение, то лейбл не ставим
            self.y_main_axis_label = ""

        if len(self.y2.keys()) > 1:
            #если множественное построение, то лейбл не ставим
            self.y_second_axis_label = ""

        if self.is_show_warning == True:
            points_num = 10000
            self.is_show_warning = False
            if len(self.x) > points_num:
                text = QApplication.translate("GraphWindow", "Число точек превысило {points_num}, расчет зависимости одного параметра от другого может занимать некоторое время.\n Особенно, на слабых компьютерах. Рекомендуется выводить графики в зависимости от времени.")
                text = text.format(points_num = points_num)
                message = messageDialog(
                    title=QApplication.translate("GraphWindow","Сообщение"),
                    text=text
                )
                message.exec_()


def update_draw(self):

        keys_y = set(self.y.keys())
        keys_y2 = set(self.y2.keys())

        to_remove1 = [key for key in self.curve1 if key not in keys_y]
        to_remove2 = [key for key in self.curve2 if key not in keys_y2]

        for key in to_remove1:
            self.graphView.removeItem(self.curve1[key])
            del self.curve1[key]

        for key in to_remove2:
            self.p2.removeItem(self.curve2[key])
            self.p2.removeItem(self.curve2_dots[key])
            del self.curve2[key]
            del self.curve2_dots[key]

        # Обновление легенд
        self.legend.clear()
        self.legend2.clear()

        self.graphView.setLabel("left", self.y_main_axis_label, color=self.color_line_main)
        self.graphView.setLabel("bottom", self.x_axis_label, color="#ffffff")

        # Обновление curve1
        for i, (key, data) in enumerate(self.y.items()):
            min_length = min(len(self.x), len(data))

            if key in self.curve1:
                self.curve1[key].setData( self.x[:min_length], data[:min_length] )
            else:
                pen = pg.mkPen(color=cold_colors[i], width=2, style=pg.QtCore.Qt.SolidLine)
           
                self.curve1[key] = pg.PlotDataItem(
                    x=self.x[:min_length],
                    y=data[:min_length],
                    pen=pen,
                    symbol='o',
                    symbolPen=cold_colors[i],
                    symbolBrush=cold_colors[i]
                )

                self.graphView.addItem(self.curve1[key])

            self.legend.addItem(self.curve1[key], f"{key}")

        # Обновление curve2, если чекбокс отмечен
        if self.second_check_box.isChecked():
            self.p1.getAxis("right").setLabel(self.y_second_axis_label, color=self.color_line_second)
            self.p1.getAxis("right").setStyle(showValues=True)

            for i, (key, data) in enumerate(self.y2.items()):
                min_length = min(len(self.x2), len(data))

                if key not in self.curve2:
                    pen = pg.mkPen(color=warm_colors[i], width=2, style=pg.QtCore.Qt.DashLine)
                    brush = pg.mkBrush(color=warm_colors[i])
                    self.curve2[key] = pg.PlotCurveItem(pen=pen)
                    self.curve2_dots[key] = pg.ScatterPlotItem(pen=pen, symbol='x', size=10)
                    self.p2.addItem(self.curve2[key])
                    self.p2.addItem(self.curve2_dots[key])
                    self.curve2_dots[key].setBrush(brush)
                    
                self.curve2[key].setData(self.x2[:min_length], data[:min_length])
                self.curve2_dots[key].setData(self.x2[:min_length], data[:min_length])
                self.legend2.addItem(self.curve2[key], f"{key}")
        else:
            self.p1.getAxis("right").setStyle(showValues=False)
            self.p1.getAxis("right").setLabel("")