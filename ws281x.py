#!/usr/bin/env python3

import json
import multiprocessing
import os
import paho.mqtt.client as paho
import time
from rpi_ws281x import Color
from rpi_ws281x import Adafruit_NeoPixel, ws
from effects.utils.utils import *

from effects.theater_chase_rainbow import effect_theater_chase_rainbow
from effects.rainbow_cycle import effect_rainbow_cycle
from effects.solid import effect_solid
from effects.solid import effect_solid_segment
#from effects.solid import effect_solid_init
from effects.knight_rider import effect_knight_rider
from typing import List

LED_GPIO = os.getenv('LED_GPIO', 18)
LED_COUNT = os.getenv('LED_COUNT', 10)
LED_CHANNEL = os.getenv('LED_CHANNEL', 0)
LED_FREQ_HZ = os.getenv('LED_FREQ_HZ', 800000)
LED_DMA_NUM = os.getenv('LED_DMA_NUM', 10)
LED_BRIGHTNESS = os.getenv('LED_BRIGHTNESS', 255)
LED_INVERT = os.getenv('LED_INVERT', 0)
LED_STRIP_TYPE = os.getenv('LED_STRIP_TYPE', 'GRB').upper()
#Array für die Segmente erstellen, das Array muss jeweils segment_start und segment_end enthalten
#Das Array muss zweidimensional sein, also [[segment_start, segment_end], [segment_start, segment_end], ...]
LED_SEGMENTS = os.getenv('LED_SEGMENTS', [[0, 126], [127, 140], [141,176], [177,238], [239,280], [281,408], [409,464]])



MQTT_BROKER = os.getenv('MQTT_BROKER', 'localhost')
MQTT_USER = os.getenv('MQTT_USER', None)
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', None)
MQTT_PORT = os.getenv('MQTT_PORT', 1883)
MQTT_QOS = os.getenv('MQTT_QOS', 1)
MQTT_ID = os.getenv('MQTT_ID', 'rpi-ws281x')
MQTT_PREFIX = os.getenv('MQTT_PREFIX', 'rpi-ws281x')
MQTT_DISCOVERY_PREFIX = os.getenv('MQTT_DISCOVERY_PREFIX',
                                  'homeassistant')

MQTT_STATUS_TOPIC = '%s/alive' % MQTT_PREFIX
MQTT_STATE_TOPIC = '%s' % MQTT_PREFIX
MQTT_COMMAND_TOPIC = '%s' % MQTT_PREFIX
MQTT_CONFIG_TOPIC = '%s/light/%s' % (MQTT_DISCOVERY_PREFIX,
                                            MQTT_PREFIX)

MQTT_PAYLOAD_ONLINE = '1'
MQTT_PAYLOAD_OFFLINE = '0'

# global states
#iteriere durch led segments und füge in jedes segment ein current dict ein
#current dict enthält die aktuellen Werte für das Segment
#current definieren

current = []
for segment in LED_SEGMENTS:
    current_instance = {
        'state': 'OFF',
        'color': {'r': 255, 'g': 255, 'b': 255},
        'brightness': 255,
        'effect': 'effect_solid_segment'
    }
    current.append(current_instance)

#effect_processes: List[multiprocessing.Process] = []
#for segment in LED_SEGMENTS:
#    effect_processes.append(multiprocessing.Process())

effect_process = [None] * len(LED_SEGMENTS)  # Assuming LED_SEGMENTS defines the segments


effect_active = []
for segment in LED_SEGMENTS:
    effect_active.append(multiprocessing.Process())

# key is actually a function name
effects_list = {
    'effects': {
        'effect_theater_chase_rainbow': 'Theater Rainbow',
        'effect_rainbow_cycle': 'Rainbow'
    },
    'color_effects': {
        'effect_solid': 'Solid',
        'effect_solid_segment': 'Solid Segment',
        'effect_knight_rider': 'Knight Rider'
    }
}

strip_type_by_name = {
    "BGR": ws.WS2811_STRIP_BGR,
    "BRG": ws.WS2811_STRIP_BRG,
    "GBR": ws.WS2811_STRIP_GBR,
    "GRB": ws.WS2811_STRIP_GRB,
    "RBG": ws.WS2811_STRIP_RBG,
    "RGB": ws.WS2811_STRIP_RGB,
    "RGBW": ws.SK6812_STRIP_RGBW,
    "RBGW": ws.SK6812_STRIP_RBGW,
    "GRBW": ws.SK6812_STRIP_GRBW,
    "GBRW": ws.SK6812_STRIP_GBRW,
    "BRGW": ws.SK6812_STRIP_BRGW,
    "BGRW": ws.SK6812_STRIP_BGRW,

}

# error checking
LED_CHANNEL = int(LED_CHANNEL)
LED_COUNT = int(LED_COUNT)
LED_FREQ_HZ = int(LED_FREQ_HZ)
LED_DMA_NUM = int(LED_DMA_NUM)
LED_GPIO = int(LED_GPIO)
LED_BRIGHTNESS = int(LED_BRIGHTNESS)
LED_INVERT = int(LED_INVERT)
LED_STRIP_TYPE = strip_type_by_name.get(LED_STRIP_TYPE)

