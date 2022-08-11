#from distutils.util import split_quoted
#from nis import match
from msilib.schema import tables
import os
import sys
import json
import glob
from textwrap import indent
import tqdm
import pandas as pd
import random
import re
config = json.load(open('config.json'))
outputpath = config['outputpath']
#outputpath = "E:\\Program Files\\Oracle\\VirtualBox\\out\\"
regex_year = "(西暦|紀元[前後])?\d+年|(\d+|元)年|\'\d{2}"
year = re.compile(regex_year) 
regex_date = "(\d?\d|[一二三四五六七八九十][一二]?)月(\d?\d|[二三]?[十]?[一二三四五六七八九])日"
date = re.compile(regex_date) 
def rule_based_matching(text,compiled,label,annotator):
    span = [m.span(1) for m in compiled.finditer(text)]
    if len(span) > 0:
        annotator[label] = span
    return annotator

def compress_spans(text,label,span,data):
    if data.get(text):
        if not (span,label) in data[text]:
            data[text].append((span[0],span[1],label))
    else:
        data[text] = [(span[0],span[1],label)]
    return data

def main():
#    tmp = glob.glob(outputpath+'keyword_articles_wikidataonly*')
#    path = glob.glob(outputpath+'keyword_articles_wikidataonly*')[-1].split("keyword_articles_wikidataonly")[-1]
#    processed_articlepath = outputpath+'keyword_articles_wikidataonly'+path+'\\'
#    extracted_texts = outputpath + 'extracted_texts'+path+'\\'
    processed_articlepath = outputpath+'keyword_articles_wikidataonly\\'
    extracted_texts = outputpath + 'extracted_texts\\'
#    annotated_articles = outputpath + 'annotated_articles\\'
 #   if not os.path.isdir(annotated_articles):
 #       try:
 #           mode = 0o755
 #           os.mkdir(annotated_articles, mode)
 #       except FileNotFoundError:
 #           print('Not found: ' + annotated_articles)
 #           exit(1)
    if not os.path.isdir(extracted_texts):
        try:
            mode = 0o755
            os.mkdir(extracted_texts, mode)
        except FileNotFoundError:
            print('Not found: ' + extracted_texts)
            exit(1)

    annotations = ["PERSON","ORG","GPE","LOC","YEAR","DATE"]
#    progress2 = tqdm.tqdm(total = len(annotations))
    
    data = {}
    c = 0
    a = 0
#    progress2 = tqdm.tqdm(total = a, leave=False)
    for annotation in annotations:
        articles = glob.glob( processed_articlepath + "\\" + annotation + "\\" + "*.json")
#        progress3 = tqdm.tqdm(total = len(articles))
        a += len(articles)
        progress2 = tqdm.tqdm(total = a, leave=False)
        progress2.update(c)    
        for article in articles:
            file = json.load(open(article,encoding="utf8"))
            for line in file:
                data = compress_spans(line[2],annotation,line[3],data)
 #           progress3.update()
            progress2.update(1)
        c = a
        progress2.close()
    count = {label:0 for label in annotations}
    summary = {label:0 for label in annotations}
    OK_data = {}

    error_data = {}
    progress2 = tqdm.tqdm(total = len(data), leave=False)
    for text,v in data.items():
        if text.endswith("。"):
            OK_span = []
            NG_span = []
            span_prev = None
            for span in [span for span in sorted(v)]:
                if span_prev:
                    if span_prev == span:
                        pass
                    elif span_prev[0] == span[0] and span_prev[1] == span[1]:
                        if span[2] == "YEAR":
                            if year.search(text[span[0]:span[1]]):
                                if span_prev in OK_span:
                                    OK_span.remove(span_prev)
                                if not span in OK_span:
                                    OK_span.append(span)
                        elif span[2] == "DATE":
                            if date.search(text[span[0]:span[1]]):
                                if span_prev in OK_span:
                                    OK_span.remove(span_prev)
                                if not span in OK_span:
                                    OK_span.append(span)
                        elif span_prev[2] == "YEAR":
                            if year.search(text[span_prev[0]:span_prev[1]]):
                                pass
                            else:
                                if not span in NG_span:
                                    NG_span.append(span)
                                if not span_prev in NG_span:
                                    NG_span.append(span_prev)
                        elif span_prev[2] == "DATE":
                            if date.search(text[span_prev[0]:span_prev[1]]):
                                pass
                            else:
                                if not span in NG_span:
                                    NG_span.append(span)
                                if not span_prev in NG_span:
                                    NG_span.append(span_prev)
                    elif int(span[0]) <= int(span_prev[0]) and int(span_prev[1]) <= int(span[1]):
                        if span_prev in OK_span:
                            OK_span.remove(span_prev)
                        if not span in OK_span:
                            OK_span.append(span)
                    elif int(span_prev[0]) <= int(span[0]) and int(span[1]) <= int(span_prev[1]):
                        pass
                        a= 1
                    elif int(span[0]) < int(span_prev[0]) and int(span_prev[0]) < int(span[1])\
                    or   int(span_prev[0]) < int(span[1]) and int(span[1]) < int(span_prev[1]):
