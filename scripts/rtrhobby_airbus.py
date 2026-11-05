#!/usr/bin/env python3
"""Veille quotidienne RTRhobby, collection Airbus : uniquement périphériques cockpit."""
from __future__ import annotations
import datetime as dt
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"public"/"rtrhobby_airbus.json"
URL="https://rtrhobby.com/collections/airbus/products.json?limit=250"
LANDING="https://rtrhobby.com/collections/airbus"
EXCLUDE=re.compile(r"\b(boeing|b737|helicopter|collective|cable|charger|usb extension|joystick|rc paraglider)\b",re.I)
INCLUDE=re.compile(r"\b(a32x|a320|a319|a321|a31x|airbus|fenix|overhead|ovhd|ecam|rmp|acp|sidestick|trim wheel)\b",re.I)

def main():
    previous={}
    if OUT.exists():
        try:previous=json.loads(OUT.read_text(encoding="utf-8"))
        except (OSError,ValueError):pass
    now=dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        req=Request(URL,headers={"User-Agent":"Mozilla/5.0 JournalMSFS/1.0","Accept":"application/json"})
        with urlopen(req,timeout=25) as resp: products=json.load(resp)["products"]
        rows=[]
        for p in products:
            title=p.get("title","")
            if EXCLUDE.search(title) or not INCLUDE.search(title):continue
            variants=p.get("variants") or []
            prices=[]
            for v in variants:
                try:prices.append(float(v["price"]))
                except (KeyError,TypeError,ValueError):pass
            image=p.get("images") or []
            rows.append({"id":str(p.get("id","")),"title":title,"url":"https://rtrhobby.com/products/"+str(p.get("handle","")),"updated_at":p.get("updated_at",""),"published_at":p.get("published_at",""),"available":any(v.get("available",False) for v in variants),"price_usd":min(prices) if prices else None,"image_url":image[0].get("src","") if image else ""})
        if not rows:raise ValueError("Catalogue vide ou filtre trop restrictif")
        previous_rows={p["id"]:p for p in previous.get("products",[])}
        changes=[p for p in rows if p["id"] not in previous_rows or any(p.get(k)!=previous_rows[p["id"]].get(k) for k in ("price_usd","available","updated_at"))]
        OUT.write_text(json.dumps({"checked_at":now,"source_url":LANDING,"source_state":"ok","products":rows,"changes":changes},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(f"RTRhobby Airbus: {len(rows)} produits, {len(changes)} changements")
    except Exception as exc:
        previous.update({"checked_at":now,"source_url":LANDING,"source_state":"unavailable","error":str(exc)[:200]})
        OUT.write_text(json.dumps(previous,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("RTRhobby Airbus: source indisponible, catalogue précédent conservé:",exc)

if __name__=="__main__":main()