if LED_COUNT is None:
    raise ValueError('LED_COUNT is required env parameter')

if LED_GPIO is None:
    raise ValueError('LED_GPIO is required env parameter')

if not 1 <= LED_BRIGHTNESS <= 255:
    raise ValueError('LED_BRIGHTNESS must be between 1-255')

if LED_FREQ_HZ != 800000 and LED_FREQ_HZ != 400000:
    raise ValueError('LED_FREQ_HZ must be 800khz or 400khz')

if LED_DMA_NUM > 14 or LED_DMA_NUM < 0:
    raise ValueError('LED_DMA_NUM must be between 0-14')

if LED_STRIP_TYPE is None:
    raise ValueError('LED_STRIP_TYPE must be one of %s', ', '.join(strip_type_by_name.keys()))


def effect_list_string():
    global effects_list
    ret = []

    for effect_name in effects_list['effects'].values():
        ret.append(effect_name)

    for effect_name in effects_list['color_effects'].values():
        ret.append(effect_name)

    return ret


def get_fn(name):
    for (effect_fn, effect_name) in effects_list['effects'].items():
        if effect_name == name:
            return effect_fn

    for (effect_fn, effect_name) in effects_list['color_effects'].items():
        if effect_name == name:
            return effect_fn

    return None


def get_fn_pretty(fn):
    if effects_list['effects'].get(fn) is not None:
        return effects_list['effects'].get(fn)

    if effects_list['color_effects'].get(fn) is not None:
        return effects_list['color_effects'].get(fn)

    return None


def on_mqtt_message(mqtt, data, message):    
    payload = json.loads(str(message.payload.decode('utf-8')))
    print('Message received ', payload)

    global current, effect_active, effect_process
    response = {}
    #MQTT Message auslesen und in die Segmente schreiben
    for segment in LED_SEGMENTS:
        print(segment)
        segment_name = 'segment_%d_%d' % (segment[0], segment[1])
        segment_count = LED_SEGMENTS.index(segment)
        print(message.topic)
        if message.topic == '%s/%s/command' % (MQTT_COMMAND_TOPIC, segment_name):
            if payload['state'] == 'ON' or payload['state'] == 'OFF':
                if current[segment_count]['state'] != payload['state']:
                    print("Turning %s" % payload['state'])

                    # set global state
                    current[segment_count]['state'] = payload['state']

                # terminate active effect
                if effect_active[segment_count]:
                    if effect_process[segment_count] is not None:
                        effect_process[segment_count].terminate()
                        effect_process[segment_count] = None  # Optionally reset the entry after termination
                    effect_active[segment_count] = False

                # power on led strip
                if current[segment_count]['state'] == 'ON':
                    # extract fields from payload
                    if 'effect' in payload:
                        fn = get_fn(payload['effect'])

                        if fn is None:
                            response['error'] = "Unsupported effect '%s'" % payload['effect']

                        else:
                            # set global efect
                            current[segment_count]['effect'] = fn

                    if 'brightness' in payload:
                        if 0 <= payload['brightness'] <= 255:
                            # set global brightness
                            current[segment_count]['brightness'] = payload['brightness']
                        else:
                            response['error'] = "Invalid brightness '%u'" % payload['brightness']

                    if 'color' in payload:
                        if ('r' in payload['color'] and 0 <= payload['color']['r'] <= 255) \
                            and ('g' in payload['color'] and 0 <= payload['color']['g'] <= 255) \
                                and ('b' in payload['color'] and 0 <= payload['color']['b'] <= 255):
                            # set global color
                            current[segment_count]['color'] = payload['color']
                        else:
                            response['error'] = "Invalid color payload"

                    response['effect'] = get_fn_pretty(current[segment_count]['effect'])
                    response['brightness'] = current[segment_count]['brightness']
                    response['color'] = current[segment_count]['color']

                    # efects with color
                    if current[segment_count]['effect'] == 'effect_solid_segment':
                        print('Setting new solid color: %s' %
                            current[segment_count]['color'])
                        effect_solid_segment(strip, current[segment_count]['color'], current[segment_count]['brightness'], segment[0], segment[1])
                    elif current[segment_count]['effect'] in effects_list['color_effects']:
                        print('Setting new color effect: "%s"' %
                            get_fn_pretty(current[segment_count]['effect']))
