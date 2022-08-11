#from distutils.util import split_quoted
#from nis import match
import os
import sys
import json
import glob
import time
import re
import spacy
import tqdm
import html
import pandas as pd
import mojimoji

#ja_spacy = spacy.load("ja_core_news_sm")
#ja_ginza = spacy.load("ja_ginza")

regex_year = "(西暦|紀元[前後])?\d+年|(\d+|元)年|\'\d{2}"
year = re.compile(regex_year) 
regex_year_suffix = "^[前後間度毎目半忌次で]|ごと|ぶり|を?かけ|が?かか|を要し|も?の([歳年]月|期?間)|((\d?\d|[一二三四五六七八九十][一二]?)[かカヶケ箇個]月)"
year_suffix = re.compile(regex_year_suffix)
regex_year_prefix = "\.$"
year_prefix = re.compile(regex_year_prefix)
regex_date = "(\d?\d|[一二三四五六七八九十][一二]?)月(\d?\d|[二三]?[十]?[一二三四五六七八九])日"
date = re.compile(regex_date) 

Hiragana = re.compile("([\u3041-\u309F]+)")
Katakana = re.compile("([\u30A0-\u30FF]+)")
Kanji = re.compile("([\u4E00-\u9FFF]+)")
JapaneseScripts = "[\u3000-\u30FF\u4E00-\u9FFF]"

LatinAlphabet = re.compile("([\u0021-\u007E]+)")
Ascii = re.compile('^[\u0020-\u007E]+$')

NOUN_RELEVANT_POS = ["NOUN","PROPN","NUM"]
NOUN_POS = ["NOUN","PROPN"]

#datadir = "E:\\OneDrive - University of Arizona\\Shares\\Datasets\\WIKIDATA\\"
rawdatadir = "WIKIDATA\\"
IGNORE_KEYS = ["Category:","Template:","カテゴリ:","テンプレート:"]
config = json.load(open('config.json'))

outputpath = config['outputpath']
datadir = outputpath

import io

def compressing_spans(spanlist,annotator):
    for span in sorted(spanlist):
        if annotator.get(span[1]):
            if not span[0] in annotator[span[1]]:
                annotator[span[1]].append(span[0])
        else:
            annotator[span[1]] = [span[0]]
    return annotator

def set_span(text,linkterm,searchterm,ner,annotator,start):
    if ner.get(linkterm):
        label = "-".join([span for span in ner[linkterm]])
        spans = [((m.span()[0] + start,m.span()[1] + start),label) for m in re.finditer(re.escape(searchterm),text)]
        return compressing_spans(spans,annotator)
    else:
        return annotator
def encoding(text):
    prestart = 0
    preend = 0
    while True:
        start = text.find('&')
        end = text.find(';')        
        if start > -1 and end > -1 and end > start and prestart < start and preend < end:
            prestart = start
            preend = end
            character = html.unescape(text[start:end+1])
            text = text[:start] + character + text[end+1:]
        else:
            break
    return text
def spoil_space(text):
    while True:
        cursor = text.find(" ")
        if cursor > -1:
            m = re.search(JapaneseScripts+" "+JapaneseScripts,text[cursor-1:cursor+2])
            if m:
                text = text[:m.span()[0]+cursor] + text[m.span()[1]+cursor-2:]
            else:
                m = re.search("[\]\w] "+JapaneseScripts,text[cursor-1:cursor+2])
                if m:
                    text = text[:m.span()[0]+cursor] + text[m.span()[1]+cursor-2:]
                else:
                    m = re.search(JapaneseScripts+" [\[\w]",text[cursor-1:cursor+2])
                    if m:
                        text = text[:m.span()[0]+cursor] + text[m.span()[1]+cursor-2:]
                    else:
                        break
        else:
            break
    return text.strip()

   

def set_spans(linkterm,a,b,ner,annotator):
    if ner.get(linkterm):
        label = "-".join([span for span in ner[linkterm]])
        spans = [[(a,b),label]] 
        return compressing_spans(spans,annotator)
    else:
        return annotator

def extract_wikipedia_link(text,ner):
#    candid = {}
    annotator = {}
#    start_prev = 0
#    anchor = text
    while True:
        key = ""
        start = text.find('[[')
        text = spoil_space(text[:start]) + text[start:]
        start = text.find('[[')
        end = text.find(']]')
        if start > -1 and end > -1 and end > start:
#            start_prev = start
            while text[end+2] == ']':
                end += 1
            before = text[:start]
            after = text[end+2:]
            m = True
            while m:
                m = re.search("\[\[.+?\|(.+?)(\|.+?)?\]\]",after)
                if m:
                    after = after.replace(m.group(0),m.group(1))
            mention = text[start+2:end]
            parts = mention.split('|')
            wikilink = parts[0].strip()
            if len(parts) == 1:
                term_in_text = parts[0].strip()
            else:           
                term_in_text = parts[1].strip()
            column_1st = wikilink.split("(")[0].strip()
            column_2nd = (term_in_text[:1] + term_in_text[1:].split("(")[0]).strip()
            m = re.match("^[\u3000-\u3002・](.+)$",column_2nd)
            if m:
                column_2nd = m.group(1)
            m = re.match("^[（〈《「【〔〖〘〚](.+)[〛〙〗〕】』」》〉）]$",column_2nd)
            if m:
                column_2nd = m.group(1)
            
            if wikilink.find("#") > -1:
                pass
            elif (len(parts) == 3 and parts[-1] == "ACRONYM"):
                key = column_2nd
            elif column_1st in (before + after) and not column_2nd in (before + after):
                key = column_2nd
            elif column_2nd in (before + after) and not column_1st in (before + after):
                key = column_1st
                term_in_text = column_1st
            elif column_1st in column_2nd:
                key = column_1st
#            elif column_2nd in column_1st:
#                candid[column_2nd] = wikilink
            else:
                nameparts = column_1st.split("・")
                if len(nameparts) == 1:
                    string = nameparts[0]
                else:
                    string = nameparts[0] + ".*" + nameparts[-1]
                m = re.search(re.escape(string),term_in_text)
                if m:
                    key = m.group()
                else:
                    key = column_1st
#                    pass
#                    key = column_2nd
            key = spoil_space(key)
            term_in_text = spoil_space(term_in_text)
#            candid[key] = wikilink
#            anchor =  text[end+2:]
            if key and key in term_in_text:
                annotator = set_span(term_in_text,wikilink,key,ner,annotator,start)
            text = text[:start] + term_in_text + text[end+2:]

        else:
#            text = text[:-len(anchor)] + spoil_space(anchor)
            break
    text = spoil_space(text)
#    for searchterm,linkterm in candid.items():
#        annotator = set_spans(text,linkterm,searchterm,ner,annotator)
    return annotator,text            


########## process for rule-based matching
def rule_based_matching(text,compiled,label,annotator):
  
    spans = [m.span(0) for m in compiled.finditer(text)]
    if len(spans) > 0:
        annotator[label] = spans
    return annotator,text

def suffix_matching(text,rules,label,annotator,extend=True):
    if annotator.get(label):
        table = annotator[label].copy()
        for span in table:
            if type(rules) == set:
                for rule in rules:
                    if text[span[1]:].startswith(rule):
                        annotator[label].remove(span)
                        if extend:
                            annotator[label].append((span[0],span[1]+len(rule)))
                        break
            else:
                m = rules.match(text[span[1]:])
                if m:
                    annotator[label].remove(span)
                    if extend:
                        annotator[label].append((span[0],span[1]+len(m.group())))
    return annotator

def prefix_matching(text,rules,label,annotator,extend=True):
    if annotator.get(label):
        table = annotator[label].copy()
        for span in table:
            if type(rules) == set:
                for rule in rules:
                    if text[:span[0]].endswith(rule):
                        annotator[label].remove(span)
                        if extend:
                            annotator[label].append((span[0]-len(rule),span[1]))
                        break
            else:
                m = rules.search(text[:span[0]])
                if m:
                    annotator[label].remove(span)
                    if extend:
                        annotator[label].append((span[1]-len(m.group()),span[1]))
    return annotator

def prefix_filtering(text,rules,criteria,label,annotator):
    if annotator.get(label):
            table = annotator[label].copy()
            for span in [span for span in table if text[span[0]:span[1]].startswith(criteria)]:
                if type(rules) == set:
                    if any(text[:span[0]].endswith(rule) for rule in rules):
                        pass
                    else:
                        annotator[label].remove(span)
                else:
                    m = rules.search(text[:span[0]])
                    if m:
                        pass
                    else:
                        annotator[label].remove(span)
    return annotator