#                        if span_prev[2] == span[2]:
#                            span_add = (span[0],span_prev[1],span[2])
#                            if span_prev in OK_span:
#                                OK_span.remove(span_prev)
#                            if not span_add in OK_span:
#                                OK_span.append(span_add))
#                        else:
                        if not span in NG_span:
                            NG_span.append(span)
                        if not span_prev in NG_span:
                            NG_span.append(span_prev)
                    elif int(span[0]) < int(span_prev[1]) and int(span_prev[1]) < int(span[1])\
                    or   int(span_prev[0]) < int(span[0]) and int(span[0]) < int(span_prev[1]):
#                        if span_prev[2] == span[2]:
#                            span_add = (span_prev[0],span[1],span[2])
#                            if span_prev in OK_span:
#                                OK_span.remove(span_prev)
#                            if not span_add in OK_span:
#                                OK_span.append(span_add))
#                        else:
                        if span[2] in ["YEAR","DATE"]:
                            if span_prev[2] == "PERSON" and \
                                (text[span_prev[0]:span_prev[1]].endswith("天皇") \
                                 or text[span_prev[0]:span_prev[1]].endswith("王")):
                                span_add = (span_prev[0],span[1],span[2])
                                if span_prev in OK_span:
                                    OK_span.remove(span_prev)
                                if not span_add in OK_span:
                                    OK_span.append(span_add)                            
                            elif span_prev[2] in ["PERSON","ORG","LOC","GPE"]:                    
                                span_add = (span_prev[1],span[1],span[2])
                                if not span_add in OK_span:
                                    OK_span.append(span_add)                            
                        else:

                            if not span in NG_span:
                                NG_span.append(span)
                            if not span_prev in NG_span:
                                NG_span.append(span_prev)
#                    elif span_prev[0] == span[1]:
#                        if span_prev[2] == span[2]:
#                            span_add = (span[0],span_prev[1],span[2])
#                            if not span_add in OK_span:
#                                OK_span.append(span_add))
#                        else:
#                            if not span in NG_span:
#                                NG_span.append(span)
#                            if not span_prev in NG_span:
#                                NG_span.append(span_prev)
#                    elif span_prev[1] == span[0]:
#                        if span_prev[2] == span[2]:
#                            span_add = (span_prev[0],span[1],span[2])
#                            if not span_add in OK_span:
#                                OK_span.append(span_add))
#                        else:
#                            if not span in NG_span:
#                                NG_span.append(span)
#                            if not span_prev in NG_span:
#                                NG_span.append(span_prev)
                    else:
                        OK_span.append(span)
                else:
                    OK_span.append(span)
#                if len(OK_span) > 0:
                span_prev = OK_span[-1]            
#                else:
 #                   span_prev = ta
            if OK_span:
                OK_data[text] = sorted(OK_span)
                for i in OK_span:
                    summary[i[2]] += 1 
            if NG_span:
                error_data[text] = sorted(NG_span)
        progress2.update(1)
    progress2.close()
    summary["TOTAL DATAPOINTS"] = sum(summary.values())
    summary["TOTAL SENTENCES"] = len(data)

    print("extract done")

    for i in annotations:
        count[i] = int(summary[i] * -0.2)
    
    t = list(OK_data.items())
    random.shuffle(t)
    
#    count_min = {}
#    for j in annotations:
#        count[j] = int(summary[j] * -0.2)
#        count_tmp = {k:v for k,v in count.items()}
    training_data = {}
#    test_data = {}
    for text,spans in t:

#        availablelabels = [label for label,c in count.items() if c < 0]

#        if all([span[2] in availablelabels for span in spans]):
#            for span in spans:
#                count[span[2]] += 1
#            test_data[text] = spans
#        else:            

        training_data[text] = spans

    with open(extracted_texts+"\\extracted_wikidataonly_train.json",'w',encoding='utf8') as f_out:
        json.dump([training_data],f_out,ensure_ascii=False,indent=2)
#    with open(extracted_texts+"\\extracted_wikidataonly_test.json",'w',encoding='utf8') as f_out:
#        json.dump([test_data],f_out,ensure_ascii=False,indent=2)
    with open(extracted_texts+"\\extracted_wikidataonly_error.json",'w',encoding='utf8') as f_out:
        json.dump([error_data],f_out,ensure_ascii=False,indent=2)
    with open(extracted_texts+"\\extracted_count.json",'w',encoding='utf8') as f_out:
        json.dump(summary,f_out,indent=4)
    with open(extracted_texts+"\\extracted_count_gaps.json",'w',encoding='utf8') as f_out:
        json.dump(count,f_out,indent=4)

    print("done")
    sys.exit()

if __name__ == '__main__':
    main()
