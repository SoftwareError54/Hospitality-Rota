# Hospitality-Rota
Attempting to solve the problem of rota generation in the context of hospitality. This code was written with the aid of generative AI, to solve constraints using CSV and CMV algorithms.

The repository currently contains a file featuring a CMV algorithm, a CSP algorithm, and a GUI.

Staff lists and skills are hard coded within the CMV and CSP files along with a default availability. The GUI is used to define staff member availability which is stored as a Json file on the user's root directory for persistance.
GUI shifts are split into morning and evening shift rotations for simplicity and user inference to case by case relevance.

With availability saved, a "rota" can be generated and sense checked by the user. CSV functions are currently used by the "GUI" code but can be exchanged for "CSP" functions.
