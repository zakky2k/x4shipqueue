X4 Foundations parser -> Excel (Equipment recipes + Hulls).
Provides basic recipes for ship hulls and thier equipment, to serve as basis of a ship building queue.
When planning shipyards, having an idea how many resources will be used building x number of ships (and thier equipment) is not immediately obvious. 
Idea is to provide the player some guidance what materials will be required in order to complete ship production queues.

What this script does
---------------------
1) Equipment recipes:
   - Reads wares.xml + modules.xml (base + extensions) from the extracted "_unpacked" tree (or raw root)
   - Extracts equipment production recipes (inputs required)
   - Normalizes names (best-effort) and exports to Excel sheets:
       Engines, Thrusters, Shields, Weapons, Turrets (+ optional All_Equipment)

2) Hulls:
   - Reads ships.xml (base + extensions) to get the canonical ship "archetypes" (buildable ship IDs)
   - Reads ship macro XML files under assets/units/size_*/macros (base + extensions)
   - Joins ships.xml ship IDs to macros using a token-subset heuristic that works across most naming patterns
   - Extracts:
       - In-game name via <identification name="{page,id}">
       - Hull HP, crew capacity
       - Slot counts via macro <connections> refs/names (engines, shields, weapons, turrets M/L)
   - Excludes masstraffic ships

Usage
-----
python x4_extract_to_excel.py --x4-root "D:\\Steam\\steamapps\\common\\X4 Foundations" --out x4_extract.xlsx --include-all-sheet

Notes
-----
- Requires extracted game data (e.g. ioTools X4 Modding Kit output) OR a tree where:
    <x4-root>/_unpacked/libraries/...
  exists. If _unpacked doesn't exist, the script will use x4-root directly.
