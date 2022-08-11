#!/bin/sh

echo "test"
python  "test.py" ja_core_news_lg ja_core_news_trf "output_from_spacy/model-best" "output_from_spacy_trf/model-best" "output_noref/model-best" "output_noref_trf/model-best" 

cmd /k 