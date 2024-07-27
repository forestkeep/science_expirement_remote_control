class A:

        def set_band_width(self, number_ch: int, is_enable: bool) -> bool:
            if is_enable:
                self.client.write(f":CHANnel{number_ch}:BWLimit 20M")
                is_ok = self.check_parameters(command=f":CHANnel{number_ch}:BWLimit?", focus_answer="20M")
            else:
                self.client.write(f":CHANnel{number_ch}:BWLimit OFF")
                is_ok = self.check_parameters(command=f":CHANnel{number_ch}:BWLimit?", focus_answer="OFF")
            return is_ok
        
        def set_coupling(self, number_ch: int, coupling = "DC") -> bool:
            self.client.write(f":CHANnel{number_ch}:COUPling {coupling}")
            is_ok = self.check_parameters(command=f":CHANnel{number_ch}:COUPling?", focus_answer=coupling)
            return is_ok
        
        def set_trigger_sourse(self, number_ch) -> bool:
            self.client.write(f":TRIGger:EDGe:SOURce CHANnel{number_ch}")
            is_ok = self.check_parameters(command=f":TRIGger:EDGe:SOURce?", focus_answer=f"CHAN{number_ch}")
            return is_ok

        def check_parameters(self, command, focus_answer) -> bool:
            ans = self.client.query(command)
            if ans == focus_answer:
                return True
            else:
                return False
