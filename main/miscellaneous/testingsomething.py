    def update_draw(self):
        for item in self.graphView.items():
            if isinstance(item, pg.PlotDataItem):
                self.graphView.removeItem(item)
        self.p2.clear()
        
        self.legend.clear()
        self.legend2.clear()

        self.graphView.setLabel(
            "left", self.y_main_axis_label, color=self.color_line_main
        )
        self.graphView.setLabel("bottom", self.x_axis_label, color="#ffffff")
        
        
        i = 0
        for key, data in self.y.items():
            pen = pg.mkPen(color=cold_colors[i], width=1, style=pg.QtCore.Qt.SolidLine)
            self.curve1 = self.graphView.plot(
            x=self.x,
            y=data,
            pen=pen,
            symbol='o',             
            symbolPen=cold_colors[i],
            symbolBrush=cold_colors[i] 
            )
            i+=1
            self.legend.addItem(self.curve1, f"{key}")
        
        if self.second_check_box.isChecked():
            self.p1.getAxis("right").setLabel(
                self.y_second_axis_label, color=self.color_line_second
            )
            self.p1.getAxis("right").setStyle(showValues=True)
            
            i = 0
            for key, data in self.y2.items():
                pen = pg.mkPen(color=warm_colors[i], width=1, style=pg.QtCore.Qt.DashLine)
                i+=1
                self.curve2 = pg.PlotCurveItem(pen=pen, symbol='o')
                self.p2.addItem(self.curve2)
                self.curve2.setData(self.x2, data)
                self.legend2.addItem(self.curve2, f"{key}")
            
        else:
            self.p1.getAxis("right").setStyle(showValues=False)
            self.p1.getAxis("right").setLabel("")
            
    def setupGraphView(self):
        graphView = pg.PlotWidget(title="")

        self.color_line_main = "#55aa00"
        self.color_line_second = "#ff0000"

        # Placeholder items for dropdown - this will be dynamically populated later
        self.x_param_selector.addItems(["Select parameter"])
        self.y_first_param_selector.addItems(["Select parameter"])
        self.y_second_param_selector.addItems(["Select parameter"])
        
        item = self.x_param_selector.item(0)
        
        self.x_param_selector.setCurrentItem( item )
        self.y_first_param_selector.setCurrentItem( item )
        self.y_second_param_selector.setCurrentItem( item )

        self.y_first_param_selector.currentItemChanged.connect(
            lambda: self.update_plot()
        )
        self.y_second_param_selector.currentItemChanged.connect(
            lambda: self.update_plot()
        )
        self.x_param_selector.currentItemChanged.connect(lambda: self.update_plot())
        self.second_check_box.stateChanged.connect(lambda: self.update_plot())

        graphView.scene().sigMouseMoved.connect(self.showToolTip)
        graphView.plotItem.getAxis("left").linkToView(graphView.plotItem.getViewBox())
        graphView.plotItem.getAxis("bottom").linkToView(graphView.plotItem.getViewBox())

        self.p1 = graphView.plotItem

        self.p2 = pg.ViewBox()
        self.p1.showAxis("right")
        self.p1.scene().addItem(self.p2)
        self.p1.getAxis("right").linkToView(self.p2)
        self.p2.setXLink(self.p1)
        self.p1.getAxis("right").setLabel("axis2", color="#000fff")

        self.p1.vb.sigResized.connect(self.updateViews)
        
        self.legend.setParentItem(self.p1)
        self.legend2.setParentItem(self.p2)

        my_font = QFont("Times", 13)
        self.p1.getAxis("right").label.setFont(my_font)
        graphView.getAxis("bottom").label.setFont(my_font)
        graphView.getAxis("left").label.setFont(my_font)

        return graphView