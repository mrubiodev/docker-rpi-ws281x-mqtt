#!/usr/bin/env python3
# Author: Pavel Slama

import time
from effects.utils import utils

LED_COUNT = 0

def effect_solid_init(_ledcount):
    global LED_COUNT
    LED_COUNT = _ledcount

def effect_solid(strip, color, brightness):
    utils.set_all_leds_color(
        strip, utils.get_color(color, brightness))
    time.sleep(10)

#einzelnes segment ansteuern 
#die funktion soll dabei den gesamtzustand des Lightstrips speichern damit die nicht veränderten LEDS nicht verändert werden
    


def effect_solid_segment(strip, color, brightness, start, end):
    print(LED_COUNT)
    utils.set_segment_color(
        strip, utils.get_color(color, brightness), start, end)
    time.sleep(10)
