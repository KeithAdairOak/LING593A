python -m spacy train noref.cfg --output ./output_noref --paths.train ./train --paths.dev ./dev --gpu-id 0
python -m spacy train noref-spacy.cfg --output ./output_noref_spacy --paths.train ./train --paths.dev ./dev 
python -m spacy train noref-trf.cfg --output ./output_noref_trf --paths.train ./train --paths.dev ./dev --gpu-id 0
python -m spacy train spacy.cfg --output ./output_from_spacy --paths.train ./train --paths.dev ./dev 
python -m spacy train spacy-trf.cfg --output ./output_from_spacy_trf --paths.train ./train --paths.dev ./dev


cmd /k