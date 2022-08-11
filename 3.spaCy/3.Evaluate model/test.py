#filepath = "SAP_text_analysis/Corpus.TagAdjusted"
filepath = "SAP_text_analysis/Corpus.TagFocused"
#filepath = "SAP_text_analysis/text.txt"
#import mojimoji
import spacy
import re
from tqdm import tqdm
import sys
models = sys.argv[1:]
if not models:
    models = ["output_from_spacy/model-best"]
def open_extract(file):
    with open(file,encoding="UTF8") as f:
#        l = [mojimoji.zen_to_han(re.sub(r"\u3000|\n$","",_), kana=False) for _ in f.readlines() if _]
        l = [re.sub(r"\u3000|\n$","",_) for _ in f.readlines() if _]
    return l
def conv_m2f(text,convert):
    if convert:
        if text in [
            "COMPANY_GROUP",
            "COMPANY",
            "SCHOOL",
            "GOVERNMENT"
            ] or "ORG" in text:

            return "ORG"

        elif text in [
            "STATION",
            "FACILITY_PART",
            "ISLAND",
            "DOMESTIC_REGION",
            "LOCATION_OTHER",
            "SPORTS_FACILITY",
            "GOE_OTHER"
            ] or "LOC" in text:

            return "LOC"

        elif text in [
            "PROVINCE",
            "CITY",
            "COUNTRY"]:

            return "GPE"

        elif text in [
            "PERIOD_YEAR"
            ]:

            return "DATE"
    return text

def conv_f2m(text,convert):
#    if convert:
        
#        text = re.sub(r"(さん|ちゃん|氏|さま|様|女史)\[/PERSON\]","[/PERSON]",text)

#        text = text.replace("MONTH]","DATE]")
#        text = text.replace("TIME_PERIOD]","DATE]")
#        text = text.replace("YEAR]","DATE]")

#        text = text.replace("ADDRESS1]","GPE]")
#        text = text.replace("COUNTRY]","GPE]")
#        text = text.replace("LOCALITY]","GPE]")
#        text = text.replace("REGION@MAJOR]","GPE]")
        
#        text = re.sub(r"ORGANIZATION\S+?\]","ORG]",text)
        
#        text = text.replace("CONTINENT]","LOC]")
#        text = re.sub(r"GEO_\S+?\]","LOC]",text)

#        text = text.replace("PEOPLE]","NORP]")
#        text = text.replace("URI@URL]","URL]")
#        text = text.replace("URI@EMAIL]","EMAIL]")

#    if convert == "SpaCy":
#        pass

#    elif convert == "GinZa":
#        pass
    return text
def extract_ne(d,text):
    dic = {}
    s_bindex = 0
    s_eindex = 0
#    compltag = False
    i = text

    m = re.search(r"\[([A-Z_]+?)\](.+?)\[/[[A-Z_]+?\]",i)
    while m:
        label = m.group(1)
        ne = m.group(2)
        s_bindex = m.span()[0]
        s_eindex = s_bindex + len(ne)
        dic[(d,s_bindex)] = (s_eindex,ne,label)
        i = i.replace(m.group(),m.group(2),1)
        m = re.search(r"\[([A-Z_]+?)\](.+?)\[/[[A-Z_]+?\]",i)
#        pos = i.find("[")
    return dic

