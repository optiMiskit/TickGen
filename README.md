# TickGen - A RHRE to Tickflow converter (wip)

## How to use this tool
1. Create your remix in RHRE3 as usual
2. Add subtitle VFX cues where you want to swap games in your remix. Set the subtitle's text to the name of the game you are switching to. [use the same name as your game swap sub]
3. Run TickGen and give it the path to your remix file.
4. Copy the tickflow from the generated .txt files into your tickflow template.

## Configuration
* At the top of the script are some configurable variables that allow you to rename or change certain parameters of the generated tickflow
* Not yet configurable (will be in the future):
  - Game swap sub naming convention (currently "gamename_slot#")

## Project Tasks
You can check current project tasks on the ![TickGen Task Board](https://github.com/users/optiMiskit/projects/3)