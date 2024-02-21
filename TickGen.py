# TickGen - v_0.0.2024-02-21

import sys, json
from zipfile import ZipFile

# function that creates cues for a section
def collectCuesForSection(remix_json, sectionStart, sectionEnd):
    sectionCues = []
    for cue in remix_json["entities"]:
        if cue["beat"] >= sectionStart and cue["beat"] < sectionEnd:
            if not cue["datamodel"].startswith("special"):
                sectionCues.append(cue)
    return sectionCues

# function that builds cues for a section
def buildCuesForSection(cueFile, sectionCues):
    for i in range(0, len(sectionCues)):
        cueFile.write("play_sfx 0x1000291\n") # temporary
        if i+1 < len(sectionCues):
            length = sectionCues[i+1]["beat"] - sectionCues[i]["beat"]
            length = length * 48
            length = str(int(length))
            cueFile.write("rest " + length + "\n\n")
        else:
            cueFile.write("stop\n")
            cueFile.write("\n\n")

# Load - RHRE3 file -----------------------------------
print("======== TickGen ========")
if len(sys.argv) >= 2:
    input_file = sys.argv[1]
else:
    print("Please select a .rhre3 file to convert:")
    input_file = input()

# Load - Remix Data -----------------------------------
remix_json = None
with open(input_file, "rb") as f:
    magic = f.read(2)
    if magic == b"PK":
        remix_json = json.load(ZipFile(input_file).open("remix.json"))
    elif magic == b"{":
        remix_json = open(input_file, "r")
    else:
        print("Invalid file type. Please select a .rhre3 file.")
        sys.exit()

# Extract - Game Swaps -----------------------------------------
swapFile = open("swaps.txt", "w")

subtitles = []
subtitleEntities = []
for cue in remix_json["entities"]:
    if cue["datamodel"] == "specialVfx_subtitleEntity":
        subtitles.append(cue["subtitle"])
        subtitleEntities.append(cue)

# Array to keep track of games loaded in each slot
slots = ["", "" , "", ""]
numLoaded = 0
index = 0
currentBeat = 0

for subtitle in subtitles:
    # Game start setup
    if(numLoaded != 0):
        swapFile.write("call swapEngine\n")
        swapFile.write("engine engID_" + subtitle + "\n")
        swapFile.write("sub 4\n")
        swapFile.write("0x29<2>\n")
        swapFile.write("async_call section" + str(index + 1).zfill(2) + "\n")
        # tmp
        # swapFile.write("async_call tmpDefault\n")
    else:
        swapFile.write("rest quarter\n")
        swapFile.write("async_call startingGame\n")

    # Game Swapping
    if(numLoaded >= 2):
        # check if there's a game 4 from now
        if index+2 < len(subtitles):
            # Get name of game to swap in
            gamename = subtitles[index+2]

            # Only swap if the game is not already loaded
            if not gamename in slots:
                # Rank priority of slots
                priority = [1000] * numLoaded
                for i in range(0, numLoaded):
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
                toSwapIndex = priority.index(max(priority))
                print(slots, priority)
                # Swap the game
                swapFile.write("async_call " + gamename + "_slot" + str(toSwapIndex) + "\n")
                # Update the slot
                slots[toSwapIndex] = gamename

    # Initial 4 slots
    if(numLoaded < 4):
        slots[numLoaded] = subtitle
        numLoaded += 1

    # Determine amount of rest before next game
    if index + 1 < len(subtitles):
        nextBeat = subtitleEntities[index+1]["beat"]
        length = nextBeat - currentBeat
        length = length * 48
        # convert length to hex
        length = str(int(length))
        swapFile.write("rest " + length + "\n")
        currentBeat = nextBeat

    swapFile.write("\n")
    index += 1

# Extract - Cue Data -----------------------------------------
cueFile = open("cues.txt", "w")

index = 1
for section in subtitleEntities:
    if index == 1:
        cueFile.write("startingGame:\n")
        cueFile.write("0x8F 3\n")
        cueFile.write("fade<1> 7, 1, quarter\n")
        cueFile.write("rest half\n")
        cueFile.write("input 1\n")
        cueFile.write("async_sub 0x53\n")
        cueFile.write("rest half\n\n")
        currentCues = collectCuesForSection(remix_json, 0, subtitleEntities[1]["beat"])
        buildCuesForSection(cueFile, currentCues)
    elif index < len(subtitleEntities):
        cueFile.write("section" + str(index).zfill(2) + ":\n")
        cueFile.write("call defaultGameSetup\n")
        cueFile.write("// async_call metronome\n")
        currentCues = collectCuesForSection(remix_json, section["beat"], subtitleEntities[index]["beat"])
        buildCuesForSection(cueFile, currentCues)
    else:
        cueFile.write("section" + str(index).zfill(2) + ":\n")
        cueFile.write("call defaultGameSetup\n")
        cueFile.write("// async_call metronome\n")
        currentCues = collectCuesForSection(remix_json, section["beat"], remix_json["entities"][-1]["beat"])
        buildCuesForSection(cueFile, currentCues)

    index += 1


# Close Files
swapFile.close()
cueFile.close()
print("======== Done :) ========")


