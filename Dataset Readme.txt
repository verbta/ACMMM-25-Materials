1. Each image sa_k.jpg in /Image has one or two annotation saved in /Annotation/sa_k.json, the split is according to whether the two question have relation.
In /Annotation/sa_k.json, the data is organized as follow:
  if the corresponding image has only one Question:
  
  {
    "question": "...",
    "answer": "...",
    "visual_clues":[ 
                   {
                     "clue1": "...",
                      "reasoning": "...",
                     },
                     {"clue2": "...",
                      "reasoning": "...",
                     }
                     ...
                     ]                           
  }
  
  if the corresponding image has two Questions(The id for clue is not refresh with a new question):
  
  {
    "question": ["...", "..."],
    "answer":   ["...", "..."],
    "visual_clues":  [
                     [{"clue1": "...",
                      "reasoning": "...",
                      },
                      ...                     
                     ],
                     
                     [{"clue2": "...",
                      "reasoning": "...",
                      },
                      ...                     
                     ],
                     ...
                     ]  
  }
2. Each bbox crossponding to clue is saved in /Box_annotation with name sa_k_bbox.json(Note, each clue may have two or more bbox)
   In sa_k_bbox.json, id represents the clue idx.
   The format is [top_left_x, top_left_y, bottom_right_x, bottom_right_y].