def function(file,model,convert=True,labelcomparison=False):
    l = open_extract(file)
    nlp = spacy.load(model)
    ent_in_text = {}
    ent_in_doc = {}
    dic3 = {}
    dic4 = {}
    delkeys_in_doc = []
    labels = []
    prev_text = ""
    progress = tqdm(total = len(l))
    for d,i in enumerate(l):
        progress.update()
        if i:
            text = conv_f2m("".join([prev_text,i]),convert)
        else:
            continue            
        if re.search(r"^.*(\[\S+\].*\[/\S+\].*)+?",text):
            prev_text = ""
            for k,v in extract_ne(d,text).items():
                ent_in_text[(k[0],k[1],v[0])] = (v[1:])
                labels.append(v[2])
            dic4[d]=[]
            text_without_annotation = re.sub("\[/?[A-Z_]+?\]","",text)
            doc = nlp(text_without_annotation)
            for ent in doc.ents:
                label = conv_m2f(ent.label_.upper(),convert)
                labels.append(label)
                ent_in_doc[(d,ent.start_char)] = (ent.end_char,ent.text,label)
                if labelcomparison:
                    dic3[(d,ent.end_char)] = (ent.text,label,ent.start_char)
                    dic4[d].append((ent.start_char,ent.end_char,ent.text,label))

            label = ""
        else:
            prev_text = text

    progress.close()
    labels = sorted(list(set(labels)))
    tp = {k:0 for k in labels}
    fp = {k:0 for k in labels}
    fn = {k:0 for k in labels}
    tn = {k:0 for k in labels}
    tl = {k:0 for k in labels}


    for k,v in ent_in_text.items():
        tl[v[1]] += 1

        if ent_in_doc.get((k[0],k[1])):
            delkeys_in_doc.append((k[0],k[1]))
            if ent_in_doc[(k[0],k[1])][0] == k[2] \
            and ent_in_doc[(k[0],k[1])][2] == v[1]:
                tp[v[1]] += 1

            elif ent_in_doc[(k[0],k[1])][0] < k[2] \
            and  ent_in_doc[(k[0],k[1])][2] == v[1]:
                end = ent_in_doc[(k[0],k[1])][0]
                openflag = False
                keys = []
                while end <= k[2]:
                    if ent_in_doc.get((k[0],end)):
                        if ent_in_doc[((k[0],end))][2] == v[1]:
                            openflag = True
                            keys.append((k[0],end))
                        else:
                            break
                        end = ent_in_doc[((k[0],end))][0]
                    elif k[2] == end and openflag:
                        tp[v[1]] += 1
                        delkeys_in_doc.extend(keys)
                        break        
                    else:
                        break
                if not openflag:
                    fp[v[1]] += 1
            else:
                fp[v[1]] += 1
        else:
            openflag = False
            for d in [d for d in ent_in_doc.items() if d[0][0] == k[0] and d[0][1] < k[1] and d[1][0] >= k[2]]:
                delkeys_in_doc.append(d[0])
                openflag = True
            for d in [d for d in ent_in_doc.items() if d[0][0] == k[0] and d[0][1] > k[1] and d[1][0] <= k[2]]:
                delkeys_in_doc.append(d[0])
                openflag = True
            if openflag :
                fp[v[1]] += 1
            else:
                fn[v[1]] += 1

    for keys in set(delkeys_in_doc):
        del ent_in_doc[keys] 
    for v in ent_in_doc.values():
        tn[v[2]] += 1

    with open("./"+model+".txt","w",encoding="UTF8") as f:
        f.write(f"Model\t{model}\n\n")
        print(f"Model:{model}")
        for l in labels:
            if 0 in [tp[l],fp[l],fn[l]]:
                continue    
            try:
                p = tp[l] / (tp[l] + fp[l]) 
            except ZeroDivisionError:
                p = 0
            try:
                r = tp[l] / (tp[l] + fn[l])
            except ZeroDivisionError:
                r = 0
            try:
                f1 = 2 * p * r / (p + r)
            except ZeroDivisionError:
                f1 = 0
            f.write(f"Label\t{l}\n")
            f.write(f"Precition\t{p}\n")
            f.write(f"Recall\t{r}\n")
            f.write(f"F-measure\t{f1}\n")
            f.write(f"TP:{tp[l]},FP:{fp[l]},FN:{fn[l]},TN:{tn[l]},TL:{tl[l]}\n\n")

            print(f"Label:{l}")
            print(f"Precition:{p}")
            print(f"Recall:{r}")
            print(f"F-measure:{f1}")
            print(f"TP:{tp[l]},FP:{fp[l]},FN:{fn[l]},TN:{tn[l]},TL:{tl[l]}")

        try:
            p2 = sum(tp.values()) / (sum(tp.values()) + sum(fp.values())) 
        except ZeroDivisionError:
            p2 = 0
        try:
            r2 = sum(tp.values()) / (sum(tp.values()) + sum(fn.values()))
        except ZeroDivisionError:
            r2 = 0
        try:
            f12 = 2 * p2 * r2 / (p2 + r2)
        except ZeroDivisionError:
            f12 = 0
        f.write(f"Label\tTOTAL\n")
        f.write(f"Precition\t{p2}\n")
        f.write(f"Recall\t{r2}\n")
        f.write(f"F-measure\t{f12}\n")
        f.write(f"TP:{sum(tp.values())},FP:{sum(fp.values())},FN:{sum(fn.values())},TN:{sum(tn.values())},TL:{sum(tl.values())}\n\n")
        print(f"Label:TOTAL")
        print(f"Precition:{p2}")
        print(f"Recall:{r2}")
        print(f"F-measure:{f12}")
        print(f"TP:{sum(tp.values())},FP:{sum(fp.values())},FN:{sum(fn.values())},TN:{sum(tn.values())},TL:{sum(tl.values())}")

[function(filepath,model,True,True) for model in models]