def concatenate_spans(text,label1,label2,label3,annotator,strict=True):
    labels1 = []
    labels2 = []
    for k in annotator.keys():
        if label1 in k.split("-"):
            labels1.append(k)
        if label2 in k.split("-"):
            labels2.append(k)

    for l1 in labels1:
        for l2 in labels2:
            tmp = None
            spans1 = []
            spans2 = []
            while not tmp or len(tmp) != len(annotator[label3]):
                if annotator.get(label3):
                    tmp = annotator[label3].copy()
                for span1 in annotator[l1]:
                    for span2 in annotator[l2]:
                        if strict:
                            if span1[1] == span2[0]:
                                pass
                            else:
                                continue
                        else:
                            if span1[1] < span2[0] and re.match("^([\u0020-\u002F\u201C-\u201D\u3008-\u301F\u30FB]){0,2}$",text[span1[1]:span2[0]]):
                                pass
                            else:
                                continue
                        span = (span1[0],span2[1])

                        if annotator.get(label3):
                            if not span in annotator[label3]:
                                annotator[label3].append(span)
                        else:
                            annotator[label3] = [span]
                        if not span1 in spans1:
                            spans1.append(span1)
                        if not span2 in spans2:
                            spans2.append(span2)
            for span1 in spans1:
                if span1 in annotator[l1]:
                    annotator[l1].remove(span1)
            for span2 in spans2:
                if span2 in annotator[l2]:
                    annotator[l2].remove(span2)
    return annotator

def expanding_annotator(annotator):
    
    return sorted([[l,k] for k,v in annotator.items() for l in v])



def merging_annotator(annotator_expanded,reverse):
    tmp = []
    span_superior = [(0,0),""]
    for span in sorted(annotator_expanded,reverse=reverse):
        if span == span_superior:
            continue
        elif span_superior[0][0] == span[0][0] and span_superior[0][1] == span[0][1]:
            if span[1] == "UNKNOWN":
                continue
        elif span_superior[0][0] <= span[0][0] and span_superior[0][1] >= span[0][1]:
            continue
        tmp.append(span)
        span_superior = span
    return tmp

def process(article,ner,gengo):
    with open(article,encoding='utf8') as f_in:
        #if not os.path.exists(annotated_filename):

        filestring = []
        annotation_items = {}
        file = re.sub('\n?。', "。", re.sub('\n?、\n?', "、", f_in.read())).replace("。","。\n")
        for line in file.split("\n"):
            content = line.strip()
            if "ハドソン・ストリート沿い" in content:
                a = 1

            if not content:
                continue
            elif not content.endswith("。"):
                filestring.append(content)
                continue

            text = encoding(content)
            annotator,text = extract_wikipedia_link(text,ner)
            annotator,text = rule_based_matching(text,year,"YEAR",annotator)
            annotator = suffix_matching(text,year_suffix,"YEAR",annotator,False)
            annotator = prefix_matching(text,year_prefix,"YEAR",annotator,False)
            annotator = prefix_matching(text,gengo,"YEAR",annotator)
            annotator = prefix_filtering(text,gengo,"元","YEAR",annotator)
            
            annotator,text = rule_based_matching(text,date,"DATE",annotator)
#            annotator = chunking_by_script(text,Hiragana,ner,annotator)
#            annotator = chunking_by_script(text,Katakana,ner,annotator)
 #           annotator = chunking_by_script(text,Kanji,ner,annotator)
 #           annotator = chunking_by_script(text,LatinAlphabet,ner,annotator)
                    
  #          doc1 = ja_spacy(text)
   #         annotator = chunking_by_spacy(text,doc1.noun_chunks,ja_spacy,ner,annotator)
    #        annotator = chunking_by_pos(text,doc1,ner,annotator)
     #       annotator = parsing_by_spacy(text,doc1,ner,annotator)
      #      excluder = excluding_pos(text,doc1,[])

       #     doc2 = ja_ginza(text)
        #    annotator = chunking_by_spacy(text,doc2.noun_chunks,ja_ginza,ner,annotator)
         #   annotator = chunking_by_pos(text,doc2,ner,annotator)
          #  annotator = parsing_by_spacy(text,doc2,ner,annotator)
           # excluder = excluding_pos(text,doc2,excluder)
        #    annotator = excluding_annotator(annotator,sorted(excluder))

#            annotator = concatenate_spans(text,"GENGO","YEAR","YEAR",annotator)
            annotator = concatenate_spans(text,"YEAR","DATE","DATE",annotator)
#            annotator = concatenate_spans(text,"PERSON","PERSON","PERSON",annotator)
#            annotator = concatenate_spans(text,"PERSON","ORG","ORG",annotator)
#            annotator = concatenate_spans(text,"GPE","ORG","ORG",annotator)
#            annotator = concatenate_spans(text,"LOC","ORG","ORG",annotator)                    
#            annotator = concatenate_spans(text,"ORG","ORG","ORG",annotator)
#            annotator = concatenate_spans(text,"UNKNOWN","UNKNOWN","X",annotator)
            filestring.append(text)
            if len(annotator.keys()) > 0:
                annotator_expanded = expanding_annotator(annotator)
                annotator_expanded = merging_annotator(annotator_expanded,True)
                annotator_expanded = merging_annotator(annotator_expanded,False)
                for spans in annotator_expanded:
                    annotation_items = compress_spans(text,spans[1],spans[0],annotation_items)
        return annotation_items,filestring

