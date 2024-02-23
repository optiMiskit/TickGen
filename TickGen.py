# TickGen - v_0.1.2024-02-23

import sys, json
from enum import Enum
from zipfile import ZipFile

# Enums ============================================
class TickStyle(Enum):
    HEX = 0     # example - 0xC0
    INT = 1     # example - 192
    STRING = 2  # example - quarter
class PlaceholderType(Enum):
    SFX = 0
    ASYNC_SUB_CALL = 1

# Configuration ====================================

# How tick values are written in tickflow output
# Rest splits - breaks down rest values into multiples of common rest values
tick_style = TickStyle.HEX
use_rest_splits = False

# Placeholder cue setup for non-implemented game cues
placeholder_type = PlaceholderType.SFX
cue_placeholder_sfx = 'play_sfx 0x1000291' # Cowbell
cue_placeholder_async_sub_call = 'async_call subHere'

# Adds call to metronome within game sections
include_metronome_helper = False

# Subroutine names
sub_name_engine_swap = 'swapEngine'
sub_name_starting_game = 'startingGame'
sub_name_default_game_setup = 'defaultGameSetup'

# Variable naming conventions
engineIDs_start_of_name = 'SCENE_'

# Project Importing ================================

def select_file():
    input_file = None
    if len(sys.argv) >= 2:
        input_file = sys.argv[1]
    else:
        print('Please select a .rhre3 file to convert:')
        input_file = input()
    return input_file

def load_remix_RHRE(input_file: str):
    """Loads and returns a remix's json data from a rhre3 file."""
    remix = None
    with open(input_file, 'rb') as f:
        magic = f.read(2)
        if magic == b'PK':
            remix = json.load(ZipFile(input_file).open('remix.json'))
        elif magic == b'{':
            remix = open(input_file, 'r')
        else:
            print('Invalid file type. Please select a .rhre3 file.')
            sys.exit()
    return remix

# Data Extraction - RHRE ===========================

def get_gamecues_for_section_RHRE(remix: json, section_start: float, section_end: float):
    """Gathers cue entities from a given game section. (currently ignores special cues)

    Args:
        remix (json): Remix Data [RHRE]
        section_start (float): Beat value that marks start of section
        section_end (float): Beat value that marks end of section

    Returns:
        list: List of gamecue entities
    """
    gamecues = []
    for cue in remix['entities']:
        if cue['beat'] >= section_start and cue['beat'] < section_end:
            if not cue['datamodel'].startswith('special'):
                gamecues.append(cue)
    return gamecues

def get_subtitle_entities_RHRE(remix: json):
    """Gets subtitle entities from a remix."""
    subtitle_entities = []
    for cue in remix['entities']:
        if cue['datamodel'] == 'specialVfx_subtitleEntity':
            subtitle_entities.append(cue)
    return subtitle_entities

def get_subtitles_RHRE(subtitle_entities: list):
    """Gets list of subtitles from a list of subtitle entities."""
    subtitles = []
    for cue in subtitle_entities:
        subtitles.append(cue['subtitle'])
    return subtitles

# Remix Building - Tickflow ===========================

def build_game_section_from_gamecues(section_cues: list):
    """
    Args:
        section_cues (list): List of cue entities for a game section

    Returns:
        string: Tickflow for a single game section
    """
    game_section_tickflow = ''
    for i in range(0, len(section_cues)):

        # TODO: Game cue lookup/replacement here
        if(placeholder_type == PlaceholderType.SFX):
            game_section_tickflow += f'{cue_placeholder_sfx}\n'
        elif(placeholder_type == PlaceholderType.ASYNC_SUB_CALL):
            game_section_tickflow += f'{cue_placeholder_async_sub_call}\n'

        if i+1 < len(section_cues):
            length = section_cues[i+1]['beat'] - section_cues[i]['beat']
            game_section_tickflow += convert_beats_to_rests(length, tick_style, use_rest_splits)
        else:
            game_section_tickflow += 'stop\n\n'
    return game_section_tickflow

