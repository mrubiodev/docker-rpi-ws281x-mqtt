#!/usr/bin/env python3

from rpi_ws281x import Color


def get_color(color, brightness):
    return Color(int(color['r'] * brightness / 255),
                 int(color['g'] * brightness / 255),
                 int(color['b'] * brightness / 255))


def set_all_leds_color(strip, new_color):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, new_color)
    strip.show()

#led strip in segmenten ansteuern
def set_segment_color(strip, new_color, segment):
   # print("set segment color start: ", start, " end: ", end, " color: ", new_color)
    for leds in segment[1]:
        for i in range(leds[0], leds[1]):
            strip.setPixelColor(i, new_color)
   # for i in range(460):
   #     if strip.getPixelColor(i) == 0:
   #         print("0", end = " ")
   #     else:
   #         print("1", end = " ")
   # print("/////////")
    strip.show()
    
