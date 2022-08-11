#!/bin/sh

echo "Step 1/7"
python 1.title2Id_redirect_parser.py
echo "Step 2/7"
python 2.article_parser_1.py
echo "Step 3/7"
python 3.dicts_creator.py
echo "Step 4/7"
python 4.article_parser_2.py
echo "Step 5/7"
python 5.article_parser_3_basic.py
echo "Step 6/7"
python 6.article_extractor_1.py
echo "Step 7/7"
python 7.article_extractor_2.py

cmd /k 