def compress_spans(text,label,span,annotator):
#    for span in sorted(spanlist):
    keyword = text[span[0]:span[1]]
    if annotator.get(keyword):
        if not span in annotator[keyword]:
            annotator[keyword].append((label,text,span))
    else:
        annotator[keyword] = [(label,text,span)]
    return annotator

def append_label(key,ner,label):
    if key in ner:
        if label in ner[key] \
        or label == "UNKNOWN":
            pass
        elif ner[key] == ["UNKNOWN"]:
            ner[key] = [label]
        elif label == "GPE"\
        and "LOC" in ner[key]:
            ner[key] = [label if value=="LOC" else value for value in ner[key]]
        elif label == "LOC"\
        and "GPE" in ner[key]:
            pass
        else:
            ner[key].append(label)
            ner[key].sort()
    elif all(not key.startswith(k) for k in IGNORE_KEYS):
        ner[key] = [label]
    return ner

def claim(wiki,ner,label,p):
    if p in wiki["claims"]:
        for name in wiki["claims"][p]:
            if "mainsnak" in name:
                if "datavalue" in name["mainsnak"]:
                    if "value" in name["mainsnak"]["datavalue"]:
                        if "language" in name["mainsnak"]["datavalue"]["value"]:
                            if name["mainsnak"]["datavalue"]["value"]["language"] == "ja":
                                key = name["mainsnak"]["datavalue"]["value"]["text"]
                                ner = append_label(key,ner,label)
    return ner
def conv_filename(filename):
    filename = filename.replace('\\', '＼')
    filename = filename.replace(' ', '_')
    filename = filename.replace('/', '／')
    filename = filename.replace('?', '？')
    filename = filename.replace('"', '”')
    filename = filename.replace('<', '＜')
    filename = filename.replace('>', '＞')
    filename = filename.replace('|', '｜')
    filename = filename.replace(':', '：')
    filename = filename.replace('*', '＊')
    return filename 
def main():
#    timestamp = str(pd.Timestamp.now()).replace(" ","-").replace(":","-")
#    processed_articlepath = outputpath + 'final_articles\\'
    processed_articlepath = outputpath + 'el_articles\\'
#    extracted_articles = outputpath + 'extracted_articles\\'
    plain_articles = outputpath + 'plain_articles\\'
#    keyword_articles = outputpath + 'keyword_articles_wikidataonly'+timestamp+'\\'
    keyword_articles = outputpath + 'keyword_articles_wikidataonly\\'

    ner = None
    ner_mod = {}
    if os.path.exists(outputpath + 'dictionaries\\annotation_master.json'):
        with open(outputpath + 'dictionaries\\annotation_master.json',encoding="utf8") as fm:
            ner = json.load(fm)
        
    if os.path.exists(outputpath + 'dictionaries\\annotation_master_modified.json'):
        with open(outputpath + 'dictionaries\\annotation_master_modified.json',encoding="utf8") as fmm:
            ner_mod = json.load(fmm)

        for k,v in ner_mod.items():
            ner[k] = v

    if ner:
        print("read json")
    else:
        with open("selected.txt",encoding='utf8') as fm:
            dic = {l.split()[0]:l.split()[1] for l in fm if len(l.split())} 

        ner = {}
        listdir = list(os.listdir(datadir+rawdatadir))
        progress = tqdm.tqdm(total = len(listdir))

        for di in listdir:
            if dic.get(di):
                label = dic[di]
            else:
                label = "UNKNOWN"
            for d in os.listdir(datadir+rawdatadir+di):
                with open(datadir+rawdatadir+di+"\\"+d, encoding="utf8") as fileopened:
                    try:
                        wikidata = json.load(fileopened)
                    except Exception:
                        continue

                for wiki in wikidata:
#                    if "labels" in wiki:
#                        if "ja" in wiki["labels"]:
#                            key = wiki["labels"]["ja"]["value"]
#                            ner = append_label(key,ner,label) 

#                    if "aliases" in wiki:
#                        if "ja" in wiki["aliases"]:
#                            for alias in wiki["aliases"]["ja"]:
#                                if "value" in alias:
#                                    key = alias["value"]
#                                    ner = append_label(key,ner,label)
            
