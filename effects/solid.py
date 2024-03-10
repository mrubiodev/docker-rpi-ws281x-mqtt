#!/usr/bin/env python3
# Author: Pavel Slama

import time
from effects.utils import utils

#LED_COUNT = 0
#led_array = []

# def effect_solid_init(_ledcount):
#     global led_array
#     for i in _ledcount:
#         current_array = {
#             'state': 'OFF',
#             'color': {'r': 255, 'g': 255, 'b': 255},
#             'brightness': 255,
#         }
#         led_array.append(current_array)

def effect_solid(strip, color, brightness):
    utils.set_all_leds_color(
        strip, utils.get_color(color, brightness))
    time.sleep(10)
    

def effect_solid_segment(strip, color, brightness, segment):
    # print(LED_COUNT)
    # for i in range(start, end):
    #     led_array[i]['color'] = color
    #     led_array[i]['brightness'] = brightness
    #     led_array[i]['state'] = 'ON'
    utils.set_segment_color(
        strip, utils.get_color(color, brightness), segment)
    #time.sleep(10)

def effect_solid_transition(strip, color, brightness, segment, duration=1000):
    print("set segment color : ", segment,  " brightness: ",)
    for i in range(0, brightness, 5):
        print( i, " ",  end=" ")
        utils.set_segment_color(
            strip, utils.get_color(color, i), segment)
        time.sleep(duration / 1000 / (brightness / 5))