import json,re,datetime,urllib.request,urllib.parse
from html.parser import HTMLParser
from pathlib import Path
SOURCE="https://dinhizmetleri.diyanet.gov.tr/kategoriler/yayinlarimiz/hutbeler/t%C3%BCrk%C3%A7e"
def safe(value):
 u=urllib.parse.urljoin(SOURCE,value.strip());p=urllib.parse.urlsplit(u)
 if p.scheme!="https" or not (p.hostname=="diyanet.gov.tr" or (p.hostname or "").endswith(".diyanet.gov.tr")):return ""
 return urllib.parse.quote(u,safe=":/?&=%#()+,;@")
class Redirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  if not safe(newurl):raise ValueError("Unsafe redirect")
  return super().redirect_request(req,fp,code,msg,headers,newurl)
def request(url,method="GET"):
 if not safe(url):raise ValueError("Unsafe source")
 req=urllib.request.Request(url,headers={"User-Agent":"MihrapSermonFeed/1.0"},method=method)
 with urllib.request.build_opener(Redirect()).open(req,timeout=40) as response:
  data=response.read(4000001) if method=="GET" else b""
  if len(data)>4000000:raise ValueError("Oversized source")
  return data
class Table(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.rows=[];self.row=None;self.cell=None;self.links=[]
 def handle_starttag(self,tag,attrs):
  attrs=dict(attrs)
  if tag=="tr":self.row=[];self.links=[]
  if tag=="td" and self.row is not None:self.cell=[]
  if tag=="a" and self.cell is not None:self.links.append(safe(attrs.get("href","")))
 def handle_data(self,data):
  if self.cell is not None:self.cell.append(data)
 def handle_endtag(self,tag):
  if tag=="td" and self.cell is not None:self.row.append(" ".join("".join(self.cell).split()));self.cell=None
  if tag=="tr" and self.row is not None:self.rows.append((self.row,self.links));self.row=None;self.cell=None
def parse(html):
 p=Table();p.feed(html);result=[]
 for cells,links in p.rows:
  for i,text in enumerate(cells[:-1]):
   if not re.fullmatch(r"\d{1,2}\.\d{2}\.\d{4}",text):continue
   day=datetime.datetime.strptime(text,"%d.%m.%Y").date();title=cells[i+1].strip()
   pdf=next((u for u in links if urllib.parse.urlsplit(u).path.lower().endswith(".pdf")),"")
   audio=next((u for u in links if urllib.parse.urlsplit(u).path.lower().endswith((".mp3",".m4a",".wav"))),"")
   if pdf and title and day<=datetime.date.today()+datetime.timedelta(days=14):result.append({"Title":title,"Day":day.isoformat(),"Date":day.strftime("%d.%m.%Y"),"Pdf":pdf,"Audio":audio})
 if len(result)<10:raise ValueError("Source list incomplete; previous feed preserved")
 return sorted(result,key=lambda x:x["Day"],reverse=True)
def main():
 path=Path("sermons.json");old=json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"items":[]}
 items=parse(request(SOURCE).decode("utf-8-sig"))
 if old["items"] and items[0]["Day"]<old["items"][0]["Day"]:raise ValueError("Source regressed; previous feed preserved")
 request(items[0]["Pdf"],"HEAD")
 if items[0]["Audio"]:request(items[0]["Audio"],"HEAD")
 known={(i["Day"],i["Pdf"]):i for i in old["items"]};known.update({(i["Day"],i["Pdf"]):i for i in items})
 out={"schemaVersion":1,"checkedAt":datetime.datetime.now(datetime.timezone.utc).isoformat(),"source":SOURCE,"items":sorted(known.values(),key=lambda x:x["Day"],reverse=True)[:500]}
 temp=path.with_suffix(".tmp");temp.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");temp.replace(path)
 print("Validated",len(out["items"]),"sermons; latest:",out["items"][0]["Day"],out["items"][0]["Title"])
if __name__=="__main__":main()
