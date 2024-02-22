# TickGen - v_0.1.2024-02-22

import sys, json
from enum import Enum
from zipfile import ZipFile

class RestStyle(Enum):
    HEX = 0
    INT = 1
    STRING = 2

class PlaceholderType(Enum):
    SFX = 0
    ASYNC_SUB_CALL = 1

# Configuration ====================================

# rest_style = RestStyle.INT
placeholder_type = PlaceholderType.SFX
include_metronome_helper = False

cue_placeholder_sfx = 'play_sfx 0x1000291' # Cowbell
cue_placeholder_async_sub_call = 'async_call subHere'

sub_name_engine_swap = 'swapEngine'
sub_name_starting_game = 'startingGame'
sub_name_default_game_setup = 'defaultGameSetup'

engineIDs_start_of_name = 'SCENE_'

value_quarter = '0x30'
value_half = '0x60'

# Project Importing ================================

def select_file():
    input_file = None
    if len(sys.argv) >= 2:
        input_file = sys.argv[1]
    else:
        print('Please select a .rhre3 file to convert:')
        input_file = input()
    return input_file

def load_remix_RHRE(input_file):
    """Loads and returns a remix's json data from a rhre3 file."""
    remix_json = None
    with open(input_file, 'rb') as f:
        magic = f.read(2)
        if magic == b'PK':
            remix_json = json.load(ZipFile(input_file).open('remix.json'))
        elif magic == b'{':
            remix_json = open(input_file, 'r')
        else:
            print('Invalid file type. Please select a .rhre3 file.')
            sys.exit()
    return remix_json

# Data Extraction - RHRE ===========================

def get_gamecues_for_section_RHRE(remix_json, section_start, section_end):
    """Gathers cue entities from a given game section. (note: ignores special cues)

    Args:
        remix_json (json): Remix Data [RHRE]
        section_start (float): Beat value that marks start of section
        section_end (float): Beat value that marks end of section

    Returns:
        list: List of game cue entities
    """
    gamecues = []
    for cue in remix_json['entities']:
        if cue['beat'] >= section_start and cue['beat'] < section_end:
            if not cue['datamodel'].startswith('special'):
                gamecues.append(cue)
    return gamecues

def get_subtitle_entities_RHRE(remix_json):
    """Gets subtitle entities from a remix."""
    subtitle_entities = []
    for cue in remix_json['entities']:
        if cue['datamodel'] == 'specialVfx_subtitleEntity':
            subtitle_entities.append(cue)
    return subtitle_entities

def get_subtitles_RHRE(subtitle_entities):
    """Gets list of subtitles from a list of subtitle entities."""
    subtitles = []
    for cue in subtitle_entities:
        subtitles.append(cue['subtitle'])
    return subtitles

# Remix Building - Tickflow ===========================

def build_game_section_from_gamecues(section_cues):
    """Builds a game section from a section of cue entities.

    Args:
        section_cues (list): List of cue entities for one minigame

    Returns:
        string: Tickflow for a game's cue section
    """
    game_section_tickflow = ''
    for i in range(0, len(section_cues)):
        # TODO: Game cue lookup/replacement will go here
        if(placeholder_type == PlaceholderType.SFX):
            game_section_tickflow += cue_placeholder_sfx + '\n'
        elif(placeholder_type == PlaceholderType.ASYNC_SUB_CALL):
            game_section_tickflow += cue_placeholder_async_sub_call + '\n'

        if i+1 < len(section_cues):
            length = section_cues[i+1]['beat'] - section_cues[i]['beat']
            length = length * 48
            # TODO: Add switch case for different rest styles
            length = str(int(length))
            game_section_tickflow += f'rest {length}\n'
        else:
            game_section_tickflow += 'stop\n\n'
    return game_section_tickflow

def build_game_swaps(subtitle_entities):
    """Builds game swaps from a list of subtitle entities.

    Args:
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

    for subtitle in subtitles:
        # Game start setup
        if(num_loaded != 0):
            game_swap_tickflow += f'call {sub_name_engine_swap}\n'
            game_swap_tickflow += f'engine {engineIDs_start_of_name}{subtitle}\n'
            game_swap_tickflow += 'sub 4\n'
            game_swap_tickflow += '0x29<2>\n'
            game_swap_tickflow += 'async_call section' + str(index + 1).zfill(2) + '\n'
        else:
            game_swap_tickflow += f'rest {value_quarter}\n'
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
                    game_swap_tickflow += 'async_call ' + gamename + '_slot' + str(swap_index) + '\n'
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
            length = length * 48
            # convert length to hex
            length = str(int(length))
            game_swap_tickflow += f'rest {length}\n'
            current_beat = next_beat

        game_swap_tickflow += '\n'
        index += 1

    # TODO: Calculate final rest value from last swap to end of remix
    return game_swap_tickflow

def build_remix_sections(remix_json, subtitleEntities):
    """Builds game sections from a list of cue entities.

    Args:
        remix_json (json): Remix data from RHRE3
        subtitleEntities (list): List of subtitle entities

    Returns:
        list: List of cue entities
    """
    remix_sections_tickflow = ''
    index = 1
    for section in subtitleEntities:
        if index == 1:
            remix_sections_tickflow += f'{sub_name_starting_game}:\n'
            remix_sections_tickflow += '0x8F 3\n'
            remix_sections_tickflow += f'fade<1> 7, 1, {value_quarter}\n'
            remix_sections_tickflow += f'rest {value_half}\n'
            remix_sections_tickflow += 'input 1\n'
            remix_sections_tickflow += 'async_sub 0x53\n'
            remix_sections_tickflow += f'rest {value_half}\n'
            currentCues = get_gamecues_for_section_RHRE(remix_json, 0, subtitleEntities[1]['beat'])
            remix_sections_tickflow += build_game_section_from_gamecues(currentCues)
        else:
            section_start = section['beat']
            section_end = section_end = remix_json['entities'][-1]['beat']
            if index < len(subtitle_entities):
                section_end = subtitleEntities[index]['beat']
            remix_sections_tickflow += f'section{index:02}:\n'
            remix_sections_tickflow += f'call {sub_name_default_game_setup}\n'
            if(include_metronome_helper):
                remix_sections_tickflow += 'async_call metronome\n'
            currentCues = get_gamecues_for_section_RHRE(remix_json, section_start, section_end)
            remix_sections_tickflow += build_game_section_from_gamecues(currentCues)
        index += 1
    return remix_sections_tickflow


# Main =============================================

if __name__ == '__main__':
    print('============= TickGen =============')
    input_file = select_file()
    remix_json = load_remix_RHRE(input_file)
    subtitle_entities = get_subtitle_entities_RHRE(remix_json)

    swaps = build_game_swaps(subtitle_entities)
    sections = build_remix_sections(remix_json, subtitle_entities)

    with open('remix_swaps.txt', 'w') as f:
        f.write(swaps)
    with open('remix_sections.txt', 'w') as f:
        f.write(sections)

    print('============= Done :) =============')
