# Copyright © 2023 Zakhidov Dmitry <zakhidov.dim@yandex.ru>
# 
# This file may be used under the terms of the GNU General Public License
# version 3.0 as published by the Free Software Foundation and appearing in
# the file LICENSE included in the packaging of this file. Please review the
# following information to ensure the GNU General Public License version 3.0
# requirements will be met: https://www.gnu.org/copyleft/gpl.html.
# 
# This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
# WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.

templates = {
'oscilloscope':
{
    "device_type": "oScilloscope",
    "device_name": 'some_device',
    "number_channels": 4,
    "commands": {
        "get_data": {
            "command": ":WAV:DATA?\\r\\n",
            "separator": ",",
            "description": "Get waveform data within specified start and end points"
        },
        "set_start_point": {
            "command": ":WAV:STARt {point}\\r\\n",
            "description": "Set the start point for waveform data retrieval"
        },
        "set_end_point": {
            "command": ":WAV:STOP {point}\\r\\n",
            "description": "Set the end point for waveform data retrieval"
        },
        "get_sample_rate": {
            "command": "ACQ:SRATe?\\r\\n",
            "description": "Get the current sample rate"
        },
        "set_band_width": {
            "command": ":CHANnel{number_ch}:BWLimit {is_enable}\\r\\n",
            "check_command": ":CHANnel{number_ch}:BWLimit?\\r\\n",
            "focus_answer": "{is_enable}\\n",
            "description": "Set the bandwidth limit for the specified channel"
        },
        "set_coupling": {
            "command": ":CHANnel{number_ch}:COUPling {coupling}\\r\\n",
            "check_command": ":CHANnel{number_ch}:COUPling?\\r\\n",
            "focus_answer": "{coupling}\\n",
            "description": "Set the coupling mode for the specified channel"
        },
        "set_trigger_mode": {
            "command": ":TRIGger:MODE {mode}\\r\\n",
            "check_command": ":TRIGger:MODE?\\r\\n",
            "focus_answer": "{mode}\\n",
            "description": "Set the trigger mode"
        },
        "set_trigger_edge_slope": {
            "command": ":TRIGger:EDGe:SLOPe {slope}\\r\\n",
            "check_command": ":TRIGger:EDGe:SLOPe?\\r\\n",
            "focus_answer": "{slope}\n",
            "description": "Set the trigger edge slope"
        },
        "set_trigger_sweep": {
            "command": ":TRIGger:SWEep {sweep}\\r\\n",
            "check_command": ":TRIGger:SWEep?\\r\\n",
            "focus_answer": "{sweep}\\n",
            "description": "Set the trigger sweep mode"
        },
        "set_trigger_source": {
            "command": ":TRIGger:EDGe:SOURce CHAN{number_ch}\\r\\n",
            "check_command": ":TRIGger:EDGe:SOURce?\\r\\n",
            "focus_answer": "CHAN{number_ch}\\n",
            "description": "Set the trigger source channel"
        },
        "set_trigger_edge_level": {
            "command": ":TRIGger:EDGe:LEVel {level}\\r\\n",
            "check_command": ":TRIGger:EDGe:LEVel?\\r\\n",
            "focus_answer": "{level}\n",
            "description": "Set the trigger edge level"
        },
        "get_meas_parameter": {
            "command": ":MEASure:ITEM? {parameter},CHANnel{ch}\\r\\n",
            "description": "Get measurement parameter for specified channels"
        },
        "set_scale": {
            "command": "TIM:MAIN:SCALe {scale}\\r\\n",
            "check_command": "TIM:MAIN:SCALe?\\r\\n",
            "focus_answer": "{scale}\n",
            "description": "Set the scale for the main time axis"
        },
        "get_scale": {
            "command": "TIM:MAIN:SCALe?\\r\\n",
            "description": "Get the current scale for the main time axis"
        },
        "set_wave_source": {
            "command": ":WAV:SOUR CHANnel{number_ch}\\r\\n",
            "check_command": ":WAV:SOUR?\\r\\n",
            "focus_answer": "CHAN{number_ch}\\r\\n",
            "description": "Set the wave source for the specified channel"
        },
        "run": {
            "command": ":RUN\\r\\n",
            "description": "Start the oscilloscope"
        },
        "stop": {
            "command": ":STOP\\r\\n",
            "description": "Stop the oscilloscope"
        },
        "clear": {
            "command": ":CLE\\r\\n",
            "description": "Clear the oscilloscope settings"
        },
        "single": {
            "command": ":SING\\r\\n",
            "description": "Trigger a single acquisition"
        },
        "get_status": {
            "command": ":TRIG:STAT?\\r\\n",
            "description": "Get the current trigger status"
        },
        "set_wave_form_mode": {
            "command": ":WAV:MODE {mode}\\r\\n",
            "check_command": ":WAV:MODE?\\r\\n",
            "focus_answer": "{mode}\\n",
            "description": "Set the waveform mode"
        },
        "set_wave_format": {
            "command": ":WAV:FORM {format}\\r\\n",
            "check_command": ":WAV:FORM?\\r\\n",
            "focus_answer": "{format}\n",
            "description": "Set the waveform format"
        },
        "set_probe": {
            "command": ":CHANnel{ch_number}:PROBe {probe}\\r\\n",
            "check_command": ":CHANnel{ch_number}:PROBe?\\r\\n",
            "focus_answer": "{probe}\n",
            "description": "Set the probe value for the specified channel"
        },
        "set_ch_scale": {
            "command": ":CHANnel{ch_number}:SCALe {scale}\\r\\n",
            "check_command": ":CHANnel{ch_number}:SCALe?\\r\\n",
            "focus_answer": "{scale}\n",
            "description": "Set the scale for the specified channel"
        },
        "set_invert": {
            "command": ":CHANnel{ch_number}:INVert {invert}\\r\\n",
            "check_command": ":CHANnel{ch_number}:INVert?\\r\\n",
            "focus_answer": "{invert}\n",
            "description": "Set the inversion state for the specified channel"
        },
        "set_meas_source": {
            "command": ":MEAS:SOUR CHANnel{number_ch}\\r\\n",
            "check_command": ":MEAS:SOUR?\r\n",
            "focus_answer": "CHAN{number_ch}\n",
            "description": "Set the measurement source for the specified channel"
        },
        "on_off_channel": {
            "command": ":CHANnel{number_ch}:DISP {is_enable}\\r\\n",
            "check_command": ":CHANnel{number_ch}:DISP?\\r\\n",
            "focus_answer": "{is_enable}\n",
            "description": "Enable or disable display for the specified channel"
        }
    }
}

}