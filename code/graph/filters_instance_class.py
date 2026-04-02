


class FilterCommand:
    def __init__(self, filter_type, params, filters_instance):
        self.filter_type = filter_type
        self.params = params
        self._filters_instance = filters_instance
    
    def apply(self, x, y):
        """Применяет фильтр к данным, используя методы filters_instance"""
        if self.filter_type == 'median':
            return self._filters_instance.med_filt(x, y, self.params['window'])
        elif self.filter_type == 'average':
            return self._filters_instance.average_filt(x, y, self.params['window'])
        elif self.filter_type == 'exp_mean':
            return self._filters_instance.exp_mean_filt(x, y, self.params['alpha'])
        elif self.filter_type == 'thinning':
            return self._filters_instance.thinning_filt(
                x, y, self.params['percent'],
                self.params['uniform'], self.params['max'],
                self.params['min'], self.params['first'], self.params['last']
            )
        elif self.filter_type == 'normalize':
            return self._filters_instance.normalize_filt(x, y, self.params['norm_type'])
        else:
            raise ValueError(f"Unknown filter type: {self.filter_type}")