def build_game_swaps(remix: json, subtitle_entities: list):
    """
    Args:
        remix (json): Remix data [RHRE]
        subtitle_entities (list): List of subtitle entities that specify game swaps

    Returns:
        string: Tickflow for a remix's game swap section
    """
    game_swap_tickflow = ''
    slots = ['', '' , '', ''] # Array to keep track of games loaded in each slot
    num_loaded = 0
    index = 0
    current_beat = 0
    subtitles = get_subtitles_RHRE(subtitle_entities)
    quarter_rest = convert_beats_to_rests(1, tick_style, use_rest_splits)

    for subtitle in subtitles:
        # Game start setup
        if(num_loaded != 0):
            game_swap_tickflow += f'call {sub_name_engine_swap}\n'
            game_swap_tickflow += f'engine {engineIDs_start_of_name}{subtitle}\n'
            game_swap_tickflow += 'sub 4\n'
            game_swap_tickflow += '0x29<2>\n'
            game_swap_tickflow += f'async_call section{(index+1):02}\n'
        else:
            game_swap_tickflow += quarter_rest
            game_swap_tickflow += f'async_call {sub_name_starting_game}\n'

        # Game Swapping
        if(num_loaded >= 2):
            # check if there's a game 4 from now
            if index+2 < len(subtitles):
                # Get name of game to swap in
                gamename = subtitles[index+2]
                # Only swap if the game is not already loaded
                if not gamename in slots:
                    # Rank priority of slots
                    priority = [1000] * num_loaded
                    for i in range(0, num_loaded):
                        # Give lowest priority to the current game (we never want to swap it out)
                        if slots[i] == subtitle:
                            priority[i] = 0
                        else:
                            # Priority is given based on the duration from now to the next time the game is used
                            for j in range(index + 1, len(subtitles)):
                                if slots[i] == subtitles[j]:
                                    priority[i] = j - index
                                    break
                    # Get the index of the slot with the highest priority
                    swap_index = priority.index(max(priority))
                    print(slots, priority)
                    # Swap the game
                    # TODO: Add renaming config for game loading subs
                    game_swap_tickflow += f'async_call {gamename}_slot{swap_index}\n'
                    # Update the slot
                    slots[swap_index] = gamename

        # Initial 4 slots
        if(num_loaded < 4):
            slots[num_loaded] = subtitle
            num_loaded += 1

        # Determine amount of rest before next game
        if index + 1 < len(subtitles):
            next_beat = subtitle_entities[index+1]['beat']
            length = next_beat - current_beat
            game_swap_tickflow += convert_beats_to_rests(length, tick_style, use_rest_splits)
            current_beat = next_beat

        game_swap_tickflow += '\n'
        index += 1

    # Final rest value
    remix_end = None
    for cue in remix['entities']:
        if cue['datamodel'] == 'special_endEntity':
            remix_end = cue['beat']
    game_swap_tickflow = f'{game_swap_tickflow[:-1]}{convert_beats_to_rests(remix_end - current_beat, tick_style, use_rest_splits)}'

    return game_swap_tickflow

