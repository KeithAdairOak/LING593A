import os
import json
#dirt = "WIKIDATA/"
config = json.load(open('config.json'))
outputpath = config['outputpath']
dirt = outputpath+"WIKIDATA\\"

def conv_filename(filename):
    filename = filename.replace("\\", '_')
    filename = filename.replace('/', '／')
    filename = filename.replace('?', '？')
    filename = filename.replace('"', '”')
    filename = filename.replace('<', '＜')
    filename = filename.replace('>', '＞')
    filename = filename.replace('❘', '｜')
    filename = filename.replace(':', '：')
    filename = filename.replace('*', '＊')
    return filename 
#dic = {}

print("read dir")
#with open("list.txt","w",encoding="utf8") as fi:
dic = {d:"" for d in os.listdir(dirt) if os.path.isdir(dirt+d) and d.startswith("Q")}

print("done")

def read_in_chunks(file_object, chunk_size=1024):
    """Lazy function (generator) to read a file piece by piece.
    Default chunk size: 1k."""
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        yield data
d = {}
d2 = {}
previous = ""

fo = open("list.txt","w",encoding="utf8")
c = 0
print("read json")
with open('id_dic_ja_en.json',encoding="utf8") as f:
    for piece in read_in_chunks(f):
    
        lines = (previous + str(piece)).split('"}},')
        previous = lines[-1]

        for l in lines[:-1]:
            if l[0] == "{":
                pass
            else:
               l = "{" + l

            if l[-3:] == '"}}}':
                pass
            else:
               l = l+'"}}}'

            print(l)
            tbl = json.loads(str(l)).items()
            for k,v in tbl:
                if k in dic:
                    print(k,v)
                    fo.write("\t".join([k,v["ja"]["labels"],v["ja"]["descriptions"],v["en"]["labels"],v["en"]["descriptions"]])+"\n") 
exit()