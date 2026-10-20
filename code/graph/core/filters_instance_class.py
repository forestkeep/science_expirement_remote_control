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
        elif self.filter_type == 'hampel':
            return self._filters_instance.hampel_filt(
                x, y, self.params['window'], self.params['n_sigmas']
            )
        elif self.filter_type == 'savitzky_golay':
            return self._filters_instance.savitzky_golay_filt(
                x, y, self.params['window'], self.params['polyorder']
            )
        elif self.filter_type == 'detrend':
            return self._filters_instance.detrend_filt(
                x, y, self.params['detrend_type'], self.params['polyorder']
            )
        elif self.filter_type == 'butterworth':
            return self._filters_instance.butterworth_filt(
                x, y, self.params['cutoff'], self.params['btype'], self.params['order']
            )
        elif self.filter_type == 'notch':
            return self._filters_instance.notch_filt(
                x, y, self.params['freq'], self.params['q']
            )
        elif self.filter_type == 'gaussian_smooth':
            return self._filters_instance.gaussian_smooth_filt(
                x, y, self.params['window'], self.params.get('sigma')
            )
        else:
            raise ValueError(f"Unknown filter type: {self.filter_type}")