def build_remix_sections(remix: json, subtitleEntities: list):
    """
    Args:
        remix (json): Remix data [RHRE]
        subtitleEntities (list): List of subtitle entities

    Returns:
        string: Tickflow for all game sections of a remix
    """
    remix_sections_tickflow = ''
    index = 1
    half_rest = convert_beats_to_rests(2, tick_style, use_rest_splits)
    quarter = convert_beats_to_ticks(1, tick_style)
    for section in subtitleEntities:
        if index == 1:
            remix_sections_tickflow += f'{sub_name_starting_game}:\n'
            remix_sections_tickflow += '0x8F 3\n'
            remix_sections_tickflow += f'fade<1> 7, 1, {quarter}\n'
            remix_sections_tickflow += half_rest
            remix_sections_tickflow += 'input 1\n'
            remix_sections_tickflow += 'async_sub 0x53\n'
            remix_sections_tickflow += f'{half_rest}'
            currentCues = get_gamecues_for_section_RHRE(remix, 0, subtitleEntities[1]['beat'])
            remix_sections_tickflow += build_game_section_from_gamecues(currentCues)
        else:
            section_start = section['beat']
            section_end = section_end = remix['entities'][-1]['beat']
            if index < len(subtitle_entities):
                section_end = subtitleEntities[index]['beat']
            remix_sections_tickflow += f'section{index:02}:\n'
            remix_sections_tickflow += f'call {sub_name_default_game_setup}\n'
            if(include_metronome_helper):
                remix_sections_tickflow += 'async_call metronome\n'
            currentCues = get_gamecues_for_section_RHRE(remix, section_start, section_end)
            remix_sections_tickflow += build_game_section_from_gamecues(currentCues)
        index += 1
    return remix_sections_tickflow

def convert_beats_to_rests(beat_length: float, tick_style: TickStyle, use_rest_splits: bool):
    """Converts a beat length into rests, considering style options."""
    ticks = int(beat_length * 48)
    ticks_list = []

    if ticks == 0:
        return ''
    elif use_rest_splits:
        tick_split = 192
        while ticks > 0 and tick_split > 0:
            current_total = 0
            while int(ticks - tick_split) >= 0:
                current_total += tick_split
                ticks -= tick_split
            if current_total > 0:
                ticks_list.append(current_total)
            tick_split = int(tick_split / 2)
            if tick_split == 96:  # Avoid half rests
                tick_split = int(tick_split / 2)

    else:
        ticks_list.append(ticks)

    ticks_str = ''
    for tick in ticks_list:
        ticks_str += f'rest {convert_beats_to_ticks(tick / 48, tick_style)}\n'
    return ticks_str

def convert_beats_to_ticks(beat_length: float, tick_style: TickStyle):
    """Converts a beat length to a tick value with a given style."""
    ticks = int(beat_length * 48)
    ticks_str = ''
    match tick_style:
        case TickStyle.HEX:
            ticks_str = '0x' + f'{int(ticks):x}'.upper()
        case TickStyle.INT:
            ticks_str = f"{int(ticks)}"
        case TickStyle.STRING:
            number_needed = 0
            # Choose base value
            if ticks % 192 == 0:
                number_needed = ticks / 192
                ticks_str = 'whole'
            # Avoiding half values for now, quarters will be used instead
            # elif ticks % 96 == 0:
            #     number_needed = ticks / 96
            #     ticks_str = 'half'
            elif ticks % 48 == 0:
                number_needed = ticks / 48
                ticks_str = 'quarter'
            elif ticks % 24 == 0:
                number_needed = ticks / 24
                ticks_str = 'eighth'
            elif ticks % 12 == 0:
                number_needed = ticks / 12
                ticks_str = 'sixteenth'
            elif ticks % 6 == 0:
                number_needed = ticks / 6
                ticks_str = 'thirtysecond'
            else:
                number_needed = ticks
                ticks_str = 'tick'

            # Multiply tick value if needed
            if number_needed > 1:
                ticks_str += f" * {int(number_needed)}"
            elif number_needed == 0:
                ticks_str = '0'
    return ticks_str

# Main =============================================

if __name__ == '__main__':
    print('============= TickGen =============')
    input_file = select_file()
    remix_data = load_remix_RHRE(input_file)
    subtitle_entities = get_subtitle_entities_RHRE(remix_data)

    swaps = build_game_swaps(remix_data, subtitle_entities)
    sections = build_remix_sections(remix_data, subtitle_entities)

    with open('remix_swaps.txt', 'w') as f:
        f.write(swaps)
    with open('remix_sections.txt', 'w') as f:
        f.write(sections)

    print('============= Done :) =============')
