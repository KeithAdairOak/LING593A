from qwikidata.entity import WikidataItem
from qwikidata.json_dump import WikidataJsonDump
from qwikidata.entity import WikidataEntity
from qwikidata.utils import pairwise

from qwikidata.utils import dump_entities_to_json
import time
import json
import re
import os
import sys
from typing import IO, Any, Dict, Iterator, List, Optional, Tuple, Iterable 
import psutil
config = json.load(open('config.json'))
outputpath = config['outputpath']
rdata = "WIKIDATA\\"


def dump_entities_to_json(entities: Iterable[WikidataEntity], out_fname: str) -> None:
    """Write entities to JSON file.

    Parameters
    ----------
    entities
      An iterable of instances of WikidataEntity
    out_fname
      Output file name
    """
    with open(out_fname, "w", encoding='UTF-8') as fp:
        fp.write("[\n")
        for ent_lo, ent_hi in pairwise(entities):
            ent_str = json.dumps(ent_lo._entity_dict,ensure_ascii=False)
            fp.write("{},\n".format(ent_str))
        ent_str = json.dumps(ent_hi._entity_dict,ensure_ascii=False)
        fp.write("{}".format(ent_str))
        fp.write("\n]")

P_INSTANCE_OF = "P31"
LANG = "ja"
JSON = ".json"
HEAD = '^\{"type":"item"'
label = re.compile(HEAD+'.*?"labels":{.*?"'+LANG+'":')

class WikidataDumpQuick(WikidataJsonDump):
    """Class for Wikidata JSON dump files.

    Represents a json file from https://dumps.wikimedia.org/wikidatawiki/entities.
    File names are of the form "wikidata-YYYYMMDD-all.json[.bz2|.gz]".  The file is a single JSON
    array and there is one element (i.e. item or property) on each line with the first and
    last lines being the opening and closing square brackets.  This class can handle bz2 or gz
    compressed files as well as the uncompressed json files.

    Parameters
    ----------
    filename: str
      The wikidata JSON dump file name (e.g. `my_data_dir/wikidata-20180730-all.json.bz2`)
    """
    def __init__(self, filename: str,p:int): 
        super().__init__(filename) 
        self.p = p

    def __iter__(self) -> Iterator[Dict]:
        """Generate lines from JSON dump file."""
        b = self.p
        with self._open_dump_file() as fp:
            fp.seek(b)
            for linebytes in fp:
                b += len(linebytes)
                linebytes = linebytes.decode("utf-8").rstrip(",\n")
                if linebytes in ["[", "]"]:
                    continue
                yield linebytes

def is_instance_of(instance,entity_dict):
    if "claims" in entity_dict:
        if P_INSTANCE_OF in entity_dict["claims"]:
            for e1 in entity_dict["claims"][P_INSTANCE_OF]:
                if "mainsnak" in e1:
                    e1 = e1["mainsnak"]
                    if "datavalue" in e1:
                        e1 = e1["datavalue"]
                        if "value" in e1:
                            e1 = e1["value"]
                            if e1.get("id") == instance:
                                return True
    return False

def dump(instance,input,i,dic):
    if len(input) > 1:

        if not os.path.exists(outputpath):
            os.mkdir(outputpath)
        if not os.path.exists(outputpath+rdata):
            os.mkdir(outputpath+rdata)
        path = outputpath+rdata+instance
#        path = "WIKIDATA/"+instance
        if not os.path.exists(path):
            os.mkdir(path)
        fname = path+"/"+instance+"_"+str(i)+JSON
        if os.path.exists(fname):
            pass
        else:
            dump_entities_to_json(input, fname)
            print("dumped "+fname)
        return []
    else:
        return input

def extract_lang(lang,dic,key):
    if key in dic:
        if any([len(k) > 3 for k in dic[key] if k.startswith(lang)]):
            dic[key] = {k:v for k,v in dic[key].items() if k.startswith(lang)} 
        elif lang in dic[key]:
            dic[key] = {lang:dic[key][lang]}
        else:
            dic[key] = {"en":dic[key].get("en")}
    return dic
def extract_desc(lang,dic,key):
    if key in dic:
        if lang in dic[key]:
            if dic[key][lang]:
#            try:
#                "value" in dic[key][lang]
#            except TypeError:
#                print(dic[key][lang])
                if "value" in dic[key][lang]:
                    if dic[key][lang]["value"]:
                        return dic[key][lang]["value"]
        return ""
# create an instance of WikidataJsonDump
wjd_dump_path = "latest-all.json.bz2"
tbl = {}
processed = [0]
proc = 0
if len(processed) > 1:
    proc = sorted(set(processed))[-2]
    
wjd = WikidataDumpQuick(wjd_dump_path,proc)

# create an iterable of WikidataItem representing politicians
humans = []
count = 0
t1 = None
extract = {}
id_dict = {}
for ii, entity_str in enumerate(wjd):
    if t1 == None:
        t1 = time.time()
    if len(entity_str) > 0:
        pass
    else:
        continue
    entity_dict = json.loads(entity_str)
    if entity_dict["type"] == "item":
        if entity_dict["labels"].get(LANG):
            if P_INSTANCE_OF in entity_dict["claims"]:
                entity_dict = extract_lang(LANG,entity_dict,"labels")
                entity_dict = extract_lang(LANG,entity_dict,"descriptions")
                entity_dict = extract_lang(LANG,entity_dict,"aliases")
                entity_dict = extract_lang(LANG,entity_dict,"sitelinks")
                entity = WikidataItem(entity_dict)
                for e1 in entity_dict["claims"][P_INSTANCE_OF]:
                    if "mainsnak" in e1:
                        e1 = e1["mainsnak"]
                        if "datavalue" in e1:
                            e1 = e1["datavalue"]
                            if "value" in e1:
                                e1 = e1["value"]
                                if "id" in e1:
                                    id = e1["id"]
                                    count += 1
                                    if id in extract:
                                        extract[id].append(entity)
                                    else:
                                        extract[id] = [entity]

        ja_label = extract_desc("ja",entity_dict,"labels")
        en_label = extract_desc("en",entity_dict,"labels")
        ja_desc = extract_desc("ja",entity_dict,"descriptions")
        en_desc = extract_desc("en",entity_dict,"descriptions")
        if ja_label or en_label or ja_desc or en_desc:
            tbl[entity_dict["id"]] = {"ja":{"labels":ja_label,"descriptions":ja_desc},"en":{"labels":en_label,"descriptions":en_desc}}
#            print(str(ii) + entity_dict["id"],tbl[entity_dict["id"]])

    if ii % 1000 == 0:
        t2 = time.time()
        dt = t2 - t1
        print("found {} entities among {} records [records/s: {:.2f}]".format(count, ii, ii / dt ),end='\r')

    if ii % 10000 == 0:
        tmp = {k:dump(k,v,ii,entity_dict) for k,v in extract.items()}
        extract = {k:v for k,v in tmp.items() if v != []}

# write the iterable of WikidataItem to disk as JSON
tmp = {k:dump(k,v,ii,entity_dict) for k,v in extract.items()}
extract = {k:v for k,v in tmp.items() if v != []}
tmp = dump("Others",[i[0] for i in extract.values()],ii,entity_dict)
extract = {}

t2 = time.time()
dt = t2 - t1
print("found {} entities among {} records [records/s: {:.2f}]".format(count, ii+1, (ii+1) / dt ))
with open("id_dic_ja_en.json", 'w',encoding="utf8") as ofile:
    json.dump(tbl, ofile, ensure_ascii=False) 
