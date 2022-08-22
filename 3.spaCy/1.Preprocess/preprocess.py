import os
import spacy
from spacy.tokens import DocBin
import json
import glob
import tqdm
import sys
config = json.load(open('config.json'))
outputpath = config['outputpath']
div = 10
filename = "extracted_wikidataonly_train.json"
if len(sys.argv) == 2:
    div = int(sys.argv[1])
elif len(sys.argv) == 3:
    div = int(sys.argv[1])
    filename = str(sys.argv[2])
#div1 = int(sys.argv[1])
#path = glob.glob(outputpath+'extracted_texts*')[-1].split("extracted_texts")[-1]
#input = outputpath + 'extracted_texts'+path+'\\'+filename
input = outputpath + 'extracted_texts\\'+filename
#train = outputpath + 'extracted_texts'+path+'\\extracted_wikidataonly_train.json'
#test = outputpath + 'extracted_texts'+path+'\\test.json'

def read_file(path):
    with open(path,encoding="utf-8") as fm:
        return json.load(fm)[0]

nlp = spacy.blank("ja")

def create_spacy_data(data,path,div):
    db = DocBin() 
    lines = len(data)
    iter = int(lines / div)
    progress = tqdm.tqdm(total = lines,leave=False)
    count = 1
    for j,(text, annotations) in enumerate(data.items()):
        doc = nlp(text)
        ents = []
        for start, end, label in annotations:
            span = doc.char_span(start, end, label=label)
            if span:
                pass
            else:
                new_token = text[start:end]
                docstart = sum([len(t) for t in nlp(text[:start])])
                cursor = 0
                index = 0
                while span is None:
                    token = str(doc[index])
                    cursor += len(token)
                    if cursor <= docstart:
                        index += 1
                        continue
                    else:
                        while not new_token in token :
                            with doc.retokenize() as retokenizer:
                                retokenizer.merge(doc[index:index+2], attrs={"LEMMA": str(doc[index:index+2])})
                            token = str(doc[index])
                        splited = [w for w in token.partition(new_token) if w]
                        if new_token in splited[-1]:
                            st = token.rfind(new_token)
                            ed = st + len(new_token)
                            splited = [w for w in [token[:st],token[st:ed],token[ed:]] if w]
                        heads = [doc[index] for _ in range(len(splited))] 
                        with doc.retokenize() as retokenizer:
                            retokenizer.split(doc[index], splited ,heads)
                    span = doc.char_span(start, end, label=label)
            ents.append(span)
        doc.ents = ents
        db.add(doc)
        progress.update()
        if (j+1) % iter == 0 and div > count:
            db.to_disk(path.replace("#",str(count),1).replace("#",str(div),1))
            db = DocBin()
            count += 1
    else:
        db.to_disk(path.replace("#",str(count),1).replace("#",str(div),1))

print("reading json")
#data = read_file(train)
data = read_file(input)
#test_data = read_file(test)
print("done")
#print("test data")
#create_spacy_data(test_data,"./div/dev_#of#.spacy",div1)
#print("\ndone")
print("Data Convert")
create_spacy_data(data,"#of#.spacy",div)
print("\ndone")