#                    if "claims" in wiki:
#                        ner = claim(wiki,ner,label,"P1477")
#                        ner = claim(wiki,ner,label,"P1448")
#                        ner = claim(wiki,ner,label,"P1705")
#                        ner = claim(wiki,ner,label,"P1635")
#                        ner = claim(wiki,ner,label,"P1559")
                    if "sitelinks" in wiki:
                        if "jawiki" in wiki["sitelinks"]:
                            if "title" in wiki["sitelinks"]["jawiki"]:
                                key = wiki["sitelinks"]["jawiki"]["title"]
                                ner = append_label(key,ner,label)
            progress.update()
        with open(outputpath + 'dictionaries\\annotation_master.json',"w",encoding="utf8") as f:
            json.dump(ner,f,indent=2,ensure_ascii=False)

    gengo = set([k.split("(")[0].strip() for k,t in ner.items() if "GENGO" in t])

    if not os.path.isdir(plain_articles):
        try:
            mode = 0o755
            os.mkdir(plain_articles, mode)
        except FileNotFoundError:
            print('Not found: ' + plain_articles)
            exit(1)
#    if not os.path.isdir(extracted_articles):
#        try:
#            mode = 0o755
#            os.mkdir(extracted_articles, mode)
#        except FileNotFoundError:
#            print('Not found: ' + extracted_articles)
#            exit(1)
    article_directories = glob.glob(processed_articlepath + "*\\")
    progress2 = tqdm.tqdm(total = len(article_directories))
    filenames = []
#    counter = {}
    for article_directory in article_directories:
        if article_directory.endswith("\\dot\\"):
            articles = glob.glob(article_directory + ".*.txt")
        else:
            articles = glob.glob(article_directory + "*.txt")            
        if not os.path.isdir(keyword_articles):
            try:
                mode = 0o755
                os.mkdir(keyword_articles, mode)
            except FileNotFoundError:
                print('Not found: ' + keyword_articles)
                exit(1)
#        start = time.time()
#        progress3 = tqdm.tqdm(total = len(articles))
        for article in articles:
#            print(article.split("\\")[-1])
            annotation_items,filestring = process(article,ner,gengo)
            if not os.path.exists(plain_articles + article.split("\\")[-2]):
                os.mkdir(plain_articles + article.split("\\")[-2])
            with open(plain_articles + "\\".join(article.split("\\")[-2:]),'w',encoding='utf8') as f_out:
                f_out.write("\n".join(filestring))
            for k,items in annotation_items.items():
#                print(k)
                for item in items:
                    file = [k,item[0],item[1],item[2]]
                    filename = conv_filename(k + ".json")
                    if os.path.exists(keyword_articles + item[0] + "\\" + filename):
                        with open(keyword_articles + item[0] + "\\" + filename,'a',encoding='utf8') as f_out:
                            f_out.write(",\n")
                            json.dump(file,f_out,ensure_ascii=False)
                    elif os.path.exists(keyword_articles + item[0]):
                        try:
                            with open(keyword_articles + item[0] + "\\" + filename,'w',encoding='utf8') as f_out:
                                f_out.write("[\n")
                                json.dump(file,f_out,ensure_ascii=False)
                            filenames.append(item[0] + "\\" + filename)
                        except:
                            if os.path.exists(keyword_articles + "Error.txt"):
                                with open(keyword_articles + "Error.txt",'a',encoding='utf8') as f_out:
                                    f_out.write(filename+"\n")
                            else:
                                with open(keyword_articles + "Error.txt",'w',encoding='utf8') as f_out:
                                    f_out.write(filename+"\n")
                    else:
                        os.mkdir(keyword_articles + item[0])
                        try:
                            with open(keyword_articles + item[0] + "\\" + filename,'w',encoding='utf8') as f_out:
                                f_out.write("[\n")
                                json.dump(file,f_out,ensure_ascii=False)
                            filenames.append(item[0] + "\\" + filename)
                        except:
                            if os.path.exists(keyword_articles + "Error.txt"):
                                with open(keyword_articles + "Error.txt",'a',encoding='utf8') as f_out:
                                    f_out.write(filename+"\n")
                            else:
                                with open(keyword_articles + "Error.txt",'w',encoding='utf8') as f_out:
                                    f_out.write(filename+"\n")
        progress2.update()
    progress3 = tqdm.tqdm(total = len(filenames))
    for filename in filenames:
        with open(keyword_articles + filename,'a') as f_out:
            f_out.write('\n]')
        progress3.update()
    sys.exit()

if __name__ == '__main__':
    main()