#Basierend auf dem aktuellen segment count das effect_process[] starten                                
                        effect_process[segment_count] = \
                            multiprocessing.Process(target=loop_function_call, args=(
                                current[segment_count]['effect'], strip, current[segment_count]['color'], current[segment_count]['brightness'], segment[0], segment[1]))
                        effect_process[segment_count].start()
                        effect_active[segment_count] = True

                    # efects not dependant on the color
                    elif current[segment_count]['effect'] in effects_list['effects']:
                        print('Setting new effect: "%s"' %
                            get_fn_pretty(current[segment_count]['effect']))

                        effect_process[segment_count] = \
                            multiprocessing.Process(target=loop_function_call,
                                                    args=(current[segment_count]['effect'], strip, 30))
                        effect_process[segment_count].start()
                        effect_active[segment_count] = True

                    else:
                        response['error'] = \
                            'Invalid request: A color or a valid effect has to be provided'

                else: #Turn off LEDS
                    #set_segment_color(strip, 0x000000, )
                    effect_solid_segment(strip, {'r': 0, 'g': 0, 'b': 0}, 0, segment[0], segment[1])

                response['state'] = current[segment_count]['state']

            else:
                response['state'] = 'none'
                response['error'] = "Invalid request: Missing/invalid 'state' field"

            if 'error' in response:
                print(response['error'])

                current[segment_count]['state'] = 'OFF'
                response['state'] = current[segment_count]['state']

            response = json.dumps(response)
            current_state_topic = '%s/%s/state' % (MQTT_STATE_TOPIC, segment_name)
            mqtt.publish(current_state_topic, payload=response, qos=MQTT_QOS,
                        retain=True)


def on_mqtt_connect(mqtt, userdata, flags, rc):
    if rc == 0:
        print('MQTT connected')
#durch LED_SEGMENTS iterieren und die Segmente in MQTT bekannt machen
        print(LED_SEGMENTS)
        for segment in LED_SEGMENTS:
            print(segment)
            #1 sekunde warten
            #time.sleep(1)
            segment_name = 'segment_%d_%d' % (segment[0], segment[1])
            segment_count = LED_SEGMENTS.index(segment)
            print("Segment count")
            print(segment_count)
            discovery_data = json.dumps(
                {
                'name': '%s_%s' % (MQTT_ID, segment_name),
                'schema': 'json',
                'command_topic': '%s/%s/command' % (MQTT_COMMAND_TOPIC, segment_name),
                'state_topic': '%s/%s/state' % (MQTT_STATE_TOPIC, segment_name),
                'availability_topic': MQTT_STATUS_TOPIC, 
                'payload_available': MQTT_PAYLOAD_ONLINE,
                'payload_not_available': MQTT_PAYLOAD_OFFLINE,
                'qos': MQTT_QOS,
                'brightness': True,
                'rgb': True,
                'color_temp': False,
                'effect': True,
                'effect_list': effect_list_string(),
                'optimistic': False,
                'unique_id': '%s_%s' % (MQTT_ID, segment_name),
                'device':{
                    'identifiers':[
                        'Neopixel'
                        ],
                    'name': 'Neopixel LED Strip',
                    'sw_version': '1.0.0',
                    'manufacturer': 'Budgie',
                    'model': 'AAAAAA'
                    }
            }
            )

            mqtt.subscribe('%s/%s/command' % (MQTT_COMMAND_TOPIC, segment_name))
            mqtt.publish(MQTT_STATUS_TOPIC, payload=MQTT_PAYLOAD_ONLINE,
                         qos=MQTT_QOS, retain=True)
            mqtt.publish('%s/%s/config' % (MQTT_CONFIG_TOPIC, segment_name),
                         payload=discovery_data, qos=MQTT_QOS, retain=True)

            if current[segment_count]['state'] == 'ON':
                response = {
                    'state': current['state'],
                    'color': current['color'],
                    'effect': get_fn_pretty(current['effect']),
                    'brightness': current['brightness']
                }
            else:
                response = {'state': current[segment_count]['state']}

            response = json.dumps(response)
            current_state_topic = '%s/%s/state' % (MQTT_STATE_TOPIC, segment_name)
            mqtt.publish(current_state_topic, payload=response, qos=MQTT_QOS,
                        retain=True)
    else:
        print('MQTT connect failed:', rc)


print('Setting up %d LEDS on pin %d' % (LED_COUNT, LED_GPIO))

# Create NeoPixel object with appropriate configuration.
strip = Adafruit_NeoPixel(
    LED_COUNT,
    LED_GPIO,
    LED_FREQ_HZ,
    LED_DMA_NUM,
    LED_INVERT,
    LED_BRIGHTNESS,
    LED_CHANNEL,
    LED_STRIP_TYPE
)

#effect_solid_init(LED_COUNT)

# Intialize the library (must be called once before other functions).
strip.begin()
set_all_leds_color(strip, 0x000000)

mqtt = paho.Client(paho.CallbackAPIVersion.VERSION1, MQTT_ID)


mqtt.on_message = on_mqtt_message
mqtt.on_connect = on_mqtt_connect

mqtt.will_set(MQTT_STATUS_TOPIC, payload=MQTT_PAYLOAD_OFFLINE,
              qos=MQTT_QOS, retain=True)
mqtt.username_pw_set(MQTT_USER, MQTT_PASSWORD)
mqtt.connect(MQTT_BROKER, MQTT_PORT)
mqtt.loop_start()


def loop_function_call(function, *args):
    while True:
        if isinstance(function, str):
            globals()[function](*args)
        else:
            function(*args)


try:
    loop_function_call(time.sleep, 0.1)
except KeyboardInterrupt:

    pass
finally:

    set_all_leds_color(strip, 0x000000)
    mqtt.disconnect()
    mqtt.loop_stop()
    try:
        effect_process.terminate()
    except AttributeError:
        pass
